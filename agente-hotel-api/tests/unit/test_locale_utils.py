from datetime import date, datetime

from app.utils.locale_utils import format_currency, format_date_locale


def test_format_currency_es():
    assert format_currency(1234.5, "es") == "$1.234,50"
    assert format_currency(1000, "es", with_symbol=False) == "1.000,00"


def test_format_currency_en():
    assert format_currency(1234.5, "en") == "$1,234.50"
    assert format_currency(-42, "en") == "$-42.00"


def test_format_currency_unknown_lang_defaults_es():
    assert format_currency(9999.99, "pt") == "$9.999,99"


def test_format_date_locale():
    d = date(2025, 10, 29)
    assert format_date_locale(d, "es") == "29/10/2025"
    assert format_date_locale(d, "en") == "10/29/2025"

    dt = datetime(2025, 10, 29, 12, 0)
    assert format_date_locale(dt, "es") == "29/10/2025"

    # Already string: unchanged
    assert format_date_locale("2025-10-29", "en") == "2025-10-29"
