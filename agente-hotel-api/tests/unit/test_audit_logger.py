"""
Tests unitarios para AuditLogger y persistencia en PostgreSQL
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.services.security.audit_logger import AuditLogger, AuditEventType
from app.models.audit_log import AuditLog


@pytest.fixture
def audit_logger():
    """Instancia del audit logger"""
    return AuditLogger()


@pytest.fixture
def sample_audit_data():
    """Datos de auditoría de prueba"""
    return {
        "event_type": AuditEventType.ESCALATION,
        "user_id": "+34612345678",
        "ip_address": "192.168.1.100",
        "resource": "/api/webhooks/whatsapp",
        "details": {"reason": "urgent_after_hours", "intent": "modificar_reserva"},
        "tenant_id": "hotel-123",
        "severity": "warning",
    }


class TestAuditLogger:
    """Tests para AuditLogger"""

    @pytest.mark.asyncio
    async def test_log_event_creates_db_record(self, audit_logger, sample_audit_data):
        """Test: log_event crea registro en PostgreSQL"""
        with patch("app.services.security.audit_logger.AsyncSessionFactory") as mock_factory:
            # Mock de la sesión de DB
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            await audit_logger.log_event(**sample_audit_data)

            # Verificar que se agregó un AuditLog
            mock_session.add.assert_called_once()
            added_log = mock_session.add.call_args[0][0]

            assert isinstance(added_log, AuditLog)
            assert added_log.event_type == "escalation"
            assert added_log.user_id == "+34612345678"
            assert added_log.ip_address == "192.168.1.100"
            assert added_log.tenant_id == "hotel-123"
            assert added_log.severity == "warning"

            # Verificar que se hizo commit
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_handles_db_failure(self, audit_logger, sample_audit_data, caplog):
        """Test: Manejo de fallo de persistencia en DB"""
        with patch("app.services.security.audit_logger.AsyncSessionFactory") as mock_factory:
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock(side_effect=Exception("DB connection failed"))
            mock_factory.return_value.__aenter__.return_value = mock_session

            # No debe lanzar excepción
            await audit_logger.log_event(**sample_audit_data)

            # Debe haber loggeado el error
            assert "persistence_failed" in caplog.text
            assert "DB connection failed" in caplog.text

    @pytest.mark.asyncio
    async def test_log_event_with_minimal_data(self, audit_logger):
        """Test: log_event funciona con datos mínimos"""
        with patch("app.services.security.audit_logger.AsyncSessionFactory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            # Solo event_type es requerido
            await audit_logger.log_event(event_type=AuditEventType.LOGIN_SUCCESS)

            # Verificar que se creó el registro
            mock_session.add.assert_called_once()
            added_log = mock_session.add.call_args[0][0]

            assert added_log.event_type == "login_success"
            assert added_log.user_id is None
            assert added_log.ip_address is None

    @pytest.mark.asyncio
    async def test_log_event_all_event_types(self, audit_logger):
        """Test: Todos los tipos de evento son soportados"""
        with patch("app.services.security.audit_logger.AsyncSessionFactory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            event_types = [
                AuditEventType.LOGIN_SUCCESS,
                AuditEventType.LOGIN_FAILED,
                AuditEventType.ACCESS_DENIED,
                AuditEventType.DATA_ACCESS,
                AuditEventType.DATA_MODIFICATION,
                AuditEventType.RATE_LIMIT_EXCEEDED,
                AuditEventType.SUSPICIOUS_ACTIVITY,
                AuditEventType.ESCALATION,
                AuditEventType.PMS_ERROR,
                AuditEventType.CIRCUIT_BREAKER_OPEN,
            ]

            for event_type in event_types:
                await audit_logger.log_event(event_type=event_type, user_id="test_user")

            # Verificar que se crearon todos los registros
            assert mock_session.add.call_count == len(event_types)

    @pytest.mark.asyncio
    async def test_log_event_preserves_details_json(self, audit_logger):
        """Test: Los detalles JSON se preservan correctamente"""
        with patch("app.services.security.audit_logger.AsyncSessionFactory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            complex_details = {
                "nested": {"data": "value", "array": [1, 2, 3], "bool": True},
                "timestamp": "2025-10-13T10:00:00Z",
            }

            await audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION, user_id="test_user", details=complex_details
            )

            added_log = mock_session.add.call_args[0][0]
            assert added_log.details == complex_details


class TestAuditLogModel:
    """Tests para el modelo AuditLog"""

    def test_audit_log_creation(self):
        """Test: Creación básica de AuditLog"""
        log = AuditLog(
            timestamp=datetime.now(timezone.utc),
            event_type="login_success",
            user_id="test_user",
            ip_address="127.0.0.1",
            resource="/api/login",
            details={"browser": "Chrome"},
            tenant_id="hotel-123",
            severity="info",
        )

        assert log.event_type == "login_success"
        assert log.user_id == "test_user"
        assert log.severity == "info"

    def test_audit_log_to_dict(self):
        """Test: Serialización a diccionario"""
        now = datetime.now(timezone.utc)
        log = AuditLog(
            id=1,
            timestamp=now,
            event_type="escalation",
            user_id="+34612345678",
            ip_address="192.168.1.100",
            resource="/api/webhooks",
            details={"reason": "urgent"},
            tenant_id="hotel-123",
            severity="warning",
            created_at=now,
        )

        result = log.to_dict()

        assert result["id"] == 1
        assert result["event_type"] == "escalation"
        assert result["user_id"] == "+34612345678"
        assert result["tenant_id"] == "hotel-123"
        assert result["severity"] == "warning"
        assert result["details"]["reason"] == "urgent"
        assert isinstance(result["timestamp"], str)  # ISO format

    def test_audit_log_repr(self):
        """Test: Representación string"""
        log = AuditLog(id=1, timestamp=datetime.now(timezone.utc), event_type="login_failed", user_id="test_user")

        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert "id=1" in repr_str
        assert "login_failed" in repr_str
        assert "test_user" in repr_str


@pytest.mark.asyncio
async def test_get_audit_logger():
    """Test: Función get_audit_logger retorna instancia correcta"""
    from app.services.security.audit_logger import get_audit_logger, audit_logger

    result = await get_audit_logger()
    assert result is audit_logger
    assert isinstance(result, AuditLogger)


class TestAuditLogIntegration:
    """Tests de integración con base de datos real"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_log_full_cycle(self):
        """Test de integración: Crear, recuperar y verificar audit log"""
        from app.core.database import AsyncSessionFactory

        async with AsyncSessionFactory() as session:
            # Crear log
            log = AuditLog(
                timestamp=datetime.now(timezone.utc),
                event_type="test_event",
                user_id="integration_test_user",
                details={"test": True},
                severity="info",
            )

            session.add(log)
            await session.commit()

            log_id = log.id

            # Recuperar log
            from sqlalchemy import select

            result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
            retrieved_log = result.scalar_one_or_none()

            assert retrieved_log is not None
            assert retrieved_log.event_type == "test_event"
            assert retrieved_log.user_id == "integration_test_user"
            assert retrieved_log.details["test"] is True

            # Limpiar
            await session.delete(retrieved_log)
            await session.commit()
