#!/usr/bin/env python3
"""
Background task para actualizar métricas operacionales del hotel.
Este script debe ejecutarse periódicamente (cronjob cada 1-6 horas).

Actualiza:
- hotel_occupancy_rate
- hotel_available_rooms (por tipo)
- hotel_daily_revenue_euros
- hotel_adr_euros
- hotel_revpar_euros
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.core.logging import logger
from app.services.business_metrics import update_operational_metrics
from app.services.pms_adapter import QloAppsAdapter, MockPMSAdapter
import redis.asyncio as redis


async def fetch_pms_data(pms_adapter):
    """
    Fetch datos operacionales del PMS.

    Returns:
        dict con occupancy_rate, available_rooms, daily_revenue, adr
    """
    try:
        # Calcular ocupación actual
        today = date.today()
        tomorrow = date.today().replace(day=today.day + 1) if today.day < 28 else today

        # Query availability para calcular habitaciones disponibles
        availability = await pms_adapter.check_availability(
            checkin=today.isoformat(), checkout=tomorrow.isoformat(), guests=2
        )

        # Contar habitaciones por tipo
        rooms_available = {}
        total_rooms = 0
        for room in availability:
            room_type = room.get("room_type", "unknown")
            rooms_available[room_type] = rooms_available.get(room_type, 0) + 1
            total_rooms += 1

        # Calcular ocupación (asumiendo 50 habitaciones totales - ajustar según hotel)
        total_hotel_rooms = 50
        occupied_rooms = total_hotel_rooms - total_rooms
        occupancy_rate = (occupied_rooms / total_hotel_rooms) * 100 if total_hotel_rooms > 0 else 0

        # Daily revenue y ADR (en producción, obtener del PMS)
        # Por ahora usar valores estimados
        daily_revenue = occupied_rooms * 150.0  # Estimación: €150 por habitación ocupada
        adr = daily_revenue / occupied_rooms if occupied_rooms > 0 else 0

        return {
            "occupancy_rate": occupancy_rate,
            "rooms_available": rooms_available,
            "daily_revenue": daily_revenue,
            "adr": adr,
        }
    except Exception as e:
        logger.error(f"Error fetching PMS data: {e}")
        raise


async def main():
    """Main execution."""
    logger.info("🏨 Starting operational metrics update task...")

    # Conectar a Redis
    redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)

    try:
        # Inicializar PMS Adapter
        if settings.pms_type == "mock":
            pms_adapter = MockPMSAdapter(redis_client)
            logger.info("Using MockPMSAdapter")
        else:
            pms_adapter = QloAppsAdapter(redis_client)
            logger.info("Using QloAppsAdapter")

        # Fetch datos del PMS
        logger.info("Fetching operational data from PMS...")
        data = await fetch_pms_data(pms_adapter)

        # Actualizar métricas de negocio
        logger.info("Updating business metrics...")
        update_operational_metrics(
            current_occupancy=data["occupancy_rate"],
            rooms_available=data["rooms_available"],
            daily_rev=data["daily_revenue"],
            adr=data["adr"],
        )

        logger.info("✅ Operational metrics updated successfully!")
        logger.info(f"   Occupancy: {data['occupancy_rate']:.1f}%")
        logger.info(f"   Rooms available: {sum(data['rooms_available'].values())}")
        logger.info(f"   Daily revenue: €{data['daily_revenue']:.2f}")
        logger.info(f"   ADR: €{data['adr']:.2f}")

    except Exception as e:
        logger.error(f"❌ Failed to update operational metrics: {e}")
        sys.exit(1)
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
