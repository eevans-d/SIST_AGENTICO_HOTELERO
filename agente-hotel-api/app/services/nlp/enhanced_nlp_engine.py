"""
Enhanced NLP Engine for Hotel Guest Intent Recognition
Advanced intent classification with hotel-specific entities and context awareness
"""

import asyncio
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge

# Configure logging
logger = logging.getLogger(__name__)

# Prometheus metrics
nlp_intent_predictions_total = Counter(
    "nlp_intent_predictions_total",
    "Total NLP intent predictions",
    ["intent", "confidence_level", "language"]
)

nlp_processing_latency = Histogram(
    "nlp_processing_latency_seconds",
    "NLP processing latency",
    ["operation", "model_type"]
)

nlp_entity_extractions_total = Counter(
    "nlp_entity_extractions_total", 
    "Total entity extractions",
    ["entity_type", "extraction_method"]
)

nlp_cache_hit_rate = Gauge(
    "nlp_cache_hit_rate",
    "NLP cache hit rate"
)

nlp_model_confidence = Gauge(
    "nlp_model_confidence",
    "Average model confidence score"
)

class IntentType(Enum):
    """Hotel-specific intent types"""
    # Reservation intents
    BOOK_ROOM = "book_room"
    CANCEL_RESERVATION = "cancel_reservation"
    MODIFY_RESERVATION = "modify_reservation"
    CHECK_AVAILABILITY = "check_availability"
    
    # Guest services
    ROOM_SERVICE = "room_service"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    MAINTENANCE = "maintenance"
    
    # Information requests
    HOTEL_INFO = "hotel_info"
    AMENITIES = "amenities"
    DIRECTIONS = "directions"
    PRICING = "pricing"
    
    # Check-in/out
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    EARLY_CHECKIN = "early_checkin"
    LATE_CHECKOUT = "late_checkout"
    
    # Complaints and feedback
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    EMERGENCY = "emergency"
    
    # Special requests
    SPECIAL_OCCASION = "special_occasion"
    ACCESSIBILITY = "accessibility"
    DIETARY = "dietary"
    
    # General
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNCLEAR = "unclear"
    CHITCHAT = "chitchat"

class EntityType(Enum):
    """Hotel-specific entity types"""
    # Temporal entities
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    
    # Room entities
    ROOM_TYPE = "room_type"
    ROOM_NUMBER = "room_number"
    FLOOR = "floor"
    
    # Guest entities
    GUEST_NAME = "guest_name"
    GUEST_COUNT = "guest_count"
    
    # Service entities
    SERVICE_TYPE = "service_type"
    AMENITY = "amenity"
    
    # Location entities
    LOCATION = "location"
    RESTAURANT = "restaurant"
    
    # Pricing entities
    PRICE = "price"
    CURRENCY = "currency"

@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    normalized_value: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class IntentPrediction:
    """Represents an intent prediction result"""
    intent: IntentType
    confidence: float
    entities: List[ExtractedEntity] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    language: str = "es"
    processing_time: float = 0.0
    model_version: str = "1.0.0"

class HotelNLPEngine:
    """Advanced NLP engine for hotel guest communications"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.nlp_model = None
        self.intent_classifier = None
        self.matcher = None
        self.tokenizer = None
        
        # Hotel-specific patterns and rules
        self.room_types = {
            "single", "doble", "suite", "presidencial", "deluxe", "standard",
            "junior", "familiar", "matrimonial", "individual", "twin"
        }
        
        self.amenities = {
            "piscina", "spa", "gimnasio", "restaurante", "bar", "wifi",
            "estacionamiento", "aire acondicionado", "minibar", "jacuzzi",
            "balcón", "vista al mar", "room service", "lavandería"
        }
        
        self.services = {
            "limpieza", "toallas", "sábanas", "comida", "bebidas", "taxi",
            "despertador", "plancha", "secador", "champú", "jabón"
        }
        
        # Intent patterns for quick classification
        self.intent_patterns = {
            IntentType.BOOK_ROOM: [
                r"quiero.*reserv", r"reservar.*habitación", r"hacer.*reserva",
                r"disponibilidad", r"necesito.*cuarto", r"book.*room"
            ],
            IntentType.CANCEL_RESERVATION: [
                r"cancel.*reserva", r"anular.*reserva", r"eliminar.*reserva"
            ],
            IntentType.ROOM_SERVICE: [
                r"room.*service", r"servicio.*habitación", r"pedir.*comida",
                r"quiero.*comer", r"menú"
            ],
            IntentType.CHECK_IN: [
                r"check.*in", r"registr", r"llegada", r"entrada"
            ],
            IntentType.CHECK_OUT: [
                r"check.*out", r"salida", r"cuenta", r"factura"
            ],
            IntentType.COMPLAINT: [
                r"problema", r"queja", r"molest", r"reclam", r"no.*funciona"
            ]
        }
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("HotelNLPEngine initialized")
    
    async def initialize(self):
        """Initialize NLP models and components"""
        logger.info("🧠 Initializing NLP Engine components...")
        
        try:
            # Load spaCy model for Spanish
            self.nlp_model = spacy.load("es_core_news_sm")
            
            # Initialize intent classifier (using multilingual model)
            self.intent_classifier = pipeline(
                "text-classification",
                model="microsoft/DialoGPT-medium",
                tokenizer="microsoft/DialoGPT-medium",
                device=-1  # CPU
            )
            
            # Initialize custom matcher for hotel entities
            self.matcher = Matcher(self.nlp_model.vocab)
            self._setup_entity_patterns()
            
            logger.info("✅ NLP Engine components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize NLP Engine: {e}")
            raise
    
    def _setup_entity_patterns(self):
        """Setup entity matching patterns"""
        # Room type patterns
        room_patterns = []
        for room_type in self.room_types:
            room_patterns.append([{"LOWER": room_type}])
            room_patterns.append([{"LOWER": "habitación"}, {"LOWER": room_type}])
            room_patterns.append([{"LOWER": "cuarto"}, {"LOWER": room_type}])
        
        self.matcher.add("ROOM_TYPE", room_patterns)
        
        # Date patterns
        date_patterns = [
            [{"TEXT": {"REGEX": r"\d{1,2}\/\d{1,2}\/\d{4}"}}],
            [{"TEXT": {"REGEX": r"\d{1,2}-\d{1,2}-\d{4}"}}],
            [{"LOWER": {"IN": ["hoy", "mañana", "pasado"]}},
             {"LOWER": {"IN": ["mañana", "", ""]}}],
        ]
        self.matcher.add("DATE", date_patterns)
        
        # Price patterns
        price_patterns = [
            [{"TEXT": {"REGEX": r"\$\d+"}},],
            [{"TEXT": {"REGEX": r"\d+"}}, {"LOWER": {"IN": ["pesos", "dolares", "euros"]}}],
        ]
        self.matcher.add("PRICE", price_patterns)
        
        logger.info("Entity patterns configured")
    
    async def predict_intent(self, text: str, context: Optional[Dict] = None) -> IntentPrediction:
        """Predict intent from text with context awareness"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            
            # Check cache first
            cache_key = f"nlp:intent:{hash(cleaned_text)}"
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                self.cache_hits += 1
                nlp_cache_hit_rate.set(self.cache_hits / (self.cache_hits + self.cache_misses))
                return IntentPrediction(**cached_result)
            
            self.cache_misses += 1
            
            # Rule-based classification first (faster)
            rule_intent = self._classify_with_rules(cleaned_text)
            
            # Extract entities
            entities = await self._extract_entities(cleaned_text)
            
            # If rule-based is confident, use it
            if rule_intent[1] > 0.8:
                intent_pred = IntentPrediction(
                    intent=rule_intent[0],
                    confidence=rule_intent[1],
                    entities=entities,
                    context=context or {},
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            else:
                # Use ML model for complex cases
                ml_intent = await self._classify_with_ml(cleaned_text, context)
                intent_pred = IntentPrediction(
                    intent=ml_intent[0],
                    confidence=ml_intent[1], 
                    entities=entities,
                    context=context or {},
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Cache result
            await self._cache_result(cache_key, intent_pred)
            
            # Update metrics
            confidence_level = "high" if intent_pred.confidence > 0.8 else "medium" if intent_pred.confidence > 0.5 else "low"
            nlp_intent_predictions_total.labels(
                intent=intent_pred.intent.value,
                confidence_level=confidence_level,
                language=intent_pred.language
            ).inc()
            
            nlp_processing_latency.labels(
                operation="intent_prediction",
                model_type="hybrid"
            ).observe(intent_pred.processing_time)
            
            nlp_model_confidence.set(intent_pred.confidence)
            
            logger.info(f"Intent predicted: {intent_pred.intent.value} (confidence: {intent_pred.confidence:.3f})")
            return intent_pred
            
        except Exception as e:
            logger.error(f"Error predicting intent: {e}")
            # Return fallback intent
            return IntentPrediction(
                intent=IntentType.UNCLEAR,
                confidence=0.0,
                processing_time=asyncio.get_event_loop().time() - start_time,
                context={"error": str(e)}
            )
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess input text"""
        # Basic cleaning
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize common hotel terms
        replacements = {
            'habitacion': 'habitación',
            'reservacion': 'reservación',
            'informacion': 'información',
            'atencion': 'atención'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _classify_with_rules(self, text: str) -> Tuple[IntentType, float]:
        """Fast rule-based intent classification"""
        best_intent = IntentType.UNCLEAR
        max_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
                    score += 1.0 / len(patterns)
            
            # Boost score if multiple patterns match
            if matches > 1:
                score *= 1.2
            
            # Context boosting
            if intent == IntentType.BOOK_ROOM and any(word in text for word in ['disponible', 'libre', 'vacante']):
                score *= 1.1
            
            if score > max_score:
                max_score = score
                best_intent = intent
        
        # Normalize confidence
        confidence = min(max_score, 1.0)
        
        return best_intent, confidence
    
    async def _classify_with_ml(self, text: str, context: Optional[Dict] = None) -> Tuple[IntentType, float]:
        """ML-based intent classification"""
        try:
            # For now, use a simple heuristic approach
            # In production, this would use a fine-tuned transformer model
            
            # Analyze text features
            doc = self.nlp_model(text)
            
            # Feature extraction
            features = {
                'has_question': '?' in text,
                'has_reservation_words': any(word in text for word in ['reserva', 'book', 'disponible']),
                'has_service_words': any(word in text for word in ['servicio', 'room service', 'comida']),
                'has_complaint_words': any(word in text for word in ['problema', 'queja', 'no funciona']),
                'has_greeting_words': any(word in text for word in ['hola', 'buenos', 'buenas']),
                'sentence_length': len(doc),
                'has_numbers': any(token.like_num for token in doc)
            }
            
            # Simple decision tree logic
            if features['has_greeting_words']:
                return IntentType.GREETING, 0.9
            elif features['has_complaint_words']:
                return IntentType.COMPLAINT, 0.85
            elif features['has_reservation_words']:
                if features['has_question']:
                    return IntentType.CHECK_AVAILABILITY, 0.8
                else:
                    return IntentType.BOOK_ROOM, 0.8
            elif features['has_service_words']:
                return IntentType.ROOM_SERVICE, 0.75
            else:
                return IntentType.UNCLEAR, 0.3
                
        except Exception as e:
            logger.error(f"ML classification error: {e}")
            return IntentType.UNCLEAR, 0.0
    
    async def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text"""
        entities = []
        
        try:
            # Process with spaCy
            doc = self.nlp_model(text)
            
            # Use custom matcher
            matches = self.matcher(doc)
            
            for match_id, start, end in matches:
                span = doc[start:end]
                label = self.nlp_model.vocab.strings[match_id]
                
                entity_type = self._label_to_entity_type(label)
                if entity_type:
                    entity = ExtractedEntity(
                        text=span.text,
                        entity_type=entity_type,
                        confidence=0.9,  # High confidence for rule-based
                        start_pos=span.start_char,
                        end_pos=span.end_char,
                        normalized_value=self._normalize_entity_value(span.text, entity_type)
                    )
                    entities.append(entity)
                    
                    nlp_entity_extractions_total.labels(
                        entity_type=entity_type.value,
                        extraction_method="rule_based"
                    ).inc()
            
            # Extract spaCy named entities
            for ent in doc.ents:
                entity_type = self._spacy_label_to_entity_type(ent.label_)
                if entity_type:
                    entity = ExtractedEntity(
                        text=ent.text,
                        entity_type=entity_type,
                        confidence=0.7,  # Medium confidence for spaCy
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        normalized_value=self._normalize_entity_value(ent.text, entity_type)
                    )
                    entities.append(entity)
                    
                    nlp_entity_extractions_total.labels(
                        entity_type=entity_type.value,
                        extraction_method="spacy_ner"
                    ).inc()
        
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
        
        return entities
    
    def _label_to_entity_type(self, label: str) -> Optional[EntityType]:
        """Convert matcher label to EntityType"""
        mapping = {
            "ROOM_TYPE": EntityType.ROOM_TYPE,
            "DATE": EntityType.DATE,
            "PRICE": EntityType.PRICE
        }
        return mapping.get(label)
    
    def _spacy_label_to_entity_type(self, label: str) -> Optional[EntityType]:
        """Convert spaCy label to EntityType"""
        mapping = {
            "PER": EntityType.GUEST_NAME,
            "MONEY": EntityType.PRICE,
            "TIME": EntityType.TIME,
            "DATE": EntityType.DATE,
            "LOC": EntityType.LOCATION,
            "ORG": EntityType.RESTAURANT
        }
        return mapping.get(label)
    
    def _normalize_entity_value(self, text: str, entity_type: EntityType) -> Any:
        """Normalize entity values"""
        try:
            if entity_type == EntityType.DATE:
                # Basic date parsing
                if re.match(r'\d{1,2}\/\d{1,2}\/\d{4}', text):
                    return datetime.strptime(text, '%d/%m/%Y').date()
                elif text.lower() == 'hoy':
                    return datetime.now().date()
                elif text.lower() == 'mañana':
                    return (datetime.now() + timedelta(days=1)).date()
            
            elif entity_type == EntityType.PRICE:
                # Extract numeric value
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return float(numbers[0])
            
            elif entity_type == EntityType.GUEST_COUNT:
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
        
        except Exception as e:
            logger.error(f"Error normalizing entity '{text}': {e}")
        
        return text  # Return original if normalization fails
    
    async def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get result from cache"""
        if not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def _cache_result(self, key: str, result: IntentPrediction):
        """Cache prediction result"""
        if not self.redis_client:
            return
        
        try:
            # Convert to dict for JSON serialization
            result_dict = {
                'intent': result.intent.value,
                'confidence': result.confidence,
                'entities': [
                    {
                        'text': e.text,
                        'entity_type': e.entity_type.value,
                        'confidence': e.confidence,
                        'start_pos': e.start_pos,
                        'end_pos': e.end_pos,
                        'normalized_value': e.normalized_value
                    }
                    for e in result.entities
                ],
                'context': result.context,
                'language': result.language,
                'processing_time': result.processing_time,
                'model_version': result.model_version
            }
            
            await self.redis_client.setex(
                key, 
                self.cache_ttl, 
                json.dumps(result_dict, default=str)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def get_similar_intents(self, text: str, top_k: int = 3) -> List[Tuple[IntentType, float]]:
        """Get top-k similar intents for ambiguous cases"""
        similar_intents = []
        
        for intent_type in IntentType:
            # Calculate similarity score
            score = self._calculate_intent_similarity(text, intent_type)
            similar_intents.append((intent_type, score))
        
        # Sort by score and return top-k
        similar_intents.sort(key=lambda x: x[1], reverse=True)
        return similar_intents[:top_k]
    
    def _calculate_intent_similarity(self, text: str, intent_type: IntentType) -> float:
        """Calculate similarity between text and intent type"""
        # Simple keyword-based similarity
        patterns = self.intent_patterns.get(intent_type, [])
        total_score = 0.0
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                total_score += 1.0
        
        return total_score / len(patterns) if patterns else 0.0
    
    async def analyze_conversation_context(self, messages: List[str]) -> Dict[str, Any]:
        """Analyze conversation context for better intent prediction"""
        context = {
            'conversation_length': len(messages),
            'dominant_intents': [],
            'extracted_entities': [],
            'sentiment': 'neutral',
            'urgency': 'normal'
        }
        
        intent_counts = {}
        all_entities = []
        
        for message in messages[-5:]:  # Analyze last 5 messages
            prediction = await self.predict_intent(message)
            
            # Count intents
            intent_key = prediction.intent.value
            intent_counts[intent_key] = intent_counts.get(intent_key, 0) + 1
            
            # Collect entities
            all_entities.extend(prediction.entities)
        
        # Determine dominant intents
        context['dominant_intents'] = sorted(
            intent_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        context['extracted_entities'] = all_entities
        
        # Simple sentiment analysis
        last_message = messages[-1] if messages else ""
        if any(word in last_message.lower() for word in ['problema', 'mal', 'terrible', 'horrible']):
            context['sentiment'] = 'negative'
        elif any(word in last_message.lower() for word in ['excelente', 'perfecto', 'genial', 'fantástico']):
            context['sentiment'] = 'positive'
        
        # Urgency detection
        if any(word in last_message.lower() for word in ['urgente', 'emergencia', 'rápido', 'ya']):
            context['urgency'] = 'high'
        
        return context
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for NLP engine"""
        health_status = {
            'status': 'healthy',
            'components': {},
            'metrics': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Check spaCy model
            if self.nlp_model:
                test_doc = self.nlp_model("test")
                health_status['components']['spacy_model'] = 'ok'
            else:
                health_status['components']['spacy_model'] = 'not_loaded'
                health_status['status'] = 'degraded'
            
            # Check cache connection
            if self.redis_client:
                await self.redis_client.ping()
                health_status['components']['redis_cache'] = 'ok'
            else:
                health_status['components']['redis_cache'] = 'not_configured'
            
            # Include performance metrics
            cache_total = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / cache_total if cache_total > 0 else 0
            
            health_status['metrics'] = {
                'cache_hit_rate': hit_rate,
                'total_predictions': cache_total,
                'average_confidence': 0.85  # Would be calculated from recent predictions
            }
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status

# Factory function
async def create_nlp_engine(redis_client: Optional[redis.Redis] = None) -> HotelNLPEngine:
    """Create and initialize NLP engine"""
    engine = HotelNLPEngine(redis_client)
    await engine.initialize()
    return engine