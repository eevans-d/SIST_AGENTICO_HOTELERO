# Runbook: Session Leak Detected

## Overview
Alerta cuando la tasa de crecimiento sostenido de sesiones indica posible fuga (sesiones no se liberan correctamente).

- Alert: SessionLeakDetected
- Severity: warning
- Expr (referencia): deriv(session_active_total[30m]) > 0.5 por 1h

## Síntomas
- Aumento continuo de `session_active_total`
- Memoria/CPU del servicio subiendo gradualmente
- Limpieza de sesiones con poca efectividad

## Causas Probables
- Tarea/cron de cleanup no ejecutándose o fallando
- Condiciones de expiración/TTL incorrectas
- Fuga lógica en el SessionManager (no se llama a release/cleanup)
- Caídas en Redis/DB que impiden actualizar estado

## Chequeos Inmediatos
- PromQL:
  - `session_active_total`
  - `deriv(session_active_total[30m])`
  - `increase(session_cleanup_total{result="error"}[1h])`
  - `up{job="agente-api"}`
- Logs:
  - Buscar `session_cleanup` errores y timeouts
  - Verificar `lock_service` conflictos/errores

## Pasos de Investigación
1. Confirmar si el incremento es global o por tenant: segmentar por labels si existen
2. Revisar ejecución del cleanup (scheduler/tarea asíncrona) y su frecuencia
3. Validar que el TTL de sesión esté bien configurado (env vars)
4. Revisar errores de Redis/DB en el periodo de crecimiento
5. Confirmar que los flujos que cierran sesión llaman a la API correspondiente

## Mitigación
- Reiniciar la tarea de cleanup o aumentar su frecuencia temporalmente
- Ejecutar cleanup manual (si existe endpoint/herramienta)
- Incrementar TTL de locks solo si hay expiraciones prematuras (evitar doble-booking)
- Si Redis está inestable, cambiar a modo degradado y reducir creación de nuevas sesiones

## Rollback / Escalado
- Si el leak persiste >2h: escalar a Backend AI Team
- Adjuntar: gráficos de `session_active_total`, logs, y resultados de PromQL

## Recursos Relacionados
- Alertas: SessionCleanupFailures, SessionsHighWarning
- Dashboards: Agent Health / Sessions
- Código: `app/services/session_manager.py`
