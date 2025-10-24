# 🚀 DÍA 3.5 - DEPLOY A STAGING (25-26 OCT 2025)

**Status**: ⏳ PRÓXIMO (Esperando validación CI)  
**Prerequisito**: CI green en main + PR #11 mergeado ✅  
**Duración Estimada**: 2-4 horas  
**Setup Inicial**: 15-20 minutos  

---

## 📋 Estado Actual (23-OCT-2025)

### ✅ Completado
- [x] PR #11 creado (23-OCT 05:00)
- [x] PR #11 mergeado a main (23-OCT 05:24 - commit 5dae3d8)
- [x] Fix CI gitleaks (23-OCT 05:50 - commit 6191f43)
- [x] Fix YAML syntax (23-OCT 05:55 - commit 9b7cc5c)
- [x] 4 bloqueantes seguridad en main ✅

### ⏳ Pendiente
- [ ] Verificar CI green en main (~5-10 min)
- [ ] Proceder con DÍA 3.5 (Deploy Staging)

---

## 🎯 Objetivo DÍA 3.5

Desplegar la aplicación con los **4 bloqueantes de seguridad** en un entorno de **Staging completo** con:

1. ✅ 7 servicios Docker (agente-api, postgres, redis, prometheus, grafana, alertmanager, jaeger)
2. ✅ Datos de prueba representativos
3. ✅ Monitoreo completo (métricas + alertas)
4. ✅ Performance benchmarking automático
5. ✅ Smoke tests (6 tests críticos)

---

## 📚 Documentación de Referencia

### Documentos Principales

1. **CHECKLIST_STAGING_DEPLOYMENT.md** (1,179 líneas)
   - Ubicación: `agente-hotel-api/.optimization-reports/`
   - Contenido: Setup completo de staging con Docker Compose
   - Duración: 1.5-2 horas total
   - Secciones:
     - Pre-flight checklist (5 min)
     - Docker Compose staging (30 min)
     - Secrets management (10 min)
     - Seed data (15 min)
     - Smoke tests (20 min)
     - Performance benchmarks (15 min)

2. **GUIA_MERGE_DEPLOYMENT.md** (759 líneas)
   - Ubicación: `agente-hotel-api/.optimization-reports/`
   - Contenido: Sección "DÍA 3.5: Deploy Staging"
   - Incluye: Monitoring setup, rollback procedures

3. **GUIA_TROUBLESHOOTING.md** (618 líneas)
   - Ubicación: `agente-hotel-api/.optimization-reports/`
   - Uso: Si algo falla durante deployment

---

## 🔍 Pre-Flight Checklist (ANTES DE EMPEZAR)

### Verificaciones Críticas

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Branch main actualizado
git checkout main && git pull origin main

# 2. CI está green en GitHub
# Ve a: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/actions
# Verifica: Último workflow run en main está ✅ GREEN

# 3. Docker disponible
docker --version && docker compose version

# 4. Puertos libres (8002, 5432, 6379, 9090, 3000, 9093, 16686)
netstat -tuln | grep -E '8002|5432|6379|9090|3000|9093|16686'

# 5. Espacio en disco (mínimo 5GB)
df -h /var/lib/docker

# 6. Archivos base existen
ls -lh docker-compose.yml Dockerfile.production pyproject.toml
```

**TODOS DEBEN PASAR** ✅ antes de continuar.

---

## 📋 Plan de Ejecución (Paso a Paso)

### FASE 1: Preparación (15-20 min)

**1.1 Generar Secrets Staging**
```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Ejecutar script de generación de secrets
./scripts/generate-staging-secrets.sh > .env.staging

# Verificar que se generaron correctamente
grep -E "SECRET_KEY|JWT_SECRET_KEY|POSTGRES_PASSWORD" .env.staging

# IMPORTANTE: Revisar y ajustar valores según necesidad
nano .env.staging
```

**1.2 Crear Docker Compose Staging**
- Archivo: `docker-compose.staging.yml`
- Contenido: Ver `CHECKLIST_STAGING_DEPLOYMENT.md` (líneas 40-250)
- Incluye: 7 servicios con healthchecks, resource limits, restart policies

**1.3 Validar Configuración**
```bash
# Validar sintaxis YAML
docker compose -f docker-compose.staging.yml config

# Verificar que no hay errores
echo $?  # Debe retornar 0
```

---

### FASE 2: Deployment (30-40 min)

**2.1 Build Images**
```bash
# Build imagen producción
docker compose -f docker-compose.staging.yml build agente-api

# Verificar imagen creada
docker images | grep agente-api-staging
```

**2.2 Start Services**
```bash
# Iniciar todos los servicios
docker compose -f docker-compose.staging.yml up -d

# Verificar que todos están running
docker compose -f docker-compose.staging.yml ps

# Seguir logs de agente-api
docker compose -f docker-compose.staging.yml logs -f agente-api
```

**2.3 Healthchecks**
```bash
# Esperar a que todos los servicios estén healthy (~2-3 min)
watch -n 5 'docker compose -f docker-compose.staging.yml ps'

# Cuando todos estén "healthy", proceder
```

---

### FASE 3: Seed Data (15 min)

**3.1 Datos de Prueba**
```bash
# Ejecutar script de seed data
docker compose -f docker-compose.staging.yml exec agente-api \
  python scripts/seed-staging-data.py

# Verificar datos creados
docker compose -f docker-compose.staging.yml exec postgres \
  psql -U agente_user -d agente_staging -c "SELECT COUNT(*) FROM tenants;"
```

**Datos esperados:**
- 3 tenants (hotel_a, hotel_b, hotel_c)
- 10 usuarios de prueba
- 5 habitaciones por tenant
- 20 mensajes de prueba

---

### FASE 4: Smoke Tests (20 min)

**4.1 Health Endpoints**
```bash
# Test 1: Liveness
curl http://localhost:8002/health/live | jq .
# Esperado: {"status": "healthy"}

# Test 2: Readiness
curl http://localhost:8002/health/ready | jq .
# Esperado: {"status": "ready", "checks": {"postgres": "ok", "redis": "ok", "pms": "ok"}}

# Test 3: Metrics
curl http://localhost:8002/metrics | head -20
# Esperado: Ver métricas Prometheus
```

**4.2 Functional Tests**
```bash
# Test 4: Webhook endpoint (simulado)
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "test_user_123",
    "channel": "whatsapp",
    "text": "Hola, quiero hacer una reserva",
    "timestamp": "'$(date -Iseconds)'"
  }' | jq .

# Esperado: Response con intent detectado
```

**4.3 Security Tests (4 bloqueantes)**
```bash
# Test 5: Tenant Isolation
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 800+)

# Test 6: Metadata Filtering
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 850+)

# Test 7: Channel Spoofing
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 900+)

# Test 8: Stale Cache
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 950+)
```

---

### FASE 5: Monitoring Setup (15 min)

**5.1 Prometheus**
```bash
# Verificar Prometheus scraping
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Esperado: agente-api con health="up"
```

**5.2 Grafana**
```bash
# Acceder a Grafana
open http://localhost:3000

# Login: admin / admin (cambiar password en primer login)

# Importar dashboards:
# - Orchestrator Dashboard
# - PMS Adapter Dashboard
# - Health Metrics Dashboard
```

**5.3 AlertManager**
```bash
# Verificar alertas configuradas
curl http://localhost:9093/api/v2/alerts | jq .

# Esperado: 0 alertas activas (sistema sano)
```

---

### FASE 6: Performance Benchmarks (15 min)

**6.1 Baseline Latency**
```bash
# Ejecutar benchmark
docker compose -f docker-compose.staging.yml exec agente-api \
  python scripts/run-performance-benchmark.py

# Métricas esperadas (ver BASELINE_METRICS.md):
# - P50: < 50ms
# - P95: < 150ms
# - P99: < 300ms
# - Throughput: > 100 req/s
```

**6.2 Load Test**
```bash
# Ejecutar load test (opcional)
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 1000+)
```

---

## ✅ Criterios de Éxito

Al final de DÍA 3.5, debes tener:

- [x] **7 servicios corriendo** (docker ps muestra 7 containers healthy)
- [x] **CI green** en main
- [x] **Health endpoints responding** (liveness + readiness)
- [x] **Datos de prueba cargados** (3 tenants, 10 users, 5 rooms/tenant)
- [x] **6 smoke tests PASSED** (health + functional + security)
- [x] **Monitoring activo** (Prometheus scraping, Grafana dashboards)
- [x] **Performance baseline** (latency < 300ms P99, throughput > 100 req/s)

---

## 🚨 Troubleshooting

### Problema: Container no inicia
```bash
# Ver logs del container
docker compose -f docker-compose.staging.yml logs [service_name]

# Revisar healthcheck
docker inspect [container_name] | jq '.[0].State.Health'
```

### Problema: Tests fallan
```bash
# Ver logs detallados
docker compose -f docker-compose.staging.yml logs -f agente-api

# Revisar GUIA_TROUBLESHOOTING.md
cat agente-hotel-api/.optimization-reports/GUIA_TROUBLESHOOTING.md
```

### Problema: Métricas no aparecen
```bash
# Verificar Prometheus targets
curl http://localhost:9090/api/v1/targets

# Revisar configuración
cat docker/prometheus/prometheus.yml
```

---

## 📊 Estado Final Esperado

| Componente | Puerto | Status | Verificación |
|------------|--------|--------|--------------|
| agente-api | 8002 | ✅ healthy | curl localhost:8002/health/live |
| postgres | 5432 | ✅ healthy | docker exec postgres-staging pg_isready |
| redis | 6379 | ✅ healthy | docker exec redis-staging redis-cli ping |
| prometheus | 9090 | ✅ running | curl localhost:9090/-/healthy |
| grafana | 3000 | ✅ running | curl localhost:3000/api/health |
| alertmanager | 9093 | ✅ running | curl localhost:9093/-/healthy |
| jaeger | 16686 | ✅ running | curl localhost:16686/ |

---

## 📋 Próximos Pasos (DÍA 3.6-7)

**Después de completar DÍA 3.5:**

1. **Validación Staging** (2 días)
   - Ejecutar test suite completo
   - Validar métricas vs BASELINE_METRICS.md
   - Revisar alertas (debe haber 0)

2. **Deploy Producción** (DÍA 3.6-7)
   - Documento: GUIA_MERGE_DEPLOYMENT.md (sección "Deploy Production")
   - Duración: 2-4 horas
   - Incluye: Blue-green deployment, smoke tests, monitoring

---

## 📚 Referencias

- **CHECKLIST_STAGING_DEPLOYMENT.md**: Setup completo
- **GUIA_MERGE_DEPLOYMENT.md**: Workflow DÍA 3.5
- **GUIA_TROUBLESHOOTING.md**: Debug procedures
- **BASELINE_METRICS.md**: SLOs y benchmarks esperados

---

**Última Actualización**: 23-OCT-2025  
**Próxima Revisión**: Después de completar DÍA 3.5
