# 🚀 DÍA 3.5 - DEPLOY A STAGING (25-26 OCT 2025)

**Status**: ⏳ PRÓXIMO (Esperando validación CI)  
**Prerequisito**: CI green en main + PR #11 mergeado ✅  
**Duración Estimada**: 2-4 horas  
**Setup Inicial**: 15-20 minutos  

---

> Documento deprecado.

  }' | jq .

# Esperado: Response con intent detectado
```

**4.3 Security Tests (4 bloqueantes)**
# Test 5: Tenant Isolation
# Ver CHECKLIST_STAGING_DEPLOYMENT.md (línea 800+)


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
