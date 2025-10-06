"""
Tests para servicio multilingüe del motor NLP.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.multilingual_service import (
    LanguageDetector,
    MultilingualNLPService,
    SupportedLanguage,
    get_multilingual_nlp_service
)


@pytest.fixture
def language_detector():
    """Detector de idioma para tests."""
    detector = LanguageDetector()
    detector.loaded = True
    detector.backend = "basic"  # usar reglas básicas para tests
    return detector


@pytest.fixture
def multilingual_service(language_detector):
    """Servicio multilingüe para tests."""
    service = MultilingualNLPService()
    service.language_detector = language_detector
    return service


class TestLanguageDetector:
    """Tests para detector de idioma."""
    
    async def test_detect_spanish(self, language_detector):
        """Test para detectar español."""
        text = "Hola, quiero hacer una reserva para dos personas"
        
        # Ejecutar
        result = await language_detector._detect_with_basic_rules(text)
        
        # Verificar
        assert result["language"] == "es"
        assert result["confidence"] > 0.5
    
    async def test_detect_english(self, language_detector):
        """Test para detectar inglés."""
        text = "Hello, I want to make a reservation for two people"
        
        # Ejecutar
        result = await language_detector._detect_with_basic_rules(text)
        
        # Verificar
        assert result["language"] == "en"
        assert result["confidence"] > 0.5
    
    async def test_detect_portuguese(self, language_detector):
        """Test para detectar portugués."""
        text = "Olá, eu quero fazer uma reserva para duas pessoas"
        
        # Ejecutar
        result = await language_detector._detect_with_basic_rules(text)
        
        # Verificar
        assert result["language"] == "pt"
        assert result["confidence"] > 0.5
    
    async def test_detect_short_text(self, language_detector):
        """Test para textos cortos."""
        # Español
        result_es = await language_detector._detect_short_text("hola")
        assert result_es["language"] == "es"
        
        # Inglés
        result_en = await language_detector._detect_short_text("hello")
        assert result_en["language"] == "en"
        
        # Portugués
        result_pt = await language_detector._detect_short_text("obrigado")
        assert result_pt["language"] == "pt"
        
        # Ambiguo (usa reglas básicas)
        result_unknown = await language_detector._detect_short_text("hi")
        assert result_unknown["language"] in ["es", "en", "pt"]
    
    async def test_detect_language_main_method(self, language_detector):
        """Test para método principal detect_language."""
        # Mock para método interno
        language_detector._detect_with_basic_rules = AsyncMock(return_value={
            "language": "es",
            "confidence": 0.9
        })
        
        # Ejecutar
        result = await language_detector.detect_language("Hola, buenos días")
        
        # Verificar
        assert result["language"] == "es"
        assert result["confidence"] == 0.9
        assert result["supported"] == True
    
    async def test_detect_unsupported_language(self, language_detector):
        """Test para idioma no soportado."""
        # Mock para simular detección de francés (no soportado)
        language_detector._detect_with_basic_rules = AsyncMock(return_value={
            "language": "fr",
            "confidence": 0.8
        })
        
        # Ejecutar
        result = await language_detector.detect_language("Bonjour")
        
        # Verificar
        assert result["language"] == "fr"
        assert result["supported"] == False
    
    async def test_initialize_without_libraries(self, language_detector):
        """Test para inicialización sin librerías externas."""
        # Reiniciar estado
        language_detector.loaded = False
        language_detector.backend = None
        
        with patch('app.services.multilingual_service.logger') as mock_logger:
            # Simular que no hay librerías disponibles
            with patch('app.services.multilingual_service.fasttext', side_effect=ImportError), \
                 patch('app.services.multilingual_service.langdetect', side_effect=ImportError):
                
                # Ejecutar
                await language_detector.initialize()
                
                # Verificar
                assert language_detector.loaded == True
                assert language_detector.backend == "basic"
                assert mock_logger.warning.called


class TestMultilingualNLPService:
    """Tests para servicio multilingüe."""
    
    async def test_process_with_language_detection(self, multilingual_service):
        """Test para procesamiento con detección de idioma."""
        # Mock para detector de idioma
        multilingual_service.language_detector.detect_language = AsyncMock(return_value={
            "language": "en",
            "confidence": 0.85,
            "supported": True
        })
        
        text = "Hello, I need a room"
        
        # Ejecutar
        result = await multilingual_service.process_with_language_detection(text)
        
        # Verificar
        assert result["language_code"] == "en"
        assert result["language_confidence"] == 0.85
        assert result["original_language"] == "en"
        assert result["text"] == text
    
    async def test_process_with_unsupported_language(self, multilingual_service):
        """Test para procesamiento con idioma no soportado."""
        # Mock para detector de idioma - detecta francés (no soportado)
        multilingual_service.language_detector.detect_language = AsyncMock(return_value={
            "language": "fr",
            "confidence": 0.9,
            "supported": False
        })
        
        multilingual_service.default_language = SupportedLanguage.SPANISH
        
        text = "Bonjour, je voudrais une chambre"
        
        # Ejecutar
        result = await multilingual_service.process_with_language_detection(text)
        
        # Verificar - debería usar el idioma por defecto
        assert result["language_code"] == "es"
        assert result["original_language"] == "fr"
    
    def test_get_language_specific_templates(self, multilingual_service):
        """Test para plantillas específicas por idioma."""
        # Plantilla en español
        template_es = multilingual_service.get_language_specific_templates("greeting", "es")
        assert "Hola" in template_es
        
        # Plantilla en inglés
        template_en = multilingual_service.get_language_specific_templates("greeting", "en")
        assert "Hello" in template_en
        
        # Plantilla en portugués
        template_pt = multilingual_service.get_language_specific_templates("greeting", "pt")
        assert "Olá" in template_pt
        
        # Idioma no soportado (debería usar español como fallback)
        template_fr = multilingual_service.get_language_specific_templates("greeting", "fr")
        assert "Hola" in template_fr
        
        # Plantilla que no existe
        template_unknown = multilingual_service.get_language_specific_templates("unknown_template", "es")
        assert template_unknown == ""
    
    def test_supported_language_enum(self):
        """Test para enum de idiomas soportados."""
        # Verificar valores individuales
        assert SupportedLanguage.SPANISH == "es"
        assert SupportedLanguage.ENGLISH == "en"
        assert SupportedLanguage.PORTUGUESE == "pt"
        
        # Verificar método para obtener todos
        all_langs = SupportedLanguage.get_all()
        assert "es" in all_langs
        assert "en" in all_langs
        assert "pt" in all_langs
        assert len(all_langs) == 3


@pytest.mark.asyncio
async def test_get_multilingual_nlp_service():
    """Test para el getter global del servicio."""
    with patch('app.services.multilingual_service.MultilingualNLPService') as MockService:
        mock_instance = MockService.return_value
        mock_instance.language_detector = MagicMock()
        mock_instance.language_detector.loaded = False
        
        # Ejecutar
        service = await get_multilingual_nlp_service()
        
        # Verificar
        assert service == mock_instance
        assert mock_instance.initialize.called