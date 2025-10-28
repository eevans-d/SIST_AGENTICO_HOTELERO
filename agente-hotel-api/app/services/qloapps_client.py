"""
QloApps REST API Client
Implements complete integration with QloApps hotel PMS system
API Documentation: https://qloapps.com/qlo-reservation-api/
"""

from datetime import date
from typing import List, Optional, Dict, Any
import httpx
from ..core.logging import logger
from ..core.settings import settings
from ..exceptions.pms_exceptions import PMSError, PMSAuthError, PMSRateLimitError
from ..core.correlation import correlation_headers


class QloAppsClient:
    """
    Client for QloApps REST API.

    QloApps uses PrestaShop-based API with WebService key authentication.
    All requests use XML format but we convert to/from JSON internally.
    """

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize QloApps API client.

        Args:
            base_url: QloApps installation URL (e.g., "https://hotel.example.com")
            api_key: WebService API key from QloApps backoffice
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_endpoint = f"{self.base_url}/api"

        # Configure HTTP client with auth
        self.client = httpx.AsyncClient(
            base_url=self.api_endpoint,
            auth=(self.api_key, ""),  # QloApps uses HTTP Basic Auth with key as username
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AgenteHotelAPI/1.0",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    async def close(self):
        """Close HTTP client connection."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        xml_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to QloApps API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/rooms")
            params: Query parameters
            json_data: JSON request body (will be converted to XML if needed)
            xml_data: Raw XML request body

        Returns:
            Response data as dictionary

        Raises:
            PMSAuthError: Authentication failed
            PMSRateLimitError: Rate limit exceeded
            PMSError: Other API errors
        """
        try:
            # QloApps API uses 'output_format=JSON' parameter for JSON responses
            if params is None:
                params = {}
            params["output_format"] = "JSON"

            # Propagate correlation headers per request
            headers = correlation_headers()
            response = await self.client.request(
                method=method, url=endpoint, params=params, json=json_data, headers=headers or None
            )

            # Handle specific HTTP errors
            if response.status_code == 401:
                raise PMSAuthError("Invalid API key or authentication failed")
            elif response.status_code == 429:
                raise PMSRateLimitError("API rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = f"QloApps API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PMSError(error_msg)

            # Parse response
            if response.content:
                return response.json()
            return {}

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling QloApps API: {e}")
            raise PMSError(f"Failed to communicate with PMS: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in QloApps API call: {e}")
            raise PMSError(f"PMS communication error: {str(e)}")

    # ============================================================================
    # ROOM TYPE OPERATIONS
    # ============================================================================

    async def get_room_types(self) -> List[Dict[str, Any]]:
        """
        Get all available room types.

        Returns:
            List of room type dictionaries with structure:
            {
                "id": int,
                "name": str,
                "description": str,
                "max_adults": int,
                "max_children": int,
                "max_guests": int,
                "facilities": List[str]
            }
        """
        response = await self._request("GET", "/room_types")
        room_types = response.get("room_types", [])

        normalized = []
        for rt in room_types:
            normalized.append(
                {
                    "id": rt.get("id_product"),
                    "name": rt.get("name"),
                    "description": rt.get("description", ""),
                    "max_adults": int(rt.get("max_adults", 2)),
                    "max_children": int(rt.get("max_children", 1)),
                    "max_guests": int(rt.get("max_guests", 3)),
                    "facilities": rt.get("facilities", []),
                }
            )

        return normalized

    async def get_room_type(self, room_type_id: int) -> Dict[str, Any]:
        """
        Get specific room type details.

        Args:
            room_type_id: Room type ID

        Returns:
            Room type dictionary
        """
        response = await self._request("GET", f"/room_types/{room_type_id}")
        rt = response.get("room_type", {})

        return {
            "id": rt.get("id_product"),
            "name": rt.get("name"),
            "description": rt.get("description", ""),
            "max_adults": int(rt.get("max_adults", 2)),
            "max_children": int(rt.get("max_children", 1)),
            "max_guests": int(rt.get("max_guests", 3)),
            "base_price": float(rt.get("price", 0)),
            "facilities": rt.get("facilities", []),
            "images": rt.get("images", []),
        }

    # ============================================================================
    # ROOM AVAILABILITY OPERATIONS
    # ============================================================================

    async def check_availability(
        self,
        hotel_id: int,
        date_from: date,
        date_to: date,
        room_type_id: Optional[int] = None,
        num_rooms: int = 1,
        num_adults: int = 2,
        num_children: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Check room availability for given dates.

        Args:
            hotel_id: Hotel ID in QloApps
            date_from: Check-in date
            date_to: Check-out date
            room_type_id: Specific room type (optional, checks all if not provided)
            num_rooms: Number of rooms needed
            num_adults: Number of adults
            num_children: Number of children

        Returns:
            List of available rooms with pricing:
            [{
                "room_type_id": int,
                "room_type_name": str,
                "available_rooms": int,
                "price_per_night": float,
                "total_price": float,
                "currency": str,
                "max_occupancy": int
            }]
        """
        params = {
            "id_hotel": hotel_id,
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "num_rooms": num_rooms,
            "num_adults": num_adults,
            "num_children": num_children,
        }

        if room_type_id:
            params["id_product"] = room_type_id

        response = await self._request("GET", "/hotel_booking", params=params)

        # Parse availability response
        available_rooms = response.get("available_rooms", [])

        normalized = []
        nights = (date_to - date_from).days

        for room in available_rooms:
            price_per_night = float(room.get("price_per_night", 0))
            total_price = price_per_night * nights * num_rooms

            normalized.append(
                {
                    "room_type_id": room.get("id_product"),
                    "room_type_name": room.get("room_type_name"),
                    "available_rooms": int(room.get("available_num", 0)),
                    "price_per_night": price_per_night,
                    "total_price": total_price,
                    "currency": room.get("currency", "USD"),
                    "max_occupancy": int(room.get("max_occupancy", 2)),
                    "room_images": room.get("images", []),
                    "facilities": room.get("facilities", []),
                }
            )

        return normalized

    # ============================================================================
    # BOOKING/RESERVATION OPERATIONS
    # ============================================================================

    async def create_booking(
        self,
        hotel_id: int,
        room_type_id: int,
        date_from: date,
        date_to: date,
        num_rooms: int,
        guest_info: Dict[str, Any],
        payment_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new booking/reservation.

        Args:
            hotel_id: Hotel ID
            room_type_id: Room type ID
            date_from: Check-in date
            date_to: Check-out date
            num_rooms: Number of rooms to book
            guest_info: Guest information dictionary with:
                - first_name: str
                - last_name: str
                - email: str
                - phone: str
                - country: str (optional)
                - address: str (optional)
            payment_info: Payment information (optional for deposit/prepayment)

        Returns:
            Booking confirmation dictionary:
            {
                "booking_id": str,
                "booking_reference": str,
                "status": str,
                "total_amount": float,
                "currency": str,
                "confirmation_sent": bool
            }
        """
        booking_data = {
            "id_hotel": hotel_id,
            "id_product": room_type_id,
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "num_rooms": num_rooms,
            "customer": {
                "firstname": guest_info.get("first_name"),
                "lastname": guest_info.get("last_name"),
                "email": guest_info.get("email"),
                "phone": guest_info.get("phone"),
                "id_country": guest_info.get("country_id", 1),
                "address": guest_info.get("address", ""),
            },
        }

        if payment_info:
            booking_data["payment"] = payment_info

        response = await self._request("POST", "/hotel_bookings", json_data=booking_data)

        booking = response.get("booking", {})

        return {
            "booking_id": booking.get("id_booking"),
            "booking_reference": booking.get("booking_reference"),
            "status": booking.get("booking_status", "pending"),
            "total_amount": float(booking.get("total_paid", 0)),
            "currency": booking.get("currency", "USD"),
            "confirmation_sent": booking.get("confirmation_sent", False),
            "check_in": booking.get("date_from"),
            "check_out": booking.get("date_to"),
        }

    async def get_booking(self, booking_id: int) -> Dict[str, Any]:
        """
        Get booking details by ID.

        Args:
            booking_id: Booking ID

        Returns:
            Complete booking information
        """
        response = await self._request("GET", f"/hotel_bookings/{booking_id}")
        booking = response.get("booking", {})

        return {
            "booking_id": booking.get("id_booking"),
            "booking_reference": booking.get("booking_reference"),
            "status": booking.get("booking_status"),
            "hotel_id": booking.get("id_hotel"),
            "room_type_id": booking.get("id_product"),
            "room_type_name": booking.get("room_type_name"),
            "check_in": booking.get("date_from"),
            "check_out": booking.get("date_to"),
            "num_rooms": int(booking.get("num_rooms", 1)),
            "num_adults": int(booking.get("num_adults", 2)),
            "num_children": int(booking.get("num_children", 0)),
            "total_amount": float(booking.get("total_paid", 0)),
            "currency": booking.get("currency", "USD"),
            "guest_info": {
                "first_name": booking.get("customer_firstname"),
                "last_name": booking.get("customer_lastname"),
                "email": booking.get("customer_email"),
                "phone": booking.get("customer_phone"),
            },
            "created_at": booking.get("date_add"),
            "updated_at": booking.get("date_upd"),
        }

    async def update_booking_status(self, booking_id: int, new_status: str) -> Dict[str, Any]:
        """
        Update booking status.

        Args:
            booking_id: Booking ID
            new_status: New status (e.g., 'confirmed', 'cancelled', 'checked_in')

        Returns:
            Updated booking information
        """
        update_data = {"booking": {"id_booking": booking_id, "booking_status": new_status}}

        response = await self._request("PUT", f"/hotel_bookings/{booking_id}", json_data=update_data)

        return response.get("booking", {})

    async def cancel_booking(self, booking_id: int, reason: Optional[str] = None) -> bool:
        """
        Cancel a booking.

        Args:
            booking_id: Booking ID to cancel
            reason: Cancellation reason (optional)

        Returns:
            True if cancelled successfully
        """
        try:
            await self.update_booking_status(booking_id, "cancelled")
            logger.info(f"Booking {booking_id} cancelled. Reason: {reason or 'Not specified'}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel booking {booking_id}: {e}")
            return False

    # ============================================================================
    # CUSTOMER/GUEST OPERATIONS
    # ============================================================================

    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer record.

        Args:
            customer_data: Customer information

        Returns:
            Created customer with ID
        """
        response = await self._request("POST", "/customers", json_data=customer_data)
        return response.get("customer", {})

    async def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """Get customer by ID."""
        response = await self._request("GET", f"/customers/{customer_id}")
        return response.get("customer", {})

    async def search_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Search for customer by email.

        Args:
            email: Customer email address

        Returns:
            Customer data if found, None otherwise
        """
        params = {"filter[email]": email}
        response = await self._request("GET", "/customers", params=params)

        customers = response.get("customers", [])
        if customers:
            return customers[0]
        return None

    # ============================================================================
    # HOTEL OPERATIONS
    # ============================================================================

    async def get_hotels(self) -> List[Dict[str, Any]]:
        """Get list of all hotels."""
        response = await self._request("GET", "/hotels")
        return response.get("hotels", [])

    async def get_hotel(self, hotel_id: int) -> Dict[str, Any]:
        """Get specific hotel details."""
        response = await self._request("GET", f"/hotels/{hotel_id}")
        return response.get("hotel", {})

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    async def test_connection(self) -> bool:
        """
        Test API connection and authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.get_hotels()
            logger.info("QloApps API connection test successful")
            return True
        except Exception as e:
            logger.error(f"QloApps API connection test failed: {e}")
            return False


# Factory function for easy instantiation
def create_qloapps_client() -> QloAppsClient:
    """Create QloApps client from settings."""
    return QloAppsClient(base_url=settings.pms_base_url, api_key=settings.pms_api_key.get_secret_value())
