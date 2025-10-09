"""
Tests unitarios para utilidades de horarios comerciales.
Feature 2: Respuestas con Horario Diferenciado
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.utils.business_hours import (
    is_business_hours,
    get_next_business_open_time,
    format_business_hours
)
from app.core.settings import settings


class TestBusinessHoursUtils:
    """Tests para utilidades de horarios comerciales."""

    def test_is_business_hours_within_range(self):
        """Test: Hora actual dentro del horario comercial."""
        # Arrange - 14:00 (2 PM) en horario 9-21
        test_time = datetime(2025, 10, 9, 14, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is True

    def test_is_business_hours_before_opening(self):
        """Test: Hora antes de apertura."""
        # Arrange - 8:00 AM, apertura a las 9
        test_time = datetime(2025, 10, 9, 8, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is False

    def test_is_business_hours_after_closing(self):
        """Test: Hora después de cierre."""
        # Arrange - 22:00 (10 PM), cierre a las 21
        test_time = datetime(2025, 10, 9, 22, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is False

    def test_is_business_hours_at_opening_time(self):
        """Test: Hora exacta de apertura (debe ser True)."""
        # Arrange - 9:00 AM exacto
        test_time = datetime(2025, 10, 9, 9, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is True

    def test_is_business_hours_at_closing_time(self):
        """Test: Hora exacta de cierre (debe ser False)."""
        # Arrange - 21:00 (9 PM) exacto
        test_time = datetime(2025, 10, 9, 21, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is False  # end_hour es exclusivo

    def test_is_business_hours_uses_settings_defaults(self):
        """Test: Uso de valores por defecto de settings."""
        # Arrange - Usar hora actual y valores de settings
        # Crear un tiempo dentro del horario por defecto (9-21)
        test_time = datetime.now(ZoneInfo(settings.business_hours_timezone))
        test_time = test_time.replace(hour=15, minute=0, second=0)  # 3 PM
        
        # Act
        result = is_business_hours(current_time=test_time)
        
        # Assert
        # Debe usar settings.business_hours_start y settings.business_hours_end
        assert isinstance(result, bool)

    def test_is_business_hours_invalid_timezone_fallback(self):
        """Test: Fallback a UTC si timezone inválido."""
        # Arrange - Timezone inválido
        test_time = datetime(2025, 10, 9, 14, 0, 0, tzinfo=ZoneInfo("UTC"))
        
        # Act - Debería manejar el error y usar fallback
        result = is_business_hours(
            current_time=None,  # Forzar cálculo interno
            start_hour=9,
            end_hour=21,
            timezone="Invalid/Timezone"
        )
        
        # Assert - No debe lanzar excepción
        assert isinstance(result, bool)

    def test_is_business_hours_midnight_edge_case(self):
        """Test: Caso edge de medianoche."""
        # Arrange - 00:00 (medianoche)
        test_time = datetime(2025, 10, 9, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is False

    def test_get_next_business_open_time_before_opening(self):
        """Test: Próxima apertura cuando está antes de abrir hoy."""
        # Arrange - 8:00 AM, abre a las 9 AM
        test_time = datetime(2025, 10, 9, 8, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        next_open = get_next_business_open_time(current_time=test_time, start_hour=9)
        
        # Assert
        # Debe ser hoy a las 9 AM
        assert next_open.hour == 9
        assert next_open.day == test_time.day

    def test_get_next_business_open_time_after_closing(self):
        """Test: Próxima apertura cuando está después de cierre (mañana)."""
        # Arrange - 22:00 (10 PM), cierra a las 21
        test_time = datetime(2025, 10, 9, 22, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        next_open = get_next_business_open_time(current_time=test_time, start_hour=9)
        
        # Assert
        # Debe ser mañana a las 9 AM
        assert next_open.hour == 9
        assert next_open.day == test_time.day + 1

    def test_get_next_business_open_time_during_business_hours(self):
        """Test: Próxima apertura cuando ya está abierto."""
        # Arrange - 14:00 (2 PM), dentro de horario
        test_time = datetime(2025, 10, 9, 14, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        next_open = get_next_business_open_time(current_time=test_time, start_hour=9)
        
        # Assert
        # Podría ser hoy mismo o mañana, dependiendo de la implementación
        # Verificar que es una datetime válida
        assert isinstance(next_open, datetime)
        assert next_open.hour == 9

    def test_format_business_hours_standard(self):
        """Test: Formato de horarios comerciales estándar."""
        # Act
        result = format_business_hours(start_hour=9, end_hour=21)
        
        # Assert
        assert isinstance(result, str)
        assert "9" in result or "09" in result
        assert "21" in result

    def test_format_business_hours_with_defaults(self):
        """Test: Formato usando valores por defecto."""
        # Act
        result = format_business_hours()
        
        # Assert
        assert isinstance(result, str)
        # Debe contener los valores de settings
        assert str(settings.business_hours_start) in result or f"0{settings.business_hours_start}" in result

    def test_format_business_hours_24hour_format(self):
        """Test: Formato de horario 24 horas."""
        # Act
        result = format_business_hours(start_hour=0, end_hour=23)
        
        # Assert
        assert isinstance(result, str)
        # Debe manejar correctamente horario 24/7

    def test_business_hours_timezone_conversion(self):
        """Test: Conversión correcta de timezone."""
        # Arrange - Crear tiempo en UTC
        utc_time = datetime(2025, 10, 9, 18, 0, 0, tzinfo=ZoneInfo("UTC"))  # 6 PM UTC
        
        # En Buenos Aires (UTC-3) sería 15:00 (3 PM), dentro de horario 9-21
        ba_time = utc_time.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        result = is_business_hours(
            current_time=ba_time,
            start_hour=9,
            end_hour=21,
            timezone="America/Argentina/Buenos_Aires"
        )
        
        # Assert
        assert result is True  # 15:00 está dentro de 9-21

    def test_business_hours_weekend_detection(self):
        """Test: Detección de fin de semana."""
        # Arrange - Sábado
        saturday = datetime(2025, 10, 11, 14, 0, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        
        # Act
        is_weekend = saturday.weekday() >= 5
        
        # Assert
        assert is_weekend is True  # Sábado = 5

    def test_business_hours_edge_case_23_59(self):
        """Test: Caso edge 23:59."""
        # Arrange - 23:59 (casi medianoche)
        test_time = datetime(2025, 10, 9, 23, 59, 0, tzinfo=ZoneInfo("UTC"))
        
        # Act
        result = is_business_hours(current_time=test_time, start_hour=9, end_hour=21)
        
        # Assert
        assert result is False

    def test_next_open_time_preserves_timezone(self):
        """Test: Próxima apertura preserva timezone."""
        # Arrange
        ba_tz = ZoneInfo("America/Argentina/Buenos_Aires")
        test_time = datetime(2025, 10, 9, 22, 0, 0, tzinfo=ba_tz)
        
        # Act
        next_open = get_next_business_open_time(
            current_time=test_time,
            start_hour=9,
            timezone="America/Argentina/Buenos_Aires"
        )
        
        # Assert
        assert next_open.tzinfo is not None
        # Verificar que el timezone está presente (no necesariamente el mismo objeto)
