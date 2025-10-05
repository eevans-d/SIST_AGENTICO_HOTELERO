# [PROMPT 2.5 + E.3] app/services/nlp_engine.py
"""
NLP Engine with Rasa Agent Integration
Replaces mock implementation with trained DIET classifier model.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from prometheus_client import Counter, Gauge, Histogram
from ..core.circuit_breaker import CircuitBreaker
from ..exceptions.pms_exceptions import CircuitBreakerOpenError
from ..core.logging import logger

# Metrics
nlp_operations = Counter("nlp_operations_total", "NLP operations", ["operation", "status"])
nlp_errors = Counter("nlp_errors_total", "NLP errors", ["operation", "error_type"])
nlp_circuit_breaker_state = Gauge("nlp_circuit_breaker_state", "NLP circuit breaker state (0=closed, 1=open, 2=half-open)")
nlp_circuit_breaker_calls = Counter("nlp_circuit_breaker_calls_total", "NLP circuit breaker calls", ["state", "result"])
nlp_confidence = Histogram("nlp_confidence_score", "NLP confidence score distribution", buckets=[0.3, 0.5, 0.7, 0.85, 0.95, 1.0])
nlp_intent_predictions = Counter("nlp_intent_predictions_total", "Intent predictions", ["intent", "confidence_bucket"])


class NLPEngine:
    """
    NLP Engine powered by Rasa DIET Classifier.
    
    Features:
    - Loads trained Rasa model from disk
    - Intent classification with confidence scores
    - Entity extraction (dates, numbers, room types, amenities)
    - Circuit breaker for resilience
    - In-memory agent caching
    - Model versioning support
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize NLP Engine with Rasa model.
        
        Args:
            model_path: Path to .tar.gz Rasa model file. If None, loads from default location.
        """
        # Circuit breaker for NLP calls
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
        nlp_circuit_breaker_state.set(0)  # 0 = closed
        
        # Model configuration
        self.model_path = model_path or self._resolve_model_path()
        self.agent = None
        self.model_version = None
        self.model_loaded_at: Optional[datetime] = None
        
        # Load model at initialization
        self._load_model()
    
    def _resolve_model_path(self) -> str:
        """
        Resolve Rasa model path from environment or default location.
        
        Priority:
        1. RASA_MODEL_PATH env variable
        2. rasa_nlu/models/latest.tar.gz (symlink to latest trained model)
        3. Fallback to mock mode if no model found
        """
        # Check environment variable
        env_path = os.getenv("RASA_MODEL_PATH")
        if env_path and Path(env_path).exists():
            logger.info(f"Using Rasa model from RASA_MODEL_PATH: {env_path}")
            return env_path
        
        # Check default location (symlink created by train_rasa.sh)
        project_root = Path(__file__).parent.parent.parent
        default_path = project_root / "rasa_nlu" / "models" / "latest.tar.gz"
        
        if default_path.exists():
            logger.info(f"Using Rasa model from default location: {default_path}")
            return str(default_path)
        
        # No model found - will use fallback mode
        logger.warning(
            "No Rasa model found. NLP engine will run in fallback mode. "
            "Train a model with: scripts/train_rasa.sh"
        )
        return ""
    
    def _load_model(self):
        """Load Rasa Agent from model file."""
        if not self.model_path:
            logger.warning("No model path configured, running in fallback mode")
            return
        
        try:
            from rasa.core.agent import Agent
            
            logger.info(f"Loading Rasa model from: {self.model_path}")
            self.agent = Agent.load(self.model_path)
            
            # Extract model version from filename
            # Example: hotel_nlu_20240115_143022.tar.gz → 20240115_143022
            model_filename = Path(self.model_path).stem
            if "_" in model_filename:
                self.model_version = "_".join(model_filename.split("_")[-2:])
            else:
                self.model_version = "unknown"
            
            self.model_loaded_at = datetime.utcnow()
            
            logger.info(
                f"Rasa model loaded successfully",
                extra={
                    "model_version": self.model_version,
                    "model_path": self.model_path,
                    "loaded_at": self.model_loaded_at.isoformat()
                }
            )
            
        except ImportError:
            logger.error(
                "Rasa not installed. Install with: pip install rasa"
            )
            self.agent = None
        except Exception as e:
            logger.error(
                f"Failed to load Rasa model: {e}",
                exc_info=True,
                extra={"model_path": self.model_path}
            )
            self.agent = None

    async def process_message(self, text: str) -> Dict[str, Any]:
        """
        Process text message to extract intent and entities.
        
        Args:
            text: User message in Spanish
        
        Returns:
            dict with structure:
            {
                "intent": {"name": str, "confidence": float},
                "entities": [{"entity": str, "value": str, "start": int, "end": int}],
                "text": str,
                "model_version": str,
                "fallback": bool (only if fallback used)
            }
        """
        try:
            result = await self.circuit_breaker.call(self._process_with_retry, text)
            nlp_operations.labels(operation="process_message", status="success").inc()
            
            # Record metrics
            confidence = result.get("intent", {}).get("confidence", 0.0)
            nlp_confidence.observe(confidence)
            
            # Intent prediction metrics (bucketed by confidence)
            intent_name = result.get("intent", {}).get("name", "unknown")
            confidence_bucket = self._get_confidence_bucket(confidence)
            nlp_intent_predictions.labels(intent=intent_name, confidence_bucket=confidence_bucket).inc()
            
            return result
            
        except CircuitBreakerOpenError:
            # Circuit breaker open: use fallback
            logger.warning("NLP circuit breaker open, using fallback response")
            nlp_circuit_breaker_calls.labels(state="open", result="fallback").inc()
            nlp_circuit_breaker_state.set(1)  # 1 = open
            return self._fallback_response()
            
        except Exception as e:
            # Other errors
            logger.error(f"NLP processing failed: {e}", exc_info=True)
            nlp_operations.labels(operation="process_message", status="error").inc()
            nlp_errors.labels(operation="process_message", error_type=type(e).__name__).inc()
            return self._fallback_response()
    
    async def _process_with_retry(self, text: str) -> Dict[str, Any]:
        """
        Internal processing method with Rasa Agent.
        
        Args:
            text: User message
        
        Returns:
            Parsed message with intent and entities
        """
        # If no agent loaded, use fallback
        if not self.agent:
            logger.warning("No Rasa agent loaded, using fallback")
            return self._fallback_response()
        
        try:
            # Parse message with Rasa
            result = await self.agent.parse_message(message_data=text)
            
            # Normalize result structure
            normalized = {
                "intent": {
                    "name": result.get("intent", {}).get("name", "unknown"),
                    "confidence": result.get("intent", {}).get("confidence", 0.0)
                },
                "entities": self._normalize_entities(result.get("entities", [])),
                "text": text,
                "model_version": self.model_version
            }
            
            return normalized
            
        except Exception as e:
            logger.error(f"Rasa parsing failed: {e}", exc_info=True)
            raise
    
    def _normalize_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize Rasa entities to consistent format.
        
        Args:
            entities: Raw entities from Rasa
        
        Returns:
            Normalized entity list
        """
        normalized = []
        
        for entity in entities:
            normalized.append({
                "entity": entity.get("entity"),
                "value": entity.get("value"),
                "start": entity.get("start"),
                "end": entity.get("end"),
                "confidence": entity.get("confidence_entity", entity.get("confidence", 1.0)),
                "extractor": entity.get("extractor", "unknown")
            })
        
        return normalized
    
    def _fallback_response(self) -> Dict[str, Any]:
        """
        Fallback response when NLP is unavailable.
        
        Returns:
            Response with unknown intent and fallback flag
        """
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": [],
            "fallback": True,
            "text": ""
        }
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """
        Map confidence score to bucket for metrics.
        
        Args:
            confidence: Confidence score (0.0-1.0)
        
        Returns:
            Bucket label: "low", "medium", "high", "very_high"
        """
        if confidence < 0.5:
            return "low"
        elif confidence < 0.7:
            return "medium"
        elif confidence < 0.85:
            return "high"
        else:
            return "very_high"

    def handle_low_confidence(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle low-confidence intent predictions with clarification prompts.
        
        Args:
            intent: Intent dict with name and confidence
        
        Returns:
            dict with response and human handoff flag, or None if confidence is acceptable
        """
        confidence = intent.get("confidence", 0.0)
        
        # Very low confidence (<0.3): escalate to human
        if confidence < 0.3:
            return {
                "response": (
                    "Disculpa, no estoy seguro de entender tu consulta. "
                    "¿Podrías reformularla o te conecto con un representante?"
                ),
                "requires_human": True,
            }
        
        # Low confidence (0.3-0.7): offer menu
        if confidence < 0.7:
            return {
                "response": (
                    "¿En qué puedo ayudarte?\n"
                    "1️⃣ Consultar disponibilidad\n"
                    "2️⃣ Hacer una reserva\n"
                    "3️⃣ Modificar/cancelar reserva\n"
                    "4️⃣ Información del hotel (precios, servicios, ubicación)\n"
                    "5️⃣ Hablar con recepción"
                ),
                "requires_human": False,
            }
        
        # Acceptable confidence (≥0.7): proceed normally
        return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded model.
        
        Returns:
            dict with model metadata
        """
        return {
            "model_path": self.model_path,
            "model_version": self.model_version,
            "model_loaded_at": self.model_loaded_at.isoformat() if self.model_loaded_at else None,
            "agent_loaded": self.agent is not None,
            "fallback_mode": self.agent is None
        }

