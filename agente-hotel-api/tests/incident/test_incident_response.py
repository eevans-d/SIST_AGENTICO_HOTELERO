"""Incident response tests temporalmente deshabilitados (FASE 0).

Este archivo se reduce a un placeholder para evitar errores de colección y
lint mientras se completa la FASE 0 del blueprint v2.0. Se restaurará en la
FASE 4 (Validation & Resilience).
"""

import pytest

pytestmark = pytest.mark.skip(reason="Skip temporal FASE 0: se reactivará en FASE 4")


def test_placeholder():
    """Mantener estructura mínima de test."""
    assert True

