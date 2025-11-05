"""
NLP Router - FastAPI endpoints for Hotel NLP Service
RESTful API endpoints for intent recognition and conversation management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from app.core.security import get_current_user
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import redis.asyncio as redis

from app.core.settings import get_settings
from app.services.nlp.integrated_nlp_service import get_nlp_service, NLPServiceRequest

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/nlp", tags=["NLP"])


# Pydantic models for API
class MessageRequest(BaseModel):
    """Request model for processing messages"""

    session_id: str = Field(..., min_length=1, max_length=100, description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=1000, description="User message to process")
    language: str = Field(default="es", description="Language code (es, en, fr)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context metadata")

    @validator("session_id")
    def validate_session_id(cls, v):
        if not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()

    @validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

    @validator("language")
    def validate_language(cls, v):
        allowed_languages = ["es", "en", "fr"]
        if v not in allowed_languages:
            raise ValueError(f"Language must be one of {allowed_languages}")
        return v


class MessageResponse(BaseModel):
    """Response model for processed messages"""

    session_id: str
    response_text: str
    quick_replies: List[str]
    intent: str
    confidence: float
    conversation_state: str
    requires_escalation: bool = False
    metadata: Dict[str, Any] = {}
    processing_time: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ConversationSummaryResponse(BaseModel):
    """Response model for conversation summary"""

    session_id: str
    state: str
    current_intent: Optional[str]
    message_count: int
    sentiment_score: float
    urgency_level: str
    reservation_status: str
    confirmed_entities: Dict[str, Any]
    reservation_context: Dict[str, Any]
    created_at: str
    last_updated: str


class IntentSuggestion(BaseModel):
    """Model for intent suggestions"""

    intent: str
    confidence: float
    description: str


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: str
    timestamp: str
    components: Dict[str, str]
    metrics: Dict[str, Any]


class AnalyticsResponse(BaseModel):
    """Analytics response model"""

    status: str
    time_range_hours: int
    total_conversations: int
    average_message_count: float
    average_sentiment: float
    intent_distribution: Dict[str, int]
    state_distribution: Dict[str, int]
    escalation_rate: float


# Dependency injection
async def get_redis_client():
    """Get Redis client"""
    settings = get_settings()
    if settings.redis_url:
        return redis.from_url(settings.redis_url)
    return None


# API Endpoints


@router.post("/message", response_model=MessageResponse)
@limiter.limit("60/minute")
async def process_message(
    request: Request,
    message_request: MessageRequest,
    background_tasks: BackgroundTasks,
    redis_client=Depends(get_redis_client),
):
    """
    Process a guest message and generate intelligent response

    This endpoint handles the complete NLP pipeline:
    - Intent recognition
    - Entity extraction
    - Context processing
    - Response generation
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Create service request
        service_request = NLPServiceRequest(
            session_id=message_request.session_id,
            message=message_request.message,
            language=message_request.language,
            context_metadata=message_request.metadata,
        )

        # Process message
        service_response = await nlp_service.process_message(service_request)

        # Convert to API response
        response = MessageResponse(
            session_id=service_response.session_id,
            response_text=service_response.response_text,
            quick_replies=service_response.quick_replies,
            intent=service_response.intent,
            confidence=service_response.confidence,
            conversation_state=service_response.conversation_state,
            requires_escalation=service_response.requires_escalation,
            metadata=service_response.metadata,
            processing_time=service_response.processing_time,
        )

        logger.info(f"Message processed successfully: {message_request.session_id}")
        return response

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversation/{session_id}", response_model=ConversationSummaryResponse)
@limiter.limit("30/minute")
async def get_conversation_summary(request: Request, session_id: str, redis_client=Depends(get_redis_client)):
    """
    Get comprehensive conversation summary for a session

    Returns current state, entities, and conversation history
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Get conversation summary
        summary = await nlp_service.get_conversation_summary(session_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Convert to response model
        response = ConversationSummaryResponse(**summary)

        logger.info(f"Conversation summary retrieved: {session_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/conversation/{session_id}")
@limiter.limit("20/minute")
async def end_conversation(
    request: Request, session_id: str, reason: str = "user_ended", redis_client=Depends(get_redis_client)
):
    """
    End a conversation session

    Cleans up session data and logs conversation metrics
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # End conversation
        success = await nlp_service.end_conversation(session_id, reason)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        logger.info(f"Conversation ended: {session_id}, reason: {reason}")
        return {"message": "Conversation ended successfully", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/suggestions", response_model=List[IntentSuggestion])
@limiter.limit("20/minute")
async def get_intent_suggestions(request: Request, partial_message: str, redis_client=Depends(get_redis_client)):
    """
    Get intent suggestions for partial message (autocomplete functionality)

    Useful for chat interfaces with predictive input
    """
    try:
        if len(partial_message.strip()) < 2:
            return []

        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Get suggestions
        suggestions = await nlp_service.get_intent_suggestions(partial_message)

        # Convert to response models
        response = [IntentSuggestion(**suggestion) for suggestion in suggestions]

        logger.info(f"Intent suggestions generated for: {partial_message[:20]}...")
        return response

    except Exception as e:
        logger.error(f"Error getting intent suggestions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics", response_model=AnalyticsResponse)
@limiter.limit("10/minute")
async def get_conversation_analytics(
    request: Request, time_range_hours: int = 24, redis_client=Depends(get_redis_client)
):
    """
    Get conversation analytics and insights

    Provides metrics on conversation patterns, intents, and performance
    """
    try:
        if time_range_hours < 1 or time_range_hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="Time range must be between 1 and 168 hours")

        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Get analytics
        analytics = await nlp_service.analyze_conversation_patterns(time_range_hours)

        if analytics["status"] == "error":
            raise HTTPException(status_code=500, detail=analytics["message"])

        if analytics["status"] == "no_data":
            # Return empty analytics
            return AnalyticsResponse(
                status="no_data",
                time_range_hours=time_range_hours,
                total_conversations=0,
                average_message_count=0.0,
                average_sentiment=0.0,
                intent_distribution={},
                state_distribution={},
                escalation_rate=0.0,
            )

        # Convert to response model
        response = AnalyticsResponse(**analytics)

        logger.info(f"Analytics generated for {time_range_hours}h range")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request, redis_client=Depends(get_redis_client)):
    """
    Comprehensive health check for NLP service

    Checks all components and returns detailed status
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Perform health check
        health_status = await nlp_service.health_check()

        # Convert to response model
        response = HealthCheckResponse(**health_status)

        # Set appropriate HTTP status
        status_code = 200
        if health_status["status"] == "degraded":
            status_code = 200  # Still operational
        elif health_status["status"] == "unhealthy":
            status_code = 503  # Service unavailable

        return JSONResponse(content=response.dict(), status_code=status_code)

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}, status_code=503
        )


# Batch processing endpoint for high-volume scenarios
@router.post("/batch", response_model=List[MessageResponse])
@limiter.limit("10/minute")
async def process_batch_messages(
    request: Request, messages: List[MessageRequest], redis_client=Depends(get_redis_client)
):
    """
    Process multiple messages in batch

    Useful for processing multiple user inputs or conversation history
    """
    try:
        if len(messages) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 messages per batch")

        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        responses = []

        for message_request in messages:
            # Create service request
            service_request = NLPServiceRequest(
                session_id=message_request.session_id,
                message=message_request.message,
                language=message_request.language,
                context_metadata=message_request.metadata,
            )

            # Process message
            service_response = await nlp_service.process_message(service_request)

            # Convert to API response
            response = MessageResponse(
                session_id=service_response.session_id,
                response_text=service_response.response_text,
                quick_replies=service_response.quick_replies,
                intent=service_response.intent,
                confidence=service_response.confidence,
                conversation_state=service_response.conversation_state,
                requires_escalation=service_response.requires_escalation,
                metadata=service_response.metadata,
                processing_time=service_response.processing_time,
            )

            responses.append(response)

        logger.info(f"Batch processed {len(messages)} messages")
        return responses

    except ValueError as e:
        logger.warning(f"Validation error in batch: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing batch messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin endpoints
@router.get("/admin/sessions", dependencies=[Depends(get_current_user)])
@limiter.limit("5/minute")
async def get_active_sessions(request: Request, redis_client=Depends(get_redis_client)):
    """
    Get list of active conversation sessions (Admin only)
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Get active sessions from context processor
        active_sessions = list(nlp_service.context_processor.active_contexts.keys())

        return {
            "active_sessions": active_sessions,
            "count": len(active_sessions),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/cleanup", dependencies=[Depends(get_current_user)])
@limiter.limit("2/minute")
async def force_cleanup(request: Request, redis_client=Depends(get_redis_client)):
    """
    Force cleanup of expired sessions (Admin only)
    """
    try:
        # Get NLP service
        nlp_service = await get_nlp_service(redis_client)

        # Force cleanup
        await nlp_service.context_processor.cleanup_expired_contexts()

        return {"message": "Cleanup completed successfully", "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Error in force cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Add rate limit exceeded handler
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
