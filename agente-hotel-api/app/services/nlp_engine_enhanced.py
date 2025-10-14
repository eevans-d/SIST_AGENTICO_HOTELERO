"""
NLP Engine con capacidades avanzadas - Fase E.5
Mejora del motor NLP con:
- Soporte multilingüe (ES, EN, PT)
- Procesamiento contextual
- Extracción avanzada de entidades
- Optimización de inferencia
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json

from prometheus_client import Counter, Gauge, Histogram, Summary
from ..core.circuit_breaker import CircuitBreaker
from ..exceptions.pms_exceptions import CircuitBreakerOpenError
from ..core.logging import logger
from ..core.redis_client import get_redis_client
from .multilingual_processor import get_multilingual_processor
from .conversational_memory import get_conversational_memory

# Métricas
nlp_operations = Counter("nlp_operations_total", "NLP operations", ["operation", "status"])
nlp_errors = Counter("nlp_errors_total", "NLP errors", ["operation", "error_type"])
nlp_circuit_breaker_state = Gauge(
    "nlp_circuit_breaker_state", "NLP circuit breaker state (0=closed, 1=open, 2=half-open)"
)
nlp_circuit_breaker_calls = Counter("nlp_circuit_breaker_calls_total", "NLP circuit breaker calls", ["state", "result"])
nlp_confidence = Histogram(
    "nlp_confidence_score", "NLP confidence score distribution", buckets=[0.3, 0.5, 0.7, 0.85, 0.95, 1.0]
)
nlp_intent_predictions = Counter(
    "nlp_intent_predictions_total", "Intent predictions", ["intent", "confidence_bucket", "language"]
)
nlp_entity_extraction = Counter("nlp_entity_extraction_total", "Entity extractions", ["entity_type", "extractor"])
nlp_context_usage = Counter("nlp_context_usage_total", "Context usage in NLP", ["operation", "success"])
nlp_cache_operations = Counter("nlp_cache_operations_total", "Cache operations", ["operation", "result"])
nlp_inference_time = Summary("nlp_inference_seconds", "Inference time", ["model_type", "language"])


class EnhancedNLPEngine:
    """
    Motor NLP mejorado con procesamiento multilingüe y contextual.

    Características:
    - Modelos específicos por idioma
    - Memoria conversacional
    - Caché de resultados
    - Fallbacks graduales
    - Integración optimizada con STT
    """

    def __init__(self, model_path: Optional[str] = None, cache_enabled: bool = True):
        """
        Inicializa el motor NLP mejorado.

        Args:
            model_path: Ruta al modelo Rasa (.tar.gz). Si es None, usa ubicación por defecto.
            cache_enabled: Si se debe usar caché Redis para respuestas frecuentes.
        """
        # Circuit breaker para llamadas NLP
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
        nlp_circuit_breaker_state.set(0)  # 0 = cerrado

        # Configuración de modelo
        self.model_path = model_path or self._resolve_model_path()
        self.models = {}
        self.model_version = None
        self.model_loaded_at: Optional[datetime] = None

        # Caché
        self.cache_enabled = cache_enabled
        self.redis = None
        self._redis_initialized = False

        # Servicios de asistencia NLP (inicialización lazy)
        self._multilingual_processor = None
        self._conversational_memory = None

        # Estadísticas y rendimiento
        self.stats = {
            "processed_messages": 0,
            "cache_hits": 0,
            "fallbacks_used": 0,
            "errors": 0,
            "languages_detected": {"es": 0, "en": 0, "pt": 0},
        }

    def _resolve_model_path(self) -> str:
        """
        Resuelve la ruta al modelo Rasa.

        Returns:
            Ruta al modelo Rasa
        """
        # Verificar variable de entorno
        env_path = os.getenv("RASA_MODEL_PATH")
        if env_path and Path(env_path).exists():
            logger.info(f"Usando modelo Rasa desde RASA_MODEL_PATH: {env_path}")
            return env_path

        # Verificar ubicación por defecto (symlink creado por train_rasa.sh)
        project_root = Path(__file__).parent.parent.parent
        default_path = project_root / "rasa_nlu" / "models" / "latest.tar.gz"

        if default_path.exists():
            logger.info(f"Usando modelo Rasa desde ubicación por defecto: {default_path}")
            return str(default_path)

        # No se encontró modelo - se usará modo de fallback
        logger.warning(
            "No se encontró modelo Rasa. El motor NLP funcionará en modo fallback. "
            "Entrena un modelo con: scripts/train_rasa.sh"
        )
        return ""

    async def _init_services(self):
        """Inicializa los servicios asociados de forma lazy."""
        # Inicializar Redis
        if self.cache_enabled and not self._redis_initialized:
            try:
                self.redis = await get_redis_client()
                self._redis_initialized = True
            except Exception as e:
                logger.warning(f"Error al conectar a Redis, deshabilitando caché: {e}")
                self.cache_enabled = False

        # Inicializar procesador multilingüe
        if not self._multilingual_processor:
            self._multilingual_processor = await get_multilingual_processor()

        # Inicializar memoria conversacional
        if not self._conversational_memory:
            self._conversational_memory = await get_conversational_memory()

    async def process_message(
        self, text: str, user_id: Optional[str] = None, channel: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje para extraer intención y entidades.

        Args:
            text: Mensaje del usuario
            user_id: ID del usuario (para procesamiento contextual)
            channel: Canal del mensaje (para procesamiento contextual)
            tenant_id: ID del tenant (opcional)

        Returns:
            Diccionario con estructura:
            {
                "intent": {"name": str, "confidence": float},
                "entities": [{"entity": str, "value": str, "start": int, "end": int}],
                "text": str,
                "language": str,
                "model_version": str,
                "fallback": bool (solo si se usó fallback),
                "context_used": bool (solo si se usó contexto)
            }
        """
        # Inicializar servicios si es necesario
        await self._init_services()

        try:
            # Verificar si hay resultado en caché
            cached_result = None
            cache_key = None

            if self.cache_enabled and self.redis and len(text) < 100:
                # Solo cachear mensajes cortos para evitar abuso
                cache_key = f"nlp:result:{text.lower().strip()}"
                cached_result = await self.redis.get(cache_key)

                if cached_result:
                    try:
                        result = json.loads(cached_result)
                        nlp_cache_operations.labels(operation="get", result="hit").inc()
                        self.stats["cache_hits"] += 1
                        return result
                    except json.JSONDecodeError:
                        nlp_cache_operations.labels(operation="get", result="error").inc()
                        # Continuar con procesamiento normal
                else:
                    nlp_cache_operations.labels(operation="get", result="miss").inc()

            # Procesar con circuit breaker
            result = await self.circuit_breaker.call(self._process_with_context, text, user_id, channel, tenant_id)

            nlp_operations.labels(operation="process_message", status="success").inc()

            # Registrar métricas
            confidence = result.get("intent", {}).get("confidence", 0.0)
            nlp_confidence.observe(confidence)

            # Métricas de predicción de intención (agrupadas por confianza)
            intent_name = result.get("intent", {}).get("name", "unknown")
            confidence_bucket = self._get_confidence_bucket(confidence)
            language = result.get("language", "es")
            nlp_intent_predictions.labels(
                intent=intent_name, confidence_bucket=confidence_bucket, language=language
            ).inc()

            # Actualizar estadísticas
            self.stats["processed_messages"] += 1
            self.stats["languages_detected"][language] = self.stats["languages_detected"].get(language, 0) + 1

            # Guardar en caché si es apropiado
            if (
                self.cache_enabled
                and self.redis
                and cache_key
                and confidence > 0.85
                and not result.get("fallback", False)
            ):
                try:
                    # Cachear solo resultados de alta confianza por 15 minutos
                    await self.redis.set(cache_key, json.dumps(result), ex=900)  # 15 minutos
                    nlp_cache_operations.labels(operation="set", result="success").inc()
                except Exception as e:
                    logger.warning(f"Error al guardar en caché: {e}")
                    nlp_cache_operations.labels(operation="set", result="error").inc()

            return result

        except CircuitBreakerOpenError:
            # Circuit breaker abierto: usar fallback
            logger.warning("Circuit breaker de NLP abierto, usando respuesta de fallback")
            nlp_circuit_breaker_calls.labels(state="open", result="fallback").inc()
            nlp_circuit_breaker_state.set(1)  # 1 = abierto
            self.stats["fallbacks_used"] += 1
            return self._fallback_response(text, language="es")

        except Exception as e:
            # Otros errores
            logger.error(f"Error en procesamiento NLP: {e}", exc_info=True)
            nlp_operations.labels(operation="process_message", status="error").inc()
            nlp_errors.labels(operation="process_message", error_type=type(e).__name__).inc()
            self.stats["errors"] += 1
            return self._fallback_response(text, language="es")

    async def _process_with_context(
        self, text: str, user_id: Optional[str], channel: Optional[str], tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Procesa mensaje con contexto conversacional.

        Args:
            text: Mensaje del usuario
            user_id: ID del usuario
            channel: Canal del mensaje
            tenant_id: ID del tenant (opcional)

        Returns:
            Resultado del procesamiento con contexto
        """
        start_time = asyncio.get_event_loop().time()
        context_applied = False

        # Paso 1: Obtener idioma de conversación previa si hay contexto
        language = None
        if user_id and channel:
            try:
                language = await self._conversational_memory.get_conversation_language(user_id, channel, tenant_id)
            except Exception as e:
                logger.warning(f"Error al recuperar idioma de conversación: {e}")

        # Paso 2: Detectar o confirmar idioma
        lang_result = await self._multilingual_processor.detect_language(text)
        detected_language = lang_result["language"]

        # Si el idioma detectado es diferente al de la conversación con alta confianza, actualizar
        if language and detected_language != language and lang_result["confidence"] > 0.8:
            language = detected_language
        elif not language:
            language = detected_language

        # Paso 3: Resolver referencias anafóricas si hay contexto
        resolved_text = text
        if user_id and channel:
            try:
                resolved_text = await self._conversational_memory.resolve_anaphora(user_id, text, channel, tenant_id)
                if resolved_text != text:
                    context_applied = True
                    nlp_context_usage.labels(operation="anaphora_resolution", success="true").inc()
            except Exception as e:
                logger.warning(f"Error al resolver anáforas: {e}")
                nlp_context_usage.labels(operation="anaphora_resolution", success="false").inc()

        # Paso 4: Procesar texto con modelo NLP multilingüe
        result = await self._multilingual_processor.process_text(resolved_text, language)

        # Paso 5: Mejorar entidades con contexto si es necesario
        if user_id and channel:
            try:
                # Verificar si es una pregunta de seguimiento
                is_followup = await self._conversational_memory.is_follow_up_question(
                    user_id, result["intent"]["name"], channel, tenant_id
                )

                if is_followup:
                    context_applied = True
                    # Obtener entidades relevantes del contexto
                    entity_types = await self._get_relevant_entity_types(result["intent"]["name"])
                    contextual_entities = await self._conversational_memory.get_relevant_entities(
                        user_id, entity_types, channel, tenant_id
                    )

                    # Complementar entidades faltantes con contexto
                    current_entities = {e["entity"]: e for e in result["entities"]}
                    for entity_type, value in contextual_entities.items():
                        if entity_type not in current_entities:
                            # Añadir entidad del contexto
                            result["entities"].append(
                                {
                                    "entity": entity_type,
                                    "value": value,
                                    "start": 0,
                                    "end": 0,
                                    "confidence": 0.9,
                                    "extractor": "contextual_memory",
                                }
                            )
                            nlp_entity_extraction.labels(entity_type=entity_type, extractor="contextual_memory").inc()

                    nlp_context_usage.labels(operation="entity_completion", success="true").inc()
            except Exception as e:
                logger.warning(f"Error al aplicar contexto a entidades: {e}")
                nlp_context_usage.labels(operation="entity_completion", success="false").inc()

        # Paso 6: Guardar contexto para uso futuro
        if user_id and channel:
            try:
                await self._conversational_memory.store_context(
                    user_id, result["entities"], text, result["intent"]["name"], channel, tenant_id
                )
                nlp_context_usage.labels(operation="store_context", success="true").inc()
            except Exception as e:
                logger.warning(f"Error al guardar contexto: {e}")
                nlp_context_usage.labels(operation="store_context", success="false").inc()

        # Añadir metadatos al resultado
        result["text"] = text
        result["model_version"] = self.model_version
        if context_applied:
            result["context_used"] = True

        # Registrar tiempo de inferencia
        inference_time = asyncio.get_event_loop().time() - start_time
        nlp_inference_time.labels(model_type="enhanced", language=language).observe(inference_time)

        return result

    async def _get_relevant_entity_types(self, intent: str) -> List[str]:
        """
        Determina qué tipos de entidades son relevantes para la intención.

        Args:
            intent: Nombre de la intención

        Returns:
            Lista de tipos de entidades relevantes
        """
        # Mapeo de intenciones a tipos de entidades relevantes
        intent_entity_map = {
            "check_availability": ["check_in_date", "check_out_date", "num_guests", "room_type"],
            "make_reservation": ["check_in_date", "check_out_date", "num_guests", "room_type", "reservation_code"],
            "pricing_info": ["room_type", "check_in_date", "check_out_date"],
            "modify_reservation": ["reservation_code", "check_in_date", "check_out_date", "num_guests", "room_type"],
            "cancel_reservation": ["reservation_code"],
            "ask_services": ["amenity"],
            "ask_location": ["location"],
            # Añadir más mapeos según sea necesario
        }

        return intent_entity_map.get(intent, [])

    def _get_confidence_bucket(self, confidence: float) -> str:
        """
        Asigna puntuación de confianza a un bucket para métricas.

        Args:
            confidence: Puntuación de confianza (0.0-1.0)

        Returns:
            Etiqueta del bucket: "low", "medium", "high", "very_high"
        """
        if confidence < 0.5:
            return "low"
        elif confidence < 0.7:
            return "medium"
        elif confidence < 0.85:
            return "high"
        else:
            return "very_high"

    def _fallback_response(self, text: str, language: str = "es") -> Dict[str, Any]:
        """
        Genera respuesta de fallback cuando NLP no está disponible.

        Args:
            text: Texto original
            language: Código de idioma

        Returns:
            Respuesta con intent desconocido y flag de fallback
        """
        # Intentar determinar intent con reglas básicas
        text_lower = text.lower()

        # Reglas multilingües
        intent_rules = {
            "es": {
                "check_availability": ["disponibilidad", "disponible", "habitacion", "cuarto", "hay lugar"],
                "make_reservation": ["reservar", "reserva", "reservacion", "booking", "quiero una habitacion"],
                "pricing_info": ["precio", "costo", "tarifa", "valor", "cuánto cuesta"],
                "ask_services": ["servicio", "wifi", "desayuno", "piscina", "gimnasio"],
                "ask_location": ["donde", "ubicacion", "dirección", "como llego"],
            },
            "en": {
                "check_availability": ["availability", "available", "room", "vacancy", "have space"],
                "make_reservation": ["book", "reserve", "booking", "reservation", "want a room"],
                "pricing_info": ["price", "cost", "rate", "how much", "fee"],
                "ask_services": ["service", "wifi", "breakfast", "pool", "gym"],
                "ask_location": ["where", "location", "address", "how to get"],
            },
            "pt": {
                "check_availability": ["disponibilidade", "disponível", "quarto", "vaga", "tem lugar"],
                "make_reservation": ["reservar", "reserva", "quero um quarto", "fazer reserva"],
                "pricing_info": ["preço", "custo", "tarifa", "valor", "quanto custa"],
                "ask_services": ["serviço", "wifi", "café da manhã", "piscina", "academia"],
                "ask_location": ["onde", "localização", "endereço", "como chegar"],
            },
        }

        # Buscar coincidencia en reglas del idioma
        rules = intent_rules.get(language, intent_rules["es"])

        for intent, keywords in rules.items():
            if any(keyword in text_lower for keyword in keywords):
                return {
                    "intent": {"name": intent, "confidence": 0.5},
                    "entities": [],
                    "fallback": True,
                    "text": text,
                    "language": language,
                }

        # Si no hay coincidencia, devolver intent desconocido
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": [],
            "fallback": True,
            "text": text,
            "language": language,
        }

    async def handle_low_confidence(self, intent: Dict[str, Any], language: str = "es") -> Optional[Dict[str, Any]]:
        """
        Maneja predicciones de intención con baja confianza.

        Args:
            intent: Diccionario de intent con nombre y confianza
            language: Código de idioma

        Returns:
            dict con respuesta y flag de derivación a humano, o None si la confianza es aceptable
        """
        confidence = intent.get("confidence", 0.0)

        # Confianza muy baja (<0.3): escalar a humano
        if confidence < 0.3:
            response_templates = {
                "es": "Disculpa, no estoy seguro de entender tu consulta. ¿Podrías reformularla o te conecto con un representante?",
                "en": "Sorry, I'm not sure I understand your query. Could you rephrase it or shall I connect you with a representative?",
                "pt": "Desculpe, não tenho certeza se entendi sua consulta. Você poderia reformulá-la ou devo conectá-lo a um representante?",
            }

            return {
                "response": response_templates.get(language, response_templates["es"]),
                "requires_human": True,
            }

        # Confianza baja (0.3-0.7): ofrecer menú
        if confidence < 0.7:
            menu_templates = {
                "es": (
                    "¿En qué puedo ayudarte?\n"
                    "1️⃣ Consultar disponibilidad\n"
                    "2️⃣ Hacer una reserva\n"
                    "3️⃣ Modificar/cancelar reserva\n"
                    "4️⃣ Información del hotel (precios, servicios, ubicación)\n"
                    "5️⃣ Hablar con recepción"
                ),
                "en": (
                    "How can I help you?\n"
                    "1️⃣ Check availability\n"
                    "2️⃣ Make a reservation\n"
                    "3️⃣ Modify/cancel reservation\n"
                    "4️⃣ Hotel information (prices, services, location)\n"
                    "5️⃣ Speak with reception"
                ),
                "pt": (
                    "Como posso ajudá-lo?\n"
                    "1️⃣ Verificar disponibilidade\n"
                    "2️⃣ Fazer uma reserva\n"
                    "3️⃣ Modificar/cancelar reserva\n"
                    "4️⃣ Informações do hotel (preços, serviços, localização)\n"
                    "5️⃣ Falar com a recepção"
                ),
            }

            return {
                "response": menu_templates.get(language, menu_templates["es"]),
                "requires_human": False,
            }

        # Confianza aceptable (≥0.7): proceder normalmente
        return None

    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el modelo cargado.

        Returns:
            dict con metadatos del modelo
        """
        return {
            "model_path": self.model_path,
            "model_version": self.model_version,
            "model_loaded_at": self.model_loaded_at.isoformat() if self.model_loaded_at else None,
            "multilingual_support": True,
            "languages": ["es", "en", "pt"],
            "contextual_memory": True,
            "fallback_mode": not self.model_path,
            "stats": self.stats,
        }


# Variable para singleton
_nlp_engine_instance = None


async def get_enhanced_nlp_engine() -> EnhancedNLPEngine:
    """
    Devuelve una instancia singleton de EnhancedNLPEngine.
    """
    global _nlp_engine_instance

    if _nlp_engine_instance is None:
        _nlp_engine_instance = EnhancedNLPEngine()

    return _nlp_engine_instance
