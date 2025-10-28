import pytest
from datetime import datetime, date
from app.utils.i18n_helpers import (
    format_currency,
    format_date,
    format_datetime,
    format_time,
    format_phone,
    parse_date,
    get_month_name,
    get_weekday_name,
)


class TestFormatCurrency:
    def test_currency_es_ars(self):
        """Formato de moneda en español (ARS)."""
        assert format_currency(100.50, "es", "ARS") == "$100,50"
        assert format_currency(1000, "es", "ARS") == "$1.000,00"
        assert format_currency(1234567.89, "es", "ARS") == "$1.234.567,89"

    def test_currency_en_usd(self):
        """Formato de moneda en inglés (USD)."""
        assert format_currency(100.50, "en", "USD") == "U$D100.50"
        assert format_currency(1000, "en", "USD") == "U$D1,000.00"
        assert format_currency(1234567.89, "en", "USD") == "U$D1,234,567.89"

    def test_currency_en_eur(self):
        """Formato de moneda Euro."""
        result = format_currency(100.50, "en", "EUR")
        assert "€" in result
        assert "100.50" in result


class TestFormatDate:
    def test_date_es(self):
        """Formato de fecha en español."""
        dt = date(2025, 10, 20)
        assert format_date(dt, "es") == "20/10/2025"
        assert format_date(dt, "es", short=True) == "20/10"

    def test_date_en(self):
        """Formato de fecha en inglés."""
        dt = date(2025, 10, 20)
        assert format_date(dt, "en") == "10/20/2025"
        assert format_date(dt, "en", short=True) == "10/20"


class TestFormatDateTime:
    def test_datetime_es(self):
        """Formato de datetime en español."""
        dt = datetime(2025, 10, 20, 15, 30, 45)
        result = format_datetime(dt, "es")
        assert "20/10/2025" in result
        assert "15:30" in result

    def test_datetime_en(self):
        """Formato de datetime en inglés."""
        dt = datetime(2025, 10, 20, 15, 30, 45)
        result = format_datetime(dt, "en")
        assert "10/20/2025" in result
        # EN usa formato 12h con AM/PM
        assert "PM" in result or "p" in result.lower()


class TestFormatTime:
    def test_time_es(self):
        """Formato de hora en español."""
        dt = datetime(2025, 10, 20, 15, 30)
        assert format_time(dt, "es") == "15:30"

    def test_time_en(self):
        """Formato de hora en inglés."""
        dt = datetime(2025, 10, 20, 15, 30)
        result = format_time(dt, "en")
        # EN usa 12h
        assert "PM" in result or "p" in result.lower()


class TestFormatPhone:
    def test_phone_argentina(self):
        """Formato de teléfono Argentina."""
        result = format_phone("1123456789", "es", "54")
        assert "+54 11 2345-6789" in result or "+54 11" in result

    def test_phone_usa(self):
        """Formato de teléfono USA."""
        result = format_phone("2025551234", "en", "1")
        assert "+1" in result
        assert "202" in result  # area code


class TestParseDate:
    def test_parse_date_es(self):
        """Parsea fecha en español."""
        result = parse_date("20/10/2025", "es")
        assert result == date(2025, 10, 20)

    def test_parse_date_en(self):
        """Parsea fecha en inglés."""
        result = parse_date("10/20/2025", "en")
        assert result == date(2025, 10, 20)

    def test_parse_date_invalid(self):
        """Retorna None si no puede parsear."""
        result = parse_date("invalid", "es")
        assert result is None


class TestGetMonthName:
    def test_month_es(self):
        """Nombres de meses en español."""
        assert get_month_name(1, "es") == "enero"
        assert get_month_name(10, "es") == "octubre"
        assert get_month_name(1, "es", short=True) == "ene"

    def test_month_en(self):
        """Nombres de meses en inglés."""
        assert get_month_name(1, "en") == "January"
        assert get_month_name(10, "en") == "October"
        assert get_month_name(1, "en", short=True) == "Jan"


class TestGetWeekdayName:
    def test_weekday_es(self):
        """Nombres de días en español."""
        assert get_weekday_name(0, "es") == "lunes"
        assert get_weekday_name(4, "es") == "viernes"
        assert get_weekday_name(0, "es", short=True) == "lun"

    def test_weekday_en(self):
        """Nombres de días en inglés."""
        assert get_weekday_name(0, "en") == "Monday"
        assert get_weekday_name(4, "en") == "Friday"
        assert get_weekday_name(0, "en", short=True) == "Mon"
