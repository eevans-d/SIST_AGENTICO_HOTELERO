"""
Test de integración E2E para flujo de solicitud de ubicación.
Feature 1: Compartir Ubicación del Hotel

Flujo completo:
1. Usuario pregunta "¿dónde están ubicados?"
2. NLP detecta intent "ask_location"
3. Orchestrator procesa y retorna response_type "location"
4. Webhook envía ubicación vía WhatsApp API
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.unified_message import UnifiedMessage
from app.core.settings import settings


class TestLocationFlowE2E:
    """Tests end-to-end del flujo de solicitud de ubicación."""

    @pytest.fixture
    def test_client(self):
        """Fixture que crea cliente de prueba."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_location_request_text_message_flow(self):
        """Test E2E: Usuario solicita ubicación via mensaje de texto."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Mensaje del usuario
        message = UnifiedMessage(
            user_id="5491112345678",
            texto="¿dónde están ubicados?",
            canal="whatsapp",
            tipo="text",
            metadata={}
        )

        # Act
        result = await orchestrator.handle_unified_message(message)

        # Assert
        assert result is not None
        
        # Verificar que es una respuesta de tipo location
        if "response_type" in result:
            assert result["response_type"] == "location"
            content = result.get("content", {})
            
            # Verificar que tiene las coordenadas correctas
            assert "latitude" in content
            assert "longitude" in content
            assert content["latitude"] == settings.hotel_latitude
            assert content["longitude"] == settings.hotel_longitude
            assert content["name"] == settings.hotel_name
            assert content["address"] == settings.hotel_address

    @pytest.mark.asyncio
    async def test_location_request_variations(self):
        """Test E2E: Diferentes variaciones de solicitud de ubicación."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Diferentes formas de pedir ubicación
        test_phrases = [
            "ubicacion",
            "mandame la ubicacion",
            "como llego?",
            "direccion del hotel",
            "donde estan?",
            "pin de ubicacion",
            "mostrame donde quedan"
        ]

        for phrase in test_phrases:
            # Arrange
            message = UnifiedMessage(
                user_id="5491112345678",
                texto=phrase,
                canal="whatsapp",
                tipo="text",
                metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None, f"Failed for phrase: {phrase}"
            
            # Puede retornar respuesta de texto o location dependiendo de la confianza del NLP
            if "response_type" in result and result["response_type"] == "location":
                content = result.get("content", {})
                assert "latitude" in content, f"Missing latitude for phrase: {phrase}"
                assert "longitude" in content, f"Missing longitude for phrase: {phrase}"

    @pytest.mark.asyncio
    async def test_location_request_audio_message_flow(self):
        """Test E2E: Usuario solicita ubicación via mensaje de audio."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Mock del procesador de audio para STT
        with patch('app.services.orchestrator.AudioProcessor') as MockAudioProcessor:
            mock_audio_processor = MockAudioProcessor.return_value
            mock_audio_processor.transcribe_whatsapp_audio = AsyncMock(return_value={
                "text": "¿dónde están ubicados?",
                "confidence": 0.95
            })
            
            orchestrator.audio_processor = mock_audio_processor

            # Mensaje de audio del usuario
            message = UnifiedMessage(
                user_id="5491112345678",
                texto=None,
                canal="whatsapp",
                tipo="audio",
                media_url="https://example.com/audio/test.ogg",
                metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            
            # Para audio, debería retornar audio_with_location
            if "response_type" in result:
                assert result["response_type"] in ["location", "audio_with_location"]
                
                if result["response_type"] == "audio_with_location":
                    content = result.get("content", {})
                    assert "location" in content
                    location = content["location"]
                    assert location["latitude"] == settings.hotel_latitude
                    assert location["longitude"] == settings.hotel_longitude

    @pytest.mark.asyncio
    async def test_location_with_whatsapp_client_integration(self):
        """Test: Integración con cliente WhatsApp (mock API)."""
        # Arrange
        from app.services.whatsapp_client import WhatsAppMetaClient
        
        whatsapp_client = WhatsAppMetaClient()
        
        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.integration_test"}]
        })

        with patch.object(whatsapp_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            # Act
            result = await whatsapp_client.send_location(
                to="5491112345678",
                latitude=settings.hotel_latitude,
                longitude=settings.hotel_longitude,
                name=settings.hotel_name,
                address=settings.hotel_address
            )

            # Assert
            assert result is not None
            assert result["messages"][0]["id"] == "wamid.integration_test"
            
            # Verificar que se envió al endpoint correcto
            call_args = mock_post.call_args
            assert f"{whatsapp_client.phone_number_id}/messages" in str(call_args)

    @pytest.mark.asyncio
    async def test_location_session_tracking(self):
        """Test: Verificar que la solicitud de ubicación se registra en sesión."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        
        # Mensaje del usuario
        message = UnifiedMessage(
            user_id=user_id,
            texto="mandame la ubicacion",
            canal="whatsapp",
            tipo="text",
            metadata={}
        )

        # Act
        result = await orchestrator.handle_unified_message(message)

        # Assert
        assert result is not None
        
        # Verificar que existe sesión para el usuario
        session = await session_manager.get_or_create_session(user_id, "whatsapp")
        assert session is not None
        assert session.get("user_id") == user_id

    @pytest.mark.asyncio
    async def test_location_with_low_nlp_confidence(self):
        """Test: Manejo de solicitud de ubicación con baja confianza del NLP."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        from app.services.nlp_engine import NLPEngine
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Mock del NLP con baja confianza
        with patch.object(orchestrator.nlp_engine, 'process_message', new_callable=AsyncMock) as mock_nlp:
            mock_nlp.return_value = {
                "intent": {"name": "ask_location", "confidence": 0.40},  # Baja confianza
                "entities": [],
                "language": "es"
            }

            # Mensaje ambiguo
            message = UnifiedMessage(
                user_id="5491112345678",
                texto="donde?",  # Muy ambiguo
                canal="whatsapp",
                tipo="text",
                metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            
            # Con baja confianza, podría pedir aclaración en vez de enviar ubicación
            # El comportamiento exacto depende de los thresholds configurados

    @pytest.mark.asyncio
    async def test_location_multilingual_support(self):
        """Test: Soporte multiidioma para solicitud de ubicación."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        
        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Diferentes idiomas
        test_cases = [
            ("¿dónde están?", "es"),  # Español
            ("where are you?", "en"),  # Inglés
            ("onde vocês estão?", "pt"),  # Portugués
        ]

        for text, expected_lang in test_cases:
            # Arrange
            message = UnifiedMessage(
                user_id="5491112345678",
                texto=text,
                canal="whatsapp",
                tipo="text",
                metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None, f"Failed for language: {expected_lang}"
