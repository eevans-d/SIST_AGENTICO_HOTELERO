"""
Mock de CacheOptimizer para tests de autenticación
"""

from typing import Dict, Any
from datetime import datetime


class MockCacheOptimizer:
    """Mock del servicio CacheOptimizer para tests"""

    async def get_report(self) -> Dict[str, Any]:
        """Retorna reporte de cache mockeado"""
        return {
            "hit_rate": 0.85,
            "total_keys": 1250,
            "memory_usage_mb": 128,
            "evictions_today": 15,
            "top_keys": [
                {"key": "session:*", "hits": 1500, "size_kb": 45},
                {"key": "availability:*", "hits": 800, "size_kb": 32},
            ],
            "recommendations": ["Increase TTL for static data keys"],
            "timestamp": datetime.now().isoformat(),
        }

    async def optimize(self) -> Dict[str, Any]:
        """Simula optimización de cache"""
        return {
            "invalidated_keys": 0,
            "status": "completed",
            "details": "Cache is healthy",
            "timestamp": datetime.now().isoformat(),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de cache"""
        return {
            "hits": 15000,
            "misses": 2500,
            "hit_rate": 0.857,
            "total_requests": 17500,
        }
