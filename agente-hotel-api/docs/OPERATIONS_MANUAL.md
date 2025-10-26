---
title: Manual de Operaciones - Agente Hotelero API
last_updated: 2025-10-26
owner: Backend AI Team
---

# Manual de Operaciones

## 1. Descripción
Servicio FastAPI que orquesta WhatsApp/Gmail con PMS (QloApps o mock). Desplegado en Fly.io. Observabilidad con Prometheus/Grafana/Alertmanager y Jaeger (local con docker-compose).

## 2. Health checks
- Liveness: `GET /health/live` (siempre 200)
- Readiness: `GET /health/ready` (depende de Postgres/Redis y PMS si está habilitado)
- Flags de readiness vía variables de entorno (ver `app/routers/health.py`).

## 3. Operación rutinaria
- Verificar logs y métricas (errores, latencia P95, circuit breaker).
- Monitorear límites de rate-limiting y estado de PMS.
- Ejecutar `scripts/final-verification.sh` antes de releases.

## 4. Incidentes comunes
- PMS caída → Circuit breaker OPEN; seguir `docs/runbooks/pms-outage.md`.
- Redis no disponible → Degradación de cache/locks; seguir `docs/runbooks/redis-degraded.md`.
- Errores 5xx elevados → `docs/runbooks/high-error-rate.md`.

## 5. Backups y restore
- Usar `scripts/backup.sh` y `scripts/restore.sh`.
- Programar cron en entorno operativo si aplica.

## 6. Despliegue
- Fly.io: `flyctl deploy` con `Dockerfile.optimized`.
- Argumento de build `INCLUDE_AUDIO=false` por defecto (reduce tamaño). Cambiar a `true` si se requiere stack de audio (ffmpeg/whisper).

## 7. Seguridad
- Secretos en Fly (secrets) y `.env` local (no commitear).
- Dependencias escaneadas con `trivy`; abordar HIGH/CRITICAL.

## 8. Testing & calidad
- Lint: `ruff` (formateo/estilo)
- Tests: `pytest` (unit/integration/e2e)
- Cobertura meta: 70% global, ≥85% en servicios críticos.

## 9. Referencias
- Arquitectura y patrones: `.github/copilot-instructions.md` y `DEVIATIONS.md`
- Configuración: `app/core/settings.py`
- Orquestador: `app/services/orchestrator.py`
