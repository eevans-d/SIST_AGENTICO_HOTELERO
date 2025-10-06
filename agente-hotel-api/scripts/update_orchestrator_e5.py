"""
Script de actualización del orquestrador para utilizar el NLP Engine mejorado.
Parte de la Fase E.5 NLP Enhancement.

Este script modifica el orquestador para:
1. Utilizar el nuevo EnhancedNLPEngine en lugar del NLPEngine original
2. Incorporar soporte multilingüe
3. Integrar procesamiento de contexto conversacional
4. Añadir métricas específicas para el NLP mejorado
"""

import shutil
import os
from pathlib import Path
import importlib.util

# Paths relativos al directorio del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
SERVICES_DIR = PROJECT_ROOT / "app" / "services"
ORCHESTRATOR_PATH = SERVICES_DIR / "orchestrator.py"
ORCHESTRATOR_BACKUP = ORCHESTRATOR_PATH.with_suffix(".py.bak")

print(f"Actualizando orquestrador en {ORCHESTRATOR_PATH}...")

# Crear backup del orquestrador original
if not ORCHESTRATOR_BACKUP.exists():
    shutil.copy(ORCHESTRATOR_PATH, ORCHESTRATOR_BACKUP)
    print(f"Backup creado en {ORCHESTRATOR_BACKUP}")

# Comprobar que existen los nuevos archivos
ENHANCED_NLP_PATH = SERVICES_DIR / "enhanced_nlp_engine.py"
CONTEXT_PATH = SERVICES_DIR / "conversation_context.py"
MULTILINGUAL_PATH = SERVICES_DIR / "multilingual_service.py"

missing_files = []
for path in [ENHANCED_NLP_PATH, CONTEXT_PATH, MULTILINGUAL_PATH]:
    if not path.exists():
        missing_files.append(path)

if missing_files:
    print("Error: Faltan archivos necesarios:")
    for path in missing_files:
        print(f"  - {path}")
    exit(1)

# Cargar módulo del orquestrador para analizar
spec = importlib.util.spec_from_file_location("orchestrator", ORCHESTRATOR_PATH)
orchestrator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orchestrator)

# Contenido de la actualización del orquestrador
updated_orchestrator = """# [PROMPT E.5] app/services/orchestrator.py (Enhanced)

import time
from prometheus_client import Histogram, Counter
from .message_gateway import MessageGateway
from .enhanced_nlp_engine import get_enhanced_nlp_engine  # Nuevo import
from .conversation_context import get_conversation_context_service  # Nuevo import
from .multilingual_service import get_multilingual_nlp_service  # Nuevo import
from .audio_processor import AudioProcessor
from .session_manager import SessionManager
from .lock_service import LockService
from .template_service import TemplateService
from ..models.unified_message import UnifiedMessage
from .feature_flag_service import get_feature_flag_service
from .metrics_service import metrics_service
from .business_metrics import (
    intents_detected,
    nlp_fallbacks,
    messages_by_channel,
    context_usage_total  # Nueva métrica
)
from ..exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError
from ..core.logging import logger


class Orchestrator:
    def __init__(self, pms_adapter, session_manager: SessionManager, lock_service: LockService):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()
        # El motor NLP se inicializa bajo demanda en handle_unified_message
        # para permitir inicialización asíncrona
        self.nlp_engine = None
        # Lo mismo para servicio de contexto y multilingüe
        self.conversation_context = None
        self.multilingual_service = None

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)
        language_code = "es"  # Default, será actualizado según detección
        
        # Inicializar servicios bajo demanda si es necesario
        if not self.nlp_engine:
            self.nlp_engine = await get_enhanced_nlp_engine()
        if not self.conversation_context:
            self.conversation_context = await get_conversation_context_service()
        if not self.multilingual_service:
            self.multilingual_service = await get_multilingual_nlp_service()
        
        # Métrica de negocio: contar mensaje por canal
        messages_by_channel.labels(channel=message.canal).inc()
        
        if message.tipo == "audio":
            if not message.media_url:
                raise ValueError("Missing media_url for audio message")
            stt_result = await self.audio_processor.transcribe_whatsapp_audio(message.media_url)
            message.texto = stt_result["text"]
            message.metadata["confidence_stt"] = stt_result["confidence"]

        try:
            text = message.texto or ""
            
            # Obtener feature flags
            ff_service = await get_feature_flag_service()
            context_enabled = await ff_service.is_enabled("nlp.context.enabled", default=True)
            
            # Procesamiento con contexto si está habilitado
            if context_enabled and message.user_id and message.canal:
                # Resolver referencias anafóricas basadas en conversación previa
                anaphora_result = await self.conversation_context.resolve_anaphora(
                    text, message.user_id, message.canal, tenant_id
                )
                
                # Si se encontraron resoluciones, usar el texto procesado
                if anaphora_result["resolutions"]:
                    context_usage_total.inc()  # Nueva métrica de contexto
                    logger.info(
                        f"Applied context resolutions: {anaphora_result['resolutions']}",
                        extra={"user_id": message.user_id, "resolutions": anaphora_result['resolutions']}
                    )
                    resolved_text = anaphora_result["resolved_text"]
                else:
                    resolved_text = text
                    
                # Registrar en metadata para análisis
                message.metadata["context_used"] = bool(anaphora_result["resolutions"])
                message.metadata["resolved_text"] = resolved_text
                
                # Usar texto resuelto para procesamiento NLP
                text_for_nlp = resolved_text
            else:
                text_for_nlp = text
            
            # Graceful degradation: Si NLP falla, usar reglas básicas
            try:
                # Procesar con NLP mejorado (incluye detección de idioma y contexto)
                nlp_result = await self.nlp_engine.process_message(
                    text_for_nlp, 
                    message.user_id, 
                    message.canal, 
                    tenant_id
                )
                
                # Obtener información clave del resultado
                intent_name = nlp_result.get("intent", {}).get("name", "unknown") or "unknown"
                language_code = nlp_result.get("language", "es")
                
            except Exception as nlp_error:
                logger.warning(f"NLP failed, using rule-based fallback: {nlp_error}")
                metrics_service.record_nlp_fallback("nlp_service_failure")
                nlp_fallbacks.inc()
                
                # Reglas básicas de fallback
                text_lower = text.lower()
                if any(word in text_lower for word in ["disponibilidad", "disponible", "habitacion", "cuarto", "availability", "available"]):
                    intent_name = "check_availability"
                    nlp_result = {"intent": {"name": "check_availability", "confidence": 0.5}, "entities": [], "language": language_code}
                elif any(word in text_lower for word in ["reservar", "reserva", "reservacion", "booking", "reserve", "book"]):
                    intent_name = "make_reservation"
                    nlp_result = {"intent": {"name": "make_reservation", "confidence": 0.5}, "entities": [], "language": language_code}
                elif any(word in text_lower for word in ["precio", "costo", "tarifa", "valor", "price", "cost", "rate"]):
                    intent_name = "ask_price"
                    nlp_result = {"intent": {"name": "ask_price", "confidence": 0.5}, "entities": [], "language": language_code}
                else:
                    intent_name = "unknown"
                    nlp_result = {"intent": {"name": "unknown", "confidence": 0.0}, "entities": [], "language": language_code}
                    
                    # Generar respuesta localizada según idioma detectado
                    if language_code == "en":
                        response = "Sorry, I'm having technical issues. Can you tell me if you want to: check availability, make a reservation, or get pricing information?"
                    elif language_code == "pt":
                        response = "Desculpe, estou tendo problemas técnicos. Você pode me dizer se deseja: verificar disponibilidade, fazer uma reserva ou obter informações sobre preços?"
                    else:  # default to Spanish
                        response = "Disculpa, estoy teniendo problemas técnicos. ¿Puedes decirme si quieres: consultar disponibilidad, hacer una reserva, o información de precios?"
                    
                    return {"response": response}
            
            # Métrica de negocio: registrar intent detectado
            intent_obj = nlp_result.get("intent", {})
            confidence = intent_obj.get("confidence", 0.0)
            confidence_level = "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low"
            intents_detected.labels(intent=intent_name, confidence_level=confidence_level).inc()
            
            # Obtener o crear sesión de usuario
            session = await self.session_manager.get_or_create_session(message.user_id, message.canal, tenant_id)
            
            # Fallback dinámico según confianza + feature flag
            enhanced_fallback = await ff_service.is_enabled("nlp.fallback.enhanced", default=True)
            
            # Registrar categoría de confianza
            metrics_service.record_nlp_confidence(confidence)
            
            # Manejo mejorado de baja confianza (más contextual)
            if enhanced_fallback:
                # Usar manejo de confianza del NLP mejorado
                low_confidence_response = await self.nlp_engine.handle_low_confidence(
                    intent_obj,
                    language_code
                )
                
                if low_confidence_response:
                    # Si requiere handoff humano, marcar en metadata
                    if low_confidence_response.get("requires_human", False):
                        message.metadata["requires_human"] = True
                        message.metadata["confidence_too_low"] = True
                        metrics_service.record_nlp_fallback("very_low_confidence")
                        nlp_fallbacks.inc()
                    else:
                        metrics_service.record_nlp_fallback("low_confidence_hint")
                        
                    return {"response": low_confidence_response["response"]}
            
            # Graceful degradation: Manejar fallos de PMS
            try:
                # Incluir idioma detectado para respuestas localizadas
                response_text = await self.handle_intent(nlp_result, session, message, language_code)
            except (PMSError, CircuitBreakerOpenError) as pms_error:
                logger.error(f"PMS unavailable, degraded response: {pms_error}")
                orchestrator_degraded_responses.inc()
                
                # Respuestas degradadas según idioma
                if language_code == "en":
                    if intent_name == "check_availability":
                        response_text = "I'm sorry, our availability system is temporarily unavailable. Please contact reception directly at [PHONE] or write to [EMAIL]."
                    elif intent_name == "make_reservation":
                        response_text = "I cannot process reservations at the moment due to system maintenance. Please contact reception at [PHONE] or try again later."
                    else:
                        response_text = "I apologize, I'm experiencing technical difficulties. Could you please contact reception directly? Phone: [PHONE]"
                elif language_code == "pt":
                    if intent_name == "check_availability":
                        response_text = "Desculpe, nosso sistema de disponibilidade está temporariamente indisponível. Entre em contato diretamente com a recepção pelo [TELEFONE] ou escreva para [EMAIL]."
                    elif intent_name == "make_reservation":
                        response_text = "Não posso processar reservas no momento devido à manutenção do sistema. Entre em contato com a recepção pelo [TELEFONE] ou tente novamente mais tarde."
                    else:
                        response_text = "Desculpe, estou enfrentando dificuldades técnicas. Poderia entrar em contato diretamente com a recepção? Telefone: [TELEFONE]"
                else:  # default to Spanish
                    if intent_name == "check_availability":
                        response_text = "Lo siento, nuestro sistema de disponibilidad está temporalmente fuera de servicio. Por favor, contacta directamente con recepción al [TELÉFONO] o escribe a [EMAIL]."
                    elif intent_name == "make_reservation":
                        response_text = "No puedo procesar reservas en este momento por mantenimiento del sistema. Por favor, contacta con recepción al [TELÉFONO] o intenta más tarde."
                    else:
                        response_text = "Disculpa, estoy experimentando dificultades técnicas. ¿Puedes contactar directamente con recepción? Teléfono: [TELÉFONO]"
            
            return {"response": response_text}
        except Exception as e:
            status = "error"
            orchestrator_errors_total.labels(intent=intent_name, error_type=type(e).__name__).inc()
            if tenant_id:
                try:
                    metrics_service.inc_tenant_request(tenant_id, error=True)
                except Exception:  # pragma: no cover
                    pass
            raise
        finally:
            duration = time.time() - start
            orchestrator_latency.labels(intent=intent_name, status=status).observe(duration)
            orchestrator_messages_total.labels(intent=intent_name, status=status).inc()
            if tenant_id:
                try:
                    metrics_service.inc_tenant_request(tenant_id, error=(status != "ok"))
                except Exception:  # pragma: no cover
                    pass

    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage, 
                          language_code: str = "es") -> str:
        """
        Procesar intent con soporte multilingüe.
        
        Args:
            nlp_result: Resultado del procesamiento NLP
            session: Sesión del usuario
            message: Mensaje unificado
            language_code: Código de idioma para respuestas localizadas
            
        Returns:
            Texto de respuesta localizado
        """
        intent = nlp_result.get("intent", {}).get("name")
        entities = nlp_result.get("entities", [])

        # Template multilingüe según el intent
        if intent == "check_availability":
            # Extraer entidades y llamar a pms_adapter.check_availability
            # ...
            
            # Usar plantilla localizada según idioma
            if language_code == "en":
                return self.template_service.get_response(
                    "availability_found_en",
                    checkin="today",
                    checkout="tomorrow",
                    room_type="Double",
                    guests=2,
                    price=10000,
                    total=20000,
                )
            elif language_code == "pt":
                return self.template_service.get_response(
                    "availability_found_pt",
                    checkin="hoje",
                    checkout="amanhã",
                    room_type="Duplo",
                    guests=2,
                    price=10000,
                    total=20000,
                )
            else:  # default: es
                return self.template_service.get_response(
                    "availability_found",
                    checkin="hoy",
                    checkout="mañana",
                    room_type="Doble",
                    guests=2,
                    price=10000,
                    total=20000,
                )

        elif intent == "make_reservation":
            # Lógica para validar datos, llamar a lock_service.acquire_lock
            # ...
            
            # Usar plantilla localizada según idioma
            if language_code == "en":
                return self.template_service.get_response(
                    "reservation_instructions_en", 
                    deposit=6000, 
                    bank_info="CBU 12345..."
                )
            elif language_code == "pt":
                return self.template_service.get_response(
                    "reservation_instructions_pt", 
                    deposit=6000, 
                    bank_info="CBU 12345..."
                )
            else:  # default: es
                return self.template_service.get_response(
                    "reservation_instructions", 
                    deposit=6000, 
                    bank_info="CBU 12345..."
                )
        else:
            # Fallback localizado según idioma
            if language_code == "en":
                return "I didn't understand your query. Could you rephrase it?"
            elif language_code == "pt":
                return "Não entendi sua consulta. Você poderia reformulá-la?"
            else:  # default: es
                return "No entendí tu consulta. ¿Podrías reformularla?"


# Prometheus metrics (module-level)
orchestrator_latency = Histogram(
    "orchestrator_latency_seconds",
    "Tiempo para procesar un mensaje unificado por intent y estado",
    ["intent", "status"],
)
orchestrator_messages_total = Counter(
    "orchestrator_messages_total", "Mensajes procesados por intent y estado", ["intent", "status"]
)
orchestrator_errors_total = Counter(
    "orchestrator_errors_total", "Errores no controlados por intent y tipo", ["intent", "error_type"]
)
orchestrator_degraded_responses = Counter(
    "orchestrator_degraded_responses_total", "Respuestas degradadas por fallo de servicios externos"
)
"""

# Escribir el nuevo contenido al archivo
with open(ORCHESTRATOR_PATH, 'w') as f:
    f.write(updated_orchestrator)

print("Orquestador actualizado con éxito.")

# Actualizar métricas de negocio
BUSINESS_METRICS_PATH = SERVICES_DIR / "business_metrics.py"
if BUSINESS_METRICS_PATH.exists():
    with open(BUSINESS_METRICS_PATH, 'r') as f:
        current_metrics = f.read()
    
    # Verificar si la métrica ya existe
    if "context_usage_total" not in current_metrics:
        # Añadir nueva métrica
        with open(BUSINESS_METRICS_PATH, 'a') as f:
            f.write("""
# [PROMPT E.5] Métricas de contexto conversacional
context_usage_total = Counter(
    "business_context_usage_total", 
    "Total de usos de contexto conversacional en interacciones"
)
""")
        print("Métricas de negocio actualizadas.")
    else:
        print("Métricas de contexto ya existían.")

print("\n¡Actualización completada con éxito!")
print("""
Los siguientes archivos han sido creados/modificados:
1. app/services/enhanced_nlp_engine.py (NUEVO)
2. app/services/conversation_context.py (NUEVO)
3. app/services/multilingual_service.py (NUEVO)
4. app/services/orchestrator.py (MODIFICADO)
5. app/services/business_metrics.py (ACTUALIZADO)

Para aplicar estos cambios:
1. Reinicia el servicio agente-api
2. Verifica los logs para confirmar la carga correcta
3. Prueba el procesamiento multilingüe y contextual
""")