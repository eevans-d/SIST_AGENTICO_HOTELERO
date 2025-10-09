"""
Hotel Context Processor
Advanced context understanding and conversation state management for hotel interactions
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
import uuid
from collections import defaultdict, deque

from .enhanced_nlp_engine import IntentType, EntityType, IntentPrediction, ExtractedEntity

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Conversation state tracking"""
    INITIAL = "initial"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ERROR = "error"

class ReservationStatus(Enum):
    """Reservation tracking status"""
    INQUIRY = "inquiry"
    PARTIAL_INFO = "partial_info"
    READY_TO_BOOK = "ready_to_book"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    MODIFIED = "modified"

@dataclass
class ConversationContext:
    """Comprehensive conversation context"""
    session_id: str
    guest_id: Optional[str] = None
    state: ConversationState = ConversationState.INITIAL
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Intent tracking
    current_intent: Optional[IntentType] = None
    intent_history: List[IntentType] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    
    # Entity tracking
    entities: Dict[str, List[ExtractedEntity]] = field(default_factory=dict)
    confirmed_entities: Dict[str, Any] = field(default_factory=dict)
    
    # Reservation context
    reservation_context: Dict[str, Any] = field(default_factory=dict)
    reservation_status: ReservationStatus = ReservationStatus.INQUIRY
    
    # Conversation metadata
    message_count: int = 0
    sentiment_score: float = 0.0
    urgency_level: str = "normal"
    language: str = "es"
    
    # Missing information tracking
    required_fields: Set[str] = field(default_factory=set)
    missing_fields: Set[str] = field(default_factory=set)
    
    # Conversation flow
    next_expected_intent: Optional[IntentType] = None
    clarification_needed: List[str] = field(default_factory=list)

@dataclass
class EntitySlot:
    """Represents a slot for entity information"""
    name: str
    entity_type: EntityType
    required: bool
    value: Optional[Any] = None
    confidence: float = 0.0
    confirmed: bool = False
    prompt_message: str = ""
    validation_rules: List[str] = field(default_factory=list)

class HotelContextProcessor:
    """Advanced context processor for hotel conversations"""
    
    def __init__(self):
        self.active_contexts: Dict[str, ConversationContext] = {}
        self.context_timeout = 3600  # 1 hour
        
        # Define entity slots for different intents
        self.intent_slots = self._initialize_intent_slots()
        
        # Hotel-specific business rules
        self.business_rules = self._initialize_business_rules()
        
        logger.info("HotelContextProcessor initialized")
    
    def _initialize_intent_slots(self) -> Dict[IntentType, List[EntitySlot]]:
        """Initialize entity slots for each intent type"""
        slots = {
            IntentType.BOOK_ROOM: [
                EntitySlot("checkin_date", EntityType.DATE, True, 
                          prompt_message="¿Para qué fecha necesita la habitación?"),
                EntitySlot("checkout_date", EntityType.DATE, True,
                          prompt_message="¿Hasta qué fecha se quedará?"),
                EntitySlot("guest_count", EntityType.GUEST_COUNT, True,
                          prompt_message="¿Para cuántas personas?"),
                EntitySlot("room_type", EntityType.ROOM_TYPE, False,
                          prompt_message="¿Qué tipo de habitación prefiere?"),
                EntitySlot("guest_name", EntityType.GUEST_NAME, True,
                          prompt_message="¿A nombre de quién será la reserva?")
            ],
            
            IntentType.CHECK_AVAILABILITY: [
                EntitySlot("checkin_date", EntityType.DATE, True,
                          prompt_message="¿Para qué fecha consulta disponibilidad?"),
                EntitySlot("checkout_date", EntityType.DATE, False,
                          prompt_message="¿Hasta qué fecha?"),
                EntitySlot("guest_count", EntityType.GUEST_COUNT, False,
                          prompt_message="¿Para cuántas personas?"),
                EntitySlot("room_type", EntityType.ROOM_TYPE, False,
                          prompt_message="¿Algún tipo de habitación en particular?")
            ],
            
            IntentType.ROOM_SERVICE: [
                EntitySlot("service_type", EntityType.SERVICE_TYPE, True,
                          prompt_message="¿Qué servicio necesita?"),
                EntitySlot("room_number", EntityType.ROOM_NUMBER, True,
                          prompt_message="¿Cuál es su número de habitación?"),
                EntitySlot("time", EntityType.TIME, False,
                          prompt_message="¿A qué hora lo necesita?")
            ],
            
            IntentType.MODIFY_RESERVATION: [
                EntitySlot("guest_name", EntityType.GUEST_NAME, True,
                          prompt_message="¿A nombre de quién está la reserva?"),
                EntitySlot("checkin_date", EntityType.DATE, False,
                          prompt_message="¿Cuál era la fecha original?")
            ],
            
            IntentType.CANCEL_RESERVATION: [
                EntitySlot("guest_name", EntityType.GUEST_NAME, True,
                          prompt_message="¿A nombre de quién está la reserva?"),
                EntitySlot("checkin_date", EntityType.DATE, False,
                          prompt_message="¿Para qué fecha era la reserva?")
            ]
        }
        
        return slots
    
    def _initialize_business_rules(self) -> Dict[str, Any]:
        """Initialize hotel business rules"""
        return {
            "min_stay_nights": 1,
            "max_stay_nights": 30,
            "max_advance_booking_days": 365,
            "min_advance_booking_hours": 2,
            "max_guests_per_room": {
                "single": 1,
                "doble": 2,
                "suite": 4,
                "familiar": 6
            },
            "checkin_time": "15:00",
            "checkout_time": "12:00",
            "room_service_hours": {
                "start": "06:00",
                "end": "23:00"
            }
        }
    
    async def process_prediction(self, session_id: str, prediction: IntentPrediction, 
                               message_text: str) -> Dict[str, Any]:
        """Process intent prediction and update conversation context"""
        
        # Get or create context
        context = self.get_or_create_context(session_id)
        
        # Update basic context
        context.last_updated = datetime.now()
        context.message_count += 1
        context.intent_history.append(prediction.intent)
        context.confidence_scores.append(prediction.confidence)
        context.current_intent = prediction.intent
        
        # Process entities
        self._process_entities(context, prediction.entities)
        
        # Update conversation state
        self._update_conversation_state(context, prediction)
        
        # Analyze what information is still needed
        missing_info = self._analyze_missing_information(context)
        
        # Generate next steps
        next_steps = self._generate_next_steps(context, missing_info)
        
        # Update sentiment and urgency
        self._update_sentiment_urgency(context, message_text)
        
        # Business rule validation
        validation_results = self._validate_business_rules(context)
        
        return {
            "context": context,
            "missing_information": missing_info,
            "next_steps": next_steps,
            "validation_results": validation_results,
            "conversation_complete": self._is_conversation_complete(context),
            "requires_escalation": self._requires_escalation(context)
        }
    
    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id in self.active_contexts:
            return self.active_contexts[session_id]
        
        context = ConversationContext(session_id=session_id)
        self.active_contexts[session_id] = context
        return context
    
    def _process_entities(self, context: ConversationContext, entities: List[ExtractedEntity]):
        """Process and store extracted entities"""
        for entity in entities:
            entity_type_key = entity.entity_type.value
            
            if entity_type_key not in context.entities:
                context.entities[entity_type_key] = []
            
            # Check if this entity already exists (avoid duplicates)
            existing = False
            for existing_entity in context.entities[entity_type_key]:
                if (existing_entity.text.lower() == entity.text.lower() and
                    abs(existing_entity.confidence - entity.confidence) < 0.1):
                    existing = True
                    break
            
            if not existing:
                context.entities[entity_type_key].append(entity)
                
                # Auto-confirm high-confidence entities
                if entity.confidence > 0.8:
                    context.confirmed_entities[entity_type_key] = entity.normalized_value or entity.text
        
        # Special processing for reservation-related entities
        self._process_reservation_entities(context)
    
    def _process_reservation_entities(self, context: ConversationContext):
        """Special processing for reservation-related entities"""
        # Check if we have date entities and process them
        if "date" in context.entities:
            dates = [e for e in context.entities["date"] if e.normalized_value]
            dates.sort(key=lambda x: x.normalized_value)
            
            if len(dates) >= 2:
                context.reservation_context["checkin_date"] = dates[0].normalized_value
                context.reservation_context["checkout_date"] = dates[1].normalized_value
            elif len(dates) == 1:
                # Assume it's check-in date
                context.reservation_context["checkin_date"] = dates[0].normalized_value
        
        # Process guest count
        if "guest_count" in context.entities:
            guest_counts = [e for e in context.entities["guest_count"] if e.normalized_value]
            if guest_counts:
                context.reservation_context["guest_count"] = max(e.normalized_value for e in guest_counts)
        
        # Process room type
        if "room_type" in context.entities:
            room_types = context.entities["room_type"]
            if room_types:
                context.reservation_context["room_type"] = room_types[-1].text  # Use most recent
        
        # Process guest name
        if "guest_name" in context.entities:
            names = context.entities["guest_name"]
            if names:
                context.reservation_context["guest_name"] = names[-1].text
    
    def _update_conversation_state(self, context: ConversationContext, prediction: IntentPrediction):
        """Update conversation state based on intent and context"""
        intent = prediction.intent
        
        if context.state == ConversationState.INITIAL:
            if intent in [IntentType.GREETING, IntentType.CHITCHAT]:
                context.state = ConversationState.INITIAL
            else:
                context.state = ConversationState.COLLECTING_INFO
        
        elif context.state == ConversationState.COLLECTING_INFO:
            if self._has_sufficient_info(context, intent):
                context.state = ConversationState.CONFIRMING
            elif intent == IntentType.COMPLAINT or intent == IntentType.EMERGENCY:
                context.state = ConversationState.ESCALATED
        
        elif context.state == ConversationState.CONFIRMING:
            if intent in [IntentType.GREETING, IntentType.CHITCHAT]:  # Confirmation words
                context.state = ConversationState.PROCESSING
        
        # Update reservation status
        if intent in [IntentType.BOOK_ROOM, IntentType.CHECK_AVAILABILITY]:
            if context.reservation_status == ReservationStatus.INQUIRY:
                context.reservation_status = ReservationStatus.PARTIAL_INFO
            
            if self._has_sufficient_reservation_info(context):
                context.reservation_status = ReservationStatus.READY_TO_BOOK
    
    def _analyze_missing_information(self, context: ConversationContext) -> Dict[str, List[str]]:
        """Analyze what information is still needed"""
        missing_info = {
            "required_entities": [],
            "clarifications_needed": [],
            "business_rule_violations": []
        }
        
        if context.current_intent and context.current_intent in self.intent_slots:
            required_slots = self.intent_slots[context.current_intent]
            
            for slot in required_slots:
                if slot.required:
                    entity_key = slot.entity_type.value
                    
                    if (entity_key not in context.confirmed_entities and
                        entity_key not in context.entities):
                        missing_info["required_entities"].append({
                            "entity": entity_key,
                            "prompt": slot.prompt_message
                        })
        
        # Check for date logic issues
        if ("checkin_date" in context.reservation_context and 
            "checkout_date" in context.reservation_context):
            
            checkin = context.reservation_context["checkin_date"]
            checkout = context.reservation_context["checkout_date"]
            
            if isinstance(checkin, date) and isinstance(checkout, date):
                if checkout <= checkin:
                    missing_info["clarifications_needed"].append(
                        "La fecha de salida debe ser posterior a la fecha de entrada"
                    )
        
        return missing_info
    
    def _generate_next_steps(self, context: ConversationContext, 
                           missing_info: Dict[str, List[str]]) -> List[str]:
        """Generate next steps for the conversation"""
        next_steps = []
        
        # Handle missing required information
        if missing_info["required_entities"]:
            next_entity = missing_info["required_entities"][0]
            next_steps.append(f"ask_for_{next_entity['entity']}")
        
        # Handle clarifications
        if missing_info["clarifications_needed"]:
            next_steps.append("request_clarification")
        
        # Handle business rule violations
        if missing_info["business_rule_violations"]:
            next_steps.append("explain_business_rules")
        
        # Handle state-specific next steps
        if context.state == ConversationState.CONFIRMING:
            next_steps.append("request_confirmation")
        elif context.state == ConversationState.PROCESSING:
            next_steps.append("process_request")
        elif context.state == ConversationState.ESCALATED:
            next_steps.append("escalate_to_human")
        
        return next_steps
    
    def _update_sentiment_urgency(self, context: ConversationContext, message_text: str):
        """Update sentiment and urgency based on message content"""
        # Simple sentiment analysis
        negative_words = ["problema", "mal", "terrible", "horrible", "no funciona", "molesto"]
        positive_words = ["excelente", "perfecto", "genial", "fantástico", "gracias"]
        urgency_words = ["urgente", "emergencia", "rápido", "ya", "inmediatamente"]
        
        message_lower = message_text.lower()
        
        # Update sentiment
        negative_count = sum(1 for word in negative_words if word in message_lower)
        positive_count = sum(1 for word in positive_words if word in message_lower)
        
        if negative_count > positive_count:
            context.sentiment_score = max(context.sentiment_score - 0.2, -1.0)
        elif positive_count > negative_count:
            context.sentiment_score = min(context.sentiment_score + 0.2, 1.0)
        
        # Update urgency
        if any(word in message_lower for word in urgency_words):
            context.urgency_level = "high"
        elif context.sentiment_score < -0.5:
            context.urgency_level = "medium"
    
    def _validate_business_rules(self, context: ConversationContext) -> Dict[str, Any]:
        """Validate against hotel business rules"""
        violations = []
        warnings = []
        
        reservation = context.reservation_context
        
        # Date validations
        if "checkin_date" in reservation and "checkout_date" in reservation:
            checkin = reservation["checkin_date"]
            checkout = reservation["checkout_date"]
            
            if isinstance(checkin, date) and isinstance(checkout, date):
                # Check stay duration
                stay_nights = (checkout - checkin).days
                if stay_nights < self.business_rules["min_stay_nights"]:
                    violations.append(f"Mínimo {self.business_rules['min_stay_nights']} noche(s)")
                elif stay_nights > self.business_rules["max_stay_nights"]:
                    violations.append(f"Máximo {self.business_rules['max_stay_nights']} noches")
                
                # Check advance booking
                days_advance = (checkin - date.today()).days
                if days_advance > self.business_rules["max_advance_booking_days"]:
                    violations.append("No se puede reservar con tanta anticipación")
                elif days_advance < 0:
                    violations.append("No se puede reservar para fechas pasadas")
        
        # Guest count validation
        if "guest_count" in reservation and "room_type" in reservation:
            guest_count = reservation["guest_count"]
            room_type = reservation["room_type"].lower()
            
            max_guests = self.business_rules["max_guests_per_room"].get(room_type)
            if max_guests and guest_count > max_guests:
                violations.append(f"Habitación {room_type} máximo {max_guests} huéspedes")
        
        return {
            "violations": violations,
            "warnings": warnings,
            "valid": len(violations) == 0
        }
    
    def _has_sufficient_info(self, context: ConversationContext, intent: IntentType) -> bool:
        """Check if we have sufficient information for the intent"""
        if intent not in self.intent_slots:
            return True
        
        required_slots = [slot for slot in self.intent_slots[intent] if slot.required]
        
        for slot in required_slots:
            entity_key = slot.entity_type.value
            if (entity_key not in context.confirmed_entities and
                entity_key not in context.entities):
                return False
        
        return True
    
    def _has_sufficient_reservation_info(self, context: ConversationContext) -> bool:
        """Check if we have sufficient information for a reservation"""
        required_fields = ["checkin_date", "guest_count", "guest_name"]
        
        for field in required_fields:
            if (field not in context.reservation_context and
                field not in context.confirmed_entities):
                return False
        
        return True
    
    def _is_conversation_complete(self, context: ConversationContext) -> bool:
        """Check if conversation is complete"""
        return context.state in [ConversationState.COMPLETED, ConversationState.PROCESSING]
    
    def _requires_escalation(self, context: ConversationContext) -> bool:
        """Check if conversation requires human escalation"""
        return (context.state == ConversationState.ESCALATED or
                context.urgency_level == "high" or
                context.sentiment_score < -0.7 or
                context.message_count > 20)
    
    async def cleanup_expired_contexts(self):
        """Clean up expired conversation contexts"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            time_diff = current_time - context.last_updated
            if time_diff.seconds > self.context_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_contexts[session_id]
            logger.info(f"Cleaned up expired context for session {session_id}")
    
    def get_context_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the conversation context"""
        if session_id not in self.active_contexts:
            return None
        
        context = self.active_contexts[session_id]
        
        return {
            "session_id": session_id,
            "state": context.state.value,
            "current_intent": context.current_intent.value if context.current_intent else None,
            "message_count": context.message_count,
            "sentiment_score": context.sentiment_score,
            "urgency_level": context.urgency_level,
            "reservation_status": context.reservation_status.value,
            "confirmed_entities": context.confirmed_entities,
            "reservation_context": context.reservation_context,
            "created_at": context.created_at.isoformat(),
            "last_updated": context.last_updated.isoformat()
        }

# Global instance
_context_processor = None

def get_context_processor() -> HotelContextProcessor:
    """Get global context processor instance"""
    global _context_processor
    if _context_processor is None:
        _context_processor = HotelContextProcessor()
    return _context_processor