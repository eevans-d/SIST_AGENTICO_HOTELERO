# [PROMPT GA-03] app/exceptions/pms_exceptions.py


class PMSError(Exception):
    """Base exception for PMS adapter errors."""

    pass


class PMSAuthError(PMSError):
    """Raised for authentication errors with the PMS."""

    pass


class PMSRateLimitError(PMSError):
    """Raised when the PMS rate limit is exceeded."""

    pass


class PMSNotFoundError(PMSError):
    """Raised when a resource is not found in the PMS (404)."""

    pass


class PMSServerError(PMSError):
    """Raised for 5xx errors from the PMS."""

    pass


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open."""

    pass
