# [PROMPT 3.2] app/core/validators.py - Enhanced with comprehensive security validation

import re
from typing import Optional, List, Dict, Any
import bleach
from datetime import datetime
import ipaddress
import urllib.parse

from .logging import logger


class SecurityValidator:
    """Comprehensive security validation for user inputs and system data."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union|select|insert|update|delete|drop|create|alter)\s",
        r"(?i)(or|and)\s+\d+\s*=\s*\d+",
        r"(?i)'?\s*(or|and)\s+'?\w+",
        r"(?i)(exec|execute|sp_|xp_)",
        r"(?i)(script|javascript|vbscript)",
        r"(?i)(onload|onerror|onclick|onmouseover)=",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"data:text/html",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [r"\.\./", r"\.\.\\", r"%2e%2e%2f", r"%2e%2e\\", r"~", r"\x00"]

    @staticmethod
    def validate_user_input(text: str, context: str = "general") -> bool:
        """Validate user input against security threats."""
        if not text or not isinstance(text, str):
            return True  # Empty or non-string input is safe

        # Check for SQL injection
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning("SQL injection attempt detected", text=text[:100], context=context, pattern=pattern)
                return False

        # Check for XSS
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("XSS attempt detected", text=text[:100], context=context, pattern=pattern)
                return False

        # Check for path traversal
        for pattern in SecurityValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("Path traversal attempt detected", text=text[:100], context=context, pattern=pattern)
                return False

        return True

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """Sanitize text input while preserving functionality."""
        if not text or not isinstance(text, str):
            return ""

        # Remove potentially dangerous HTML tags
        if allow_html:
            # Allow safe HTML tags only
            allowed_tags = ["b", "i", "u", "em", "strong", "p", "br"]
            text = bleach.clean(text, tags=allowed_tags, attributes={}, strip=True)
        else:
            # Strip all HTML
            text = bleach.clean(text, tags=[], attributes={}, strip=True)

        # Normalize whitespace
        text = " ".join(text.split())

        # Truncate to max length
        return text[:max_length]

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = None) -> bool:
        """Validate URL format and scheme."""
        if not url:
            return False

        allowed_schemes = allowed_schemes or ["http", "https"]

        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in allowed_schemes and parsed.netloc
        except Exception:
            return False

    @staticmethod
    def validate_file_path(path: str) -> bool:
        """Validate file path to prevent directory traversal."""
        if not path:
            return False

        # Check for path traversal patterns
        for pattern in SecurityValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return False

        # Additional checks
        if path.startswith(("/etc/", "/proc/", "/sys/", "C:\\")):
            return False

        return True


class InputValidator:
    """Enhanced input validator with comprehensive validation rules."""

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize text using the security validator."""
        return SecurityValidator.sanitize_text(text, max_length, allow_html=False)

    @staticmethod
    def validate_phone(phone: str) -> Optional[str]:
        """Validate and normalize phone number."""
        if not phone or not isinstance(phone, str):
            return None

        # Security check first
        if not SecurityValidator.validate_user_input(phone, "phone"):
            return None

        phone = re.sub(r"\D", "", phone)

        # Argentina phone number patterns
        if re.match(r"^54\d{10}$", phone):
            return f"+{phone}"
        elif re.match(r"^\d{10}$", phone):
            return f"+54{phone}"
        elif re.match(r"^9\d{10}$", phone):  # Cell phone with 9 prefix
            return f"+54{phone}"

        return None

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not email or not isinstance(email, str):
            return False

        # Security check first
        if not SecurityValidator.validate_user_input(email, "email"):
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    @staticmethod
    def validate_dates(check_in: str, check_out: str) -> tuple:
        """Validate and parse check-in/check-out dates."""
        try:
            # Security check first
            if not SecurityValidator.validate_user_input(check_in, "date") or not SecurityValidator.validate_user_input(
                check_out, "date"
            ):
                raise ValueError("Invalid date format detected")

            ci = datetime.fromisoformat(check_in).date()
            co = datetime.fromisoformat(check_out).date()

            if ci < datetime.now().date():
                raise ValueError("Check-in no puede ser en el pasado")
            if co <= ci:
                raise ValueError("Check-out debe ser después del check-in")
            if (co - ci).days > 365:  # Extended from 30 to 365 days
                raise ValueError("Estadía máxima 365 días")
            return ci, co
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Fechas inválidas: {e}")

    @staticmethod
    def validate_guest_count(adults: int, children: int = 0) -> bool:
        """Validate guest count numbers."""
        try:
            adults = int(adults)
            children = int(children)

            if adults < 1 or adults > 10:
                return False
            if children < 0 or children > 6:
                return False
            if (adults + children) > 12:
                return False

            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_room_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize room preferences."""
        if not isinstance(preferences, dict):
            return {}

        validated = {}

        # Validate specific preference fields
        allowed_fields = ["room_type", "bed_type", "floor_preference", "special_requests"]

        for field, value in preferences.items():
            if field not in allowed_fields:
                continue

            if isinstance(value, str):
                # Security validation
                if SecurityValidator.validate_user_input(value, f"preference_{field}"):
                    validated[field] = SecurityValidator.sanitize_text(value, 500)
            elif isinstance(value, (int, float, bool)):
                validated[field] = value

        return validated
