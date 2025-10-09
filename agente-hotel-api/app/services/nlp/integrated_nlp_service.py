"""
Integrated Hotel NLP Service
Complete NLP orchestration service integrating intent recognition, context processing, and response generation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, Summary

from .enhanced_nlp_engine import HotelNLPEngine, IntentType, create_nlp_engine
from .hotel_context_processor import HotelContextProcessor, get_context_processor
from .hotel_response_generator import HotelResponseGenerator, get_response_generator

logger = logging.getLogger(__name__)

# Prometheus metrics
nlp_service_requests_total = Counter(
    "nlp_service_requests_total",
    "Total NLP service requests",
    ["endpoint", "status"]
)

nlp_service_processing_time = Histogram(
    "nlp_service_processing_time_seconds",
    "NLP service processing time",
    ["operation"]
)

nlp_service_active_sessions = Gauge(
    "nlp_service_active_sessions",
    "Number of active NLP sessions"
)

nlp_conversation_length = Summary(
    "nlp_conversation_length_messages",
    "Length of conversations in messages"
)

@dataclass
class NLPServiceRequest:
    """Request to NLP service"""
    session_id: str
    message: str
    language: str = "es"
    context_metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass 
class NLPServiceResponse:
    """Response from NLP service"""
    session_id: str
    response_text: str
    quick_replies: List[str]
    intent: str
    confidence: float
    conversation_state: str
    requires_escalation: bool = False
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class IntegratedHotelNLPService:
    """Complete NLP service for hotel guest interactions"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.nlp_engine: Optional[HotelNLPEngine] = None
        self.context_processor: HotelContextProcessor = get_context_processor()
        self.response_generator: HotelResponseGenerator = get_response_generator()
        
        # Service configuration
        self.max_message_length = 1000
        self.session_timeout = 3600  # 1 hour
        self.max_concurrent_sessions = 1000
        
        # Performance tracking
        self.active_sessions = set()
        self.request_count = 0
        
        logger.info("IntegratedHotelNLPService initialized")
    
    async def initialize(self):
        """Initialize all NLP components"""
        logger.info("🧠 Initializing Integrated Hotel NLP Service...")
        
        try:
            # Initialize NLP engine
            self.nlp_engine = await create_nlp_engine(self.redis_client)
            
            # Start background tasks
            asyncio.create_task(self._cleanup_expired_sessions())
            asyncio.create_task(self._update_metrics())
            
            logger.info("✅ Integrated Hotel NLP Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize NLP Service: {e}")
            raise
    
    async def process_message(self, request: NLPServiceRequest) -> NLPServiceResponse:
        """Process a guest message and generate response"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate request
            self._validate_request(request)
            
            # Track active session
            self.active_sessions.add(request.session_id)
            self.request_count += 1
            
            # Step 1: Intent prediction
            prediction = await self.nlp_engine.predict_intent(
                request.message, 
                request.context_metadata
            )
            
            # Step 2: Context processing
            processing_result = await self.context_processor.process_prediction(
                request.session_id,
                prediction,
                request.message
            )
            
            # Step 3: Response generation
            response_data = await self.response_generator.generate_response(
                processing_result["context"],
                processing_result
            )
            
            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Create response
            response = NLPServiceResponse(
                session_id=request.session_id,
                response_text=response_data["text"],
                quick_replies=response_data["quick_replies"],
                intent=prediction.intent.value,
                confidence=prediction.confidence,
                conversation_state=processing_result["context"].state.value,
                requires_escalation=processing_result["requires_escalation"],
                metadata=response_data["metadata"],
                processing_time=processing_time
            )
            
            # Update metrics
            nlp_service_requests_total.labels(
                endpoint="process_message",
                status="success"
            ).inc()
            
            nlp_service_processing_time.labels(
                operation="full_processing"
            ).observe(processing_time)
            
            # Log conversation length if completed
            if processing_result["conversation_complete"]:
                context = processing_result["context"]
                nlp_conversation_length.observe(context.message_count)
            
            logger.info(f"Message processed successfully - Session: {request.session_id}, "
                       f"Intent: {prediction.intent.value}, Confidence: {prediction.confidence:.3f}, "
                       f"Time: {processing_time:.3f}s")
            
            return response
            
        except Exception as e:
            # Update error metrics
            nlp_service_requests_total.labels(
                endpoint="process_message",
                status="error"
            ).inc()
            
            logger.error(f"Error processing message for session {request.session_id}: {e}")
            
            # Generate error response
            error_response_text = await self.response_generator.generate_error_response(
                "system_error",
                self.context_processor.get_or_create_context(request.session_id)
            )
            
            return NLPServiceResponse(
                session_id=request.session_id,
                response_text=error_response_text,
                quick_replies=["Hablar con agente", "Intentar nuevamente"],
                intent="error",
                confidence=0.0,
                conversation_state="error",
                requires_escalation=True,
                processing_time=asyncio.get_event_loop().time() - start_time
            )
        
        finally:
            # Clean up session tracking
            self.active_sessions.discard(request.session_id)
    
    def _validate_request(self, request: NLPServiceRequest):
        """Validate incoming request"""
        if not request.session_id:
            raise ValueError("Session ID is required")
        
        if not request.message or not request.message.strip():
            raise ValueError("Message cannot be empty")
        
        if len(request.message) > self.max_message_length:
            raise ValueError(f"Message too long (max {self.max_message_length} characters)")
        
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            raise ValueError("Maximum concurrent sessions reached")
    
    async def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation summary for a session"""
        try:
            summary = self.context_processor.get_context_summary(session_id)
            
            if summary:
                nlp_service_requests_total.labels(
                    endpoint="get_summary",
                    status="success"
                ).inc()
            
            return summary
            
        except Exception as e:
            nlp_service_requests_total.labels(
                endpoint="get_summary", 
                status="error"
            ).inc()
            
            logger.error(f"Error getting conversation summary for {session_id}: {e}")
            return None
    
    async def end_conversation(self, session_id: str, reason: str = "user_ended") -> bool:
        """End a conversation session"""
        try:
            # Get context before removing
            context = self.context_processor.active_contexts.get(session_id)
            
            if context:
                # Log conversation metrics
                nlp_conversation_length.observe(context.message_count)
                
                # Remove from active contexts
                del self.context_processor.active_contexts[session_id]
                
                logger.info(f"Conversation ended - Session: {session_id}, "
                           f"Reason: {reason}, Messages: {context.message_count}")
            
            nlp_service_requests_total.labels(
                endpoint="end_conversation",
                status="success"
            ).inc()
            
            return True
            
        except Exception as e:
            nlp_service_requests_total.labels(
                endpoint="end_conversation",
                status="error"
            ).inc()
            
            logger.error(f"Error ending conversation {session_id}: {e}")
            return False
    
    async def get_intent_suggestions(self, partial_message: str) -> List[Dict[str, Any]]:
        """Get intent suggestions for partial message (autocomplete)"""
        try:
            # Get similar intents
            similar_intents = await self.nlp_engine.get_similar_intents(partial_message, top_k=5)
            
            suggestions = []
            for intent, score in similar_intents:
                if score > 0.3:  # Only include relevant suggestions
                    suggestions.append({
                        "intent": intent.value,
                        "confidence": score,
                        "description": self._get_intent_description(intent)
                    })
            
            nlp_service_requests_total.labels(
                endpoint="get_suggestions",
                status="success"
            ).inc()
            
            return suggestions
            
        except Exception as e:
            nlp_service_requests_total.labels(
                endpoint="get_suggestions",
                status="error"
            ).inc()
            
            logger.error(f"Error getting intent suggestions: {e}")
            return []
    
    def _get_intent_description(self, intent: IntentType) -> str:
        """Get human-readable description for intent"""
        descriptions = {
            IntentType.BOOK_ROOM: "Reservar habitación",
            IntentType.CHECK_AVAILABILITY: "Consultar disponibilidad",
            IntentType.ROOM_SERVICE: "Servicio a la habitación",
            IntentType.CANCEL_RESERVATION: "Cancelar reserva",
            IntentType.MODIFY_RESERVATION: "Modificar reserva",
            IntentType.HOTEL_INFO: "Información del hotel",
            IntentType.AMENITIES: "Servicios y amenidades",
            IntentType.CHECK_IN: "Check-in",
            IntentType.CHECK_OUT: "Check-out",
            IntentType.COMPLAINT: "Reclamo o problema",
            IntentType.FEEDBACK: "Comentarios",
            IntentType.EMERGENCY: "Emergencia",
            IntentType.GREETING: "Saludo",
            IntentType.GOODBYE: "Despedida"
        }
        
        return descriptions.get(intent, intent.value)
    
    async def analyze_conversation_patterns(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Analyze conversation patterns for insights"""
        try:
            # This would typically query a database or analytics service
            # For now, return sample analytics based on active contexts
            
            active_contexts = list(self.context_processor.active_contexts.values())
            
            if not active_contexts:
                return {"status": "no_data", "message": "No active conversations"}
            
            # Calculate basic statistics
            total_conversations = len(active_contexts)
            avg_message_count = sum(ctx.message_count for ctx in active_contexts) / total_conversations
            
            # Intent distribution
            intent_counts = {}
            for ctx in active_contexts:
                for intent in ctx.intent_history:
                    intent_counts[intent.value] = intent_counts.get(intent.value, 0) + 1
            
            # Sentiment analysis
            avg_sentiment = sum(ctx.sentiment_score for ctx in active_contexts) / total_conversations
            
            # State distribution
            state_counts = {}
            for ctx in active_contexts:
                state_counts[ctx.state.value] = state_counts.get(ctx.state.value, 0) + 1
            
            return {
                "status": "success",
                "time_range_hours": time_range_hours,
                "total_conversations": total_conversations,
                "average_message_count": round(avg_message_count, 2),
                "average_sentiment": round(avg_sentiment, 3),
                "intent_distribution": intent_counts,
                "state_distribution": state_counts,
                "escalation_rate": sum(1 for ctx in active_contexts if ctx.urgency_level == "high") / total_conversations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation patterns: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _cleanup_expired_sessions(self):
        """Background task to clean up expired sessions"""
        while True:
            try:
                await self.context_processor.cleanup_expired_contexts()
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def _update_metrics(self):
        """Background task to update metrics"""
        while True:
            try:
                # Update active sessions gauge
                nlp_service_active_sessions.set(len(self.active_sessions))
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(60)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "metrics": {}
        }
        
        try:
            # Check NLP engine
            if self.nlp_engine:
                nlp_health = await self.nlp_engine.health_check()
                health_status["components"]["nlp_engine"] = nlp_health["status"]
            else:
                health_status["components"]["nlp_engine"] = "not_initialized"
                health_status["status"] = "degraded"
            
            # Check context processor
            active_contexts_count = len(self.context_processor.active_contexts)
            health_status["components"]["context_processor"] = "ok"
            
            # Check response generator
            health_status["components"]["response_generator"] = "ok"
            
            # Check Redis connection
            if self.redis_client:
                await self.redis_client.ping()
                health_status["components"]["redis"] = "ok"
            else:
                health_status["components"]["redis"] = "not_configured"
            
            # Include performance metrics
            health_status["metrics"] = {
                "active_sessions": len(self.active_sessions),
                "active_contexts": active_contexts_count,
                "total_requests": self.request_count,
                "session_limit": self.max_concurrent_sessions
            }
            
            # Check if we're approaching limits
            if len(self.active_sessions) > self.max_concurrent_sessions * 0.8:
                health_status["status"] = "degraded"
                health_status["warning"] = "Approaching session limit"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status

# Global service instance
_nlp_service = None

async def get_nlp_service(redis_client: Optional[redis.Redis] = None) -> IntegratedHotelNLPService:
    """Get global NLP service instance"""
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = IntegratedHotelNLPService(redis_client)
        await _nlp_service.initialize()
    return _nlp_service

async def create_nlp_service(redis_client: Optional[redis.Redis] = None) -> IntegratedHotelNLPService:
    """Create and initialize new NLP service instance"""
    service = IntegratedHotelNLPService(redis_client)
    await service.initialize()
    return service