# LLM Implementation Master Guide — Supabase (SIST_AGENTICO_HOTELERO)

Versión: 1.1.0 FINAL  
Fecha: 2025-11-07  
Estado: Listo para Ejecución Operativa (100% autosuficiente)

Nota operativa: La plataforma Fly.io ha sido dada de baja. No hay dependencias activas con Fly.io. Este documento se centra exclusivamente en la plataforma de base de datos gestionada (Supabase Postgres) para el proyecto.

---

## Índice

- 1) Propósito y Alcance
- 2) Arquitectura de Datos (Resumen)
- 3) Conexión a Supabase (Pooler + SSL)
- 4) DDL Canónico (Single Source of Truth)
- 5) Automatización disponible en el repo
- 6) Proceso de Ejecución (para el LLM)
- 7) Seguridad y Guardrails
- 8) Costos y Control de Consumo
- 9) Troubleshooting rápido
- 10) Criterios de Aceptación (Definition of Done)
- 11) Apéndices
- 12) Monitoreo y Observabilidad
- 13) Mantenimiento Periódico
- 14) Migración de Datos
- 15) Disaster Recovery
- 16) Performance y Optimización
- 17) Integración con Backend
- 18) FAQ Avanzado
- 19) Glosario de Términos
- 20) Quick Reference

---

## 1) Propósito y Alcance

Este documento es la fuente única de verdad para implementar y operar todo lo necesario en Supabase para el proyecto “SIST_AGENTICO_HOTELERO”. Está diseñado para que un asistente externo (LLM) pueda, apoyándose sólo en este documento, ejecutar casi el 100% de las tareas requeridas sin consultar información adicional.

Lo que sí cubre:
- Modelo de datos y DDL canónico (tablas, índices, FKs, triggers) para Postgres en Supabase.
- Configuración de conexión mediante Connection Pooler (puerto 6543) con SSL obligatorio.
- Scripts y comandos de automatización existentes en el repositorio y cómo usarlos.
- Validaciones post-despliegue, pruebas de humo y verificación de integridad.
- Seguridad, permisos mínimos recomendados y guardrails.
- Operación diaria, troubleshooting y control de costos.

Lo que NO cubre (fuera de alcance en Supabase):
- Dominio hotelero (rooms, reservations, pricing, guests): reside en QloApps PMS (externo).
- Conversational sessions: residen en Redis (TTL 30 minutos).
- Feature flags: residen en Redis (hash). 
- Autenticación gestionada por Supabase Auth: NO se usa; el backend usa JWT custom con python-jose.

---

## 2) Arquitectura de Datos (Resumen)

Entidades en Supabase (todas en schema `public`):
- users
- user_sessions
- password_history
- tenants
- tenant_user_identifiers
- lock_audit

Relaciones clave (con aclaración de FK lógicas vs reales):
- user_sessions.user_id → users.id (FK constraint real)
- password_history.user_id → users.id (FK constraint real)
- tenant_user_identifiers.tenant_id → tenants.id (FK constraint real - nota: apunta a PK numérica)
- users.tenant_id → tenants.tenant_id (FK lógica SIN constraint - apunta a slug VARCHAR)

**Aclaración importante sobre tenant_id**:
- Tabla `tenants` tiene DOS identificadores:
  - `id`: SERIAL PRIMARY KEY (numérico autoincrementado)
  - `tenant_id`: VARCHAR slug único (ej: "hotel-abc") - clave lógica usada en código
- Tabla `tenant_user_identifiers` usa `tenant_id INTEGER` con FK real a `tenants.id` (PK)
- Tabla `users` usa `tenant_id VARCHAR` sin constraint FK, referencia lógica a `tenants.tenant_id` (slug)
- Razón: flexibilidad para tenant_id null y evitar constraint cascade en multi-tenancy flexible

Motivación de diseño:
- Multi-tenancy lógico vía slug `tenant_id` legible ("hotel-abc") en `users.tenant_id` y `tenants.tenant_id`.
- Resolución dinámica de tenant mediante identificadores normalizados (teléfono E.164, email) en `tenant_user_identifiers`.
- Auditoría de locks de Redis en `lock_audit` para trazabilidad de concurrencia.
- Historial de passwords para prevenir reutilización.
- Tracking de sesiones JWT (JTI) para revocación manual.

---

## 3) Conexión a Supabase (Pooler + SSL)

Requisitos de conexión:
- Usar Connection Pooler (PgBouncer modo Transaction), puerto 6543.
- SSL obligatorio: `?sslmode=require` en el connection string.

Formato de `DATABASE_URL` (actualizado 2025-11):
```
postgresql://postgres.<PROJECT-REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:6543/postgres?sslmode=require
```

**Nota sobre formato del pooler**: Supabase usa `aws-0-[region]` (con cero, no uno). Ejemplo para us-east-1:
- Correcto: `aws-0-us-east-1.pooler.supabase.com:6543`
- Incorrecto: `aws-1-us-east-1.pooler.supabase.com:6543` (formato antiguo/incorrecto)
- Verifica el endpoint exacto en tu Dashboard → Project Settings → Database → Connection Pooling

El backend convierte automáticamente a `asyncpg` si recibe `postgresql://...` (ver `app/core/settings.py`).

Variables relevantes en `.env` (raíz `agente-hotel-api/`):
- `DATABASE_URL` (recomendada, con `sslmode=require`)
- Opcionalmente: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (el settings construye la URL)

Nota sobre desarrollo local y diagnósticos: existe un modo de conexión “inseguro” para facilitar pruebas puntuales sin verificación SSL. Este modo está bloqueado en CI/producción y requiere confirmación interactiva.
- Script que soporta el modo inseguro: `scripts/test_supabase_connection.py --insecure`
- Efecto: elimina `sslmode=require` del DSN y conecta con `ssl=False` (solo para diagnóstico local)
- Protección: pide escribir exactamente `YES` antes de continuar; aborta si `CI=true` o `ENVIRONMENT=production`.

---

## 4) DDL Canónico (Single Source of Truth)

El siguiente DDL es la especificación canónica para Supabase Postgres. Debe aplicarse tal cual, en `schema public`. Incluye índices, FKs, triggers y comentarios. Cualquier divergencia debe ser justificada y aprobada.

```sql
-- (BEGIN DDL - Copiado de docs/supabase/schema.sql)
-- ============================================
-- SCHEMA: Agente Hotel API - Supabase Backend
-- ============================================
-- Versión: 1.0.0
-- Fecha: 2025-11-06
-- Descripción: Schema de base de datos para el backend del agente hotelero
--              Incluye autenticación JWT, multi-tenancy y auditoría
--
-- IMPORTANTE:
-- • NO incluye tablas del dominio hotelero (en QloApps PMS)
-- • NO incluye conversation sessions (en Redis con TTL 30min)
-- • NO incluye feature flags (en Redis hash)
-- ============================================

-- ============================================
-- 1. USERS: Autenticación y gestión de usuarios
-- ============================================
-- Propósito: Almacenar usuarios del sistema con autenticación JWT
-- Relaciones: → user_sessions, password_history
-- Índices: username, email, tenant_id

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),

    -- Status y permisos
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,

    -- Multi-tenancy (FK lógica, sin constraint para flexibilidad)
    tenant_id VARCHAR(255),

    -- Gestión de contraseñas
    password_last_changed TIMESTAMP NOT NULL DEFAULT NOW(),
    password_must_change BOOLEAN NOT NULL DEFAULT FALSE,

    -- Auditoría
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);

COMMENT ON TABLE users IS 'Usuarios del sistema con autenticación JWT custom';
COMMENT ON COLUMN users.tenant_id IS 'Referencia lógica a tenants.tenant_id (slug)';
COMMENT ON COLUMN users.password_must_change IS 'Forzar cambio de password en próximo login';

-- ============================================
-- 2. USER_SESSIONS: Tracking de JWT tokens activos
-- ============================================
-- Propósito: Rastrear tokens JWT activos para soporte de logout/revocación
-- Uso: Validar que token no haya sido revocado manualmente
-- Limpieza: Job periódico elimina expired sessions

CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    token_jti VARCHAR(255) UNIQUE NOT NULL,

    -- Ciclo de vida del token
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,

    -- Auditoría de seguridad
    user_agent TEXT,
    ip_address VARCHAR(45),  -- IPv6 compatible (max 45 chars)

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

COMMENT ON TABLE user_sessions IS 'Sesiones JWT activas para soporte de revocación';
COMMENT ON COLUMN user_sessions.token_jti IS 'JWT ID (jti claim) para identificación única';
COMMENT ON COLUMN user_sessions.is_revoked IS 'Marcado true en logout manual o por admin';

-- ============================================
-- 3. PASSWORD_HISTORY: Prevención de reutilización
-- ============================================
-- Propósito: Almacenar últimos N passwords para prevenir reutilización
-- Política: Mantener últimos 5-10 passwords por usuario
-- Limpieza: Eliminar registros antiguos más allá de la política

CREATE TABLE IF NOT EXISTS password_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_password_history_user_id ON password_history(user_id);
CREATE INDEX idx_password_history_created_at ON password_history(created_at);

COMMENT ON TABLE password_history IS 'Historial de contraseñas para prevenir reutilización';
COMMENT ON COLUMN password_history.password_hash IS 'Hash bcrypt del password anterior';

-- ============================================
-- 4. TENANTS: Configuración multi-tenant
-- ============================================
-- Propósito: Configuración por hotel/cliente para aislamiento de datos
-- Identificador: tenant_id (slug legible) es la clave lógica principal
-- Relaciones: ← users (FK lógica), ← tenant_user_identifiers

CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) UNIQUE NOT NULL,  -- Slug: "hotel-abc", "resort-xyz"
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, inactive, suspended

    -- Configuración opcional de horarios de negocio
    business_hours_start INTEGER,  -- Hora en formato 0-23 (ej: 8 = 8am)
    business_hours_end INTEGER,    -- Hora en formato 0-23 (ej: 22 = 10pm)
    business_hours_timezone VARCHAR(50),  -- Ej: "America/Argentina/Buenos_Aires"

    -- Auditoría
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_tenant_id ON tenants(tenant_id);
CREATE INDEX idx_tenants_status ON tenants(status);

COMMENT ON TABLE tenants IS 'Configuración multi-tenant (por hotel/cliente)';
COMMENT ON COLUMN tenants.tenant_id IS 'Slug legible usado en código como clave lógica principal (ej: "hotel-abc")';
COMMENT ON COLUMN tenants.id IS 'PK numérica autoincrementada (usada en FKs de tenant_user_identifiers)';
COMMENT ON COLUMN tenants.business_hours_start IS 'Hora de inicio (0-23), NULL = 24/7';

-- ============================================
-- 5. TENANT_USER_IDENTIFIERS: Mapeo dinámico
-- ============================================
-- Propósito: Resolver teléfonos/emails → tenant_id automáticamente
-- Caso de uso: WhatsApp +54911xxxx → detectar tenant "hotel-abc"
-- Unicidad: identifier debe ser único (un phone/email → un tenant)
-- IMPORTANTE: tenant_id aquí es INTEGER FK a tenants.id (PK numérica), NO al slug tenant_id

CREATE TABLE IF NOT EXISTS tenant_user_identifiers (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    identifier VARCHAR(255) NOT NULL,  -- phone: +54911xxxx, email: guest@example.com
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_identifier UNIQUE (identifier)
);

CREATE INDEX idx_tenant_identifiers_tenant_id ON tenant_user_identifiers(tenant_id);
CREATE INDEX idx_tenant_identifiers_identifier ON tenant_user_identifiers(identifier);

COMMENT ON TABLE tenant_user_identifiers IS 'Mapeo phone/email → tenant para resolución dinámica';
COMMENT ON COLUMN tenant_user_identifiers.identifier IS 'Formato normalizado: E.164 para phones';
COMMENT ON CONSTRAINT uq_identifier ON tenant_user_identifiers IS 'Un identifier solo puede pertenecer a un tenant';

-- ============================================
-- 6. LOCK_AUDIT: Auditoría de locks distribuidos
-- ============================================
-- Propósito: Trazabilidad de locks Redis para debugging y análisis
-- Eventos: acquired, extended, released, expired
-- Uso: Investigar deadlocks, contention, errores de locks

CREATE TABLE IF NOT EXISTS lock_audit (
    id SERIAL PRIMARY KEY,
    lock_key VARCHAR(255) NOT NULL,  -- Ej: "reservation:guest123"
    event_type VARCHAR(50) NOT NULL,  -- acquired, extended, released, expired
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    details JSONB  -- Metadata: holder_id, ttl, reason, stack_trace
);

CREATE INDEX idx_lock_audit_lock_key ON lock_audit(lock_key);
CREATE INDEX idx_lock_audit_timestamp ON lock_audit(timestamp);
CREATE INDEX idx_lock_audit_event_type ON lock_audit(event_type);

COMMENT ON TABLE lock_audit IS 'Auditoría de locks distribuidos Redis para debugging';
COMMENT ON COLUMN lock_audit.details IS 'JSON: {"holder_id": "worker-1", "ttl": 30, "reason": "timeout"}';

-- ============================================
-- TRIGGERS: Auto-actualización de updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON FUNCTION update_updated_at_column() IS 'Actualiza automáticamente updated_at en UPDATEs';

-- ============================================
-- ROLES Y PERMISOS (Opcional pero recomendado)
-- ============================================
-- Crear rol específico para el backend (más seguro que usar postgres superuser)

-- NOTA: Ejecutar solo si deseas crear un rol dedicado
-- Si usas el usuario postgres default de Supabase, omitir esta sección

/*
CREATE ROLE agente_backend WITH LOGIN PASSWORD 'CAMBIAR-EN-PRODUCCION';

GRANT CONNECT ON DATABASE postgres TO agente_backend;
GRANT USAGE ON SCHEMA public TO agente_backend;

-- Permisos en tablas existentes
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agente_backend;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agente_backend;

-- Permisos en tablas futuras (auto-grant)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agente_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO agente_backend;

COMMENT ON ROLE agente_backend IS 'Rol dedicado para Agente Hotel API backend';
*/

-- ============================================
-- DATOS DE EJEMPLO (Development/Testing)
-- ============================================
-- Solo para ambientes de desarrollo/staging
-- NO ejecutar en producción con datos reales

/*
-- Tenant de ejemplo
INSERT INTO tenants (tenant_id, name, status, business_hours_start, business_hours_end, business_hours_timezone)
VALUES
    ('hotel-demo', 'Hotel Demo', 'active', 8, 22, 'America/Argentina/Buenos_Aires'),
    ('resort-test', 'Resort Test', 'active', 0, 23, 'UTC')
ON CONFLICT (tenant_id) DO NOTHING;

-- Identificadores de ejemplo
INSERT INTO tenant_user_identifiers (tenant_id, identifier)
SELECT t.id, '+5491112345678'
FROM tenants t WHERE t.tenant_id = 'hotel-demo'
ON CONFLICT (identifier) DO NOTHING;

-- Usuario admin de ejemplo (password: "admin123" hasheado con bcrypt)
-- CAMBIAR PASSWORD EN PRODUCCIÓN
INSERT INTO users (id, username, email, hashed_password, full_name, is_active, is_superuser, tenant_id)
VALUES (
    'usr_admin_demo',
    'admin',
    'admin@hotel-demo.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYL5obAJ5EK',  -- "admin123"
    'Administrator',
    TRUE,
    TRUE,
    'hotel-demo'
)
ON CONFLICT (id) DO NOTHING;
*/

-- ============================================
-- VALIDACIONES POST-DEPLOYMENT
-- ============================================
-- Ejecutar después de aplicar el schema para verificar integridad

-- Verificar tablas creadas
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Verificar índices
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Verificar foreign keys
SELECT
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- ============================================
-- FIN DEL SCHEMA
-- ============================================
-- (END DDL)
```

---

## 5) Automatización disponible en el repo

Ubicación: `agente-hotel-api/`

- Scripts:
  - `scripts/test_supabase_connection.py`: prueba de conectividad con `SELECT version()` usando asyncpg. Flags: `--insecure` (solo DEV; requiere confirmación; bloqueado en CI/PRD).
  - `scripts/apply_supabase_schema.py`: aplica `docs/supabase/schema.sql` de forma transaccional; parser seguro que respeta strings/comentarios/dollar-quoted; genera log en `logs/`.
  - `scripts/validate_supabase_schema.py`: verifica tablas esperadas e índices por tabla. Normaliza SSL para Supabase automáticamente (quita `sslmode` y usa `ssl=True`).
  - `scripts/seed_supabase_minimal.py`: seed idempotente para crear/actualizar un tenant y (opcional) un usuario admin. Flags: `--skip-admin`, `--force-password`, `--update-if-exists`.

- Makefile targets:
  - `make supabase-test-connection`
  - `make supabase-apply-schema`
  - `make supabase-validate`
  - (opcional) seed: usar el workflow `Supabase Schema Ops` con `confirm_seed=true` y el secreto `SUPABASE_ADMIN_PASSWORD` configurado.

Requisito común: `DATABASE_URL` definido (pooler 6543 + `sslmode=require`).

---

## 6) Proceso de Ejecución (para el LLM)

Objetivo: Aplicar y validar el schema en un proyecto Supabase dado, sin romper nada existente.

Checklist previo:
1. Confirmar que `DATABASE_URL` apunta al pooler (puerto 6543) y contiene `?sslmode=require`.
2. Confirmar credenciales válidas (usuario `postgres.<PROJECT-REF>` y password del proyecto).
3. No ejecutar datos de ejemplo en producción.

Pasos:
1) Probar conexión
   - Ejecutar: `make supabase-test-connection`
  - Éxito: imprime versión de Postgres. Error: revisar host/puerto/SSL.
  - Solo si falla por SSL en un entorno de desarrollo y necesitas diagnosticar: puedes ejecutar el script directamente con `--insecure` (te pedirá confirmar escribiendo `YES`; bloqueado en CI/PRD):
    - `python scripts/test_supabase_connection.py --insecure`

2) Aplicar schema
   - Ejecutar: `make supabase-apply-schema`
   - Resultado: transacción única; si un statement falla → rollback; revisar estado impreso y log.

3) Validar schema
   - Ejecutar: `make supabase-validate`
   - Resultado: lista de tablas encontradas y sus índices; comparar contra el set esperado de 6 tablas.

4) (Opcional) Seed mínimo (tenant + admin)
  - Ejecutar el workflow "Supabase Schema Ops" con `confirm_seed=true`.
  - Requisitos: definir en GitHub Secrets `SUPABASE_ADMIN_PASSWORD` (no usar inputs).
  - El seed es idempotente y permite `--update-if-exists` para actualizar el nombre del tenant si ya existe.

5) (Opcional) Crear rol dedicado mínimo
   - Evaluar sección “ROLES Y PERMISOS” en el DDL (bloque comentado) y ejecutarlo si se desea endurecer permisos.

6) (Opcional) Datos de ejemplo para DEV/STG
   - Bloque “DATOS DE EJEMPLO” (comentado). No usar en producción.

7) Entregar evidencia
   - Adjuntar logs de `apply_supabase_schema.py` y salida de `supabase-validate`.

Éxito = todas las tablas creadas/validadas, sin errores; conexión y validaciones OK.

---

## 7) Seguridad y Guardrails

- Conexión cifrada (SSL): obligatorio `?sslmode=require`.
- No usar Supabase Auth; todo acceso desde backend con JWT custom.
- No crear ni tocar tablas del dominio hotelero (QloApps PMS las gestiona).
- No crear `sessions` ni `feature_flags` en Postgres; residen en Redis.
- Ajustar pool de conexiones según entorno (ver README Supabase existente):
  - DEV: `POSTGRES_POOL_SIZE=5`, `POSTGRES_MAX_OVERFLOW=5`
  - STG: `10/10`
  - PRD: `10/5` por réplica backend
- Opcional: role `agente_backend` para mínimo privilegio.
- **Validación de secrets en producción**: El código valida automáticamente que secrets (API keys, JWT secret_key, etc.) no usen valores dummy en `ENVIRONMENT=production`. Ver `app/core/settings.py:validate_secrets_in_prod()`. Los secrets deben tener mínimo 8 caracteres y no estar en lista de dummy values ("dev-", "test", "changeme", etc.).
- Secretos nunca en Git; usar `.env` local seguro y gitleaks en CI.
- **Timezone del servidor**: El backend usa `datetime.now(UTC)` pero el DDL usa `NOW()` sin especificar timezone. Recomendación: verificar que el servidor Postgres esté configurado en UTC o ajustar explícitamente con `SET timezone = 'UTC';` en script de inicialización si es necesario.

---

## 8) Costos y Control de Consumo

- Usar siempre el Pooler (6543) para evitar conexión directa (más costosa y limitada).
- Reducir `POOL_SIZE` en entornos pequeños para no agotar el límite de conexiones.
- Evitar consultas pesadas; tablas aquí son ligeras (auth/tenancy/audit), no reporting.
- Sin Fly.io: no hay costos de compute asociados a fly; sólo DB (Supabase) + egress si aplica.

---

## 9) Troubleshooting rápido

- "password authentication failed": revisar usuario `postgres.<PROJECT-REF>` y password.
- "connection refused/timeout": confirmar host del pooler (`aws-0-<region>.pooler.supabase.com`) y puerto 6543.
- "SSL connection closed": agregar `?sslmode=require`.
  - En DEV, si necesitas confirmar que el problema es únicamente SSL, usa temporalmente `python scripts/test_supabase_connection.py --insecure` (confirmación requerida; no disponible en CI/PRD) y corrige tu `DATABASE_URL` después.
- "relation 'users' does not exist": schema no aplicado o search_path distinto de `public`.
- "too many connections": bajar pool sizes.
- "timezone mismatch warnings": verificar que servidor Postgres use UTC o ajustar con `SET timezone = 'UTC';`

Consultas útiles (ya incluidas al final del DDL):
- Listado de tablas en `public`.
- Índices por tabla (`pg_indexes`).
- Foreign keys (`information_schema`).
- Verificar timezone del servidor: `SHOW timezone;`

---

## 10) Criterios de Aceptación (Definition of Done)

1. `make supabase-test-connection` → OK (versión Postgres impresa).
2. `make supabase-apply-schema` → OK (sin errores; log generado en `logs/`).
3. `make supabase-validate` → Reporta exactamente las 6 tablas esperadas; índices presentes.
4. (Opcional) Rol `agente_backend` creado y con permisos mínimos.
5. (Opcional DEV/STG) Datos de ejemplo insertados; no en producción.
6. Documentar: `DATABASE_URL` (sin exponer password en texto plano público).

---

## 11) Apéndices

### A. Ubicaciones relevantes en el repositorio

- `docs/supabase/schema.sql` → DDL canónico (idéntico al incluido en este documento).
- `docs/supabase/README.md` → Guía operativa ampliada y FAQ.
- `docs/supabase/EXECUTION-PLAN.md` → Blueprint y checklist detallada por fases.
- `scripts/test_supabase_connection.py` → Conectividad.
- `scripts/apply_supabase_schema.py` → Aplicación transaccional del schema.
- `scripts/validate_supabase_schema.py` → Validación post-deploy.
- `Makefile` → Targets `supabase-*`.

### B. Convenciones y límites

- Esquema: `public`.
- Nombres de tablas/índices como en el DDL.
- Campos `created_at/updated_at` con `NOW()` y triggers para actualización.
- Codificación UTF-8; timestamps con zona según servidor (UTC recomendado, verificar con `SHOW timezone;`).
- **Relaciones multi-tenant**: 
  - `users.tenant_id` (VARCHAR) es FK lógica sin constraint a `tenants.tenant_id` (slug)
  - `tenant_user_identifiers.tenant_id` (INTEGER) es FK real con constraint a `tenants.id` (PK)
  - Esta dualidad permite flexibilidad en multi-tenancy sin cascade estricto en users

---

## 12) Monitoreo y Observabilidad

Objetivo: detectar problemas antes de que impacten al usuario y validar salud del servicio.

- Conexiones activas (PgBouncer/Pooler):
  - Dashboard Supabase → Database → Connection Pooling
  - SQL rápido: `SELECT count(*) FROM pg_stat_activity;`
- Métricas Prometheus (stack del proyecto):
  - `postgres_connections_active` (uso del pool)
  - `postgres_query_duration_seconds` (latencia)
  - `postgres_errors_total` (errores de conexión)
  - Dashboards en `docker/grafana/` (ver README-Infra.md)
- Trazas (Jaeger): correlación por `X-Request-ID` desde FastAPI.
- Alertas (Alertmanager):
  - Umbrales sugeridos: conexiones > 80% por >5m; P95 query > 150ms por >10m.

Buenas prácticas:
- Mantener P95 de queries < 50-100ms (estas tablas son livianas).
- Evitar cardinalidad explosiva en métricas (labels controlados).

---

## 13) Mantenimiento Periódico

Limpieza recomendada (agregar como job diario/semanal según volumen):

```sql
-- 1) Eliminar user_sessions expiradas (ejecutar diariamente)
DELETE FROM user_sessions 
WHERE expires_at < NOW() - INTERVAL '7 days';

-- 2) Mantener solo los últimos 10 passwords por usuario
DELETE FROM password_history 
WHERE id NOT IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
        FROM password_history
    ) sub WHERE rn <= 10
);

-- 3) Limpiar lock_audit (mantener 30 días)
DELETE FROM lock_audit 
WHERE timestamp < NOW() - INTERVAL '30 days';
```

Notas:
- Supabase usa autovacuum; no obstante, monitorear bloat si el volumen crece.
- Programar con cron o un scheduler del backend (según políticas).

---

## 14) Migración de Datos

Si existe una base local con datos que migrar a Supabase:

- Opción A (recomendada): `pg_dump` + `psql` (data-only)
  ```bash
  # Export desde local
  pg_dump -h localhost -U postgres -d postgres --schema=public --data-only > data.sql

  # Import a Supabase (usar pooler + SSL)
  psql "postgresql://postgres.<PROJECT-REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:6543/postgres?sslmode=require" < data.sql
  ```

- Opción B: Script Python dedicado (útil para transformaciones)
  - Crear `scripts/migrate_to_supabase.py` (si se requiere) usando `asyncpg`.

Validación post-migración:
- Conteo de filas por tabla, checks básicos de integridad, y consultas de muestra.

---

## 15) Disaster Recovery

- Backups automáticos (Supabase):
  - Free: 7 días de retención
  - Pro: 30 días + Point-in-Time Recovery (PITR)
- Procedimiento (alto nivel):
  1. Identificar backup o punto en el tiempo.
  2. Restaurar a un proyecto base de prueba (staging) para verificar.
  3. Validar integridad con `scripts/validate_supabase_schema.py`.
  4. Ejecutar smoke tests del backend.
- Objetivos operativos (sugeridos):
  - RTO ≤ 2h, RPO ≤ 15min (ajustar según tier y negocio).

---

## 16) Performance y Optimización

- Índices: ya definidos en DDL; añadir nuevos solo con evidencia (EXPLAIN ANALYZE).
- Pooling: usar modo Transaction (requerido por `asyncpg`); evitar Session mode.
- Tamaño del pool:
  - DEV: 5/5
  - STG: 10/10
  - PRD: 10/5 por réplica backend (ajustar a límites del tier)
- Prepared statements: `asyncpg` los gestiona eficientemente; evitar concatenar SQL.
- Consultas: pedir columnas necesarias (no `SELECT *`) para minimizar I/O.

---

## 17) Integración con Backend

Conexión y ORM:
- `app/core/database.py` crea `engine` con `create_async_engine` y configura pool/echo/pre-ping.
- `app/core/settings.py` convierte automáticamente `postgresql://` → `postgresql+asyncpg://`.
- Dependencia de sesión: `get_db()` usando `AsyncSessionFactory` (SQLAlchemy 2.x).

Tenancy dinámico:
- `DynamicTenantService` precarga `Tenant` + `TenantUserIdentifier` y expone `resolve_tenant()`.
- En bootstrap hace `Base.metadata.create_all()` para facilitar DEV; en PRD preferir migraciones controladas.

Locks y auditoría:
- `LockService` usa Redis para locks; la tabla `lock_audit` sirve para trazabilidad (inserciones opcionales vía capa de servicio cuando se considere necesario).

Testing:
- Unit tests: SQLite en memoria (rápidos, sin Postgres real).
- Integración: pueden apuntar a Supabase si `DATABASE_URL` está presente.

Ejemplos (pseudo-código):
```python
# Crear tenant (ORM)
tenant = Tenant(tenant_id="hotel-demo", name="Hotel Demo")
session.add(tenant)
await session.commit()

# Resolver tenant por identificador
tid = dynamic_tenant_service.resolve_tenant("+5491112345678")

# Registrar auditoría (si se instrumenta desde backend)
await session.execute(
    text("INSERT INTO lock_audit(lock_key, event_type, details) VALUES (:k, :e, :d)"),
    {"k": "lock:room:101:2025-01-01:2025-01-05", "e": "acquired", "d": json.dumps({"ttl": 600})}
)
await session.commit()
```

---

## 18) FAQ Avanzado

- ¿Alembic o Supabase CLI?
  - Proyecto incluye `alembic/`, pero para este scope el DDL canónico + scripts automatizados son suficientes.
  - Si se habilitan migraciones continuas, elegir una sola vía y estandarizar (Alembic recomendado en backend Python; Supabase CLI si se desea homogeneidad infra-first).
- ¿Por qué no RLS?
  - Acceso solo desde backend con credenciales de servicio; permisos y multi-tenancy se controlan en la aplicación.
- Multi-región / latencia:
  - Elegir región cercana a usuarios y al backend; validar P95 de consultas tras desplegar.
- Escalado:
  - Aumentar tier en Supabase, optimizar pool, revisar índices y consultas.

---

## 19) Glosario de Términos

- FK lógica: referencia sin constraint (p. ej., `users.tenant_id` → `tenants.tenant_id` slug).
- FK real: constraint de base de datos (p. ej., `tenant_user_identifiers.tenant_id` → `tenants.id`).
- Pooler: proxy PgBouncer gestionado por Supabase (puerto 6543, modo Transaction).
- Transaction vs Session mode: en Transaction cada checkout es por statement/tx; `asyncpg` requiere Transaction.
- Tenant slug: identificador legible único (`tenants.tenant_id`).

---

## 20) Quick Reference

Comandos Make:
- `make supabase-test-connection`
- `make supabase-apply-schema`
- `make supabase-validate`

Scripts:
- `scripts/test_supabase_connection.py`
- `scripts/apply_supabase_schema.py`
- `scripts/validate_supabase_schema.py`

Ejemplos rápidos:
- Test estándar: `python scripts/test_supabase_connection.py`
- Test (solo diagnóstico local) sin verificación SSL: `python scripts/test_supabase_connection.py --insecure`

SQL útiles:
- Tablas en public: ver sección “VALIDACIONES POST-DEPLOYMENT” del DDL.
- Conexiones activas: `SELECT count(*) FROM pg_stat_activity;`
- Timezone del servidor: `SHOW timezone;`

Ubicaciones de dashboards/monitoreo:
- Grafana: `docker/grafana/` (ver README-Infra.md)
- Jaeger: puerto 16686 (tracing)

---

Fin del documento.

---

## Anexo: Correcciones, Simplificación y Recomendaciones (Añadido 2025-11-07)

Este anexo sintetiza hallazgos tras revisar un plan externo más extenso. Objetivo: mantener experiencia sencilla para administrador/dueño del hotel, evitando complejidad innecesaria y reduciendo riesgo operativo.

### 1. Ajustes de Exactitud Técnica

- Función `ssl_is_used()` mencionada en algunos planes externos NO es estándar de PostgreSQL. Para verificar SSL usar:
  ```sql
  SELECT ssl, ssl_version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid();
  ```
- Scripts de creación de rol externo usaban `:'app_password'` sin previo `\set app_password`; reemplazar por interpolación shell segura. Ejemplo:
  ```bash
  APP_USER_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
  psql "$DATABASE_URL" -v app_password="$APP_USER_PASSWORD" -c "CREATE ROLE agente_hotel_app WITH LOGIN PASSWORD :'app_password';"
  ```
- Rollback total que hace `DROP SCHEMA public CASCADE` es demasiado destructivo para PRD. Recomendación: restaurar a base temporal y hacer cut‑over (renombrar DB o actualizar `DATABASE_URL`) tras validación.
- RLS: El plan externo propone múltiples políticas. Actualmente el backend aplica multi-tenancy lógico en código (slug). Activar RLS solo si se requiere defensa en profundidad; caso contrario mantiene simplicidad operativa. Si se habilita, documentar claramente los GUC: `SET LOCAL app.current_tenant_id = 'hotel-demo';`.
- Métrica de sesiones activas ya integrada (`jwt_sessions_active`). Evitar duplicar contadores en nuevos scripts ad-hoc.
- Alerta de sesiones expiradas masivas >1000 no aplica (volumen actual bajo). Ajustar umbral tras obtener base line real (observación primero, alerta después).

### 2. Reducción de Complejidad (Mantenerlo Simple)

- Mantener solo tres comandos para operación diaria:
  1. `make supabase-test-connection`
  2. `make supabase-validate`
  3. `make maintenance-cleanup` (cuando el volumen de sesiones crezca)
- Postergar implementación de plan de RLS completo hasta que exista necesidad regulatoria o auditoría externa.
- Unificar scripts de mantenimiento: usar el ya existente de limpieza de sesiones y evitar múltiples variantes.
- Evitar crear nuevos dashboards si los paneles actuales cubren: conexiones, latencia, timeouts y sesiones.

### 3. Seguridad Pragmatista

- Priorizar rotación del `JWT_SECRET_KEY` y verificación de longitud > 64 antes de crear usuario dedicado.
- Si se crea rol dedicado, aplicar principio de menor privilegio pero validar primero que todas operaciones del backend (migraciones internas, seeds) funcionen bajo el rol.
- Añadir chequeo opcional (no bloqueante) para detectar passwords débiles en `DATABASE_URL` (< 20 chars) durante arranque en DEV para educación del usuario.

### 4. Costos y Pool de Conexiones

- Mantener configuración actual de timeouts (`statement_timeout=15s`) y no reducir más (evita falsa sensación de velocidad y aumenta riesgo de abortar operaciones legítimas).
- Re-evaluar `POSTGRES_POOL_SIZE` una vez que concurrency real > 30 req/min sostenidos. Hasta entonces no escalar.

### 5. Observabilidad Ajustada

- Ya existe contador `db_statement_timeouts_total` y alerta `StatementTimeoutsPresent`. No añadir segunda alerta para mismo evento.
- Incorporar en dashboard ratio simple: `increase(db_statement_timeouts_total[1h])` vs total queries para ver tendencia sin saturar Alertmanager.

### 6. Rollback Seguro (Recomendación Actualizada)

Procedimiento sugerido en caso de corrupción severa:
1. Crear nueva base temporal en Supabase (proyecto clon o restauración PITR aislada).
2. Aplicar `schema.sql` y validar con `make supabase-validate`.
3. Importar datos críticos (usuarios y tenants) con script selectivo.
4. Cambiar variables de entorno / secretos apuntando a nueva DB y hacer smoke tests.
5. Decommission de la base anterior solo tras verificación de 24h.

Evitar borrado directo de `public` en producción.

### 7. Próximos Pasos Propuestos (Orden Prioritario)

1. Aumentar cobertura de tests críticos (orchestrator, pms_adapter, session_manager, lock_service) → objetivo intermedio 55%.
2. Pequeño dashboard “Operación Rápida” (sesiones activas, conexiones, timeouts) para usuario no técnico (panel único Grafana).
3. Script de export consolidado (`scripts/maintenance/export_core_tables.py`) opcional para auditoría manual.
4. Revisar índices redundantes (documentados) sólo si tamaño tablas > 1M filas.
5. Evaluar RLS mínima (solo lectura tenants) si se planea exponer endpoints multi-tenant públicos.

### 8. Flujo Operativo Simplificado para Admin (Resumen)

| Acción | Comando | Resultado | Frecuencia |
|--------|---------|-----------|------------|
| Verificar conexión | `make supabase-test-connection` | Versión y acceso OK | Diario |
| Validar schema | `make supabase-validate` | Tabla/índices integridad | Semanal / Post-deploy |
| Revisar métricas | Grafana Panel “Supabase Básico” | Conexiones / Timeouts / Sesiones | Diario |
| Limpieza sesiones | `make maintenance-cleanup` | Sesiones expiradas eliminadas | Semanal (o volumen) |
| Revisión seguridad | Manual (secrets, roles) | Sin secretos débiles | Mensual |

### 9. Decisiones NO Adoptadas (y por qué)

- RLS completo multi-tabla: deferido (incrementa complejidad y soporte).
- Rollback destructivo (DROP SCHEMA): descartado por riesgo operativo alto.
- Alertas de “ExpiredSessionsAccumulating” con SQL embebido en Prometheus: no compatible directamente y baja prioridad actual.
- Doble instrumentación de métricas de sesiones (evitamos duplicar `active_sessions_total` y `jwt_sessions_active` en panel básico; se usarán ambas para distintos niveles de detalle si fuese necesario).

### 10. Indicadores de Revisión Futura

- Si `db_statement_timeouts_total` > 10 por hora → revisar queries y posibles missing indexes.
- Si `db_connections_active` sostenido > 70% del máximo → evaluar ajustar pool o optimizar sesiones.
- Si `jwt_sessions_active` crece > 50 y limpiezas semanales eliminan < 5% → revisar política de expiración.

---

Fin del anexo.
