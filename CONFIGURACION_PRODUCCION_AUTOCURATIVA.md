# CONFIGURACIONES DE PRODUCCIÓN AUTOCURATIVAS - SIST_AGENTICO_HOTELERO

## .env.prod.template COMPLETO Y COMENTADO

```bash
# ============================================================================
# AGENTE HOTELERO - PRODUCTION ENVIRONMENT (AUTO-HEALING)
# ============================================================================
# CRITICAL: Replace ALL values before deployment!
# Validation: All required vars checked at runtime

# ==============================================================================
# Application Core - REQUIRED
# ==============================================================================
# Generate: openssl rand -hex 32
SECRET_KEY=                             # REQUIRED - 64 char hex string
ENVIRONMENT=production                  # REQUIRED - triggers prod validations
DEBUG=false                            # REQUIRED - NEVER true in production
APP_NAME=Agente Hotel API              # Display name
VERSION=0.1.0                          # App version

# ==============================================================================
# Database Configuration - REQUIRED  
# ==============================================================================
# PostgreSQL (Agent metadata, sessions, locks)
POSTGRES_HOST=postgres                 # Container name or IP
POSTGRES_PORT=5432                     # Default PostgreSQL port
POSTGRES_DB=agente_hotel              # Database name
POSTGRES_USER=agente_user             # Database user
POSTGRES_PASSWORD=                     # REQUIRED - Strong password (16+ chars)
POSTGRES_URL=postgresql+asyncpg://agente_user:${POSTGRES_PASSWORD}@postgres:5432/agente_hotel
POSTGRES_POOL_SIZE=10                 # Connection pool size
POSTGRES_MAX_OVERFLOW=10              # Pool overflow limit

# MySQL (QloApps PMS database)
MYSQL_DATABASE=qloapps                # QloApps database name
MYSQL_USER=qloapps                    # QloApps database user  
MYSQL_PASSWORD=                       # REQUIRED - Strong password (16+ chars)
MYSQL_ROOT_PASSWORD=                  # REQUIRED - MySQL root password

# Redis (Cache, distributed locks, rate limiting)
REDIS_PASSWORD=                       # REQUIRED - Redis password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_POOL_SIZE=20                    # Redis connection pool

# ==============================================================================
# External APIs - REQUIRED
# ==============================================================================
# QloApps PMS Integration
PMS_TYPE=qloapps                      # PMS type identifier
PMS_BASE_URL=http://qloapps:80        # PMS API base URL
PMS_API_KEY=                          # REQUIRED - QloApps API key
PMS_TIMEOUT=30                        # API timeout seconds

# WhatsApp Business API (Meta Cloud)
WHATSAPP_ACCESS_TOKEN=                # REQUIRED - Meta access token
WHATSAPP_PHONE_NUMBER_ID=             # REQUIRED - Phone number ID
WHATSAPP_VERIFY_TOKEN=                # REQUIRED - Webhook verify token
WHATSAPP_APP_SECRET=                  # REQUIRED - App secret for validation

# Gmail Integration
GMAIL_USERNAME=reception@hotel.com    # Gmail account for notifications
GMAIL_APP_PASSWORD=                   # REQUIRED - Gmail app password (NOT regular password)

# ==============================================================================
# Security & Performance - AUTO-HEALING CONFIGS
# ==============================================================================
# JWT Configuration
JWT_ALGORITHM=HS256                   # JWT signing algorithm
JWT_EXPIRATION_MINUTES=60             # JWT token expiration

# Security Headers
CSP_EXTRA_SOURCES=https://fonts.googleapis.com https://fonts.gstatic.com
COOP_ENABLED=true                     # Cross-Origin-Opener-Policy
COEP_ENABLED=true                     # Cross-Origin-Embedder-Policy

# Rate Limiting (Auto-healing against abuse)
RATE_LIMIT_ENABLED=true               # Enable rate limiting
RATE_LIMIT_REQUESTS=60                # Requests per minute per IP
RATE_LIMIT_WINDOW=60                  # Rate limit window in seconds

# Circuit Breaker (Auto-healing for external APIs)
CIRCUIT_BREAKER_ENABLED=true          # Enable circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5   # Failures before opening
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60   # Seconds before retry
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3 # Max calls in half-open state

# ==============================================================================
# AI/ML Configuration - FAULT TOLERANT
# ==============================================================================
# Audio Processing
AUDIO_ENABLED=true                    # Enable audio processing
TTS_ENGINE=espeak                     # Text-to-speech engine (espeak|coqui)
AUDIO_MAX_FILE_SIZE=10485760         # Max audio file size (10MB)
AUDIO_TIMEOUT=60                      # Audio processing timeout

# NLP Configuration  
NLP_LANGUAGE=es                       # Spanish language processing
NLP_CONFIDENCE_THRESHOLD=0.7          # Minimum confidence for intent recognition
NLP_FALLBACK_ENABLED=true            # Enable fallback responses
NLP_TIMEOUT=10                        # NLP processing timeout

# Rasa Integration (Optional - can be disabled)
RASA_ENABLED=false                    # Enable/disable Rasa NLU
RASA_SERVER_URL=http://rasa:5005     # Rasa server URL
RASA_MODEL_PATH=/app/models/nlu.tar.gz # Rasa model path
RASA_CONFIDENCE_THRESHOLD=0.7         # Rasa confidence threshold

# ==============================================================================
# Monitoring & Observability - SELF-HEALING
# ==============================================================================
# Logging
LOG_LEVEL=INFO                        # Logging level (DEBUG|INFO|WARNING|ERROR)
LOG_FORMAT=json                       # Log format (json|text)
LOG_FILE=/var/log/agente/app.log     # Log file path (optional)

# Health Checks
CHECK_PMS_IN_READINESS=true          # Include PMS health in readiness check
HEALTH_CHECK_TIMEOUT=5               # Health check timeout seconds
HEALTH_CHECK_INTERVAL=30             # Health check interval seconds

# Metrics & Monitoring
PROMETHEUS_ENABLED=true              # Enable Prometheus metrics
PROMETHEUS_PORT=9090                 # Prometheus server port
GRAFANA_ADMIN_PASSWORD=              # REQUIRED - Grafana admin password

# ==============================================================================
# Alerting Configuration - AUTO-RECOVERY
# ==============================================================================
# Slack Alerts (Optional)
SLACK_WEBHOOK_URL=                   # Slack webhook for alerts
SLACK_CHANNEL=#agente-hotel-alerts   # Slack channel for notifications

# Email Alerts
ALERT_EMAIL_ENABLED=true             # Enable email alerting
ALERT_EMAIL_TO=ops@hotel.com         # Alert recipient email
ALERT_EMAIL_FROM=alerts@hotel.com    # Alert sender email

# SMTP Configuration
SMTP_HOST=smtp.hotel.com             # SMTP server host
SMTP_PORT=587                        # SMTP server port
SMTP_USER=alerts@hotel.com           # SMTP username
SMTP_PASSWORD=                       # REQUIRED - SMTP password
SMTP_TLS=true                        # Enable SMTP TLS

# ==============================================================================
# SSL/TLS & Domain Configuration
# ==============================================================================
DOMAIN=agente.hotel.com              # Production domain
EMAIL_FOR_CERTBOT=admin@hotel.com    # Email for SSL certificate
SSL_ENABLED=true                     # Enable SSL/HTTPS

# ==============================================================================
# Resource Limits - PREVENT RESOURCE EXHAUSTION  
# ==============================================================================
# Application Limits
MAX_WORKERS=4                        # Uvicorn worker processes
MAX_CONNECTIONS=1000                 # Max concurrent connections
REQUEST_TIMEOUT=30                   # Request timeout seconds
WORKER_TIMEOUT=120                   # Worker timeout seconds

# Memory Management
MAX_MEMORY_MB=1024                   # Max memory usage per worker
MEMORY_CHECK_INTERVAL=60             # Memory check interval seconds
MEMORY_CLEANUP_THRESHOLD=80          # Memory cleanup threshold (%)

# File Upload Limits
MAX_UPLOAD_SIZE=10485760             # Max file upload size (10MB)
UPLOAD_TIMEOUT=300                   # File upload timeout seconds

# ==============================================================================
# Auto-Healing Thresholds - SELF-RECOVERY
# ==============================================================================
# Service Health Thresholds
ERROR_RATE_THRESHOLD=0.05            # 5% error rate triggers alert
RESPONSE_TIME_THRESHOLD=2000         # 2s response time threshold (ms)
MEMORY_USAGE_THRESHOLD=85            # 85% memory usage triggers cleanup
CPU_USAGE_THRESHOLD=80               # 80% CPU usage triggers alert

# Auto-restart Conditions
AUTO_RESTART_ENABLED=true            # Enable automatic service restart
MAX_RESTART_ATTEMPTS=3               # Max restart attempts before giving up
RESTART_COOLDOWN=300                 # Cooldown between restart attempts (seconds)
RESTART_ON_MEMORY_LEAK=true          # Restart if memory leak detected

# ==============================================================================
# VALIDATION CHECKLIST - DEPLOYMENT READINESS
# ==============================================================================
# Before deploying, ensure:
# [ ] All REQUIRED variables are set (no empty values)
# [ ] All passwords are strong (16+ characters, mixed case, numbers, symbols)
# [ ] WhatsApp webhook is verified and tokens are valid
# [ ] Gmail app password is generated (not regular password)  
# [ ] PMS API connectivity is tested and authenticated
# [ ] SSL certificates are configured for DOMAIN
# [ ] SMTP settings are tested for alert delivery
# [ ] Backup procedures are configured and tested
# [ ] Monitoring dashboards are accessible
# [ ] Resource limits are appropriate for server capacity
```

## SNIPPET DE VALIDACIÓN RUNTIME

### Python Runtime Validation

```python
# app/core/validation.py - Runtime environment validation

import os
import sys
import re
from typing import List, Dict, Any
from app.core.logging import logger

class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass

def validate_production_config() -> None:
    """
    Validates all required configuration for production deployment.
    Raises ConfigurationError if any critical config is missing or invalid.
    """
    errors: List[str] = []
    
    # Critical secrets that must be set
    REQUIRED_SECRETS = [
        "SECRET_KEY",
        "POSTGRES_PASSWORD", 
        "MYSQL_PASSWORD",
        "MYSQL_ROOT_PASSWORD",
        "REDIS_PASSWORD",
        "PMS_API_KEY",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_VERIFY_TOKEN", 
        "WHATSAPP_APP_SECRET",
        "GMAIL_APP_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD"
    ]
    
    # Check for missing required variables
    missing = [key for key in REQUIRED_SECRETS if not os.getenv(key)]
    if missing:
        errors.append(f"Missing required environment variables: {', '.join(missing)}")
    
    # Validate SECRET_KEY format (64 char hex)
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key and not re.match(r'^[a-fA-F0-9]{64}$', secret_key):
        errors.append("SECRET_KEY must be 64 character hexadecimal string")
    
    # Validate password strength
    for key in ["POSTGRES_PASSWORD", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "REDIS_PASSWORD"]:
        password = os.getenv(key, "")
        if password and len(password) < 16:
            errors.append(f"{key} must be at least 16 characters long")
    
    # Validate environment setting
    environment = os.getenv("ENVIRONMENT", "")
    if environment != "production":
        logger.warning("ENVIRONMENT not set to 'production', some validations may be skipped")
    
    # Validate debug setting
    debug = os.getenv("DEBUG", "").lower()
    if debug == "true" and environment == "production":
        errors.append("DEBUG must be 'false' in production environment")
    
    # Validate database URLs
    postgres_url = os.getenv("POSTGRES_URL", "")
    if postgres_url and "postgres:postgres@" in postgres_url:
        errors.append("POSTGRES_URL contains default/weak credentials")
    
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url and redis_url == "redis://localhost:6379/0":
        errors.append("REDIS_URL is using default configuration without password")
    
    # Validate numeric configurations
    numeric_configs = {
        "POSTGRES_POOL_SIZE": (1, 50),
        "REDIS_POOL_SIZE": (1, 100), 
        "PMS_TIMEOUT": (5, 300),
        "JWT_EXPIRATION_MINUTES": (5, 1440),
        "MAX_WORKERS": (1, 16)
    }
    
    for key, (min_val, max_val) in numeric_configs.items():
        value = os.getenv(key)
        if value:
            try:
                num_value = int(value)
                if not (min_val <= num_value <= max_val):
                    errors.append(f"{key} must be between {min_val} and {max_val}")
            except ValueError:
                errors.append(f"{key} must be a valid integer")
    
    # If any errors found, raise exception
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        logger.error("Configuration validation failed", errors=errors)
        raise ConfigurationError(error_msg)
    
    logger.info("Production configuration validation passed")

# Integration with FastAPI startup
async def startup_validation():
    """Run all validations on application startup"""
    try:
        validate_production_config()
        
        logger.info("Application startup validation completed")
        
    except ConfigurationError as e:
        logger.error("Startup validation failed", error=str(e))
        sys.exit(1)
```