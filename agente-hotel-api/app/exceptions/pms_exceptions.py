# [PROMPT GA-03] app/exceptions/pms_exceptions.py - Enhanced with comprehensive error handling

from typing import Dict, Any, Optional
import time


class PMSError(Exception):
    """Base exception for PMS adapter errors with enhanced context."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.correlation_id = correlation_id
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


class PMSAuthError(PMSError):
    """Raised for authentication errors with the PMS."""

    def __init__(self, message: str = "PMS authentication failed", **kwargs):
        super().__init__(message, error_code="PMS_AUTH_ERROR", **kwargs)


class PMSRateLimitError(PMSError):
    """Raised when the PMS rate limit is exceeded."""

    def __init__(self, message: str = "PMS rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="PMS_RATE_LIMIT", **kwargs)
        self.retry_after = retry_after


class PMSServerError(PMSError):
    """Raised for 5xx errors from the PMS."""

    def __init__(self, message: str = "PMS server error", status_code: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="PMS_SERVER_ERROR", **kwargs)
        self.status_code = status_code


class PMSTimeoutError(PMSError):
    """Raised when PMS operations timeout."""

    def __init__(self, message: str = "PMS operation timed out", timeout_duration: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="PMS_TIMEOUT", **kwargs)
        self.timeout_duration = timeout_duration


class PMSValidationError(PMSError):
    """Raised for PMS data validation errors."""

    def __init__(self, message: str = "PMS data validation failed", validation_errors: Optional[list] = None, **kwargs):
        super().__init__(message, error_code="PMS_VALIDATION_ERROR", **kwargs)
        self.validation_errors = validation_errors or []


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        service_name: str = "unknown",
        failure_count: int = 0,
        recovery_timeout: Optional[float] = None,
    ):
        super().__init__(message)
        self.message = message
        self.service_name = service_name
        self.failure_count = failure_count
        self.recovery_timeout = recovery_timeout
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "service_name": self.service_name,
            "failure_count": self.failure_count,
            "recovery_timeout": self.recovery_timeout,
            "timestamp": self.timestamp,
        }


class SessionError(Exception):
    """Raised for session management errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.session_id = session_id
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.timestamp = time.time()


class ValidationError(Exception):
    """Raised for input validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_rules: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value
        self.validation_rules = validation_rules or []
        self.timestamp = time.time()
