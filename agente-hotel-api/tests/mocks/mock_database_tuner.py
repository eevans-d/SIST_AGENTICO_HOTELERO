"""
Mock de DatabasePerformanceTuner para tests de autenticación
"""

from typing import Dict, Any
from datetime import datetime


class MockDatabaseTuner:
    """Mock del servicio DatabasePerformanceTuner para tests"""

    async def get_report(self) -> Dict[str, Any]:
        """Retorna reporte de performance de DB mockeado"""
        return {
            "status": "healthy",
            "connection_pool": {
                "active": 5,
                "idle": 10,
                "total": 15,
            },
            "slow_queries_count": 2,
            "slow_queries": [
                {
                    "query": "SELECT * FROM sessions WHERE...",
                    "execution_time_ms": 1500,
                    "frequency": 25,
                }
            ],
            "recommendations": ["Add composite index on (tenant_id, created_at)"],
            "timestamp": datetime.now().isoformat(),
        }

    async def optimize(self) -> Dict[str, Any]:
        """Simula optimización de base de datos"""
        return {
            "optimizations_applied": 0,
            "status": "completed",
            "details": "No optimizations needed",
            "timestamp": datetime.now().isoformat(),
        }

    async def analyze_queries(self) -> Dict[str, Any]:
        """Analiza queries lentas"""
        return {
            "analyzed_queries": 150,
            "slow_queries": 2,
            "recommendations": 3,
        }
