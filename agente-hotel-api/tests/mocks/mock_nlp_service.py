"""
Mock de NLP Service para tests de autenticación de endpoints admin
"""

from typing import Dict, Any, List
from datetime import datetime


class MockNLPService:
    """Mock del servicio NLP para tests de endpoints admin"""

    async def get_sessions(
        self, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """Retorna sesiones de conversación mockeadas"""
        return {
            "sessions": [
                {
                    "id": "session_001",
                    "user_id": "user_123",
                    "created_at": datetime.now().isoformat(),
                    "message_count": 5,
                    "status": "active",
                },
                {
                    "id": "session_002",
                    "user_id": "user_456",
                    "created_at": datetime.now().isoformat(),
                    "message_count": 12,
                    "status": "completed",
                },
            ],
            "total": 2,
            "limit": limit,
            "offset": offset,
        }

    async def cleanup_sessions(
        self, older_than_days: int = 30
    ) -> Dict[str, Any]:
        """Simula limpieza de sesiones antiguas"""
        return {
            "deleted": 0,
            "older_than_days": older_than_days,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

    async def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """Retorna detalles de una sesión"""
        return {
            "id": session_id,
            "user_id": "user_123",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }

    async def get_analytics(self) -> Dict[str, Any]:
        """Retorna analytics de NLP"""
        return {
            "total_sessions": 150,
            "active_sessions": 25,
            "avg_messages_per_session": 8.5,
            "top_intents": [
                {"intent": "check_availability", "count": 450},
                {"intent": "make_reservation", "count": 280},
            ],
        }
