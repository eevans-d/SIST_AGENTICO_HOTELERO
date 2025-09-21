# [PROMPT 3.2] app/core/validators.py

import re
from typing import Optional
import bleach
from datetime import datetime


class InputValidator:
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        cleaned = bleach.clean(text, tags=[], strip=True)
        return cleaned[:max_length]

    @staticmethod
    def validate_phone(phone: str) -> Optional[str]:
        phone = re.sub(r"\D", "", phone)
        if re.match(r"^54\d{10}$", phone):
            return f"+{phone}"
        elif re.match(r"^\d{10}$", phone):
            return f"+54{phone}"
        return None

    @staticmethod
    def validate_dates(check_in: str, check_out: str) -> tuple:
        try:
            ci = datetime.fromisoformat(check_in).date()
            co = datetime.fromisoformat(check_out).date()

            if ci < datetime.now().date():
                raise ValueError("Check-in no puede ser en el pasado")
            if co <= ci:
                raise ValueError("Check-out debe ser después del check-in")
            if (co - ci).days > 30:
                raise ValueError("Estadía máxima 30 días")
            return ci, co
        except Exception as e:
            raise ValueError(f"Fechas inválidas: {e}")
