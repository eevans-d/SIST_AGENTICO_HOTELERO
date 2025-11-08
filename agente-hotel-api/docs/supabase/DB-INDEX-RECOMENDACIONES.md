# Recomendaciones de índices (staging)

Objetivo: reducir latencias en consultas frecuentes y preparar escalabilidad.

## lock_audit (PostgreSQL)
- Índices propuestos:
  - `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lock_audit_room_dates ON lock_audit (room_id, check_in, check_out);`
  - `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lock_audit_session ON lock_audit (session_id);`
- Racional: búsquedas por habitación y ventanas de fechas; trazabilidad por sesión.

## tenant / tenant_user_identifier
- Índices propuestos:
  - `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_slug ON tenant (slug);`
  - `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_user_identifier ON tenant_user_identifier (external_id, channel);`
- Racional: resolución de tenant por canal/identificador externo (WhatsApp/Gmail).

## admin_audit_log (si aplica)
- Índices propuestos:
  - `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_audit_ts ON admin_audit_log (created_at DESC);`
  - `CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log (actor_id);`
- Racional: listados por fecha y filtros por actor.

## Consideraciones
- Usar `CONCURRENTLY` en producción para minimizar bloqueos.
- Verificar tamaño de índices y cardinalidad; evitar over-indexing.
- Revisar planes con `EXPLAIN (ANALYZE, BUFFERS)` previo a crear índices definitivos.
- Alinear con patrones de consulta reales de `SessionManager`/`LockService`/resolución de tenant.
