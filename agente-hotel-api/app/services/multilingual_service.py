"""
Servicio para el soporte multilingüe del motor NLP.
Permite detectar idioma y gestionar modelos NLP específicos por idioma.
"""

from typing import Dict, Any, List
from enum import Enum
import asyncio
from functools import lru_cache

from prometheus_client import Counter, Histogram
from ..core.logging import logger

# Métricas para monitoreo
language_detection_total = Counter("language_detection_total", "Total de detecciones de idioma", ["detected_language"])

language_detection_latency = Histogram("language_detection_latency_seconds", "Latencia de detección de idioma")


class SupportedLanguage(str, Enum):
    """Idiomas soportados por el motor NLP."""

    SPANISH = "es"
    ENGLISH = "en"
    PORTUGUESE = "pt"

    @classmethod
    def get_all(cls) -> List[str]:
        """Obtener lista de todos los códigos de idioma soportados."""
        return [lang.value for lang in cls]


class LanguageDetector:
    """
    Detector de idioma basado en modelos livianos.
    Utiliza fasttext o langdetect según disponibilidad.
    """

    def __init__(self):
        """Inicializar detector de idioma."""
        self.model = None
        self.backend = None
        self.loaded = False
        self.threshold = 0.7  # Umbral de confianza para detección

    async def initialize(self):
        """
        Inicializar de forma asíncrona.
        Carga el modelo más adecuado según disponibilidad.
        """
        if self.loaded:
            return

        try:
            # Intentar cargar fasttext (más preciso pero más pesado)
            import fasttext

            logger.info("Initializing language detector with fasttext")

            # Ejecutar carga del modelo en thread pool para no bloquear
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, lambda: fasttext.load_model("lid.176.bin"))
            self.backend = "fasttext"

        except ImportError:
            # Fallback a langdetect (más liviano)
            try:
                from langdetect import DetectorFactory

                DetectorFactory.seed = 0  # Para resultados consistentes
                self.backend = "langdetect"
                logger.info("Initializing language detector with langdetect")
            except ImportError:
                logger.warning("No language detection libraries available. Install either fasttext or langdetect.")
                self.backend = "basic"

        self.loaded = True

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detectar idioma de un texto.

        Args:
            text: Texto a analizar

        Returns:
            Dict con idioma detectado y confianza
            {
                "language": "es",
                "confidence": 0.95,
                "supported": True
            }
        """
        if not self.loaded:
            await self.initialize()

        start_time = asyncio.get_event_loop().time()

        # Texto muy corto - usar heurísticas básicas
        if len(text.strip()) < 10:
            result = await self._detect_short_text(text)
            language_detection_total.labels(detected_language=result["language"]).inc()
            return result

        try:
            if self.backend == "fasttext":
                result = await self._detect_with_fasttext(text)
            elif self.backend == "langdetect":
                result = await self._detect_with_langdetect(text)
            else:
                result = await self._detect_with_basic_rules(text)

            # Verificar si es idioma soportado
            result["supported"] = result["language"] in SupportedLanguage.get_all()

            language_detection_total.labels(detected_language=result["language"]).inc()

            return result

        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}", exc_info=True)
            # En caso de error, asumir español (default)
            return {"language": "es", "confidence": 0.5, "supported": True, "error": str(e)}
        finally:
            latency = asyncio.get_event_loop().time() - start_time
            language_detection_latency.observe(latency)

    async def _detect_with_fasttext(self, text: str) -> Dict[str, Any]:
        """Detectar idioma usando fasttext."""
        loop = asyncio.get_event_loop()
        # Ejecutar en thread pool para evitar bloqueo
        predictions = await loop.run_in_executor(None, lambda: self.model.predict(text, k=3))

        # Obtener top language y confianza
        languages = [lang.replace("__label__", "") for lang in predictions[0]]
        confidences = predictions[1].tolist()

        return {
            "language": languages[0],
            "confidence": confidences[0],
            "alternatives": [
                {"language": lang, "confidence": conf} for lang, conf in zip(languages[1:], confidences[1:])
            ],
        }

    async def _detect_with_langdetect(self, text: str) -> Dict[str, Any]:
        """Detectar idioma usando langdetect."""
        from langdetect import detect_langs

        loop = asyncio.get_event_loop()
        # Ejecutar en thread pool para evitar bloqueo
        langs = await loop.run_in_executor(None, lambda: detect_langs(text))

        return {
            "language": langs[0].lang,
            "confidence": langs[0].prob,
            "alternatives": [
                {"language": lang.lang, "confidence": lang.prob} for lang in langs[1:3] if lang.prob > 0.05
            ],
        }

    async def _detect_with_basic_rules(self, text: str) -> Dict[str, Any]:
        """
        Detectar idioma usando reglas básicas cuando no hay librerías disponibles.
        Basado en frecuencia de palabras específicas.
        """
        text_lower = text.lower()

        # Indicadores por idioma (artículos, pronombres, preposiciones comunes)
        spanish_indicators = ["el", "la", "los", "las", "que", "es", "son", "para", "con", "por"]
        english_indicators = ["the", "a", "an", "is", "are", "for", "to", "with", "and", "of"]
        portuguese_indicators = ["o", "a", "os", "as", "é", "são", "para", "com", "por", "em"]

        # Contar matches por idioma
        es_count = sum(1 for word in spanish_indicators if f" {word} " in f" {text_lower} ")
        en_count = sum(1 for word in english_indicators if f" {word} " in f" {text_lower} ")
        pt_count = sum(1 for word in portuguese_indicators if f" {word} " in f" {text_lower} ")

        total = es_count + en_count + pt_count
        if total == 0:
            # Sin indicadores claros, asumir español
            return {"language": "es", "confidence": 0.33}

        if es_count >= en_count and es_count >= pt_count:
            return {"language": "es", "confidence": es_count / total}
        elif en_count >= es_count and en_count >= pt_count:
            return {"language": "en", "confidence": en_count / total}
        else:
            return {"language": "pt", "confidence": pt_count / total}

    async def _detect_short_text(self, text: str) -> Dict[str, Any]:
        """Heurística especial para textos muy cortos."""
        # Palabras únicas para cada idioma
        unique_es = {"hola", "gracias", "sí", "bueno", "vale", "adios", "hasta", "luego"}
        unique_en = {"hello", "thanks", "yes", "good", "bye", "see", "you", "welcome"}
        unique_pt = {"obrigado", "sim", "bom", "tchau", "ate", "logo", "oi", "ola"}

        text_lower = text.lower()

        for word in text_lower.split():
            if word in unique_es:
                return {"language": "es", "confidence": 0.8}
            if word in unique_en:
                return {"language": "en", "confidence": 0.8}
            if word in unique_pt:
                return {"language": "pt", "confidence": 0.8}

        # Sin matches claros, usar reglas básicas
        return await self._detect_with_basic_rules(text)


class MultilingualNLPService:
    """
    Servicio para gestión de modelos NLP multilingües.
    Mantiene un modelo para cada idioma soportado.
    """

    def __init__(self):
        """Inicializar servicio multilingüe."""
        self.language_detector = LanguageDetector()
        self.models = {}
        self.default_language = SupportedLanguage.SPANISH

    async def initialize(self):
        """Inicializar detector de idioma."""
        await self.language_detector.initialize()

    async def process_with_language_detection(self, text: str) -> Dict[str, Any]:
        """
        Procesar texto con detección automática de idioma.

        Args:
            text: Texto a procesar

        Returns:
            Dict con resultado del procesamiento y metadatos de idioma
        """
        # Detectar idioma
        language_info = await self.language_detector.detect_language(text)
        detected_language = language_info["language"]

        # Si el idioma no es soportado, usar idioma por defecto
        if not language_info.get("supported", False):
            language_code = self.default_language.value
            logger.info(f"Unsupported language detected: {detected_language}, using default: {language_code}")
        else:
            language_code = detected_language

        # Regresar idioma y texto original para procesamiento posterior
        return {
            "language_code": language_code,
            "language_confidence": language_info.get("confidence", 0.0),
            "original_language": detected_language,
            "text": text,
        }

    @lru_cache(maxsize=1000)
    def get_language_specific_templates(self, template_name: str, language: str) -> Dict[str, str]:
        """
        Obtener plantillas específicas por idioma.

        Args:
            template_name: Nombre de la plantilla
            language: Código de idioma

        Returns:
            Dict con plantilla multilingüe
        """
        # Definir plantillas para los distintos idiomas
        templates = {
            "greeting": {
                "es": "Hola, ¿en qué puedo ayudarte hoy?",
                "en": "Hello, how may I help you today?",
                "pt": "Olá, como posso ajudá-lo hoje?",
            },
            "availability_found": {
                "es": "Tenemos disponibilidad para tu solicitud del {checkin} al {checkout} en habitación {room_type} para {guests} personas. El precio es de ${price} por noche, total ${total}.",
                "en": "We have availability for your request from {checkin} to {checkout} in a {room_type} room for {guests} people. The price is ${price} per night, total ${total}.",
                "pt": "Temos disponibilidade para sua solicitação de {checkin} a {checkout} em quarto {room_type} para {guests} pessoas. O preço é de ${price} por noite, total ${total}.",
            },
            # Más plantillas aquí...
        }

        # Regresar plantilla en idioma solicitado o en español como fallback
        template_dict = templates.get(template_name, {})
        return template_dict.get(language, template_dict.get("es", ""))


# Instancia global del servicio
multilingual_nlp_service = MultilingualNLPService()


async def get_multilingual_nlp_service() -> MultilingualNLPService:
    """Getter para el servicio multilingüe."""
    if not multilingual_nlp_service.language_detector.loaded:
        await multilingual_nlp_service.initialize()
    return multilingual_nlp_service
