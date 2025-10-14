"""
WhatsApp-specific exception hierarchy for error handling.

Provides granular error types for different failure scenarios in WhatsApp Business API integration.
"""

from typing import Optional, Dict, Any


class WhatsAppError(Exception):
    """Base exception for all WhatsApp-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "context": self.context,
        }


class WhatsAppAuthError(WhatsAppError):
    """
    Authentication/authorization errors (401, 403).

    Examples:
    - Invalid access token
    - Expired token
    - Insufficient permissions
    """

    def __init__(self, message: str = "WhatsApp authentication failed", status_code: int = 401, **kwargs):
        super().__init__(message, status_code=status_code, **kwargs)


class WhatsAppRateLimitError(WhatsAppError):
    """
    Rate limit exceeded errors (429).

    Business API default: 1000 messages/day
    Cloud API: Variable based on tier
    """

    def __init__(self, message: str = "WhatsApp rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.context["retry_after_seconds"] = retry_after


class WhatsAppMediaError(WhatsAppError):
    """
    Media-related errors (download, upload, format).

    Examples:
    - Media ID not found
    - Download failed
    - Unsupported format
    - File too large
    """

    def __init__(self, message: str = "WhatsApp media operation failed", media_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if media_id:
            self.context["media_id"] = media_id


class WhatsAppTemplateError(WhatsAppError):
    """
    Template message errors.

    Examples:
    - Template not found
    - Invalid parameters
    - Template not approved
    - Parameter count mismatch
    """

    def __init__(
        self, message: str = "WhatsApp template operation failed", template_name: Optional[str] = None, **kwargs
    ):
        super().__init__(message, **kwargs)
        if template_name:
            self.context["template_name"] = template_name


class WhatsAppWebhookError(WhatsAppError):
    """
    Webhook validation/processing errors.

    Examples:
    - Invalid signature
    - Malformed payload
    - Missing required fields
    """

    def __init__(self, message: str = "WhatsApp webhook validation failed", **kwargs):
        super().__init__(message, **kwargs)


class WhatsAppNetworkError(WhatsAppError):
    """
    Network/connectivity errors.

    Examples:
    - Timeout
    - Connection refused
    - DNS resolution failed
    """

    def __init__(self, message: str = "WhatsApp API network error", **kwargs):
        super().__init__(message, **kwargs)
