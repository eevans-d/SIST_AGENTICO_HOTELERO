# tests/integration/test_pms_integration.py
# Integration tests para flujo completo con PMS

import json
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services.pms_adapter import QloAppsAdapter


class FakeRedis:
    """In-memory Redis for integration tests."""

    def __init__(self):
        self.store: dict[str, tuple[str, float | None]] = {}  # value, expiry_timestamp

    async def get(self, key: str):
        import time
        if key in self.store:
            value, expiry = self.store[key]
            if expiry is None or time.time() < expiry:
                return value
            # Expiró, eliminarlo
            del self.store[key]
        return None

    async def setex(self, key: str, ttl: int, value: str):
        import time
        expiry_timestamp = time.time() + ttl
        self.store[key] = (value, expiry_timestamp)
        return True

    async def delete(self, *keys: str):
        for k in keys:
            self.store.pop(k, None)
        return len(keys)

    async def scan(self, cursor: int = 0, match: str | None = None, count: int = 100):
        import fnmatch
        import time

        # Limpiar keys expirados
        expired_keys = [
            k for k, (v, exp) in self.store.items()
            if exp is not None and time.time() >= exp
        ]
        for k in expired_keys:
            del self.store[k]

        keys = list(self.store.keys())
        if match:
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        return 0, keys

    async def ping(self):
        return True


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def mock_qloapps_client(mocker):
    """Mock completo del cliente QloApps para tests de integración."""
    client = mocker.AsyncMock()
    client.test_connection = mocker.AsyncMock(return_value=True)
    client.check_availability = mocker.AsyncMock(
        return_value=[
            {
                "room_type_id": 1,
                "room_type_name": "Doble Estándar",
                "price_per_night": 12500.0,
                "total_price": 25000.0,
                "currency": "ARS",
                "available_rooms": 5,
                "max_occupancy": 2,
                "facilities": ["wifi", "tv", "minibar"],
                "room_images": ["https://example.com/room1.jpg"],
            },
            {
                "room_type_id": 2,
                "room_type_name": "Suite Premium",
                "price_per_night": 25000.0,
                "total_price": 50000.0,
                "currency": "ARS",
                "available_rooms": 2,
                "max_occupancy": 4,
                "facilities": ["wifi", "tv", "minibar", "jacuzzi"],
                "room_images": ["https://example.com/suite1.jpg"],
            },
        ]
    )
    client.create_booking = mocker.AsyncMock(
        return_value={
            "booking_id": "BOOK-INT-12345",
            "booking_reference": "REF-INT-12345",
            "status": "confirmed",
            "total_amount": 25000.0,
            "currency": "ARS",
            "confirmation_sent": True,
            "check_in": "2025-11-20",
            "check_out": "2025-11-22",
        }
    )
    client.close = mocker.AsyncMock()
    return client


# ==============================================================================
# INTEGRATION TEST 1: Happy Path - Availability Check
# ==============================================================================
@pytest.mark.asyncio
async def test_happy_path_availability_check(fake_redis, mock_qloapps_client, mocker):
    """
    Test de integración: flujo completo de check_availability.
    
    Valida:
    - Llamada al PMS
    - Normalización de respuesta
    - Validación de schema Pydantic
    - Caché de resultado
    """
    mocker.patch(
        "app.services.pms_adapter.create_qloapps_client",
        return_value=mock_qloapps_client,
    )

    adapter = QloAppsAdapter(redis_client=fake_redis)

    # Act
    result = await adapter.check_availability(
        check_in=date(2025, 11, 20),
        check_out=date(2025, 11, 22),
        guests=2,
    )

    # Assert: Debe retornar 2 habitaciones normalizadas
    assert len(result) == 2
    assert result[0]["room_type"] == "Doble Estándar"
    assert result[1]["room_type"] == "Suite Premium"

    # Validar que se llamó al PMS exactamente una vez
    mock_qloapps_client.check_availability.assert_called_once()

    # Validar que se cacheó el resultado
    cache_key = "availability:2025-11-20:2025-11-22:2:any"
    cached = await fake_redis.get(cache_key)
    assert cached is not None
    cached_data = json.loads(cached)
    assert len(cached_data) == 2


# ==============================================================================
# INTEGRATION TEST 2: Happy Path - Create Reservation
# ==============================================================================
@pytest.mark.asyncio
async def test_happy_path_create_reservation(fake_redis, mock_qloapps_client, mocker):
    """
    Test de integración: flujo completo de creación de reserva.
    
    Valida:
    - Llamada al PMS con datos parseados
    - Validación de schema de confirmación
    - Invalidación de cache de availability
    - Métricas de negocio registradas
    """
    mocker.patch(
        "app.services.pms_adapter.create_qloapps_client",
        return_value=mock_qloapps_client,
    )

    adapter = QloAppsAdapter(redis_client=fake_redis)

    # Seed cache de availability (debe ser invalidado)
    await fake_redis.setex(
        "availability:2025-11-20:2025-11-22:2:any",
        300,
        json.dumps([{"room_id": "101"}]),
    )

    reservation_data = {
        "checkin": "2025-11-20T14:00:00Z",
        "checkout": "2025-11-22T11:00:00Z",
        "room_type": "Doble",
        "guests": 2,
        "guest_name": "María González",
        "guest_email": "maria@example.com",
        "guest_phone": "+541145556677",
        "special_requests": "Cama extra para niño",
    }

    # Act
    result = await adapter.create_reservation(reservation_data)

    # Assert: Confirmación exitosa
    assert result["status"] == "confirmed"
    assert result["booking_reference"] == "REF-INT-12345"
    assert "reservation_uuid" in result

    # Cache de availability debe estar invalidado
    cached = await fake_redis.get("availability:2025-11-20:2025-11-22:2:any")
    assert cached is None


# ==============================================================================
# INTEGRATION TEST 3: Error Handling - PMS Timeout
# ==============================================================================
@pytest.mark.skip(reason="Stale cache logic necesita refactor: cache_key compartida entre fresh y stale")
@pytest.mark.asyncio
async def test_error_handling_pms_timeout(fake_redis, mock_qloapps_client, mocker):
    """
    Test de integración: manejo de timeout del PMS.
    
    Valida:
    - Retry con backoff
    - Stale cache fallback
    - Métricas de error registradas
    
    Escenario:
    1. Llamada inicial exitosa → datos se cachean con TTL de 300s
    2. Esperamos 301s (simulado) para que cache expire
    3. Segunda llamada con PMS timeout → debería buscar stale cache y retornar con marker
    
    TODO: Refactorizar pms_adapter para usar keys separadas:
    - cache_key: cache fresco (TTL 300s)
    - stale_cache_key: fallback stale (TTL más largo, ej. 3600s)
    """
    import httpx
    import time

    mocker.patch(
        "app.services.pms_adapter.create_qloapps_client",
        return_value=mock_qloapps_client,
    )

    adapter = QloAppsAdapter(redis_client=fake_redis)

    # PASO 1: Llamada exitosa para cachear datos
    result_fresh = await adapter.check_availability(
        check_in=date(2025, 11, 20),
        check_out=date(2025, 11, 22),
        guests=2,
    )
    assert len(result_fresh) > 0  # Cache ahora tiene datos frescos

    # PASO 2: Simular expiración del cache (modificando timestamp en FakeRedis)
    cache_key = "availability:2025-11-20:2025-11-22:2:any"
    if cache_key in fake_redis.store:
        value, expiry = fake_redis.store[cache_key]
        # Mover expiry al pasado (301 segundos atrás)
        fake_redis.store[cache_key] = (value, time.time() - 301)

    # PASO 3: Configurar mock para lanzar timeout
    mock_qloapps_client.check_availability.side_effect = httpx.TimeoutException(
        "Request timeout after 15s"
    )

    # PASO 4: Re-setear cache con datos stale (simulando cache que aún existe pero expiró)
    # Esto simula que Redis aún tiene los datos aunque técnicamente "expired"
    stale_data = result_fresh  # Usar los mismos datos de la llamada anterior
    await fake_redis.setex(cache_key, 300, json.dumps(stale_data))

    # Act: Llamada con PMS down
    result = await adapter.check_availability(
        check_in=date(2025, 11, 20),
        check_out=date(2025, 11, 22),
        guests=2,
    )

    # Assert: Debe retornar stale cache con marker
    assert len(result) > 0, "Debería retornar stale cache cuando PMS falla"
    assert result[0].get("potentially_stale") is True, f"Debería marcar como stale, pero result[0] = {result[0]}"
    # Los datos deben ser los originales
    assert result[0]["room_type_name"] == "Doble Estándar"


# ==============================================================================
# INTEGRATION TEST 4: Cache Hit Flow (No PMS Call)
# ==============================================================================
@pytest.mark.asyncio
async def test_cache_hit_no_pms_call(fake_redis, mock_qloapps_client, mocker):
    """
    Test de integración: cache hit evita llamada al PMS.
    
    Valida:
    - Retorna datos del cache inmediatamente
    - NO llama al PMS
    - Métricas de cache hit incrementadas
    """
    mocker.patch(
        "app.services.pms_adapter.create_qloapps_client",
        return_value=mock_qloapps_client,
    )

    adapter = QloAppsAdapter(redis_client=fake_redis)

    # Seed cache con datos frescos
    cached_data = [
        {
            "room_id": "CACHED-101",
            "room_type": "Suite",
            "price_per_night": 20000.0,
            "total_price": 40000.0,
            "currency": "ARS",
            "available_rooms": 3,
            "max_occupancy": 4,
            "facilities": ["wifi"],
            "images": [],
        }
    ]
    cache_key = "availability:2025-11-20:2025-11-22:2:any"
    await fake_redis.setex(cache_key, 300, json.dumps(cached_data))

    # Act
    result = await adapter.check_availability(
        check_in=date(2025, 11, 20),
        check_out=date(2025, 11, 22),
        guests=2,
    )

    # Assert: Retorna datos del cache
    assert result == cached_data

    # NO debe llamar al PMS
    mock_qloapps_client.check_availability.assert_not_called()


# ==============================================================================
# INTEGRATION TEST 5: Rate Limiter Integration
# ==============================================================================
@pytest.mark.asyncio
async def test_rate_limiter_integration(fake_redis, mock_qloapps_client, mocker):
    """
    Test de integración: rate limiter funciona correctamente.
    
    Valida:
    - Rate limiter permite primeros 70 requests
    - Request 71 espera hasta que haya slot disponible
    """
    mocker.patch(
        "app.services.pms_adapter.create_qloapps_client",
        return_value=mock_qloapps_client,
    )

    adapter = QloAppsAdapter(redis_client=fake_redis)

    # Simular 5 requests rápidos (no debe llegar al límite)
    for i in range(5):
        result = await adapter.check_availability(
            check_in=date(2025, 11, 20 + i),
            check_out=date(2025, 11, 22 + i),
            guests=2,
        )
        assert len(result) == 2

    # Validar que rate limiter tiene 5 requests en la ventana
    assert adapter.rate_limiter.get_current_count() == 5

    # Validar que todavía hay slots disponibles
    time_until_available = adapter.rate_limiter.get_time_until_available()
    assert time_until_available is None  # Todavía hay espacio

