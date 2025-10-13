"""
Constantes del sistema para el agente hotelero.

Este módulo centraliza todos los valores constantes utilizados en el sistema,
incluyendo thresholds de confianza, timeouts, TTLs de cache, y valores por defecto.

Categorías:
    - NLP & Confidence: Thresholds para clasificación de intents
    - Circuit Breaker: Configuración de circuit breakers
    - Cache & TTL: Tiempos de vida de cache en Redis
    - Business Logic: Horarios, precios, y datos de negocio
    - Timeouts & Retries: Configuración de timeouts y reintentos
"""

# ============================================================
# NLP & CONFIDENCE THRESHOLDS
# ============================================================

# Confidence thresholds para clasificación de intents
CONFIDENCE_THRESHOLD_VERY_LOW = 0.45  # Escalado inmediato
CONFIDENCE_THRESHOLD_LOW = 0.75  # Sugerencias contextuales
CONFIDENCE_THRESHOLD_HIGH = 0.85  # Confianza alta
CONFIDENCE_THRESHOLD_VERY_HIGH = 0.90  # Confianza muy alta

# ============================================================
# CIRCUIT BREAKER CONFIGURATION
# ============================================================

# PMS Adapter circuit breaker
PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # Fallos antes de abrir
PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30  # Segundos en estado OPEN

# NLP Engine circuit breaker
NLP_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
NLP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60  # Segundos

# Audio Processor circuit breaker
AUDIO_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
AUDIO_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 45  # Segundos

# ============================================================
# CACHE TTL (Time To Live) - En segundos
# ============================================================

# PMS data caching
CACHE_TTL_AVAILABILITY = 300  # 5 minutos - disponibilidad de habitaciones
CACHE_TTL_ROOM_TYPES = 3600  # 1 hora - tipos de habitaciones
CACHE_TTL_GUEST_DATA = 1800  # 30 minutos - datos de huéspedes

# Audio processing caching
CACHE_TTL_AUDIO_TRANSCRIPTION = 3600  # 1 hora - transcripciones de audio
CACHE_TTL_AUDIO_SYNTHESIS = 1800  # 30 minutos - audio sintetizado
CACHE_TTL_AUDIO_DEFAULT = 3600  # 1 hora - cache general de audio

# Session caching
CACHE_TTL_SESSION = 86400  # 24 horas - sesiones de usuario

# ============================================================
# BUSINESS LOGIC CONSTANTS
# ============================================================

# Horarios del hotel
HOTEL_STANDARD_CHECKOUT_TIME = "12:00"  # Check-out estándar
HOTEL_LATE_CHECKOUT_TIME = "14:00"  # Late check-out default
HOTEL_EARLY_CHECKIN_TIME = "10:00"  # Early check-in

# Precios de ejemplo (en producción vienen del PMS)
PRICE_ROOM_SINGLE = 8000
PRICE_ROOM_DOUBLE = 12000
PRICE_ROOM_PREMIUM_SINGLE = 15000
PRICE_ROOM_PREMIUM_DOUBLE = 20000

# Depósito de reserva (en producción viene del PMS)
RESERVATION_DEPOSIT_AMOUNT = 6000

# Capacidad de habitaciones
ROOM_CAPACITY_SINGLE = 1
ROOM_CAPACITY_DOUBLE = 2
ROOM_CAPACITY_SUITE = 4

# ============================================================
# TIMEOUTS & RETRIES
# ============================================================

# HTTP request timeouts (en segundos)
HTTP_TIMEOUT_DEFAULT = 30.0
HTTP_TIMEOUT_PMS = 45.0
HTTP_TIMEOUT_NLP = 60.0
HTTP_TIMEOUT_AUDIO = 30.0

# Cleanup timeouts
CLEANUP_TIMEOUT = 5.0  # Timeout para operaciones de limpieza

# Background task sleep intervals (en segundos)
CLEANUP_INTERVAL = 60  # Limpieza cada minuto
MONITORING_INTERVAL = 30  # Monitoreo cada 30 segundos
HEALTH_CHECK_INTERVAL = 15  # Health check cada 15 segundos
SESSION_CLEANUP_INTERVAL = 600  # Limpieza de sesiones cada 10 minutos

# Retry configuration
MAX_RETRIES_DEFAULT = 3
MAX_RETRIES_PMS = 5
RETRY_DELAY_BASE = 1  # Delay base en segundos para exponential backoff

# ============================================================
# SESSION & ESCALATION
# ============================================================

# TTL de sesiones
SESSION_TTL_DEFAULT = 1800  # 30 minutos de inactividad

# Límites de mensajes en historial
MAX_ESCALATION_HISTORY_ITEMS = 5  # Máximo de mensajes en historial de escalado
MAX_SESSION_MESSAGES = 50  # Máximo de mensajes en sesión antes de limpiar

# Tiempos de espera para escalación
ESCALATION_TIMEOUT_MINUTES = 10  # Minutos antes de escalar por timeout
URGENT_RESPONSE_TIMEOUT_MINUTES = 5  # Minutos para respuestas urgentes

# ============================================================
# RATE LIMITING
# ============================================================

# Rate limits por endpoint (requests por minuto)
RATE_LIMIT_WEBHOOK = "120/minute"
RATE_LIMIT_API_DEFAULT = "60/minute"
RATE_LIMIT_ADMIN = "30/minute"

# Rate limit burst
RATE_LIMIT_BURST_MULTIPLIER = 1.5  # Permite 1.5x el rate limit en burst

# ============================================================
# PAGINATION
# ============================================================

# Paginación de resultados
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# ============================================================
# VALIDATION LIMITS
# ============================================================

# Límites de tamaño de mensaje
MAX_MESSAGE_LENGTH = 4096  # Caracteres
MAX_AUDIO_SIZE_MB = 16  # Megabytes
MAX_IMAGE_SIZE_MB = 5  # Megabytes

# Límites de nombres
MAX_GUEST_NAME_LENGTH = 100
MAX_ROOM_TYPE_NAME_LENGTH = 50

# ============================================================
# FEATURE FLAGS DEFAULTS
# ============================================================

# Feature flags por defecto (pueden ser sobrescritos por Redis)
DEFAULT_FEATURE_FLAGS = {
    "nlp.fallback.enhanced": True,
    "features.interactive_messages": True,
    "features.audio_responses": True,
    "features.room_images": True,
    "tenancy.dynamic.enabled": True,
    "monitoring.detailed_metrics": True,
}

# ============================================================
# MONITORING & METRICS
# ============================================================

# Intervalos de reporte de métricas (en segundos)
METRICS_REPORT_INTERVAL = 60  # Reportar métricas cada minuto
METRICS_AGGREGATION_WINDOW = 300  # Ventana de agregación de 5 minutos

# Thresholds de alertas
ALERT_THRESHOLD_ERROR_RATE = 0.05  # 5% de error rate
ALERT_THRESHOLD_LATENCY_P95 = 2.0  # 2 segundos P95 latency
ALERT_THRESHOLD_CIRCUIT_BREAKER_OPEN_TIME = 300  # 5 minutos con circuit breaker abierto

# ============================================================
# MOCK DATA (Para desarrollo y testing)
# ============================================================

# Fechas de ejemplo para mock data
MOCK_CHECKIN_DATE = "2025-10-15"
MOCK_CHECKOUT_DATE = "2025-10-17"
MOCK_ROOM_NUMBER = "205"

# ID de ejemplo para mock data
MOCK_BOOKING_ID_PREFIX = "HTL"
MOCK_GUEST_ID_DEFAULT = "+34612345678"

# Información bancaria de ejemplo (NO USAR EN PRODUCCIÓN)
MOCK_BANK_INFO = "CBU 12345..."  # Placeholder para desarrollo

# ============================================================
# LANGUAGE & LOCALIZATION
# ============================================================

# Idiomas soportados
SUPPORTED_LANGUAGES = ["es", "en", "pt"]
DEFAULT_LANGUAGE = "es"

# Códigos de país
COUNTRY_CODE_ARGENTINA = "+54"
COUNTRY_CODE_SPAIN = "+34"
COUNTRY_CODE_MEXICO = "+52"

# ============================================================
# FILE PATHS & DIRECTORIES
# ============================================================

# Directorios para archivos generados
QR_CODE_DIRECTORY = "qr_codes"
AUDIO_CACHE_DIRECTORY = "audio_cache"
TEMP_FILES_DIRECTORY = "temp"

# Extensiones de archivo permitidas
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]
ALLOWED_AUDIO_EXTENSIONS = [".mp3", ".ogg", ".wav", ".m4a"]

# ============================================================
# DATETIME FORMATS
# ============================================================

# Formatos de fecha y hora
DATE_FORMAT_ISO = "%Y-%m-%d"
DATE_FORMAT_DISPLAY = "%d/%m/%Y"
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%SZ"
TIME_FORMAT_24H = "%H:%M"
TIME_FORMAT_12H = "%I:%M %p"

# ============================================================
# VALIDATION PATTERNS
# ============================================================

# Regex patterns (definir como strings para uso con re.compile)
PATTERN_EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PATTERN_PHONE_INTERNATIONAL = r"^\+[1-9]\d{1,14}$"
PATTERN_BOOKING_ID = r"^[A-Z]{3}-\d{6,}$"

# ============================================================
# ERROR MESSAGES
# ============================================================

# Mensajes de error comunes (pueden ser sobrescritos por templates)
ERROR_MESSAGE_GENERIC = "Lo siento, ha ocurrido un error. Por favor, intenta de nuevo."
ERROR_MESSAGE_TIMEOUT = "La operación ha tardado demasiado. Por favor, intenta de nuevo."
ERROR_MESSAGE_NOT_FOUND = "No se encontró la información solicitada."
ERROR_MESSAGE_INVALID_INPUT = "La información proporcionada no es válida."

# ============================================================
# UNICODE EMOJIS (Para respuestas interactivas)
# ============================================================

EMOJI_CHECK = "✅"
EMOJI_CROSS = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_CLOCK = "🕐"
EMOJI_CALENDAR = "📅"
EMOJI_BED = "🛏️"
EMOJI_KEY = "🔑"
EMOJI_QR = "🎫"
EMOJI_PAYMENT = "💳"
EMOJI_LOCATION = "📍"
