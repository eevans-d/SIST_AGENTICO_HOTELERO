"""
Mock de ResourceMonitor para tests de autenticación
"""

from typing import Dict, Any, List
from datetime import datetime


class MockResourceMonitor:
    """Mock del servicio ResourceMonitor para tests"""

    async def get_resource_report(self) -> Dict[str, Any]:
        """Retorna reporte de recursos del sistema"""
        return {
            "current_metrics": {
                "cpu_percent": 45.2,
                "memory_percent": 62.8,
                "disk_percent": 35.5,
                "network_io": {"bytes_sent": 1024000, "bytes_recv": 2048000},
            },
            "thresholds": {
                "cpu_warning": 70,
                "cpu_critical": 85,
                "memory_warning": 75,
                "memory_critical": 90,
            },
            "predictions": {
                "cpu_next_hour": 48.5,
                "memory_next_hour": 65.2,
            },
            "active_alerts": [],
            "metrics_history_count": 1440,  # 24 horas de datos
            "timestamp": datetime.now().isoformat(),
        }

    async def get_current_metrics(self) -> Dict[str, float]:
        """Retorna métricas actuales simplificadas"""
        return {
            "cpu_percent": 45.2,
            "memory_percent": 62.8,
            "disk_percent": 35.5,
        }

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Retorna alertas activas"""
        return []
