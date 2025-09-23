# [PROMPT 3.6] Manual de Operaciones - Agente Hotel

## 📋 Índice

1. [Operación Diaria](#operación-diaria)
2. [Troubleshooting](#troubleshooting)
3. [Runbooks](#runbooks)
4. [Mantenimiento](#mantenimiento)
5. [Recuperación de Desastres](#recuperación-de-desastres)

---

## Operación Diaria

### Checklist Matutino (08:00 - 5 minutos)

- **Verificar salud:** `curl https://tu-hotel.com.ar/health/ready`
- **Revisar logs de errores:** `docker logs agente-api --since="8h" | grep ERROR`
- **Verificar backups:** `ls -la /backups/agente-hotel/daily/`

---

## Troubleshooting

### 🔴 PROBLEMA: WhatsApp No Recibe Mensajes

- **Diagnóstico:** `curl "https://.../webhooks/whatsapp?hub.mode=subscribe..."`
- **Solución:** Verificar token, renovar SSL, revisar logs de NGINX.

### 🔴 PROBLEMA: PMS No Responde

- **Diagnóstico:** `docker exec agente-api ping qloapps` y `docker logs qloapps`
- **Solución:** `docker-compose restart qloapps mysql`

---

## Runbooks

### 📘 RUNBOOK: Confirmar Reserva con Seña

1. Verificar comprobante en dashboard.
2. Click en "Confirmar Reserva".
3. Verificar voucher enviado al cliente.
 
 ### 📘 RUNBOOK: Alerta DependencyDown
 - Síntoma: Alertmanager muestra "Alguna dependencia está caída".
 - Diagnóstico rápido:
	 1) Abrir Grafana → Dashboard "Readiness & Dependencies".
	 2) Ver `dependency_up` para identificar cuál (database, redis, pms) está en 0.
	 3) Revisar `/health/ready` para obtener detalles.
 - Acciones sugeridas:
	 - Database: verificar contenedor `postgres`, logs y conectividad; credenciales en `.env`.
	 - Redis: verificar contenedor `redis`, salud y puertos.
	 - PMS: si `pms_type=mock`, es esperado que esté en 1; si real, validar `PMS_BASE_URL` y disponibilidad del PMS.
 - Notas: la alerta solo dispara si hubo checks de readiness recientes (<5m) para evitar falsos positivos.

 ### 📘 RUNBOOK: OrchestratorHighErrorRate
 - Síntoma: Alertmanager muestra "Alta tasa de errores en Orchestrator".
 - Diagnóstico rápido:
	 1) Abrir Grafana → Dashboard "Agente - Overview".
	 2) Revisar panel "Orchestrator error rate by intent (5m)" para identificar el intent afectado.
	 3) Ver panel "Orchestrator latency p95 by intent" y "PMS API latency p95" para correlacionar con problemas externos.
 - Acciones sugeridas:
	 - Chequear logs de la API (docker compose logs agente-api) filtrando por el intent y correlations IDs.
	 - Validar la salud del PMS (/health/ready, paneles de PMS) si el intent involucra llamadas al PMS.
	 - Si el error aparece en intents de audio, revisar el flujo de STT/TTS.

 ### 📘 RUNBOOK: OrchestratorHighLatencyP95
 - Síntoma: Alertmanager muestra "Latencia p95 alta en Orchestrator".
 - Diagnóstico rápido:
	 1) Grafana → "Agente - Overview" → panel "Orchestrator latency p95 by intent".
	 2) Correlacionar con "PMS API latency p95" y estado del Circuit Breaker.
	 3) Verificar tasa de requests (carga) y reintentos.
 - Acciones sugeridas:
	 - Escalar horizontalmente `agente-api` si la carga es sostenida.
	 - Revisar latencia y errores del PMS; aplicar circuit breaker/reintentos si no estuvieran activos.
	 - Verificar Redis y Postgres (locks/sesiones/DB) en `/health/ready`.

---

## Mantenimiento

### Semanal (Domingos 04:00)

- Limpiar logs antiguos.
- Optimizar base de datos: `docker exec postgres vacuumdb ...`

---

## Recuperación de Desastres

### Falla Total del Servidor

1. Provisionar nuevo servidor.
2. Restaurar último backup desde S3.
3. Ejecutar `./scripts/restore_backup.sh`.
4. Actualizar DNS.
