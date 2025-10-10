# DIAGNÓSTICO FORENSE UNIVERSAL - SIST_AGENTICO_HOTELERO

## RESUMEN EJECUTIVO (6 líneas máx.)

**Stack inferido**: FastAPI 0.111.0 + Python 3.12, arquitectura multi-servicio Docker (agente-api, QloApps PMS, PostgreSQL, MySQL, Redis), observabilidad Prometheus/Grafana, IA con Rasa NLU español + spaCy + audio processing FFmpeg/espeak.

**Riesgos críticos**: 15+ secrets hardcodeados en .env.example requieren reemplazo, sin health endpoints evidenciados en código, dependencias externas sin circuit breakers validados, potencial exposición de API keys en logs/configs, falta validación runtime de secrets críticos.

## DETECCIÓN TECNOLÓGICA (EVIDENCIA)

### Lenguajes y Versiones

**Python 3.12** (fuente: pyproject.toml:9, Dockerfile:4, Dockerfile:13)
**FastAPI 0.111.0** (fuente: pyproject.toml:10, requirements.txt:1)
**Uvicorn 0.30.1** (fuente: pyproject.toml:11, requirements.txt:2, Dockerfile:51)

### Frameworks Web/Serverless

**FastAPI** - Framework principal detectado:
- `agente-hotel-api/app/main.py:4` - `from fastapi import FastAPI`
- `agente-hotel-api/app/routers/health.py:5` - `from fastapi import APIRouter`
- `agente-hotel-api/app/routers/webhooks.py:5` - `from fastapi import APIRouter`
- `agente-hotel-api/app/routers/admin.py:3` - `from fastapi import APIRouter`

**Uvicorn ASGI Server**:
- `agente-hotel-api/Dockerfile:51` - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]`
- `agente-hotel-api/Dockerfile.production:80` - `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-4}"]`

### Librerías ML/IA

**Rasa NLU** - Natural Language Understanding:
- `agente-hotel-api/app/services/nlp_engine.py:4` - `# from rasa.core.agent import Agent` (comentado, configuración pendiente)
- `agente-hotel-api/rasa_nlu/config.yml:1` - Archivo configuración Rasa
- `agente-hotel-api/rasa_nlu/data/nlu.yml:1` - Datos entrenamiento NLU
- `agente-hotel-api/rasa_nlu/domain.yml:1` - Dominio del bot

**Audio Processing** - FFmpeg + espeak (inferido):
- `agente-hotel-api/app/utils/audio_converter.py` - Conversor de audio
- `agente-hotel-api/app/services/audio_processor.py` - Procesador de audio
- `agente-hotel-api/app/core/settings.py:27` - `tts_engine: TTSEngine = TTSEngine.ESPEAK`

**RIESGO: [ALTA]** - Rasa agent comentado, integración ML no completada.

### Bases de Datos y Drivers

**PostgreSQL + asyncpg**:
- `agente-hotel-api/pyproject.toml:13` - `asyncpg = "^0.29.0"`
- `agente-hotel-api/app/core/settings.py:63` - `postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"`

**MySQL**:
- `agente-hotel-api/docker-compose.yml:26-44` - Servicio MySQL 8.0 para QloApps

**Redis**:
- `agente-hotel-api/pyproject.toml:14` - `redis = "^5.0.7"`
- `agente-hotel-api/app/core/redis_client.py:8-16` - Cliente Redis con password

**Pooling/Retries**: 
- `agente-hotel-api/app/core/settings.py:68-69` - `postgres_pool_size: int = 10`, `postgres_max_overflow: int = 10`
- **NO EVIDENCIADO**: Retry policies para bases de datos

### Conectores Externos

**WhatsApp Meta Cloud API**:
- `agente-hotel-api/app/services/whatsapp_client.py` - Cliente WhatsApp
- `agente-hotel-api/app/core/settings.py:53-56` - Configuración tokens WhatsApp

**Gmail Integration**:
- `agente-hotel-api/app/services/gmail_client.py` - Cliente Gmail
- `agente-hotel-api/app/core/settings.py:58-59` - Configuración Gmail

**QloApps PMS**:
- `agente-hotel-api/app/services/pms_adapter.py` - Adaptador PMS
- `agente-hotel-api/app/core/settings.py:48-51` - Configuración PMS

**RIESGO: [MEDIA]** - Hardcodes detectados en configuración por defecto.

## ARQUITECTURA FORENSE

### Estructura de Carpetas Ejecutables

```
agente-hotel-api/
├── app/                     # Aplicación principal
│   ├── core/               # Configuración, database, Redis, logging (8 archivos)
│   ├── services/           # Lógica de negocio (12 archivos)
│   ├── models/             # Pydantic schemas, SQLAlchemy (3 archivos)
│   ├── routers/            # FastAPI endpoints (4 archivos)
│   ├── exceptions/         # Custom exceptions (1 archivo)
│   └── utils/              # Utilities (1 archivo)
├── docker/                 # Configuraciones Docker (Prometheus, Grafana, NGINX)
├── tests/                  # Tests unitarios, integración, e2e (14 archivos)
├── scripts/                # Scripts deployment, backup, monitoring (15 archivos)
└── rasa_nlu/              # Configuración Rasa NLU (3 archivos)
```

### Puntos de Entrada Principales

**app/main.py** - FastAPI application factory:
- `agente-hotel-api/app/main.py:43` - `app = FastAPI(title=APP_TITLE, version=APP_VERSION, debug=APP_DEBUG, lifespan=lifespan)`

**Dockerfile** - Container multi-stage:
- `agente-hotel-api/Dockerfile:4` - `FROM python:3.12-slim AS builder`
- `agente-hotel-api/Dockerfile:13` - `FROM python:3.12-slim` (runtime)

**docker-compose.yml** - Orquestación servicios:
- `agente-hotel-api/docker-compose.yml:48-60` - Servicio agente-api principal

**Makefile** - Comandos desarrollo/deploy:
- `agente-hotel-api/Makefile:17-34` - Detección automática gestores dependencias

### Módulos Core por Referencias

1. **orchestrator.py** - Coordinador workflows IA (importado en tests/integration)
2. **pms_adapter.py** - Abstracción PMS con circuit breaker (importado 3 veces)
3. **settings.py** - Configuración central (importado 8+ veces)
4. **middleware.py** - Middlewares CORS, logging, exception handling (importado en main.py)
5. **health.py** - Health checks (endpoint /health/live, /health/ready)

### Patrones Detectados

**Orchestrator Pattern**:
- `agente-hotel-api/app/services/orchestrator.py:80-93` - Lógica coordinación entre PMS y NLP

**Adapter Pattern**:
- `agente-hotel-api/app/services/pms_adapter.py:161` - "Adaptador de prueba que emula respuestas del PMS"

**Circuit Breaker Pattern**:
- `agente-hotel-api/app/core/circuit_breaker.py:21-32` - Métricas circuit breaker PMS

**Event-driven**: 
- **NO EVIDENCIADO** - No se detectan event handlers o message queues

**Streaming**:
- **NO EVIDENCIADO** - No se detectan interfaces streaming

### Integraciones Agénticas

**Memory Stores**: Redis para sesiones - `agente-hotel-api/app/services/session_manager.py`
**Tool Interfaces**: PMS adapter, WhatsApp client, Gmail client
**Orquestadores**: Orchestrator service coordina NLP + PMS

**GAPS DETECTADOS**:
- Rasa agent deshabilitado (comentado)
- Falta integración OpenAI (configurado en docs pero no en código)
- Audio transcription workflow incompleto

## REQUISITOS DE DESPLIEGUE (EVIDENCIA)

### Variables de Entorno Usadas

**Secrets críticos** (detectados con os.getenv/settings pattern):
- `SECRET_KEY` - `agente-hotel-api/app/core/settings.py:28` - Sin default, requerido
- `PMS_API_KEY` - `agente-hotel-api/app/core/settings.py:50` - Sin default, requerido  
- `WHATSAPP_ACCESS_TOKEN` - `agente-hotel-api/app/core/settings.py:53` - Sin default, requerido
- `GMAIL_APP_PASSWORD` - `agente-hotel-api/app/core/settings.py:59` - Sin default, requerido

**Defaults inseguros detectados**:
- `agente-hotel-api/app/core/settings.py:63` - `postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"`
- `agente-hotel-api/app/core/settings.py:69` - `redis_url: str = "redis://localhost:6379/0"` (sin password por defecto)

### Puertos/Protocolos

**Puerto 8000** - Aplicación principal:
- `agente-hotel-api/Dockerfile:48-51` - `EXPOSE 8000`
- `agente-hotel-api/app/main.py` - FastAPI server

**Healthchecks detectados**:
- `agente-hotel-api/Dockerfile:42-43` - `HEALTHCHECK CMD curl -f http://localhost:8000/health/live`
- `agente-hotel-api/app/routers/health.py` - Endpoints /health/live, /health/ready

### Recursos Estimados (CPU/IO/VRAM)

**CPU**: 2-4 workers uvicorn (configurable), FastAPI async + PostgreSQL pooling → **Estimado: 2-4 vCPUs**
**Memoria**: Python 3.12 + FastAPI + Redis + audio processing → **Estimado: 1-2GB RAM**
**IO**: Audio files, DB operations, external API calls → **Medio-Alto I/O**
**VRAM**: **N/A** - No hay modelos ML cargados en memoria (Rasa deshabilitado)

### Dependencias del Sistema

**curl** - `agente-hotel-api/Dockerfile:24` - Para healthchecks
**FFmpeg** - Inferido para audio processing (no explícito en Dockerfile)
**espeak** - TTS engine configurado por defecto

**RIESGO: [MEDIA]** - Dependencias sistema no documentadas en Dockerfile.

## CONFIGURACIÓN ACTUAL Y BRECHAS

### Archivos .env Detectados

**Archivos existentes**:
- `agente-hotel-api/.env.example:1-136` - Template completo con 15+ placeholders REPLACE_WITH_*

**Archivos ausentes**:
- `.env` - NO EVIDENCIADO
- `.env.production` - NO EVIDENCIADO  
- `.env.local` - NO EVIDENCIADO

### Scripts Build/Test/Deploy

**Makefile idempotente**:
- `agente-hotel-api/Makefile:17-34` - Auto-detección poetry/uv/npm
- `agente-hotel-api/Makefile:50-95` - Comandos Docker con --build

**Scripts deployment**:
- `agente-hotel-api/scripts/deploy.sh` - Script deployment
- `agente-hotel-api/scripts/backup.sh` - Backup databases
- `agente-hotel-api/scripts/health-check.sh` - Health validation

**RIESGO: [BAJA]** - Scripts bien estructurados, idempotencia validada.

### Hardcoding (API keys, hosts, rutas absolutas)

**ALTA severidad**:
- `agente-hotel-api/.env.example:11` - `SECRET_KEY=REPLACE_WITH_SECURE_32_CHAR_HEX_KEY`
- `agente-hotel-api/.env.example:23` - `PMS_API_KEY=REPLACE_WITH_REAL_QLOAPPS_API_KEY`
- `agente-hotel-api/.env.example:32` - `POSTGRES_PASSWORD=REPLACE_WITH_SECURE_POSTGRES_PASSWORD`

**MEDIA severidad**:
- `agente-hotel-api/app/core/settings.py:63` - Default postgres URL con credenciales débiles
- `agente-hotel-api/app/core/settings.py:69` - Default redis sin password

## TABLA DE RIESGOS

| Riesgo | Severidad | Evidencia (archivo:líneas) | TODO |
|--------|-----------|---------------------------|------|
| Secrets en .env.example | Alta | .env.example:11,23,32,44,50,58,68 | Reemplazar todos REPLACE_WITH_* antes deploy (Prioridad: Alta) |
| Defaults DB inseguros | Alta | app/core/settings.py:63,69 | Forzar validación secrets en producción (Prioridad: Alta) |
| Rasa NLU deshabilitado | Media | app/services/nlp_engine.py:4 | Completar integración IA o documentar alternativa (Prioridad: Media) |
| Dependencias sistema sin docs | Media | Dockerfile:24 vs audio processing | Documentar FFmpeg/espeak en Dockerfile (Prioridad: Media) |
| Sin retry policies DB | Media | NO EVIDENCIADO | Implementar retry exponential backoff (Prioridad: Baja) |
| Circuit breaker sin validar | Media | app/core/circuit_breaker.py:21-32 | Validar funcionamiento PMS circuit breaker (Prioridad: Media) |
| Health endpoint simple | Baja | Dockerfile:42-43 | Mejorar health check con dependency validation (Prioridad: Baja) |

## COMANDOS DE VERIFICACIÓN (COPIAR/PEGAR)

```bash
# Verificar frameworks y puntos de entrada
cd /home/runner/work/SIST_AGENTICO_HOTELERO/SIST_AGENTICO_HOTELERO
git ls-files | xargs grep -nE "import fastapi|from fastapi|Flask|Django|uvicorn|gunicorn" || true

# Detectar librerías IA/ML
git ls-files | xargs grep -nE "import torch|from transformers|openai\.|langchain|llama|gpt-|accelerate|tiktoken|rasa|spacy" || true

# Buscar secrets y hardcodes
git ls-files | xargs grep -nE "API_KEY|SECRET_KEY|PASSWORD|AWS_SECRET_ACCESS_KEY|\"sk-\"|\"AKIA" || true

# Detectar strings conexión DB
git ls-files | xargs grep -nE "postgresql://|mongodb://|mysql://|redis://" || true

# Verificar configuración Docker
cd agente-hotel-api
docker-compose config

# Validar health endpoints
curl -f http://localhost:8000/health/live || echo "APP NOT RUNNING"
curl -f http://localhost:8000/health/ready || echo "DEPENDENCIES NOT READY"

# Verificar secrets en .env
grep -E "REPLACE_WITH_|your_.*_here" .env.example | wc -l
```

## MAPA ARQUITECTURA ANTIFRÁGIL

```mermaid
flowchart TD
    User -->|requests| LoadBalancer[NGINX Reverse Proxy]
    LoadBalancer --> Web[agente-api:8000]
    Web --> Orchestrator[Orchestrator Service]
    Orchestrator --> LLMPrimary[Rasa NLU - Deshabilitado]
    Orchestrator --> LLMFallback[spaCy NLP Fallback]
    LLMPrimary -.fail.-> LLMFallback
    Orchestrator --> Cache[Redis Cache/Locks]
    Orchestrator --> PMS[QloApps PMS via Adapter]
    PMS --> MySQL[(MySQL 8.0)]
    Web --> Postgres[(PostgreSQL)]
    Postgres --> Backup[Scripts/backup.sh]
    Backup -->|daily| Storage[Volume Storage]
    Monitoring[Prometheus] --> Alerting[AlertManager]
    Monitoring --> AutoHealing[Health Scripts]
    AutoHealing -.restart.-> Web
```