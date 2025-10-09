"""
Enhanced NLP Engine con soporte multilingüe y contexto conversacional.
Actualización de la Fase E.5 del motor NLP con mejoras significativas.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json

from prometheus_client import Counter, Gauge, Histogram
from ..core.circuit_breaker import CircuitBreaker
from ..exceptions.pms_exceptions import CircuitBreakerOpenError
from ..core.logging import logger
from ..core.redis_client import get_redis

# Servicios adicionales
from .conversation_context import get_conversation_context_service
from .multilingual_service import get_multilingual_nlp_service, SupportedLanguage

# Métricas
nlp_operations = Counter("nlp_operations_total", "NLP operations", ["operation", "status"])
nlp_errors = Counter("nlp_errors_total", "NLP errors", ["operation", "error_type"])
nlp_circuit_breaker_state = Gauge("nlp_circuit_breaker_state", "NLP circuit breaker state (0=closed, 1=open, 2=half-open)")
nlp_circuit_breaker_calls = Counter("nlp_circuit_breaker_calls_total", "NLP circuit breaker calls", ["state", "result"])
nlp_confidence = Histogram("nlp_confidence_score", "NLP confidence score distribution", buckets=[0.3, 0.5, 0.7, 0.85, 0.95, 1.0])
nlp_intent_predictions = Counter("nlp_intent_predictions_total", "Intent predictions", ["intent", "confidence_bucket", "language"])
nlp_entity_extractions = Counter("nlp_entity_extractions_total", "Entity extractions", ["entity_type", "extractor"])
nlp_context_usage = Counter("nlp_context_usage_total", "Context usage in NLP processing", ["context_type", "result"])
nlp_inference_latency = Histogram("nlp_inference_latency_seconds", "NLP inference latency", ["model_type", "language"])


class EnhancedNLPEngine:
    """
    NLP Engine mejorado con soporte multilingüe, contextual y optimizado.
    
    Nuevas características:
    - Soporte para español, inglés y portugués
    - Procesamiento contextual para referencia anafóricas
    - Mejora de extracción de entidades
    - Caché de inferencia para respuestas rápidas
    - Sistema de fallback gradual
    - Optimizaciones de rendimiento para entornos de producción
    """
    
    def __init__(self, model_directory: Optional[str] = None):
        """
        Inicializar NLP Engine mejorado.
        
        Args:
            model_directory: Directorio con modelos por idioma. Si es None, se usa la ubicación por defecto.
        """
        # Circuit breaker para llamadas NLP
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
        nlp_circuit_breaker_state.set(0)  # 0 = closed
        
        # Configuración de modelos
        self.model_directory = model_directory or self._resolve_model_directory()
        self.agents = {}  # Un agente por idioma
        self.model_versions = {}
        self.models_loaded_at = {}
        self.default_language = SupportedLanguage.SPANISH
        
        # Servicios complementarios (se inicializan bajo demanda)
        self.redis = None
        self.conversation_context = None
        self.multilingual_service = None
        
        # Caché de inferencia (respuestas recientes)
        self.cache_enabled = True
        self.cache_ttl = 3600  # 1 hora
        
        # Cargar modelos de forma asíncrona en startup
        self._initialize_called = False
        
    async def initialize(self):
        """Inicializar servicios y modelos de forma asíncrona."""
        if self._initialize_called:
            return
            
        self._initialize_called = True
        
        # Inicializar Redis
        self.redis = await get_redis()
        
        # Inicializar servicios complementarios
        self.conversation_context = await get_conversation_context_service()
        self.multilingual_service = await get_multilingual_nlp_service()
        
        # Cargar modelos para cada idioma soportado
        languages = SupportedLanguage.get_all()
        
        # Cargar modelos en paralelo
        load_tasks = []
        for lang in languages:
            load_tasks.append(self._load_model_for_language(lang))
            
        # Esperar a que todos los modelos se carguen
        await asyncio.gather(*load_tasks)
        
        logger.info(
            f"Enhanced NLP Engine initialized successfully with {len(self.agents)} language models",
            extra={"supported_languages": list(self.agents.keys())}
        )
    
    def _resolve_model_directory(self) -> str:
        """
        Resolver directorio de modelos desde variable de entorno o ubicación por defecto.
        
        Returns:
            Ruta al directorio de modelos
        """
        # Verificar variable de entorno
        env_path = os.getenv("RASA_MODELS_DIR")
        if env_path and Path(env_path).exists():
            logger.info(f"Using Rasa models from RASA_MODELS_DIR: {env_path}")
            return env_path
        
        # Verificar ubicación por defecto
        project_root = Path(__file__).parent.parent.parent
        default_path = project_root / "rasa_nlu" / "models"
        
        if default_path.exists():
            logger.info(f"Using Rasa models from default location: {default_path}")
            return str(default_path)
        
        # Crear directorio si no existe
        default_path.mkdir(parents=True, exist_ok=True)
        return str(default_path)
        
    async def _load_model_for_language(self, language_code: str):
        """
        Cargar modelo Rasa para un idioma específico.
        
        Args:
            language_code: Código de idioma (es, en, pt)
        """
        try:
            from rasa.core.agent import Agent
            
            # Construir path al modelo según convención: hotel_nlu_{lang}_latest.tar.gz
            model_filename = f"hotel_nlu_{language_code}_latest.tar.gz"
            model_path = Path(self.model_directory) / model_filename
            
            if not model_path.exists():
                # Verificar si hay un modelo específico por fecha
                pattern = f"hotel_nlu_{language_code}_*.tar.gz"
                candidates = list(Path(self.model_directory).glob(pattern))
                
                if candidates:
                    # Usar el más reciente
                    model_path = sorted(candidates)[-1]
                else:
                    # Si no hay modelo para este idioma, usar modelo por defecto (español)
                    if language_code != self.default_language:
                        logger.warning(
                            f"No model found for language {language_code}, will use default language instead"
                        )
                        return
                    else:
                        # Si no hay modelo para el idioma por defecto, error crítico
                        logger.error(f"No model found for default language {language_code}")
                        return
            
            logger.info(f"Loading Rasa model for language {language_code} from: {model_path}")
            
            # Ejecutar carga del modelo en thread pool para no bloquear
            loop = asyncio.get_event_loop()
            agent = await loop.run_in_executor(
                None,
                lambda: Agent.load(str(model_path))
            )
            
            self.agents[language_code] = agent
            
            # Extraer versión del modelo del nombre de archivo
            # Ejemplo: hotel_nlu_es_20240115_143022.tar.gz → 20240115_143022
            model_filename = model_path.stem
            if "_" in model_filename:
                self.model_versions[language_code] = "_".join(model_filename.split("_")[-2:])
            else:
                self.model_versions[language_code] = "unknown"
                
            self.models_loaded_at[language_code] = datetime.utcnow()
            
            logger.info(
                f"Rasa model for language {language_code} loaded successfully",
                extra={
                    "language": language_code,
                    "model_version": self.model_versions[language_code],
                    "model_path": str(model_path),
                    "loaded_at": self.models_loaded_at[language_code].isoformat()
                }
            )
            
        except ImportError:
            logger.error(
                "Rasa not installed. Install with: pip install rasa"
            )
        except Exception as e:
            logger.error(
                f"Failed to load Rasa model for language {language_code}: {e}",
                exc_info=True,
                extra={"language": language_code}
            )
    
    async def process_message(self, text: str, user_id: str = None, 
                             channel: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """
        Procesar mensaje con detección de idioma y contexto conversacional.
        
        Args:
            text: Mensaje del usuario
            user_id: ID del usuario (para contexto)
            channel: Canal de comunicación (whatsapp, gmail)
            tenant_id: ID del tenant (opcional)
        
        Returns:
            Diccionario con estructura:
            {
                "intent": {"name": str, "confidence": float},
                "entities": [{"entity": str, "value": str, "start": int, "end": int}],
                "language": str,
                "text": str,
                "model_version": str,
                "context_used": bool,
                "resolutions": dict (solo si se usó contexto)
            }
        """
        if not self._initialize_called:
            await self.initialize()
            
        # Verificar caché si está habilitado
        if self.cache_enabled and self.redis:
            cache_key = f"nlp:cache:{hash(text)}"
            cached = await self.redis.get(cache_key)
            if cached:
                try:
                    result = json.loads(cached)
                    nlp_operations.labels(operation="process_message", status="cache_hit").inc()
                    return result
                except json.JSONDecodeError:
                    pass
        
        try:
            # Ejecutar proceso NLP con circuit breaker
            result = await self.circuit_breaker.call(
                self._process_with_context, text, user_id, channel, tenant_id
            )
            nlp_operations.labels(operation="process_message", status="success").inc()
            
            # Registrar métricas
            confidence = result.get("intent", {}).get("confidence", 0.0)
            nlp_confidence.observe(confidence)
            
            # Métricas de predicción de intents (por nivel de confianza)
            intent_name = result.get("intent", {}).get("name", "unknown")
            language = result.get("language", self.default_language.value)
            confidence_bucket = self._get_confidence_bucket(confidence)
            nlp_intent_predictions.labels(
                intent=intent_name, 
                confidence_bucket=confidence_bucket,
                language=language
            ).inc()
            
            # Métricas de entidades extraídas
            for entity in result.get("entities", []):
                nlp_entity_extractions.labels(
                    entity_type=entity.get("entity", "unknown"),
                    extractor=entity.get("extractor", "unknown")
                ).inc()
                
            # Guardar en caché si está habilitado
            if self.cache_enabled and self.redis:
                # Solo cachear si la confianza es alta
                if confidence >= 0.85:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(result)
                    )
            
            return result
            
        except CircuitBreakerOpenError:
            # Circuit breaker abierto: usar fallback
            logger.warning("NLP circuit breaker open, using fallback response")
            nlp_circuit_breaker_calls.labels(state="open", result="fallback").inc()
            nlp_circuit_breaker_state.set(1)  # 1 = open
            return self._fallback_response()
            
        except Exception as e:
            # Otros errores
            logger.error(f"NLP processing failed: {e}", exc_info=True)
            nlp_operations.labels(operation="process_message", status="error").inc()
            nlp_errors.labels(operation="process_message", error_type=type(e).__name__).inc()
            return self._fallback_response()
    
    async def _process_with_context(self, text: str, user_id: str = None, 
                                   channel: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """
        Procesamiento interno con soporte de contexto e idioma.
        
        Args:
            text: Mensaje del usuario
            user_id: ID del usuario (para contexto)
            channel: Canal de comunicación
            tenant_id: ID del tenant (opcional)
            
        Returns:
            Resultado procesado con información adicional
        """
        start_time = asyncio.get_event_loop().time()
        
        # 1. Detección de idioma
        language_result = await self.multilingual_service.process_with_language_detection(text)
        language_code = language_result["language_code"]
        
        # 2. Procesamiento de contexto conversacional (si hay ID de usuario y canal)
        context_used = False
        resolved_text = text
        resolutions = {}
        
        if user_id and channel:
            # Resolver referencias anafóricas
            anaphora_result = await self.conversation_context.resolve_anaphora(
                text, user_id, channel, tenant_id
            )
            
            if anaphora_result["resolutions"]:
                resolved_text = anaphora_result["resolved_text"]
                resolutions = anaphora_result["resolutions"]
                context_used = True
                nlp_context_usage.labels(context_type="anaphora", result="applied").inc()
                
        # 3. Procesar con el modelo del idioma detectado
        agent = self.agents.get(language_code)
        
        # Si no hay modelo para el idioma detectado, usar el de español
        if not agent:
            logger.warning(f"No NLP model for language {language_code}, using default")
            language_code = self.default_language.value
            agent = self.agents.get(language_code)
            
        if not agent:
            logger.error("No NLP agents loaded, using fallback")
            result = self._fallback_response()
            result["language"] = language_code
            return result
            
        try:
            # Ejecutar inferencia en modelo Rasa
            model_result = await agent.parse_message(message_data=resolved_text)
            
            # Medir latencia de inferencia
            inference_latency = asyncio.get_event_loop().time() - start_time
            nlp_inference_latency.labels(
                model_type="rasa", 
                language=language_code
            ).observe(inference_latency)
            
            # Normalizar resultado
            normalized = {
                "intent": {
                    "name": model_result.get("intent", {}).get("name", "unknown"),
                    "confidence": model_result.get("intent", {}).get("confidence", 0.0)
                },
                "entities": self._normalize_entities(model_result.get("entities", [])),
                "language": language_code,
                "text": text,
                "model_version": self.model_versions.get(language_code, "unknown"),
                "context_used": context_used,
            }
            
            # Añadir información sobre resoluciones anafóricas si se usaron
            if context_used:
                normalized["resolutions"] = resolutions
            
            # Si hay contexto, almacenar resultado para futuras referencias
            if user_id and channel:
                await self.conversation_context.store_context(
                    user_id, 
                    channel, 
                    normalized["intent"]["name"],
                    normalized["entities"],
                    text,
                    tenant_id
                )
                
            return normalized
            
        except Exception as e:
            logger.error(f"Rasa parsing failed: {e}", exc_info=True)
            raise
    
    def _normalize_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalizar entidades de Rasa a formato consistente.
        
        Args:
            entities: Entidades crudas de Rasa
            
        Returns:
            Lista de entidades normalizada
        """
        normalized = []
        
        for entity in entities:
            normalized.append({
                "entity": entity.get("entity"),
                "value": entity.get("value"),
                "start": entity.get("start"),
                "end": entity.get("end"),
                "confidence": entity.get("confidence_entity", entity.get("confidence", 1.0)),
                "extractor": entity.get("extractor", "unknown"),
                # Agregar metadatos adicionales si existen
                "additional_info": entity.get("additional_info", {})
            })
        
        return normalized
    
    def _fallback_response(self) -> Dict[str, Any]:
        """
        Respuesta de fallback cuando NLP no está disponible.
        
        Returns:
            Respuesta con intent desconocido y flag de fallback
        """
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": [],
            "fallback": True,
            "language": self.default_language.value,
            "text": "",
            "model_version": "fallback"
        }
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """
        Mapear score de confianza a bucket para métricas.
        
        Args:
            confidence: Score de confianza (0.0-1.0)
            
        Returns:
            Etiqueta de bucket: "very_low", "low", "medium", "high", "very_high"
        """
        if confidence < 0.3:
            return "very_low"
        elif confidence < 0.5:
            return "low"
        elif confidence < 0.7:
            return "medium"
        elif confidence < 0.85:
            return "high"
        else:
            return "very_high"
    
    async def handle_low_confidence(self, intent: Dict[str, Any], 
                                  language_code: str = None) -> Optional[Dict[str, Any]]:
        """
        Manejar predicciones de intent con baja confianza usando clarificación.
        
        Args:
            intent: Diccionario de intent con name y confidence
            language_code: Código de idioma para respuesta localizada
            
        Returns:
            Diccionario con respuesta y flag de handoff humano, o None si la confianza es aceptable
        """
        confidence = intent.get("confidence", 0.0)
        language = language_code or self.default_language.value
        
        # Confianza muy baja (<0.3): escalar a humano
        if confidence < 0.3:
            if language == "en":
                response = (
                    "I'm sorry, I'm not sure I understand your query. "
                    "Would you like to rephrase it or should I connect you with a representative?"
                )
            elif language == "pt":
                response = (
                    "Desculpe, não tenho certeza se entendi sua consulta. "
                    "Você poderia reformulá-la ou prefere que eu te conecte com um representante?"
                )
            else:  # default: es
                response = (
                    "Disculpa, no estoy seguro de entender tu consulta. "
                    "¿Podrías reformularla o te conecto con un representante?"
                )
                
            return {
                "response": response,
                "requires_human": True,
            }
        
        # Confianza baja (0.3-0.7): ofrecer menú
        if confidence < 0.7:
            if language == "en":
                response = (
                    "How can I help you?\n"
                    "1️⃣ Check availability\n"
                    "2️⃣ Make a reservation\n"
                    "3️⃣ Modify/cancel reservation\n"
                    "4️⃣ Hotel information (prices, services, location)\n"
                    "5️⃣ Talk to reception"
                )
            elif language == "pt":
                response = (
                    "Como posso ajudá-lo?\n"
                    "1️⃣ Verificar disponibilidade\n"
                    "2️⃣ Fazer uma reserva\n"
                    "3️⃣ Modificar/cancelar reserva\n"
                    "4️⃣ Informações do hotel (preços, serviços, localização)\n"
                    "5️⃣ Falar com a recepção"
                )
            else:  # default: es
                response = (
                    "¿En qué puedo ayudarte?\n"
                    "1️⃣ Consultar disponibilidad\n"
                    "2️⃣ Hacer una reserva\n"
                    "3️⃣ Modificar/cancelar reserva\n"
                    "4️⃣ Información del hotel (precios, servicios, ubicación)\n"
                    "5️⃣ Hablar con recepción"
                )
                
            return {
                "response": response,
                "requires_human": False,
            }
        
        # Confianza aceptable (≥0.7): proceder normalmente
        return None
    
    async def get_models_info(self) -> Dict[str, Any]:
        """
        Obtener información sobre los modelos cargados.
        
        Returns:
            Diccionario con metadatos de modelos
        """
        if not self._initialize_called:
            await self.initialize()
            
        info = {
            "models": {},
            "default_language": self.default_language.value,
            "supported_languages": list(self.agents.keys()),
            "cache_enabled": self.cache_enabled
        }
        
        for lang, agent in self.agents.items():
            info["models"][lang] = {
                "model_version": self.model_versions.get(lang, "unknown"),
                "model_loaded_at": self.models_loaded_at.get(lang, datetime.utcnow()).isoformat(),
                "agent_loaded": agent is not None
            }
            
        return info
        
    async def reload_models(self):
        """Recargar todos los modelos."""
        # Reinicializar agentes
        self.agents = {}
        self.model_versions = {}
        self.models_loaded_at = {}
        
        # Cargar modelos para cada idioma soportado
        languages = SupportedLanguage.get_all()
        
        # Cargar modelos en paralelo
        load_tasks = []
        for lang in languages:
            load_tasks.append(self._load_model_for_language(lang))
            
        # Esperar a que todos los modelos se carguen
        await asyncio.gather(*load_tasks)
        
        logger.info(
            f"Enhanced NLP Engine reloaded successfully with {len(self.agents)} language models",
            extra={"supported_languages": list(self.agents.keys())}
        )
        
        return {
            "status": "success",
            "models_loaded": list(self.agents.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }


# Instancia global del servicio
enhanced_nlp_engine = EnhancedNLPEngine()

async def get_enhanced_nlp_engine() -> EnhancedNLPEngine:
    """Getter para el servicio de NLP mejorado."""
    if not enhanced_nlp_engine._initialize_called:
        await enhanced_nlp_engine.initialize()
    return enhanced_nlp_engine