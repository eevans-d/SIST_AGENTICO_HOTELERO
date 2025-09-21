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


class Settings(BaseSettings):
    # Config base (Pydantic v2)
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # App metadata
    app_name: str = "Agente Hotel API"
    version: str = "0.1.0"
    debug: bool = True

    # PMS Configuration
    pms_base_url: str = "http://localhost:8080"
    pms_api_key: SecretStr = SecretStr("dev-pms-key")
    pms_timeout: int = 30

    # WhatsApp Meta Cloud
    whatsapp_access_token: SecretStr = SecretStr("dev-whatsapp-token")
    whatsapp_phone_number_id: str = "000000000000"
    whatsapp_verify_token: SecretStr = SecretStr("dev-verify-token")

    # Gmail Configuration
    gmail_username: str = "dev@example.com"
    gmail_app_password: SecretStr = SecretStr("dev-gmail-pass")

    # Database & Cache
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
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
    secret_key: SecretStr = SecretStr("generate_secure_key_here")

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    @field_validator("pms_api_key", "whatsapp_access_token", "whatsapp_verify_token", "gmail_app_password", "secret_key")
    @classmethod
    def validate_secrets_in_prod(cls, v: SecretStr, info):
        env = info.data.get("environment") if hasattr(info, "data") else None
        if env == Environment.PROD and v and v.get_secret_value() in [
            None,
            "",
            "your_token_here",
            "generate_secure_key_here",
        ]:
            raise ValueError("Critical secret is not set for production environment")
        return v


settings = Settings()
