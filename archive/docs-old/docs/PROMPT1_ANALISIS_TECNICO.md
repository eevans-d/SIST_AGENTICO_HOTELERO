# PROMPT 1: ANÁLISIS TÉCNICO COMPLETO DEL PROYECTO

## 1. STACK TECNOLÓGICO

### Framework Principal
- **FastAPI 0.111.0** - Framework web asíncrono de alto rendimiento
- **Python 3.12** - Runtime environment
- **Uvicorn 0.30.1** - Servidor ASGI con soporte estándar

### Dependencias Críticas y Versiones
- **SQLAlchemy 2.0.31** - ORM con soporte asyncio para PostgreSQL
- **AsyncPG 0.29.0** - Driver asíncrono para PostgreSQL
- **Redis 5.0.7** - Cliente Redis para cache y distributed locks
- **Pydantic 2.8.2** - Validación de datos y settings management
- **Pydantic-Settings 2.3.4** - Configuración desde variables de entorno
- **Structlog 24.3.0** - Logging estructurado con correlation IDs
- **HTTPx 0.27.0** - Cliente HTTP asíncrono para integraciones
- **Prometheus-Client 0.20.0** - Métricas y observabilidad
- **SlowAPI 0.1.9** - Rate limiting con Redis backend
- **Bleach 6.1.0** - Sanitización de inputs
- **Python-Jose 3.3.0** - JWT authentication con cryptography
- **Passlib 1.7.4** - Hashing de passwords con bcrypt

### Base de Datos
- **PostgreSQL** - Base de datos principal para el agente (asyncpg driver)
- **MySQL 8.0** - Base de datos para QloApps PMS
- **Redis** - Cache, locks distribuidos, rate limiting, session storage

### APIs Externas Integradas
- **WhatsApp Business API (Meta Cloud API v18.0)** - Comunicación via WhatsApp
- **Gmail API** - Integración de correo electrónico
- **QloApps PMS API** - Sistema de gestión hotelera

### Servicios de Terceros
- **QloApps** - Sistema PMS (Property Management System)
- **Meta Business Cloud API** - WhatsApp Business integration
- **Gmail SMTP** - Email notifications

### Librerías de IA/ML
- **Rasa NLU** - Natural Language Understanding
- **spaCy** - Procesamiento de lenguaje natural en español
- **Audio Processing** - FFmpeg para conversión de audio
- **TTS Engines** - Espeak/Coqui para text-to-speech

## 2. ARQUITECTURA DEL SISTEMA

### Estructura de Carpetas Clave
```
agente-hotel-api/
├── app/
│   ├── core/           # Configuración, database, Redis, logging
│   ├── services/       # Lógica de negocio (orchestrator, PMS adapter)
│   ├── models/         # Pydantic schemas, SQLAlchemy models
│   ├── routers/        # FastAPI endpoints (health, webhooks, admin)
│   ├── exceptions/     # Custom exceptions
│   └── utils/          # Utilities (audio converter)
├── docker/             # Prometheus, Grafana, NGINX configs
├── tests/              # Unit, integration, e2e tests
├── scripts/            # Deployment, backup, monitoring scripts
└── docs/               # Documentation and runbooks
```

### Puntos de Entrada Principales
- **app/main.py** - FastAPI application factory
- **Dockerfile** - Multi-stage production container
- **docker-compose.yml** - Orquestación de servicios
- **Makefile** - Comandos de desarrollo, testing, deployment

### Servicios y Módulos Core
- **Orchestrator** (`app/services/orchestrator.py`) - Coordina workflows de IA
- **PMS Adapter** (`app/services/pms_adapter.py`) - Abstrae interacciones con QloApps
- **Message Gateway** (`app/services/message_gateway.py`) - Manejo unificado de mensajes
- **Session Manager** (`app/services/session_manager.py`) - Estado de conversaciones
- **NLP Engine** (`app/services/nlp_engine.py`) - Procesamiento de lenguaje natural
- **Audio Processor** (`app/utils/audio_converter.py`) - STT/TTS processing

### Integraciones Agénticas Específicas
- **Unified Message Model** - Normaliza comunicaciones multi-canal
- **Circuit Breaker Pattern** - Resiliencia en integraciones externas
- **Distributed Locks** - Previene conflictos en reservas
- **Correlation IDs** - Trazabilidad cross-service
- **Structured Logging** - Observabilidad de workflows de IA

### Patrones de Arquitectura Implementados
- **Adapter Pattern** - PMS integration con circuit breaker
- **Gateway Pattern** - Unified messaging interface
- **Observer Pattern** - Metrics y monitoring
- **Circuit Breaker** - Fault tolerance
- **Repository Pattern** - Data access abstraction

## 3. REQUISITOS DE DESPLIEGUE

### Variables de Entorno Necesarias (Lista Completa)
```bash
# Core Application
SECRET_KEY=                    # JWT secret (32 chars hex)
ENVIRONMENT=production         # development|production
DEBUG=false                   # true|false
APP_NAME=Agente Hotel API
VERSION=0.1.0

# Database (PostgreSQL - Agent)
POSTGRES_DB=agente_hotel
POSTGRES_USER=agente_user
POSTGRES_PASSWORD=            # Strong password required
POSTGRES_URL=postgresql+asyncpg://user:pass@postgres:5432/db
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=10

# Database (MySQL - QloApps PMS)
MYSQL_DATABASE=qloapps
MYSQL_USER=qloapps
MYSQL_PASSWORD=              # Strong password required
MYSQL_ROOT_PASSWORD=         # Strong password required

# Redis (Cache & Locks)
REDIS_PASSWORD=              # Strong password required
REDIS_URL=redis://:password@redis:6379/0
REDIS_POOL_SIZE=20

# PMS Integration
PMS_TYPE=qloapps             # qloapps|mock
PMS_BASE_URL=http://qloapps:80
PMS_API_KEY=                 # QloApps API key
PMS_TIMEOUT=30

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=       # Meta Cloud API token
WHATSAPP_PHONE_NUMBER_ID=    # Phone number ID from Meta
WHATSAPP_VERIFY_TOKEN=       # Webhook verification token
WHATSAPP_APP_SECRET=         # App secret for signature verification

# Gmail Integration
GMAIL_USERNAME=              # Gmail account
GMAIL_APP_PASSWORD=          # Gmail app password (not regular)

# Audio & NLP
AUDIO_ENABLED=true
TTS_ENGINE=espeak           # espeak|coqui
LOG_LEVEL=INFO              # DEBUG|INFO|WARNING|ERROR

# Security Headers
CSP_EXTRA_SOURCES=          # Space-separated URLs
COOP_ENABLED=true
COEP_ENABLED=true

# JWT Authentication
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Operational
CHECK_PMS_IN_READINESS=true  # Enable PMS health checks

# Monitoring
GRAFANA_ADMIN_PASSWORD=      # Grafana admin password

# Alerting (Optional)
SLACK_WEBHOOK_URL=           # Slack webhook for alerts
SLACK_CHANNEL=#alerts
ALERT_EMAIL_TO=ops@domain.com
ALERT_EMAIL_FROM=alerts@domain.com
SMTP_HOST=smtp.domain.com
SMTP_PORT=587
SMTP_USER=alerts@domain.com
SMTP_PASSWORD=               # SMTP password

# SSL/TLS (Production)
DOMAIN=agente.domain.com
EMAIL_FOR_CERTBOT=admin@domain.com
```

### Configuraciones de Base de Datos Requeridas
- **PostgreSQL**: Database `agente_hotel`, user `agente_user`, pool size 10
- **MySQL**: Database `qloapps`, user `qloapps` para QloApps PMS
- **Redis**: Password-protected, database 0, pool size 20

### Puertos y Servicios que Debe Exponer
- **8000**: FastAPI application (internal)
- **80/443**: NGINX proxy (external)
- **3000**: Grafana dashboard (optional external)
- **9090**: Prometheus (internal)
- **9093**: AlertManager (internal)
- **6379**: Redis (internal)
- **5432**: PostgreSQL (internal)
- **3306**: MySQL (internal)

### Recursos Mínimos
- **RAM**: 4GB mínimo, 8GB recomendado
- **CPU**: 2 cores mínimo, 4 cores recomendado
- **Storage**: 20GB mínimo, 50GB recomendado
- **Network**: 1Gbps recomendado para integraciones API

### Certificados SSL/HTTPS Necesarios
- **Domain SSL Certificate** para HTTPS
- **Let's Encrypt** configurado con Certbot
- **NGINX SSL termination** configurado

## 4. DEPENDENCIAS DE SISTEMA

### Versión Específica de Runtime
- **Python 3.12** (exacto, no 3.11 o anteriores)
- **Poetry** para gestión de dependencias
- **Docker 20.10+** y Docker Compose V2

### Servicios del Sistema Operativo
- **systemd** para service management
- **cron** para tareas programadas
- **logrotate** para gestión de logs
- **fail2ban** para seguridad (opcional)

### Herramientas de Build Requeridas
- **Docker** y **Docker Compose**
- **Make** para automatización
- **curl** para health checks
- **jq** para procesamiento JSON
- **FFmpeg** para audio processing
- **Espeak** o **Coqui TTS** para text-to-speech

### Comandos de Instalación Global
```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Ruff (linting)
pip install ruff

# FFmpeg (audio processing)
sudo apt-get install ffmpeg

# Espeak (TTS)
sudo apt-get install espeak espeak-data

# K6 (performance testing)
curl -L https://github.com/grafana/k6/releases/download/v0.46.0/k6-v0.46.0-linux-amd64.tar.gz | tar -xz
sudo cp k6-v0.46.0-linux-amd64/k6 /usr/local/bin/
```

## 5. CONFIGURACIÓN ACTUAL

### Archivos de Configuración Existentes
- **.env.example** - Template con todas las variables requeridas
- **docker-compose.yml** - Orquestación development/production
- **docker-compose.production.yml** - Configuración específica de producción
- **Dockerfile** - Multi-stage container build
- **Dockerfile.production** - Production-optimized container
- **pyproject.toml** - Poetry dependencies y configuración
- **pytest.ini** - Testing configuration
- **.pre-commit-config.yaml** - Git hooks

### Scripts de Makefile
```bash
# Development
make install          # Install dependencies (auto-detects poetry/uv)
make dev-setup        # Create .env from .env.example
make fmt              # Format with Ruff + Prettier
make lint             # Lint with Ruff + security scan
make test             # Run pytest

# Docker Operations
make docker-up        # Start full stack with --build
make docker-down      # Stop and remove containers
make logs             # Follow all service logs
make health           # Run health checks

# Security & Performance
make security-scan    # Full security scan
make security-fast    # Quick HIGH/CRITICAL scan
make performance-test # K6 load testing
make stress-test      # K6 stress testing

# Governance & SLO
make validate-slo-compliance    # SLO compliance validation
make check-error-budget        # Error budget monitoring
make validate-runbooks         # Runbook validation
make pre-deploy-check         # Complete pre-deployment validation

# Production Deployment
make validate-deployment      # Comprehensive pre-deployment validation
make deploy-production       # Production deployment with validations
make build-production        # Build production Docker image
make canary-deploy          # Canary deployment
```

### Variables de Entorno ya Definidas
Ver sección 3 para lista completa. Variables críticas incluyen:
- Application secrets (SECRET_KEY, JWT config)
- Database credentials (PostgreSQL, MySQL, Redis)
- External API keys (WhatsApp, Gmail, PMS)
- Monitoring passwords (Grafana)

### Configuraciones Desarrollo vs Producción
- **Development**: Debug enabled, mock PMS, permissive CORS
- **Production**: Debug disabled, real PMS, strict security headers
- **Environment validation**: Blocks production start with dummy secrets
- **Docker configs**: Separate docker-compose files per environment
- **Resource limits**: Production containers have memory/CPU limits
- **Health checks**: More stringent in production
- **Monitoring**: Full observability stack in production

## Comandos Ejecutables Específicos

### Setup Inicial
```bash
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api
make dev-setup
# Edit .env with real credentials
make install
```

### Desarrollo Local
```bash
make fmt && make lint && make test
make docker-up
make health
make logs
```

### Producción
```bash
make validate-deployment
make deploy-production
make deployment-status
```

### Monitoreo
```bash
make validate-slo-compliance
make check-error-budget
make performance-test
```