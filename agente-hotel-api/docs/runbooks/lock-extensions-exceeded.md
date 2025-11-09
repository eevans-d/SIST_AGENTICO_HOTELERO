# Runbook: Lock Extensions Exceeded

## Overview
Alerta cuando se exceden extensiones de locks (se llega a `max_reached`) con frecuencia.

- Alert: LockExtensionsExceeded
- Severity: warning
- Expr (referencia): sum(rate(lock_extensions_total{result="max_reached"}[5m])) > 0.2 por 10m

## Síntomas
- Flujos de reserva frenados por imposibilidad de extender locks
- Mayor tasa de expiración de locks en medio de la transacción

## Causas Probables
- Transacciones más lentas de lo esperado (PMS lento, red, DB)
- `max_extensions` demasiado bajo para el SLA actual
- Cálculo de TTL/extend mal ajustado

## Chequeos Inmediatos
- PromQL:
  - `sum(rate(lock_extensions_total{result="max_reached"}[5m]))`
  - `sum(rate(lock_operations_total{operation="extend"}[5m]))`
  - `histogram_quantile(0.95, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le))`
- Logs: buscar `Máximo de extensiones alcanzado` y `extend` fallidos

## Pasos de Investigación
1. Revisar latencia del PMS y errores asociados
2. Validar el `max_extensions` y `extra_ttl` actuales
3. Revisar si hay picos de carga que alargan transacciones

## Mitigación
- Aumentar temporalmente `max_extensions` y/o `extra_ttl`
- Optimizar llamadas a PMS (cache, circuit breaker) para reducir latencia

## Rollback / Escalado
- Si persiste >30m con impacto en reservas, escalar a Backend AI Team

## Recursos Relacionados
- Código: `app/services/lock_service.py`
- Métricas: `lock_extensions_total`, `pms_api_latency_seconds`
- Alertas: LockConflictsHigh, LockOperationsFailureRate
