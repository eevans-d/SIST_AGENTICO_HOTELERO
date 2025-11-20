-- Supabase Schema for Agente Hotel API
-- Version: 3.0.0 - Ultra Simple
-- Date: 2025-11-20

-- Table 1: Tenants
CREATE TABLE tenants (id BIGSERIAL PRIMARY KEY, tenant_id VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(255) NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'active', metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE INDEX IF NOT EXISTS idx_tenants_tenant_id ON tenants(tenant_id);

CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

-- Table 2: Tenant User Identifiers
CREATE TABLE tenant_user_identifiers (id BIGSERIAL PRIMARY KEY, tenant_id VARCHAR(255) NOT NULL, identifier_type VARCHAR(50) NOT NULL, identifier_value VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE, UNIQUE (identifier_type, identifier_value));

CREATE INDEX IF NOT EXISTS idx_tenant_identifiers_tenant ON tenant_user_identifiers(tenant_id);

CREATE INDEX IF NOT EXISTS idx_tenant_identifiers_type_value ON tenant_user_identifiers(identifier_type, identifier_value);

-- Table 3: Audit Logs
CREATE TABLE audit_logs (id BIGSERIAL PRIMARY KEY, user_id UUID, tenant_id VARCHAR(255), action VARCHAR(100) NOT NULL, resource_type VARCHAR(100), resource_id VARCHAR(255), details JSONB DEFAULT '{}', ip_address INET, user_agent TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Table 4: Lock Audit
CREATE TABLE lock_audit (id BIGSERIAL PRIMARY KEY, lock_key VARCHAR(255) NOT NULL, operation VARCHAR(50) NOT NULL, success BOOLEAN NOT NULL, holder_id VARCHAR(255), ttl_seconds INTEGER, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE INDEX IF NOT EXISTS idx_lock_audit_lock_key ON lock_audit(lock_key);

CREATE INDEX IF NOT EXISTS idx_lock_audit_created_at ON lock_audit(created_at);

-- Enable RLS
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

ALTER TABLE tenant_user_identifiers ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE lock_audit ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Allow authenticated read tenants" ON tenants FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated read identifiers" ON tenant_user_identifiers FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated insert audit_logs" ON audit_logs FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated read own audit_logs" ON audit_logs FOR SELECT TO authenticated USING (user_id = auth.uid());
