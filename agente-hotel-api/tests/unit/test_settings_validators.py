import pytest
from pydantic import SecretStr
from app.core.settings import Settings, Environment

@pytest.mark.asyncio
async def test_postgres_url_normalization():
    s = Settings(postgres_url="postgres://user:pass@localhost:5432/dbtest")
    assert s.postgres_url.startswith("postgresql+asyncpg://")

@pytest.mark.asyncio
async def test_build_postgres_url_from_components():
    s = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="hotel",
        postgres_user="u",
        postgres_password=SecretStr("pw-secure"),
        # Forzamos que la URL por defecto esté presente para que el validador la sustituya
        postgres_url="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
    )
    assert s.postgres_url.startswith("postgresql+asyncpg://u:pw-secure@localhost:5432/hotel"), s.postgres_url

@pytest.mark.asyncio
async def test_validate_secrets_in_prod_rejects_dummy():
    with pytest.raises(ValueError):
        Settings(environment=Environment.PROD, secret_key=SecretStr("dev-pms-key"))

@pytest.mark.asyncio
async def test_metrics_allowed_ips_validator_accepts_ipv4_ipv6():
    s = Settings(metrics_allowed_ips=["127.0.0.1", "::1"])  # válidos
    assert "127.0.0.1" in s.metrics_allowed_ips and "::1" in s.metrics_allowed_ips

@pytest.mark.asyncio
async def test_metrics_allowed_ips_validator_rejects_invalid():
    with pytest.raises(ValueError):
        Settings(metrics_allowed_ips=["not_an_ip"])  # inválido
