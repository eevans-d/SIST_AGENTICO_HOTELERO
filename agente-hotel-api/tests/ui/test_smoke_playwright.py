"""Smoke test UI con Playwright (Python).

Este test se salta si no hay playwright instalado o si no se define PLAYWRIGHT_SMOKE_URL.
De esta forma no rompe la colección general ni introduce flakiness cuando el API no está levantado.
"""

import os
import pytest

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:  # pragma: no cover
    pytest.skip("playwright (Python) no instalado", allow_module_level=True)

BASE_URL = os.environ.get("PLAYWRIGHT_SMOKE_URL")

if not BASE_URL:  # pragma: no cover
    pytest.skip("PLAYWRIGHT_SMOKE_URL no seteado; saltando smoke UI", allow_module_level=True)


def test_health_endpoint_accessible():
    """Abre la URL de salud si el servicio está disponible y verifica status HTTP.

    Requiere que PLAYWRIGHT_SMOKE_URL apunte a un endpoint HTTP (p.ej. http://localhost:8002/health/live)
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        resp = page.goto(BASE_URL, wait_until="domcontentloaded")
        try:
            assert resp is not None, "Sin respuesta del servidor"
            assert resp.ok, f"Respuesta no OK: {resp.status}"
        finally:
            browser.close()
