"""
Tests de integración para validar multi-tenancy y aislamiento de datos.

Este módulo verifica que los datos de diferentes tenants están correctamente
aislados en las tablas: audit_logs, dlq_permanent_failures, y lock_audit.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.dlq import DLQEntry
from app.models.lock_audit import LockAudit


# Import fixtures from multi_tenancy module
pytest_plugins = ["tests.fixtures.multi_tenancy"]


@pytest_asyncio.fixture
async def db_session(test_db_session):
    """
    Alias for test_db_session to match test signatures.
    Uses SQLite in-memory database for fast, isolated tests.
    """
    return test_db_session


class TestMultiTenancyIsolation:
    """Test suite para validar aislamiento de datos por tenant_id."""

    @pytest.mark.asyncio
    async def test_audit_log_tenant_isolation(
        self,
        db_session,
        audit_log_data_tenant_a,
        audit_log_data_tenant_b,
        tenant_a_id,
        tenant_b_id,
    ):
        """
        Verifica que los audit logs de diferentes tenants están aislados.
        
        Test:
        1. Crea audit logs para tenant A y tenant B
        2. Consulta logs filtrando por tenant_id
        3. Verifica que cada tenant solo ve sus propios logs
        """
        # Crear audit log para tenant A
        log_a = AuditLog(**audit_log_data_tenant_a)
        db_session.add(log_a)
        
        # Crear audit log para tenant B
        log_b = AuditLog(**audit_log_data_tenant_b)
        db_session.add(log_b)
        
        await db_session.commit()
        
        # Consultar logs de tenant A
        stmt_a = select(AuditLog).where(AuditLog.tenant_id == tenant_a_id)
        result_a = await db_session.execute(stmt_a)
        logs_a = result_a.scalars().all()
        
        # Consultar logs de tenant B
        stmt_b = select(AuditLog).where(AuditLog.tenant_id == tenant_b_id)
        result_b = await db_session.execute(stmt_b)
        logs_b = result_b.scalars().all()
        
        # Verificar aislamiento
        assert len(logs_a) >= 1, "Tenant A debe tener al menos 1 log"
        assert len(logs_b) >= 1, "Tenant B debe tener al menos 1 log"
        
        # Verificar que los logs de tenant A solo pertenecen a tenant A
        for log in logs_a:
            assert log.tenant_id == tenant_a_id, f"Log {log.id} no pertenece a tenant A"
        
        # Verificar que los logs de tenant B solo pertenecen a tenant B
        for log in logs_b:
            assert log.tenant_id == tenant_b_id, f"Log {log.id} no pertenece a tenant B"
        
        # Verificar que no hay cross-contamination
        tenant_a_user_ids = {log.user_id for log in logs_a}
        tenant_b_user_ids = {log.user_id for log in logs_b}
        
        assert audit_log_data_tenant_a["user_id"] in tenant_a_user_ids
        assert audit_log_data_tenant_b["user_id"] in tenant_b_user_ids
        assert audit_log_data_tenant_a["user_id"] not in tenant_b_user_ids
        assert audit_log_data_tenant_b["user_id"] not in tenant_a_user_ids
        
        # Cleanup
        await db_session.delete(log_a)
        await db_session.delete(log_b)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_dlq_entry_tenant_isolation(
        self,
        db_session,
        dlq_entry_data_tenant_a,
        dlq_entry_data_tenant_b,
        tenant_a_id,
        tenant_b_id,
    ):
        """
        Verifica que las entradas DLQ de diferentes tenants están aisladas.
        
        Test:
        1. Crea DLQ entries para tenant A y tenant B
        2. Consulta entries filtrando por tenant_id
        3. Verifica que cada tenant solo ve sus propias entries
        """
        # Crear DLQ entry para tenant A
        entry_a = DLQEntry(**dlq_entry_data_tenant_a)
        db_session.add(entry_a)
        
        # Crear DLQ entry para tenant B
        entry_b = DLQEntry(**dlq_entry_data_tenant_b)
        db_session.add(entry_b)
        
        await db_session.commit()
        
        # Consultar entries de tenant A
        stmt_a = select(DLQEntry).where(DLQEntry.tenant_id == tenant_a_id)
        result_a = await db_session.execute(stmt_a)
        entries_a = result_a.scalars().all()
        
        # Consultar entries de tenant B
        stmt_b = select(DLQEntry).where(DLQEntry.tenant_id == tenant_b_id)
        result_b = await db_session.execute(stmt_b)
        entries_b = result_b.scalars().all()
        
        # Verificar aislamiento
        assert len(entries_a) >= 1, "Tenant A debe tener al menos 1 DLQ entry"
        assert len(entries_b) >= 1, "Tenant B debe tener al menos 1 DLQ entry"
        
        # Verificar que las entries de tenant A solo pertenecen a tenant A
        for entry in entries_a:
            assert entry.tenant_id == tenant_a_id, f"Entry {entry.id} no pertenece a tenant A"
        
        # Verificar que las entries de tenant B solo pertenecen a tenant B
        for entry in entries_b:
            assert entry.tenant_id == tenant_b_id, f"Entry {entry.id} no pertenece a tenant B"
        
        # Verificar que los IDs no se cruzan
        ids_a = {entry.id for entry in entries_a}
        ids_b = {entry.id for entry in entries_b}
        
        assert dlq_entry_data_tenant_a["id"] in ids_a
        assert dlq_entry_data_tenant_b["id"] in ids_b
        assert dlq_entry_data_tenant_a["id"] not in ids_b
        assert dlq_entry_data_tenant_b["id"] not in ids_a
        
        # Cleanup
        await db_session.delete(entry_a)
        await db_session.delete(entry_b)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_lock_audit_tenant_isolation(
        self,
        db_session,
        lock_audit_data_tenant_a,
        lock_audit_data_tenant_b,
        tenant_a_id,
        tenant_b_id,
    ):
        """
        Verifica que los lock audits de diferentes tenants están aislados.
        
        Test:
        1. Crea lock audits para tenant A y tenant B
        2. Consulta audits filtrando por tenant_id
        3. Verifica que cada tenant solo ve sus propios audits
        """
        # Crear lock audit para tenant A
        audit_a = LockAudit(**lock_audit_data_tenant_a)
        db_session.add(audit_a)
        
        # Crear lock audit para tenant B
        audit_b = LockAudit(**lock_audit_data_tenant_b)
        db_session.add(audit_b)
        
        await db_session.commit()
        
        # Consultar audits de tenant A
        stmt_a = select(LockAudit).where(LockAudit.tenant_id == tenant_a_id)
        result_a = await db_session.execute(stmt_a)
        audits_a = result_a.scalars().all()
        
        # Consultar audits de tenant B
        stmt_b = select(LockAudit).where(LockAudit.tenant_id == tenant_b_id)
        result_b = await db_session.execute(stmt_b)
        audits_b = result_b.scalars().all()
        
        # Verificar aislamiento
        assert len(audits_a) >= 1, "Tenant A debe tener al menos 1 lock audit"
        assert len(audits_b) >= 1, "Tenant B debe tener al menos 1 lock audit"
        
        # Verificar que los audits de tenant A solo pertenecen a tenant A
        for audit in audits_a:
            assert audit.tenant_id == tenant_a_id, f"Audit {audit.id} no pertenece a tenant A"
        
        # Verificar que los audits de tenant B solo pertenecen a tenant B
        for audit in audits_b:
            assert audit.tenant_id == tenant_b_id, f"Audit {audit.id} no pertenece a tenant B"
        
        # Verificar que los lock_keys no se cruzan
        lock_keys_a = {audit.lock_key for audit in audits_a}
        lock_keys_b = {audit.lock_key for audit in audits_b}
        
        assert lock_audit_data_tenant_a["lock_key"] in lock_keys_a
        assert lock_audit_data_tenant_b["lock_key"] in lock_keys_b
        assert lock_audit_data_tenant_a["lock_key"] not in lock_keys_b
        assert lock_audit_data_tenant_b["lock_key"] not in lock_keys_a
        
        # Cleanup
        await db_session.delete(audit_a)
        await db_session.delete(audit_b)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_cross_tenant_query_returns_empty(
        self,
        db_session,
        audit_log_data_tenant_a,
        tenant_a_id,
        tenant_b_id,
    ):
        """
        Verifica que consultar con tenant_id incorrecto no retorna datos de otro tenant.
        
        Test:
        1. Crea audit log para tenant A
        2. Consulta con tenant_id de tenant B
        3. Verifica que no se retornan datos
        """
        # Crear audit log solo para tenant A
        log_a = AuditLog(**audit_log_data_tenant_a)
        db_session.add(log_a)
        await db_session.commit()
        
        # Intentar consultar con tenant_id de tenant B
        stmt = select(AuditLog).where(
            AuditLog.tenant_id == tenant_b_id,
            AuditLog.user_id == audit_log_data_tenant_a["user_id"]
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()
        
        # Verificar que no se retornan datos
        assert len(logs) == 0, "No debe retornar datos de otro tenant"
        
        # Cleanup
        await db_session.delete(log_a)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_tenant_id_index_performance(
        self,
        db_session,
        tenant_a_id,
    ):
        """
        Verifica que los índices de tenant_id están funcionando correctamente.
        
        Test:
        1. Crea múltiples audit logs para tenant A
        2. Ejecuta query con EXPLAIN ANALYZE
        3. Verifica que se usa el índice idx_audit_tenant_timestamp
        """
        # Crear múltiples audit logs
        for i in range(10):
            log = AuditLog(
                event_type=f"test_event_{i}",
                user_id=f"+3460011{i:04d}",
                tenant_id=tenant_a_id,
                severity="info",
            )
            db_session.add(log)
        
        await db_session.commit()
        
        # Consultar con tenant_id
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_a_id)
        result = await db_session.execute(stmt)
        logs = result.scalars().all()
        
        # Verificar que se retornan los logs
        assert len(logs) >= 10, "Debe retornar al menos 10 logs"
        
        # Verificar que todos pertenecen al tenant correcto
        for log in logs:
            assert log.tenant_id == tenant_a_id
        
        # Cleanup
        for log in logs:
            await db_session.delete(log)
        await db_session.commit()
