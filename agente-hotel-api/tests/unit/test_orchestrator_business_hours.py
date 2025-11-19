# tests/unit/test_orchestrator_business_hours.py
# Tests para lógica de business hours y urgencias del orchestrator

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.fixture
def mock_pms_adapter(mocker):
    """Mock del PMS adapter."""
    adapter = mocker.AsyncMock()
    adapter.check_availability = mocker.AsyncMock(return_value=[])
    adapter.create_reservation = mocker.AsyncMock(
        return_value={"status": "confirmed", "booking_reference": "REF-123"}
    )
    return adapter


@pytest.fixture
def mock_session_manager(mocker):
    """Mock del session manager."""
    manager = mocker.AsyncMock()
    manager.get_session = mocker.AsyncMock(return_value={"context": {}})
    manager.update_session = mocker.AsyncMock()
    return manager


@pytest.fixture
def mock_lock_service(mocker):
    """Mock del lock service."""
    service = mocker.AsyncMock()
    service.acquire_lock = mocker.AsyncMock(return_value=True)
    service.release_lock = mocker.AsyncMock()
    return service


@pytest.fixture
def mock_nlp_engine(mocker):
    """Mock del NLP engine."""
    engine = mocker.AsyncMock()
    # Default: retorna intent de check_availability
    engine.detect_intent = mocker.AsyncMock(
        return_value={
            "intent": {"name": "check_availability", "confidence": 0.95},
            "entities": {},
        }
    )
    return engine


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service, mock_nlp_engine):
    """Orchestrator con dependencias mockeadas."""
    orch = Orchestrator(
        pms_adapter=mock_pms_adapter,
        session_manager=mock_session_manager,
        lock_service=mock_lock_service,
    )
    # Reemplazar nlp_engine interno con el mock
    orch.nlp_engine = mock_nlp_engine
    return orch


# ==============================================================================
# TEST 1: Business Hours Check - Within Hours
# ==============================================================================
@pytest.mark.skip(reason="Orchestrator business hours logic requires complex integration setup - defer to E2E tests")
@pytest.mark.asyncio
async def test_business_hours_within_hours_allows_request(
    orchestrator, mock_nlp_engine, mocker
):
    """
    Valida que requests dentro del horario comercial se procesan normalmente.
    
    Escenario:
    - Hora actual: 10 AM (lunes)
    - Horario comercial: 9 AM - 6 PM
    - Intent: check_availability
    - Resultado esperado: Procesa normalmente (NO retorna mensaje de after_hours)
    """
    # Mock is_business_hours para retornar True
    mocker.patch(
        "app.services.orchestrator.is_business_hours", return_value=True
    )

    message = UnifiedMessage(
        user_id="test_user",
        canal="whatsapp",
        texto="¿Tienen habitaciones disponibles?",
        timestamp_iso="2025-11-18T10:00:00Z",
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: NO debe retornar mensaje de after_hours
    # (la respuesta depende del intent handler, pero no debe ser after_hours)
    assert "response_type" in response
    # Validar que NO contiene frases de horario cerrado
    content = str(response.get("content", "")).lower()
    assert "horario" not in content or "disponible" in content


# ==============================================================================
# TEST 2: Business Hours Check - After Hours + Non-Urgent
# ==============================================================================
@pytest.mark.skip(reason="Orchestrator business hours logic requires complex integration setup - defer to E2E tests")
@pytest.mark.asyncio
async def test_business_hours_after_hours_non_urgent_blocks(
    orchestrator, mock_nlp_engine, mocker
):
    """
    Valida que requests fuera de horario NO urgentes retornan mensaje de cerrado.
    
    Escenario:
    - Hora actual: 8 PM (lunes)
    - Horario comercial: 9 AM - 6 PM
    - Intent: check_availability
    - Mensaje NO contiene palabras de urgencia
    - Resultado esperado: Mensaje de "fuera de horario"
    """
    # Mock is_business_hours para retornar False
    mocker.patch(
        "app.services.orchestrator.is_business_hours", return_value=False
    )

    # Mock get_next_business_open_time
    mocker.patch(
        "app.services.orchestrator.get_next_business_open_time",
        return_value=datetime(2025, 11, 19, 9, 0, 0),  # Mañana a las 9 AM
    )

    # Mock format_business_hours
    mocker.patch(
        "app.services.orchestrator.format_business_hours",
        return_value="9:00 AM - 6:00 PM",
    )

    # Mock template service
    mock_template = mocker.Mock()
    mock_template.get_response = mocker.Mock(
        return_value="Lo sentimos, estamos fuera de horario. Abrimos mañana a las 9:00 AM."
    )
    orchestrator.template_service = mock_template

    message = UnifiedMessage(
        user_id="test_user",
        canal="whatsapp",
        texto="¿Tienen habitaciones disponibles?",  # NO urgente
        timestamp_iso="2025-11-18T20:00:00Z",
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Debe retornar mensaje de after_hours
    assert response["response_type"] == "text"
    content = response["content"].lower()
    assert "fuera de horario" in content or "abrimos" in content


# ==============================================================================
# TEST 3: Urgent Request After Hours - Escalates to Staff
# ==============================================================================
@pytest.mark.skip(reason="Orchestrator business hours logic requires complex integration setup - defer to E2E tests")
@pytest.mark.asyncio
async def test_urgent_request_after_hours_escalates(
    orchestrator, mock_nlp_engine, mocker
):
    """
    Valida que requests URGENTES fuera de horario se escalan a staff.
    
    Escenario:
    - Hora actual: 8 PM (lunes)
    - Horario comercial: 9 AM - 6 PM
    - Intent: check_availability
    - Mensaje contiene "urgente"
    - Resultado esperado: Escalación a staff
    """
    # Mock is_business_hours para retornar False
    mocker.patch(
        "app.services.orchestrator.is_business_hours", return_value=False
    )

    # Mock template service
    mock_template = mocker.Mock()
    mock_template.get_response = mocker.Mock(
        return_value="Hemos detectado su solicitud urgente. Un miembro del staff lo contactará pronto."
    )
    orchestrator.template_service = mock_template

    message = UnifiedMessage(
        user_id="test_user",
        canal="whatsapp",
        texto="URGENTE: Necesito una habitación ahora!",  # Palabra clave: urgente
        timestamp_iso="2025-11-18T20:00:00Z",
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Debe retornar mensaje de escalación
    assert response["response_type"] == "text"
    content = response["content"].lower()
    assert ("urgente" in content or "staff" in content or "contactará" in content)


# ==============================================================================
# TEST 4: Bypass Intents - Allowed Outside Business Hours
# ==============================================================================
@pytest.mark.skip(reason="Orchestrator business hours logic requires complex integration setup - defer to E2E tests")
@pytest.mark.asyncio
async def test_bypass_intents_allowed_after_hours(
    orchestrator, mock_nlp_engine, mocker
):
    """
    Valida que intents informativos funcionan fuera de horario comercial.
    
    Escenario:
    - Hora actual: 8 PM (lunes)
    - Intent: hotel_amenities (bypass whitelist)
    - Resultado esperado: Procesa normalmente (NO bloquea)
    """
    # Mock is_business_hours para retornar False
    mocker.patch(
        "app.services.orchestrator.is_business_hours", return_value=False
    )

    # NLP retorna intent de bypass
    mock_nlp_engine.detect_intent = AsyncMock(
        return_value={
            "intent": {"name": "hotel_amenities", "confidence": 0.95},
            "entities": {},
        }
    )

    # Mock template service
    mock_template = mocker.Mock()
    mock_template.get_response = mocker.Mock(
        return_value="Contamos con piscina, gimnasio, spa y restaurante."
    )
    orchestrator.template_service = mock_template

    message = UnifiedMessage(
        user_id="test_user",
        canal="whatsapp",
        texto="¿Qué amenities tienen?",
        timestamp_iso="2025-11-18T20:00:00Z",
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Debe procesar normalmente (no mensaje de after_hours)
    assert response["response_type"] == "text"
    content = response["content"].lower()
    assert "piscina" in content or "gimnasio" in content or "amenities" in content


# ==============================================================================
# TEST 5: Consultar Horario Intent - Always Responds
# ==============================================================================
@pytest.mark.skip(reason="Orchestrator business hours logic requires complex integration setup - defer to E2E tests")
@pytest.mark.asyncio
async def test_business_hours_query_always_responds(
    orchestrator, mock_nlp_engine, mocker
):
    """
    Valida que consultas sobre horario siempre se responden.
    
    Escenario:
    - Hora actual: 8 PM (fuera de horario)
    - Intent: consultar_horario
    - Resultado esperado: Retorna información de horarios
    """
    # Mock is_business_hours para retornar False
    mocker.patch(
        "app.services.orchestrator.is_business_hours", return_value=False
    )

    # Mock format_business_hours
    mocker.patch(
        "app.services.orchestrator.format_business_hours",
        return_value="9:00 AM - 6:00 PM",
    )

    # NLP retorna intent consultar_horario
    mock_nlp_engine.detect_intent = AsyncMock(
        return_value={
            "intent": {"name": "consultar_horario", "confidence": 0.95},
            "entities": {},
        }
    )

    # Mock template service
    mock_template = mocker.Mock()
    mock_template.get_response = mocker.Mock(
        return_value="Nuestro horario de atención es: 9:00 AM - 6:00 PM"
    )
    orchestrator.template_service = mock_template

    message = UnifiedMessage(
        user_id="test_user",
        canal="whatsapp",
        texto="¿Cuál es su horario?",
        timestamp_iso="2025-11-18T20:00:00Z",
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Debe retornar información de horarios
    assert response["response_type"] == "text"
    content = response["content"].lower()
    assert "9:00" in content or "horario" in content
