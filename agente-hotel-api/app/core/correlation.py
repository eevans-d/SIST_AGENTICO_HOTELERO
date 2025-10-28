"""
Correlation ID utilities.

Provides a ContextVar-backed correlation id that middleware can set and
downstream services can read to propagate headers to external calls.
"""

from contextvars import ContextVar
from typing import Optional, Dict


_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(value: Optional[str]) -> None:
    """Set the correlation id for the current context."""
    _correlation_id_var.set(value)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation id, if any."""
    return _correlation_id_var.get()


def correlation_headers() -> Dict[str, str]:
    """Return headers to propagate correlation id to external services.

    Includes both X-Request-ID and X-Correlation-ID for compatibility.
    """
    cid = get_correlation_id()
    if not cid:
        return {}
    return {"X-Request-ID": cid, "X-Correlation-ID": cid}
