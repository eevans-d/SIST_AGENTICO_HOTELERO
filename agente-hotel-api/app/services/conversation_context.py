"""
Servicio para el procesamiento del contexto conversacional y gestión de referencias anafóricas.
Permite mantener y recuperar información contextual de conversaciones previas.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import json

from ..core.logging import logger
from ..core.redis_client import get_redis


class ConversationContext:
    """
    Clase para almacenar y recuperar contexto conversacional.
    Mantiene histórico de entidades detectadas, intenciones y referencias.

    Características:
    - Almacenamiento en Redis con TTL
    - Resolución de referencias anafóricas (ej: "quiero reservarla" -> habitación previa)
    - Tracking de entidades a través de múltiples turnos
    - Detección de correcciones (ej: "no, quiero para 3 personas, no 2")
    - Extracción de referencias temporales relativas ("mañana", "el próximo fin de semana")
    """

    # Prefijo para claves Redis
    REDIS_PREFIX = "context:"
    # TTL para contexto (24 horas)
    CONTEXT_TTL_SECONDS = 86400

    def __init__(self):
        self.redis = None

    async def initialize(self):
        """Inicializar cliente Redis."""
        self.redis = await get_redis()

    async def store_context(
        self,
        user_id: str,
        channel: str,
        intent: str,
        entities: List[Dict[str, Any]],
        text: str,
        tenant_id: Optional[str] = None,
    ) -> str:
        """
        Almacenar contexto de un turno de conversación.

        Args:
            user_id: ID de usuario (teléfono, email)
            channel: Canal de comunicación (whatsapp, gmail)
            intent: Intención detectada
            entities: Entidades extraídas
            text: Texto original del usuario
            tenant_id: ID del tenant (opcional)

        Returns:
            ID del contexto almacenado
        """
        if not self.redis:
            await self.initialize()

        context_id = f"{user_id}:{channel}"
        if tenant_id:
            context_id = f"{tenant_id}:{context_id}"

        timestamp = datetime.utcnow().isoformat()

        # Recuperar contexto previo si existe
        previous_context = await self._get_raw_context(context_id)

        # Actualizar con nueva información
        context_data = {
            "last_updated": timestamp,
            "last_intent": intent,
            "last_text": text,
            "turns": previous_context.get("turns", 0) + 1,
            "entity_history": {},
            "intent_history": previous_context.get("intent_history", [])[-4:] + [intent],
        }

        # Guardar historial de entidades con tracking de origen
        entity_history = previous_context.get("entity_history", {})
        for entity in entities:
            entity_type = entity.get("entity")
            entity_value = entity.get("value")
            confidence = entity.get("confidence", 0.0)

            if entity_type and entity_value:
                if entity_type not in entity_history:
                    entity_history[entity_type] = []

                # Verificar si esta entidad representa una corrección
                is_correction = self._is_correction(
                    text, entity_type, entity_value, entity_history.get(entity_type, [])
                )

                entity_history[entity_type].append(
                    {
                        "value": entity_value,
                        "turn": context_data["turns"],
                        "timestamp": timestamp,
                        "confidence": confidence,
                        "is_correction": is_correction,
                    }
                )

                # Mantener solo las 3 menciones más recientes para cada tipo de entidad
                entity_history[entity_type] = entity_history[entity_type][-3:]

        context_data["entity_history"] = entity_history

        # Almacenar en Redis
        await self.redis.setex(f"{self.REDIS_PREFIX}{context_id}", self.CONTEXT_TTL_SECONDS, json.dumps(context_data))

        return context_id

    async def get_context(self, user_id: str, channel: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Recuperar contexto conversacional procesado.

        Args:
            user_id: ID de usuario (teléfono, email)
            channel: Canal de comunicación (whatsapp, gmail)
            tenant_id: ID del tenant (opcional)

        Returns:
            Diccionario con contexto procesado
        """
        if not self.redis:
            await self.initialize()

        context_id = f"{user_id}:{channel}"
        if tenant_id:
            context_id = f"{tenant_id}:{context_id}"

        raw_context = await self._get_raw_context(context_id)
        if not raw_context:
            return {"current_entities": {}, "has_context": False, "turns": 0}

        # Procesar contexto para extraer entidades actuales (última mención o corrección)
        current_entities = {}
        for entity_type, entries in raw_context.get("entity_history", {}).items():
            # Ordenar por timestamp descendente
            sorted_entries = sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)

            # Priorizar correcciones sobre menciones regulares
            correction_entries = [e for e in sorted_entries if e.get("is_correction", False)]
            if correction_entries:
                current_entities[entity_type] = correction_entries[0]["value"]
            elif sorted_entries:
                current_entities[entity_type] = sorted_entries[0]["value"]

        return {
            "current_entities": current_entities,
            "last_intent": raw_context.get("last_intent"),
            "turns": raw_context.get("turns", 0),
            "intent_history": raw_context.get("intent_history", []),
            "has_context": True,
        }

    async def resolve_anaphora(
        self, text: str, user_id: str, channel: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolver referencias anafóricas en el texto basadas en contexto previo.

        Args:
            text: Texto a analizar
            user_id: ID de usuario
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            Diccionario con resoluciones de referencias
        """
        if not self.redis:
            await self.initialize()

        # Obtener contexto
        context = await self.get_context(user_id, channel, tenant_id)
        if not context.get("has_context"):
            return {"resolved_text": text, "resolutions": {}}

        # Definir patrones anafóricos comunes en español
        anaphoric_patterns = {
            "room_type": [
                "la",
                "esa habitación",
                "ese cuarto",
                "esa suite",
                "la misma",
                "igual",
                "del mismo tipo",
            ],
            "check_in_date": [
                "esa fecha",
                "ese día",
                "esas fechas",
                "las mismas fechas",
                "la misma fecha",
                "misma fecha",
            ],
            "check_out_date": ["hasta entonces", "hasta esa fecha", "hasta ese día"],
            "num_guests": ["esa cantidad", "ese número de personas", "mismas personas"],
        }

        # Buscar patrones en el texto
        text_lower = text.lower()
        resolutions = {}
        resolved_text = text

        for entity_type, patterns in anaphoric_patterns.items():
            if entity_type in context["current_entities"]:
                for pattern in patterns:
                    if pattern in text_lower:
                        resolutions[entity_type] = context["current_entities"][entity_type]
                        # Reemplazar en texto para mejora de NLU posterior
                        resolved_text = resolved_text.replace(
                            pattern, f"{pattern} ({context['current_entities'][entity_type]})"
                        )

        return {"resolved_text": resolved_text, "resolutions": resolutions}

    async def clear_context(self, user_id: str, channel: str, tenant_id: Optional[str] = None) -> bool:
        """
        Eliminar contexto conversacional.

        Args:
            user_id: ID de usuario
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)

        Returns:
            True si se eliminó correctamente
        """
        if not self.redis:
            await self.initialize()

        context_id = f"{user_id}:{channel}"
        if tenant_id:
            context_id = f"{tenant_id}:{context_id}"

        await self.redis.delete(f"{self.REDIS_PREFIX}{context_id}")
        return True

    async def _get_raw_context(self, context_id: str) -> Dict[str, Any]:
        """Obtener contexto raw desde Redis."""
        if not self.redis:
            await self.initialize()

        context_data = await self.redis.get(f"{self.REDIS_PREFIX}{context_id}")
        if not context_data:
            return {}

        try:
            return json.loads(context_data)
        except json.JSONDecodeError:
            logger.error(f"Error decoding context data for {context_id}")
            return {}

    def _is_correction(
        self, text: str, entity_type: str, new_value: Any, previous_entries: List[Dict[str, Any]]
    ) -> bool:
        """
        Detectar si una entidad es una corrección basada en patrones lingüísticos.

        Args:
            text: Texto completo del usuario
            entity_type: Tipo de entidad
            new_value: Nuevo valor detectado
            previous_entries: Menciones previas de esta entidad

        Returns:
            True si parece ser una corrección
        """
        if not previous_entries:
            return False

        # Patrones de corrección en español
        correction_patterns = [
            "no, ",
            "no es ",
            "me equivoqué",
            "corregir",
            "cambiar",
            "en realidad",
            "quise decir",
            "mejor",
            "prefiero",
            "perdón",
        ]

        text_lower = text.lower()

        # Verificar patrones de corrección
        has_correction_pattern = any(pattern in text_lower for pattern in correction_patterns)

        # Verificar si el valor es distinto al anterior
        last_value = previous_entries[-1].get("value")
        value_changed = str(new_value) != str(last_value)

        return has_correction_pattern and value_changed


# Instancia global del servicio (lazy para permitir patch en tests)
conversation_context_service: Optional[ConversationContext] = None


async def get_conversation_context_service() -> ConversationContext:
    """Getter para el servicio de contexto conversacional."""
    global conversation_context_service
    if conversation_context_service is None:
        # Permite que ConversationContext sea parcheado en tests
        conversation_context_service = ConversationContext()
    if not conversation_context_service.redis:
        initialize_fn = getattr(conversation_context_service, "initialize", None)
        if callable(initialize_fn):
            try:
                import asyncio as _asyncio

                if _asyncio.iscoroutinefunction(initialize_fn):
                    await initialize_fn()
                else:
                    initialize_fn()
            except TypeError:
                # Puede ser MagicMock no awaitable: ignorar para tests
                pass
    return conversation_context_service
