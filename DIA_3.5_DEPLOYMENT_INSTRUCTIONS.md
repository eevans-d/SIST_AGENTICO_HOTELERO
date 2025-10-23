# 🚀 DÍA 3.5 - STAGING DEPLOYMENT INSTRUCTIONS

**Generated**: 2025-10-23  
**Status**: ✅ FASE 2 COMPLETA - Sistema listo para deploy  
**Estimated Time**: 30-40 minutos más para deployment

---

## 📋 CHECKLIST PRE-DEPLOY

Antes de ejecutar `docker compose up`, verifica:

- ✅ `.env.staging` creado con secrets
- ✅ `docker-compose.staging.yml` creado con 7 servicios
- ✅ `docker/postgres-init.sql` creado
- ✅ `scripts/seed_data.py` creado
- ✅ `scripts/smoke_tests.py` creado
- ✅ 2GB RAM mínimo disponible
- ✅ Puertos libres: 8002, 5432, 6379, 9090, 3000, 9093, 16686

---

## 🎯 PRÓXIMOS PASOS - FASE 3 a 6

### FASE 3: Deploy 7 Servicios (30-40 min)

```bash
# Paso 1: Navegar al directorio
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO

# Paso 2: Construir imagen de agente-api
docker build -f agente-hotel-api/Dockerfile.production -t agente-api:staging ./agente-hotel-api

# Paso 3: Iniciar todos los servicios
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Paso 4: Verificar que todos están levantados
docker compose -f docker-compose.staging.yml ps

# Esperado:
# CONTAINER ID   IMAGE               STATUS                NAMES
# ...            agente-api:staging   Up (healthy)         agente-api-staging
# ...            postgres:14-alpine   Up (healthy)         postgres-staging
# ...            redis:7-alpine       Up (healthy)         redis-staging
# ...            prom/prometheus      Up                   prometheus-staging
# ...            grafana/grafana      Up                   grafana-staging
# ...            prom/alertmanager    Up                   alertmanager-staging
# ...            jaegertracing/*      Up                   jaeger-staging
```

**URLs Disponibles después del deploy**:
- API: http://localhost:8002
- Health: http://localhost:8002/health/live
- Metrics: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Jaeger UI: http://localhost:16686
- AlertManager: http://localhost:9093

---

### FASE 4: Seed Data + Smoke Tests (20 min)

```bash
# Paso 1: Instalar dependencias Python (si no están instaladas)
cd agente-hotel-api
poetry install --all-extras --no-root

# Paso 2: Cargar seed data
cd ..
python scripts/seed_data.py

# Esperado:
# ✅ Database schema created successfully
# ✅ Seeded 3 tenants
# ✅ Seeded 10 users across 3 tenants
# ✅ Seeded 15 rooms
# ✅ ALL SEED DATA LOADED SUCCESSFULLY

# Paso 3: Ejecutar smoke tests
python scripts/smoke_tests.py

# Esperado:
# ✅ ALL SMOKE TESTS PASSED! System ready for operation
# Success Rate: 100%
```

---

### FASE 5: Setup Monitoring (15 min)

```bash
# Los dashboards y reglas de alertas se configuran automáticamente via:
# 1. docker/prometheus/prometheus.yml - Scrape config
# 2. docker/grafana/provisioning/ - Dashboards automáticos
# 3. docker/alertmanager/config.yml - Alert rules

# Verificar Prometheus está scrapeando métricas
curl http://localhost:9090/api/v1/query?query=up

# Esperado: JSON con status="success"

# Acceder a Grafana y ver dashboards
open http://localhost:3000
# Login: admin/admin
```

---

### FASE 6: Performance Benchmarks (15 min)

```bash
# Ejecutar benchmark de latencia
curl -w "@scripts/curl_benchmark.txt" http://localhost:8002/health/live

# Verificar P95 latency en Prometheus
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, http_request_duration_seconds_bucket)'

# Esperado: < 300ms para P95
```

---

## 🐛 Troubleshooting

**Si algún contenedor falla:**

```bash
# Ver logs de un servicio específico
docker compose -f docker-compose.staging.yml logs agente-api

# Reiniciar un servicio
docker compose -f docker-compose.staging.yml restart agente-api

# Detener todo
docker compose -f docker-compose.staging.yml down

# Limpiar volúmenes (CUIDADO: borra datos)
docker compose -f docker-compose.staging.yml down -v
```

**Si PostgreSQL no inicia:**

```bash
# Verificar conexión manualmente
psql -h localhost -U agente_user -d agente_hotel_staging -c "SELECT 1"

# Si falla, revisar logs
docker logs postgres-staging
```

**Si Redis no responde:**

```bash
# Verificar conexión
redis-cli -h localhost ping

# Esperado: PONG
```

---

## ✅ Criterios de Éxito

- ✅ Todos los 7 servicios levantados
- ✅ Health checks pasando 100%
- ✅ 3 tenants + 10 users + 15 rooms cargados
- ✅ 6/6 smoke tests pasando
- ✅ Prometheus scrapeando métricas
- ✅ Grafana dashboards visible
- ✅ Jaeger UI mostrando traces
- ✅ P95 latency < 300ms

---

## 📊 Comandos Útiles

```bash
# Ver estado de todos los servicios
docker compose -f docker-compose.staging.yml ps

# Ver logs en vivo
docker compose -f docker-compose.staging.yml logs -f agente-api

# Ver uso de recursos
docker stats

# Verificar conectividad entre servicios
docker compose -f docker-compose.staging.yml exec agente-api ping postgres

# Acceder a PostgreSQL
docker compose -f docker-compose.staging.yml exec postgres psql -U agente_user -d agente_hotel_staging

# Acceder a Redis CLI
docker compose -f docker-compose.staging.yml exec redis redis-cli
```

---

## 🎯 Próximos Pasos después de Staging

1. **DÍA 3.6**: Performance Testing & Optimization
2. **DÍA 3.7**: Load Testing & Stress Testing
3. **DÍA 4.0**: Production Deployment Prep
4. **DÍA 4.1**: Production Deployment

---

**Last Updated**: 2025-10-23  
**Deployment Status**: READY FOR PHASE 3
