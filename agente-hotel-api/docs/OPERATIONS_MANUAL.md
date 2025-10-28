---
title: Manual de Operaciones - Agente Hotelero API
last_updated: 2025-10-27
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

### Flags de funciones (Feature Flags)

- Backend usa Redis para resolver flags con caché en memoria. Defaults en `app/services/feature_flag_service.py`.
- Flag relevante para WhatsApp:
	- `features.interactive_messages`
		- Default: `false` (pruebas usan texto plano para aserciones deterministas).
		- Staging/Producción: activar para enviar botones/listas interactivas.
		- Cómo activar (Redis hash `feature_flags`):
			- `HSET feature_flags features.interactive_messages 1`
		- Observabilidad: métrica gauge por flag en Prometheus.
		- Variantes: cuando hay imagen disponible se usará `interactive_buttons_with_image` en lugar de `interactive_buttons`.
		- Verificación: el webhook de WhatsApp devuelve eco de `response_type` y `content` en respuestas de test para facilitar aserciones.

#### Administración y lectura de flags
- Endpoint de solo lectura (auth requerida): `GET /admin/feature-flags`
  - Devuelve `{ "flags": { "flag_name": true|false } }`
  - Origen: Redis `feature_flags` con fallback a defaults (`DEFAULT_FLAGS`).
  - Rate limit: 60/min.

#### Métricas y administración de flags
- Métrica Prometheus: `feature_flag_enabled{flag}` (Gauge 1/0)
- Endpoint admin (requiere auth): `GET /admin/feature-flags`
  - Retorna lista con `flag`, `enabled`, `source` (`redis`|`default`).
- Flag de normalización telefónica avanzada: `tenancy.phone_normalization.advanced`
  - Default: `false`. Al habilitar, si está disponible la librería `phonenumbers`, se normaliza a E.164.

Nota: En entorno de pruebas, el sistema fuerza “horario hábil” para evitar respuestas de fuera de horario y mantener estabilidad de los tests de integración.

## 9. Referencias
- Arquitectura y patrones: `.github/copilot-instructions.md` y `DEVIATIONS.md`
- Configuración: `app/core/settings.py`
- Orquestador: `app/services/orchestrator.py`
