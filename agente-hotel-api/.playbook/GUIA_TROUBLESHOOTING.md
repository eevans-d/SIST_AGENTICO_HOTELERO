# GUÍA RÁPIDA DE TROUBLESHOOTING - EMERGENCIAS EN PRODUCCIÓN

**Última actualización**: 2025-10-24  
**Versión**: 1.0  
**Preparado para**: Respuesta rápida en incidentes

---

## ⚡ CHECKLIST DE RESPUESTA RÁPIDA (Primeros 5 minutos)

### Paso 1: Confirmar el Problema (< 1 min)
```bash
# Estado de servicios
curl -s http://localhost:8002/health/ready | jq .

# Logs en tiempo real
docker logs agente-api-prod 2>&1 | tail -50

# Métricas críticas
curl -s http://localhost:9090/api/v1/query?query=up | jq .
```

### Paso 2: Clasificar la Severidad (< 2 min)
| Síntoma | Severidad | Acción |
|---------|-----------|--------|
| API respondiendo lentamente | 🟡 MEDIA | Revisar Grafana P95 latency |
| API no responde (5xx errors) | 🔴 CRÍTICA | Reiniciar agente-api-prod |
| Base de datos no accesible | 🔴 CRÍTICA | Verificar postgres-prod |
| Redis no accesible | 🟠 ALTA | Verificar redis-prod + reintentar |
| Memory leak detectado | 🟠 ALTA | Iniciar graceful shutdown + restart |
| Circuit breaker abierto | 🟡 MEDIA | Revisar PMS adapter logs |

### Paso 3: Ejecutar Comando de Emergencia (< 2 min)
```bash
# Según el tipo de problema:

# OPCIÓN A: Servicio respondiendo lentamente
make health && make logs | head -100

# OPCIÓN B: Servicio caído completamente
make docker-restart  # Reinicia todos los servicios

# OPCIÓN C: Solo agente-api problemático
docker restart agente-api-prod

# OPCIÓN D: Database/Redis problemático
docker restart postgres-prod redis-prod
```

---

## 🔴 EMERGENCIA CRÍTICA - GUÍA 10 MINUTOS

### Escenario 1: API No Responde (HTTP 5xx errors > 10%)

**Síntomas**:
- Solicitudes devuelven 500 Internal Server Error
- Logs muestran stack traces
- Grafana muestra error_rate > 10%

**Diagnóstico**:
```bash
# 1. Verificar logs recientes
docker logs agente-api-prod | grep -i "error\|exception" | tail -20

# 2. Verificar dependencias
curl -s http://localhost:8002/health/ready | jq '.dependencies'

# 3. Revisar recursos (memoria/CPU)
docker stats agente-api-prod --no-stream
```

**Remediación** (por orden de intento):

1️⃣ **INMEDIATO** (< 30 seg):
```bash
# Reiniciar solo el container
docker restart agente-api-prod

# Esperar 10 segundos
sleep 10

# Verificar salud
curl -s http://localhost:8002/health/ready
```

2️⃣ **Si falla (1-2 min)**:
```bash
# Revisar logs para causas
docker logs agente-api-prod --tail 50 | tail -20

# Si es memoria: memory leak probable
# Si es database: verificar postgres
# Si es Redis: verificar redis
```

3️⃣ **Si persiste (2-3 min)**:
```bash
# Reiniciar dependencias
docker restart postgres-prod redis-prod

# Esperar 20 segundos
sleep 20

# Reiniciar API
docker restart agente-api-prod

# Verificar
curl -s http://localhost:8002/health/ready
```

4️⃣ **Último recurso (3-5 min)**:
```bash
# Reiniciar TODOS los servicios
make docker-stop && make docker-up

# Esperar a que todo esté ready
for i in {1..30}; do
  curl -s http://localhost:8002/health/ready && echo "✅ READY" && break
  echo "Intento $i... esperando"
  sleep 2
done
```

**Escalación** (si sigue fallando después de 5 min):
- Revisar últimos commits en git
- Preparar rollback si cambios recientes
- Contactar con equipo de backend

---

### Escenario 2: Circuit Breaker Abierto (PMS No Accesible)

**Síntomas**:
- Métrica `pms_circuit_breaker_state = 1` (OPEN)
- Logs muestran "Circuit breaker is OPEN"
- Disponibilidad reportada incorrectamente

**Diagnóstico**:
```bash
# Verificar estado del circuit breaker
curl -s http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state | jq '.data.result[0].value'

# Revisar intentos fallidos recientes
curl -s http://localhost:9090/api/v1/query?query='rate(pms_circuit_breaker_calls_total[5m])' | jq .

# Revisar logs de PMS adapter
docker logs agente-api-prod | grep -i "pms\|circuit" | tail -30
```

**Remediación**:

1️⃣ **Verificar PMS accesibilidad**:
```bash
# Si PMS_TYPE=qloapps, verificar conectividad
curl -I https://<pms_host>/api/status

# Si responde: Circuit breaker está bien, esperar recovery (~30s)
# Si no responde: PMS realmente caído, esperar mientras retorna

# Monitoring: Circuit breaker auto-cambia a HALF_OPEN después de 30s
```

2️⃣ **Si tarda mucho en recuperarse**:
```bash
# Aumentar timeout de recovery
# Editar app/services/pms_adapter.py:
# recovery_timeout = 30  -> recovery_timeout = 60

# Reiniciar API
docker restart agente-api-prod
```

3️⃣ **Si traffic es crítica y PMS no vuelve**:
```bash
# Habilitar fallback para consultas de disponibilidad
# Editar feature flags en Redis:
redis-cli SET "feature_flags:pms.fallback.enabled" "true"

# O vía API:
curl -X POST http://localhost:8002/admin/feature-flags \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"flag": "pms.fallback.enabled", "enabled": true}'

# Reiniciar API
docker restart agente-api-prod
```

---

### Escenario 3: Database Crítico (Postgres No Accesible)

**Síntomas**:
- Logs: "Connection refused to postgres:5432"
- Health endpoint: postgres status = UNHEALTHY
- API returnando 503 Service Unavailable

**Diagnóstico**:
```bash
# Verificar si container está corriendo
docker ps | grep postgres-prod

# Revisar logs de postgres
docker logs postgres-prod | tail -50

# Intentar conexión directa
docker exec -it postgres-prod psql -U agente -d agente_db -c "SELECT 1"
```

**Remediación**:

1️⃣ **Container corriendo pero no responde**:
```bash
# Reiniciar postgres
docker restart postgres-prod

# Esperar 5-10 segundos a que inicie
sleep 10

# Verificar estado
docker logs postgres-prod | tail -5

# Verificar conectividad
docker exec -it postgres-prod psql -U agente -d agente_db -c "SELECT 1"
```

2️⃣ **Revisar espacio en disco**:
```bash
# Si logs muestran "disk full"
docker exec -it postgres-prod df -h

# Si < 10% free: evacuación de datos o limpieza
# En emergency: borrar logs antiguos
docker exec -it postgres-prod psql -U agente -d agente_db -c \
  "DELETE FROM logs WHERE created_at < NOW() - INTERVAL '7 days';"
```

3️⃣ **Corrupción de datos (muy raro)**:
```bash
# Intentar recuperación automática
docker restart postgres-prod

# Si sigue fallando, revisar backup
ls -lah /backup/postgres/

# Restaurar desde backup más reciente
docker stop postgres-prod
docker rm postgres-prod
# [Restaurar volumen desde backup]
docker compose up -d postgres-prod
```

---

### Escenario 4: Ataque o Spam (Rate Limiting)

**Síntomas**:
- Métrica `http_requests_total{status=429}` elevada
- Logs: "Rate limit exceeded"
- IP específica generando mucho tráfico

**Diagnóstico**:
```bash
# Revisar solicitudes por IP
docker logs agente-api-prod | grep "429\|rate_limit" | tail -20

# Analizar patrón de IPs
docker logs agente-api-prod | grep "rate_limit" | awk '{print $NF}' | sort | uniq -c | sort -rn

# Verificar en Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status="429"}[5m])'
```

**Remediación**:

1️⃣ **Bloquear IP específica** (si es evidente):
```bash
# Editar NGINX config
docker exec -it nginx-prod bash -c \
  'echo "deny 192.168.1.100;" >> /etc/nginx/conf.d/blacklist.conf && nginx -s reload'

# O vía iptables
docker exec -it nginx-prod iptables -A INPUT -s 192.168.1.100 -j DROP
```

2️⃣ **Ajustar rate limits si es tráfico legítimo**:
```bash
# Aumentar límite temporalmente
redis-cli SET "rate_limit:max_requests" "300"  # De 120 a 300

# Aplicará en siguiente window de rate limit (1 minuto)

# O vía API
curl -X POST http://localhost:8002/admin/rate-limits \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"max_requests": 300, "window_seconds": 60}'
```

3️⃣ **Si es DDoS verificado**:
```bash
# Activar modo strict rate limiting
redis-cli SET "rate_limit:strict_mode" "true"

# Reducir límite temporalmente
redis-cli SET "rate_limit:max_requests" "60"

# Notificar a equipo de seguridad
echo "DDoS DETECTED - IP patterns saved to security_log"
```

---

## 🟠 PROBLEMAS DE RENDIMIENTO

### P95 Latency > 300ms

**Diagnóstico rápido**:
```bash
# 1. Verificar qué operación es lenta
curl -s http://localhost:16686/api/traces?service=agente-api&limit=10 | jq .

# 2. Revisar top 10 operaciones lentas (Prometheus)
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_requests_duration_seconds_bucket[5m]))'

# 3. Analizar traces en Jaeger
# Abrir: http://localhost:16687/search
# Filtrar por duración > 300ms
```

**Causas comunes**:
| Causa | Síntoma | Fix |
|-------|---------|-----|
| Query DB lenta | Query toma > 100ms | Agregar índice / analizar query plan |
| Redis miss | Cache_hit < 80% | Revisar TTL / aumentar cache size |
| PMS timeout | latency pico cada ~30s | Aumentar timeout / revisar PMS |
| Memory pressure | GC pausas | Reiniciar / revisar memory leak |

**Acción**:
```bash
# Si es database
# 1. Analizar query
docker exec -it postgres-prod psql -U agente -d agente_db -c "\
  SELECT query, calls, mean_time FROM pg_stat_statements 
  WHERE mean_time > 100 
  ORDER BY mean_time DESC LIMIT 10"

# 2. Agregar índices necesarios
docker exec -it postgres-prod psql -U agente -d agente_db -c \
  "CREATE INDEX idx_sessions_guest_id ON sessions(guest_id);"

# Si es Redis
# 1. Revisar tamaño de cache
redis-cli INFO memory

# 2. Aumentar max memory
docker exec -it redis-prod redis-cli CONFIG SET maxmemory 1gb

# 3. Ajustar política de evicción
docker exec -it redis-prod redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

### Memory Leak Detectado

**Síntomas**:
- `docker stats` muestra memoria creciente en agente-api-prod
- Métrica `process_resident_memory_bytes` aumentando constantemente
- Después de ~4-8 horas, API se vuelve lenta/no responde

**Diagnóstico**:
```bash
# Graficar tendencia de memoria
curl -s 'http://localhost:9090/api/v1/query_range?query=process_resident_memory_bytes&start=<now-1h>&end=<now>&step=60'

# Ver si es leak o uso normal
docker stats agente-api-prod --no-stream | awk '{print $NF}'

# Si crece > 100MB/hora: probable leak
```

**Remediación** (mientras se investiga):

1️⃣ **Graceful shutdown + restart**:
```bash
# Sin perder solicitudes en vuelo
docker kill --signal SIGTERM agente-api-prod

# Esperar max 30 segundos para que termine
sleep 30

# Reiniciar
docker start agente-api-prod
```

2️⃣ **Scheduled daily restart** (temporal fix):
```bash
# Agregar a crontab
echo "0 3 * * * docker restart agente-api-prod >> /var/log/restart.log 2>&1" | crontab -

# O vía docker compose restart policy
# Editar docker-compose.yml:
# restart_policy:
#   condition: on-failure
#   delay: 10s
#   max_attempts: 3
```

3️⃣ **Investigar source** (después de mitiga):
```bash
# Habilitar memory profiling
export PYTHONUNBUFFERED=1
export PYTHONASYNCDEBUG=1

# Agregar a startup:
# from memory_profiler import profile
# @profile
# def my_function():
#     ...

# Redeployr y analizar profiles
```

---

## 🟡 ALERTAS COMUNES Y SOLUCIONES

### Alert: "High Error Rate"
```bash
# Causas comunes:
# 1. PMS adapter failing
# 2. Database timeout
# 3. Invalid request format

# Fix inmediato:
# - Verificar PMS status
# - Revisar connection pool status
# - Revisar últimos cambios en API

docker logs agente-api-prod | grep -i error | tail -20
```

### Alert: "Service Degradation"
```bash
# Causas comunes:
# 1. Circuit breaker abierto
# 2. Fallback mode activo
# 3. Graceful degradation activado

# Fix:
# - Revisar health del servicio relacionado
# - Aumentar timeout/retry config
# - Escalar si persiste > 5 minutos

curl -s http://localhost:8002/health/ready | jq '.dependencies'
```

### Alert: "Pod Memory Exceeded"
```bash
# Fix:
# 1. Reducir traffic temporalmente
# 2. Restart service
# 3. Investigar memory leak

docker restart agente-api-prod
```

---

## 📊 DASHBOARDS Y HERRAMIENTAS

| Herramienta | URL | Uso |
|------------|-----|-----|
| Grafana | http://localhost:3000 | Dashboards de métricas |
| Prometheus | http://localhost:9090 | Queries de métricas |
| AlertManager | http://localhost:9094 | Alertas activas |
| Jaeger | http://localhost:16687 | Traces distribuidos |
| API Health | http://localhost:8002/health/ready | Estado servicios |

**Dashboard Recomendado para Emergencias**: "PMS Adapter Status" + "API Performance"

---

## 🆘 ESCALACIÓN

**Si problema persiste después de 10 minutos**:

1. Documentar:
   ```bash
   # Capturar estado completo
   docker ps > /tmp/incident_containers.txt
   docker logs agente-api-prod > /tmp/incident_logs.txt
   curl -s http://localhost:9090/api/v1/targets > /tmp/incident_metrics.json
   ```

2. Preparar rollback:
   ```bash
   # Ver commits recientes
   git log --oneline -5
   
   # Identificar último commit estable
   git log --grep="PRODUCTION STABLE" --oneline -1
   ```

3. Contactar equipo:
   - 🔴 CRÍTICA (API caído): All hands on deck
   - 🟠 ALTA (degraded): Senior engineer + on-call
   - 🟡 MEDIA (slow): DevOps lead review

**Post-Incident**:
```bash
# 1. Documentar qué pasó
# 2. Identificar causa raíz
# 3. Implementar fix
# 4. Update runbook
# 5. Post-mortem si es grave
```

---

## ✅ VERIFICACIÓN DE RECUPERACIÓN

Después de cualquier incidente, ejecutar:
```bash
# 1. Salud general
curl -s http://localhost:8002/health/ready | jq '.status'

# 2. Verificar métricas
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result | map(select(.value[1] != "1"))'

# 3. Revisar logs para errores
docker logs agente-api-prod | grep -i error | wc -l  # Debe ser < 5

# 4. Verificar alertas
curl -s http://localhost:9094/api/v1/alerts | jq '.data | length'  # Debe ser 0

# 5. Prueba básica de funcionalidad
curl -X POST http://localhost:8002/api/test \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' | jq '.status'  # Debe ser "success"
```

---

**Última Actualización**: 2025-10-24  
**Próxima Revisión**: 2025-11-24  
**Mantenedor**: Backend Team  
**Criticidad**: 🔴 MÁXIMA - Para uso en emergencias
