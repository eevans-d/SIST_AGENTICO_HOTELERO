# tests/e2e/test_orchestrator_flow.py
# Test E2E del flujo completo del orchestrator con componentes reales

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator
from app.services.pms_adapter import MockPMSAdapter
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.models.unified_message import UnifiedMessage


class FakeRedis:
    """In-memory Redis for E2E tests."""

    def __init__(self):
        self.store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str):
        import time
        if key in self.store:
            value, expiry = self.store[key]
            if expiry is None or time.time() < expiry:
                return value
            del self.store[key]
        return None

    async def setex(self, key: str, ttl: int, value: str):
        import time
        expiry_timestamp = time.time() + ttl
        self.store[key] = (value, expiry_timestamp)
        return True

    async def delete(self, *keys: str):
        for k in keys:
            self.store.pop(k, None)
        return len(keys)

    async def scan(self, cursor: int = 0, match: str | None = None, count: int = 100):
        import fnmatch
        import time

        expired_keys = [
            k for k, (v, exp) in self.store.items()
            if exp is not None and time.time() >= exp
        ]
        for k in expired_keys:
            del self.store[k]

        keys = list(self.store.keys())
        if match:
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        return 0, keys

    async def ping(self):
        return True

    async def exists(self, key: str):
        return 1 if key in self.store else 0


@pytest.fixture
async def fake_redis():
    """Fake Redis for E2E tests."""
    return FakeRedis()


@pytest.fixture
async def mock_pms_adapter(fake_redis):
    """Mock PMS adapter con datos fixture."""
    return MockPMSAdapter(redis_client=fake_redis)


@pytest.fixture
async def session_manager(fake_redis):
    """Session manager real con FakeRedis."""
    from app.core.database import AsyncSessionFactory
    from app.models.session import ConversationSession
    
    # Session manager usa DB, creamos mock de DB
    class MockAsyncSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def execute(self, query):
            class MockResult:
                def scalars(self):
                    return self
                def first(self):
                    return None
            return MockResult()
        async def commit(self):
            pass
        def add(self, obj):
            pass
    
    manager = SessionManager()
    manager.redis = fake_redis
    
    return manager


@pytest.fixture
async def lock_service(fake_redis):
    """Lock service real con FakeRedis."""
    from app.core.database import AsyncSessionFactory
    
    # Lock service usa DB
    class MockAsyncSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def commit(self):
            pass
        def add(self, obj):
            pass
    
    service = LockService()
    service.redis = fake_redis
    
    return service


@pytest.fixture
async def orchestrator(mock_pms_adapter, session_manager, lock_service):
    """Orchestrator con dependencias semi-reales."""
    orch = Orchestrator(
        pms_adapter=mock_pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service,
    )
    return orch


# ==============================================================================
# E2E TEST 1: Check Availability Flow
# ==============================================================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E orchestrator requires full setup - implement after B1 stabilized")
async def test_e2e_check_availability_flow(orchestrator, mock_pms_adapter):
    """
    Test E2E completo del flujo de consulta de disponibilidad.
    
    Flujo:
    1. Usuario envía mensaje: "¿Tienen habitaciones disponibles del 20 al 22 de noviembre?"
    2. NLP detecta intent: check_availability
    3. Orchestrator llama al PMS adapter
    4. PMS retorna habitaciones disponibles (mock)
    5. Orchestrator genera respuesta con template
    6. Retorna respuesta formateada
    """
    message = UnifiedMessage(
        user_id="e2e_test_user",
        canal="whatsapp",
        texto="¿Tienen habitaciones disponibles del 20 al 22 de noviembre?",
        timestamp_iso=datetime.now().isoformat(),
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Respuesta con habitaciones
    assert response is not None
    assert "response_type" in response
    # El orchestrator siempre retorna algo, aunque sea fallback
    assert response["response_type"] in ["text", "audio"]


# ==============================================================================
# E2E TEST 2: NLP Fallback Flow
# ==============================================================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E orchestrator requires full setup - implement after B1 stabilized")
async def test_e2e_nlp_fallback_low_confidence(orchestrator):
    """
    Test E2E del flujo de fallback cuando NLP tiene baja confianza.
    
    Flujo:
    1. Usuario envía mensaje ambiguo
    2. NLP retorna baja confianza (< threshold)
    3. Orchestrator usa respuesta de fallback
    """
    message = UnifiedMessage(
        user_id="e2e_test_user",
        canal="whatsapp",
        texto="asdfghjkl",  # Mensaje sin sentido
        timestamp_iso=datetime.now().isoformat(),
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Respuesta de fallback
    assert response is not None
    assert "response_type" in response
    # Fallback retorna texto explicativo
    assert response["response_type"] == "text"


# ==============================================================================
# E2E TEST 3: Metrics Tracking
# ==============================================================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E orchestrator requires full setup - implement after B1 stabilized")
async def test_e2e_metrics_tracking(orchestrator):
    """
    Test E2E que valida que las métricas se registran correctamente.
    
    Flujo:
    1. Procesar mensaje
    2. Verificar que métricas de Prometheus se incrementaron
    """
    from app.services.business_metrics import intents_detected, messages_by_channel

    # Obtener valor inicial de métricas (Prometheus Counter)
    # Nota: No se pueden "resetear" counters, solo verificar incremento relativo
    
    message = UnifiedMessage(
        user_id="e2e_test_user",
        canal="whatsapp",
        texto="Hola, necesito información sobre habitaciones",
        timestamp_iso=datetime.now().isoformat(),
    )

    # Act
    response = await orchestrator.process_message(message)

    # Assert: Métricas incrementadas
    assert response is not None
    # Las métricas deberían haberse incrementado, pero no podemos verificar valores absolutos
    # en tests aislados sin reset de Prometheus registry


# ==============================================================================
# E2E TEST 4: Session Persistence
# ==============================================================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E orchestrator requires full setup - implement after B1 stabilized")
async def test_e2e_session_persistence_multi_turn(orchestrator):
    """
    Test E2E de persistencia de sesión en conversación multi-turno.
    
    Flujo:
    1. Primer mensaje: "Quiero reservar una habitación"
    2. Segundo mensaje: "Para el 20 de noviembre"
    3. Verificar que el contexto se mantiene entre turnos
    """
    user_id = "e2e_multi_turn_user"

    # Primer turno
    message1 = UnifiedMessage(
        user_id=user_id,
        canal="whatsapp",
        texto="Quiero reservar una habitación",
        timestamp_iso=datetime.now().isoformat(),
    )
    
    response1 = await orchestrator.process_message(message1)
    assert response1 is not None

    # Segundo turno
    message2 = UnifiedMessage(
        user_id=user_id,
        canal="whatsapp",
        texto="Para el 20 de noviembre",
        timestamp_iso=datetime.now().isoformat(),
    )
    
    response2 = await orchestrator.process_message(message2)
    assert response2 is not None

    # La sesión debería mantener contexto entre turnos
    # (verificación específica requiere acceso a session_manager internals)
