"""
[PROMPT 2.5 + E.3] tests/integration/test_nlp_integration.py
Integration Tests for NLP Engine with Rasa
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from app.services.nlp_engine import NLPEngine
from app.services.entity_extractors import (
    DateExtractor,
    NumberExtractor,
    RoomTypeExtractor,
    AmenityExtractor,
    extract_all_entities
)


# ==================== NLP Engine Tests ====================

class TestNLPEngine:
    """Test NLP Engine with Rasa integration."""
    
    @pytest.fixture
    def mock_rasa_agent(self):
        """Mock Rasa Agent for testing."""
        agent = AsyncMock()
        agent.parse_message = AsyncMock()
        return agent
    
    @pytest.fixture
    def nlp_engine_with_mock(self, mock_rasa_agent):
        """NLP Engine with mocked Rasa Agent."""
        engine = NLPEngine(model_path=None)  # Will use fallback
        engine.agent = mock_rasa_agent
        engine.model_version = "test_v1"
        return engine
    
    @pytest.mark.asyncio
    async def test_process_message_check_availability(self, nlp_engine_with_mock):
        """Test intent classification for check_availability."""
        # Mock Rasa response
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.92},
            "entities": [
                {"entity": "date", "value": "2025-10-15", "start": 20, "end": 30}
            ]
        }
        
        result = await nlp_engine_with_mock.process_message(
            "¿Hay disponibilidad para el 15 de octubre?"
        )
        
        assert result["intent"]["name"] == "check_availability"
        assert result["intent"]["confidence"] == 0.92
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity"] == "date"
        assert result["model_version"] == "test_v1"
        assert "fallback" not in result
    
    @pytest.mark.asyncio
    async def test_process_message_make_reservation(self, nlp_engine_with_mock):
        """Test intent classification for make_reservation."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "make_reservation", "confidence": 0.89},
            "entities": [
                {"entity": "date", "value": "2025-10-20", "start": 15, "end": 25},
                {"entity": "number", "value": "2", "start": 30, "end": 31}
            ]
        }
        
        result = await nlp_engine_with_mock.process_message(
            "Quiero reservar para el 20 de octubre para 2 personas"
        )
        
        assert result["intent"]["name"] == "make_reservation"
        assert result["intent"]["confidence"] == 0.89
        assert len(result["entities"]) == 2
    
    @pytest.mark.asyncio
    async def test_process_message_cancel_reservation(self, nlp_engine_with_mock):
        """Test intent classification for cancel_reservation."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "cancel_reservation", "confidence": 0.95},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message(
            "Necesito cancelar mi reserva"
        )
        
        assert result["intent"]["name"] == "cancel_reservation"
        assert result["intent"]["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_process_message_ask_price(self, nlp_engine_with_mock):
        """Test intent classification for ask_price."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "ask_price", "confidence": 0.87},
            "entities": [
                {"entity": "room_type", "value": "doble", "start": 20, "end": 25}
            ]
        }
        
        result = await nlp_engine_with_mock.process_message(
            "Cuánto cuesta la habitación doble?"
        )
        
        assert result["intent"]["name"] == "ask_price"
        assert result["intent"]["confidence"] == 0.87
    
    @pytest.mark.asyncio
    async def test_process_message_low_confidence(self, nlp_engine_with_mock):
        """Test low confidence intent handling."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.42},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message(
            "algo para el finde?"
        )
        
        assert result["intent"]["confidence"] == 0.42
        
        # Check low confidence handler
        handler_result = nlp_engine_with_mock.handle_low_confidence(result["intent"])
        assert handler_result is not None
        assert "response" in handler_result
        assert handler_result["requires_human"] is False
    
    @pytest.mark.asyncio
    async def test_process_message_very_low_confidence(self, nlp_engine_with_mock):
        """Test very low confidence (requires human)."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "unknown", "confidence": 0.18},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message(
            "asdfghjkl blablabla"
        )
        
        assert result["intent"]["confidence"] == 0.18
        
        handler_result = nlp_engine_with_mock.handle_low_confidence(result["intent"])
        assert handler_result is not None
        assert handler_result["requires_human"] is True
    
    @pytest.mark.asyncio
    async def test_process_message_no_agent_fallback(self):
        """Test fallback when no agent loaded."""
        engine = NLPEngine(model_path=None)
        engine.agent = None
        
        result = await engine.process_message("Hola, hay disponibilidad?")
        
        assert result["intent"]["name"] == "unknown"
        assert result["intent"]["confidence"] == 0.0
        assert result["fallback"] is True
        assert result["entities"] == []
    
    @pytest.mark.asyncio
    async def test_process_message_circuit_breaker_open(self, nlp_engine_with_mock):
        """Test circuit breaker open scenario."""
        # Simulate circuit breaker opening after failures
        nlp_engine_with_mock.agent.parse_message.side_effect = Exception("Rasa error")
        
        # First few calls will fail and open circuit breaker
        for _ in range(5):
            result = await nlp_engine_with_mock.process_message("test")
            # Should eventually return fallback
            assert "intent" in result
    
    @pytest.mark.asyncio
    async def test_multiple_intents_sequence(self, nlp_engine_with_mock):
        """Test sequence of different intents."""
        test_cases = [
            ("Hola", "greeting", 0.98),
            ("Hay disponibilidad?", "check_availability", 0.91),
            ("Cuánto cuesta?", "ask_price", 0.88),
            ("Tiene piscina?", "ask_amenities", 0.90),
            ("Quiero reservar", "make_reservation", 0.93),
            ("Gracias, chau", "goodbye", 0.96),
        ]
        
        for text, expected_intent, confidence in test_cases:
            nlp_engine_with_mock.agent.parse_message.return_value = {
                "intent": {"name": expected_intent, "confidence": confidence},
                "entities": []
            }
            
            result = await nlp_engine_with_mock.process_message(text)
            assert result["intent"]["name"] == expected_intent
            assert result["intent"]["confidence"] == confidence
    
    def test_get_model_info(self):
        """Test model info retrieval."""
        engine = NLPEngine(model_path=None)
        
        info = engine.get_model_info()
        
        assert "model_path" in info
        assert "model_version" in info
        assert "model_loaded_at" in info
        assert "agent_loaded" in info
        assert "fallback_mode" in info
        assert info["agent_loaded"] is False or info["agent_loaded"] is True


# ==================== Date Extractor Tests ====================

class TestDateExtractor:
    """Test DateExtractor for Spanish date patterns."""
    
    def test_extract_absolute_date(self):
        """Test extraction of absolute dates."""
        entities = [{"entity": "date", "value": "2025-10-15"}]
        text = "para el 15 de octubre"
        
        result = DateExtractor.extract(entities, text)
        
        assert result["check_in"] is not None
        assert result["check_in"].year == 2025
        assert result["check_in"].month == 10
        assert result["check_in"].day == 15
        assert result["check_out"] == result["check_in"] + timedelta(days=1)
    
    def test_extract_relative_date_manana(self):
        """Test extraction of 'mañana' (tomorrow)."""
        entities = []
        text = "hay disponibilidad para mañana?"
        
        result = DateExtractor.extract(entities, text)
        
        assert result["check_in"] is not None
        expected = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        assert result["check_in"].date() == expected.date()
    
    def test_extract_date_range_del_al(self):
        """Test extraction of date range 'del X al Y'."""
        entities = [
            {"entity": "date", "value": "2025-10-15"},
            {"entity": "date", "value": "2025-10-20"}
        ]
        text = "del 15 al 20 de octubre"
        
        result = DateExtractor.extract(entities, text)
        
        assert result["check_in"] is not None
        assert result["check_out"] is not None
        assert result["check_in"].day == 15
        assert result["check_out"].day == 20
    
    def test_extract_no_dates(self):
        """Test when no dates found."""
        entities = []
        text = "cuánto cuesta?"
        
        result = DateExtractor.extract(entities, text)
        
        assert result["check_in"] is None
        assert result["check_out"] is None


# ==================== Number Extractor Tests ====================

class TestNumberExtractor:
    """Test NumberExtractor for guests and nights."""
    
    def test_extract_guests_number(self):
        """Test extraction of guest count."""
        entities = [{"entity": "number", "value": "3"}]
        text = "para 3 personas"
        
        result = NumberExtractor.extract_guests(entities, text)
        
        assert result == 3
    
    def test_extract_guests_word(self):
        """Test extraction with Spanish number words."""
        entities = []
        text = "para dos personas"
        
        result = NumberExtractor.extract_guests(entities, text)
        
        assert result == 2
    
    def test_extract_guests_default(self):
        """Test default guest count when none specified."""
        entities = []
        text = "hay disponibilidad?"
        
        result = NumberExtractor.extract_guests(entities, text)
        
        assert result == 2  # Default
    
    def test_extract_nights(self):
        """Test extraction of nights count."""
        entities = []
        text = "por 3 noches"
        
        result = NumberExtractor.extract_nights(entities, text)
        
        assert result == 3
    
    def test_extract_nights_default(self):
        """Test default nights when none specified."""
        entities = []
        text = "hay disponibilidad?"
        
        result = NumberExtractor.extract_nights(entities, text)
        
        assert result == 1  # Default


# ==================== Room Type Extractor Tests ====================

class TestRoomTypeExtractor:
    """Test RoomTypeExtractor with synonyms."""
    
    def test_extract_room_type_doble(self):
        """Test extraction of 'doble' room type."""
        entities = [{"entity": "room_type", "value": "doble"}]
        text = "habitación doble"
        
        result = RoomTypeExtractor.extract(entities, text)
        
        assert result == "doble"
    
    def test_extract_room_type_synonym_matrimonial(self):
        """Test synonym 'matrimonial' → 'doble'."""
        entities = []
        text = "habitación matrimonial"
        
        result = RoomTypeExtractor.extract(entities, text)
        
        assert result == "doble"
    
    def test_extract_room_type_suite(self):
        """Test extraction of 'suite'."""
        entities = []
        text = "una suite por favor"
        
        result = RoomTypeExtractor.extract(entities, text)
        
        assert result == "suite"
    
    def test_extract_no_room_type(self):
        """Test when no room type mentioned."""
        entities = []
        text = "hay disponibilidad?"
        
        result = RoomTypeExtractor.extract(entities, text)
        
        assert result is None


# ==================== Amenity Extractor Tests ====================

class TestAmenityExtractor:
    """Test AmenityExtractor with synonyms."""
    
    def test_extract_amenity_piscina(self):
        """Test extraction of 'piscina'."""
        text = "tiene piscina?"
        
        result = AmenityExtractor.extract(text)
        
        assert "piscina" in result
    
    def test_extract_amenity_synonym_pileta(self):
        """Test synonym 'pileta' → 'piscina'."""
        text = "hay pileta?"
        
        result = AmenityExtractor.extract(text)
        
        assert "piscina" in result
    
    def test_extract_multiple_amenities(self):
        """Test extraction of multiple amenities."""
        text = "tiene piscina, gimnasio y wifi?"
        
        result = AmenityExtractor.extract(text)
        
        assert "piscina" in result
        assert "gimnasio" in result
        assert "wifi" in result
        assert len(result) == 3
    
    def test_extract_no_amenities(self):
        """Test when no amenities mentioned."""
        text = "cuánto cuesta?"
        
        result = AmenityExtractor.extract(text)
        
        assert len(result) == 0


# ==================== Combined Entity Extraction Tests ====================

class TestExtractAllEntities:
    """Test combined entity extraction."""
    
    def test_extract_all_entities_full(self):
        """Test extraction of all entity types."""
        text = "Necesito una doble para 3 personas del 15 al 20 con piscina y wifi"
        rasa_entities = [
            {"entity": "room_type", "value": "doble"},
            {"entity": "number", "value": "3"},
            {"entity": "date", "value": "2025-10-15"},
            {"entity": "date", "value": "2025-10-20"}
        ]
        
        result = extract_all_entities(text, rasa_entities)
        
        assert result["dates"]["check_in"] is not None
        assert result["dates"]["check_out"] is not None
        assert result["guests"] == 3
        assert result["room_type"] == "doble"
        assert "piscina" in result["amenities"]
        assert "wifi" in result["amenities"]
    
    def test_extract_all_entities_minimal(self):
        """Test extraction with minimal entities."""
        text = "hay disponibilidad?"
        rasa_entities = []
        
        result = extract_all_entities(text, rasa_entities)
        
        assert result["dates"]["check_in"] is None
        assert result["dates"]["check_out"] is None
        assert result["guests"] == 2  # Default
        assert result["nights"] == 1  # Default
        assert result["room_type"] is None
        assert len(result["amenities"]) == 0


# ==================== Edge Cases Tests ====================

class TestNLPEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_text(self, nlp_engine_with_mock):
        """Test processing empty text."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message("")
        
        assert result["intent"]["name"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_very_long_text(self, nlp_engine_with_mock):
        """Test processing very long text."""
        long_text = "hola " * 500  # 2500 characters
        
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "greeting", "confidence": 0.85},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message(long_text)
        
        assert result["intent"]["name"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_special_characters(self, nlp_engine_with_mock):
        """Test processing text with special characters."""
        text = "¿Hay disponibilidad? 🏨🌴☀️"
        
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.90},
            "entities": []
        }
        
        result = await nlp_engine_with_mock.process_message(text)
        
        assert result["intent"]["name"] == "check_availability"
    
    def test_date_extractor_invalid_date(self):
        """Test date extraction with invalid date."""
        entities = [{"entity": "date", "value": "invalid-date"}]
        text = "para una fecha invalida"
        
        result = DateExtractor.extract(entities, text)
        
        # Should handle gracefully
        assert isinstance(result, dict)


# ==================== Performance Tests ====================

class TestNLPPerformance:
    """Test NLP performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_confidence_buckets(self, nlp_engine_with_mock):
        """Test confidence bucket classification."""
        test_cases = [
            (0.25, "low"),
            (0.55, "medium"),
            (0.75, "high"),
            (0.92, "very_high"),
        ]
        
        for confidence, expected_bucket in test_cases:
            nlp_engine_with_mock.agent.parse_message.return_value = {
                "intent": {"name": "check_availability", "confidence": confidence},
                "entities": []
            }
            
            result = await nlp_engine_with_mock.process_message("test")
            bucket = nlp_engine_with_mock._get_confidence_bucket(result["intent"]["confidence"])
            
            assert bucket == expected_bucket
    
    @pytest.mark.asyncio
    async def test_entity_normalization(self, nlp_engine_with_mock):
        """Test entity normalization consistency."""
        nlp_engine_with_mock.agent.parse_message.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.90},
            "entities": [
                {
                    "entity": "date",
                    "value": "2025-10-15",
                    "start": 10,
                    "end": 20,
                    "confidence": 0.95,
                    "extractor": "DIETClassifier"
                }
            ]
        }
        
        result = await nlp_engine_with_mock.process_message("test message")
        
        entity = result["entities"][0]
        assert "entity" in entity
        assert "value" in entity
        assert "start" in entity
        assert "end" in entity
        assert "confidence" in entity
        assert "extractor" in entity
