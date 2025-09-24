# Agente Hotelero IA

![CI](https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/actions/workflows/ci.yml/badge.svg)

Sistema multi-servicio (FastAPI) para recepcionista virtual que integra WhatsApp/Gmail y QloApps PMS.

## Requisitos rápidos
- Docker y Docker Compose
- Python 3.11+ (opcional para desarrollo local)

## Puesta en marcha
1. Configurar variables de entorno
   - Copia el archivo .env.example (si existe) o crea `.env` en `agente-hotel-api/`:
     - APP_NAME, ENV, DEBUG
     - POSTGRES_URL, REDIS_URL
     - JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
     - WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET
     - PMS_BASE_URL, PMS_API_KEY
     - CHECK_PMS_IN_READINESS=true|false
2. Construir y levantar stack
   - make docker-up
3. Verificar salud
   - make health

## Desarrollo
- make dev-setup (crear .env)
- make install (deps)
- make fmt / make lint
- make logs

## Endpoints clave
- /health/live | /health/ready
- /metrics (Prometheus)
- /webhooks/whatsapp (GET verificación; POST eventos)
- /admin/dashboard (protegido)

## Estructura
- agente-hotel-api/app: código FastAPI
- docker/: Prometheus, Grafana, Alertmanager, NGINX
- tests/: unit, integration, e2e con pytest

## Webhook de WhatsApp
- GET: valida challenge usando parámetros hub.mode, hub.verify_token, hub.challenge
- POST: firma X-Hub-Signature-256 con HMAC SHA-256 usando WHATSAPP_APP_SECRET

## CI
- GitHub Actions (workflow `ci.yml`):
   - Instalación dependencias (Poetry)
   - Lint & formato (ruff)
   - Tests (unit, integration, e2e rápidos)
   - Escaneo seguridad rápido (Trivy modo light)
   - Build de imagen Docker (verificación)

Badge arriba indica estado de la última ejecución en rama `main`.

### Próximos (roadmap)
- Workflow `deploy.yml` (manual dispatch) para publicar imagen versionada
- Dependabot / Renovate para actualización de dependencias
- Escaneo deep (Trivy fs + SBOM) en pipeline nocturno

## Notas
- Logging estructurado con structlog y correlation IDs
- Circuit breaker y caché para PMS
- Rate limiting con Redis

Para más detalles ver `agente-hotel-api/README-Infra.md` y `.github/copilot-instructions.md`.
