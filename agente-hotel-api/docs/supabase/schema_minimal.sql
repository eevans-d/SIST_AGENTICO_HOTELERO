-- ============================================
-- SCHEMA MINIMAL: Agente Hotel API - Supabase Backend
-- ============================================
-- Versión: 2.0.0 (Compatible con Supabase Auth)
-- Fecha: 2025-11-20
-- Descripción: Schema minimalista compatible con auth.users de Supabase
--
-- IMPORTANTE:
-- • USA auth.users de Supabase (NO crea tabla users propia)
-- • Solo incluye tablas específicas del proyecto
-- • Compatible con Row Level Security (RLS)
-- ============================================

-- ============================================
-- 1. TENANTS: Multi-tenancy support
-- ============================================
CREATE TABLE tenants (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
;

CREATE INDEX IF NOT EXISTS idx_tenants_tenant_id ON tenants(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

COMMENT ON TABLE tenants IS 'Organizaciones/clientes del sistema (multi-tenancy)';
COMMENT ON COLUMN tenants.tenant_id IS 'Identificador único del tenant (slug)';

-- ============================================
-- 2. TENANT_USER_IDENTIFIERS: Mapeo user → tenant
-- ============================================
CREATE TABLE tenant_user_identifiers (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    identifier_type VARCHAR(50) NOT NULL,
    identifier_value VARCHAR(255) NOT NULL,
    
    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE (identifier_type, identifier_value)
)
;

CREATE INDEX IF NOT EXISTS idx_tenant_identifiers_tenant ON tenant_user_identifiers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_identifiers_type_value ON tenant_user_identifiers(identifier_type, identifier_value);

COMMENT ON TABLE tenant_user_identifiers IS 'Identifica a qué tenant pertenece cada usuario (email, phone, etc.)';

-- ============================================
-- 3. AUDIT_LOGS: Registro de auditoría
-- ============================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,  -- Referencia a auth.users(id) de Supabase
    tenant_id VARCHAR(255),
    
    -- Acción realizada
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    
    -- Detalles
    details JSONB DEFAULT '{}',
    
    -- Metadatos de solicitud
    ip_address INET,
    user_agent TEXT,
    
    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

COMMENT ON TABLE audit_logs IS 'Registro de auditoría de acciones del sistema';
COMMENT ON COLUMN audit_logs.user_id IS 'Referencia a auth.users de Supabase';

-- ============================================
-- 4. LOCK_AUDIT: Auditoría de locks distribuidos
-- ============================================
CREATE TABLE lock_audit (
    id BIGSERIAL PRIMARY KEY,
    lock_key VARCHAR(255) NOT NULL,
    
    -- Estado del lock
    operation VARCHAR(50) NOT NULL,  -- 'acquire', 'release', 'timeout'
    success BOOLEAN NOT NULL,
    
    -- Metadata
    holder_id VARCHAR(255),
    ttl_seconds INTEGER,
    
    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
;

CREATE INDEX IF NOT EXISTS idx_lock_audit_lock_key ON lock_audit(lock_key);
CREATE INDEX IF NOT EXISTS idx_lock_audit_created_at ON lock_audit(created_at);

COMMENT ON TABLE lock_audit IS 'Auditoría de locks distribuidos (Redis)';

-- ============================================
-- 5. Habilitar Row Level Security (RLS)
-- ============================================
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_user_identifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE lock_audit ENABLE ROW LEVEL SECURITY;

-- Políticas básicas (ajustar según necesidades)
-- Permitir lectura autenticada por defecto
CREATE POLICY "Allow authenticated read tenants" ON tenants
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated read identifiers" ON tenant_user_identifiers
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated insert audit_logs" ON audit_logs
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated read own audit_logs" ON audit_logs
    FOR SELECT TO authenticated USING (user_id = auth.uid());

-- ============================================
-- FIN DEL SCHEMA MINIMAL
-- ============================================
