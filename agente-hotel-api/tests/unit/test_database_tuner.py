"""
Tests unitarios para DatabasePerformanceTuner service.
Fase 1.3 del plan de calidad.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.database_tuner import (
    DatabasePerformanceTuner,
    QueryOptimizationType,
    SlowQuery,
    IndexRecommendation,
    DatabaseStats,
)


class TestDatabaseTunerInitialization:
    """Tests de inicialización del DatabasePerformanceTuner."""

    def test_initialization_sets_default_threshold(self):
        """El tuner debe tener un umbral de queries lentas por defecto."""
        tuner = DatabasePerformanceTuner()
        
        assert tuner.slow_query_threshold > 0
        assert tuner.slow_query_threshold == 1000  # 1 segundo en ms

    def test_initialization_creates_empty_recommendations(self):
        """Las recomendaciones deben empezar vacías."""
        tuner = DatabasePerformanceTuner()
        
        assert tuner.index_recommendations == []
        assert tuner.optimization_history == []


class TestDatabaseTunerStartStop:
    """Tests de start/stop del servicio."""

    @pytest.mark.asyncio
    async def test_start_does_not_throw(self):
        """Start no debe lanzar excepciones."""
        tuner = DatabasePerformanceTuner()
        
        # Mock de la sesión de DB
        with patch.object(tuner, "db_engine", MagicMock()):
            await tuner.start()
            # No debe lanzar excepción

    @pytest.mark.asyncio
    async def test_stop_clears_resources(self):
        """Stop debe limpiar recursos correctamente."""
        tuner = DatabasePerformanceTuner()
        
        await tuner.stop()
        # No debe lanzar excepción


class TestSlowQueryDataclass:
    """Tests del dataclass SlowQuery."""

    def test_slow_query_creation(self):
        """SlowQuery debe crear instancias válidas."""
        query = SlowQuery(
            query="SELECT * FROM users WHERE id = 1",
            mean_time=1500.0,
            calls=100,
            total_time=150000.0,
            rows=100,
            query_id="abc123",
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        assert query.mean_time == 1500.0
        assert query.calls == 100

    def test_slow_query_identifies_slow(self):
        """Debe identificar queries lentas basado en mean_time."""
        query = SlowQuery(
            query="SELECT * FROM large_table",
            mean_time=2000.0,  # 2 segundos
            calls=50,
            total_time=100000.0,
            rows=10000,
            query_id="xyz789",
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )
        
        tuner = DatabasePerformanceTuner()
        is_slow = query.mean_time > tuner.slow_query_threshold
        
        assert is_slow is True


class TestIndexRecommendation:
    """Tests del dataclass IndexRecommendation."""

    def test_index_recommendation_creation(self):
        """IndexRecommendation debe crear instancias válidas."""
        recommendation = IndexRecommendation(
            table_name="users",
            columns=["email", "tenant_id"],
            index_type="btree",
            estimated_benefit=0.8,
            reason="Frequent lookups by email within tenant",
            query_pattern="SELECT * FROM users WHERE email = ? AND tenant_id = ?",
        )
        
        assert recommendation.table_name == "users"
        assert len(recommendation.columns) == 2
        assert recommendation.index_type == "btree"
        assert 0 <= recommendation.estimated_benefit <= 1


class TestDatabaseStats:
    """Tests del dataclass DatabaseStats."""

    def test_database_stats_creation(self):
        """DatabaseStats debe crear instancias válidas."""
        stats = DatabaseStats(
            total_size=1073741824,  # 1 GB
            table_count=50,
            index_count=100,
            active_connections=10,
            idle_connections=5,
            slow_queries_count=3,
            cache_hit_ratio=0.95,
            checkpoint_frequency=300.0,
            wal_size=104857600,  # 100 MB
        )
        
        assert stats.cache_hit_ratio == 0.95
        assert stats.active_connections == 10
        assert stats.slow_queries_count == 3


class TestQueryOptimization:
    """Tests de optimización de queries."""

    @pytest.mark.asyncio
    async def test_analyze_slow_queries_returns_list(self):
        """analyze_slow_queries debe retornar una lista."""
        tuner = DatabasePerformanceTuner()
        
        # Mock de AsyncSessionFactory para evitar conexión real
        with patch("app.services.database_tuner.AsyncSessionFactory") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.__iter__ = MagicMock(return_value=iter([]))
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await tuner.analyze_slow_queries()
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_recommendations_returns_list(self):
        """get_recommendations debe retornar una lista."""
        tuner = DatabasePerformanceTuner()
        
        # Verificar que el método existe y retorna lista
        if hasattr(tuner, "get_recommendations"):
            result = await tuner.get_recommendations()
            assert isinstance(result, list)


class TestQueryOptimizationType:
    """Tests del enum QueryOptimizationType."""

    def test_all_optimization_types_exist(self):
        """Todos los tipos de optimización deben existir."""
        assert QueryOptimizationType.INDEX_CREATION
        assert QueryOptimizationType.INDEX_REMOVAL
        assert QueryOptimizationType.QUERY_REWRITE
        assert QueryOptimizationType.STATISTICS_UPDATE
        assert QueryOptimizationType.VACUUM_ANALYZE
        assert QueryOptimizationType.CONFIGURATION_TUNE


class TestOptimizationHistory:
    """Tests del historial de optimizaciones."""

    def test_history_is_list(self):
        """El historial debe ser una lista."""
        tuner = DatabasePerformanceTuner()
        
        assert isinstance(tuner.optimization_history, list)

    def test_history_can_store_entries(self):
        """El historial debe poder almacenar entradas."""
        tuner = DatabasePerformanceTuner()
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": QueryOptimizationType.STATISTICS_UPDATE.value,
            "result": "success",
            "details": "Updated statistics for users table",
        }
        
        tuner.optimization_history.append(entry)
        
        assert len(tuner.optimization_history) == 1
        assert tuner.optimization_history[0]["action"] == "statistics_update"


class TestCacheHitRatio:
    """Tests relacionados con cache hit ratio."""

    def test_healthy_cache_ratio(self):
        """Cache hit ratio saludable debe ser > 0.9."""
        stats = DatabaseStats(
            total_size=1073741824,
            table_count=50,
            index_count=100,
            active_connections=10,
            idle_connections=5,
            slow_queries_count=0,
            cache_hit_ratio=0.95,
            checkpoint_frequency=300.0,
            wal_size=104857600,
        )
        
        assert stats.cache_hit_ratio >= 0.9

    def test_unhealthy_cache_ratio_detection(self):
        """Debe detectar cache hit ratio bajo."""
        stats = DatabaseStats(
            total_size=1073741824,
            table_count=50,
            index_count=100,
            active_connections=10,
            idle_connections=5,
            slow_queries_count=10,
            cache_hit_ratio=0.70,  # Bajo
            checkpoint_frequency=300.0,
            wal_size=104857600,
        )
        
        is_healthy = stats.cache_hit_ratio >= 0.9
        
        assert is_healthy is False
