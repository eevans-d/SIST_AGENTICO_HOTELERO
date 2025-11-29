"""
Módulo para procesamiento multilingüe de lenguaje natural.

Este módulo proporciona capacidades para:
1. Detectar automáticamente el idioma del mensaje
2. Cargar y gestionar modelos NLP multilingües
3. Procesar texto en español, inglés y portugués
4. Normalizar entidades entre diferentes idiomas
"""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import re

from prometheus_client import Counter, Histogram, Gauge
from ..core.logging import logger
from ..core.circuit_breaker import CircuitBreaker

# Métricas para monitoreo
multilingual_detection = Counter(
    "multilingual_detection_total", "Detecciones de idioma", ["language", "confidence_level"]
)

multilingual_processing = Counter("multilingual_processing_total", "Procesamiento multilingüe", ["language", "status"])

multilingual_model_loads = Counter(
    "multilingual_model_loads_total", "Cargas de modelo multilingüe", ["language", "status"]
)

multilingual_latency = Histogram(
    "multilingual_latency_seconds", "Latencia de procesamiento multilingüe", ["language", "operation"]
)

multilingual_memory = Gauge("multilingual_memory_bytes", "Memoria utilizada por modelos multilingües", ["language"])


class MultilingualProcessor:
    """
    Procesador multilingüe para textos en español, inglés y portugués.

    Características:
    - Detección automática de idioma
    - Modelos específicos por idioma
    - Carga lazy de modelos
    - Normalización de entidades
    """

    def __init__(self):
        """
        Inicializa el procesador multilingüe.
        """
        # Inicialización de modelos (lazy loading)
        self.models = {}
        self.language_detectors = {}
        self._models_loaded = {"es": False, "en": False, "pt": False}
        self._loading_locks = {"es": asyncio.Lock(), "en": asyncio.Lock(), "pt": asyncio.Lock()}

        # Circuit breaker para protección
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)

    # =========================================================================
    # LANGUAGE DETECTION HELPERS - Extracted to reduce complexity
    # =========================================================================

    def _detect_by_heuristics(self, text_lower: str) -> Optional[Dict[str, Any]]:
        """Detect language using keyword-based heuristics."""
        es_indicators = ["hola", "gracias", "buenos días", "habitación", "reserva"]
        en_indicators = ["hello", "thank", "room", "booking", "reservation", "available"]
        pt_indicators = ["olá", "obrigado", "quarto", "reserva", "disponível"]

        es_score = sum(2 for word in es_indicators if word in text_lower)
        en_score = sum(2 for word in en_indicators if word in text_lower)
        pt_score = sum(2 for word in pt_indicators if word in text_lower)

        max_score = max(es_score, en_score, pt_score)
        if max_score < 4:
            return None

        lang_scores = [("es", es_score), ("en", en_score), ("pt", pt_score)]
        best_lang, best_score = max(lang_scores, key=lambda x: x[1])
        confidence = min(0.7 + (best_score - 4) * 0.05, 0.95)
        multilingual_detection.labels(language=best_lang, confidence_level="heuristic").inc()
        return {"language": best_lang, "confidence": confidence, "method": "heuristic"}

    def _detect_by_fasttext(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect language using fastText model."""
        if not self.language_detectors.get("fasttext"):
            return None

        try:
            lang_pred = self.language_detectors["fasttext"].predict(text, k=3)
            predictions = [
                (label.replace("__label__", ""), float(prob))
                for label, prob in zip(lang_pred[0], lang_pred[1])
            ]

            relevant_preds = [(lang, prob) for lang, prob in predictions if lang in ["es", "en", "pt"]]
            if not relevant_preds:
                return None

            best_lang, best_prob = relevant_preds[0]
            confidence_level = "high" if best_prob > 0.8 else "medium" if best_prob > 0.6 else "low"
            multilingual_detection.labels(language=best_lang, confidence_level=confidence_level).inc()
            return {"language": best_lang, "confidence": best_prob, "method": "fasttext"}
        except Exception as e:
            logger.warning(f"Error in fastText language detection: {e}")
            return None

    def _detect_by_grammar(self, text_lower: str) -> Optional[Dict[str, Any]]:
        """Detect language using grammar rules (articles)."""
        grammar_rules = [
            ("es", [" el ", " la ", " los ", " las ", " un ", " una "]),
            ("en", [" the ", " a ", " an ", " this ", " that "]),
            ("pt", [" o ", " a ", " os ", " as ", " um ", " uma "]),
        ]
        for lang, articles in grammar_rules:
            if any(article in text_lower for article in articles):
                multilingual_detection.labels(language=lang, confidence_level="grammar").inc()
                return {"language": lang, "confidence": 0.6, "method": "grammar"}
        return None

    # =========================================================================
    # END LANGUAGE DETECTION HELPERS
    # =========================================================================

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detecta el idioma del texto.
        Uses extracted helpers for improved maintainability (CC reduced from 27 to ~10).
        """
        start_time = asyncio.get_event_loop().time()

        try:
            await self._ensure_language_detector()

            # Short text fallback
            if len(text.strip()) < 5:
                return {"language": "es", "confidence": 0.5, "method": "fallback"}

            text_lower = text.lower()

            # Try detection methods in order of priority
            result = self._detect_by_heuristics(text_lower)
            if result:
                return result

            result = self._detect_by_fasttext(text)
            if result:
                return result

            result = self._detect_by_grammar(text_lower)
            if result:
                return result

            # Default: Spanish
            multilingual_detection.labels(language="es", confidence_level="default").inc()
            return {"language": "es", "confidence": 0.5, "method": "default"}

        except Exception as e:
            logger.error(f"Language detection error: {e}", exc_info=True)
            multilingual_detection.labels(language="es", confidence_level="error").inc()
            return {"language": "es", "confidence": 0.5, "method": "error"}

        finally:
            duration = asyncio.get_event_loop().time() - start_time
            multilingual_latency.labels(language="all", operation="detect").observe(duration)

    async def process_text(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesa texto en el idioma especificado o detectado automáticamente.

        Args:
            text: Texto a procesar
            language: Código de idioma (opcional)

        Returns:
            Resultado del procesamiento NLP
        """
        start_time = asyncio.get_event_loop().time()
        detected_lang = language

        try:
            # Detectar idioma si no se proporciona
            if not detected_lang:
                lang_result = await self.detect_language(text)
                detected_lang = lang_result["language"]

            # Asegurar que tenemos el modelo cargado
            await self._ensure_model_loaded(detected_lang)

            # Procesar texto con el modelo adecuado
            result = await self._process_with_model(text, detected_lang)

            # Normalizar resultado a formato estándar
            normalized = self._normalize_result(result, detected_lang)
            multilingual_processing.labels(language=detected_lang, status="success").inc()

            return normalized

        except Exception as e:
            logger.error(f"Multilingual processing error: {e}", exc_info=True)
            multilingual_processing.labels(language=detected_lang or "unknown", status="error").inc()
            return {
                "intent": {"name": "unknown", "confidence": 0.0},
                "entities": [],
                "language": detected_lang or "es",
                "error": str(e),
            }

        finally:
            duration = asyncio.get_event_loop().time() - start_time
            multilingual_latency.labels(language=detected_lang or "unknown", operation="process").observe(duration)

    async def _ensure_language_detector(self):
        """
        Asegura que el detector de idioma esté cargado.
        """
        if "fasttext" not in self.language_detectors:
            try:
                import fasttext

                # Verificar si existe el modelo en la ruta por defecto
                model_path = Path(__file__).parent.parent.parent / "models" / "lid.176.bin"

                if not model_path.exists():
                    # Descargar modelo si no existe
                    logger.info("Language detection model not found, downloading...")
                    model_path = Path(__file__).parent.parent.parent / "models"
                    model_path.mkdir(exist_ok=True)
                    # Esta línea usaría fasttext.util.download_model pero requiere manejo especial
                    # Por simplicidad, asumimos que el modelo estará disponible o usamos alternativas
                    logger.warning("FastText download not implemented, using rule-based detection")
                else:
                    # Cargar modelo
                    self.language_detectors["fasttext"] = fasttext.load_model(str(model_path))
                    logger.info("Language detection model loaded successfully")
            except ImportError:
                logger.warning("FastText not installed, using rule-based language detection")
            except Exception as e:
                logger.error(f"Error loading language detection model: {e}", exc_info=True)

    async def _ensure_model_loaded(self, language: str):
        """
        Asegura que el modelo para el idioma especificado esté cargado.

        Args:
            language: Código de idioma
        """
        if language not in ["es", "en", "pt"]:
            language = "es"  # Fallback a español

        if not self._models_loaded.get(language, False):
            async with self._loading_locks[language]:
                # Verificar nuevamente dentro del lock
                if not self._models_loaded.get(language, False):
                    try:
                        model = await self._load_model(language)
                        self.models[language] = model
                        self._models_loaded[language] = True
                        multilingual_model_loads.labels(language=language, status="success").inc()

                        # Estimar memoria usada por el modelo (aproximado)
                        try:
                            import sys

                            model_size = sys.getsizeof(model) / (1024 * 1024)  # MB
                            multilingual_memory.labels(language=language).set(model_size)
                        except Exception:
                            pass

                    except Exception as e:
                        logger.error(f"Error loading model for {language}: {e}", exc_info=True)
                        multilingual_model_loads.labels(language=language, status="error").inc()
                        raise

    async def _load_model(self, language: str):
        """
        Carga un modelo NLP para el idioma especificado.

        Args:
            language: Código de idioma

        Returns:
            Modelo NLP
        """
        logger.info(f"Loading NLP model for language: {language}")

        try:
            from rasa.core.agent import Agent

            # Definir ruta del modelo
            model_path = os.getenv("RASA_MODEL_PATH")
            if not model_path:
                project_root = Path(__file__).parent.parent.parent
                model_dir = project_root / "rasa_nlu" / "models"

                # Buscar modelo específico para el idioma
                model_pattern = f"*{language}*.tar.gz"
                models = list(model_dir.glob(model_pattern))

                if models:
                    # Usar el modelo más reciente
                    models.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    model_path = str(models[0])
                else:
                    # Si no hay modelo específico para el idioma, usar modelo por defecto
                    default_model = model_dir / "latest.tar.gz"
                    if default_model.exists():
                        model_path = str(default_model)
                    else:
                        raise FileNotFoundError(f"No model found for {language}")

            # Cargar modelo
            logger.info(f"Loading model from: {model_path}")
            model = await asyncio.to_thread(Agent.load, model_path)

            return model

        except ImportError:
            logger.error("Rasa not installed. Install with: pip install rasa")
            raise
        except Exception as e:
            logger.error(f"Failed to load model for {language}: {e}", exc_info=True)
            raise

    async def _process_with_model(self, text: str, language: str) -> Dict[str, Any]:
        """
        Procesa texto con el modelo NLP adecuado.

        Args:
            text: Texto a procesar
            language: Código de idioma

        Returns:
            Resultado del procesamiento
        """
        model = self.models.get(language)
        if not model:
            raise ValueError(f"Model for language {language} not loaded")

        try:
            # Preprocesar texto
            preprocessed_text = await self._preprocess_text(text, language)

            # Procesar con circuit breaker para resiliencia
            result = await self.circuit_breaker.call(self._call_model, model, preprocessed_text)

            return result

        except Exception as e:
            logger.error(f"Error processing text with model: {e}", exc_info=True)
            raise

    async def _call_model(self, model, text: str) -> Dict[str, Any]:
        """
        Llama al modelo Rasa con el texto.

        Args:
            model: Modelo Rasa
            text: Texto a procesar

        Returns:
            Resultado del procesamiento
        """
        # Convertir a thread pool para no bloquear event loop
        result = await asyncio.to_thread(model.parse_message, text)
        return result

    async def _preprocess_text(self, text: str, language: str) -> str:
        """
        Preprocesa el texto según el idioma.

        Args:
            text: Texto a preprocesar
            language: Código de idioma

        Returns:
            Texto preprocesado
        """
        # Normalizar espacios
        text = re.sub(r"\s+", " ", text).strip()

        # Correcciones específicas por idioma
        if language == "es":
            # Corregir errores comunes en español
            corrections = {
                r"\bhabitacion(es)?\b": "habitación\\1",
                r"\breservacion(es)?\b": "reservación\\1",
                r"\bkiero\b": "quiero",
                r"\bfinde\b": "fin de semana",
            }

            for pattern, replacement in corrections.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        elif language == "en":
            # Corregir errores comunes en inglés
            corrections = {
                r"\bwanna\b": "want to",
                r"\bgonna\b": "going to",
                r"\bu\b": "you",
                r"\br\b": "are",
            }

            for pattern, replacement in corrections.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        elif language == "pt":
            # Corregir errores comunes en portugués
            corrections = {
                r"\bkero\b": "quero",
                r"\breserva(r|)\b": "reserva\\1",
            }

            for pattern, replacement in corrections.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _normalize_result(self, result: Dict[str, Any], language: str) -> Dict[str, Any]:
        """
        Normaliza el resultado del procesamiento NLP.

        Args:
            result: Resultado del procesamiento
            language: Código de idioma

        Returns:
            Resultado normalizado
        """
        # Extraer intent y confianza
        intent_name = result.get("intent", {}).get("name", "unknown")
        confidence = result.get("intent", {}).get("confidence", 0.0)

        # Normalizar entities
        normalized_entities = []
        for entity in result.get("entities", []):
            normalized_entity = {
                "entity": entity.get("entity"),
                "value": entity.get("value"),
                "start": entity.get("start"),
                "end": entity.get("end"),
                "confidence": entity.get("confidence_entity", entity.get("confidence", 1.0)),
                "extractor": entity.get("extractor", "unknown"),
                "language": language,
            }
            normalized_entities.append(normalized_entity)

        # Resultado normalizado
        normalized = {
            "intent": {"name": intent_name, "confidence": confidence},
            "entities": normalized_entities,
            "language": language,
        }

        return normalized


# Variable para singleton
_multilingual_processor_instance = None


async def get_multilingual_processor() -> MultilingualProcessor:
    """
    Devuelve una instancia singleton de MultilingualProcessor.
    """
    global _multilingual_processor_instance

    if _multilingual_processor_instance is None:
        _multilingual_processor_instance = MultilingualProcessor()

    return _multilingual_processor_instance
