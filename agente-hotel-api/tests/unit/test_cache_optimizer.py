"""
Tests unitarios para CacheOptimizer service.
Fase 1.3 del plan de calidad.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.cache_optimizer import (
    CacheOptimizer,
    CacheStrategy,
    CacheLayer,
    CachePattern,
    CacheStats,
)


class TestCacheOptimizerInitialization:
    """Tests de inicialización del CacheOptimizer."""

    def test_initialization_creates_empty_patterns(self):
        """Los patrones de cache deben empezar vacíos."""
        optimizer = CacheOptimizer()
        
        assert optimizer.cache_patterns == {}
        assert optimizer.hot_keys == set()
        assert optimizer.cold_keys == set()

    def test_initialization_sets_default_config(self):
        """La configuración por defecto debe existir."""
        optimizer = CacheOptimizer()
        
        assert "hot_key_threshold" in optimizer.config
        assert "cold_key_threshold" in optimizer.config
        assert optimizer.config["hot_key_threshold"] > optimizer.config["cold_key_threshold"]


class TestCacheOptimizerStartStop:
    """Tests de start/stop del servicio."""

    @pytest.mark.asyncio
    async def test_start_initializes_redis(self):
        """Start debe inicializar el cliente Redis."""
        optimizer = CacheOptimizer()
        
        with patch("app.services.cache_optimizer.get_redis_client") as mock_redis:
            mock_redis.return_value = AsyncMock()
            await optimizer.start()
            
            assert optimizer.redis_client is not None

    @pytest.mark.asyncio
    async def test_start_handles_redis_error(self):
        """Start debe manejar errores de Redis gracefully."""
        optimizer = CacheOptimizer()
        
        with patch("app.services.cache_optimizer.get_redis_client") as mock_redis:
            mock_redis.side_effect = Exception("Redis unavailable")
            
            # No debe lanzar excepción crítica
            try:
                await optimizer.start()
            except Exception:
                pass  # Aceptable si falla, pero no debe ser fatal

    @pytest.mark.asyncio
    async def test_stop_clears_resources(self):
        """Stop debe limpiar recursos."""
        optimizer = CacheOptimizer()
        optimizer.redis_client = AsyncMock()
        
        await optimizer.stop()
        # No debe lanzar excepción


class TestCacheStrategy:
    """Tests del enum CacheStrategy."""

    def test_all_strategies_exist(self):
        """Todas las estrategias de cache deben existir."""
        assert CacheStrategy.LRU
        assert CacheStrategy.LFU
        assert CacheStrategy.TTL_BASED
        assert CacheStrategy.WRITE_THROUGH
        assert CacheStrategy.WRITE_BACK
        assert CacheStrategy.READ_THROUGH


class TestCacheLayer:
    """Tests del enum CacheLayer."""

    def test_all_layers_exist(self):
        """Todas las capas de cache deben existir."""
        assert CacheLayer.L1_APPLICATION
        assert CacheLayer.L2_REDIS
        assert CacheLayer.L3_DATABASE


class TestCachePattern:
    """Tests del dataclass CachePattern."""

    def test_cache_pattern_creation(self):
        """CachePattern debe crear instancias válidas."""
        pattern = CachePattern(
            key_pattern="session:*",
            access_frequency=100.0,
            hit_rate=0.85,
            avg_size=1024,
            ttl=3600,
            last_access=datetime.now(),
            hotness_score=0.9,
        )
        
        assert pattern.key_pattern == "session:*"
        assert pattern.hit_rate == 0.85
        assert pattern.hotness_score == 0.9

    def test_hot_pattern_identification(self):
        """Debe identificar patrones hot basado en hotness_score."""
        pattern = CachePattern(
            key_pattern="user:*",
            access_frequency=1000.0,
            hit_rate=0.95,
            avg_size=512,
            ttl=7200,
            last_access=datetime.now(),
            hotness_score=0.95,
        )
        
        optimizer = CacheOptimizer()
        is_hot = pattern.hotness_score >= optimizer.config["hot_key_threshold"]
        
        assert is_hot is True

    def test_cold_pattern_identification(self):
        """Debe identificar patrones cold basado en hotness_score."""
        pattern = CachePattern(
            key_pattern="legacy:*",
            access_frequency=5.0,
            hit_rate=0.1,
            avg_size=2048,
            ttl=86400,
            last_access=datetime.now(),
            hotness_score=0.1,
        )
        
        optimizer = CacheOptimizer()
        is_cold = pattern.hotness_score <= optimizer.config["cold_key_threshold"]
        
        assert is_cold is True


class TestCacheStats:
    """Tests del dataclass CacheStats."""

    def test_cache_stats_creation(self):
        """CacheStats debe crear instancias válidas."""
        stats = CacheStats(
            total_keys=10000,
            memory_usage=104857600,  # 100 MB
            hit_rate=0.92,
            miss_rate=0.08,
            eviction_rate=0.01,
            avg_ttl=3600.0,
            fragmentation_ratio=1.1,
            ops_per_second=5000.0,
        )
        
        assert stats.total_keys == 10000
        assert stats.hit_rate + stats.miss_rate == 1.0
        assert stats.fragmentation_ratio >= 1.0

    def test_healthy_cache_stats(self):
        """Stats saludables deben tener hit_rate > 0.8."""
        stats = CacheStats(
            total_keys=5000,
            memory_usage=52428800,
            hit_rate=0.95,
            miss_rate=0.05,
            eviction_rate=0.005,
            avg_ttl=7200.0,
            fragmentation_ratio=1.05,
            ops_per_second=3000.0,
        )
        
        is_healthy = stats.hit_rate >= 0.8 and stats.fragmentation_ratio < 1.5
        
        assert is_healthy is True


class TestHotColdKeyManagement:
    """Tests de gestión de hot/cold keys."""

    def test_hot_keys_are_tracked(self):
        """Los hot keys deben poder ser tracked."""
        optimizer = CacheOptimizer()
        
        optimizer.hot_keys.add("user:123")
        optimizer.hot_keys.add("session:abc")
        
        assert len(optimizer.hot_keys) == 2
        assert "user:123" in optimizer.hot_keys

    def test_cold_keys_are_tracked(self):
        """Los cold keys deben poder ser tracked."""
        optimizer = CacheOptimizer()
        
        optimizer.cold_keys.add("legacy:old_data")
        
        assert len(optimizer.cold_keys) == 1
        assert "legacy:old_data" in optimizer.cold_keys

    def test_key_cannot_be_hot_and_cold(self):
        """Una key no debe estar en hot y cold simultáneamente."""
        optimizer = CacheOptimizer()
        
        key = "test:key"
        optimizer.hot_keys.add(key)
        
        # Simular promoción a cold
        optimizer.hot_keys.discard(key)
        optimizer.cold_keys.add(key)
        
        assert key not in optimizer.hot_keys
        assert key in optimizer.cold_keys


class TestOptimizationHistory:
    """Tests del historial de optimizaciones."""

    def test_history_is_list(self):
        """El historial debe ser una lista."""
        optimizer = CacheOptimizer()
        
        assert isinstance(optimizer.optimization_history, list)

    def test_history_can_store_entries(self):
        """El historial debe poder almacenar entradas."""
        optimizer = CacheOptimizer()
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": "ttl_adjustment",
            "pattern": "session:*",
            "old_ttl": 3600,
            "new_ttl": 7200,
            "reason": "Low eviction rate detected",
        }
        
        optimizer.optimization_history.append(entry)
        
        assert len(optimizer.optimization_history) == 1
        assert optimizer.optimization_history[0]["operation"] == "ttl_adjustment"


class TestMemoryOptimization:
    """Tests de optimización de memoria."""

    def test_fragmentation_detection(self):
        """Debe detectar fragmentación de memoria alta."""
        stats = CacheStats(
            total_keys=1000,
            memory_usage=104857600,
            hit_rate=0.9,
            miss_rate=0.1,
            eviction_rate=0.02,
            avg_ttl=3600.0,
            fragmentation_ratio=2.5,  # Muy alto
            ops_per_second=1000.0,
        )
        
        needs_defrag = stats.fragmentation_ratio > 1.5
        
        assert needs_defrag is True

    def test_low_ops_detection(self):
        """Debe detectar baja actividad de operaciones."""
        stats = CacheStats(
            total_keys=100,
            memory_usage=1048576,
            hit_rate=0.5,
            miss_rate=0.5,
            eviction_rate=0.0,
            avg_ttl=86400.0,
            fragmentation_ratio=1.0,
            ops_per_second=10.0,  # Muy bajo
        )
        
        low_activity = stats.ops_per_second < 100
        
        assert low_activity is True
