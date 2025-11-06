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
