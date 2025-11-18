# app/models/pms_schemas.py
# Pydantic schemas para validar respuestas del PMS (QloApps)

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RoomAvailability(BaseModel):
    """Schema para disponibilidad de una habitación."""

    room_id: str = Field(..., description="ID único de la habitación")
    room_type: str = Field(..., description="Tipo de habitación (Doble, Suite, etc.)")
    price_per_night: float = Field(..., ge=0, description="Precio por noche")
    total_price: Optional[float] = Field(None, ge=0, description="Precio total de la estadía")
    currency: str = Field(default="ARS", description="Moneda del precio")
    available_rooms: int = Field(default=1, ge=0, description="Cantidad de habitaciones disponibles")
    max_occupancy: int = Field(default=2, ge=1, le=10, description="Ocupación máxima")
    facilities: List[str] = Field(default_factory=list, description="Amenities de la habitación")
    images: List[str] = Field(default_factory=list, description="URLs de imágenes")
    potentially_stale: bool = Field(
        default=False, description="Marker: datos posiblemente desactualizados (stale cache)"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Valida que la moneda sea una de las soportadas."""
        allowed = ["ARS", "USD", "EUR", "BRL"]
        if v.upper() not in allowed:
            raise ValueError(f"Currency {v} not supported. Allowed: {allowed}")
        return v.upper()


class AvailabilityResponse(BaseModel):
    """Schema para respuesta completa de check_availability."""

    rooms: List[RoomAvailability] = Field(
        ..., description="Lista de habitaciones disponibles"
    )


class ReservationConfirmation(BaseModel):
    """Schema para confirmación de reserva."""

    reservation_uuid: str = Field(..., description="UUID interno de la reserva")
    booking_id: Optional[str] = Field(None, description="ID de booking del PMS")
    booking_reference: str = Field(..., description="Referencia de reserva (REF-XXXXX)")
    status: str = Field(..., description="Estado de la reserva")
    total_amount: float = Field(..., ge=0, description="Monto total")
    currency: str = Field(default="ARS", description="Moneda")
    confirmation_sent: bool = Field(
        default=False, description="Si se envió confirmación al guest"
    )
    check_in: str = Field(..., description="Fecha de check-in (ISO)")
    check_out: str = Field(..., description="Fecha de check-out (ISO)")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Valida que el status sea uno de los permitidos."""
        allowed = ["confirmed", "pending", "cancelled", "failed"]
        if v.lower() not in allowed:
            raise ValueError(f"Status {v} not valid. Allowed: {allowed}")
        return v.lower()


class CancellationResult(BaseModel):
    """Schema para resultado de cancelación."""

    reservation_uuid: str
    booking_reference: str
    status: str = Field(..., description="Debe ser 'cancelled'")
    refund_amount: Optional[float] = Field(None, ge=0)
    cancellation_fee: Optional[float] = Field(None, ge=0)


class RoomDetails(BaseModel):
    """Schema para detalles completos de una habitación."""

    room_id: str
    room_type: str
    description: str = Field(default="", description="Descripción larga de la habitación")
    base_price: float = Field(..., ge=0)
    max_occupancy: int = Field(..., ge=1, le=10)
    size_sqm: Optional[int] = Field(None, ge=0, description="Tamaño en metros cuadrados")
    bed_type: Optional[str] = Field(None, description="Tipo de cama (king, queen, twin)")
    facilities: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    floor: Optional[int] = Field(None, description="Piso donde está ubicada")
    view: Optional[str] = Field(None, description="Vista (mar, ciudad, jardín)")
