# [PROMPT 2.8] app/utils/i18n_helpers.py

"""
Utilidades de formato por locale (moneda, fechas, teléfono).

Proporciona helpers para formatear valores según el idioma/región seleccionada.
"""

from datetime import datetime, date
from typing import Union

# Configuraciones de formato por idioma
_LOCALE_CONFIGS = {
    "es": {
        "currency_symbol": "$",
        "currency_position": "left",
        "decimal_sep": ",",
        "thousands_sep": ".",
        "date_format": "%d/%m/%Y",
        "datetime_format": "%d/%m/%Y %H:%M",
        "time_format": "%H:%M",
        "timezone": "America/Argentina/Buenos_Aires",
        "phone_format": "+54 {area} {number}",
    },
    "en": {
        "currency_symbol": "$",
        "currency_position": "left",
        "decimal_sep": ".",
        "thousands_sep": ",",
        "date_format": "%m/%d/%Y",
        "datetime_format": "%m/%d/%Y %I:%M %p",
        "time_format": "%I:%M %p",
        "timezone": "UTC",
        "phone_format": "+1 ({area}) {number}",
    },
}


def format_currency(
    amount: Union[int, float],
    language: str = "es",
    currency_code: str = "ARS",
) -> str:
    """
    Formatea un monto en moneda según el idioma.

    Args:
        amount: Monto a formatear
        language: Idioma (es|en)
        currency_code: Código ISO de moneda (ARS, USD, etc.)

    Returns:
        String formateado (ej: "$100,50" para ES, "$100.50" para EN)
    """
    config = _LOCALE_CONFIGS.get(language, _LOCALE_CONFIGS["es"])

    # Redondear a 2 decimales
    rounded = round(float(amount), 2)
    
    # Separar parte entera y decimal
    integer_part = int(rounded)
    decimal_part = int(round((rounded - integer_part) * 100))

    # Aplicar separador de miles
    integer_str = _add_thousands_separator(
        str(integer_part), config["thousands_sep"]
    )

    # Armar cadena con decimal
    formatted = f"{integer_str}{config['decimal_sep']}{decimal_part:02d}"

    # Posicionar símbolo
    symbol = _get_currency_symbol(currency_code)
    if config["currency_position"] == "left":
        return f"{symbol}{formatted}"
    else:
        return f"{formatted} {symbol}"


def format_date(
    dt: Union[datetime, date],
    language: str = "es",
    short: bool = False,
) -> str:
    """
    Formatea una fecha según el idioma.

    Args:
        dt: Fecha/datetime a formatear
        language: Idioma (es|en)
        short: Si es True, usa formato corto (dd/mm o mm/dd)

    Returns:
        String formateado
    """
    config = _LOCALE_CONFIGS.get(language, _LOCALE_CONFIGS["es"])
    fmt = config["date_format"]

    if short:
        # Formato ultra corto: d/m o m/d
        if language == "es":
            fmt = "%d/%m"
        else:
            fmt = "%m/%d"

    return dt.strftime(fmt)


def format_datetime(
    dt: datetime,
    language: str = "es",
) -> str:
    """
    Formatea un datetime completo según el idioma.

    Args:
        dt: Datetime a formatear
        language: Idioma (es|en)

    Returns:
        String formateado (ej: "20/10/2025 15:30" para ES)
    """
    config = _LOCALE_CONFIGS.get(language, _LOCALE_CONFIGS["es"])
    return dt.strftime(config["datetime_format"])


def format_time(
    dt: Union[datetime, date],
    language: str = "es",
) -> str:
    """
    Formatea solo la hora según el idioma.

    Args:
        dt: Datetime/date a formatear
        language: Idioma (es|en)

    Returns:
        String formateado (ej: "15:30" para ES, "3:30 PM" para EN)
    """
    config = _LOCALE_CONFIGS.get(language, _LOCALE_CONFIGS["es"])

    if isinstance(dt, date) and not isinstance(dt, datetime):
        return ""
    
    return dt.strftime(config["time_format"])


def format_phone(
    phone: str,
    language: str = "es",
    country_code: str = "54",
) -> str:
    """
    Formatea un número de teléfono según el idioma/región.

    Args:
        phone: Número de teléfono (ej: "1123456789" para Argentina)
        language: Idioma (es|en)
        country_code: Código de país (54 para Argentina, 1 para USA)

    Returns:
        String formateado (ej: "+54 11 23456789" para ES)
    """
    # Limpiar dígitos no numéricos
    digits = "".join(c for c in phone if c.isdigit())

    # Para Argentina: formato área-número (11 2345-6789)
    if country_code == "54" and len(digits) == 10:
        area = digits[:2]
        number = f"{digits[2:6]}-{digits[6:]}"
        return f"+54 {area} {number}"
    
    # Para USA: formato (área) número (standard)
    if country_code == "1" and len(digits) == 10:
        area = digits[:3]
        exchange = digits[3:6]
        number = digits[6:]
        return f"+1 ({area}) {exchange}-{number}"

    # Fallback: retornar con código de país
    return f"+{country_code} {digits}"


def parse_date(
    date_str: str,
    language: str = "es",
) -> Union[date, None]:
    """
    Parsea una fecha string en formato local al tipo date.

    Args:
        date_str: String con la fecha (ej: "20/10/2025" para ES)
        language: Idioma (es|en)

    Returns:
        Objeto date, o None si el parseo falla
    """
    config = _LOCALE_CONFIGS.get(language, _LOCALE_CONFIGS["es"])
    try:
        dt = datetime.strptime(date_str, config["date_format"])
        return dt.date()
    except (ValueError, TypeError):
        return None


def get_month_name(
    month: int,
    language: str = "es",
    short: bool = False,
) -> str:
    """
    Obtiene el nombre del mes en el idioma especificado.

    Args:
        month: Número de mes (1-12)
        language: Idioma (es|en)
        short: Si es True, retorna nombre corto (3 letras)

    Returns:
        Nombre del mes
    """
    months_es = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    months_en = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    months = months_es if language == "es" else months_en
    
    try:
        name = months[month - 1]
        if short:
            return name[:3]
        return name
    except IndexError:
        return ""


def get_weekday_name(
    weekday: int,  # 0=Lunes, 6=Domingo
    language: str = "es",
    short: bool = False,
) -> str:
    """
    Obtiene el nombre del día de la semana en el idioma especificado.

    Args:
        weekday: Número de día (0=Lunes, 6=Domingo, similar a dt.weekday())
        language: Idioma (es|en)
        short: Si es True, retorna nombre corto (3 letras)

    Returns:
        Nombre del día
    """
    days_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    days = days_es if language == "es" else days_en
    
    try:
        name = days[weekday]
        if short:
            return name[:3]
        return name
    except IndexError:
        return ""


# Helpers privados

def _add_thousands_separator(num_str: str, separator: str) -> str:
    """Añade separador de miles a una cadena numérica."""
    if len(num_str) <= 3:
        return num_str
    
    parts = []
    for i, digit in enumerate(reversed(num_str)):
        if i > 0 and i % 3 == 0:
            parts.append(separator)
        parts.append(digit)
    
    return "".join(reversed(parts))


def _get_currency_symbol(currency_code: str) -> str:
    """Retorna el símbolo para un código de moneda."""
    symbols = {
        "ARS": "$",
        "USD": "U$D",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "BRL": "R$",
    }
    return symbols.get(currency_code, "$")
