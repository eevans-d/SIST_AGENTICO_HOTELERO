"""
Mock de AutoScaler para tests de autenticación
"""

from typing import Dict, Any, List
from datetime import datetime


class MockAutoScaler:
    """Mock del servicio AutoScaler para tests"""

    async def get_scaling_status(self) -> Dict[str, Any]:
        """Retorna estado del auto-scaler"""
        return {
            "current_instances": {
                "agente-api": 2,
                "redis": 1,
                "postgres": 1,
            },
            "desired_instances": {
                "agente-api": 2,
                "redis": 1,
                "postgres": 1,
            },
            "decisions_today": 5,
            "last_scaling_event": {
                "timestamp": datetime.now().isoformat(),
                "service": "agente-api",
                "action": "scale_up",
                "from": 1,
                "to": 2,
                "reason": "High CPU usage",
            },
            "rules": [
                {
                    "service": "agente-api",
                    "metric": "cpu_percent",
                    "threshold": 75,
                    "action": "scale_up",
                    "enabled": True,
                }
            ],
            "timestamp": datetime.now().isoformat(),
        }

    async def evaluate(self) -> Dict[str, Any]:
        """Evalúa necesidad de escalado"""
        return {
            "recommendations": [],
            "current_load": "normal",
            "scaling_needed": False,
            "timestamp": datetime.now().isoformat(),
        }

    async def execute(self, service: str, action: str) -> Dict[str, Any]:
        """Ejecuta acción de escalado"""
        return {
            "status": "executed",
            "service": service,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        }

    async def update_rule(
        self, service: str, rule_name: str, value: Any
    ) -> Dict[str, Any]:
        """Actualiza regla de escalado"""
        return {
            "updated": True,
            "service": service,
            "rule": rule_name,
            "new_value": value,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Retorna alertas de escalado"""
        return []

    async def resolve_alert(self, alert_id: str) -> Dict[str, Any]:
        """Marca alerta como resuelta"""
        return {
            "resolved": True,
            "alert_id": alert_id,
            "timestamp": datetime.now().isoformat(),
        }
