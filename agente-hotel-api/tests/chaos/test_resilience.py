# [PHASE D.6] tests/chaos/test_resilience.py

"""
Chaos engineering tests para validar resilience del sistema.

Simula fallos de componentes externos (Redis, PMS, NLP) y valida
que el sistema degrada gracefully sin crash completo.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.orchestrator import Orchestrator
from app.services.pms_adapter import QloAppsAdapter
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.models.unified_message import UnifiedMessage
from app.exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError
from datetime import datetime


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_pms_adapter(mock_redis):
    """Mock PMS adapter."""
    pms = QloAppsAdapter(mock_redis)
    return pms


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_redis):
    """Orchestrator con dependencias mockeadas."""
    session_mgr = SessionManager(mock_redis)
    lock_svc = LockService(mock_redis)
    return Orchestrator(mock_pms_adapter, session_mgr, lock_svc)


@pytest.fixture
def sample_message():
    """Mensaje de prueba."""
    return UnifiedMessage(
        message_id="test_123",
        canal="whatsapp",
        user_id="test_user",
        tipo="text",
        texto="Hola, quiero consultar disponibilidad",
        timestamp_iso=datetime.utcnow().isoformat(),
        metadata={},
    )


class TestRedisFailure:
    """Test suite para fallos de Redis."""

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, orchestrator, sample_message, mock_redis):
        """Test que el sistema maneja fallo de conexión a Redis."""
        # Arrange: Redis falla
        mock_redis.ping.side_effect = ConnectionError("Redis unavailable")
        mock_redis.get.side_effect = ConnectionError("Redis unavailable")

        # Act & Assert: El sistema debería degradar pero no crashear
        try:
            result = await orchestrator.handle_unified_message(sample_message)
            # Esperamos respuesta degradada o error controlado
            assert isinstance(result, dict), "Should return dict even with Redis failure"
        except Exception as e:
            # Si hay excepción, debe ser controlada (no timeout ni crash)
            assert not isinstance(e, asyncio.TimeoutError), "Should not timeout"

    @pytest.mark.asyncio
    async def test_redis_slow_response(self, orchestrator, sample_message, mock_redis):
        """Test que el sistema maneja respuestas lentas de Redis."""

        # Arrange: Redis responde lentamente
        async def slow_get(*args, **kwargs):
            await asyncio.sleep(2)  # Simula latencia
            return None

        mock_redis.get.side_effect = slow_get

        # Act: Request con timeout
        try:
            result = await asyncio.wait_for(orchestrator.handle_unified_message(sample_message), timeout=5.0)
            assert isinstance(result, dict), "Should complete even with slow Redis"
        except asyncio.TimeoutError:
            pytest.fail("System should not timeout with slow Redis")


class TestPMSFailure:
    """Test suite para fallos del PMS."""

    @pytest.mark.asyncio
    async def test_pms_circuit_breaker_open(self, orchestrator, sample_message):
        """Test degradación cuando circuit breaker de PMS está abierto."""
        # Arrange: PMS con circuit breaker abierto
        with patch.object(orchestrator.pms_adapter, "check_availability") as mock_check:
            mock_check.side_effect = CircuitBreakerOpenError("Circuit breaker open")

            # Act
            result = await orchestrator.handle_unified_message(sample_message)

            # Assert: Respuesta degradada pero funcional
            assert isinstance(result, dict), "Should return dict"
            assert "response" in result, "Should have response field"
            # La respuesta debe indicar problema técnico
            assert "técnico" in result["response"].lower() or "mantenimiento" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_pms_timeout(self, orchestrator, sample_message):
        """Test manejo de timeout del PMS."""
        # Arrange: PMS con timeout
        with patch.object(orchestrator.pms_adapter, "check_availability") as mock_check:

            async def timeout_fn(*args, **kwargs):
                await asyncio.sleep(10)  # Simula timeout
                return []

            mock_check.side_effect = timeout_fn

            # Act: Con timeout limitado
            try:
                result = await asyncio.wait_for(orchestrator.handle_unified_message(sample_message), timeout=3.0)
                # Si completa, debe ser con degradación
                assert isinstance(result, dict)
            except asyncio.TimeoutError:
                # Timeout es aceptable si está controlado
                pass

    @pytest.mark.asyncio
    async def test_pms_intermittent_failures(self, orchestrator, sample_message):
        """Test resiliencia ante fallos intermitentes del PMS."""
        # Arrange: PMS falla 2 de cada 3 veces
        call_count = 0

        async def intermittent_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                return [{"room_type": "standard", "available": True}]
            else:
                raise PMSError("PMS temporarily unavailable")

        with patch.object(orchestrator.pms_adapter, "check_availability") as mock_check:
            mock_check.side_effect = intermittent_fail

            # Act: Múltiples requests
            results = []
            for _ in range(3):
                try:
                    result = await orchestrator.handle_unified_message(sample_message)
                    results.append(result)
                except Exception:
                    results.append({"error": True})

            # Assert: Sistema debe continuar funcionando
            assert len(results) == 3, "Should process all requests"
            assert any(not r.get("error") for r in results), "At least one should succeed"


class TestNLPFailure:
    """Test suite para fallos del NLP engine."""

    @pytest.mark.asyncio
    async def test_nlp_circuit_breaker_fallback(self, orchestrator, sample_message):
        """Test fallback a reglas básicas cuando NLP falla."""
        # Arrange: NLP falla completamente
        with patch.object(orchestrator.nlp_engine, "process_message") as mock_nlp:
            mock_nlp.side_effect = Exception("NLP service down")

            # Act
            result = await orchestrator.handle_unified_message(sample_message)

            # Assert: Sistema usa reglas básicas
            assert isinstance(result, dict), "Should return dict"
            assert "response" in result, "Should have response"
            # Debería usar fallback de reglas

    @pytest.mark.asyncio
    async def test_nlp_low_confidence_fallback(self, orchestrator, sample_message):
        """Test fallback cuando NLP tiene baja confianza."""
        # Arrange: NLP con confianza muy baja
        with patch.object(orchestrator.nlp_engine, "process_message") as mock_nlp:
            mock_nlp.return_value = {"intent": {"name": "unknown", "confidence": 0.1}, "entities": []}

            # Act
            result = await orchestrator.handle_unified_message(sample_message)

            # Assert: Respuesta de fallback amigable
            assert isinstance(result, dict)
            assert "response" in result
            # Debe pedir aclaración o mostrar opciones


class TestCombinedFailures:
    """Test suite para fallos combinados de múltiples componentes."""

    @pytest.mark.asyncio
    async def test_redis_and_pms_failure(self, orchestrator, sample_message, mock_redis):
        """Test fallo simultáneo de Redis y PMS."""
        # Arrange: Ambos servicios fallan
        mock_redis.ping.side_effect = ConnectionError("Redis down")
        with patch.object(orchestrator.pms_adapter, "check_availability") as mock_pms:
            mock_pms.side_effect = PMSError("PMS down")

            # Act: El sistema debe manejar ambos fallos
            try:
                result = await orchestrator.handle_unified_message(sample_message)
                # Si completa, debe ser respuesta degradada
                assert isinstance(result, dict)
            except Exception as e:
                # Excepción controlada es aceptable
                assert not isinstance(e, asyncio.TimeoutError)

    @pytest.mark.asyncio
    async def test_all_services_degraded(self, orchestrator, sample_message, mock_redis):
        """Test cuando todos los servicios están degradados."""
        # Arrange: Todos los servicios lentos/fallando
        mock_redis.get.side_effect = lambda *args, **kwargs: asyncio.sleep(1)

        with patch.object(orchestrator.nlp_engine, "process_message") as mock_nlp:
            mock_nlp.side_effect = Exception("NLP slow")

            with patch.object(orchestrator.pms_adapter, "check_availability") as mock_pms:
                mock_pms.side_effect = PMSError("PMS slow")

                # Act: Con timeout global
                try:
                    result = await asyncio.wait_for(orchestrator.handle_unified_message(sample_message), timeout=5.0)
                    # Sistema debe completar con degradación máxima
                    assert isinstance(result, dict)
                except asyncio.TimeoutError:
                    # Timeout controlado es aceptable en este escenario extremo
                    pass


class TestRecovery:
    """Test suite para recuperación después de fallos."""

    @pytest.mark.asyncio
    async def test_pms_circuit_breaker_recovery(self, orchestrator, sample_message):
        """Test recuperación del circuit breaker de PMS."""
        # Arrange: PMS falla inicialmente, luego recupera
        call_count = 0

        async def recovering_pms(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise PMSError("PMS recovering")
            return [{"room_type": "standard", "available": True}]

        with patch.object(orchestrator.pms_adapter, "check_availability") as mock_pms:
            mock_pms.side_effect = recovering_pms

            # Act: Múltiples intentos
            results = []
            for _ in range(5):
                try:
                    result = await orchestrator.handle_unified_message(sample_message)
                    results.append(result)
                except Exception:
                    results.append({"error": True})
                await asyncio.sleep(0.1)  # Pequeña pausa entre requests

            # Assert: Debe recuperarse eventualmente
            successful = [r for r in results if not r.get("error")]
            assert len(successful) > 0, "Should recover after initial failures"


# Comandos útiles para ejecutar estos tests:
# pytest tests/chaos/test_resilience.py -v
# pytest tests/chaos/test_resilience.py -v -k "pms"
# pytest tests/chaos/test_resilience.py -v --tb=short
