# PROMPT 3: CONFIGURACIONES DE PRODUCCIÓN ESPECÍFICAS

## 1. VARIABLES DE ENTORNO COMPLETAS

### Lista Exhaustiva de Variables de Entorno
```bash
# ============================================================================
# AGENTE HOTELERO - PRODUCTION ENVIRONMENT CONFIGURATION
# ============================================================================

# ==============================================================================
# Application Core Settings
# ==============================================================================
SECRET_KEY=                    # REQUIRED: JWT secret (openssl rand -hex 32)
ENVIRONMENT=production         # REQUIRED: development|production
DEBUG=false                   # REQUIRED: true|false for production
APP_NAME=Agente Hotel API     # Application display name
VERSION=1.0.0                 # Application version for tracking

# ==============================================================================
# Database Configuration (PostgreSQL - Agent Data)
# ==============================================================================
POSTGRES_DB=agente_hotel       # Database name for agent data
POSTGRES_USER=agente_user      # Database username
POSTGRES_PASSWORD=             # REQUIRED: Strong password (16+ chars)
POSTGRES_URL=                  # REQUIRED: Full connection string
POSTGRES_POOL_SIZE=10          # Connection pool size
POSTGRES_MAX_OVERFLOW=10       # Max overflow connections

# ==============================================================================
# MySQL Configuration (QloApps PMS Database)
# ==============================================================================
MYSQL_DATABASE=qloapps         # QloApps database name
MYSQL_USER=qloapps            # QloApps database user
MYSQL_PASSWORD=               # REQUIRED: Strong password for MySQL user
MYSQL_ROOT_PASSWORD=          # REQUIRED: Strong password for MySQL root

# ==============================================================================
# Redis Configuration (Cache & Locks)
# ==============================================================================
REDIS_PASSWORD=               # REQUIRED: Strong password for Redis
REDIS_URL=                    # REQUIRED: Full Redis connection string
REDIS_POOL_SIZE=20           # Redis connection pool size

# ==============================================================================
# PMS Integration (QloApps)
# ==============================================================================
PMS_TYPE=qloapps             # PMS type: qloapps|mock
PMS_BASE_URL=http://qloapps:80  # Base URL for PMS API
PMS_API_KEY=                 # REQUIRED: QloApps API key
PMS_TIMEOUT=30               # API timeout in seconds

# ==============================================================================
# WhatsApp Business API (Meta Cloud API)
# ==============================================================================
WHATSAPP_ACCESS_TOKEN=        # REQUIRED: Meta Cloud API access token
WHATSAPP_PHONE_NUMBER_ID=     # REQUIRED: Phone number ID from Meta
WHATSAPP_VERIFY_TOKEN=        # REQUIRED: Webhook verification token
WHATSAPP_APP_SECRET=          # REQUIRED: App secret for signature verification

# ==============================================================================
# Gmail Integration
# ==============================================================================
GMAIL_USERNAME=               # REQUIRED: Gmail account for notifications
GMAIL_APP_PASSWORD=           # REQUIRED: Gmail app password (not regular password)

# ==============================================================================
# Audio & NLP Configuration
# ==============================================================================
AUDIO_ENABLED=true           # Enable audio processing features
TTS_ENGINE=espeak           # Text-to-speech engine: espeak|coqui
LOG_LEVEL=INFO              # Logging level: DEBUG|INFO|WARNING|ERROR

# ==============================================================================
# Security Headers Configuration
# ==============================================================================
CSP_EXTRA_SOURCES=          # Space-separated additional CSP sources
COOP_ENABLED=true          # Cross-Origin-Opener-Policy enabled
COEP_ENABLED=true          # Cross-Origin-Embedder-Policy enabled

# ==============================================================================
# JWT Authentication
# ==============================================================================
JWT_ALGORITHM=HS256         # JWT signing algorithm
JWT_EXPIRATION_MINUTES=60   # JWT token expiration time

# ==============================================================================
# Operational Settings
# ==============================================================================
CHECK_PMS_IN_READINESS=true # Enable PMS connectivity in health checks

# ==============================================================================
# Monitoring & Observability
# ==============================================================================
GRAFANA_ADMIN_PASSWORD=      # REQUIRED: Grafana admin password

# ==============================================================================
# Alerting Configuration
# ==============================================================================
SLACK_WEBHOOK_URL=           # Slack webhook URL for alerts (optional)
SLACK_CHANNEL=#agente-alerts # Slack channel for alerts
ALERT_EMAIL_TO=              # Email for alert notifications
ALERT_EMAIL_FROM=            # From email for alerts
SMTP_HOST=                   # SMTP server for email alerts
SMTP_PORT=587               # SMTP port
SMTP_USER=                  # SMTP username
SMTP_PASSWORD=              # SMTP password

# ==============================================================================
# SSL/TLS Configuration
# ==============================================================================
DOMAIN=                     # Production domain name
EMAIL_FOR_CERTBOT=          # Email for SSL certificate registration

# ==============================================================================
# Performance Tuning
# ==============================================================================
UVICORN_WORKERS=4           # Number of Uvicorn workers
UVICORN_MAX_REQUESTS=1000   # Max requests per worker before restart
UVICORN_TIMEOUT_KEEP_ALIVE=5 # Keep-alive timeout
```

### Descripción de Cada Variable y su Propósito

#### Application Core
- **SECRET_KEY**: Clave secreta para JWT y encriptación. Debe ser de 32 caracteres hexadecimales.
- **ENVIRONMENT**: Define el entorno de ejecución. Controla validaciones de seguridad.
- **DEBUG**: Habilita/deshabilita modo debug. SIEMPRE false en producción.

#### Databases
- **POSTGRES_***: Configuración para la base de datos principal del agente (sessiones, locks, metadata).
- **MYSQL_***: Configuración para QloApps PMS database (reservas, huéspedes, habitaciones).
- **REDIS_***: Configuración para cache, distributed locks, y rate limiting.

#### External APIs
- **WHATSAPP_***: Integración con Meta WhatsApp Business API para comunicación con huéspedes.
- **GMAIL_***: Integración SMTP para notificaciones por email.
- **PMS_***: Configuración del Property Management System (QloApps).

#### Security & Performance
- **JWT_***: Configuración de autenticación JWT para admin endpoints.
- **CSP_***: Content Security Policy para headers de seguridad.
- **UVICORN_***: Configuración del servidor web para optimizar performance.

### Valores de Ejemplo Seguros (sin exponer secretos)
```bash
# .env.production.example
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
ENVIRONMENT=production
DEBUG=false

POSTGRES_PASSWORD=MySecurePostgresPassword2024!
MYSQL_PASSWORD=MySecureMySQLPassword2024!
REDIS_PASSWORD=MySecureRedisPassword2024!

WHATSAPP_VERIFY_TOKEN=MySecureWebhookToken2024
GMAIL_USERNAME=recepcion@mihotel.com.ar
PMS_API_KEY=qloapps_production_api_key_2024

DOMAIN=agente.mihotel.com.ar
EMAIL_FOR_CERTBOT=admin@mihotel.com.ar
```

### Variables Específicas por Entorno

#### Development Environment
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
CHECK_PMS_IN_READINESS=false
PMS_TYPE=mock
UVICORN_WORKERS=1
```

#### Staging Environment
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
CHECK_PMS_IN_READINESS=true
PMS_TYPE=qloapps
UVICORN_WORKERS=2
```

#### Production Environment
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
CHECK_PMS_IN_READINESS=true
PMS_TYPE=qloapps
UVICORN_WORKERS=4
```

### Template de .env.production
```bash
# Copy this template to .env.production and fill in real values
# cp .env.production.example .env.production

# CRITICAL: Replace ALL placeholder values before deployment!

SECRET_KEY=GENERATE_WITH_openssl_rand_hex_32
ENVIRONMENT=production
DEBUG=false

POSTGRES_PASSWORD=YOUR_SECURE_POSTGRES_PASSWORD_HERE
MYSQL_PASSWORD=YOUR_SECURE_MYSQL_PASSWORD_HERE
REDIS_PASSWORD=YOUR_SECURE_REDIS_PASSWORD_HERE

WHATSAPP_ACCESS_TOKEN=YOUR_META_WHATSAPP_TOKEN_HERE
WHATSAPP_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID_HERE
WHATSAPP_VERIFY_TOKEN=YOUR_WEBHOOK_VERIFY_TOKEN_HERE
WHATSAPP_APP_SECRET=YOUR_WHATSAPP_APP_SECRET_HERE

GMAIL_USERNAME=your-hotel-email@domain.com
GMAIL_APP_PASSWORD=YOUR_GMAIL_APP_PASSWORD_HERE

PMS_API_KEY=YOUR_QLOAPPS_API_KEY_HERE

GRAFANA_ADMIN_PASSWORD=YOUR_GRAFANA_ADMIN_PASSWORD_HERE

DOMAIN=your-domain.com
EMAIL_FOR_CERTBOT=admin@your-domain.com
```

## 2. CONFIGURACIÓN DE BASE DE DATOS

### Connection Strings para Producción
```python
# PostgreSQL (Agent Database)
POSTGRES_URL = "postgresql+asyncpg://agente_user:secure_password@postgres:5432/agente_hotel"

# MySQL (QloApps PMS Database)  
MYSQL_URL = "mysql+pymysql://qloapps:secure_password@mysql:3306/qloapps"

# Redis (Cache & Locks)
REDIS_URL = "redis://:secure_password@redis:6379/0"
```

### Configuración de Connection Pooling
```python
# app/core/database.py - Production Settings
DATABASE_CONFIG = {
    "pool_size": 10,           # Base connection pool size
    "max_overflow": 10,        # Additional connections when pool exhausted
    "pool_timeout": 30,        # Seconds to wait for connection
    "pool_recycle": 3600,      # Seconds before connection recycled
    "pool_pre_ping": True,     # Validate connections before use
}

REDIS_CONFIG = {
    "pool_size": 20,           # Redis connection pool size
    "retry_on_timeout": True,   # Retry on timeout
    "socket_connect_timeout": 5, # Connection timeout
    "socket_timeout": 5,        # Socket timeout
}
```

### Migrations Necesarias para Producción
```sql
-- PostgreSQL initialization for agent database
CREATE DATABASE agente_hotel;
CREATE USER agente_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE agente_hotel TO agente_user;

-- Create required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create tables (via SQLAlchemy alembic)
-- Run: alembic upgrade head
```

```sql
-- MySQL initialization for QloApps
CREATE DATABASE qloapps CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'qloapps'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON qloapps.* TO 'qloapps'@'%';
FLUSH PRIVILEGES;
```

### Seeds o Data Inicial Requerida
```python
# scripts/seed_production.py
import asyncio
from app.core.database import get_db
from app.models import FeatureFlag, SystemConfig

async def seed_production_data():
    """Seed essential production data"""
    
    # Feature flags for production
    feature_flags = [
        {"key": "whatsapp_enabled", "value": True},
        {"key": "gmail_enabled", "value": True},
        {"key": "pms_integration", "value": True},
        {"key": "audio_processing", "value": True},
        {"key": "rate_limiting", "value": True},
    ]
    
    # System configuration
    system_configs = [
        {"key": "max_message_length", "value": 1000},
        {"key": "session_timeout_minutes", "value": 30},
        {"key": "max_concurrent_sessions", "value": 100},
    ]
    
    # Insert data...
    print("✅ Production data seeded successfully")

if __name__ == "__main__":
    asyncio.run(seed_production_data())
```

### Configuración de Backup Automático
```bash
#!/bin/bash
# scripts/backup-production.sh

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker exec agente_postgres pg_dump -U agente_user agente_hotel > $BACKUP_DIR/postgres_backup.sql

# MySQL backup  
docker exec agente_mysql mysqldump -u qloapps -p qloapps > $BACKUP_DIR/mysql_backup.sql

# Redis backup
docker exec agente_redis redis-cli --rdb $BACKUP_DIR/redis_backup.rdb

# Compress backups
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Keep only last 7 days of backups
find /backups -name "*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed: $BACKUP_DIR.tar.gz"
```

## 3. CONFIGURACIÓN DE SEGURIDAD

### CORS Setup Específico para este Proyecto
```python
# app/core/middleware.py
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    """Configure CORS for production"""
    
    if settings.environment == Environment.PROD:
        # Production CORS - restrictive
        allowed_origins = [
            f"https://{settings.domain}",
            "https://admin.mihotel.com.ar",
        ]
        allow_credentials = True
        allowed_methods = ["GET", "POST"]
        allowed_headers = ["Authorization", "Content-Type"]
    else:
        # Development CORS - permissive
        allowed_origins = ["*"]
        allow_credentials = True
        allowed_methods = ["*"]
        allowed_headers = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
    )
```

### Rate Limiting Adecuado
```python
# app/core/ratelimit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Production rate limits
RATE_LIMITS = {
    "whatsapp_webhook": "100/minute",    # WhatsApp webhooks
    "health_check": "60/minute",         # Health checks
    "admin_api": "30/minute",            # Admin endpoints
    "public_api": "20/minute",           # Public endpoints
}

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    headers_enabled=True,
)

# Apply to routes
@router.post("/webhooks/whatsapp")
@limiter.limit(RATE_LIMITS["whatsapp_webhook"])
async def whatsapp_webhook(request: Request):
    pass
```

### Validación de Inputs Implementada
```python
# app/models/validation.py
from pydantic import BaseModel, validator, Field
import bleach

class MessageInput(BaseModel):
    """Validated message input"""
    
    content: str = Field(..., min_length=1, max_length=1000)
    phone_number: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    
    @validator('content')
    def sanitize_content(cls, v):
        """Sanitize message content"""
        return bleach.clean(v, tags=[], strip=True)
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Remove non-digits except +
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        return cleaned
```

### Headers de Seguridad Necesarios
```python
# app/core/security_headers.py
from fastapi import Request, Response

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    
    response = await call_next(request)
    
    # Security headers for production
    if settings.environment == Environment.PROD:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp_sources = "https: 'self'"
        if settings.csp_extra_sources:
            csp_sources += f" {settings.csp_extra_sources}"
        response.headers["Content-Security-Policy"] = f"default-src {csp_sources}"
        
        # Cross-Origin policies
        if settings.coop_enabled:
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if settings.coep_enabled:
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    
    return response
```

### Configuración de Autenticación/Autorización
```python
# app/core/auth.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.secret_key = settings.secret_key.get_secret_value()
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expiration_minutes
    
    def create_access_token(self, data: dict):
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
```

## 4. OPTIMIZACIÓN DE PERFORMANCE

### Configuración de Caching Apropiada
```python
# app/core/cache.py
import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            decode_responses=False,
            max_connections=settings.redis_pool_size
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL"""
        try:
            await self.redis.setex(key, ttl, pickle.dumps(value))
        except Exception as e:
            logger.error(f"Cache set error: {e}")

# Cache decorators for common operations
def cache_pms_response(ttl: int = 300):
    """Cache PMS API responses"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_key = f"pms:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached = await cache_service.get(cache_key)
            if cached:
                return cached
            
            # Get fresh data and cache
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

### Compression y Minification Setup
```python
# app/core/compression.py
from fastapi.middleware.gzip import GZipMiddleware

def setup_compression(app):
    """Setup response compression"""
    app.add_middleware(
        GZipMiddleware, 
        minimum_size=1000,  # Only compress responses > 1KB
        compresslevel=6     # Balance between compression and CPU
    )
```

### Optimización de Static Assets
```python
# app/core/static.py
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

def setup_static_files(app):
    """Setup optimized static file serving"""
    
    if settings.environment == Environment.PROD:
        # Production: serve static files with caching headers
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        @app.middleware("http")
        async def add_cache_headers(request, call_next):
            response = await call_next(request)
            if request.url.path.startswith("/static"):
                # Cache static files for 1 year
                response.headers["Cache-Control"] = "public, max-age=31536000"
                response.headers["ETag"] = f'"{hash(request.url.path)}"'
            return response
```

### CDN Configuration (si es necesario)
```nginx
# nginx/nginx.conf - CDN setup
upstream backend {
    server agente-api:8000;
}

server {
    listen 80;
    server_name agente.mihotel.com.ar;
    
    # Static files - serve directly
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }
    
    # API requests - proxy to backend
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Enable caching for GET requests
        proxy_cache_valid 200 302 10m;
        proxy_cache_valid 404 1m;
    }
}
```

### Database Query Optimization
```python
# app/services/optimized_queries.py
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

class OptimizedQueries:
    
    @staticmethod
    async def get_session_with_messages(session_id: str):
        """Optimized query to get session with messages"""
        query = (
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id)
        )
        return await db.scalar(query)
    
    @staticmethod
    async def get_active_sessions_count():
        """Optimized count of active sessions"""
        query = select(func.count(Session.id)).where(
            Session.is_active == True,
            Session.updated_at > datetime.utcnow() - timedelta(hours=1)
        )
        return await db.scalar(query)
```

## 5. ARCHIVOS DE CONFIGURACIÓN COMPLETOS

### Dockerfile Completo
```dockerfile
# Dockerfile.production
FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    espeak \
    espeak-data \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=app:app ./app ./app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### docker-compose.yml Completo
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  agente-api:
    build:
      context: .
      dockerfile: Dockerfile.production
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mysql:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-postgres.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - agente-api
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  postgres_data:
  mysql_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: agente_network
```

### Archivo de Configuración del Servidor
```python
# app/core/config.py - Production Configuration
from functools import lru_cache
from pydantic import BaseSettings

class ProductionConfig:
    """Production-specific configuration"""
    
    # Server Configuration
    UVICORN_HOST = "0.0.0.0"
    UVICORN_PORT = 8000
    UVICORN_WORKERS = 4
    UVICORN_MAX_REQUESTS = 1000
    UVICORN_TIMEOUT_KEEP_ALIVE = 5
    
    # Database Configuration
    DB_POOL_SIZE = 10
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 3600
    
    # Redis Configuration
    REDIS_POOL_SIZE = 20
    REDIS_SOCKET_TIMEOUT = 5
    REDIS_SOCKET_CONNECT_TIMEOUT = 5
    
    # Logging Configuration
    LOG_FORMAT = "json"
    LOG_LEVEL = "INFO"
    LOG_FILE = "/var/log/agente/app.log"
    
    # Security Configuration
    BCRYPT_ROUNDS = 12
    SESSION_TIMEOUT = 3600
    MAX_LOGIN_ATTEMPTS = 5
    
    # Performance Configuration
    ENABLE_GZIP = True
    GZIP_MIN_SIZE = 1000
    CACHE_TTL = 300
    
    # External API Timeouts
    WHATSAPP_TIMEOUT = 30
    GMAIL_TIMEOUT = 30
    PMS_TIMEOUT = 30

@lru_cache()
def get_production_config():
    return ProductionConfig()
```

### Scripts de package.json Optimizados
```json
{
  "name": "agente-hotel-frontend",
  "version": "1.0.0",
  "scripts": {
    "build": "npm run build:prod",
    "build:prod": "NODE_ENV=production webpack --mode=production",
    "build:staging": "NODE_ENV=staging webpack --mode=production",
    "start": "npm run serve:prod",
    "serve:prod": "serve -s dist -l 3001",
    "lint": "eslint src/ --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint src/ --ext .js,.jsx,.ts,.tsx --fix",
    "test": "jest --coverage",
    "test:prod": "jest --coverage --ci --watchAll=false"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "webpack": "^5.88.0",
    "webpack-cli": "^5.1.0",
    "serve": "^14.2.0",
    "eslint": "^8.44.0",
    "jest": "^29.5.0"
  }
}
```

### Configuración de CI/CD Básica
```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --all-extras
          
      - name: Run tests
        run: poetry run pytest
        
      - name: Security scan
        run: |
          pip install safety bandit
          safety check
          bandit -r app/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build production image
        run: |
          docker build -f Dockerfile.production -t agente-hotel:${{ github.sha }} .
          
      - name: Test production image
        run: |
          docker run -d --name test-container -p 8080:8000 agente-hotel:${{ github.sha }}
          sleep 10
          curl -f http://localhost:8080/health/live
          docker stop test-container

  deploy:
    needs: [test, build]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        run: |
          npm install -g @railway/cli
          railway deploy
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## 6. CONFIGURACIÓN ESPECÍFICA DE IA/AGENTES

### Variables de Entorno para APIs de IA
```bash
# OpenAI/ChatGPT Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# Rasa NLU Configuration
RASA_MODEL_PATH=/app/rasa_models/spanish_hotel_model.tar.gz
RASA_SERVER_URL=http://rasa:5005
RASA_CONFIDENCE_THRESHOLD=0.7

# Audio Processing
AUDIO_MAX_FILE_SIZE=10485760  # 10MB
AUDIO_SUPPORTED_FORMATS=mp3,wav,ogg,m4a
STT_ENGINE=whisper  # whisper|google|azure
TTS_ENGINE=espeak   # espeak|coqui|azure

# NLP Processing
NLP_LANGUAGE=es  # Spanish
NLP_MAX_TEXT_LENGTH=2000
NLP_BATCH_SIZE=32
```

### Configuración de Timeouts y Rate Limits
```python
# app/core/ai_config.py
AI_TIMEOUTS = {
    "openai_completion": 30,      # OpenAI API timeout
    "rasa_nlu": 10,              # Rasa NLU processing
    "audio_transcription": 60,    # Audio to text
    "text_to_speech": 30,        # Text to speech
    "pms_query": 15,             # PMS API calls
}

AI_RATE_LIMITS = {
    "openai_requests": "60/minute",     # OpenAI API calls
    "audio_processing": "10/minute",    # Audio processing per user
    "message_processing": "30/minute",  # Message processing per user
    "pms_operations": "20/minute",      # PMS operations per user
}

AI_CIRCUIT_BREAKER = {
    "failure_threshold": 5,        # Failures before opening circuit
    "recovery_timeout": 60,        # Seconds before trying again
    "expected_exception": (AIServiceError, TimeoutError),
}
```

### Manejo de Errores de APIs Externas
```python
# app/services/ai_error_handler.py
from enum import Enum
import asyncio
from typing import Optional

class AIErrorType(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    MODEL_ERROR = "model_error"

class AIErrorHandler:
    
    @staticmethod
    async def handle_ai_error(error: Exception, service: str) -> Optional[str]:
        """Handle AI service errors with fallback responses"""
        
        if isinstance(error, asyncio.TimeoutError):
            logger.warning(f"AI service {service} timeout")
            return "Lo siento, estoy procesando muchas consultas. Por favor intenta en un momento."
        
        elif "rate limit" in str(error).lower():
            logger.warning(f"AI service {service} rate limited")
            return "Temporalmente estoy procesando muchas consultas. Intenta nuevamente en unos minutos."
        
        elif "quota" in str(error).lower():
            logger.error(f"AI service {service} quota exceeded")
            return "Servicio temporalmente no disponible. Por favor contacta directamente al hotel."
        
        else:
            logger.error(f"AI service {service} unexpected error: {error}")
            return "Disculpa, hubo un problema técnico. ¿Podrías reformular tu pregunta?"

# Usage in services
async def process_with_ai(text: str) -> str:
    try:
        result = await ai_service.process(text)
        return result
    except Exception as e:
        fallback = await AIErrorHandler.handle_ai_error(e, "openai")
        return fallback or "Lo siento, no pude procesar tu consulta."
```

### Configuración de Fallbacks
```python
# app/services/ai_fallbacks.py
class AIFallbackService:
    """Fallback responses when AI services fail"""
    
    FALLBACK_RESPONSES = {
        "greeting": [
            "¡Hola! Soy el asistente virtual del hotel. ¿En qué puedo ayudarte?",
            "¡Bienvenido! ¿Cómo puedo asistirte hoy?",
            "¡Hola! Estoy aquí para ayudarte con tu reserva o consultas del hotel.",
        ],
        "booking_inquiry": [
            "Para consultas de reservas, por favor proporciona las fechas que te interesan.",
            "¿Qué fechas tienes en mente para tu estadía?",
            "Me encantaría ayudarte con tu reserva. ¿Para cuándo necesitas la habitación?",
        ],
        "services_inquiry": [
            "Nuestro hotel ofrece diversos servicios. ¿Hay algo específico que te interese?",
            "¿Te gustaría conocer sobre nuestros servicios de restaurante, spa o actividades?",
            "Tenemos múltiples servicios disponibles. ¿Cuál te interesa más?",
        ],
        "error_fallback": [
            "Disculpa, no entendí completamente. ¿Podrías ser más específico?",
            "Lo siento, hubo un problema. ¿Podrías reformular tu pregunta?",
            "No pude procesar tu consulta. Por favor intenta con otras palabras.",
        ]
    }
    
    @classmethod
    def get_fallback_response(cls, intent: str) -> str:
        """Get random fallback response for intent"""
        import random
        responses = cls.FALLBACK_RESPONSES.get(intent, cls.FALLBACK_RESPONSES["error_fallback"])
        return random.choice(responses)
```

Este documento proporciona configuraciones production-ready específicas para el proyecto de Agente Hotelero, incluyendo todas las variables de entorno necesarias, configuración de bases de datos, seguridad, performance y manejo de servicios de IA.