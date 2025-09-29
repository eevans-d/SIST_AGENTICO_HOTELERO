from enum import Enum
from typing import Optional

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "development"
    PROD = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TTSEngine(str, Enum):
    ESPEAK = "espeak"
    COQUI = "coqui"


class PMSType(str, Enum):
    QLOAPPS = "qloapps"
    MOCK = "mock"


class Settings(BaseSettings):
    # Config base (Pydantic v2)
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignora variables extra de .env usadas por infraestructura/monitorización
    )

    # App metadata
    app_name: str = "Agente Hotel API"
    version: str = "0.1.0"
    debug: bool = True

    # PMS Configuration
    pms_type: PMSType = PMSType.QLOAPPS
    pms_base_url: str = "http://localhost:8080"
    pms_api_key: SecretStr  # No default - must be provided via environment
    pms_timeout: int = 30

    # WhatsApp Meta Cloud
    whatsapp_access_token: SecretStr  # No default - must be provided via environment
    whatsapp_phone_number_id: str = "000000000000"
    whatsapp_verify_token: SecretStr  # No default - must be provided via environment
    whatsapp_app_secret: SecretStr  # No default - must be provided via environment

    # Gmail Configuration
    gmail_username: str = "dev@example.com"
    gmail_app_password: SecretStr  # No default - must be provided via environment

    # Database & Cache
    # Si existen variables POSTGRES_* se usará para construir postgres_url automáticamente
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_db: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[SecretStr] = None
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 20
    redis_password: Optional[SecretStr] = None

    # Operational Settings
    environment: Environment = Environment.DEV
    log_level: LogLevel = LogLevel.INFO
    audio_enabled: bool = True
    tts_engine: TTSEngine = TTSEngine.ESPEAK
    secret_key: SecretStr  # No default - must be provided via environment
    # Health/Readiness toggles
    check_pms_in_readiness: bool = False

    # Seguridad / CSP
    csp_extra_sources: Optional[str] = None  # Ej: "https://cdn.example.com https://fonts.gstatic.com"
    coop_enabled: bool = False  # Cross-Origin-Opener-Policy
    coep_enabled: bool = False  # Cross-Origin-Embedder-Policy

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    @field_validator(
        "pms_api_key",
        "whatsapp_access_token",
        "whatsapp_verify_token",
        "whatsapp_app_secret",
        "gmail_app_password",
        "secret_key",
    )
    @classmethod
    def validate_secrets_in_prod(cls, v: SecretStr, info):
        env = info.data.get("environment") if hasattr(info, "data") else None
        if (
            env == Environment.PROD
            and v
            and v.get_secret_value()
            in [
                None,
                "",
                "your_token_here",
                "generate_secure_key_here",
                "dev-pms-key",
                "dev-whatsapp-token",
                "dev-verify-token",
                "dev-app-secret",
                "dev-gmail-pass",
                "your_qloapps_api_key_here",
                "your_meta_token_here",
                "your_verify_token_here",
                "your_app_secret_here",
                "your_app_password_here",
            ]
        ):
            raise ValueError("Critical secret contains development/placeholder value for production environment")
        return v

    # Construye postgres_url si hay POSTGRES_* en el entorno o en el modelo
    @field_validator("postgres_url", mode="before")
    @classmethod
    def build_postgres_url(cls, v, info):
        data = getattr(info, "data", {}) or {}
        host = data.get("postgres_host") or None
        port = data.get("postgres_port") or None
        db = data.get("postgres_db") or None
        user = data.get("postgres_user") or None
        pwd = data.get("postgres_password")
        pwd_val = pwd.get_secret_value() if isinstance(pwd, SecretStr) else (pwd or None)

        # Si no hay suficientes datos, mantener el valor existente (por defecto o proporcionado)
        if not (host and port and db and user and pwd_val):
            return v

        return f"postgresql+asyncpg://{user}:{pwd_val}@{host}:{port}/{db}"


settings = Settings()

# Helper para exponer lista normalizada (evita repetir split en middleware)
if settings.csp_extra_sources:
    try:
        settings.csp_extra_sources = " ".join(sorted(set(settings.csp_extra_sources.split())))  # type: ignore[assignment]
    except Exception:  # pragma: no cover - robustez
        pass
