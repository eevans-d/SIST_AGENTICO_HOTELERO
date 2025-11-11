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


def test_format_currency_es_en():
    assert format_currency(1234.5, "es", "ARS").startswith("$")
    assert format_currency(1234.5, "es", "ARS") == "$1.234,50"
    # El símbolo configurado para USD en helpers es 'U$D'
    assert format_currency(1234.5, "en", "USD") == "U$D1,234.50"
    # Large number grouping
    assert format_currency(1234567.89, "es", "ARS") == "$1.234.567,89"


def test_format_date_and_datetime():
    d = date(2025, 10, 20)
    dt = datetime(2025, 10, 20, 15, 30)
    assert format_date(d, "es") == "20/10/2025"
    assert format_date(d, "en") == "10/20/2025"
    assert format_date(d, "es", short=True) == "20/10"
    assert format_date(d, "en", short=True) == "10/20"
    assert format_datetime(dt, "es") == "20/10/2025 15:30"
    # EN uses 12h format with AM/PM
    assert "PM" in format_datetime(dt, "en")


def test_format_time_phone_and_parse():
    dt = datetime(2025, 10, 20, 15, 30)
    assert format_time(dt, "es") == "15:30"
    assert "PM" in format_time(dt, "en")

    # Phone AR
    assert format_phone("11-2345-6789", "es", country_code="54") == "+54 11 2345-6789"
    # Phone US
    assert format_phone("(212)555-7890", "en", country_code="1") == "+1 (212) 555-7890"

    # Parse date
    d_es = parse_date("20/10/2025", "es")
    assert d_es is not None and d_es.isoformat() == "2025-10-20"
    d_en = parse_date("10/20/2025", "en")
    assert d_en is not None and d_en.isoformat() == "2025-10-20"
    assert parse_date("bad", "es") is None


def test_month_and_weekday_names():
    assert get_month_name(1, "es") == "enero"
    assert get_month_name(12, "en") == "December"
    assert get_month_name(13, "es") == ""
    assert get_month_name(5, "es", short=True) == "may"

    assert get_weekday_name(0, "es") == "lunes"
    assert get_weekday_name(6, "en") == "Sunday"
    assert get_weekday_name(10, "es") == ""
    assert len(get_weekday_name(3, "en", short=True)) == 3
