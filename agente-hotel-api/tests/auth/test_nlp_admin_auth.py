"""
Test Suite: NLP Router JWT Authentication
Validates that admin endpoints require JWT while public endpoints remain accessible
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.core.security import create_access_token

# Endpoints de administración protegidos
ADMIN_ENDPOINTS = [
    ("GET", "/api/nlp/admin/sessions"),
    ("POST", "/api/nlp/admin/cleanup"),
]

# Endpoints públicos que NO requieren autenticación
PUBLIC_ENDPOINTS = [
    ("POST", "/api/nlp/message"),
    ("GET", "/api/nlp/conversation/conv-123"),
    ("GET", "/api/nlp/analytics"),
    ("GET", "/api/nlp/health"),
]


@pytest_asyncio.fixture
async def test_client():
    """Async test client for FastAPI"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
def valid_token():
    """Genera un token JWT válido para testing"""
    return create_access_token(
        data={"sub": "test_admin", "role": "admin"}
    )


@pytest_asyncio.fixture
def expired_token():
    """
    Genera un token JWT expirado
    """
    from datetime import datetime, timezone, timedelta
    from jose import jwt
    from app.core.settings import get_settings

    settings = get_settings()
    payload = {
        "sub": "test_admin",
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=10)
    }
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )


# Test 1: Admin endpoints requieren autenticación (401 sin token)
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
async def test_admin_endpoints_require_authentication(test_client, method, endpoint):
    """
    Verifica que endpoints /admin/* retornan 401 sin token
    """
    if method == "GET":
        response = await test_client.get(endpoint)
    elif method == "POST":
        response = await test_client.post(endpoint, json={})

    assert response.status_code == 401, (
        f"{method} {endpoint} debe retornar 401 sin token, "
        f"pero retornó {response.status_code}"
    )
    assert response.json()["detail"] == "Not authenticated"


# Test 2: Admin endpoints rechazan tokens inválidos (403 Forbidden)
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
async def test_admin_endpoints_reject_invalid_token(test_client, method, endpoint):
    """
    Verifica que endpoints /admin/* retornan 403 con token inválido
    """
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID.INVALID"
    headers = {"Authorization": f"Bearer {invalid_token}"}

    if method == "GET":
        response = await test_client.get(endpoint, headers=headers)
    elif method == "POST":
        response = await test_client.post(endpoint, json={}, headers=headers)

    assert response.status_code == 403, (
        f"{method} {endpoint} debe retornar 403 con token inválido, "
        f"pero retornó {response.status_code}"
    )


# Test 3: Admin endpoints rechazan tokens expirados (403 Forbidden)
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
async def test_admin_endpoints_reject_expired_token(test_client, expired_token, method, endpoint):
    """
    Verifica que endpoints /admin/* retornan 403 con token expirado
    """
    headers = {"Authorization": f"Bearer {expired_token}"}

    if method == "GET":
        response = await test_client.get(endpoint, headers=headers)
    elif method == "POST":
        response = await test_client.post(endpoint, json={}, headers=headers)

    assert response.status_code == 403, (
        f"{method} {endpoint} debe retornar 403 con token expirado, "
        f"pero retornó {response.status_code}"
    )


# Test 4: Admin endpoints accesibles con token válido
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
async def test_admin_endpoints_accept_valid_token(test_client, valid_token, method, endpoint):
    """
    Verifica que endpoints /admin/* aceptan token válido (NO 401/403)
    Puede retornar errores funcionales (400, 500) pero NO de autenticación
    """
    headers = {"Authorization": f"Bearer {valid_token}"}

    if method == "GET":
        response = await test_client.get(endpoint, headers=headers)
    elif method == "POST":
        response = await test_client.post(endpoint, json={}, headers=headers)

    assert response.status_code not in [401, 403], (
        f"{method} {endpoint} con token válido no debe retornar 401/403, "
        f"pero retornó {response.status_code}. Detalles: {response.text}"
    )


# Test 5: Endpoints públicos NO requieren autenticación (accesibles sin token)
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", PUBLIC_ENDPOINTS)
async def test_public_endpoints_no_auth_required(test_client, method, endpoint):
    """
    CRÍTICO: Verifica que endpoints públicos (/message, /conversation, etc.)
    NO requieren token y permanecen accesibles sin autenticación.

    Esto es esencial para el flujo de WhatsApp/Gmail donde guests no tienen tokens.
    """
    if method == "GET":
        response = await test_client.get(endpoint)
    elif method == "POST":
        response = await test_client.post(endpoint, json={"text": "hola", "user_id": "guest-123"})

    # NO debe ser error de autenticación (401/403)
    assert response.status_code not in [401, 403], (
        f"{method} {endpoint} es público y NO debe requerir autenticación, "
        f"pero retornó {response.status_code}"
    )

    # Puede retornar error funcional (400, 500) por datos faltantes,
    # pero NO debe ser bloqueado por autenticación


# Test 6: Endpoints públicos funcionan igual con o sin token
@pytest.mark.asyncio
@pytest.mark.parametrize("method,endpoint", PUBLIC_ENDPOINTS)
async def test_public_endpoints_token_optional(test_client, valid_token, method, endpoint):
    """
    Verifica que endpoints públicos funcionan con o sin token (token es opcional)
    """
    # Request sin token
    if method == "GET":
        response_no_token = await test_client.get(endpoint)
    elif method == "POST":
        response_no_token = await test_client.post(
            endpoint,
            json={"text": "hola", "user_id": "guest-123"}
        )

    # Request con token válido
    headers = {"Authorization": f"Bearer {valid_token}"}
    if method == "GET":
        response_with_token = await test_client.get(endpoint, headers=headers)
    elif method == "POST":
        response_with_token = await test_client.post(
            endpoint,
            json={"text": "hola", "user_id": "guest-123"},
            headers=headers
        )

    # Ambos deben tener el mismo status code (no bloqueados por auth)
    assert response_no_token.status_code == response_with_token.status_code, (
        f"{method} {endpoint} debe comportarse igual con o sin token"
    )

    # Ninguno debe ser error de autenticación
    assert response_no_token.status_code not in [401, 403]
    assert response_with_token.status_code not in [401, 403]


# Test 7: Admin sessions endpoint retorna lista de sesiones con auth válida
@pytest.mark.asyncio
async def test_admin_sessions_returns_data_with_auth(test_client, valid_token):
    """
    Verifica que /admin/sessions retorna datos cuando se proporciona auth válida
    """
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = await test_client.get("/api/nlp/admin/sessions", headers=headers)

    # Debe aceptar el request (no 401/403)
    assert response.status_code not in [401, 403]

    # Si retorna 200, debe tener estructura esperada
    if response.status_code == 200:
        data = response.json()
        assert "active_sessions" in data
        assert "count" in data
        assert isinstance(data["active_sessions"], list)
        assert isinstance(data["count"], int)


# Test 8: Admin cleanup endpoint ejecuta con auth válida
@pytest.mark.asyncio
async def test_admin_cleanup_executes_with_auth(test_client, valid_token):
    """
    Verifica que /admin/cleanup ejecuta cuando se proporciona auth válida
    """
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = await test_client.post("/api/nlp/admin/cleanup", headers=headers)

    # Debe aceptar el request (no 401/403)
    assert response.status_code not in [401, 403]

    # Si retorna 200, debe tener estructura esperada
    if response.status_code == 200:
        data = response.json()
        assert "cleaned_sessions" in data or "message" in data


# Test 9: Rate limiting respeta autenticación
@pytest.mark.asyncio
async def test_rate_limiting_after_auth(test_client, valid_token):
    """
    Verifica que rate limiting se aplica DESPUÉS de validar autenticación.
    Un token inválido debe retornar 403 (no 429 rate limit).
    """
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID.INVALID"
    headers = {"Authorization": f"Bearer {invalid_token}"}

    # Primera llamada con token inválido
    response = await test_client.get("/api/nlp/admin/sessions", headers=headers)

    # Debe ser 403 (auth error), no 429 (rate limit)
    assert response.status_code == 403, (
        "Rate limiting no debe aplicarse antes de validar autenticación"
    )


# Test 10: Multiple admin calls con mismo token válido
@pytest.mark.asyncio
async def test_admin_multiple_calls_same_token(test_client, valid_token):
    """
    Verifica que el mismo token puede usarse múltiples veces en admin endpoints
    """
    headers = {"Authorization": f"Bearer {valid_token}"}

    # Primera llamada
    response1 = await test_client.get("/api/nlp/admin/sessions", headers=headers)
    assert response1.status_code not in [401, 403]

    # Segunda llamada
    response2 = await test_client.post("/api/nlp/admin/cleanup", headers=headers)
    assert response2.status_code not in [401, 403]

    # Tercera llamada
    response3 = await test_client.get("/api/nlp/admin/sessions", headers=headers)
    assert response3.status_code not in [401, 403]


# Test 11: Separación de responsabilidades (admin vs public)
@pytest.mark.asyncio
async def test_endpoint_segregation(test_client):
    """
    Verifica que existe clara separación entre endpoints admin y públicos
    """
    # Admin sin auth → 401
    admin_response = await test_client.get("/api/nlp/admin/sessions")
    assert admin_response.status_code == 401

    # Public sin auth → NO 401
    public_response = await test_client.get("/api/nlp/health")
    assert public_response.status_code != 401

    # Esto valida que la protección está aplicada selectivamente


# Test 12: Token con rol admin vs user (ambos deben ser aceptados)
@pytest.mark.asyncio
async def test_role_based_access_not_enforced(test_client):
    """
    Verifica que cualquier token válido (independiente del rol) puede acceder admin endpoints.

    NOTA: Si en el futuro se implementa RBAC, este test debe actualizarse
    para validar que solo rol 'admin' puede acceder /admin/*.
    """
    # Token con rol admin
    admin_token = create_access_token(
        data={"sub": "admin_user", "role": "admin"}
    )

    # Token con rol user
    user_token = create_access_token(
        data={"sub": "regular_user", "role": "user"}
    )

    # Actualmente ambos deben ser aceptados (solo valida JWT, no roles)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}

    response_admin = await test_client.get("/api/nlp/admin/sessions", headers=admin_headers)
    response_user = await test_client.get("/api/nlp/admin/sessions", headers=user_headers)

    # Ambos no deben ser rechazados por autenticación
    assert response_admin.status_code not in [401, 403]
    assert response_user.status_code not in [401, 403]

    # Ambos no deben ser rechazados por autenticación
    assert response_admin.status_code not in [401, 403]
    assert response_user.status_code not in [401, 403]
