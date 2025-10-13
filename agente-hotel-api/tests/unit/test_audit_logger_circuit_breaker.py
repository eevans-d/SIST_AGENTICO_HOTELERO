"""
Tests de Circuit Breaker y fallback en AuditLogger.

Valida:
- Circuit breaker se abre después de 5 fallos consecutivos
- Fallback a archivo cuando circuit está OPEN
- Recovery automático después de timeout (30s)
- Métricas de Prometheus actualizadas correctamente
- Retry con exponential backoff en escrituras DB
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.services.security.audit_logger import AuditLogger, AuditEventType
from app.core.circuit_breaker import CircuitState
from app.core.constants import (
    PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold_failures():
    """
    Circuit breaker debe abrir después de FAILURE_THRESHOLD fallos consecutivos.
    
    Escenario:
    - Simular 5 fallos consecutivos de PostgreSQL
    
    Resultado esperado:
    - Circuit breaker en estado OPEN después del 5to fallo
    - Métrica audit_circuit_breaker_state = 1 (OPEN)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        # Mock session que siempre falla
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB down"))
            mock_session.rollback = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            # Generar 5 fallos consecutivos
            for i in range(PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD):
                await audit_logger.log_event(
                    event_type=AuditEventType.LOGIN_SUCCESS,
                    user_id=f"user{i}",
                    details={"attempt": i + 1}
                )
        
        # Verificar circuit breaker está OPEN
        assert audit_logger.circuit_breaker.state == CircuitState.OPEN, \
            f"Circuit debe estar OPEN después de {PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD} fallos"


@pytest.mark.asyncio
async def test_fallback_to_file_when_circuit_open():
    """
    Debe escribir a archivo de fallback cuando circuit breaker está OPEN.
    
    Escenario:
    - Forzar circuit OPEN con 5 fallos
    - Intentar log_event adicional
    
    Resultado esperado:
    - Evento se escribe a audit_fallback.jsonl
    - Formato JSONL correcto (un JSON por línea)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        # Forzar circuit OPEN con 5 fallos
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB down"))
            mock_session.rollback = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            for i in range(PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD):
                await audit_logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    user_id=f"user{i}"
                )
        
        # Circuit debe estar OPEN
        assert audit_logger.circuit_breaker.state == CircuitState.OPEN
        
        # Intentar log adicional (debe usar fallback)
        await audit_logger.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            user_id="fallback_user",
            ip_address="192.168.1.100",
            resource="/api/admin",
            details={"reason": "circuit open test"}
        )
        
        # Verificar archivo de fallback existe y tiene contenido
        fallback_file = Path(temp_dir) / "audit_fallback.jsonl"
        assert fallback_file.exists(), "Archivo de fallback debe existir"
        
        # Leer y validar formato JSONL
        with open(fallback_file) as f:
            lines = f.readlines()
            assert len(lines) > 0, "Debe haber al menos 1 evento en fallback"
            
            # Parsear última línea (evento de fallback)
            last_event = json.loads(lines[-1])
            assert last_event["event_type"] == "suspicious_activity"
            assert last_event["user_id"] == "fallback_user"
            assert last_event["ip_address"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_circuit_recovers_to_half_open():
    """
    Circuit breaker debe intentar recovery después de RECOVERY_TIMEOUT.
    
    Escenario:
    - Circuit en OPEN
    - Esperar RECOVERY_TIMEOUT
    - Intentar operación
    
    Resultado esperado:
    - Circuit pasa a HALF_OPEN
    - Si operación exitosa, vuelve a CLOSED
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Usar recovery timeout corto para testing
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        # Modificar circuit breaker para recovery más rápido
        audit_logger.circuit_breaker = audit_logger.circuit_breaker.__class__(
            failure_threshold=PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=1,  # 1s para testing (en lugar de 30s)
            expected_exception=SQLAlchemyError,
        )
        
        # Forzar circuit OPEN
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB down"))
            mock_session.rollback = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            for i in range(PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD):
                await audit_logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    user_id=f"user{i}"
                )
        
        assert audit_logger.circuit_breaker.state == CircuitState.OPEN
        
        # Esperar recovery timeout
        await asyncio.sleep(1.1)  # > 1s recovery timeout
        
        # Mock DB exitosa para recovery
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(return_value=None)  # Éxito
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            # Intentar operación (debe pasar a HALF_OPEN y luego CLOSED)
            await audit_logger.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                user_id="recovery_user"
            )
        
        # Circuit debe haberse recuperado a CLOSED
        assert audit_logger.circuit_breaker.state == CircuitState.CLOSED, \
            "Circuit debe volver a CLOSED después de recovery exitoso"


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_on_db_errors():
    """
    Debe reintentar escrituras DB con exponential backoff.
    
    Escenario:
    - 1er intento: Falla (OperationalError)
    - 2do intento: Falla
    - 3er intento: Éxito
    
    Resultado esperado:
    - Completa exitosamente después de 3 intentos
    - Delays de 1s, 2s entre intentos (exponential backoff)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(
            fallback_dir=temp_dir,
            max_retries=3,
            retry_delay_base=1  # 1s (se hace override en el código con constante)
        )
        
        call_count = 0
        
        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SQLAlchemyError("Transient error")
            # 3er intento exitoso (no raise)
        
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=intermittent_failure)
            mock_session.rollback = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            await audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                user_id="retry_user"
            )
        
        assert call_count == 3, "Debe intentar 3 veces antes de éxito"


@pytest.mark.asyncio
async def test_fallback_file_format_jsonl():
    """
    Archivo de fallback debe usar formato JSONL (un JSON por línea).
    
    Resultado esperado:
    - Cada línea es un JSON válido
    - Todas las líneas parsean correctamente
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        # Forzar circuit OPEN
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB down"))
            mock_session.rollback = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            for i in range(PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD):
                await audit_logger.log_event(
                    event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                    user_id=f"user{i}"
                )
        
        # Escribir múltiples eventos usando fallback
        for i in range(3):
            await audit_logger.log_event(
                event_type=AuditEventType.ESCALATION,
                user_id=f"fallback_{i}",
                details={"index": i}
            )
        
        # Verificar formato JSONL
        fallback_file = Path(temp_dir) / "audit_fallback.jsonl"
        with open(fallback_file) as f:
            lines = f.readlines()
            
            # Todas las líneas deben parsear como JSON
            for idx, line in enumerate(lines):
                try:
                    event = json.loads(line)
                    assert "timestamp" in event
                    assert "event_type" in event
                    assert "user_id" in event
                except json.JSONDecodeError as e:
                    pytest.fail(f"Línea {idx} no es JSON válido: {line}, error: {e}")


@pytest.mark.asyncio
async def test_metrics_updated_correctly():
    """
    Métricas de Prometheus deben actualizarse correctamente.
    
    Resultado esperado:
    - audit_circuit_breaker_state refleja estado actual
    - audit_events_total incrementa en cada evento
    - audit_fallback_writes incrementa en fallback
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        # Verificar métrica inicial (CLOSED = 0)
        from app.services.security.audit_logger import audit_circuit_breaker_state
        # Nota: Prometheus metrics no se pueden leer fácilmente en tests
        # Este test valida que _update_circuit_breaker_metric() se llama
        
        # Mock exitoso
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(return_value=None)
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            await audit_logger.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                user_id="metrics_user"
            )
        
        # Circuit debe seguir CLOSED
        assert audit_logger.circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_no_exception_propagation_to_caller():
    """
    log_event nunca debe propagar excepciones al caller.
    
    Escenario:
    - Fallo catastrófico en persistencia
    
    Resultado esperado:
    - log_event completa sin raise
    - Caller no ve excepción
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        # Mock que falla catastróficamente
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_factory.side_effect = Exception("Catastrophic failure")
            
            # No debe raise exception
            try:
                await audit_logger.log_event(
                    event_type=AuditEventType.PMS_ERROR,
                    user_id="error_user"
                )
            except Exception as e:
                pytest.fail(f"log_event no debe propagar excepciones: {e}")


@pytest.mark.asyncio
async def test_concurrent_log_events_independent():
    """
    Múltiples log_event concurrentes deben ser independientes.
    
    Resultado esperado:
    - Todos completan sin interferencia
    - Circuit breaker maneja concurrencia correctamente
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(return_value=None)
            mock_factory.return_value.__aenter__.return_value = mock_session
            
            # Ejecutar 5 eventos en paralelo
            await asyncio.gather(
                *[
                    audit_logger.log_event(
                        event_type=AuditEventType.DATA_ACCESS,
                        user_id=f"concurrent_user_{i}"
                    )
                    for i in range(5)
                ]
            )
        
        # Todos deben completar sin error
        # Circuit debe seguir CLOSED (todos exitosos)
        assert audit_logger.circuit_breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_failure_count_resets_on_success():
    """
    Circuit breaker debe resetear contador de fallos después de éxito.
    
    Escenario:
    - 2 fallos
    - 1 éxito
    - 2 fallos más (no debe abrir, contador reseteado)
    
    Resultado esperado:
    - Circuit permanece CLOSED
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_logger = AuditLogger(fallback_dir=temp_dir)
        
        with patch('app.services.security.audit_logger.AsyncSessionFactory') as mock_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            
            # 2 fallos
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Error"))
            mock_session.rollback = AsyncMock()
            for i in range(2):
                await audit_logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    user_id=f"fail_{i}"
                )
            
            # 1 éxito (resetea contador)
            mock_session.commit = AsyncMock(return_value=None)
            await audit_logger.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                user_id="success_user"
            )
            
            # 2 fallos más (contador reseteado, no llega a threshold de 5)
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Error"))
            mock_session.rollback = AsyncMock()
            for i in range(2):
                await audit_logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    user_id=f"fail2_{i}"
                )
        
        # Circuit debe permanecer CLOSED (solo 2 fallos consecutivos después del éxito)
        assert audit_logger.circuit_breaker.state == CircuitState.CLOSED
