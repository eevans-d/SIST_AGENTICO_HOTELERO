# Manual de Operaciones - Sistema Agente Hotelero IA

## 📋 Índice

1. [Arquitectura del Sistema](#arquitectura-del-sistema)
2. [Operación Diaria](#operación-diaria)
3. [Troubleshooting](#troubleshooting)
4. [Runbooks](#runbooks)
5. [Mantenimiento](#mantenimiento)
6. [Monitoreo y Alertas](#monitoreo-y-alertas)
7. [Recuperación de Desastres](#recuperación-de-desastres)
8. [Seguridad](#seguridad)

---

## Arquitectura del Sistema

### Componentes Principales

- **agente-api**: API principal FastAPI que orquesta todo el sistema
- **postgres**: Base de datos para sesiones, bloqueos y mapeo de inquilinos
- **redis**: Caché, control de velocidad y bloqueos distribuidos
- **qloapps**: Sistema PMS de gestión hotelera
- **monitoring**: Prometheus, Grafana y AlertManager

### Patrones de Diseño Clave

- **Patrón Orquestador**: `orchestrator.py` coordina el flujo completo
- **Circuit Breaker**: Previene cascadas de fallos con servicios externos
- **Mensajes Unificados**: Normaliza comunicaciones de diferentes canales
- **Feature Flags**: Habilita/deshabilita funciones sin redespliegue

## Operación Diaria

### Checklist Matutino (08:00 - 5 minutos)

- **Verificar salud:** `curl https://api.agente-hotel.com/health/ready`
- **Revisar logs de errores:** `docker logs agente-api --since="8h" | grep ERROR`
- **Verificar backups:** `ls -la /backups/agente-hotel/daily/`
- **Comprobar estado del circuit breaker:** `curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state`
- **Verificar uso de recursos:** `docker stats --no-stream`

### Parámetros SLO

- `SLO_TARGET` (default 99.0) controla el objetivo global de éxito del orquestador.
- El error budget = 1 - (SLO_TARGET/100) se inserta dinámicamente en las recording rules al iniciar Prometheus.
- Para cambiarlo: editar `.env`, reiniciar servicio `prometheus` y validar reglas regeneradas.
- Pisos de tráfico: las alertas SLO requieren `orchestrator_message_rate_all > 0.5` para evitar falsos positivos en horas valle.

### Gestión de Feature Flags

```bash
# Listar feature flags actuales
curl http://localhost:8000/admin/feature-flags

# Activar flag específico
curl -X POST http://localhost:8000/admin/feature-flags \
  -H "Content-Type: application/json" \
  -d '{"name": "nlp.fallback.enhanced", "enabled": true}'

# Desactivar flag específico
curl -X POST http://localhost:8000/admin/feature-flags \
  -H "Content-Type: application/json" \
  -d '{"name": "nlp.fallback.enhanced", "enabled": false}'
```

---

## Troubleshooting

### 🔴 PROBLEMA: WhatsApp No Recibe Mensajes

- **Síntomas**: No llegan mensajes al webhook, error "verificación fallida" en logs
- **Diagnóstico:** 
  ```bash
  curl "https://.../webhooks/whatsapp?hub.mode=subscribe&hub.challenge=1234&hub.verify_token=YOUR_TOKEN"
  docker-compose logs -f agente-api | grep -i whatsapp
  ```
- **Solución:** 
  - Verificar token en `.env.production`
  - Renovar certificado SSL si está expirado
  - Revisar logs de NGINX para problemas de conexión
  - Confirmar que el puerto 443 está abierto

### 🔴 PROBLEMA: PMS No Responde

- **Síntomas**: Circuit breaker en estado OPEN, errores 503 en respuestas API
- **Diagnóstico:** 
  ```bash
  docker exec agente-api ping qloapps
  docker logs qloapps | tail -n 100
  curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state
  ```
- **Solución:** 
  ```bash
  # Reiniciar servicios relacionados con PMS
  docker-compose restart qloapps mysql
  
  # Verificar conexión después del reinicio
  docker exec agente-api curl -v http://qloapps:8080/api/v1/ping
  
  # Si persiste, verificar configuración
  grep -E "^PMS_" .env.production
  ```

### 🔴 PROBLEMA: Alta Latencia en API

- **Síntomas**: Alertas de latencia P95, quejas de usuarios
- **Diagnóstico:**
  ```bash
  # Verificar métricas de latencia
  curl http://localhost:9090/api/v1/query?query=histogram_quantile\(0.95,\ rate\(http_request_duration_seconds_bucket\[5m\]\)\)
  
  # Verificar uso de recursos
  docker stats
  
  # Verificar conexiones DB
  docker exec postgres psql -U agente -c "SELECT count(*) FROM pg_stat_activity;"
  ```
- **Solución:**
  - Verificar tasa de aciertos de caché
  - Comprobar si hay tareas en segundo plano consumiendo recursos
  - Reiniciar el servicio si es necesario
  - Escalar verticalmente recursos si el problema persiste

---

## Runbooks

### 📘 RUNBOOK: Confirmar Reserva con Seña

1. Verificar comprobante en dashboard.
2. Click en "Confirmar Reserva".
3. Verificar voucher enviado al cliente.
4. Comprobar en logs que se registró correctamente:
   ```bash
   docker-compose logs agente-api | grep -i "reservation confirmed" | tail -n 20
   ```
5. Verificar sincronización con QloApps:
   ```bash
   curl -H "Authorization: Bearer $PMS_API_KEY" http://qloapps:8080/api/v1/reservations/{ID}
   ```
 
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

	 ### 📘 RUNBOOK: SLO Budget Exhaust Forecast
	 - Síntoma: Alertmanager muestra proyección de agotamiento (<12h o <6h).
	 - Diagnóstico rápido:
		 1) Grafana → "SLO Health" → panel "Hours to Exhaust Budget".
		 2) Verificar burn rates y budget used.
		 3) Identificar intents top error% / p95.
	 - Acciones sugeridas:
		 - Iniciar acciones de mitigación (reducción de features, fallback responses).
		 - Si crítico (<6h) escalar a guardia e iniciar plan de reducción de errores priorizando intents top.
		 - Evaluar si hay despliegue reciente correlacionado.
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

	 ### 📘 RUNBOOK: PmsCircuitBreakerImminentOpen
	 - Síntoma: Alertas `PmsCircuitBreakerImminentOpenWarning` o `PmsCircuitBreakerImminentOpenCritical` indicando riesgo de apertura.
	 - Diagnóstico rápido:
		 1) Grafana → panel "Circuit Breaker state" y añadir paneles derivados (failure ratios, streak) si no existen.
		 2) Ver panel "PMS API latency p95" y "PMS Errors by type" para correlacionar naturaleza (timeouts vs 5xx).
		 3) Consultar métricas: `pms_cb_failure_streak_fraction`, `pms_cb_failure_ratio_1m`, `pms_cb_minutes_to_open_estimate`.
	 - Posibles causas:
		 - Degradación real del PMS (timeouts incrementales).
		 - Cambios recientes en timeouts o thresholds del adapter.
		 - Pico de tráfico con patrones no cacheados (incrementa presión y fallos).
	 - Acciones sugeridas (orden):
		 1) Confirmar que los fallos son legítimos revisando logs (buscar patrones repetidos).
		 2) Si los fallos son timeouts → aumentar temporalmente `read` timeout (ej. +50%) y monitorear efecto.
		 3) Activar rutas de degradación: limitar intents que disparan llamadas PMS no críticas.
		 4) Incrementar TTL de cache de disponibilidad para reducir presión sobre PMS.
		 5) Coordinar con equipo PMS si latencia/errores se originan upstream.
	 - Mitigación preventiva:
		 - Si `pms_cb_minutes_to_open_estimate < 2` y la racha sigue subiendo, aplicar pasos 2–4 antes de que el breaker abra.
	 - Post-mortem:
		 - Evaluar si `failure_threshold=5` es demasiado bajo para el perfil de error transitorio.
		 - Considerar backoff más agresivo para retries o circuit half-open probabilístico.

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

	 ### 📘 RUNBOOK: PmsCacheHitRatio
	 - Síntoma: Alertas `PmsCacheHitRatioLowWarning` o `PmsCacheHitRatioLowCritical`.
	 - Diagnóstico rápido:
		 1) Grafana → Dashboard "Agente - Overview" → panel 21 (hit ratio) y panel 22 (hits vs misses).
		 2) Correlacionar con panel de latencia PMS p95 y estado del Circuit Breaker.
		 3) Verificar en logs si hay patrón de invalidaciones frecuentes (`Invalidated ... cache keys`).
	 - Posibles causas:
		 - TTL demasiado corto (expiraciones antes de reutilización real).
		 - Clave de cache con demasiados parámetros (alta cardinalidad) → baja reutilización.
		 - Invalidation agresiva tras `create_reservation` u otras operaciones de escritura.
		 - Pico de nuevos tipos de consultas (cambio de tráfico estacional) aún no calientes.
	 - Acciones sugeridas (orden):
		 1) Confirmar volumen: asegurar actividad >0.2 ops/s (condición de la alerta).
		 2) Inspeccionar keys representativas en Redis (opcional) para patrones de cardinalidad.
		 3) Ajustar TTL (aumentar) temporalmente si expiración temprana es evidente.
		 4) Implementar cache pre-warm (script) para queries populares de disponibilidad (fechas cercanas, room types top).
		 5) Revisar lógica de invalidación: evaluar un patrón más específico en lugar de `availability:*` completo.
		 6) Si latencia PMS también aumenta → priorizar mitigación y escalar a equipo PMS.
	 - Métrica clave:
		 `pms_cache_hit_ratio` (recording rule 5m). Objetivo recomendado inicial: >0.8.
	 - Post-mortem:
		 Documentar ajustes (TTL, patrones clave, warm-up) y validar mejora sostenida >24h.

---

## Mantenimiento

### Semanal (Domingos 04:00)

- Limpiar logs antiguos:
  ```bash
  # Eliminar logs más antiguos que 7 días
  find /var/log/agente-hotel -type f -name "*.log" -mtime +7 -delete
  
  # Comprimir logs más antiguos que 2 días
  find /var/log/agente-hotel -type f -name "*.log" -mtime +2 -not -name "*.gz" -exec gzip {} \;
  ```
  
- Optimizar base de datos:
  ```bash
  docker exec postgres vacuumdb -U agente --analyze
  ```
  
- Verificar espacio en disco:
  ```bash
  df -h /
  ```
  
- Limpiar imágenes Docker no utilizadas:
  ```bash
  docker system prune -f
  ```

### Mensual (Primer Domingo del Mes)

- Rotación de claves de acceso:
  ```bash
  # Generar nueva API key en QloApps
  # Actualizar .env.production
  nano .env.production
  
  # Reiniciar el servicio para aplicar cambios
  docker-compose -f docker-compose.production.yml restart agente-api
  ```
  
- Verificar certificados SSL:
  ```bash
  # Comprobar fecha de expiración
  openssl x509 -enddate -noout -in /etc/nginx/ssl/agente-hotel.com.crt
  ```
  
- Test de recuperación:
  ```bash
  # Crear backup de prueba
  make backup ENVIRONMENT=production
  
  # Intentar restauración en ambiente de staging
  make restore ENVIRONMENT=staging BACKUP_DATE=$(date +%Y%m%d)_000000
  ```

- Auditoría de seguridad:
  ```bash
  make security
  ```

### Trimestral

- Actualización de dependencias:
  ```bash
  # Actualizar desde repositorio
  git pull origin main
  
  # Actualizar dependencias
  docker-compose -f docker-compose.production.yml build --no-cache
  
  # Reiniciar servicios
  docker-compose -f docker-compose.production.yml down
  docker-compose -f docker-compose.production.yml up -d
  ```
  
- Revisión de umbrales de alertas:
  ```bash
  # Verificar estadísticas reales vs umbrales
  docker exec prometheus promtool query instant 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30d])) by (le, endpoint))'
  
  # Ajustar umbrales si es necesario
  nano docker/prometheus/rules/slo.rules.yml
  
  # Aplicar cambios
  docker-compose -f docker-compose.production.yml restart prometheus
  ```

## Monitoreo y Alertas

### Dashboards Principales

- **URL**: https://grafana.agente-hotel.com
- **Credenciales**: En `.env.production` (GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)

Dashboards clave:
1. **Agente - Overview**: Vista general del sistema
2. **SLO Health**: Métricas de nivel de servicio
3. **PMS Integration**: Métricas de integración con QloApps
4. **WhatsApp Metrics**: Estadísticas de mensajería
5. **Resource Utilization**: Uso de recursos del sistema

### Métricas Críticas

| Métrica | Descripción | Umbral Warning | Umbral Critical |
|---------|-------------|----------------|-----------------|
| `pms_circuit_breaker_state` | Estado del circuit breaker (0=cerrado, 1=abierto) | >0 por 1m | >0 por 5m |
| `http_request_duration_seconds` | Latencia de solicitudes API | P95 > 500ms | P95 > 1s |
| `orchestrator_error_ratio` | Tasa de errores del orquestador | >0.01 por 5m | >0.05 por 5m |
| `pms_cache_hit_ratio` | Tasa de aciertos de caché | <0.7 | <0.5 |
| `orchestrator_slo_budget_remaining` | Presupuesto de error SLO restante | <50% | <25% |

### Configuración de Alertas

Las reglas de alertas están definidas en:
- `docker/prometheus/rules/agente.rules.yml`
- `docker/prometheus/rules/slo.rules.yml`

Canales de notificación configurados:
- Slack: #agente-hotel-alerts
- Email: alertas@agente-hotel.com
- PagerDuty: Sólo para alertas críticas

### Respuesta a Alertas

| Prioridad | Tiempo de Respuesta | Notificación | Ejemplo de Alerta |
|-----------|---------------------|--------------|-----------------|
| P1 (Crítica) | 15 minutos | Slack, Email, PagerDuty | CircuitBreakerOpen, HighErrorRate |
| P2 (Alta) | 30 minutos | Slack, Email | HighLatencyP95, SLOBurnRateFast |
| P3 (Media) | 2 horas | Slack | CacheLowHitRate, HighWarningRate |
| P4 (Baja) | 24 horas | Ticket en sistema | DiskSpaceWarning, SlowGrowth |

---

## Recuperación de Desastres

### Plan de Continuidad de Negocio

El sistema está diseñado para mantener operaciones críticas incluso durante eventos disruptivos:

1. **Degradación Gradual**: Feature flags permiten deshabilitar funcionalidades no críticas
2. **Caching Agresivo**: Redis mantiene datos críticos para operación offline
3. **Respuestas de Fallback**: NLP configurado con respuestas generales cuando PMS no responde

### Falla Total del Servidor

1. Provisionar nuevo servidor con requisitos mínimos:
   - 4 CPU, 8GB RAM, 100GB SSD
   - Docker y Docker Compose instalados

2. Restaurar desde backup:
   ```bash
   # Clonar repositorio
   git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
   cd SIST_AGENTICO_HOTELERO/agente-hotel-api
   
   # Descargar último backup de S3
   aws s3 cp s3://agente-hotel-backups/latest/ ./backups/ --recursive
   
   # Restaurar datos
   ./scripts/restore.sh --backup-date 20251005_153045
   
   # Iniciar servicios
   docker-compose -f docker-compose.production.yml up -d
   ```

3. Actualizar DNS:
   - Apuntar api.agente-hotel.com al nuevo servidor
   - Esperar propagación DNS (TTL: 300s)
   
4. Verificar restauración:
   ```bash
   # Verificar servicios
   docker-compose -f docker-compose.production.yml ps
   
   # Verificar endpoints de salud
   curl https://api.agente-hotel.com/health/live
   curl https://api.agente-hotel.com/health/ready
   
   # Verificar procesamiento de mensajes
   curl https://api.agente-hotel.com/admin/test-message
   ```

### Recuperación de Base de Datos

En caso de corrupción de datos o fallo en PostgreSQL:

```bash
# Detener servicios que dependen de la base de datos
docker-compose -f docker-compose.production.yml stop agente-api

# Restaurar desde backup específico
make restore ENVIRONMENT=production BACKUP_DATE=20251005_153045 DATABASE=postgres

# Reiniciar servicios
docker-compose -f docker-compose.production.yml up -d
```

### Degradación Controlada del Servicio

En caso de sobrecarga o problemas severos:

```bash
# Activar modo de degradación (deshabilita funciones no críticas)
curl -X POST http://localhost:8000/admin/feature-flags \
  -H "Content-Type: application/json" \
  -d '{"name": "service.degradation.enabled", "enabled": true}'

# Aumentar agresividad del caching
curl -X POST http://localhost:8000/admin/cache/ttl \
  -H "Content-Type: application/json" \
  -d '{"pattern": "availability:*", "ttl": 3600}'
```

## Seguridad

### Gestión de Secretos

- Los secretos están almacenados en archivos `.env.[environment]`
- Nunca se deben commitear estos archivos al repositorio
- Las contraseñas deben rotarse regularmente según la política:
  - API keys: cada 90 días
  - Contraseñas DB: cada 180 días
  - Tokens de acceso: según el proveedor

### Verificaciones de Seguridad

```bash
# Escaneo de vulnerabilidades
make security-fast

# Análisis de código estático
make lint

# Verificación de secretos expuestos
gitleaks detect
```

### Logs de Auditoría

Las acciones administrativas se registran en logs de auditoría:

```bash
# Ver logs de acciones administrativas
docker-compose -f docker-compose.production.yml logs agente-api | grep -i "audit"

# Exportar logs de auditoría para cumplimiento
docker-compose -f docker-compose.production.yml logs --since=30d agente-api | grep -i "audit" > /tmp/audit_logs_$(date +%Y%m%d).log
```

### Respuesta a Incidentes de Seguridad

1. **Detección**: Alertas automáticas o reporte manual
2. **Contención**: Aislar sistemas afectados
3. **Erradicación**: Eliminar amenaza y vulnerabilidad
4. **Recuperación**: Restaurar servicios desde backup limpio
5. **Lecciones aprendidas**: Documentar y actualizar procesos
