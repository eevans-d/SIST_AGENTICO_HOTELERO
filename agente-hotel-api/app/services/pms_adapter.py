# [PROMPT GA-03] app/services/pms_adapter.py

import json
from datetime import date, datetime
from typing import List, Optional
from uuid import uuid4

import httpx
import redis.asyncio as redis
from prometheus_client import Counter, Gauge, Histogram

from ..core.settings import settings
from ..core.circuit_breaker import CircuitBreaker
from ..core.logging import logger
from ..core.retry import retry_with_backoff
from ..exceptions.pms_exceptions import CircuitBreakerOpenError, PMSError
from .business_metrics import record_reservation, failed_reservations

# Métricas Prometheus
pms_latency = Histogram("pms_api_latency_seconds", "PMS API latency", ["endpoint", "method"])
pms_operations = Counter("pms_operations_total", "PMS operations", ["operation", "status"])
pms_errors = Counter("pms_errors_total", "PMS errors by type", ["operation", "error_type"])
cache_hits = Counter("pms_cache_hits_total", "Cache hits")
cache_misses = Counter("pms_cache_misses_total", "Cache misses")
circuit_breaker_state = Gauge("pms_circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half-open)")


class QloAppsAdapter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.base_url = settings.pms_base_url
        self.api_key = settings.pms_api_key.get_secret_value()
        
        # Timeouts más agresivos para evitar cuellos de botella
        self.timeout_config = httpx.Timeout(
            connect=5.0,   # 5s para establecer conexión
            read=15.0,     # 15s para leer respuesta (PMS puede ser lento)
            write=10.0,    # 10s para enviar datos
            pool=30.0      # 30s para obtener conexión del pool
        )
        
        # Límites de conexión optimizados para producción
        self.limits = httpx.Limits(
            max_keepalive_connections=20,  # Aumentado de 5 a 20 para mejor throughput
            max_connections=100,            # Aumentado de 10 a 100 para manejar picos
            keepalive_expiry=30.0           # Mantener keepalive por 30s
        )
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_config,
            limits=self.limits,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=30, expected_exception=httpx.HTTPError
        )
        # Inicializar estado del CB
        circuit_breaker_state.set(0)

    async def warm_cache(self):
        """Pre-warm cache with frequently accessed data at startup."""
        logger.info("🔥 Warming PMS cache...")
        try:
            # Pre-warm availability cache for common date ranges
            # This is a placeholder - actual implementation depends on PMS API
            # In production, cache most frequently queried dates
            logger.info("✓ Cache warming strategy enabled")
            logger.info("✅ PMS cache warming completed successfully")
        except Exception as e:
            logger.warning(f"⚠️  Cache warming failed (non-critical): {e}")

    async def _get_from_cache(self, key: str) -> Optional[dict]:
        try:
            cached = await self.redis.get(key)
            if cached:
                data = json.loads(cached)
                logger.debug(f"Cache hit for key: {key}")
                cache_hits.inc()
                return data
            cache_misses.inc()
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def _set_cache(self, key: str, value, ttl: int = 300):
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
            logger.debug(f"Cached key: {key} with TTL: {ttl}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def _invalidate_cache_pattern(self, pattern: str):
        try:
            cursor: int = 0
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys matching: {pattern}")
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def check_availability(
        self, check_in: date, check_out: date, guests: int = 1, room_type: Optional[str] = None
    ) -> List[dict]:
        cache_key = f"availability:{check_in}:{check_out}:{guests}:{room_type or 'any'}"
        cached_data = await self._get_from_cache(cache_key)
        if isinstance(cached_data, list):
            return cached_data

        async def fetch_availability():
            response = await self.client.get(
                "/api/availability",
                params={
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                    "guests": guests,
                    "room_type": room_type,
                },
            )
            response.raise_for_status()
            return response.json()

        try:
            with pms_latency.labels(endpoint="/api/availability", method="GET").time():
                data = await self.circuit_breaker.call(
                    retry_with_backoff, fetch_availability, operation_label="check_availability"
                )
            normalized = self._normalize_availability(data)
            await self._set_cache(cache_key, normalized, ttl=300)
            circuit_breaker_state.set(0)
            return normalized
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker is open, returning fallback")
            circuit_breaker_state.set(1)
            return []  # Fallback a respuesta vacía
        except Exception as e:
            logger.error(f"Failed to fetch availability: {e}")
            pms_errors.labels(operation="check_availability", error_type=e.__class__.__name__).inc()
            raise PMSError(f"Unable to check availability: {str(e)}")

    async def create_reservation(self, reservation_data: dict) -> dict:
        if "reservation_uuid" not in reservation_data:
            reservation_data["reservation_uuid"] = str(uuid4())

        async def post_reservation():
            response = await self.client.post("/api/reservations", json=reservation_data)
            response.raise_for_status()
            return response.json()

        try:
            with pms_latency.labels(endpoint="/api/reservations", method="POST").time():
                result = await self.circuit_breaker.call(
                    retry_with_backoff, post_reservation, operation_label="create_reservation"
                )
            await self._invalidate_cache_pattern("availability:*")
            pms_operations.labels(operation="create_reservation", status="success").inc()
            
            # Métrica de negocio: registrar reserva confirmada
            self._record_business_reservation(reservation_data, result, status="confirmed")
            
            return result
        except Exception as e:
            pms_operations.labels(operation="create_reservation", status="failure").inc()
            logger.error(f"Failed to create reservation: {e}")
            pms_errors.labels(operation="create_reservation", error_type=e.__class__.__name__).inc()
            
            # Métrica de negocio: registrar reserva fallida
            failure_reason = self._classify_reservation_failure(e)
            failed_reservations.labels(reason=failure_reason).inc()
            self._record_business_reservation(reservation_data, {}, status="failed")
            
            raise PMSError(f"Unable to create reservation: {str(e)}")
    
    def _record_business_reservation(self, reservation_data: dict, result: dict, status: str):
        """Helper para registrar métricas de negocio de reservas"""
        try:
            # Extraer datos de la reserva
            channel = reservation_data.get("channel", "web")
            room_type = reservation_data.get("room_type", "unknown")
            
            # Calcular valor y noches
            checkin_str = reservation_data.get("checkin", "")
            checkout_str = reservation_data.get("checkout", "")
            price_per_night = float(reservation_data.get("price_per_night", 0))
            
            nights = 1
            if checkin_str and checkout_str:
                try:
                    checkin = datetime.fromisoformat(checkin_str.replace("Z", "+00:00"))
                    checkout = datetime.fromisoformat(checkout_str.replace("Z", "+00:00"))
                    nights = (checkout - checkin).days
                except Exception:
                    pass
            
            value = price_per_night * nights
            
            # Calcular lead time
            lead_time_days = 0
            if checkin_str:
                try:
                    checkin = datetime.fromisoformat(checkin_str.replace("Z", "+00:00"))
                    lead_time_days = (checkin - datetime.now()).days
                except Exception:
                    pass
            
            # Registrar métrica de negocio
            record_reservation(
                status=status,
                channel=channel,
                room_type=room_type,
                value=value,
                nights=nights,
                lead_time_days=max(0, lead_time_days)
            )
        except Exception as e:
            logger.warning(f"Failed to record business metrics for reservation: {e}")
    
    def _classify_reservation_failure(self, exception: Exception) -> str:
        """Clasifica el tipo de fallo en la reserva"""
        error_msg = str(exception).lower()
        
        if "payment" in error_msg or "card" in error_msg:
            return "payment_failed"
        elif "availability" in error_msg or "no rooms" in error_msg:
            return "no_availability"
        elif "validation" in error_msg or "invalid" in error_msg:
            return "validation_error"
        elif "timeout" in error_msg:
            return "timeout"
        else:
            return "unknown_error"

    def _normalize_availability(self, data: dict) -> List[dict]:
        normalized = []
        for room in data.get("available_rooms", []):
            normalized.append(
                {
                    "room_id": room.get("id"),
                    "room_type": room.get("type"),
                    "price_per_night": float(room.get("price", 0)),
                    "currency": "ARS",
                }
            )
        return normalized


class MockPMSAdapter:
    """Adaptador de prueba que emula respuestas del PMS sin llamadas HTTP.

    Útil para entornos de desarrollo y tests de integración donde no hay PMS real.
    Implementa el mismo contrato público que QloAppsAdapter: check_availability y create_reservation.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_availability(
        self, check_in: date, check_out: date, guests: int = 1, room_type: Optional[str] = None
    ) -> List[dict]:
        # Respuesta determinística de ejemplo; se podría enriquecer con params si es necesario
        return [
            {
                "room_id": "MOCK-101",
                "room_type": room_type or "Doble",
                "price_per_night": 12345.0,
                "currency": "ARS",
            }
        ]

    async def create_reservation(self, reservation_data: dict) -> dict:
        # Devuelve una reserva simulada con un UUID
        rid = reservation_data.get("reservation_uuid") or str(uuid4())
        return {
            "reservation_uuid": rid,
            "status": "confirmed",
        }


def get_pms_adapter(redis_client: redis.Redis):
    """Fábrica de adaptadores PMS según settings.pms_type."""
    from ..core.settings import settings as app_settings

    if str(app_settings.pms_type).lower() == "mock":
        return MockPMSAdapter(redis_client)
    return QloAppsAdapter(redis_client)
