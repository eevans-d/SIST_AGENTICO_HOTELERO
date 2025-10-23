-- ════════════════════════════════════════════════════════════════════════════════
-- PostgreSQL Initialization Script for Staging
-- ════════════════════════════════════════════════════════════════════════════════
-- Purpose: Initialize database with staging seed data
-- Generated: 2025-10-23
-- ════════════════════════════════════════════════════════════════════════════════

-- ════════════════════════════════════════════════════════════════════════════════
-- 1. CREATE EXTENSIONS
-- ════════════════════════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ════════════════════════════════════════════════════════════════════════════════
-- 2. CREATE SCHEMAS & TABLES (will be created by SQLAlchemy ORM)
-- ════════════════════════════════════════════════════════════════════════════════
-- Note: SQLAlchemy creates tables via app/core/database.py on startup
-- This script runs BEFORE the app starts, so we just ensure extensions exist

-- ════════════════════════════════════════════════════════════════════════════════
-- 3. CREATE INITIAL DATA (will be loaded via seed scripts)
-- ════════════════════════════════════════════════════════════════════════════════
-- Seed data is loaded after SQLAlchemy creates tables (via scripts/seed_data.py)

-- ════════════════════════════════════════════════════════════════════════════════
-- VERIFICATION
-- ════════════════════════════════════════════════════════════════════════════════
\dt
SELECT version();
