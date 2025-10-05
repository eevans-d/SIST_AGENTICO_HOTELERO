# [PROMPT 2.5] app/services/nlp_engine.py

from typing import Optional
from prometheus_client import Counter, Gauge
from ..core.circuit_breaker import CircuitBreaker
from ..exceptions.pms_exceptions import CircuitBreakerOpenError
from ..core.logging import logger

# Metrics
nlp_operations = Counter("nlp_operations_total", "NLP operations", ["operation", "status"])
nlp_errors = Counter("nlp_errors_total", "NLP errors", ["operation", "error_type"])
nlp_circuit_breaker_state = Gauge("nlp_circuit_breaker_state", "NLP circuit breaker state (0=closed, 1=open, 2=half-open)")
nlp_circuit_breaker_calls = Counter("nlp_circuit_breaker_calls_total", "NLP circuit breaker calls", ["state", "result"])


class NLPEngine:
    def __init__(self, model_path: Optional[str] = None):
        # Circuit breaker for NLP calls
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
        # Initialize circuit breaker state metric
        nlp_circuit_breaker_state.set(0)  # 0 = closed
        
        # self.agent = Agent.load(model_path) if model_path else None
        pass

    async def process_message(self, text: str) -> dict:
        """
        Procesa un mensaje de texto para extraer intent y entidades.
        
        Usa circuit breaker para resilience. Si el circuit breaker está abierto,
        devuelve un fallback con intent desconocido de baja confianza.
        """
        try:
            result = await self.circuit_breaker.call(self._process_with_retry, text)
            nlp_operations.labels(operation="process_message", status="success").inc()
            return result
        except CircuitBreakerOpenError:
            # Circuit breaker open: use fallback
            logger.warning("NLP circuit breaker open, using fallback response")
            nlp_circuit_breaker_calls.labels(state="open", result="fallback").inc()
            nlp_circuit_breaker_state.set(1)  # 1 = open
            return self._fallback_response()
        except Exception as e:
            # Other errors
            logger.error(f"NLP processing failed: {e}")
            nlp_operations.labels(operation="process_message", status="error").inc()
            nlp_errors.labels(operation="process_message", error_type=type(e).__name__).inc()
            return self._fallback_response()
    
    async def _process_with_retry(self, text: str) -> dict:
        """Internal processing method with retry logic."""
        # if not self.agent:
        #     return {"intent": {"name": "unknown", "confidence": 0.0}, "entities": []}
        # result = await self.agent.parse_message(message_data=text)
        # return result
        
        # Mock response hasta que se entrene y cargue un modelo Rasa
        # Simula procesamiento exitoso
        return {"intent": {"name": "check_availability", "confidence": 0.95}, "entities": []}
    
    def _fallback_response(self) -> dict:
        """Fallback response when NLP is unavailable."""
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": [],
            "fallback": True
        }

    def handle_low_confidence(self, intent: dict) -> Optional[dict]:
        confidence = intent.get("confidence", 0.0)
        if confidence < 0.7:
            return {
                "response": "¿En qué puedo ayudarte?\n1️⃣ Consultar disponibilidad\n2️⃣ Ver precios\n3️⃣ Información del hotel\n4️⃣ Hablar con recepción",
                "requires_human": confidence < 0.3,
            }
        return None
