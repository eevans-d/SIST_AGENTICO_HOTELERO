"""
Validador de Entrada Robusto
Protección contra inyección y XSS
"""

import re
from html import escape


class InputValidator:
    """Validador de entrada para prevenir ataques"""

    # Patrones peligrosos
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*)",
        r"(;.*drop\b)",
        r"(;.*delete\b)",
        r"(exec\s*\()",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
    ]

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitizar string eliminando contenido peligroso"""
        if not isinstance(value, str):
            return value

        # Escapar HTML
        sanitized = escape(value)

        # Remover patrones XSS
        for pattern in cls.XSS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def validate_no_sql_injection(cls, value: str) -> bool:
        """Verificar que no haya patrones de SQL injection"""
        if not isinstance(value, str):
            return True

        value_lower = value.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return False

        return True

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validar formato de email"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validar formato de teléfono"""
        # Acepta formatos: +1234567890, 123-456-7890, (123) 456-7890
        pattern = r"^\+?[\d\s\-\(\)]{10,}$"
        return bool(re.match(pattern, phone))


# Instancia global
input_validator = InputValidator()


def get_input_validator() -> InputValidator:
    """Obtener instancia del validador"""
    return input_validator
