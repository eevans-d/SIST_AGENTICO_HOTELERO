"""
Test Suite: Metrics Endpoint IP Allowlist
Validates IP-based access control for /metrics endpoint
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch
from app.main import app
from app.core.settings import get_settings


@pytest_asyncio.fixture
async def test_client():
    """Async test client for FastAPI"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Test 1: IP en allowlist puede acceder a /metrics (200 OK)
@pytest.mark.asyncio
async def test_allowed_ip_can_access_metrics(test_client):
    """
    Verifica que IP en settings.metrics_allowed_ips puede acceder /metrics

    NOTA: TestClient no usa IPs reales, por lo que mockeamos get_real_client_ip()
    para simular diferentes IPs
    """
    from app.routers.metrics import get_real_client_ip

    # Mockear get_real_client_ip para retornar IP permitida
    with patch("app.routers.metrics.get_real_client_ip", return_value="127.0.0.1"):
        response = await test_client.get("/metrics")

    assert response.status_code == 200, (
        "IP en allowlist debe poder acceder /metrics"
    )

    # Validar que retorna métricas de Prometheus
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert b"# HELP" in response.content or b"# TYPE" in response.content


# Test 2: IP no autorizada recibe 403 Forbidden
@pytest.mark.asyncio
async def test_unauthorized_ip_gets_403(test_client):
    """
    Verifica que IP no en allowlist recibe 403 Forbidden
    """
    from app.routers.metrics import get_real_client_ip

    # Mockear IP no autorizada
    with patch("app.routers.metrics.get_real_client_ip", return_value="192.168.100.50"):
        response = await test_client.get("/metrics")

    assert response.status_code == 403, (
        "IP no autorizada debe recibir 403 Forbidden"
    )

    # Validar mensaje de error
    error_data = response.json()
    # FastAPI wrappea HTTPException.detail en campo "detail"
    assert "detail" in error_data
    error_detail = error_data["detail"]
    assert "error" in error_detail
    assert error_detail["error"] == "Forbidden"
    assert "not authorized" in error_detail["message"]


# Test 3: X-Forwarded-For parsing correcto (primera IP)
@pytest.mark.asyncio
async def test_x_forwarded_for_parsing(test_client):
    """
    Verifica que X-Forwarded-For se parsea correctamente (primera IP de la lista)
    """
    from app.routers.metrics import get_real_client_ip
    from fastapi import Request

    # Simular request con X-Forwarded-For
    # Formato: "client, proxy1, proxy2" → debe tomar "client"
    mock_request = type('MockRequest', (), {
        'headers': {'X-Forwarded-For': '127.0.0.1, 10.0.0.1, 172.16.0.1'},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()

    client_ip = get_real_client_ip(mock_request)

    assert client_ip == "127.0.0.1", (
        "get_real_client_ip debe retornar la primera IP de X-Forwarded-For"
    )


# Test 4: X-Real-IP fallback cuando no hay X-Forwarded-For
@pytest.mark.asyncio
async def test_x_real_ip_fallback(test_client):
    """
    Verifica que X-Real-IP se usa cuando X-Forwarded-For no está presente
    """
    from app.routers.metrics import get_real_client_ip

    # Simular request con X-Real-IP
    mock_request = type('MockRequest', (), {
        'headers': {'X-Real-IP': '127.0.0.1'},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()

    client_ip = get_real_client_ip(mock_request)

    assert client_ip == "127.0.0.1", (
        "get_real_client_ip debe retornar X-Real-IP cuando X-Forwarded-For no existe"
    )


# Test 5: request.client.host fallback cuando no hay headers
@pytest.mark.asyncio
async def test_client_host_fallback(test_client):
    """
    Verifica que request.client.host se usa cuando no hay headers de proxy
    """
    from app.routers.metrics import get_real_client_ip

    # Simular request sin headers de proxy
    mock_request = type('MockRequest', (), {
        'headers': {},
        'client': type('Client', (), {'host': '127.0.0.1'})()
    })()

    client_ip = get_real_client_ip(mock_request)

    assert client_ip == "127.0.0.1", (
        "get_real_client_ip debe retornar request.client.host como último fallback"
    )


# Test 6: IPv6 localhost (::1) en allowlist
@pytest.mark.asyncio
async def test_ipv6_localhost_allowed(test_client):
    """
    Verifica que IPv6 localhost (::1) puede acceder /metrics
    """
    from app.routers.metrics import get_real_client_ip

    # Mockear IPv6 localhost
    with patch("app.routers.metrics.get_real_client_ip", return_value="::1"):
        response = await test_client.get("/metrics")

    assert response.status_code == 200, (
        "IPv6 localhost (::1) debe estar en allowlist por defecto"
    )


# Test 7: Multiple IPs permitidas en allowlist
@pytest.mark.asyncio
async def test_multiple_allowed_ips(test_client, monkeypatch):
    """
    Verifica que múltiples IPs en allowlist funcionan correctamente
    """
    from app.routers.metrics import get_real_client_ip

    # Configurar múltiples IPs permitidas
    settings = get_settings()
    original_allowed_ips = settings.metrics_allowed_ips

    try:
        # Agregar IPs de prueba
        settings.metrics_allowed_ips = ["127.0.0.1", "::1", "10.0.0.5", "172.16.0.10"]

        # Probar cada IP permitida
        for allowed_ip in ["127.0.0.1", "10.0.0.5", "172.16.0.10"]:
            with patch("app.routers.metrics.get_real_client_ip", return_value=allowed_ip):
                response = await test_client.get("/metrics")
                assert response.status_code == 200, (
                    f"IP {allowed_ip} en allowlist debe poder acceder /metrics"
                )

        # Probar IP no permitida
        with patch("app.routers.metrics.get_real_client_ip", return_value="192.168.1.100"):
            response = await test_client.get("/metrics")
            assert response.status_code == 403, (
                "IP no en allowlist debe recibir 403"
            )

    finally:
        # Restaurar configuración original
        settings.metrics_allowed_ips = original_allowed_ips


# Test 8: Logging de acceso denegado
@pytest.mark.asyncio
async def test_denied_access_logging(test_client, caplog):
    """
    Verifica que accesos denegados se loguean correctamente
    """
    from app.routers.metrics import get_real_client_ip
    import logging

    # Capturar logs
    with caplog.at_level(logging.WARNING):
        # Mockear IP no autorizada
        with patch("app.routers.metrics.get_real_client_ip", return_value="192.168.100.50"):
            response = await test_client.get("/metrics")

    assert response.status_code == 403

    # Validar que se logueó el acceso denegado
    assert any("Metrics access denied" in record.message for record in caplog.records), (
        "Acceso denegado debe ser logueado"
    )
    assert any("192.168.100.50" in record.message for record in caplog.records), (
        "IP no autorizada debe aparecer en logs"
    )


# Test 9: Logging de acceso concedido
@pytest.mark.asyncio
async def test_granted_access_logging(test_client, caplog):
    """
    Verifica que accesos autorizados se loguean correctamente
    """
    from app.routers.metrics import get_real_client_ip
    import logging

    # Capturar logs
    with caplog.at_level(logging.INFO):
        # Mockear IP autorizada
        with patch("app.routers.metrics.get_real_client_ip", return_value="127.0.0.1"):
            response = await test_client.get("/metrics")

    assert response.status_code == 200

    # Validar que se logueó el acceso concedido
    assert any("Metrics access granted" in record.message for record in caplog.records), (
        "Acceso concedido debe ser logueado"
    )
    assert any("127.0.0.1" in record.message for record in caplog.records), (
        "IP autorizada debe aparecer en logs"
    )


# Test 10: X-Forwarded-For con espacios extra
@pytest.mark.asyncio
async def test_x_forwarded_for_with_spaces(test_client):
    """
    Verifica que X-Forwarded-For con espacios extra se maneja correctamente
    """
    from app.routers.metrics import get_real_client_ip

    # Simular X-Forwarded-For con espacios inconsistentes
    mock_request = type('MockRequest', (), {
        'headers': {'X-Forwarded-For': '  127.0.0.1  ,  10.0.0.1  ,  172.16.0.1  '},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()

    client_ip = get_real_client_ip(mock_request)

    assert client_ip == "127.0.0.1", (
        "get_real_client_ip debe hacer strip() de espacios en X-Forwarded-For"
    )


# Test 11: Precedencia correcta de headers (X-Forwarded-For > X-Real-IP > client.host)
@pytest.mark.asyncio
async def test_header_precedence(test_client):
    """
    Verifica que la precedencia de headers es correcta:
    1. X-Forwarded-For (primera IP)
    2. X-Real-IP
    3. request.client.host
    """
    from app.routers.metrics import get_real_client_ip

    # Caso 1: Solo X-Forwarded-For presente
    mock_request1 = type('MockRequest', (), {
        'headers': {'X-Forwarded-For': '10.0.0.1, 10.0.0.2'},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()
    assert get_real_client_ip(mock_request1) == "10.0.0.1"

    # Caso 2: X-Forwarded-For y X-Real-IP presentes (X-Forwarded-For gana)
    mock_request2 = type('MockRequest', (), {
        'headers': {
            'X-Forwarded-For': '10.0.0.1, 10.0.0.2',
            'X-Real-IP': '172.16.0.1'
        },
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()
    assert get_real_client_ip(mock_request2) == "10.0.0.1"

    # Caso 3: Solo X-Real-IP presente
    mock_request3 = type('MockRequest', (), {
        'headers': {'X-Real-IP': '172.16.0.1'},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()
    assert get_real_client_ip(mock_request3) == "172.16.0.1"

    # Caso 4: Sin headers, solo client.host
    mock_request4 = type('MockRequest', (), {
        'headers': {},
        'client': type('Client', (), {'host': '192.168.1.1'})()
    })()
    assert get_real_client_ip(mock_request4) == "192.168.1.1"


# Test 12: Formato de respuesta 403 (JSON con hint)
@pytest.mark.asyncio
async def test_403_response_format(test_client):
    """
    Verifica que respuesta 403 tiene formato JSON correcto con hint
    """
    from app.routers.metrics import get_real_client_ip

    # Mockear IP no autorizada
    with patch("app.routers.metrics.get_real_client_ip", return_value="192.168.100.50"):
        response = await test_client.get("/metrics")

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Validar estructura de error
    assert "detail" in data
    error_detail = data["detail"]
    assert "error" in error_detail
    assert "message" in error_detail
    assert "hint" in error_detail

    # Validar contenido
    assert error_detail["error"] == "Forbidden"
    assert "192.168.100.50" in error_detail["message"]
    assert "metrics_allowed_ips" in error_detail["hint"]
