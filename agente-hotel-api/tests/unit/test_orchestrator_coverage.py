import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, date, timezone
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.core.settings import settings

@pytest.fixture
def mock_pms_adapter():
    return AsyncMock()

@pytest.fixture
def mock_session_manager():
    manager = AsyncMock()
    manager.update_session = AsyncMock()
    return manager

@pytest.fixture
def mock_lock_service():
    return AsyncMock()

@pytest.fixture
def mock_audio_processor():
    processor = AsyncMock()
    processor.generate_audio_response = AsyncMock(return_value=b"fake_audio_data")
    return processor

@pytest.fixture
def mock_template_service():
    service = MagicMock()
    service.get_response.return_value = "Template response"
    service.get_interactive_buttons.return_value = {"type": "buttons"}
    service.get_interactive_list.return_value = {"type": "list"}
    return service

@pytest.fixture
def mock_feature_flag_service():
    service = AsyncMock()
    service.is_enabled.return_value = True
    return service

@pytest.fixture
def orchestrator(
    mock_pms_adapter,
    mock_session_manager,
    mock_lock_service,
    mock_audio_processor,
    mock_template_service,
    mock_feature_flag_service
):
    with patch("app.services.orchestrator.get_feature_flag_service", return_value=mock_feature_flag_service), \
         patch("app.services.orchestrator.AudioProcessor", return_value=mock_audio_processor), \
         patch("app.services.orchestrator.TemplateService", return_value=mock_template_service):
        
        orch = Orchestrator(
            pms_adapter=mock_pms_adapter,
            session_manager=mock_session_manager,
            lock_service=mock_lock_service
        )
        # Replace the auto-instantiated services with our mocks
        orch.audio_processor = mock_audio_processor
        orch.template_service = mock_template_service
        return orch

@pytest.mark.asyncio
async def test_handle_availability_with_audio_and_images(orchestrator, mock_audio_processor):
    # Setup
    nlp_result = {"intent": "check_availability", "entities": {}}
    session = {}
    message = UnifiedMessage(
        user_id="user123",
        texto="tengo disponibilidad?",
        canal="whatsapp",
        tipo="audio",
        metadata={"detected_language": "es"}
    )
    
    # Mock settings to enable room images
    with patch("app.services.orchestrator.settings.room_images_enabled", True), \
         patch("app.services.orchestrator.get_room_image_url", return_value="http://example.com/room.jpg"), \
         patch("app.services.orchestrator.validate_image_url", return_value=True):
        
        # Execute
        response = await orchestrator._handle_availability(
            nlp_result=nlp_result,
            session=session,
            message=message,
            respond_with_audio=True
        )
        
        # Verify
        assert response["response_type"] == "audio_with_image"
        assert response["audio_data"] == b"fake_audio_data"
        assert response["image_url"] == "http://example.com/room.jpg"
        mock_audio_processor.generate_audio_response.assert_called_once()

@pytest.mark.asyncio
async def test_handle_room_options_audio_flow(orchestrator, mock_audio_processor):
    # Setup
    nlp_result = {"intent": "show_room_options"}
    session = {}
    message = UnifiedMessage(
        user_id="user123",
        texto="opciones",
        canal="whatsapp",
        tipo="audio",
        metadata={"detected_language": "es"}
    )
    
    # Execute
    response = await orchestrator._handle_room_options(nlp_result, session, message)
    
    # Verify
    assert response["response_type"] == "audio"
    assert response["content"]["audio_data"] == b"fake_audio_data"
    assert "follow_up" in response["content"]
    assert response["content"]["follow_up"]["type"] == "interactive_list"

@pytest.mark.asyncio
async def test_handle_late_checkout_new_request_available(orchestrator, mock_pms_adapter, mock_session_manager):
    # Setup
    nlp_result = {"intent": "late_checkout"}
    session = {"booking_id": "BOOK123"}
    message = UnifiedMessage(user_id="user123", texto="late checkout", canal="whatsapp")
    
    mock_pms_adapter.check_late_checkout_availability.return_value = {
        "available": True,
        "fee": 20.0,
        "requested_time": "14:00"
    }
    
    # Execute
    response = await orchestrator._handle_late_checkout(nlp_result, session, message)
    
    # Verify
    assert response["response_type"] == "text"
    mock_pms_adapter.check_late_checkout_availability.assert_called_with(
        reservation_id="BOOK123",
        requested_checkout_time="14:00"  # Default constant
    )
    # Verify session update
    mock_session_manager.update_session.assert_called()
    call_args = mock_session_manager.update_session.call_args
    updated_session = call_args[0][1]
    assert "pending_late_checkout" in updated_session
    assert updated_session["pending_late_checkout"]["booking_id"] == "BOOK123"

@pytest.mark.asyncio
async def test_handle_late_checkout_confirmation(orchestrator, mock_pms_adapter, mock_session_manager):
    # Setup
    nlp_result = {"intent": "confirm"}
    session = {
        "pending_late_checkout": {
            "booking_id": "BOOK123",
            "checkout_time": "14:00",
            "fee": 20.0
        }
    }
    message = UnifiedMessage(user_id="user123", texto="si confirmar", canal="whatsapp")
    
    mock_pms_adapter.confirm_late_checkout.return_value = {"success": True}
    
    # Execute
    response = await orchestrator._handle_late_checkout(nlp_result, session, message)
    
    # Verify
    assert response["response_type"] == "text"
    mock_pms_adapter.confirm_late_checkout.assert_called_with(
        reservation_id="BOOK123",
        checkout_time="14:00"
    )
    # Verify session cleared
    mock_session_manager.update_session.assert_called()
    call_args = mock_session_manager.update_session.call_args
    updated_session = call_args[0][1]
    assert "pending_late_checkout" not in updated_session

@pytest.mark.asyncio
async def test_handle_review_response_positive(orchestrator):
    # Setup
    nlp_result = {"intent": "review_response"}
    session = {}
    message = UnifiedMessage(user_id="user123", texto="me encanto todo", canal="whatsapp")
    
    with patch("app.services.orchestrator.get_review_service") as mock_get_review_service:
        mock_service = AsyncMock()
        mock_service.process_review_response.return_value = {
            "success": True,
            "intent": "positive",
            "sentiment": 0.9
        }
        mock_get_review_service.return_value = mock_service
        
        # Execute
        response = await orchestrator._handle_review_request(nlp_result, session, message)
        
        # Verify
        assert response["response_type"] == "text"
        assert "enlaces" in response["content"]
        mock_service.process_review_response.assert_called_with(
            guest_id="user123",
            response_text="me encanto todo"
        )

@pytest.mark.asyncio
async def test_handle_review_checkout_detection(orchestrator):
    # Setup
    nlp_result = {"intent": "check_out_info"}
    session = {"booking_id": "BOOK123", "guest_name": "John"}
    message = UnifiedMessage(user_id="user123", texto="checkout", canal="whatsapp")
    
    with patch("app.services.orchestrator.get_review_service") as mock_get_review_service:
        mock_service = AsyncMock()
        mock_service.schedule_review_request.return_value = {
            "success": True,
            "request_id": "req123",
            "scheduled_time": "tomorrow"
        }
        mock_get_review_service.return_value = mock_service
        
        # Execute
        await orchestrator._handle_review_request(nlp_result, session, message)
        
        # Verify
        mock_service.schedule_review_request.assert_called()

@pytest.mark.asyncio
async def test_escalate_to_staff_urgent(orchestrator, mock_template_service):
    # Setup
    message = UnifiedMessage(user_id="user123", texto="ayuda urgente", canal="whatsapp")
    session = {"history": []}
    
    with patch("app.services.orchestrator.alert_manager.send_alert", new_callable=AsyncMock) as mock_send_alert:
        # Execute
        response = await orchestrator._escalate_to_staff(
            message=message,
            reason="urgent_after_hours",
            intent="emergency",
            session_data=session
        )
        
        # Verify
        assert response["escalated"] is True
        assert session["escalated"] is True
        mock_send_alert.assert_called()
        mock_template_service.get_response.assert_called_with("escalated_to_staff", next_business_time=ANY)

@pytest.mark.asyncio
async def test_handle_business_hours_urgent_after_hours(orchestrator):
    # Setup
    nlp_result = {"intent": "emergency"}
    session = {}
    message = UnifiedMessage(user_id="user123", texto="es urgente", canal="whatsapp")
    
    # Mock business hours to be closed
    with patch("app.services.orchestrator.is_business_hours", return_value=False), \
         patch("app.services.orchestrator.Orchestrator._escalate_to_staff", new_callable=AsyncMock) as mock_escalate:
        
        mock_escalate.return_value = {"response_type": "text", "content": "Escalated"}
        
        # Execute
        response = await orchestrator._handle_business_hours(nlp_result, session, message)
        
        # Verify
        mock_escalate.assert_called()
        assert response == {"response_type": "text", "content": "Escalated"}

@pytest.mark.asyncio
async def test_handle_business_hours_closed_non_urgent(orchestrator, mock_template_service, mock_audio_processor):
    # Setup
    nlp_result = {"intent": "check_availability"}
    session = {}
    message = UnifiedMessage(user_id="user123", texto="hola", canal="whatsapp")
    
    # Mock business hours to be closed
    with patch("app.services.orchestrator.is_business_hours", return_value=False):
        
        # Execute
        response = await orchestrator._handle_business_hours(nlp_result, session, message)
        
        # Verify
        assert response["response_type"] == "text"
        mock_template_service.get_response.assert_called()
        # Should not escalate
        assert "escalated" not in response or not response.get("escalated")

@pytest.mark.asyncio
async def test_handle_info_intent(orchestrator, mock_template_service):
    # Setup
    nlp_result = {"intent": "hotel_amenities"}
    session = {}
    message = UnifiedMessage(user_id="user123", texto="amenities", canal="whatsapp")
    
    # Execute
    response = await orchestrator._handle_info_intent(nlp_result, session, message)
    
    # Verify
    assert response["response_type"] == "text"
    mock_template_service.get_response.assert_called_with("hotel_amenities")
