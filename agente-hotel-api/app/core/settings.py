from enum import Enum
from pydantic import BaseSettings, PostgresDsn, RedisDsn, HttpUrl, EmailStr, SecretStr, validator


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
    # PMS Configuration
    pms_base_url: HttpUrl
    pms_api_key: SecretStr
    pms_timeout: int = 30

    # WhatsApp Meta Cloud
    whatsapp_access_token: SecretStr
    whatsapp_phone_number_id: str
    whatsapp_verify_token: SecretStr

    # Gmail Configuration
    gmail_username: EmailStr
    gmail_app_password: SecretStr

    # Database & Cache
    postgres_url: PostgresDsn
    redis_url: RedisDsn
    database_pool_size: int = 10

    # Operational Settings
    environment: Environment = Environment.DEV
    log_level: LogLevel = LogLevel.INFO
    audio_enabled: bool = True
    tts_engine: TTSEngine = TTSEngine.ESPEAK
    secret_key: SecretStr

    @validator("pms_api_key", "whatsapp_access_token", "whatsapp_verify_token", "gmail_app_password", "secret_key")
    def validate_secrets_in_prod(cls, v, values):
        if values.get("environment") == Environment.PROD and v.get_secret_value() in [
            None,
            "",
            "your_token_here",
            "generate_secure_key_here",
        ]:
            raise ValueError("Critical secret is not set for production environment")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
