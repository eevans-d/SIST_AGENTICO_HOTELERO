"""
Sistema de Configuración Avanzada
Configuración completa para producción y desarrollo
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
import secrets


class Environment(str, Enum):
    """Entornos de ejecución"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Niveles de logging"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheBackend(str, Enum):
    """Backends de cache"""

    REDIS = "redis"
    MEMORY = "memory"
    DISABLED = "disabled"


class PMSType(str, Enum):
    """Tipos de PMS soportados"""

    QLOAPPS = "qloapps"
    MOCK = "mock"
    OPERA = "opera"
    FIDELIO = "fidelio"


class TTSEngine(str, Enum):
    """Motores de Text-to-Speech"""

    ESPEAK = "espeak"
    COQUI = "coqui"
    AZURE = "azure"
    GOOGLE = "google"


class STTEngine(str, Enum):
    """Motores de Speech-to-Text"""

    WHISPER = "whisper"
    AZURE = "azure"
    GOOGLE = "google"


class AdvancedSettings(BaseModel):
    """Configuración avanzada del sistema de agente hotelero"""

    class Config:
        """Configuración del modelo Pydantic"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        validate_assignment = True

    # === CONFIGURACIÓN BÁSICA ===
    app_name: str = Field(default="Sistema Agente Hotelero IA", description="Nombre de la aplicación")
    version: str = Field(default="1.0.0", description="Versión de la aplicación")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Entorno de ejecución")
    debug: bool = Field(default=False, description="Modo debug")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Nivel de logging")

    # === CONFIGURACIÓN DE SERVIDOR ===
    host: str = Field(default="0.0.0.0", description="Host del servidor")
    port: int = Field(default=8000, description="Puerto del servidor")
    workers: int = Field(default=1, description="Número de workers")
    reload: bool = Field(default=False, description="Auto-reload en desarrollo")

    # === CONFIGURACIÓN DE BASE DE DATOS ===
    postgres_host: str = Field(default="localhost", description="Host de PostgreSQL")
    postgres_port: int = Field(default=5432, description="Puerto de PostgreSQL")
    postgres_db: str = Field(default="agente_hotel", description="Nombre de la base de datos")
    postgres_user: str = Field(default="postgres", description="Usuario de PostgreSQL")
    postgres_password: str = Field(default="", description="Contraseña de PostgreSQL")
    postgres_url: Optional[str] = Field(default=None, description="URL completa de PostgreSQL")

    # Pool de conexiones
    db_pool_size: int = Field(default=10, description="Tamaño del pool de conexiones")
    db_max_overflow: int = Field(default=20, description="Overflow máximo del pool")
    db_pool_pre_ping: bool = Field(default=True, description="Pre-ping para validar conexiones")
    db_pool_recycle: int = Field(default=3600, description="Tiempo de reciclaje de conexiones (segundos)")

    # === CONFIGURACIÓN DE REDIS ===
    redis_host: str = Field(default="localhost", description="Host de Redis")
    redis_port: int = Field(default=6379, description="Puerto de Redis")
    redis_db: int = Field(default=0, description="Número de base de datos Redis")
    redis_password: Optional[str] = Field(default=None, description="Contraseña de Redis")
    redis_url: Optional[str] = Field(default=None, description="URL completa de Redis")
    redis_ssl: bool = Field(default=False, description="Usar SSL para Redis")
    redis_socket_timeout: float = Field(default=5.0, description="Timeout de socket Redis")
    redis_socket_connect_timeout: float = Field(default=5.0, description="Timeout de conexión Redis")

    # Pool de conexiones Redis
    redis_max_connections: int = Field(default=50, description="Máximo de conexiones Redis")
    redis_retry_on_timeout: bool = Field(default=True, description="Reintentar en timeout")

    # === CONFIGURACIÓN DE CACHE ===
    cache_backend: CacheBackend = Field(default=CacheBackend.REDIS, description="Backend de cache")
    cache_default_ttl: int = Field(default=300, description="TTL por defecto del cache (segundos)")
    cache_max_size: int = Field(default=1000, description="Tamaño máximo del cache en memoria")

    # === CONFIGURACIÓN DE PMS ===
    pms_type: PMSType = Field(default=PMSType.MOCK, description="Tipo de PMS")
    pms_api_url: str = Field(default="http://qloapps:80/api", description="URL de la API del PMS")
    pms_api_key: str = Field(default="", description="API Key del PMS")
    pms_api_secret: str = Field(default="", description="API Secret del PMS")
    pms_timeout: float = Field(default=30.0, description="Timeout para llamadas al PMS")
    pms_retries: int = Field(default=3, description="Número de reintentos para PMS")
    pms_circuit_breaker_enabled: bool = Field(default=True, description="Habilitar circuit breaker")
    pms_circuit_breaker_failure_threshold: int = Field(default=5, description="Umbral de fallos del circuit breaker")
    pms_circuit_breaker_recovery_timeout: int = Field(
        default=60, description="Timeout de recuperación del circuit breaker"
    )

    # === CONFIGURACIÓN DE WHATSAPP ===
    whatsapp_access_token: str = Field(default="", description="Token de acceso de WhatsApp")
    whatsapp_verify_token: str = Field(default="", description="Token de verificación de WhatsApp")
    whatsapp_phone_number_id: str = Field(default="", description="ID del número de teléfono WhatsApp")
    whatsapp_business_account_id: str = Field(default="", description="ID de la cuenta de negocio WhatsApp")
    whatsapp_webhook_url: str = Field(default="", description="URL del webhook WhatsApp")
    whatsapp_api_version: str = Field(default="v18.0", description="Versión de la API de WhatsApp")
    whatsapp_max_media_size: int = Field(default=16_000_000, description="Tamaño máximo de media WhatsApp")

    # === CONFIGURACIÓN DE EMAIL ===
    gmail_credentials_path: str = Field(default="", description="Ruta a las credenciales de Gmail")
    gmail_token_path: str = Field(default="", description="Ruta al token de Gmail")
    gmail_scopes: List[str] = Field(
        default=["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
        description="Scopes de Gmail",
    )
    smtp_host: str = Field(default="smtp.gmail.com", description="Host SMTP")
    smtp_port: int = Field(default=587, description="Puerto SMTP")
    smtp_username: str = Field(default="", description="Usuario SMTP")
    smtp_password: str = Field(default="", description="Contraseña SMTP")
    smtp_use_tls: bool = Field(default=True, description="Usar TLS para SMTP")

    # === CONFIGURACIÓN DE AUDIO ===
    tts_engine: TTSEngine = Field(default=TTSEngine.ESPEAK, description="Motor TTS")
    stt_engine: STTEngine = Field(default=STTEngine.WHISPER, description="Motor STT")
    audio_temp_dir: str = Field(default="/tmp/audio", description="Directorio temporal de audio")
    audio_max_duration: int = Field(default=300, description="Duración máxima de audio (segundos)")
    audio_sample_rate: int = Field(default=16000, description="Sample rate de audio")
    audio_channels: int = Field(default=1, description="Número de canales de audio")
    audio_bit_depth: int = Field(default=16, description="Profundidad de bits de audio")

    # OpenAI/Whisper
    openai_api_key: str = Field(default="", description="API Key de OpenAI")
    whisper_model: str = Field(default="base", description="Modelo de Whisper")

    # Azure Speech Services
    azure_speech_key: str = Field(default="", description="API Key de Azure Speech")
    azure_speech_region: str = Field(default="", description="Región de Azure Speech")

    # === CONFIGURACIÓN DE NLP ===
    nlp_model_path: str = Field(default="models/nlp", description="Ruta al modelo NLP")
    nlp_confidence_threshold: float = Field(default=0.7, description="Umbral de confianza NLP")
    nlp_max_tokens: int = Field(default=512, description="Máximo de tokens NLP")
    nlp_cache_enabled: bool = Field(default=True, description="Habilitar cache NLP")
    nlp_cache_ttl: int = Field(default=3600, description="TTL del cache NLP")

    # === CONFIGURACIÓN DE SEGURIDAD ===
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="Clave secreta")
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="Clave secreta JWT")
    jwt_algorithm: str = Field(default="HS256", description="Algoritmo JWT")
    jwt_expiration_hours: int = Field(default=24, description="Expiración JWT en horas")
    encryption_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="Clave de cifrado")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Habilitar rate limiting")
    rate_limit_requests: int = Field(default=120, description="Requests por minuto")
    rate_limit_window: int = Field(default=60, description="Ventana de rate limit (segundos)")

    # CORS
    cors_origins: List[str] = Field(default=["*"], description="Orígenes permitidos CORS")
    cors_credentials: bool = Field(default=True, description="Permitir credenciales CORS")
    cors_methods: List[str] = Field(default=["*"], description="Métodos permitidos CORS")
    cors_headers: List[str] = Field(default=["*"], description="Headers permitidos CORS")

    # === CONFIGURACIÓN DE MONITOREO ===
    monitoring_enabled: bool = Field(default=True, description="Habilitar monitoreo")
    metrics_enabled: bool = Field(default=True, description="Habilitar métricas")
    tracing_enabled: bool = Field(default=True, description="Habilitar tracing")
    tracing_sample_rate: float = Field(default=0.1, description="Tasa de muestreo de tracing")

    # Prometheus
    prometheus_enabled: bool = Field(default=True, description="Habilitar Prometheus")
    prometheus_port: int = Field(default=9090, description="Puerto de Prometheus")
    prometheus_path: str = Field(default="/metrics", description="Path de métricas Prometheus")

    # Logging
    log_format: str = Field(default="json", description="Formato de logging")
    log_file: Optional[str] = Field(default=None, description="Archivo de log")
    log_rotation: str = Field(default="daily", description="Rotación de logs")
    log_retention: int = Field(default=30, description="Retención de logs (días)")

    # === CONFIGURACIÓN DE BUSINESS INTELLIGENCE ===
    bi_enabled: bool = Field(default=True, description="Habilitar Business Intelligence")
    bi_update_interval: int = Field(default=300, description="Intervalo de actualización BI (segundos)")
    bi_data_retention_days: int = Field(default=365, description="Retención de datos BI (días)")
    bi_alert_enabled: bool = Field(default=True, description="Habilitar alertas BI")

    # KPIs del hotel
    hotel_rooms_total: int = Field(default=100, description="Número total de habitaciones")
    hotel_target_occupancy: float = Field(default=85.0, description="Ocupación objetivo (%)")
    hotel_target_adr: float = Field(default=150.0, description="ADR objetivo")
    hotel_target_revpar: float = Field(default=127.5, description="RevPAR objetivo")
    hotel_target_nps: float = Field(default=70.0, description="NPS objetivo")

    # === CONFIGURACIÓN DE ALERTAS ===
    alerting_enabled: bool = Field(default=True, description="Habilitar sistema de alertas")
    alerting_email_enabled: bool = Field(default=True, description="Habilitar alertas por email")
    alerting_sms_enabled: bool = Field(default=False, description="Habilitar alertas por SMS")
    alerting_slack_enabled: bool = Field(default=False, description="Habilitar alertas por Slack")
    alerting_webhook_enabled: bool = Field(default=False, description="Habilitar alertas por webhook")

    # Configuración de notificaciones
    notification_email_from: str = Field(default="", description="Email remitente")
    notification_email_to: List[str] = Field(default=[], description="Emails destinatarios")
    slack_webhook_url: str = Field(default="", description="URL del webhook Slack")
    sms_api_key: str = Field(default="", description="API Key para SMS")
    sms_from_number: str = Field(default="", description="Número de origen SMS")

    # === CONFIGURACIÓN DE PERFORMANCE ===
    performance_monitoring_enabled: bool = Field(default=True, description="Habilitar monitoreo de performance")
    performance_sample_interval: int = Field(default=60, description="Intervalo de muestreo (segundos)")
    performance_history_retention: int = Field(default=7, description="Retención de historial (días)")

    # Umbrales de performance
    api_response_time_threshold: float = Field(default=1000.0, description="Umbral de tiempo de respuesta API (ms)")
    db_query_time_threshold: float = Field(default=500.0, description="Umbral de tiempo de query DB (ms)")
    cpu_usage_threshold: float = Field(default=80.0, description="Umbral de uso de CPU (%)")
    memory_usage_threshold: float = Field(default=85.0, description="Umbral de uso de memoria (%)")
    disk_usage_threshold: float = Field(default=90.0, description="Umbral de uso de disco (%)")

    # === CONFIGURACIÓN DE HEALTH CHECKS ===
    health_check_enabled: bool = Field(default=True, description="Habilitar health checks")
    health_check_interval: int = Field(default=30, description="Intervalo de health checks (segundos)")
    health_check_timeout: int = Field(default=10, description="Timeout de health checks (segundos)")
    health_check_retries: int = Field(default=3, description="Reintentos de health checks")

    # Dependencias críticas
    check_redis_in_readiness: bool = Field(default=True, description="Verificar Redis en readiness")
    check_db_in_readiness: bool = Field(default=True, description="Verificar DB en readiness")
    check_pms_in_readiness: bool = Field(default=False, description="Verificar PMS en readiness")

    # === CONFIGURACIÓN DE DESARROLLO ===
    dev_auto_reload: bool = Field(default=False, description="Auto-reload en desarrollo")
    dev_debug_sql: bool = Field(default=False, description="Debug SQL en desarrollo")
    dev_mock_services: bool = Field(default=False, description="Usar servicios mock en desarrollo")
    dev_skip_auth: bool = Field(default=False, description="Saltar autenticación en desarrollo")

    # === CONFIGURACIÓN DE TESTING ===
    test_database_url: str = Field(default="sqlite:///./test.db", description="URL de DB para tests")
    test_redis_url: str = Field(default="redis://localhost:6379/15", description="URL de Redis para tests")
    test_mock_external_apis: bool = Field(default=True, description="Mockear APIs externas en tests")
    test_timeout: int = Field(default=30, description="Timeout para tests (segundos)")

    # === CONFIGURACIÓN DE DEPLOYMENT ===
    deployment_environment: str = Field(default="local", description="Entorno de deployment")
    deployment_version: str = Field(default="1.0.0", description="Versión de deployment")
    deployment_build_id: str = Field(default="", description="ID de build")
    deployment_commit_sha: str = Field(default="", description="SHA del commit")

    # Container/K8s
    container_name: str = Field(default="agente-hotel-api", description="Nombre del contenedor")
    pod_name: Optional[str] = Field(default=None, description="Nombre del pod K8s")
    namespace: Optional[str] = Field(default=None, description="Namespace K8s")
    node_name: Optional[str] = Field(default=None, description="Nombre del nodo K8s")

    # === VALIDADORES ===
    @validator("postgres_url", pre=True, always=True)
    def assemble_postgres_url(cls, v, values):
        """Construir URL de PostgreSQL si no se proporciona"""
        if v:
            return v

        user = values.get("postgres_user", "postgres")
        password = values.get("postgres_password", "")
        host = values.get("postgres_host", "localhost")
        port = values.get("postgres_port", 5432)
        db = values.get("postgres_db", "agente_hotel")

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        else:
            return f"postgresql://{user}@{host}:{port}/{db}"

    @validator("redis_url", pre=True, always=True)
    def assemble_redis_url(cls, v, values):
        """Construir URL de Redis si no se proporciona"""
        if v:
            return v

        host = values.get("redis_host", "localhost")
        port = values.get("redis_port", 6379)
        db = values.get("redis_db", 0)
        password = values.get("redis_password")
        ssl = values.get("redis_ssl", False)

        scheme = "rediss" if ssl else "redis"

        if password:
            return f"{scheme}://:{password}@{host}:{port}/{db}"
        else:
            return f"{scheme}://{host}:{port}/{db}"

    @validator("debug")
    def validate_debug_environment(cls, v, values):
        """Validar que debug solo esté habilitado en desarrollo"""
        env = values.get("environment", Environment.DEVELOPMENT)
        if v and env == Environment.PRODUCTION:
            raise ValueError("Debug mode cannot be enabled in production")
        return v

    @validator("jwt_secret_key", "encryption_key", "secret_key")
    def validate_production_secrets(cls, v, values):
        """Validar que las claves no sean por defecto en producción"""
        env = values.get("environment", Environment.DEVELOPMENT)
        if env == Environment.PRODUCTION and len(v) < 32:
            raise ValueError("Production secrets must be at least 32 characters long")
        return v

    @validator("cors_origins")
    def validate_cors_origins(cls, v, values):
        """Validar orígenes CORS en producción"""
        env = values.get("environment", Environment.DEVELOPMENT)
        if env == Environment.PRODUCTION and "*" in v:
            raise ValueError("Wildcard CORS origins not allowed in production")
        return v

    # === MÉTODOS HELPER ===
    def is_production(self) -> bool:
        """Verificar si está en producción"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Verificar si está en desarrollo"""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Verificar si está en testing"""
        return self.environment == Environment.TEST

    def get_database_url(self, async_driver: bool = True) -> str:
        """Obtener URL de base de datos"""
        if self.is_testing():
            return self.test_database_url

        url = self.postgres_url or ""
        if async_driver and url and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url or ""

    def get_redis_url(self) -> str:
        """Obtener URL de Redis"""
        if self.is_testing():
            return self.test_redis_url
        return self.redis_url or ""

    def get_log_config(self) -> Dict[str, Any]:
        """Obtener configuración de logging"""
        return {
            "level": self.log_level,
            "format": self.log_format,
            "file": self.log_file,
            "rotation": self.log_rotation,
            "retention": self.log_retention,
        }

    def get_cors_config(self) -> Dict[str, Any]:
        """Obtener configuración CORS"""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_credentials,
            "allow_methods": self.cors_methods,
            "allow_headers": self.cors_headers,
        }

    def get_security_config(self) -> Dict[str, Any]:
        """Obtener configuración de seguridad"""
        return {
            "secret_key": self.secret_key,
            "jwt_secret_key": self.jwt_secret_key,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_expiration_hours": self.jwt_expiration_hours,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window": self.rate_limit_window,
        }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Obtener configuración de monitoreo"""
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "metrics_enabled": self.metrics_enabled,
            "tracing_enabled": self.tracing_enabled,
            "tracing_sample_rate": self.tracing_sample_rate,
            "prometheus_enabled": self.prometheus_enabled,
            "prometheus_port": self.prometheus_port,
        }

    class ConfigModel:
        """Configuración del modelo Pydantic"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        validate_assignment = True


# Crear instancia global de configuración
try:
    settings = AdvancedSettings()
except Exception as e:
    # Configuración mínima de fallback
    print(f"Warning: Could not load advanced settings: {e}")
    # Crear configuración básica como fallback
    settings = AdvancedSettings()


def get_advanced_settings() -> AdvancedSettings:
    """Obtener configuración avanzada"""
    return settings
