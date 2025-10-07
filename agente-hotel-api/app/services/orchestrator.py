# [PROMPT 2.7] app/services/orchestrator.py

import time
from prometheus_client import Histogram, Counter
from .message_gateway import MessageGateway
from .nlp_engine import NLPEngine
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
    messages_by_channel
)
from ..exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError
from ..core.logging import logger


class Orchestrator:
    def __init__(self, pms_adapter, session_manager: SessionManager, lock_service: LockService):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.nlp_engine = NLPEngine()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)
        
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
            
            # Graceful degradation: Si NLP falla, usar reglas básicas
            try:
                # Detect language from the message if not specified
                detected_language = await self.nlp_engine.detect_language(text)
                
                # Process message with detected/specified language
                nlp_result = await self.nlp_engine.process_message(text, language=detected_language)
                intent_name = nlp_result.get("intent", {}).get("name", "unknown") or "unknown"
                
                # Store language info in session for continuity
                message.metadata["detected_language"] = detected_language
                
            except Exception as nlp_error:
                logger.warning(f"NLP failed, using rule-based fallback: {nlp_error}")
                metrics_service.record_nlp_fallback("nlp_service_failure")
                nlp_fallbacks.inc()
                
                # Language detection fallback for rule-based matching
                detected_language = await self.nlp_engine.detect_language(text)
                message.metadata["detected_language"] = detected_language
                
                # Reglas básicas de fallback (multilingual)
                text_lower = text.lower()
                if any(word in text_lower for word in [
                    "disponibilidad", "disponible", "habitacion", "cuarto",  # Spanish
                    "availability", "available", "room", "rooms",             # English
                    "disponibilidade", "quarto", "quartos"                    # Portuguese
                ]):
                    intent_name = "check_availability"
                    nlp_result = {"intent": {"name": "check_availability", "confidence": 0.5}, "entities": [], "language": detected_language}
                elif any(word in text_lower for word in [
                    "reservar", "reserva", "reservacion",     # Spanish
                    "book", "booking", "reserve", "reservation",  # English
                    "reservar", "reserva"                     # Portuguese
                ]):
                    intent_name = "make_reservation"
                    nlp_result = {"intent": {"name": "make_reservation", "confidence": 0.5}, "entities": [], "language": detected_language}
                elif any(word in text_lower for word in [
                    "precio", "costo", "tarifa", "valor",     # Spanish
                    "price", "cost", "rate", "pricing",      # English
                    "preço", "custo", "tarifa"               # Portuguese
                ]):
                    intent_name = "pricing_info"
                    nlp_result = {"intent": {"name": "pricing_info", "confidence": 0.5}, "entities": [], "language": detected_language}
                elif any(word in text_lower for word in [
                    "ubicacion", "ubicación", "dirección", "direccion", "llegar", "mapa",   # Spanish
                    "location", "address", "map", "directions", "where",                    # English
                    "localização", "endereço", "mapa", "direções"                          # Portuguese
                ]):
                    intent_name = "hotel_location"
                    nlp_result = {"intent": {"name": "hotel_location", "confidence": 0.5}, "entities": [], "language": detected_language}
                else:
                    intent_name = "unknown"
                    nlp_result = {"intent": {"name": "unknown", "confidence": 0.0}, "entities": [], "language": detected_language}
                    
                    # Return multilingual error message
                    return {
                        "response": self._get_technical_error_message(detected_language)
                    }
            
            # Métrica de negocio: registrar intent detectado
            intent_obj = nlp_result.get("intent", {})
            confidence = intent_obj.get("confidence", 0.0)
            confidence_level = "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low"
            intents_detected.labels(intent=intent_name, confidence_level=confidence_level).inc()
            
            session = await self.session_manager.get_or_create_session(message.user_id, message.canal, tenant_id)
            # Fallback dinámico según confianza + feature flag
            ff_service = await get_feature_flag_service()
            enhanced_fallback = await ff_service.is_enabled("nlp.fallback.enhanced", default=True)
            # Registrar categoría de confianza
            metrics_service.record_nlp_confidence(confidence)
            
            # Get language from NLP result or message metadata
            response_language = nlp_result.get("language", message.metadata.get("detected_language", "es"))
            
            if enhanced_fallback and confidence < 0.45:
                # Respuesta de bajo nivel de confianza agresiva
                metrics_service.record_nlp_fallback("very_low_confidence")
                nlp_fallbacks.inc()  # Métrica de negocio: fallback detectado
                return {
                    "response": self._get_low_confidence_message(response_language)
                }
            elif enhanced_fallback and confidence < 0.75:
                message.metadata["low_confidence"] = True
                metrics_service.record_nlp_fallback("low_confidence_hint")
            
            # Graceful degradation: Manejar fallos de PMS
            try:
                response_data = await self.handle_intent(nlp_result, session, message)
                response_type = response_data.get("response_type", "text")
                
                if response_type == "text":
                    # Respuesta de texto simple, compatible con el formato anterior
                    return {"response": response_data.get("content", "")}
                    
                elif response_type == "audio":
                    # Respuesta de audio (texto + audio)
                    return {
                        "response_type": "audio",
                        "content": {
                            "text": response_data.get("content", ""),
                            "audio_data": response_data.get("audio_data")
                        },
                        "original_message": message
                    }
                    
                elif response_type == "interactive_buttons":
                    # Respuesta con botones interactivos
                    return {
                        "response_type": "interactive_buttons",
                        "content": response_data.get("content", {}),
                        "original_message": message
                    }
                    
                elif response_type == "interactive_list":
                    # Respuesta con lista interactiva
                    return {
                        "response_type": "interactive_list",
                        "content": response_data.get("content", {}),
                        "original_message": message
                    }
                    
                elif response_type == "location":
                    # Respuesta con ubicación
                    return {
                        "response_type": "location",
                        "content": response_data.get("content", {}),
                        "original_message": message
                    }
                    
                elif response_type == "audio_with_location":
                    # Respuesta combinada de audio + ubicación
                    # El router deberá manejar esto enviando primero el audio y luego la ubicación
                    content = response_data.get("content", {})
                    return {
                        "response_type": "audio_with_location",
                        "content": {
                            "text": content.get("text", ""),
                            "audio_data": content.get("audio_data"),
                            "location": content.get("location", {})
                        },
                        "original_message": message
                    }
                    
                elif response_type == "reaction":
                    # Respuesta con reacción a un mensaje
                    return {
                        "response_type": "reaction",
                        "content": response_data.get("content", {}),
                        "original_message": message
                    }
                    
                else:
                    # Tipo de respuesta desconocido, usar texto por defecto
                    logger.warning(f"Unknown response_type: {response_type}, defaulting to text")
                    return {"response": "Lo siento, no puedo procesar tu solicitud en este momento."}
                    
            except (PMSError, CircuitBreakerOpenError) as pms_error:
                logger.error(f"PMS unavailable, degraded response: {pms_error}")
                orchestrator_degraded_responses.inc()
                
                # Respuesta degradada según el intent
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

    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Procesa un intent detectado y genera la respuesta apropiada.
        
        Args:
            nlp_result: Resultado del procesamiento NLP con intent y entidades
            session: Sesión del usuario
            message: Mensaje unificado original
            
        Returns:
            Diccionario con tipo de respuesta y contenido:
            {
                "response_type": "text|audio|interactive|location|reaction",
                "content": { ... contenido específico del tipo ... }
            }
        """
        intent = nlp_result.get("intent", {}).get("name")
        language = nlp_result.get("language", "es")
        tenant_id = getattr(message, "tenant_id", None)
        
        # Verificar si el mensaje original era de audio
        respond_with_audio = message.tipo == "audio"
        
        # Detectar si es una respuesta a un mensaje interactivo
        is_interactive_response = False
        interactive_id = None
        
        if message.tipo == "interactive" and message.metadata.get("interactive_data"):
            is_interactive_response = True
            interactive_data = message.metadata.get("interactive_data", {})
            interactive_id = interactive_data.get("id")
            
            # Procesar respuesta interactiva según su ID
            if interactive_id:
                return await self._handle_interactive_response(interactive_id, session, message)

        if intent == "check_availability":
            # Comprobar si la feature flag de mensajes interactivos está activada
            ff_service = await get_feature_flag_service()
            use_interactive = await ff_service.is_enabled("features.interactive_messages", default=True)
            
            # Datos de disponibilidad (simulados - en producción vendrían del PMS)
            availability_data = {
                "checkin": "hoy",
                "checkout": "mañana",
                "room_type": "Doble",
                "guests": 2,
                "price": 10000,
                "total": 20000
            }
            
            # Preparar mensaje de respuesta de texto
            response_text = self.template_service.get_response("availability_found", **availability_data)
            
            # Si el mensaje original era de audio, responder también con audio
            if respond_with_audio:
                try:
                    # Generar audio con el texto de respuesta
                    audio_data = await self.audio_processor.generate_audio_response(response_text)
                    
                    if audio_data:
                        logger.info("Generated audio response for availability check", 
                                   audio_bytes=len(audio_data))
                        
                        # No podemos combinar audio con mensajes interactivos en WhatsApp,
                        # así que en este caso priorizamos el audio
                        return {
                            "response_type": "audio",
                            "content": response_text,
                            "audio_data": audio_data
                        }
                except Exception as e:
                    # Si falla la generación de audio, continuamos con texto normal
                    logger.error(f"Failed to generate audio response: {e}")
            
            # Si llegamos aquí, usamos respuesta normal (texto o interactiva)
            if use_interactive:
                # Respuesta con botones interactivos
                button_template = self.template_service.get_interactive_buttons(
                    "availability_confirmation",
                    **availability_data
                )
                
                return {
                    "response_type": "interactive_buttons",
                    "content": button_template
                }
            else:
                # Respuesta de texto tradicional
                return {
                    "response_type": "text",
                    "content": response_text
                }

        elif intent == "make_reservation":
            # Datos de reserva (simulados)
            reservation_data = {
                "deposit": 6000, 
                "bank_info": "CBU 12345..."
            }
            
            # Actualizar estado de sesión para seguimiento de reserva
            session["reservation_pending"] = True
            session["deposit_amount"] = reservation_data["deposit"]
            await self.session_manager.update_session(message.user_id, session, tenant_id)
            
            return {
                "response_type": "text",
                "content": self.template_service.get_response("reservation_instructions", **reservation_data)
            }
            
        elif intent == "hotel_location":
            # Intención de obtener la ubicación del hotel
            response_text = "Nuestro hotel está ubicado en Av. Principal 123, Centro, Ciudad. ¡Esperamos tu visita!"
            
            # Si es un mensaje de audio, responder con audio + ubicación
            if message.tipo == "audio":
                # Generar respuesta de audio
                audio_data = await self.audio_processor.generate_audio_response(response_text)
                
                # Obtener respuesta combinada audio + ubicación
                content = self.template_service.get_audio_with_location(
                    location_template="hotel_location",
                    text=response_text,
                    audio_data=audio_data
                )
                
                return {
                    "response_type": "audio_with_location",
                    "content": content
                }
            else:
                # Responder solo con ubicación (mapa)
                location_data = self.template_service.get_location("hotel_location")
                
                return {
                    "response_type": "location",
                    "content": location_data
                }
            
        elif intent == "show_room_options":
            # Enviar lista interactiva con opciones de habitaciones
            room_options = self.template_service.get_interactive_list(
                "room_options",
                checkin="01/01/2023",
                checkout="05/01/2023",
                price_single=8000,
                price_double=12000,
                price_prem_single=15000,
                price_prem_double=20000
            )
            
            return {
                "response_type": "interactive_list",
                "content": room_options
            }
            
        elif intent == "payment_confirmation" and message.tipo == "image":
            # Si el usuario envía una imagen de comprobante de pago y tiene una reserva pendiente
            if session.get("reservation_pending"):
                # Simular la confirmación del pago
                # En un caso real, procesaríamos la imagen y confirmaríamos con el PMS
                
                # Responder con una reacción positiva al comprobante
                return {
                    "response_type": "reaction",
                    "content": {
                        "message_id": message.message_id,
                        "emoji": self.template_service.get_reaction("payment_received")
                    }
                }
            
        # Si llegamos aquí, devolver respuesta por defecto
        return {
            "response_type": "text",
            "content": "No entendí tu consulta. ¿Podrías reformularla?"
        }
    
    async def _handle_interactive_response(self, interactive_id: str, session: dict, message: UnifiedMessage) -> dict:
        """
        Procesa respuestas a mensajes interactivos basadas en su ID.
        
        Args:
            interactive_id: ID del elemento interactivo seleccionado
            session: Sesión del usuario
            message: Mensaje unificado original
            
        Returns:
            Respuesta formateada según el ID interactivo
        """
        tenant_id = getattr(message, "tenant_id", None)
        
        if interactive_id == "confirm_reservation":
            # Usuario confirmó que quiere reservar después de ver disponibilidad
            reservation_data = {
                "deposit": 6000, 
                "bank_info": "CBU 12345..."
            }
            
            # Actualizar estado de sesión para seguimiento de reserva
            session["reservation_pending"] = True
            session["deposit_amount"] = reservation_data["deposit"]
            await self.session_manager.update_session(message.user_id, session, tenant_id)
            
            return {
                "response_type": "text",
                "content": self.template_service.get_response("reservation_instructions", **reservation_data)
            }
            
        elif interactive_id == "more_options":
            # Usuario quiere ver más opciones de habitaciones
            room_options = self.template_service.get_interactive_list(
                "room_options",
                checkin="01/01/2023",
                checkout="05/01/2023",
                price_single=8000,
                price_double=12000,
                price_prem_single=15000,
                price_prem_double=20000
            )
            
            return {
                "response_type": "interactive_list",
                "content": room_options
            }
            
        elif interactive_id == "transfer_request":
            # Usuario solicitó servicio de transfer
            session["transfer_requested"] = True
            await self.session_manager.update_session(message.user_id, session, tenant_id)
            
            return {
                "response_type": "text",
                "content": "Perfecto. Hemos registrado tu solicitud de transfer. ¿A qué hora llegas?"
            }
            
        # ID interactivo desconocido, enviar mensaje genérico
        return {
            "response_type": "text",
            "content": "Gracias por tu selección. Un representante procesará tu solicitud."
        }
    
    def _get_technical_error_message(self, language: str = "es") -> str:
        """
        Return technical error message in the appropriate language.
        
        Args:
            language: ISO language code (es, en, pt)
            
        Returns:
            Localized error message
        """
        if language == "en":
            return (
                "Sorry, I'm having technical issues. Can you tell me if you want to: "
                "check availability, make a reservation, or get pricing information?"
            )
        elif language == "pt":
            return (
                "Desculpe, estou com problemas técnicos. Você pode me dizer se quer: "
                "verificar disponibilidade, fazer uma reserva ou obter informações de preços?"
            )
        else:  # Spanish (default)
            return (
                "Disculpa, estoy teniendo problemas técnicos. ¿Puedes decirme si quieres: "
                "consultar disponibilidad, hacer una reserva, o información de precios?"
            )
    
    def _get_low_confidence_message(self, language: str = "es") -> str:
        """
        Return low confidence clarification message in the appropriate language.
        
        Args:
            language: ISO language code (es, en, pt)
            
        Returns:
            Localized clarification message
        """
        if language == "en":
            return (
                "I'm not sure I understood. Can you rephrase or choose an option: "
                "availability, pricing, hotel information?"
            )
        elif language == "pt":
            return (
                "Não tenho certeza se entendi. Você pode reformular ou escolher uma opção: "
                "disponibilidade, preços, informações do hotel?"
            )
        else:  # Spanish (default)
            return (
                "No estoy seguro de haber entendido. ¿Puedes reformular o elegir una opción: "
                "disponibilidad, precios, información del hotel?"
            )


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
