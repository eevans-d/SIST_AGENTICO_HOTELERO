# app/utils/humanizer.py

from __future__ import annotations

import re
from typing import Iterable


def apply_es_ar_tone(text: str) -> str:
    """Aplica un tono suave rioplatense (es-AR) sin ser demasiado coloquial.

    Reemplazos conservadores para minimizar riesgos en contenido formal.
    """
    if not isinstance(text, str) or not text:
        return text

    rules: list[tuple[re.Pattern[str], str]] = [
        # voseo básico
        (re.compile(r"\btú\b", re.IGNORECASE), "vos"),
        (re.compile(r"\bpuedes\b", re.IGNORECASE), "podés"),
        (re.compile(r"\bquieres\b", re.IGNORECASE), "querés"),
        (re.compile(r"\bestás\?\b", re.IGNORECASE), "estás?"),  # noop, mantiene tilde
        # expresiones frecuentes
        (re.compile(r"\bvale\b", re.IGNORECASE), "dale"),
        (re.compile(r"\bdisculpa\b", re.IGNORECASE), "perdón"),
        (re.compile(r"\bhola\b", re.IGNORECASE), "Hola"),
    ]

    out = text
    for pat, repl in rules:
        out = pat.sub(repl, out)
    return out


essential_whitespace = re.compile(r"[ \t]+")


def consolidate_text(blocks: Iterable[str]) -> str:
    """Consolida múltiples bloques en un solo mensaje legible.

    - Une con dos saltos de línea
    - Normaliza espacios repetidos
    - Elimina líneas vacías superfluas
    """
    parts = [b.strip() for b in blocks if isinstance(b, str) and b.strip()]
    if not parts:
        return ""
    text = "\n\n".join(parts)
    # Normalizar espacios dentro de líneas
    text = "\n".join(essential_whitespace.sub(" ", line).strip() for line in text.splitlines())
    # Colapsar saltos extra
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
