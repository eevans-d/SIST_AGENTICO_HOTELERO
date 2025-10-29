from __future__ import annotations

from datetime import date, datetime
from typing import Union


def _separators_for_language(language: str) -> tuple[str, str]:
    """Return (thousands_sep, decimal_sep) for a language code."""
    lang = (language or "es").lower()
    if lang.startswith("en"):
        return ",", "."
    # Default Spanish-style
    return ".", ","


def format_currency(amount: Union[int, float], language: str = "es", with_symbol: bool = True) -> str:
    """Format a numeric amount with locale-appropriate thousands and decimal separators.

    Note: This is a lightweight formatter without external deps. It does not handle
    negative/edge cases beyond basic formatting.
    """
    try:
        value = float(amount)
    except Exception:
        return str(amount)

    thousands, decimal = _separators_for_language(language)

    # Always two decimals
    integral, frac = divmod(abs(value), 1)
    integral_str = f"{int(integral):,}".replace(",", "_")  # Temporary placeholder

    # Apply target thousands separator
    integral_str = integral_str.replace("_", thousands)
    frac_str = f"{frac:.2f}".split(".")[-1]

    sign = "-" if value < 0 else ""
    formatted = f"{sign}{integral_str}{decimal}{frac_str}"
    if with_symbol:
        return f"${formatted}"
    return formatted


def format_date_locale(d: Union[date, datetime, str], language: str = "es") -> str:
    """Format date/datetime as string per language (dd/mm/yyyy vs mm/dd/yyyy).

    If input is already a string, it is returned unchanged.
    """
    if isinstance(d, str):
        return d
    if isinstance(d, datetime):
        d = d.date()

    if not isinstance(d, date):
        return str(d)

    if (language or "es").lower().startswith("en"):
        return d.strftime("%m/%d/%Y")
    # Default Spanish format
    return d.strftime("%d/%m/%Y")
