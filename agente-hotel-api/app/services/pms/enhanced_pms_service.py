"""
Enhanced PMS Integration Service
Advanced Property Management System integration with QloApps and fallback providers
"""

import asyncio

# TEMPORAL FIX: Comentado hasta agregar aiohttp a requirements
# import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import hashlib
import random
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Summary
from app.core.prometheus import metrics as _metrics

from app.core.circuit_breaker import CircuitBreaker
from app.core.retry import retry_with_backoff
from app.exceptions.pms_exceptions import PMSError, PMSAuthError, PMSRateLimitError, PMSNotFoundError

logger = logging.getLogger(__name__)

# Prometheus metrics
pms_requests_total = Counter("pms_requests_total", "Total PMS API requests", ["provider", "operation", "status"])

pms_response_time = Histogram("pms_response_time_seconds", "PMS API response time", ["provider", "operation"])

# Reusar métricas centralizadas para evitar duplicados
pms_cache_hits_total = _metrics.pms_cache_hits_total
pms_cache_misses_total = _metrics.pms_cache_misses_total

pms_availability_check_duration = Summary("pms_availability_check_duration_seconds", "Duration of availability checks")

pms_reservation_processing_time = Histogram(
    "pms_reservation_processing_time_seconds", "Time to process reservations", ["operation_type"]
)


class PMSProvider(Enum):
    """Supported PMS providers"""

    QLOAPPS = "qloapps"
    MOCK = "mock"
    OPERA = "opera"  # Future support
    FIDELIO = "fidelio"  # Future support

# Compatibilidad con código/fixtures antiguos
PMSType = PMSProvider


class ReservationStatus(Enum):
    """Reservation status in PMS"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class RoomType(Enum):
    """Standard room types"""

    STANDARD_SINGLE = "standard_single"
    STANDARD_DOUBLE = "standard_double"
    DELUXE_DOUBLE = "deluxe_double"
    JUNIOR_SUITE = "junior_suite"
    EXECUTIVE_SUITE = "executive_suite"
    PRESIDENTIAL_SUITE = "presidential_suite"


@dataclass
class Room:
    """Room representation"""

    id: str
    room_number: str
    room_type: RoomType
    floor: int
    capacity: int
    amenities: List[str] = field(default_factory=list)
    base_price: float = 0.0
    status: str = "available"  # available, occupied, maintenance, out_of_order
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateInfo:
    """Rate information for rooms"""

    rate_id: str
    rate_name: str
    base_rate: float
    currency: str = "USD"
    includes_tax: bool = False
    includes_breakfast: bool = False
    cancellation_policy: str = ""
    minimum_stay: int = 1
    maximum_stay: int = 30


@dataclass
class Availability:
    """Room availability information"""

    date: date
    room_type: RoomType
    available_rooms: int
    total_rooms: int
    rates: List[RateInfo] = field(default_factory=list)
    restrictions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Guest:
    """Guest information"""

    guest_id: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    document_type: str = ""
    document_number: str = ""
    nationality: str = ""
    date_of_birth: Optional[date] = None
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reservation:
    """Complete reservation object"""

    reservation_id: Optional[str] = None
    confirmation_number: Optional[str] = None
    guest: Guest = field(default_factory=Guest)
    room_type: Optional[RoomType] = None
    room_number: Optional[str] = None
    checkin_date: Optional[date] = None
    checkout_date: Optional[date] = None
    adults: int = 1
    children: int = 0
    nights: int = 0
    total_amount: float = 0.0
    currency: str = "USD"
    status: ReservationStatus = ReservationStatus.PENDING
    rate_info: Optional[RateInfo] = None
    special_requests: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = "agente_ia"
    notes: str = ""

    def __post_init__(self):
        if self.checkin_date and self.checkout_date:
            self.nights = (self.checkout_date - self.checkin_date).days


class EnhancedPMSService:
    """Advanced PMS integration service with multiple provider support"""

    def __init__(
        self,
        provider: PMSProvider = PMSProvider.QLOAPPS,
        base_url: str = "http://qloapps:80",
        api_key: str = "",
        redis_client: Optional[redis.Redis] = None,
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.redis_client = redis_client

        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0, expected_exception=PMSError)

        # HTTP session
        self.session: Optional[Any] = None

        # Cache configuration
        self.cache_ttl = {
            "availability": 300,  # 5 minutes
            "rates": 900,  # 15 minutes
            "rooms": 3600,  # 1 hour
            "guest": 1800,  # 30 minutes
        }

        # Provider-specific configurations
        self.provider_configs = {
            PMSProvider.QLOAPPS: {
                "api_version": "v1",
                "auth_header": "X-API-Key",
                "endpoints": {
                    "availability": "/api/v1/availability",
                    "reservations": "/api/v1/reservations",
                    "rooms": "/api/v1/rooms",
                    "guests": "/api/v1/guests",
                    "rates": "/api/v1/rates",
                },
            },
            PMSProvider.MOCK: {
                "api_version": "v1",
                "auth_header": "Authorization",
                "endpoints": {
                    "availability": "/mock/availability",
                    "reservations": "/mock/reservations",
                    "rooms": "/mock/rooms",
                    "guests": "/mock/guests",
                    "rates": "/mock/rates",
                },
            },
        }

        logger.info(f"Enhanced PMS Service initialized - Provider: {provider.value}")

    async def initialize(self):
        """Initialize PMS service and connections"""
        logger.info("🏨 Initializing Enhanced PMS Service...")

        try:
            # Create HTTP session
            timeout = Any(total=30)
            self.session = Any(timeout=timeout)

            # Test connection
            await self._test_connection()

            logger.info("✅ Enhanced PMS Service initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize PMS Service: {e}")
            raise

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

    async def _test_connection(self):
        """Test PMS connection"""
        try:
            if self.provider == PMSProvider.MOCK:
                # Mock provider is always available
                return True

            # Test actual PMS connection
            self.provider_configs[self.provider]
            test_url = f"{self.base_url}/api/health"

            headers = self._get_auth_headers()

            async with self.session.get(test_url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"PMS connection test successful - {self.provider.value}")
                    return True
                else:
                    raise PMSError(f"PMS connection test failed: {response.status}")

        except Exception as e:
            logger.warning(f"PMS connection test failed: {e}")
            # Don't fail initialization - use fallback
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for PMS provider"""
        config = self.provider_configs[self.provider]
        auth_header = config["auth_header"]

        if self.provider == PMSProvider.QLOAPPS:
            return {auth_header: self.api_key}
        elif self.provider == PMSProvider.MOCK:
            return {auth_header: f"Bearer {self.api_key}"}

        return {}

    async def check_availability(
        self,
        checkin_date: date,
        checkout_date: date,
        adults: int = 1,
        children: int = 0,
        room_type: Optional[RoomType] = None,
    ) -> List[Availability]:
        """Check room availability for given dates"""

        start_time = asyncio.get_event_loop().time()

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                "availability",
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                adults=adults,
                children=children,
                room_type=room_type.value if room_type else "all",
            )

            # Check cache first
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                pms_cache_hits_total.labels(operation="availability").inc()
                return [Availability(**item) for item in cached_result]

            pms_cache_misses_total.labels(operation="availability").inc()

            # Circuit breaker protection
            availability_data = await self.circuit_breaker.call(
                self._fetch_availability_from_pms, checkin_date, checkout_date, adults, children, room_type
            )

            # Parse and validate results
            availability_list = self._parse_availability_response(availability_data)

            # Cache results
            await self._cache_result(
                cache_key, [availability.__dict__ for availability in availability_list], self.cache_ttl["availability"]
            )

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            pms_requests_total.labels(
                provider=self.provider.value, operation="check_availability", status="success"
            ).inc()

            pms_response_time.labels(provider=self.provider.value, operation="check_availability").observe(
                processing_time
            )

            pms_availability_check_duration.observe(processing_time)

            logger.info(f"Availability checked successfully - {len(availability_list)} options found")
            return availability_list

        except Exception as e:
            pms_requests_total.labels(
                provider=self.provider.value, operation="check_availability", status="error"
            ).inc()

            logger.error(f"Error checking availability: {e}")

            # Return fallback availability if possible
            return await self._get_fallback_availability(checkin_date, checkout_date, adults, children)

    @retry_with_backoff(max_retries=3)
    async def _fetch_availability_from_pms(
        self, checkin_date: date, checkout_date: date, adults: int, children: int, room_type: Optional[RoomType]
    ) -> Dict[str, Any]:
        """Fetch availability data from PMS"""

        if self.provider == PMSProvider.MOCK:
            return await self._get_mock_availability(checkin_date, checkout_date, adults, children)

        config = self.provider_configs[self.provider]
        url = f"{self.base_url}{config['endpoints']['availability']}"

        params = {
            "checkin": checkin_date.isoformat(),
            "checkout": checkout_date.isoformat(),
            "adults": adults,
            "children": children,
        }

        if room_type:
            params["room_type"] = room_type.value

        headers = self._get_auth_headers()

        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                raise PMSAuthError("Authentication failed")
            elif response.status == 429:
                raise PMSRateLimitError("Rate limit exceeded")
            elif response.status == 404:
                raise PMSNotFoundError("Availability endpoint not found")
            else:
                raise PMSError(f"PMS request failed: {response.status}")

    async def _get_mock_availability(
        self, checkin_date: date, checkout_date: date, adults: int, children: int
    ) -> Dict[str, Any]:
        """Generate mock availability data for testing"""

        # Simulate processing delay
        await asyncio.sleep(0.1)

        mock_rooms = [
            {
                "room_type": "standard_double",
                "available_rooms": 5,
                "total_rooms": 10,
                "base_rate": 150.0,
                "currency": "USD",
            },
            {
                "room_type": "deluxe_double",
                "available_rooms": 3,
                "total_rooms": 8,
                "base_rate": 220.0,
                "currency": "USD",
            },
            {
                "room_type": "junior_suite",
                "available_rooms": 2,
                "total_rooms": 4,
                "base_rate": 350.0,
                "currency": "USD",
            },
        ]

        return {
            "availability": mock_rooms,
            "checkin_date": checkin_date.isoformat(),
            "checkout_date": checkout_date.isoformat(),
            "currency": "USD",
        }

    def _parse_availability_response(self, data: Dict[str, Any]) -> List[Availability]:
        """Parse availability response from PMS"""
        availability_list = []

        for item in data.get("availability", []):
            try:
                # Parse room type
                room_type_str = item.get("room_type", "")
                room_type = (
                    RoomType(room_type_str)
                    if room_type_str in [rt.value for rt in RoomType]
                    else RoomType.STANDARD_DOUBLE
                )

                # Create rate info
                rate_info = RateInfo(
                    rate_id=item.get("rate_id", "standard"),
                    rate_name=item.get("rate_name", "Standard Rate"),
                    base_rate=float(item.get("base_rate", 0)),
                    currency=item.get("currency", "USD"),
                    includes_tax=item.get("includes_tax", False),
                    includes_breakfast=item.get("includes_breakfast", False),
                )

                # Create availability object
                availability = Availability(
                    date=datetime.fromisoformat(data.get("checkin_date")).date(),
                    room_type=room_type,
                    available_rooms=int(item.get("available_rooms", 0)),
                    total_rooms=int(item.get("total_rooms", 0)),
                    rates=[rate_info],
                )

                availability_list.append(availability)

            except Exception as e:
                logger.warning(f"Error parsing availability item: {e}")
                continue

        return availability_list

    async def create_reservation(self, reservation: Reservation) -> Reservation:
        """Create a new reservation in PMS"""

        start_time = asyncio.get_event_loop().time()

        try:
            # Validate reservation data
            self._validate_reservation(reservation)

            # Generate confirmation number if not provided
            if not reservation.confirmation_number:
                reservation.confirmation_number = self._generate_confirmation_number()

            # Circuit breaker protection
            reservation_data = await self.circuit_breaker.call(self._create_reservation_in_pms, reservation)

            # Update reservation with PMS response
            updated_reservation = self._parse_reservation_response(reservation_data, reservation)

            # Cache the reservation
            await self._cache_reservation(updated_reservation)

            # Update metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            pms_requests_total.labels(
                provider=self.provider.value, operation="create_reservation", status="success"
            ).inc()

            pms_reservation_processing_time.labels(operation_type="create").observe(processing_time)

            logger.info(f"Reservation created successfully - ID: {updated_reservation.reservation_id}")
            return updated_reservation

        except Exception as e:
            pms_requests_total.labels(
                provider=self.provider.value, operation="create_reservation", status="error"
            ).inc()

            logger.error(f"Error creating reservation: {e}")
            raise

    @retry_with_backoff(max_retries=3)
    async def _create_reservation_in_pms(self, reservation: Reservation) -> Dict[str, Any]:
        """Create reservation in PMS system"""

        if self.provider == PMSProvider.MOCK:
            return await self._create_mock_reservation(reservation)

        config = self.provider_configs[self.provider]
        url = f"{self.base_url}{config['endpoints']['reservations']}"

        # Prepare reservation data for PMS
        reservation_data = {
            "confirmation_number": reservation.confirmation_number,
            "guest": {
                "first_name": reservation.guest.first_name,
                "last_name": reservation.guest.last_name,
                "email": reservation.guest.email,
                "phone": reservation.guest.phone,
            },
            "room_type": reservation.room_type.value if reservation.room_type else None,
            "checkin_date": reservation.checkin_date.isoformat(),
            "checkout_date": reservation.checkout_date.isoformat(),
            "adults": reservation.adults,
            "children": reservation.children,
            "special_requests": reservation.special_requests,
            "source": reservation.source,
            "notes": reservation.notes,
        }

        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        async with self.session.post(url, json=reservation_data, headers=headers) as response:
            if response.status in [200, 201]:
                return await response.json()
            elif response.status == 401:
                raise PMSAuthError("Authentication failed")
            elif response.status == 429:
                raise PMSRateLimitError("Rate limit exceeded")
            else:
                raise PMSError(f"PMS reservation creation failed: {response.status}")

    async def _create_mock_reservation(self, reservation: Reservation) -> Dict[str, Any]:
        """Create mock reservation for testing"""

        # Simulate processing delay
        await asyncio.sleep(0.2)

        return {
            "reservation_id": f"RES{hash(reservation.confirmation_number) % 100000:05d}",
            "confirmation_number": reservation.confirmation_number,
            "status": "confirmed",
            "room_number": f"{random.randint(100, 999)}",
            "total_amount": 150.0 * reservation.nights,
            "currency": "USD",
            "created_at": datetime.now().isoformat(),
        }

    def _validate_reservation(self, reservation: Reservation):
        """Validate reservation data"""
        if not reservation.checkin_date:
            raise ValueError("Check-in date is required")

        if not reservation.checkout_date:
            raise ValueError("Check-out date is required")

        if reservation.checkout_date <= reservation.checkin_date:
            raise ValueError("Check-out date must be after check-in date")

        if not reservation.guest.first_name or not reservation.guest.last_name:
            raise ValueError("Guest name is required")

        if reservation.adults < 1:
            raise ValueError("At least one adult is required")

        if reservation.children < 0:
            raise ValueError("Children count cannot be negative")

    def _generate_confirmation_number(self) -> str:
        """Generate unique confirmation number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(timestamp.encode()).hexdigest()[:6].upper()
        return f"AGH{timestamp[-6:]}{hash_part}"

    def _parse_reservation_response(self, data: Dict[str, Any], original: Reservation) -> Reservation:
        """Parse reservation response from PMS"""
        original.reservation_id = data.get("reservation_id")
        original.confirmation_number = data.get("confirmation_number", original.confirmation_number)
        original.room_number = data.get("room_number")
        original.total_amount = float(data.get("total_amount", original.total_amount))
        original.currency = data.get("currency", original.currency)

        if data.get("status"):
            status_map = {
                "confirmed": ReservationStatus.CONFIRMED,
                "pending": ReservationStatus.PENDING,
                "cancelled": ReservationStatus.CANCELLED,
            }
            original.status = status_map.get(data["status"], ReservationStatus.CONFIRMED)

        original.updated_at = datetime.now()

        return original

    async def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """Get reservation by ID"""
        try:
            # Check cache first
            cache_key = f"reservation:{reservation_id}"
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                pms_cache_hits_total.labels(operation="get_reservation").inc()
                return Reservation(**cached_result)

            pms_cache_misses_total.labels(operation="get_reservation").inc()

            # Fetch from PMS
            reservation_data = await self._fetch_reservation_from_pms(reservation_id)

            if reservation_data:
                reservation = self._parse_full_reservation_response(reservation_data)
                await self._cache_reservation(reservation)
                return reservation

            return None

        except Exception as e:
            logger.error(f"Error getting reservation {reservation_id}: {e}")
            return None

    async def _fetch_reservation_from_pms(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Fetch reservation from PMS"""

        if self.provider == PMSProvider.MOCK:
            return await self._get_mock_reservation(reservation_id)

        config = self.provider_configs[self.provider]
        url = f"{self.base_url}{config['endpoints']['reservations']}/{reservation_id}"

        headers = self._get_auth_headers()

        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            else:
                raise PMSError(f"PMS get reservation failed: {response.status}")

    async def _get_mock_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """Get mock reservation data"""

        return {
            "reservation_id": reservation_id,
            "confirmation_number": f"AGH{reservation_id[-8:]}",
            "guest": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
            },
            "room_type": "standard_double",
            "room_number": "305",
            "checkin_date": (date.today() + timedelta(days=1)).isoformat(),
            "checkout_date": (date.today() + timedelta(days=3)).isoformat(),
            "adults": 2,
            "children": 0,
            "total_amount": 300.0,
            "currency": "USD",
            "status": "confirmed",
        }

    def _parse_full_reservation_response(self, data: Dict[str, Any]) -> Reservation:
        """Parse full reservation response"""
        guest_data = data.get("guest", {})
        guest = Guest(
            first_name=guest_data.get("first_name", ""),
            last_name=guest_data.get("last_name", ""),
            email=guest_data.get("email", ""),
            phone=guest_data.get("phone", ""),
        )

        room_type_str = data.get("room_type", "")
        room_type = None
        if room_type_str in [rt.value for rt in RoomType]:
            room_type = RoomType(room_type_str)

        status_map = {
            "confirmed": ReservationStatus.CONFIRMED,
            "pending": ReservationStatus.PENDING,
            "cancelled": ReservationStatus.CANCELLED,
            "checked_in": ReservationStatus.CHECKED_IN,
            "checked_out": ReservationStatus.CHECKED_OUT,
        }

        status = status_map.get(data.get("status"), ReservationStatus.CONFIRMED)

        return Reservation(
            reservation_id=data.get("reservation_id"),
            confirmation_number=data.get("confirmation_number"),
            guest=guest,
            room_type=room_type,
            room_number=data.get("room_number"),
            checkin_date=datetime.fromisoformat(data["checkin_date"]).date(),
            checkout_date=datetime.fromisoformat(data["checkout_date"]).date(),
            adults=int(data.get("adults", 1)),
            children=int(data.get("children", 0)),
            total_amount=float(data.get("total_amount", 0)),
            currency=data.get("currency", "USD"),
            status=status,
        )

    async def _get_fallback_availability(
        self, checkin_date: date, checkout_date: date, adults: int, children: int
    ) -> List[Availability]:
        """Get fallback availability when PMS is unavailable"""

        logger.warning("Using fallback availability - PMS unavailable")

        # Return basic availability based on static data
        fallback_availability = [
            Availability(
                date=checkin_date,
                room_type=RoomType.STANDARD_DOUBLE,
                available_rooms=3,
                total_rooms=10,
                rates=[
                    RateInfo(rate_id="fallback_standard", rate_name="Standard Rate", base_rate=150.0, currency="USD")
                ],
            ),
            Availability(
                date=checkin_date,
                room_type=RoomType.DELUXE_DOUBLE,
                available_rooms=1,
                total_rooms=5,
                rates=[RateInfo(rate_id="fallback_deluxe", rate_name="Deluxe Rate", base_rate=220.0, currency="USD")],
            ),
        ]

        return fallback_availability

    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation"""
        key_parts = [operation]
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        if not self.redis_client:
            return None

        try:
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")

        return None

    async def _cache_result(self, key: str, data: Any, ttl: int):
        """Cache result with TTL"""
        if not self.redis_client:
            return

        try:
            await self.redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def _cache_reservation(self, reservation: Reservation):
        """Cache reservation data"""
        if reservation.reservation_id:
            cache_key = f"reservation:{reservation.reservation_id}"
            await self._cache_result(cache_key, reservation.__dict__, self.cache_ttl["guest"])

    async def health_check(self) -> Dict[str, Any]:
        """Health check for PMS service"""
        health_status = {
            "status": "healthy",
            "provider": self.provider.value,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Test PMS connection
            if self.provider != PMSProvider.MOCK:
                await self._test_connection()
                health_status["pms_connection"] = "ok"
            else:
                health_status["pms_connection"] = "mock"

            # Test cache connection
            if self.redis_client:
                await self.redis_client.ping()
                health_status["cache_connection"] = "ok"
            else:
                health_status["cache_connection"] = "not_configured"

        except Exception as e:
            health_status["status"] = "degraded"
            health_status["error"] = str(e)

        return health_status


# Global service instance
_pms_service = None


async def get_pms_service(
    provider: PMSProvider = PMSProvider.MOCK,
    base_url: str = "http://localhost:8080",
    api_key: str = "test_key",
    redis_client: Optional[redis.Redis] = None,
) -> EnhancedPMSService:
    """Get global PMS service instance"""
    global _pms_service
    if _pms_service is None:
        _pms_service = EnhancedPMSService(provider, base_url, api_key, redis_client)
        await _pms_service.initialize()
    return _pms_service


async def create_pms_service(
    provider: PMSProvider = PMSProvider.MOCK,
    base_url: str = "http://localhost:8080",
    api_key: str = "test_key",
    redis_client: Optional[redis.Redis] = None,
) -> EnhancedPMSService:
    """Create new PMS service instance"""
    service = EnhancedPMSService(provider, base_url, api_key, redis_client)
    await service.initialize()
    return service
