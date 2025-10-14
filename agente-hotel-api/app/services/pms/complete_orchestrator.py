"""
Complete PMS Integration Orchestrator
Orchestrates the complete hotel workflow from voice input to confirmed reservation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import uuid

from app.services.pms.enhanced_pms_service import EnhancedPMSService, Reservation
from app.services.pms.intelligent_reservation_manager import ReservationWorkflowState, get_reservation_manager
from app.services.pms.booking_confirmation_service import (
    ConfirmationChannel,
    GuestPreferences,
    get_confirmation_service,
)
from app.services.nlp.hotel_context_processor import ConversationContext
from app.core.retry import retry_with_backoff
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
orchestrator_operations_total = Counter(
    "orchestrator_operations_total", "Total orchestrator operations", ["operation", "status"]
)

orchestrator_processing_time = Histogram(
    "orchestrator_processing_time_seconds", "Orchestrator processing time", ["operation"]
)

active_workflows_gauge = Gauge("active_workflows_total", "Number of active reservation workflows")

conversion_rate_gauge = Gauge("reservation_conversion_rate", "Reservation conversion rate from inquiry to completion")


class WorkflowStage(Enum):
    """Workflow processing stages"""

    AUDIO_PROCESSING = "audio_processing"
    NLP_ANALYSIS = "nlp_analysis"
    INTENT_RECOGNITION = "intent_recognition"
    CONTEXT_PROCESSING = "context_processing"
    PMS_OPERATIONS = "pms_operations"
    RESPONSE_GENERATION = "response_generation"
    CONFIRMATION_SENDING = "confirmation_sending"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class OrchestrationRequest:
    """Complete orchestration request"""

    session_id: str
    channel: str = "whatsapp"  # whatsapp, email, chat, voice
    content_type: str = "text"  # text, audio, image
    content: Any = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    language: str = "en"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class OrchestrationResponse:
    """Complete orchestration response"""

    session_id: str
    correlation_id: str
    response_text: str
    response_audio: Optional[bytes] = None
    workflow_state: Optional[ReservationWorkflowState] = None
    available_options: List[Dict[str, Any]] = field(default_factory=list)
    reservation_summary: Optional[Dict[str, Any]] = None
    confirmation_sent: bool = False
    suggested_actions: List[str] = field(default_factory=list)
    processing_time_ms: float = 0
    stage_completed: WorkflowStage = WorkflowStage.COMPLETED
    error_message: Optional[str] = None


class CompletePMSOrchestrator:
    """Complete orchestrator for hotel agent workflows"""

    def __init__(self):
        # Core services
        self.audio_processor = None
        self.nlp_engine = None
        self.context_processor = None
        self.response_generator = None
        self.pms_service = None
        self.reservation_manager = None
        self.confirmation_service = None
        self.session_manager = None

        # Orchestration state
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.workflow_sessions: Dict[str, str] = {}  # session_id -> workflow_id

        # Performance tracking
        self.total_inquiries = 0
        self.completed_reservations = 0

        logger.info("Complete PMS Orchestrator initialized")

    async def initialize_services(self):
        """Initialize all required services"""

        try:
            # Initialize audio processor
            from app.services.audio_processor import get_audio_processor

            self.audio_processor = get_audio_processor()

            # Initialize NLP services
            from app.services.nlp.enhanced_nlp_engine import get_nlp_engine
            from app.services.nlp.hotel_context_processor import get_context_processor
            from app.services.nlp.hotel_response_generator import get_response_generator

            self.nlp_engine = get_nlp_engine()
            self.context_processor = get_context_processor()
            self.response_generator = get_response_generator()

            # Initialize PMS services
            from app.core.settings import get_settings

            settings = get_settings()

            self.pms_service = EnhancedPMSService(pms_type=settings.pms_type)
            await self.pms_service.start()

            self.reservation_manager = get_reservation_manager(self.pms_service)

            # Initialize confirmation service
            from app.services.template_service import get_template_service
            from app.services.whatsapp_client import get_whatsapp_client
            from app.services.gmail_client import get_gmail_client

            self.confirmation_service = get_confirmation_service(
                template_service=get_template_service(),
                whatsapp_client=get_whatsapp_client(),
                gmail_client=get_gmail_client(),
            )

            # Initialize session manager
            from app.services.session_manager import get_session_manager

            self.session_manager = get_session_manager()

            logger.info("All orchestrator services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator services: {e}")
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def process_guest_input(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Process complete guest input through the entire workflow"""

        start_time = asyncio.get_event_loop().time()

        try:
            # Initialize response
            response = OrchestrationResponse(
                session_id=request.session_id,
                correlation_id=request.correlation_id,
                response_text="",
                stage_completed=WorkflowStage.AUDIO_PROCESSING,
            )

            # Update session tracking
            if request.session_id not in self.active_sessions:
                self.active_sessions[request.session_id] = {
                    "created_at": datetime.now(),
                    "channel": request.channel,
                    "guest_phone": request.guest_phone,
                    "guest_email": request.guest_email,
                    "language": request.language,
                    "interactions": 0,
                }

            self.active_sessions[request.session_id]["interactions"] += 1

            # Stage 1: Audio Processing (if needed)
            text_content = await self._process_audio_content(request, response)
            response.stage_completed = WorkflowStage.NLP_ANALYSIS

            # Stage 2: NLP Analysis and Intent Recognition
            nlp_result = await self._process_nlp_analysis(request, text_content, response)
            response.stage_completed = WorkflowStage.CONTEXT_PROCESSING

            # Stage 3: Context Processing and Workflow Management
            workflow_result = await self._process_workflow_context(request, nlp_result, response)
            response.stage_completed = WorkflowStage.PMS_OPERATIONS

            # Stage 4: PMS Operations (if needed)
            pms_result = await self._process_pms_operations(request, workflow_result, response)
            response.stage_completed = WorkflowStage.RESPONSE_GENERATION

            # Stage 5: Response Generation
            final_response = await self._generate_response(request, pms_result, response)
            response.stage_completed = WorkflowStage.CONFIRMATION_SENDING

            # Stage 6: Confirmation Sending (if reservation completed)
            await self._handle_confirmation_sending(request, final_response, response)
            response.stage_completed = WorkflowStage.COMPLETED

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            response.processing_time_ms = processing_time * 1000

            orchestrator_processing_time.labels(operation="complete_workflow").observe(processing_time)

            orchestrator_operations_total.labels(operation="process_input", status="success").inc()

            # Update conversion metrics
            self._update_conversion_metrics()

            logger.info(f"Processed guest input successfully: {request.correlation_id} in {processing_time:.2f}s")

            return response

        except Exception as e:
            logger.error(f"Error processing guest input: {e}")

            orchestrator_operations_total.labels(operation="process_input", status="error").inc()

            processing_time = asyncio.get_event_loop().time() - start_time

            return OrchestrationResponse(
                session_id=request.session_id,
                correlation_id=request.correlation_id,
                response_text="I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                processing_time_ms=processing_time * 1000,
                stage_completed=WorkflowStage.ERROR,
                error_message=str(e),
            )

    async def _process_audio_content(self, request: OrchestrationRequest, response: OrchestrationResponse) -> str:
        """Process audio content to text"""

        if request.content_type == "audio" and request.content:
            try:
                # Convert audio to text using STT
                transcription_result = await self.audio_processor.transcribe_audio(
                    audio_data=request.content, language=request.language
                )

                logger.info(f"Audio transcribed for session {request.session_id}: {transcription_result.text[:100]}...")

                return transcription_result.text

            except Exception as e:
                logger.error(f"Audio processing failed: {e}")
                raise ValueError(f"Failed to process audio: {str(e)}")

        elif request.content_type == "text":
            return str(request.content) if request.content else ""

        else:
            raise ValueError(f"Unsupported content type: {request.content_type}")

    async def _process_nlp_analysis(
        self, request: OrchestrationRequest, text_content: str, response: OrchestrationResponse
    ) -> Dict[str, Any]:
        """Process NLP analysis and intent recognition"""

        try:
            # Get session context
            session_data = await self.session_manager.get_session(request.session_id)

            # Process with NLP engine
            nlp_result = await self.nlp_engine.process_guest_message(
                message=text_content, session_id=request.session_id, context=session_data
            )

            logger.info(
                f"NLP analysis completed for session {request.session_id}: "
                f"intent={nlp_result.primary_intent}, "
                f"confidence={nlp_result.confidence:.2f}"
            )

            return {"nlp_result": nlp_result, "text_content": text_content, "session_data": session_data}

        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            raise ValueError(f"Failed to analyze message: {str(e)}")

    async def _process_workflow_context(
        self, request: OrchestrationRequest, nlp_result: Dict[str, Any], response: OrchestrationResponse
    ) -> Dict[str, Any]:
        """Process conversation context and manage workflow"""

        try:
            nlp_output = nlp_result["nlp_result"]
            session_data = nlp_result["session_data"]

            # Create conversation context
            context = ConversationContext(
                session_id=request.session_id,
                current_intent=nlp_output.primary_intent,
                intent_confidence=nlp_output.confidence,
                entities=nlp_output.entities,
                sentiment=nlp_output.sentiment,
                previous_intents=session_data.get("intent_history", []),
                reservation_context=nlp_output.reservation_data,
            )

            # Process context for hotel-specific information
            processed_context = await self.context_processor.process_context(context)

            # Manage reservation workflow
            workflow_id = self.workflow_sessions.get(request.session_id)

            if not workflow_id and processed_context.is_reservation_related:
                # Start new reservation workflow
                workflow = await self.reservation_manager.start_reservation_workflow(
                    request.session_id, processed_context
                )
                self.workflow_sessions[request.session_id] = workflow.workflow_id
                workflow_id = workflow.workflow_id

                self.total_inquiries += 1
                active_workflows_gauge.inc()

                logger.info(f"Started new reservation workflow: {workflow_id}")

            workflow_state = None
            workflow_data = {}

            if workflow_id:
                # Process workflow step
                try:
                    workflow_state, workflow_data = await self.reservation_manager.process_workflow_step(
                        workflow_id, processed_context
                    )

                    response.workflow_state = workflow_state

                    # Handle workflow completion
                    if workflow_state == ReservationWorkflowState.COMPLETED:
                        self.completed_reservations += 1
                        active_workflows_gauge.dec()
                        logger.info(f"Completed reservation workflow: {workflow_id}")

                    elif workflow_state in [ReservationWorkflowState.CANCELLED, ReservationWorkflowState.ERROR]:
                        active_workflows_gauge.dec()

                except Exception as e:
                    logger.error(f"Workflow processing failed: {e}")
                    # Continue with standard response generation

            # Update session data
            await self.session_manager.update_session(
                session_id=request.session_id,
                data={
                    "last_intent": nlp_output.primary_intent,
                    "last_confidence": nlp_output.confidence,
                    "intent_history": session_data.get("intent_history", [])[-10:] + [nlp_output.primary_intent],
                    "workflow_id": workflow_id,
                    "workflow_state": workflow_state.value if workflow_state else None,
                    "last_interaction": datetime.now().isoformat(),
                },
            )

            return {
                "processed_context": processed_context,
                "workflow_state": workflow_state,
                "workflow_data": workflow_data,
                "workflow_id": workflow_id,
            }

        except Exception as e:
            logger.error(f"Context processing failed: {e}")
            raise ValueError(f"Failed to process context: {str(e)}")

    async def _process_pms_operations(
        self, request: OrchestrationRequest, workflow_result: Dict[str, Any], response: OrchestrationResponse
    ) -> Dict[str, Any]:
        """Process PMS operations based on workflow state"""

        try:
            workflow_state = workflow_result.get("workflow_state")
            workflow_data = workflow_result.get("workflow_data", {})
            processed_context = workflow_result["processed_context"]

            pms_data = {}

            # Handle availability checks
            if "available_options" in workflow_data:
                response.available_options = [
                    {
                        "room_type": option.room_type.value,
                        "available_rooms": option.available_rooms,
                        "base_rate": option.rates[0].base_rate if option.rates else 0,
                        "currency": option.rates[0].currency if option.rates else "USD",
                        "includes_breakfast": option.rates[0].includes_breakfast if option.rates else False,
                    }
                    for option in workflow_data["available_options"]
                ]
                pms_data["availability_checked"] = True

            # Handle reservation summaries
            if "reservation_summary" in workflow_data:
                response.reservation_summary = workflow_data["reservation_summary"]
                pms_data["reservation_summary"] = workflow_data["reservation_summary"]

            # Handle completed reservations
            if workflow_state == ReservationWorkflowState.COMPLETED and "reservation" in workflow_data:
                pms_data["completed_reservation"] = workflow_data["reservation"]
                pms_data["confirmation_details"] = workflow_data.get("confirmation_details", {})

            # Direct PMS queries for non-workflow requests
            if processed_context.current_intent in ["check_availability", "room_info"] and not workflow_data:
                # Perform direct availability check
                if processed_context.reservation_context.get("checkin_date"):
                    try:
                        checkin_date = date.fromisoformat(processed_context.reservation_context["checkin_date"])
                        checkout_date = date.fromisoformat(
                            processed_context.reservation_context.get(
                                "checkout_date", (checkin_date + timedelta(days=1)).isoformat()
                            )
                        )

                        availability = await self.pms_service.check_availability(
                            checkin_date=checkin_date,
                            checkout_date=checkout_date,
                            adults=processed_context.reservation_context.get("guest_count", 1),
                            children=0,
                        )

                        pms_data["direct_availability"] = availability

                    except Exception as e:
                        logger.error(f"Direct availability check failed: {e}")

            return {**workflow_result, "pms_data": pms_data}

        except Exception as e:
            logger.error(f"PMS operations failed: {e}")
            return workflow_result  # Continue without PMS data

    async def _generate_response(
        self, request: OrchestrationRequest, pms_result: Dict[str, Any], response: OrchestrationResponse
    ) -> Dict[str, Any]:
        """Generate appropriate response based on workflow state and data"""

        try:
            processed_context = pms_result["processed_context"]
            workflow_state = pms_result.get("workflow_state")
            pms_result.get("workflow_data", {})
            pms_result.get("pms_data", {})

            # Generate contextual response
            response_data = await self.response_generator.generate_response(
                context=processed_context,
                workflow_state=workflow_state,
                available_options=response.available_options,
                reservation_summary=response.reservation_summary,
                language=request.language,
            )

            response.response_text = response_data["response_text"]
            response.suggested_actions = response_data.get("suggested_actions", [])

            # Generate audio response if needed
            if request.channel in ["voice", "whatsapp_voice"]:
                try:
                    audio_response = await self.audio_processor.text_to_speech(
                        text=response.response_text, language=request.language
                    )
                    response.response_audio = audio_response.audio_data
                except Exception as e:
                    logger.error(f"TTS generation failed: {e}")
                    # Continue without audio

            return {**pms_result, "response_generated": True, "response_data": response_data}

        except Exception as e:
            logger.error(f"Response generation failed: {e}")

            # Fallback response
            response.response_text = "I apologize, but I'm having trouble generating a response. Please try again."
            return pms_result

    async def _handle_confirmation_sending(
        self, request: OrchestrationRequest, final_result: Dict[str, Any], response: OrchestrationResponse
    ):
        """Handle sending confirmation for completed reservations"""

        try:
            pms_data = final_result.get("pms_data", {})

            if "completed_reservation" in pms_data:
                completed_reservation = pms_data["completed_reservation"]

                # Determine confirmation channels
                channels = []
                if request.guest_email:
                    channels.append(ConfirmationChannel.EMAIL)
                if request.guest_phone and request.channel == "whatsapp":
                    channels.append(ConfirmationChannel.WHATSAPP)

                if channels:
                    guest_preferences = GuestPreferences(
                        preferred_language=request.language, preferred_channels=channels
                    )

                    # Send confirmation asynchronously
                    asyncio.create_task(
                        self._send_confirmation_async(completed_reservation, channels, guest_preferences)
                    )

                    response.confirmation_sent = True

                    logger.info(f"Confirmation initiated for reservation: {completed_reservation.confirmation_number}")

        except Exception as e:
            logger.error(f"Confirmation sending failed: {e}")
            # Don't fail the entire request for confirmation issues

    async def _send_confirmation_async(
        self, reservation: Reservation, channels: List[ConfirmationChannel], guest_preferences: GuestPreferences
    ):
        """Send confirmation asynchronously"""

        try:
            result = await self.confirmation_service.send_confirmation(reservation, channels, guest_preferences)

            logger.info(f"Confirmation sent successfully for reservation {reservation.confirmation_number}: {result}")

        except Exception as e:
            logger.error(f"Async confirmation sending failed: {e}")

    def _update_conversion_metrics(self):
        """Update conversion rate metrics"""

        if self.total_inquiries > 0:
            conversion_rate = self.completed_reservations / self.total_inquiries
            conversion_rate_gauge.set(conversion_rate)

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session status"""

        session_data = self.active_sessions.get(session_id)
        if not session_data:
            return None

        workflow_id = self.workflow_sessions.get(session_id)
        workflow_status = None

        if workflow_id:
            workflow_status = await self.reservation_manager.get_workflow_status(workflow_id)

        return {
            "session_id": session_id,
            "created_at": session_data["created_at"].isoformat(),
            "channel": session_data["channel"],
            "language": session_data["language"],
            "interactions": session_data["interactions"],
            "workflow_id": workflow_id,
            "workflow_status": workflow_status,
        }

    async def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions"""

        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        expired_sessions = []
        for session_id, session_data in self.active_sessions.items():
            if session_data["created_at"] < cutoff_time:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            # Clean up workflow if exists
            workflow_id = self.workflow_sessions.get(session_id)
            if workflow_id:
                await self.reservation_manager.cancel_reservation(workflow_id, "session_expired")
                del self.workflow_sessions[session_id]
                active_workflows_gauge.dec()

            # Clean up session
            del self.active_sessions[session_id]

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Global instance
_orchestrator = None


async def get_orchestrator() -> CompletePMSOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CompletePMSOrchestrator()
        await _orchestrator.initialize_services()
    return _orchestrator
