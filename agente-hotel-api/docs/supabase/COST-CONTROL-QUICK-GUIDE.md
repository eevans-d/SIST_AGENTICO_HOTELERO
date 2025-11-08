# Supabase Cost-Control Quick Guide

Minimiza costes y evita ejecuciones accidentales al usar Supabase con el Agente Hotelero.

---

## 1) Activación explícita (DEV)

Por defecto, en desarrollo NO se levanta Postgres local a menos que pidas el perfil `local-db`.

- Usar Postgres local (sin tocar Supabase):

```bash
docker compose -f agente-hotel-api/docker-compose.dev.yml --profile local-db up
```

- Usar Supabase puntualmente (pool mínimo + timeouts):

```bash
export USE_SUPABASE=true
export DATABASE_URL="postgresql+asyncpg://USER:PASS@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"
# Levanta sólo lo necesario (sin Postgres local):
docker compose -f agente-hotel-api/docker-compose.dev.yml up agente-api redis
```

Guardarraíles automáticos cuando `USE_SUPABASE=true` y URL de Supabase:
- Pool reducido: `postgres_pool_size=2`, `postgres_max_overflow=2`
- Timeouts: `statement_timeout=15s`, `idle_in_transaction_session_timeout=10s`
- Debug SQL desactivado

---

## 2) Operaciones de esquema (CI) – Seguro y manual

Workflow: `Supabase Schema Ops`.
- URL directa: `https://github.com/OWNER/REPO/actions/workflows/supabase-schema-ops.yml`
  (reemplaza OWNER/REPO con tu repo real: `eevans-d/SIST_AGENTICO_HOTELERO`)

Cómo lanzarlo:
1. Actions → "Supabase Schema Ops" → "Run workflow".
2. Para validar sin aplicar: `validate_only=true` (recomendado).
3. Para aplicar: deja `apply=true` y `validate_only=false`.

Seguridad integrada:
- Concurrency con cancelación: nunca habrá 2 ejecuciones simultáneas.
- Timeout 20 min.
- Verificaciones previas: exige pooler `:6543` y `sslmode=require`.
- El script requiere `--yes` para aplicar; sin eso aborta.
 - Job opcional de seed (desactivado por defecto) protegido por input `confirm_seed=false`.
 - Validación de secretos: aborta si `SUPABASE_ADMIN_PASSWORD` es placeholder.
 - Seed idempotente con flag `--update-if-exists` para actualizar nombre de tenant.

Nota sobre diagnóstico local (SSL): para confirmar problemas puntuales de SSL en desarrollo, el script `scripts/test_supabase_connection.py` ofrece `--insecure`, que desactiva la verificación SSL de manera temporal y solicita confirmación manual escribiendo `YES`. Este modo está bloqueado automáticamente en CI/producción.

---

## 3) Checklist de bajo coste (antes de conectar a Supabase)

- [ ] `USE_SUPABASE=true` sólo cuando realmente lo uses.
- [ ] `DATABASE_URL` apunta al pooler y tiene `sslmode=require`.
- [ ] Logs de arranque muestran pool 2/2 y timeouts activos.
- [ ] Sin procesos en loop (polling <1s). Usa backoff y TTLs de cache.
- [ ] No hagas profiling/echo SQL en Supabase.
 - [ ] Seed sólo si necesitas tenant/admin inicial (usar confirm_seed). 
 - [ ] Verifica que el password admin viene de secret y no de input manual.

---

## 4) Buenas prácticas

- Ejecuta validaciones (validate-only) con más frecuencia que aplicaciones de schema.
- Agrupa escrituras en transacciones cortas.
- Evita workers o cron jobs ociosos que mantengan conexiones abiertas.
- Prefiere Postgres local para pruebas intensivas.

---

## 5) Diagnóstico rápido

Conexiones activas por estado (en Supabase):

```sql
SELECT state, COUNT(*)
FROM pg_stat_activity
WHERE application_name LIKE 'hotel_agent_%'
GROUP BY state;
```

Objetivo en dev/staging: ≤ 4 conexiones totales.

Diagnóstico de conexión:
- Normal: `python scripts/test_supabase_connection.py`
- Solo DEV (temporal, confirmación requerida): `python scripts/test_supabase_connection.py --insecure`

---

## 6) Referencias

- Compose: `agente-hotel-api/docker-compose.dev.yml`
- Settings: `app/core/settings.py` (`USE_SUPABASE`, pool y timeouts)
- Engine: `app/core/database.py` (server_settings, application_name)
- Workflow: `.github/workflows/supabase-schema-ops.yml`
- Script apply: `scripts/apply_supabase_schema.py` (`--yes` requerido)
- Script validate: `scripts/validate_supabase_schema.py`
- Script seed: `scripts/seed_supabase_minimal.py` (flags: `--skip-admin`, `--force-password`, `--update-if-exists`)
