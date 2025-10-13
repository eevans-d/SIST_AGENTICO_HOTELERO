"""
Tests unitarios para el método _escalate_to_staff del Orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService


@pytest.fixture
def mock_pms_adapter():
    """Mock del PMS adapter"""
    return AsyncMock()


@pytest.fixture
def mock_session_manager():
    """Mock del session manager"""
    manager = AsyncMock(spec=SessionManager)
    manager.save_session = AsyncMock()
    return manager


@pytest.fixture
def mock_lock_service():
    """Mock del lock service"""
    return AsyncMock(spec=LockService)


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service):
    """Instancia del orchestrator con mocks"""
    return Orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service)


@pytest.fixture
def sample_message():
    """Mensaje de prueba"""
    return UnifiedMessage(
        message_id="msg-test-123",
        user_id="+34612345678",
        canal="whatsapp",
        texto="¡URGENTE! Necesito ayuda con mi reserva",
        tipo="text",
        timestamp_iso="2025-10-13T10:00:00Z",
        metadata={"detected_language": "es"}
    )


@pytest.fixture
def sample_session():
    """Sesión de prueba"""
    return {
        "user_id": "+34612345678",
        "history": [
            {"user": "Hola", "bot": "¿En qué puedo ayudarte?"},
            {"user": "Necesito cambiar mi reserva", "bot": "Déjame verificar..."}
        ],
        "intent": "modificar_reserva",
        "entities": {}
    }


class TestEscalateToStaff:
    """Tests para el método _escalate_to_staff"""
    
    @pytest.mark.asyncio
    async def test_escalate_urgent_after_hours(
        self,
        orchestrator,
        sample_message,
        sample_session
    ):
        """Test: Escalamiento por urgencia fuera de horario"""
        with patch('app.services.orchestrator.alert_manager') as mock_alert_manager:
            mock_alert_manager.send_alert = AsyncMock()
            
            result = await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="urgent_after_hours",
                intent="modificar_reserva",
                session_data=sample_session
            )
            
            # Verificar estructura de respuesta
            assert result["response_type"] == "text"
            assert "escalated" in result
            assert result["escalated"] is True
            assert "escalation_id" in result
            assert result["escalation_id"].startswith("ESC-")
            
            # Verificar que se llamó al alert manager
            mock_alert_manager.send_alert.assert_called_once()
            call_args = mock_alert_manager.send_alert.call_args[0][0]
            assert call_args["metric"] == "conversation_escalation"
            assert call_args["level"] == "warning"
            assert call_args["user_id"] == "+34612345678"
    
    @pytest.mark.asyncio
    async def test_escalate_nlp_failure(
        self,
        orchestrator,
        sample_message,
        sample_session
    ):
        """Test: Escalamiento por fallo de NLP"""
        with patch('app.services.orchestrator.alert_manager') as mock_alert_manager:
            mock_alert_manager.send_alert = AsyncMock()
            
            result = await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="nlp_failure",
                intent="unknown",
                session_data=sample_session
            )
            
            assert result["escalated"] is True
            assert "content" in result
    
    @pytest.mark.asyncio
    async def test_escalate_updates_session(
        self,
        orchestrator,
        mock_session_manager,
        sample_message,
        sample_session
    ):
        """Test: Escalamiento actualiza la sesión correctamente"""
        with patch('app.services.orchestrator.alert_manager'):
            result = await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="urgent_after_hours",
                intent="modificar_reserva",
                session_data=sample_session
            )
            
            # Verificar que se guardó la sesión
            mock_session_manager.save_session.assert_called_once()
            call_args = mock_session_manager.save_session.call_args
            
            # Verificar que la sesión tiene los flags de escalamiento
            saved_data = call_args[1]["data"]
            assert saved_data["escalated"] is True
            assert "escalation_timestamp" in saved_data
            assert saved_data["escalation_reason"] == "urgent_after_hours"
    
    @pytest.mark.asyncio
    async def test_escalate_handles_alert_failure(
        self,
        orchestrator,
        sample_message,
        sample_session,
        caplog
    ):
        """Test: Manejo de fallo al enviar alerta"""
        with patch('app.services.orchestrator.alert_manager') as mock_alert_manager:
            mock_alert_manager.send_alert = AsyncMock(side_effect=Exception("Network error"))
            
            # No debe fallar aunque la alerta falle
            result = await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="urgent_after_hours",
                intent="modificar_reserva",
                session_data=sample_session
            )
            
            # Debe retornar respuesta válida
            assert result["escalated"] is True
            
            # Debe haber loggeado el error
            assert "alert_send_failed" in caplog.text
    
    @pytest.mark.asyncio
    async def test_escalate_handles_session_save_failure(
        self,
        orchestrator,
        mock_session_manager,
        sample_message,
        sample_session,
        caplog
    ):
        """Test: Manejo de fallo al guardar sesión"""
        mock_session_manager.save_session = AsyncMock(side_effect=Exception("DB error"))
        
        with patch('app.services.orchestrator.alert_manager'):
            # No debe fallar aunque el guardado de sesión falle
            result = await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="urgent_after_hours",
                intent="modificar_reserva",
                session_data=sample_session
            )
            
            # Debe retornar respuesta válida
            assert result["escalated"] is True
            
            # Debe haber loggeado el error
            assert "session_save_failed" in caplog.text
    
    @pytest.mark.asyncio
    async def test_escalate_includes_context(
        self,
        orchestrator,
        sample_message,
        sample_session
    ):
        """Test: El escalamiento incluye contexto completo"""
        with patch('app.services.orchestrator.alert_manager') as mock_alert_manager:
            mock_alert_manager.send_alert = AsyncMock()
            
            sample_message.tenant_id = "hotel-123"
            
            await orchestrator._escalate_to_staff(
                message=sample_message,
                reason="urgent_after_hours",
                intent="modificar_reserva",
                session_data=sample_session
            )
            
            # Verificar contexto en la alerta
            call_args = mock_alert_manager.send_alert.call_args[0][0]
            context = call_args["context"]
            
            assert context["user_id"] == "+34612345678"
            assert context["channel"] == "whatsapp"
            assert context["intent"] == "modificar_reserva"
            assert context["reason"] == "urgent_after_hours"
            assert "session_history" in context
            assert len(context["session_history"]) <= 5  # Últimos 5 mensajes
            assert context["metadata"]["tenant_id"] == "hotel-123"
    
    @pytest.mark.asyncio
    async def test_escalate_different_reasons(
        self,
        orchestrator,
        sample_message,
        sample_session
    ):
        """Test: Diferentes razones generan respuestas apropiadas"""
        with patch('app.services.orchestrator.alert_manager'):
            # Test cada razón
            reasons = ["urgent_after_hours", "nlp_failure", "critical_error"]
            
            for reason in reasons:
                result = await orchestrator._escalate_to_staff(
                    message=sample_message,
                    reason=reason,
                    intent="test",
                    session_data=sample_session
                )
                
                assert result["escalated"] is True
                assert "content" in result
                assert len(result["content"]) > 0  # Debe tener mensaje


@pytest.mark.asyncio
async def test_escalate_metrics_recorded(orchestrator, sample_message, sample_session):
    """Test: Métricas de Prometheus se registran correctamente"""
    with patch('app.services.orchestrator.alert_manager'), \
         patch('app.services.orchestrator.escalations_total') as mock_counter:
        
        await orchestrator._escalate_to_staff(
            message=sample_message,
            reason="urgent_after_hours",
            intent="test",
            session_data=sample_session
        )
        
        # Verificar que se incrementó el contador
        mock_counter.labels.assert_called_once_with(
            reason="urgent_after_hours",
            channel="whatsapp"
        )
        mock_counter.labels.return_value.inc.assert_called_once()
