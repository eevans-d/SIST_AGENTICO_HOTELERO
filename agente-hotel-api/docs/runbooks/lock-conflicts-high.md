# Runbook: Lock Conflicts High

## Overview
Alerta cuando la tasa de conflictos de locks supera umbral sostenido.

- Alert: LockConflictsHigh / LockConflictsCritical
- Severities: warning / critical
- Exprs (referencia):
  - Warning: sum(rate(lock_conflicts_total[5m])) > 0.5 por 10m
  - Critical: sum(rate(lock_conflicts_total[5m])) > 2 por 5m

## Síntomas
- Reservas rechazadas por "conflicto" aun con disponibilidad
- Latencia creciente en flujos de reserva
- Aumento de intentos fallidos y reintentos

## Causas Probables
- Sobreposición de fechas por lógica de validación defectuosa
- TTL de locks demasiado largo (locks "fantasma")
- Limpieza de locks expirados no ejecutada
- Pico de tráfico legítimo (promoción/evento)

## Chequeos Inmediatos
- PromQL:
  - `sum(rate(lock_conflicts_total[5m]))`
  - `sum(rate(lock_operations_total{operation="acquire"}[5m]))`
  - `sum(rate(lock_operations_total{result="success"}[5m]))`
- Logs: buscar `lock_service.conflict_detected`

## Pasos de Investigación
1. Determinar si concentración en ciertas habitaciones (segmentar por label room_id si disponible)
2. Revisar TTL actual y número de extensiones promedio
3. Validar consistencia de check-in/check-out enviados por el frontend
4. Revisar cambios recientes en `check_conflicts` (comparación de rangos)

## Mitigación
- Reducir TTL de locks mientras se investiga (evitar retener locks obsoletos)
- Proporcionar reintentos con backoff exponencial en la capa de reserva
- Ejecutar limpieza manual de locks huérfanos

## Rollback / Escalado
- Critical >15m o degradación severa de reservas: escalar a Backend AI Team y Product para posible limitación de tráfico.

## Recursos Relacionados
- Código: `app/services/lock_service.py`
- Métricas: `lock_conflicts_total`, `lock_operations_total`
- Alertas: LockExtensionsExceeded, LockOperationsFailureRate
