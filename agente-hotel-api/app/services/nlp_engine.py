# [PROMPT 2.5 + E.3 + E.5] app/services/nlp_engine.py
"""
NLP Engine with Rasa Agent Integration
Enhanced with multilingual support (ES, EN, PT)
"""

import os
import re
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
nlp_circuit_breaker_state = Gauge(
    "nlp_circuit_breaker_state", "NLP circuit breaker state (0=closed, 1=open, 2=half-open)"
)
nlp_circuit_breaker_calls = Counter("nlp_circuit_breaker_calls_total", "NLP circuit breaker calls", ["state", "result"])
nlp_confidence = Histogram(
    "nlp_confidence_score", "NLP confidence score distribution", buckets=[0.3, 0.5, 0.7, 0.85, 0.95, 1.0]
)
nlp_intent_predictions = Counter("nlp_intent_predictions_total", "Intent predictions", ["intent", "confidence_bucket"])
nlp_language_detection = Counter(
    "nlp_language_detection_total", "Language detection results", ["detected_language", "source"]
)


class NLPEngine:
    """
    Enhanced NLP Engine powered by Rasa DIET Classifier with multilingual support.

    Features:
    - Loads trained Rasa models from disk (specific per language or multilingual)
    - Intent classification with confidence scores
    - Entity extraction (dates, numbers, room types, amenities)
    - Language detection capabilities (ES, EN, PT)
    - Circuit breaker for resilience
    - In-memory agent caching
    - Model versioning support
    """

    # Supported languages with ISO codes
    SUPPORTED_LANGUAGES = {"es": "Spanish", "en": "English", "pt": "Portuguese"}

    # Common words for language detection as fallback
    LANGUAGE_MARKERS = {
        "es": [
            "hola",
            "gracias",
            "por favor",
            "hotel",
            "habitación",
            "reserva",
            "disponibilidad",
            "buenas",
            "quiero",
            "necesito",
            "días",
            "noches",
            "precio",
            "cuánto",
        ],
        "en": [
            "hello",
            "thanks",
            "please",
            "hotel",
            "room",
            "booking",
            "reservation",
            "availability",
            "good",
            "want",
            "need",
            "days",
            "nights",
            "price",
            "how much",
        ],
        "pt": [
            "olá",
            "obrigado",
            "por favor",
            "hotel",
            "quarto",
            "reserva",
            "disponibilidade",
            "bom",
            "quero",
            "preciso",
            "dias",
            "noites",
            "preço",
            "quanto",
        ],
    }

    def __init__(self, model_path: Optional[str] = None, languages: Optional[List[str]] = None):
        """
        Initialize NLP Engine with Rasa model.

        Args:
            model_path: Path to .tar.gz Rasa model file. If None, loads from default location.
            languages: List of supported languages ISO codes. Defaults to ["es", "en", "pt"]
        """
        # Circuit breaker for NLP calls
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
        nlp_circuit_breaker_state.set(0)  # 0 = closed

        # Supported languages
        self.languages = languages or ["es", "en", "pt"]

        # Model configuration - can be either multilingual or language-specific
        self.use_multilingual = os.getenv("NLP_USE_MULTILINGUAL", "true").lower() == "true"
        self.default_language = os.getenv("NLP_DEFAULT_LANGUAGE", "es")

        # Initialize models dict
        self.models: Dict[str, Dict[str, Any]] = {}
        self.model_paths: Dict[str, str] = {}

        # Try to load language detection model if available
        self.lang_detector = self._initialize_language_detector()

        # Load appropriate models
        self._resolve_model_paths()
        self._load_models()

    def _initialize_language_detector(self) -> Optional[Any]:
        """Initialize language detector if available"""
        try:
            import fasttext

            # Try to load pretrained model
            return fasttext.load_model(
                os.getenv(
                    "LANGUAGE_DETECTION_MODEL", os.path.join(os.path.dirname(__file__), "../../models/lid.176.bin")
                )
            )
        except ImportError:
            logger.warning("FastText not installed. Using fallback language detection.")
            return None
        except Exception as e:
            logger.error(f"Failed to load language detection model: {e}", exc_info=True)
            return None

    def _resolve_model_paths(self) -> None:
        """
        Resolve Rasa model paths from environment or default locations.

        Sets self.model_paths with language codes as keys.
        """
        # Check if we're using a single multilingual model
        if self.use_multilingual:
            multilingual_path = os.getenv("RASA_MULTILINGUAL_MODEL_PATH")
            if multilingual_path and Path(multilingual_path).exists():
                logger.info(f"Using multilingual Rasa model: {multilingual_path}")
                # Use the same model for all languages
                for lang in self.languages:
                    self.model_paths[lang] = multilingual_path
                return

        # Check for language-specific models from environment
        project_root = Path(__file__).parent.parent.parent
        models_found = False

        for lang in self.languages:
            # Try environment variable first
            env_var = f"RASA_MODEL_PATH_{lang.upper()}"
            env_path = os.getenv(env_var)

            if env_path and Path(env_path).exists():
                self.model_paths[lang] = env_path
                models_found = True
                logger.info(f"Using {lang} Rasa model from {env_var}: {env_path}")
                continue

            # Try default location with language-specific name
            default_path = project_root / "rasa_nlu" / "models" / f"nlu_enhanced_{lang}.tar.gz"
            if default_path.exists():
                self.model_paths[lang] = str(default_path)
                models_found = True
                logger.info(f"Using {lang} Rasa model from default location: {default_path}")
                continue

            # Try symlinked latest model as fallback
            latest_path = project_root / "rasa_nlu" / "models" / "latest.tar.gz"
            if latest_path.exists():
                self.model_paths[lang] = str(latest_path)
                models_found = True
                logger.info(f"Using fallback Rasa model for {lang}: {latest_path}")
                continue

            logger.warning(f"No model found for language {lang}")

        if not models_found:
            logger.warning(
                "No Rasa models found. NLP engine will run in fallback mode. "
                "Train models with: scripts/train_enhanced_models.sh"
            )

    def _load_models(self) -> None:
        """Load Rasa Agents from model files."""
        if not self.model_paths:
            logger.warning("No model paths configured, running in fallback mode")
            return

        try:
            from rasa.core.agent import Agent

            for lang, model_path in self.model_paths.items():
                try:
                    logger.info(f"Loading Rasa model for {lang} from: {model_path}")
                    agent = Agent.load(model_path)

                    # Extract model version from filename
                    model_filename = Path(model_path).stem
                    if "_" in model_filename:
                        model_version = "_".join(model_filename.split("_")[-2:])
                    else:
                        model_version = "unknown"

                    # Store model info
                    self.models[lang] = {
                        "agent": agent,
                        "model_path": model_path,
                        "model_version": model_version,
                        "loaded_at": datetime.utcnow(),
                    }

                    logger.info(
                        f"Rasa model for {lang} loaded successfully",
                        extra={"language": lang, "model_version": model_version, "model_path": model_path},
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to load Rasa model for {lang}: {e}",
                        exc_info=True,
                        extra={"model_path": model_path, "language": lang},
                    )

        except ImportError:
            logger.error("Rasa not installed. Install with: pip install rasa")

    async def detect_language(self, text: str) -> str:
        """
        Detect language of input text.

        Args:
            text: User message

        Returns:
            ISO language code (es, en, pt) or default language if detection fails
        """
        # Sanity check for empty text
        if not text or len(text.strip()) == 0:
            nlp_language_detection.labels(detected_language=self.default_language, source="empty").inc()
            return self.default_language

        # Try FastText if available
        if self.lang_detector:
            try:
                # FastText requires text to be preprocessed
                clean_text = " ".join(text.lower().split())
                prediction = self.lang_detector.predict(clean_text, k=1)
                lang_code = prediction[0][0].replace("__label__", "")

                # Map to our supported languages
                if lang_code in self.languages:
                    nlp_language_detection.labels(detected_language=lang_code, source="fasttext").inc()
                    return lang_code

                # Special case for variants (e.g., pt-br -> pt)
                for supported_lang in self.languages:
                    if lang_code.startswith(supported_lang):
                        nlp_language_detection.labels(detected_language=supported_lang, source="fasttext_mapped").inc()
                        return supported_lang
            except Exception as e:
                logger.warning(f"Language detection failed: {e}", exc_info=True)

        # Fallback: Word frequency analysis
        lang_scores = {lang: 0 for lang in self.languages}

        # Normalize text for comparison
        text_lower = text.lower()

        # Count occurrences of marker words
        for lang, markers in self.LANGUAGE_MARKERS.items():
            for word in markers:
                # Match whole words only
                pattern = r"\b" + re.escape(word) + r"\b"
                matches = re.findall(pattern, text_lower)
                lang_scores[lang] += len(matches)

        # Get language with highest score
        if sum(lang_scores.values()) > 0:
            detected = max(lang_scores, key=lang_scores.get)
            nlp_language_detection.labels(detected_language=detected, source="word_frequency").inc()
            return detected

        # Last resort: return default language
        nlp_language_detection.labels(detected_language=self.default_language, source="default").inc()
        return self.default_language

    async def process_message(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Process text message to extract intent and entities.

        Args:
            text: User message
            language: ISO language code (es, en, pt) or None for auto-detection

        Returns:
            dict with structure:
            {
                "intent": {"name": str, "confidence": float},
                "entities": [{"entity": str, "value": str, "start": int, "end": int}],
                "text": str,
                "language": str,
                "model_version": str,
                "fallback": bool (only if fallback used)
            }
        """
        try:
            # Detect language if not provided
            if not language:
                language = await self.detect_language(text)

            # Regla rápida basada en palabras clave (fallback simple sin modelos)
            text_l = (text or "").lower()
            rule_intent: Optional[str] = None
            # Español/Portugués/Inglés: disponibilidad/availability
            if re.search(r"\b(disponibilidad|disponible|availability)\b", text_l):
                rule_intent = "check_availability"
            elif re.search(r"\b(reserva(r)?|reservation|book(ing)?)\b", text_l):
                rule_intent = "make_reservation"

            if rule_intent is not None:
                result = {
                    "intent": {"name": rule_intent, "confidence": 0.8},
                    "entities": [],
                    "text": text,
                    "model_version": "rules-heuristics",
                }
            else:
                # Process with appropriate model (o fallback si no hay modelo)
                result = await self.circuit_breaker.call(self._process_with_retry, text, language)

            nlp_operations.labels(operation="process_message", status="success").inc()

            # Record metrics
            confidence = result.get("intent", {}).get("confidence", 0.0)
            nlp_confidence.observe(confidence)

            # Intent prediction metrics (bucketed by confidence)
            intent_name = result.get("intent", {}).get("name", "unknown")
            confidence_bucket = self._get_confidence_bucket(confidence)
            nlp_intent_predictions.labels(intent=intent_name, confidence_bucket=confidence_bucket).inc()

            # Add detected language to result
            result["language"] = language

            return result

        except CircuitBreakerOpenError:
            # Circuit breaker open: use fallback
            logger.warning("NLP circuit breaker open, using fallback response")
            nlp_circuit_breaker_calls.labels(state="open", result="fallback").inc()
            nlp_circuit_breaker_state.set(1)  # 1 = open
            return self._fallback_response(language or self.default_language)

        except Exception as e:
            # Other errors
            logger.error(f"NLP processing failed: {e}", exc_info=True)
            nlp_operations.labels(operation="process_message", status="error").inc()
            nlp_errors.labels(operation="process_message", error_type=type(e).__name__).inc()
            return self._fallback_response(language or self.default_language)

    # Backward-compatibility shim for tests that patch `process_text` instead of `process_message`
    async def process_text(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Compat wrapper: delegates to process_message. Some tests patch this method directly.

        Args:
            text: User message
            language: Optional ISO language code

        Returns:
            Parsed NLP result dict (same contract as process_message)
        """
        return await self.process_message(text=text, language=language)

    async def _process_with_retry(self, text: str, language: str) -> Dict[str, Any]:
        """
        Internal processing method with Rasa Agent.

        Args:
            text: User message
            language: ISO language code

        Returns:
            Parsed message with intent and entities
        """
        # If language not supported, use default
        if language not in self.models:
            if self.default_language in self.models:
                language = self.default_language
            else:
                logger.warning(f"No model available for {language} or default language")
                return self._fallback_response(language)

        # Get model info
        model_info = self.models.get(language)
        if not model_info or "agent" not in model_info:
            logger.warning(f"No agent loaded for language {language}, using fallback")
            return self._fallback_response(language)

        try:
            # Parse message with Rasa
            agent = model_info["agent"]
            result = await agent.parse_message(message_data=text)

            # Normalize result structure
            normalized = {
                "intent": {
                    "name": result.get("intent", {}).get("name", "unknown"),
                    "confidence": result.get("intent", {}).get("confidence", 0.0),
                },
                "entities": self._normalize_entities(result.get("entities", [])),
                "text": text,
                "model_version": model_info["model_version"],
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
            normalized.append(
                {
                    "entity": entity.get("entity"),
                    "value": entity.get("value"),
                    "start": entity.get("start"),
                    "end": entity.get("end"),
                    "confidence": entity.get("confidence_entity", entity.get("confidence", 1.0)),
                    "extractor": entity.get("extractor", "unknown"),
                }
            )

        return normalized

    def _fallback_response(self, language: str = "es") -> Dict[str, Any]:
        """
        Fallback response when NLP is unavailable.

        Args:
            language: ISO language code for response

        Returns:
            Response with unknown intent and fallback flag
        """
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": [],
            "fallback": True,
            "text": "",
            "language": language,
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

    def handle_low_confidence(self, intent: Dict[str, Any], language: str = "es") -> Optional[Dict[str, Any]]:
        """
        Handle low-confidence intent predictions with clarification prompts.

        Args:
            intent: Intent dict with name and confidence
            language: ISO language code for response

        Returns:
            dict with response and human handoff flag, or None if confidence is acceptable
        """
        confidence = intent.get("confidence", 0.0)

        # Very low confidence (<0.3): escalate to human
        if confidence < 0.3:
            if language == "en":
                return {
                    "response": (
                        "I'm sorry, I'm not sure I understand your inquiry. "
                        "Could you rephrase it or would you like me to connect you with a representative?"
                    ),
                    "requires_human": True,
                }
            elif language == "pt":
                return {
                    "response": (
                        "Desculpe, não tenho certeza se entendi sua pergunta. "
                        "Você poderia reformulá-la ou gostaria que eu o conectasse com um representante?"
                    ),
                    "requires_human": True,
                }
            else:  # Spanish (default)
                return {
                    "response": (
                        "Disculpa, no estoy seguro de entender tu consulta. "
                        "¿Podrías reformularla o te conecto con un representante?"
                    ),
                    "requires_human": True,
                }

        # Low confidence (0.3-0.7): offer menu
        if confidence < 0.7:
            if language == "en":
                return {
                    "response": (
                        "How can I help you?\n"
                        "1️⃣ Check availability\n"
                        "2️⃣ Make a reservation\n"
                        "3️⃣ Modify/cancel reservation\n"
                        "4️⃣ Hotel information (prices, services, location)\n"
                        "5️⃣ Talk to reception"
                    ),
                    "requires_human": False,
                }
            elif language == "pt":
                return {
                    "response": (
                        "Como posso ajudá-lo?\n"
                        "1️⃣ Verificar disponibilidade\n"
                        "2️⃣ Fazer uma reserva\n"
                        "3️⃣ Modificar/cancelar reserva\n"
                        "4️⃣ Informações do hotel (preços, serviços, localização)\n"
                        "5️⃣ Falar com a recepção"
                    ),
                    "requires_human": False,
                }
            else:  # Spanish (default)
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
        Get information about loaded models.

        Returns:
            dict with model metadata
        """
        models_info = {}

        for lang, model in self.models.items():
            models_info[lang] = {
                "model_path": model.get("model_path", ""),
                "model_version": model.get("model_version", "unknown"),
                "model_loaded_at": model.get("loaded_at").isoformat() if model.get("loaded_at") is not None else None,
                "agent_loaded": model.get("agent") is not None,
            }

        return {
            "supported_languages": self.languages,
            "default_language": self.default_language,
            "models": models_info,
            "use_multilingual": self.use_multilingual,
            "language_detector": self.lang_detector is not None,
            "fallback_mode": len(self.models) == 0,
        }
