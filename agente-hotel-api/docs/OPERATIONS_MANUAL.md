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

### Parámetros SLO

- `SLO_TARGET` (default 99.0) controla el objetivo global de éxito del orquestador.
- El error budget = 1 - (SLO_TARGET/100) se inserta dinámicamente en las recording rules al iniciar Prometheus.
- Para cambiarlo: editar `.env`, reiniciar servicio `prometheus` y validar reglas regeneradas.
- Pisos de tráfico: las alertas SLO requieren `orchestrator_message_rate_all > 0.5` para evitar falsos positivos en horas valle.

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

	 ### 📘 RUNBOOK: Orchestrator SLO Degradation
	 - Síntoma: Alertmanager muestra "SLO del Orchestrator en degradación" (warning/critical).
	 - Diagnóstico rápido:
		 1) Grafana → "SLO Health" → paneles "Success Rate Global" y "Top 5 Intents by Error %".
		 2) Identificar intents con peor success rate y correlacionar con paneles de error% y p95.
		 3) Revisar dependencia PMS/Redis si los intents involucrados llaman servicios externos.
	 - Acciones sugeridas:
		 - Mitigar intents problemáticos: degradación controlada, respuestas de fallback.
		 - Abrir incidente si el success rate <97% por más de 10m.
		 - Ajustar umbrales tras análisis de tráfico real.
		 - Ajustar piso de tráfico (`orchestrator_message_rate_all`) si la alerta no dispara pese a fallos en alto volumen o dispara con volumen muy bajo.

	 ### 📘 RUNBOOK: Orchestrator SLO Burn Rate
	 - Síntoma: Alertmanager muestra "SLO burn rate alto/crítico".
	 - Diagnóstico rápido:
		 1) Grafana → "SLO Health" → paneles de burn rate (fast/slow) y budget usado/restante.
		 2) Confirmar si el burn rate fast y slow superan umbrales (ver anotaciones de la alerta).
	 - Acciones sugeridas:
		 - Aplicar mitigaciones inmediatas en intents top-k con alto error%.
		 - Si crítico, considerar revertir despliegues recientes relacionados.
		 - Documentar impacto y consumo de error budget en el incidente.
		 - Ajustar `SLO_TARGET` (y por ende error budget) sólo tras análisis post-mortem, nunca durante un incidente activo.

	 ### 📘 RUNBOOK: HighHttp5xxRate
	 - Síntoma: Alertmanager muestra "Alta tasa de 5xx" en un endpoint.
	 - Diagnóstico rápido:
		 1) Grafana → "Agente - Overview" → panel "HTTP 5xx rate (5m)".
		 2) Revisar logs de `agente-api` y NGINX para ese endpoint.
		 3) Correlacionar con "Orchestrator error percentage" si aplica.
	 - Acciones sugeridas:
		 - Identificar excepciones frecuentes en logs y abrir issue.
		 - Validar payloads de entrada (sanitización/validación) y dependencias externas.
		 - Implementar manejo de errores y tests si faltan.

	 ### 📘 RUNBOOK: HighPmsLatencyP95
	 - Síntoma: p95 de PMS > umbral sostenido.
	 - Diagnóstico rápido:
		 1) Grafana → panel "PMS API latency p95".
		 2) Verificar estado del PMS (servicios `qloapps`/`mysql`).
		 3) Revisar circuit breaker y reintentos.
	 - Acciones sugeridas:
		 - Aumentar caching en el adapter; validar Redis.
		 - Ajustar timeouts/backoff del adapter.
		 - Coordinar con el equipo del PMS.

	 ### 📘 RUNBOOK: CircuitBreakerOpen
	 - Síntoma: Circuit Breaker abierto por más de 2m.
	 - Diagnóstico rápido:
		 1) Grafana → panel "Circuit Breaker state" (rojo cuando >0).
		 2) Correlacionar con latencia/errores del PMS.
		 3) Logs del adapter para ver causas (rate limit, timeouts, 5xx).
	 - Acciones sugeridas:
		 - Verificar credenciales/endpoints del PMS.
		 - Incrementar límites/retrys temporalmente si corresponde.
		 - Desplegar mitigaciones (cache warmup, degradación controlada).

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
