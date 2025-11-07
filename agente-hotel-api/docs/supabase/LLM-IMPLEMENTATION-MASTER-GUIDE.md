# LLM Implementation Master Guide — Supabase (SIST_AGENTICO_HOTELERO)

Versión: 1.0.0  
Fecha: 2025-11-07  
Estado: Listo para Ejecución Operativa (100% autosuficiente)

Nota operativa: La plataforma Fly.io ha sido dada de baja. No hay dependencias activas con Fly.io. Este documento se centra exclusivamente en la plataforma de base de datos gestionada (Supabase Postgres) para el proyecto.

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

Relaciones clave:
- user_sessions.user_id → users.id (FK)
- password_history.user_id → users.id (FK)
- tenant_user_identifiers.tenant_id → tenants.id (FK)

Motivación de diseño:
- Multi-tenancy lógico vía `tenant_id` (slug legible) en `users` y tabla `tenants` para configuración.
- Resolución dinámica de tenant mediante identificadores normalizados (teléfono E.164, email) en `tenant_user_identifiers`.
- Auditoría de locks de Redis en `lock_audit` para trazabilidad de concurrencia.
- Historial de passwords para prevenir reutilización.
- Tracking de sesiones JWT (JTI) para revocación manual.

---

## 3) Conexión a Supabase (Pooler + SSL)

Requisitos de conexión:
- Usar Connection Pooler (PgBouncer modo Transaction), puerto 6543.
- SSL obligatorio: `?sslmode=require` en el connection string.

Formato de `DATABASE_URL`:
```
postgresql://postgres.<PROJECT-REF>:<PASSWORD>@<REGION>.pooler.supabase.com:6543/postgres?sslmode=require
```

El backend convierte automáticamente a `asyncpg` si recibe `postgresql://...` (ver `app/core/settings.py`).

Variables relevantes en `.env` (raíz `agente-hotel-api/`):
- `DATABASE_URL` (recomendada, con `sslmode=require`)
- Opcionalmente: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (el settings construye la URL)

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
COMMENT ON COLUMN tenants.tenant_id IS 'Slug legible usado en código (clave lógica principal)';
COMMENT ON COLUMN tenants.business_hours_start IS 'Hora de inicio (0-23), NULL = 24/7';

-- ============================================
-- 5. TENANT_USER_IDENTIFIERS: Mapeo dinámico
-- ============================================
-- Propósito: Resolver teléfonos/emails → tenant_id automáticamente
-- Caso de uso: WhatsApp +54911xxxx → detectar tenant "hotel-abc"
-- Unicidad: identifier debe ser único (un phone/email → un tenant)

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
  - `scripts/test_supabase_connection.py`: prueba de conectividad con `SELECT version()` usando asyncpg.
  - `scripts/apply_supabase_schema.py`: aplica `docs/supabase/schema.sql` de forma transaccional; parser seguro que respeta strings/comentarios/dollar-quoted; genera log en `logs/`.
  - `scripts/validate_supabase_schema.py`: verifica tablas esperadas e índices por tabla.

- Makefile targets:
  - `make supabase-test-connection`
  - `make supabase-apply-schema`
  - `make supabase-validate`

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

2) Aplicar schema
   - Ejecutar: `make supabase-apply-schema`
   - Resultado: transacción única; si un statement falla → rollback; revisar estado impreso y log.

3) Validar schema
   - Ejecutar: `make supabase-validate`
   - Resultado: lista de tablas encontradas y sus índices; comparar contra el set esperado de 6 tablas.

4) (Opcional) Crear rol dedicado mínimo
   - Evaluar sección “ROLES Y PERMISOS” en el DDL (bloque comentado) y ejecutarlo si se desea endurecer permisos.

5) (Opcional) Datos de ejemplo para DEV/STG
   - Bloque “DATOS DE EJEMPLO” (comentado). No usar en producción.

6) Entregar evidencia
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
- Secretos nunca en Git; usar `.env` local seguro y gitleaks en CI.

---

## 8) Costos y Control de Consumo

- Usar siempre el Pooler (6543) para evitar conexión directa (más costosa y limitada).
- Reducir `POOL_SIZE` en entornos pequeños para no agotar el límite de conexiones.
- Evitar consultas pesadas; tablas aquí son ligeras (auth/tenancy/audit), no reporting.
- Sin Fly.io: no hay costos de compute asociados a fly; sólo DB (Supabase) + egress si aplica.

---

## 9) Troubleshooting rápido

- “password authentication failed”: revisar usuario `postgres.<PROJECT-REF>` y password.
- “connection refused/timeout”: confirmar host del pooler y puerto 6543.
- “SSL connection closed”: agregar `?sslmode=require`.
- “relation 'users' does not exist”: schema no aplicado o search_path distinto de `public`.
- “too many connections”: bajar pool sizes.

Consultas útiles (ya incluidas al final del DDL):
- Listado de tablas en `public`.
- Índices por tabla (`pg_indexes`).
- Foreign keys (`information_schema`).

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
- Codificación UTF-8; timestamps con zona según servidor (UTC recomendado).

---

Fin del documento.
