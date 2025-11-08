# Operación Rápida – Supabase + Agente Hotelero

Guía corta para personal no técnico (administrador/operador). Mantiene lo esencial para revisar salud del sistema y actuar rápido.

## Requisitos
- Acceso a Grafana y Prometheus del entorno.
- Terminal con `make` disponible en el proyecto `agente-hotel-api`.
- Variables `.env` configuradas (ver `docs/supabase/LLM-IMPLEMENTATION-MASTER-GUIDE.md`).

## Rutina Diaria (5 minutos)
1) Verificar conexión básica
- Ejecuta: `make supabase-test-connection`
- Esperado: muestra versión de Postgres y confirma SSL.

2) Revisar panel único en Grafana
- Panel: “Supabase Básico” (si no existe, usa panel general de base de datos)
- Observa:
  - Conexiones activas (db_connections_active)
  - Timeouts (db_statement_timeouts_total)
  - Sesiones JWT activas (jwt_sessions_active)
- Si hay alertas en amarillo/rojo, abre la tarjeta para ver descripción.

## Rutina Semanal
- Validar esquema y migraciones: `make supabase-validate`
- Limpieza de sesiones expiradas: `make maintenance-cleanup`
- Revisa en Prometheus la tendencia de: `increase(db_statement_timeouts_total[1h])`

## Qué hacer ante una alerta
- DBConnectionsHigh: Reduce temporalmente actividad (descartar tareas batch) y revisa consultas recientes. Si persiste > 30 min, contacta al equipo técnico.
- StatementTimeoutsPresent: Identifica endpoints lentos (ver logs/Jaeger) y evita operaciones costosas hasta corrección.

## Checklist de Salud (sí/no)
- SSL activo en la conexión
- Conexiones < umbral de alerta (>4 sostenido = investigar en dev)
- Timeouts = 0 en última hora
- Sesiones activas consistente con el tráfico del día

## Problemas Comunes y Soluciones Rápidas
- Error SSL en conexión: verifica `sslmode=require` en `DATABASE_URL`.
- Subida brusca de `db_connections_active`: asegúrate de que no haya workers zombis ni múltiples procesos en segundo plano.
- Aumento de timeouts: confirma que `statement_timeout` sigue en 15s y reduce operaciones pesadas.

## Procedimiento de Emergencia (DB dañada)
1) Cambiar a base temporal restaurada/alternativa (staging o PITR) – coordinación con equipo técnico.
2) Actualizar `.env` con nueva `DATABASE_URL`.
3) Ejecutar `make supabase-validate` y pruebas de humo.

## Dónde pedir ayuda
- Equipo Backend AI (canal interno)
- Documentación ampliada: `docs/supabase/LLM-IMPLEMENTATION-MASTER-GUIDE.md`
