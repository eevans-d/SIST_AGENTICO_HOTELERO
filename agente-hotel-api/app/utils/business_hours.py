# app/utils/business_hours.py
"""
Business hours utilities for time-differentiated responses.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from ..core.settings import settings
from ..core.logging import logger


def is_business_hours(
    current_time: Optional[datetime] = None,
    start_hour: Optional[int] = None,
    end_hour: Optional[int] = None,
    timezone: Optional[str] = None,
) -> bool:
    """
    Check if current time is within business hours.

    Args:
        current_time: Time to check (defaults to now)
        start_hour: Business start hour (defaults to settings)
        end_hour: Business end hour (defaults to settings)
        timezone: Timezone string (defaults to settings)

    Returns:
        True if within business hours, False otherwise

    Example:
        ```python
        if is_business_hours():
            # Send normal response
        else:
            # Send after-hours response
        ```
    """
    # Importante: No forzar True en tests o DEV. Mantener lógica determinística basada en horario real.

    # Use defaults from settings
    start = start_hour if start_hour is not None else settings.business_hours_start
    end = end_hour if end_hour is not None else settings.business_hours_end
    tz = timezone or settings.business_hours_timezone

    # Get current time in hotel timezone
    if current_time is None:
        try:
            tz_info = ZoneInfo(tz)
            current_time = datetime.now(tz_info)
        except Exception as e:
            logger.warning("business_hours.timezone_error", timezone=tz, error=str(e), fallback="UTC")
            # Fallback to UTC if timezone is invalid
            current_time = datetime.now(ZoneInfo("UTC"))

    current_hour = current_time.hour

    # Check if within business hours
    in_hours = start <= current_hour < end

    logger.debug(
        "business_hours.check", current_hour=current_hour, start_hour=start, end_hour=end, in_business_hours=in_hours
    )

    return in_hours


def get_next_business_open_time(
    current_time: Optional[datetime] = None, start_hour: Optional[int] = None, timezone: Optional[str] = None
) -> datetime:
    """
    Get the next time business opens.

    Args:
        current_time: Current time (defaults to now)
        start_hour: Business start hour (defaults to settings)
        timezone: Timezone string (defaults to settings)

    Returns:
        Datetime of next business opening

    Example:
        ```python
        next_open = get_next_business_open_time()
        message = f"Abrimos mañana a las {next_open.hour}:00"
        ```
    """
    start = start_hour if start_hour is not None else settings.business_hours_start
    tz = timezone or settings.business_hours_timezone

    if current_time is None:
        try:
            tz_info = ZoneInfo(tz)
            current_time = datetime.now(tz_info)
        except Exception:
            current_time = datetime.now(ZoneInfo("UTC"))

    # If currently before opening time today, open is today
    if current_time.hour < start:
        next_open = current_time.replace(hour=start, minute=0, second=0, microsecond=0)
    else:
        # Otherwise, open is tomorrow at start_hour
        from datetime import timedelta

        next_day = current_time + timedelta(days=1)
        next_open = next_day.replace(hour=start, minute=0, second=0, microsecond=0)

    return next_open


def format_business_hours(start_hour: Optional[int] = None, end_hour: Optional[int] = None) -> str:
    """
    Format business hours for display.

    Args:
        start_hour: Business start hour (defaults to settings)
        end_hour: Business end hour (defaults to settings)

    Returns:
        Formatted string like "9:00 - 21:00"

    Example:
        ```python
        hours = format_business_hours()  # "9:00 - 21:00"
        ```
    """
    start = start_hour if start_hour is not None else settings.business_hours_start
    end = end_hour if end_hour is not None else settings.business_hours_end

    return f"{start}:00 - {end}:00"
