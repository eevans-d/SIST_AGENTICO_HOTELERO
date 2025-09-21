# [PROMPT 2.10] tests/conftest.py

import pytest


@pytest.fixture
async def test_app():
    # Lógica para crear una app de prueba con BD temporal
    from app.main import app

    return app
