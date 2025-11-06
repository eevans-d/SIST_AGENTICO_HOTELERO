"""
Mock de PerformanceOptimizer para tests de autenticación
Retorna datos dummy sin lógica de negocio real
"""

from typing import Dict, Any, List
from datetime import datetime


class MockPerformanceOptimizer:
    """Mock del servicio PerformanceOptimizer para tests"""

    async def get_optimization_report(self) -> Dict[str, Any]:
        """
        Retorna reporte de optimización mockeado
        """
        return {
            "overall_score": 85,
            "optimizations_today": 3,
            "recommendations": [
                {
                    "type": "query_optimization",
                    "priority": "high",
                    "impact_score": 8.5,
                    "description": "Mock optimization recommendation",
                }
            ],
            "executed_today": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "cache_warming",
                    "status": "completed",
                }
            ],
            "timestamp": datetime.now().isoformat(),
        }

    async def get_current_status(self) -> Dict[str, Any]:
        """
        Retorna estado actual del optimizador
        """
        return {
            "status": "active",
            "last_run": datetime.now().isoformat(),
            "next_run": datetime.now().isoformat(),
            "active_jobs": 0,
            "total_optimizations": 15,
        }

    async def execute_optimization(
        self, optimization_type: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simula ejecución de optimización
        """
        return {
            "status": "executed",
            "optimization_type": optimization_type,
            "execution_time_ms": 150,
            "improvements": {
                "query_time_reduction": "15%",
                "cache_hit_increase": "8%",
            },
            "timestamp": datetime.now().isoformat(),
        }

    async def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de recomendaciones de optimización
        """
        return [
            {
                "id": "opt_001",
                "type": "database",
                "priority": "high",
                "description": "Add index on frequently queried column",
                "estimated_impact": 8.5,
            },
            {
                "id": "opt_002",
                "type": "cache",
                "priority": "medium",
                "description": "Increase cache TTL for static data",
                "estimated_impact": 6.2,
            },
        ]
