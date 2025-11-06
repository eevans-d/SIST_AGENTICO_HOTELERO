"""
Mocks para tests de autenticación y seguridad
"""

from .mock_performance_optimizer import MockPerformanceOptimizer
from .mock_database_tuner import MockDatabaseTuner
from .mock_cache_optimizer import MockCacheOptimizer
from .mock_resource_monitor import MockResourceMonitor
from .mock_auto_scaler import MockAutoScaler
from .mock_nlp_service import MockNLPService

__all__ = [
    "MockPerformanceOptimizer",
    "MockDatabaseTuner",
    "MockCacheOptimizer",
    "MockResourceMonitor",
    "MockAutoScaler",
    "MockNLPService",
]
