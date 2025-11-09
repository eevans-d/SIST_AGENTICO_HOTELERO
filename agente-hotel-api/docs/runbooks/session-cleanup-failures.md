# Runbook: Session Cleanup Failures

## Overview
Alerta cuando fallan en exceso las tareas de limpieza de sesiones.

- Alert: SessionCleanupFailures
- Severity: warning
- Expr (referencia): increase(session_cleanup_total{result="error"}[1h]) > 3

## Síntomas
- Sesiones activas no decrecen
- Errores frecuentes de cleanup en logs
- Posibles timeouts o desconexiones con Redis/DB

## Causas Probables
- Redis no disponible o con latencia alta
- Cambios en esquema/contratos del SessionManager
- Excepciones no controladas en la rutina de cleanup
- Cambios recientes en feature flags que afectan cleanup

## Chequeos Inmediatos
- PromQL:
  - `increase(session_cleanup_total{result="error"}[1h])`
  - `session_active_total`
  - `up{job="agente-api"}`
- Logs: filtrar por `session_cleanup` y `error`

## Pasos de Investigación
1. Verificar estado de Redis y latencia (exporters/monitoring)
2. Revisar despliegues recientes y diffs en `session_manager.py`
3. Asegurar que la tarea de cleanup está programada y activa
4. Reproducir en staging con carga sintética y trazas activas

## Mitigación
- Reintentar manualmente la ejecución de cleanup (si existe endpoint)
- Aumentar reintentos/backoff de cleanup temporalmente
- Ajustar TTLs para evitar acumulación mientras se corrige

## Rollback / Escalado
- Si los errores >10 en 1h o persisten >2h: escalar a Backend AI Team

## Recursos Relacionados
- Alertas: SessionLeakDetected, SessionsHighWarning
- Código: `app/services/session_manager.py`
- Métricas: `session_cleanup_total{result}`
