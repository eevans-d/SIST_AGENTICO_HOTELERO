# [PROMPT 2.10] tests/conftest.py

import warnings
from typing import Any
import sys
from unittest.mock import MagicMock

# [GLOBAL MOCK] OpenTelemetry dependencies
# This prevents ModuleNotFoundError in environments where opentelemetry is not installed
# Must be executed before any app imports that might use tracing
if "opentelemetry" not in sys.modules:
    mock_otel = MagicMock()
    mock_otel.trace = MagicMock()
    mock_otel.trace.get_tracer = MagicMock(return_value=MagicMock())
    mock_otel.trace.Span = MagicMock
    sys.modules["opentelemetry"] = mock_otel
    sys.modules["opentelemetry.trace"] = mock_otel.trace
    sys.modules["opentelemetry.instrumentation.fastapi"] = MagicMock()
    sys.modules["opentelemetry.instrumentation.sqlalchemy"] = MagicMock()
    sys.modules["opentelemetry.sdk.trace"] = MagicMock()
    sys.modules["opentelemetry.sdk.trace.export"] = MagicMock()
    sys.modules["opentelemetry.sdk.trace.sampling"] = MagicMock()
    sys.modules["opentelemetry.sdk.resources"] = MagicMock()
    # Mock exporters
    sys.modules["opentelemetry.exporter"] = MagicMock()
    sys.modules["opentelemetry.exporter.otlp"] = MagicMock()
    sys.modules["opentelemetry.exporter.otlp.proto"] = MagicMock()
    sys.modules["opentelemetry.exporter.otlp.proto.grpc"] = MagicMock()
    sys.modules["opentelemetry.exporter.otlp.proto.grpc.trace_exporter"] = MagicMock()

import httpx
import pytest
import pytest_asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address

# Mocks para tests de autenticación
from tests.mocks import (
    MockPerformanceOptimizer,
    MockDatabaseTuner,
    MockCacheOptimizer,
    MockResourceMonitor,
    MockAutoScaler,
    MockNLPService,
)

# Silenciar DeprecationWarning específico de passlib (crypt será removido en Python 3.13)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib.utils")


# Reset Prometheus default registry between tests to avoid duplicated timeseries
@pytest_asyncio.fixture(autouse=True)
async def _reset_prometheus_registry() -> Any:
    try:
        from prometheus_client import REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
        # Unregister all custom collectors (keep process/platform/gc)
        for collector in list(getattr(REGISTRY, "_collector_to_names", {}).keys()):
            if collector not in {PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR}:
                try:
                    REGISTRY.unregister(collector)
                except Exception:
                    pass
    except Exception:
        # If prometheus_client not present or API changes, ignore silently
        pass
    yield


# --- Compatibility shim for httpx.AsyncClient(app=..., base_url=...) in newer httpx versions ---
# Some tests use AsyncClient(app=app, base_url="http://test"), which was removed in newer httpx.
# Provide a lightweight subclass that accepts `app` and translates it into an ASGITransport.
try:
    from httpx import ASGITransport  # type: ignore
except Exception:  # pragma: no cover - older httpx
    ASGITransport = None  # type: ignore


class _AsyncClientCompat(httpx.AsyncClient):  # type: ignore[misc]
    def __init__(self, *args, app=None, **kwargs):  # type: ignore[no-untyped-def]
        if app is not None and "transport" not in kwargs:
            try:
                if ASGITransport is not None:
                    kwargs["transport"] = ASGITransport(app=app)
            except Exception:
                # Fallback: leave transport unset
                pass
        super().__init__(*args, **kwargs)


# Apply the shim globally for tests
httpx.AsyncClient = _AsyncClientCompat  # type: ignore[assignment]


@pytest_asyncio.fixture
async def test_app():
    # Lógica para crear una app de prueba con BD temporal
    from app.main import app

    # Forzar inclusión de routers de performance y nlp (para tests de autenticación)
    try:
        from app.routers import performance, nlp

        # Solo incluir si no están ya incluidos
        performance_included = any(
            getattr(route, "path", "").startswith("/api/v1/performance")
            for route in app.routes
        )
        nlp_included = any(
            getattr(route, "path", "").startswith("/api/nlp")
            for route in app.routes
        )

        if not performance_included:
            app.include_router(performance.router)
        if not nlp_included:
            app.include_router(nlp.router)
    except Exception:
        # Silenciar errores de import en tests que no requieren estos routers
        pass

    # Usar almacenamiento en memoria para el rate limiter en pruebas
    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    return app


@pytest_asyncio.fixture(autouse=True)
async def _force_memory_rate_limiter():
    """Configura el rate limiter en memoria para todas las pruebas (autouse)."""
    from app.main import app

    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    yield


# ===== Fixtures para override de servicios con mocks (para tests de autenticación) =====

@pytest.fixture
def mock_performance_optimizer():
    """Retorna mock de PerformanceOptimizer"""
    return MockPerformanceOptimizer()


@pytest.fixture
def mock_database_tuner():
    """Retorna mock de DatabaseTuner"""
    return MockDatabaseTuner()


@pytest.fixture
def mock_cache_optimizer():
    """Retorna mock de CacheOptimizer"""
    return MockCacheOptimizer()


@pytest.fixture
def mock_resource_monitor():
    """Retorna mock de ResourceMonitor"""
    return MockResourceMonitor()


@pytest.fixture
def mock_auto_scaler():
    """Retorna mock de AutoScaler"""
    return MockAutoScaler()


@pytest.fixture
def mock_nlp_service():
    """Retorna mock de NLPService"""
    return MockNLPService()


@pytest.fixture
def mock_pms_adapter():
    """Fixture for mocking QloAppsAdapter with AsyncMock."""
    from unittest.mock import AsyncMock
    from app.services.pms_adapter import QloAppsAdapter
    
    mock = AsyncMock(spec=QloAppsAdapter)
    # Setup default return values for common methods to avoid TypeErrors in tests
    mock.check_availability.return_value = []
    mock.create_reservation.return_value = {"reservation_uuid": "mock-uuid", "status": "confirmed"}
    mock.test_connection.return_value = True
    return mock


@pytest_asyncio.fixture
async def test_client(test_app, mock_performance_optimizer, mock_database_tuner,
                      mock_cache_optimizer, mock_resource_monitor, mock_auto_scaler,
                      mock_nlp_service):
    """
    Cliente de test con mocks de servicios inyectados para override de Depends()
    """
    from app.services.performance_optimizer import get_performance_optimizer
    try:
        from app.services.database_tuner import get_db_performance_tuner as get_database_tuner
    except Exception:  # fallback nombre anterior
        from app.services.database_tuner import get_database_tuner  # type: ignore
    from app.services.cache_optimizer import get_cache_optimizer
    from app.services.resource_monitor import get_resource_monitor
    from app.services.auto_scaler import get_auto_scaler

    # NLP service puede no estar disponible si spacy no está instalado
    try:
        from app.services.nlp.integrated_nlp_service import get_nlp_service
        nlp_available = True
    except (ImportError, ModuleNotFoundError):
        get_nlp_service = None
        nlp_available = False

    # Override de dependencias con mocks
    test_app.dependency_overrides[get_performance_optimizer] = lambda: mock_performance_optimizer
    test_app.dependency_overrides[get_database_tuner] = lambda: mock_database_tuner
    test_app.dependency_overrides[get_cache_optimizer] = lambda: mock_cache_optimizer
    test_app.dependency_overrides[get_resource_monitor] = lambda: mock_resource_monitor
    test_app.dependency_overrides[get_auto_scaler] = lambda: mock_auto_scaler
    if nlp_available and get_nlp_service:
        test_app.dependency_overrides[get_nlp_service] = lambda: mock_nlp_service

    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:  # type: ignore
        yield client

    # Limpiar overrides después de tests
    test_app.dependency_overrides.clear()
