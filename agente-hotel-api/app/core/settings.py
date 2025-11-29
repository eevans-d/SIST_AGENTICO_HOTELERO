from enum import Enum
from typing import Optional

from pydantic import SecretStr, field_validator, Field, AliasChoices
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "development"
    STAGING = "staging"
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
    pms_api_key: SecretStr = SecretStr("dev-pms-key")
    pms_timeout: int = 30
    pms_hotel_id: int = 1  # Default hotel ID in QloApps

    # WhatsApp Meta Cloud
    whatsapp_access_token: SecretStr = SecretStr("dev-whatsapp-token")
    whatsapp_phone_number_id: str = "000000000000"
    whatsapp_verify_token: SecretStr = SecretStr("dev-verify-token")
    whatsapp_app_secret: SecretStr = SecretStr("dev-app-secret")

    # Gmail Configuration
    gmail_username: str = "dev@example.com"
    gmail_app_password: SecretStr = SecretStr("dev-gmail-pass")

    # Alert Configuration (for AlertManager)
    alert_email_recipients: list[str] = Field(
        default=[],
        description="List of email addresses to receive system alerts"
    )
    slack_alert_webhook_url: str = Field(
        default="",
        description="Slack webhook URL for alert notifications"
    )

    # Database & Cache
    # Si existen variables POSTGRES_* se usará para construir postgres_url automáticamente
    # Acepta DATABASE_URL (común en plataformas) o POSTGRES_URL además de postgres_url
    # Normalizaremos a URL asíncrona (postgresql+asyncpg://)
    postgres_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "postgres_url"),
    )
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_db: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[SecretStr] = None
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 10
    # Modo Supabase (reduce conexiones para ahorrar costes). Si true y la URL apunta a supabase se aplican límites.
    use_supabase: bool = Field(default=False, validation_alias=AliasChoices("USE_SUPABASE", "use_supabase"))
    supabase_min_pool_size: int = Field(default=2, description="Pool base mínimo al usar Supabase para entornos dev/staging")
    supabase_max_overflow: int = Field(default=2, description="Overflow mínimo al usar Supabase para entornos dev/staging")
    # Acepta REDIS_URL además de redis_url
    redis_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("REDIS_URL", "redis_url"))
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_pool_size: int = 20
    redis_password: Optional[SecretStr] = None

    # Audio Processing Settings
    audio_enabled: bool = True
    tts_engine: TTSEngine = TTSEngine.ESPEAK

    # Whisper STT Configuration
    whisper_model: str = "base"  # tiny, base, small, medium, large
    whisper_language: str = "es"  # Spanish by default

    # Hotel Location Settings (for sharing location feature)
    hotel_latitude: float = -34.6037  # Default: Buenos Aires (configurable per tenant)
    hotel_longitude: float = -58.3816
    hotel_name: str = "Hotel Ejemplo"
    hotel_address: str = "Av. 9 de Julio 1000, Buenos Aires, Argentina"

    # Business Hours Settings (for time-differentiated responses)
    business_hours_start: int = 9  # 9 AM
    business_hours_end: int = 21  # 9 PM
    business_hours_timezone: str = "America/Argentina/Buenos_Aires"

    # Room Images Settings (for photo sending feature)
    room_images_enabled: bool = True
    room_images_base_url: str = "https://example.com/images/rooms/"  # S3 or local NGINX

    # Review Request Settings - Feature 6
    review_max_reminders: int = 3
    review_initial_delay_hours: int = 24  # Wait 24h after checkout
    review_reminder_interval_hours: int = 72  # Remind every 3 days
    google_review_url: str = "https://g.page/r/EXAMPLE/review"
    tripadvisor_review_url: str = "https://www.tripadvisor.com/UserReviewEdit-EXAMPLE"
    booking_review_url: str = "https://www.booking.com/reviewcenter/EXAMPLE"

    # eSpeak TTS Configuration
    espeak_voice: str = "es"
    espeak_speed: int = 150  # words per minute
    espeak_pitch: int = 50  # 0-99

    # Audio Processing Limits
    audio_max_size_mb: int = 25  # WhatsApp limit
    audio_timeout_seconds: int = 30

    # Audio Cache Settings
    audio_cache_enabled: bool = True
    audio_cache_ttl_seconds: int = 86400  # 24 horas por defecto
    audio_cache_max_size_mb: int = 100  # Tamaño máximo de caché en MB
    audio_cache_compression_enabled: bool = True  # Habilitar compresión para archivos grandes
    audio_cache_compression_threshold_kb: int = 100  # Comprimir archivos mayores a 100KB
    audio_cache_compression_level: int = 6  # Nivel de compresión (1-9, donde 9 es máxima compresión)

    # Dead Letter Queue Settings (H2)
    dlq_max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("DLQ_MAX_RETRIES", "dlq_max_retries"),
        description="Maximum retry attempts before permanent failure"
    )
    dlq_retry_backoff_base: int = Field(
        default=60,
        validation_alias=AliasChoices("DLQ_RETRY_BACKOFF_BASE", "dlq_retry_backoff_base"),
        description="Base delay in seconds for exponential backoff (60 → 120 → 240)"
    )
    dlq_ttl_days: int = Field(
        default=7,
        validation_alias=AliasChoices("DLQ_TTL_DAYS", "dlq_ttl_days"),
        description="Time-to-live for DLQ messages in days"
    )
    dlq_worker_interval: int = Field(
        default=300,
        validation_alias=AliasChoices("DLQ_WORKER_INTERVAL", "dlq_worker_interval"),
        description="Retry worker interval in seconds (default: 5 minutes)"
    )

    # Operational Settings
    environment: Environment = Environment.DEV
    log_level: LogLevel = LogLevel.INFO
    secret_key: SecretStr = SecretStr("generate_secure_key_here")
    # Health/Readiness toggles
    check_pms_in_readiness: bool = False
    # New: allow relaxing readiness in environments where DB/Redis may take longer to be available
    # Accept env names in UPPERCASE too (e.g., CHECK_DB_IN_READINESS) for compatibility with platform secrets
    check_db_in_readiness: bool = Field(default=True, validation_alias=AliasChoices("CHECK_DB_IN_READINESS", "check_db_in_readiness"))
    check_redis_in_readiness: bool = Field(default=True, validation_alias=AliasChoices("CHECK_REDIS_IN_READINESS", "check_redis_in_readiness"))

    # Seguridad / CSP
    csp_extra_sources: Optional[str] = None  # Ej: "https://cdn.example.com https://fonts.gstatic.com"
    coop_enabled: bool = False  # Cross-Origin-Opener-Policy
    coep_enabled: bool = False  # Cross-Origin-Embedder-Policy

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Metrics Security Configuration
    metrics_allowed_ips: list[str] = Field(
        default=["127.0.0.1", "::1"],
        description="Allowed IPs for Prometheus scraping. IPv4 and IPv6 supported."
    )

    # Tracing / Sampling configuration
    trace_sampling_rate: float = Field(
        default=1.0,
        description="Base sampling rate for traces (0.0 - 1.0)",
        validation_alias=AliasChoices("TRACE_SAMPLING_RATE", "trace_sampling_rate"),
    )

    # TrustedHost Configuration (PROD only)
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed Host headers in production. Configure with real domains."
    )

    @field_validator("metrics_allowed_ips", mode="before")
    @classmethod
    def parse_metrics_ips(cls, v):
        """Parse and validate IP addresses from string or list"""
        import ipaddress
        import json
        
        # Handle string input (from env vars)
        if isinstance(v, str):
            # Try parsing as JSON array first
            try:
                v = json.loads(v)
            except (json.JSONDecodeError, ValueError):
                # Fall back to comma-separated string
                v = [ip.strip() for ip in v.split(",") if ip.strip()]
        
        # Ensure we have a list
        if not isinstance(v, list):
            v = [v]
        
        # Validate each IP
        validated_ips = []
        for ip_str in v:
            try:
                # Validate IPv4 or IPv6
                ipaddress.ip_address(str(ip_str).strip())
                validated_ips.append(str(ip_str).strip())
            except ValueError:
                raise ValueError(
                    f"Invalid IP address in metrics_allowed_ips: {ip_str}"
                )

        if not validated_ips:
            raise ValueError(
                "metrics_allowed_ips must contain at least one valid IP address"
            )

        return validated_ips

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
        """
        Valida que secrets no usen valores dummy en producción.
        Previene deploys accidentales con credenciales de desarrollo.
        """
        env = info.data.get("environment") if hasattr(info, "data") else None

        # Lista extendida de valores dummy prohibidos en producción
        dummy_values = [
            None,
            "",
            "your_token_here",
            "generate_secure_key_here",
            "dev-pms-key",
            "dev-whatsapp-token",
            "dev-verify-token",
            "dev-app-secret",
            "dev-gmail-pass",
            "test",
            "testing",
            "dummy",
            "changeme",
            "replace_me",
            "secret",
            "password",
            "12345",
        ]

        if env == Environment.PROD and v:
            secret_value = v.get_secret_value()
            if secret_value in dummy_values or len(secret_value) < 8:
                field_name = info.field_name if hasattr(info, "field_name") else "secret"
                raise ValueError(
                    f"Production secret '{field_name}' is not secure. "
                    f"Must be at least 8 characters and not a dummy value. "
                    f"Please set proper secrets in production environment."
                )
        return v

    # Construye postgres_url si hay POSTGRES_* en el entorno o en el modelo
    @field_validator("postgres_url", mode="before")
    @classmethod
    def build_postgres_url(cls, v, info):
        # Si viene como string, normalizamos a async driver si es necesario
        if isinstance(v, str) and v:
            # Reemplazar esquemas sin async por asyncpg
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # En validación 'before' no siempre están disponibles los otros campos,
        # así que aquí solo normalizamos el esquema si viene como string.
        # La construcción desde componentes se hará en un validador 'after'.
        return v

    @model_validator(mode="after")
    def finalize_postgres_url(self) -> "Settings":
        """Construye postgres_url desde componentes si están presentes.

        Se ejecuta después de que todos los campos hayan sido validados, lo que permite
        combinar postgres_host/port/db/user/password de forma confiable. No sobreescribe
        una URL explícita distinta al valor por defecto.
        """
        try:
            if (
                self.postgres_host
                and self.postgres_port
                and self.postgres_db
                and self.postgres_user
                and self.postgres_password
            ):
                # Solo sobreescribir si la URL actual es el valor por defecto
                DEFAULT_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
                if not self.postgres_url or self.postgres_url == DEFAULT_URL:
                    pwd_val = (
                        self.postgres_password.get_secret_value()
                        if isinstance(self.postgres_password, SecretStr)
                        else str(self.postgres_password)
                    )
                    self.postgres_url = (
                        f"postgresql+asyncpg://{self.postgres_user}:{pwd_val}@"
                        f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                    )
        except Exception:
            # No romper inicio por errores de composición; se mantendrá la URL existente
            pass
        return self

    # Build redis_url dynamically after all fields are set
    def __init__(self, **data):
        super().__init__(**data)
        # If redis_url not explicitly provided, build from redis_host/port/db
        if not self.redis_url or self.redis_url == "redis://localhost:6379/0":
            self.redis_url = f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()

# Ajustes dinámicos de coste Supabase: si USE_SUPABASE=true y la URL contiene 'supabase.co'
if settings.use_supabase and "supabase.co" in settings.postgres_url:
    # Reducir tamaño de pool sólo si valores actuales son mayores que mínimos definidos
    if settings.postgres_pool_size > settings.supabase_min_pool_size:
        settings.postgres_pool_size = settings.supabase_min_pool_size  # type: ignore
    if settings.postgres_max_overflow > settings.supabase_max_overflow:
        settings.postgres_max_overflow = settings.supabase_max_overflow  # type: ignore
    # Desactivar debug SQL para no generar logs excesivos en remoto
    settings.debug = False  # type: ignore



# FastAPI dependency injection function
def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings


# Helper para exponer lista normalizada (evita repetir split en middleware)
if settings.csp_extra_sources:
    try:
        settings.csp_extra_sources = " ".join(sorted(set(settings.csp_extra_sources.split())))  # type: ignore[assignment]
    except Exception:  # pragma: no cover - robustez
        pass
