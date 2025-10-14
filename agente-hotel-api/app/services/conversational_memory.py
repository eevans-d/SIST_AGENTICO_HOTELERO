"""
Módulo para gestión de memoria conversacional y contexto.

Este módulo proporciona funcionalidades para:
1. Mantener contexto entre mensajes de la conversación
2. Resolver referencias anafóricas (él, ella, eso, etc.)
3. Rastrear información previamente mencionada
4. Gestionar "follow-up questions" sin repetir toda la información
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import re

from prometheus_client import Counter, Histogram, Gauge
from ..core.logging import logger
from ..core.redis_client import get_redis_client

# Métricas para monitoreo
context_resolution_total = Counter("context_resolution_total", "Resoluciones de contexto", ["operation", "result"])

anaphora_resolution_total = Counter(
    "anaphora_resolution_total", "Resoluciones de referencias anafóricas", ["type", "success"]
)

context_memory_size = Gauge("context_memory_size", "Tamaño de la memoria contextual", ["tenant_id"])

context_operations_latency = Histogram(
    "context_operations_latency_seconds", "Latencia de operaciones de contexto", ["operation"]
)

ENTITY_LIFESPAN = {
    "check_in_date": timedelta(minutes=30),
    "check_out_date": timedelta(minutes=30),
    "num_guests": timedelta(minutes=30),
    "room_type": timedelta(minutes=30),
    "reservation_code": timedelta(hours=2),
    "location": timedelta(minutes=20),
    "amenity": timedelta(minutes=15),
    "price_range": timedelta(minutes=20),
}

# Patrones para detectar referencias anafóricas
ANAPHORA_PATTERNS = {
    "es": {
        "object": r"\b(esa habitación|ese cuarto|esa fecha|ese precio)\b",
        "temporal": r"\b(esas fechas|esos días|ese día|esa semana)\b",
        "personal": r"\b(ellos|ellas|él|ella|nosotros|ustedes)\b",
        "demonstrative": r"\b(esto|eso|aquello|esta|ese|aquel|estas|esos|aquellos)\b",
    },
    "en": {
        "object": r"\b(that room|those rooms|that price|those prices)\b",
        "temporal": r"\b(those dates|those days|that day|that week)\b",
        "personal": r"\b(they|them|he|she|we|you|us)\b",
        "demonstrative": r"\b(this|that|these|those|it)\b",
    },
    "pt": {
        "object": r"\b(esse quarto|essa habitação|esse preço)\b",
        "temporal": r"\b(essas datas|esses dias|esse dia|essa semana)\b",
        "personal": r"\b(eles|elas|ele|ela|nós|vocês)\b",
        "demonstrative": r"\b(isto|isso|aquilo|esta|esse|aquele|estas|esses|aqueles)\b",
    },
}


class ConversationalMemory:
    """
    Gestiona la memoria conversacional para mantener contexto entre mensajes.

    Características:
    - Almacenamiento en Redis con TTL
    - Resolución de referencias anafóricas
    - Seguimiento de entidades mencionadas
    - Detección automática de idioma
    """

    def __init__(self, redis_client=None):
        """
        Inicializa la memoria conversacional.

        Args:
            redis_client: Cliente Redis opcional. Si no se proporciona, se crea uno.
        """
        self.redis = redis_client
        self._redis_initialized = redis_client is not None

    async def _init_redis(self):
        """Inicializa la conexión a Redis de forma lazy."""
        if not self._redis_initialized:
            self.redis = await get_redis_client()
            self._redis_initialized = True

    async def store_context(
        self, user_id: str, entities: List[Dict], text: str, intent: str, channel: str, tenant_id: Optional[str] = None
    ) -> None:
        """
        Almacena el contexto de la conversación.

        Args:
            user_id: ID del usuario
            entities: Lista de entidades detectadas
            text: Texto del mensaje
            intent: Intención detectada
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)
        """
        await self._init_redis()
        start_time = datetime.now()

        try:
            # Clave para Redis
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"

            # Obtener contexto existente
            existing_context = await self._get_raw_context(context_key)
            context = existing_context or {
                "entities": {},
                "history": [],
                "language": "es",  # Por defecto español
                "last_intent": None,
                "last_update": datetime.utcnow().isoformat(),
            }

            # Actualizar historial
            history_entry = {"text": text, "intent": intent, "timestamp": datetime.utcnow().isoformat()}
            context["history"] = (context.get("history", []) + [history_entry])[-10:]  # Mantener solo los últimos 10

            # Actualizar entities con timestamps
            current_time = datetime.utcnow()

            # Procesar nuevas entidades
            for entity in entities:
                entity_key = entity["entity"]
                entity_value = entity["value"]

                # Añadir timestamp a la entidad
                context["entities"][entity_key] = {
                    "value": entity_value,
                    "updated_at": current_time.isoformat(),
                    "mention_count": context.get("entities", {}).get(entity_key, {}).get("mention_count", 0) + 1,
                }

            # Actualizar última intención
            context["last_intent"] = intent
            context["last_update"] = current_time.isoformat()

            # Detectar idioma si no está establecido o ha cambiado
            if not context.get("language") or len(context["history"]) % 5 == 0:
                detected_lang = await self._detect_language(text)
                if detected_lang:
                    context["language"] = detected_lang

            # Guardar en Redis con TTL de 30 minutos
            await self.redis.set(
                context_key,
                json.dumps(context),
                ex=1800,  # 30 minutos
            )

            # Reportar métrica
            context_memory_size.labels(tenant_id=tenant_id or "default").set(len(json.dumps(context)))
            context_resolution_total.labels(operation="store", result="success").inc()

        except Exception as e:
            logger.error(f"Error storing context: {e}", exc_info=True)
            context_resolution_total.labels(operation="store", result="error").inc()

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            context_operations_latency.labels(operation="store").observe(duration)

    async def resolve_anaphora(self, user_id: str, text: str, channel: str, tenant_id: Optional[str] = None) -> str:
        """
        Resuelve referencias anafóricas en el texto.

        Args:
            user_id: ID del usuario
            text: Texto a procesar
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            Texto con referencias resueltas
        """
        await self._init_redis()
        start_time = datetime.now()
        result_text = text
        success = False
        anaphora_type = "none"

        try:
            # Obtener contexto
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"
            context = await self._get_raw_context(context_key)

            if not context:
                return text

            # Determinar idioma para seleccionar patrones adecuados
            language = context.get("language", "es")
            patterns = ANAPHORA_PATTERNS.get(language, ANAPHORA_PATTERNS["es"])

            # Comprobar patrones anafóricos
            for a_type, pattern in patterns.items():
                anaphora_matches = re.search(pattern, text.lower())
                if anaphora_matches:
                    anaphora_type = a_type
                    # Hay una referencia anafórica, intentar resolverla
                    resolved_text = await self._resolve_reference(text, context, a_type)
                    if resolved_text != text:
                        result_text = resolved_text
                        success = True
                        break

            anaphora_resolution_total.labels(type=anaphora_type, success=str(success).lower()).inc()
            return result_text

        except Exception as e:
            logger.error(f"Error resolving anaphora: {e}", exc_info=True)
            anaphora_resolution_total.labels(type="error", success="false").inc()
            return text

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            context_operations_latency.labels(operation="resolve_anaphora").observe(duration)

    async def get_relevant_entities(
        self, user_id: str, entity_types: List[str], channel: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene entidades relevantes del contexto.

        Args:
            user_id: ID del usuario
            entity_types: Tipos de entidad a recuperar
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            Diccionario con entidades relevantes
        """
        await self._init_redis()
        start_time = datetime.now()
        result = {}

        try:
            # Obtener contexto
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"
            context = await self._get_raw_context(context_key)

            if not context or "entities" not in context:
                context_resolution_total.labels(operation="get_entities", result="no_context").inc()
                return {}

            # Filtrar entidades por tipo y comprobar vigencia
            current_time = datetime.utcnow()
            for entity_type in entity_types:
                if entity_type in context["entities"]:
                    entity_data = context["entities"][entity_type]
                    updated_at = datetime.fromisoformat(entity_data["updated_at"])

                    # Comprobar si la entidad sigue siendo relevante (no ha caducado)
                    if current_time - updated_at <= ENTITY_LIFESPAN.get(entity_type, timedelta(minutes=15)):
                        result[entity_type] = entity_data["value"]

            context_resolution_total.labels(operation="get_entities", result="found" if result else "not_found").inc()

            return result

        except Exception as e:
            logger.error(f"Error getting relevant entities: {e}", exc_info=True)
            context_resolution_total.labels(operation="get_entities", result="error").inc()
            return {}

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            context_operations_latency.labels(operation="get_entities").observe(duration)

    async def get_conversation_language(self, user_id: str, channel: str, tenant_id: Optional[str] = None) -> str:
        """
        Obtiene el idioma detectado para la conversación.

        Args:
            user_id: ID del usuario
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            Código de idioma (es, en, pt) o "es" por defecto
        """
        await self._init_redis()

        try:
            # Obtener contexto
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"
            context = await self._get_raw_context(context_key)

            if not context:
                return "es"  # Español por defecto

            return context.get("language", "es")

        except Exception as e:
            logger.error(f"Error getting conversation language: {e}", exc_info=True)
            return "es"  # Español por defecto

    async def is_follow_up_question(
        self, user_id: str, current_intent: str, channel: str, tenant_id: Optional[str] = None
    ) -> bool:
        """
        Determina si la pregunta actual es una continuación de la conversación.

        Args:
            user_id: ID del usuario
            current_intent: Intención actual
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            True si es una pregunta de seguimiento
        """
        await self._init_redis()

        try:
            # Obtener contexto
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"
            context = await self._get_raw_context(context_key)

            if not context or "history" not in context or len(context["history"]) < 2:
                return False

            # Verificar si hay una conversación en curso
            last_update = datetime.fromisoformat(context["last_update"])
            if datetime.utcnow() - last_update > timedelta(minutes=5):
                # Si ha pasado más de 5 minutos, no es una pregunta de seguimiento
                return False

            # Verificar intención previa compatible
            last_intent = context.get("last_intent")

            # Mapeo de intenciones relacionadas
            related_intents = {
                "check_availability": ["make_reservation", "pricing_info", "room_details"],
                "make_reservation": ["check_availability", "pricing_info", "payment_methods"],
                "pricing_info": ["check_availability", "make_reservation", "room_details"],
                # Añadir más mapeos según sea necesario
            }

            # Comprobar si la intención actual está relacionada con la anterior
            if last_intent in related_intents and current_intent in related_intents.get(last_intent, []):
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking follow-up question: {e}", exc_info=True)
            return False

    async def clear_context(self, user_id: str, channel: str, tenant_id: Optional[str] = None) -> None:
        """
        Elimina el contexto almacenado para un usuario.

        Args:
            user_id: ID del usuario
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)
        """
        await self._init_redis()

        try:
            context_key = f"context:{tenant_id or 'default'}:{channel}:{user_id}"
            await self.redis.delete(context_key)
            context_resolution_total.labels(operation="clear", result="success").inc()

        except Exception as e:
            logger.error(f"Error clearing context: {e}", exc_info=True)
            context_resolution_total.labels(operation="clear", result="error").inc()

    async def _get_raw_context(self, context_key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el contexto en bruto de Redis.

        Args:
            context_key: Clave de Redis para el contexto

        Returns:
            Contexto como diccionario o None si no existe
        """
        try:
            raw_data = await self.redis.get(context_key)
            if not raw_data:
                return None

            return json.loads(raw_data)

        except Exception as e:
            logger.error(f"Error getting raw context: {e}", exc_info=True)
            return None

    async def _detect_language(self, text: str) -> Optional[str]:
        """
        Detecta el idioma del texto.

        Args:
            text: Texto a analizar

        Returns:
            Código de idioma (es, en, pt) o None si no se puede detectar
        """
        # Palabras clave específicas por idioma
        es_keywords = {"hola", "gracias", "habitación", "reserva", "precio", "disponible"}
        en_keywords = {"hello", "thanks", "room", "booking", "price", "available"}
        pt_keywords = {"olá", "obrigado", "quarto", "reserva", "preço", "disponível"}

        # Contar coincidencias
        text_lower = text.lower()
        es_count = sum(1 for word in es_keywords if word in text_lower)
        en_count = sum(1 for word in en_keywords if word in text_lower)
        pt_count = sum(1 for word in pt_keywords if word in text_lower)

        # Determinar idioma
        if es_count > max(en_count, pt_count):
            return "es"
        elif en_count > max(es_count, pt_count):
            return "en"
        elif pt_count > max(es_count, en_count):
            return "pt"

        # Si no hay coincidencias claras, intentar con reglas gramaticales
        if "the " in text_lower or " is " in text_lower:
            return "en"
        elif "el " in text_lower or "la " in text_lower or " está " in text_lower:
            return "es"
        elif "o " in text_lower or " está " in text_lower:
            return "pt"

        # Por defecto, devolver español
        return "es"

    async def _resolve_reference(self, text: str, context: Dict[str, Any], anaphora_type: str) -> str:
        """
        Resuelve una referencia anafórica en el texto.

        Args:
            text: Texto con referencia
            context: Contexto de la conversación
            anaphora_type: Tipo de anáfora detectada

        Returns:
            Texto con referencia resuelta o texto original si no se puede resolver
        """
        if not context or "entities" not in context:
            return text

        if anaphora_type == "temporal" and any(
            entity in context["entities"] for entity in ["check_in_date", "check_out_date"]
        ):
            # Resolver referencias temporales
            checkin = context["entities"].get("check_in_date", {}).get("value", "")
            checkout = context["entities"].get("check_out_date", {}).get("value", "")

            if checkin and checkout:
                # Detectar idioma
                language = context.get("language", "es")

                if language == "es":
                    replacements = {
                        "esas fechas": f"del {checkin} al {checkout}",
                        "esos días": f"del {checkin} al {checkout}",
                        "ese día": checkin,
                        "esa semana": f"la semana del {checkin}",
                    }
                elif language == "en":
                    replacements = {
                        "those dates": f"from {checkin} to {checkout}",
                        "those days": f"from {checkin} to {checkout}",
                        "that day": checkin,
                        "that week": f"the week of {checkin}",
                    }
                elif language == "pt":
                    replacements = {
                        "essas datas": f"de {checkin} a {checkout}",
                        "esses dias": f"de {checkin} a {checkout}",
                        "esse dia": checkin,
                        "essa semana": f"a semana de {checkin}",
                    }

                # Realizar reemplazos
                result = text
                for anaphora, replacement in replacements.items():
                    result = re.sub(r"\b" + anaphora + r"\b", replacement, result, flags=re.IGNORECASE)

                return result

        elif anaphora_type == "object" and "room_type" in context["entities"]:
            # Resolver referencias a objetos (habitaciones)
            room_type = context["entities"]["room_type"]["value"]

            # Detectar idioma
            language = context.get("language", "es")

            if language == "es":
                replacements = {"esa habitación": f"la habitación {room_type}", "ese cuarto": f"el cuarto {room_type}"}
            elif language == "en":
                replacements = {"that room": f"the {room_type} room", "those rooms": f"the {room_type} rooms"}
            elif language == "pt":
                replacements = {"esse quarto": f"o quarto {room_type}", "essa habitação": f"a habitação {room_type}"}

            # Realizar reemplazos
            result = text
            for anaphora, replacement in replacements.items():
                result = re.sub(r"\b" + anaphora + r"\b", replacement, result, flags=re.IGNORECASE)

            return result

        # Para otros tipos de anáforas, mantener texto original por ahora
        return text


# Variable para singleton
_conversational_memory_instance = None


async def get_conversational_memory() -> ConversationalMemory:
    """
    Devuelve una instancia singleton de ConversationalMemory.
    """
    global _conversational_memory_instance

    if _conversational_memory_instance is None:
        redis_client = await get_redis_client()
        _conversational_memory_instance = ConversationalMemory(redis_client=redis_client)

    return _conversational_memory_instance
