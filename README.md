# 🏨 SIST_AGENTICO_HOTELERO - Sistema de Agente Hotelero IA

[![Deployment Readiness](https://img.shields.io/badge/deployment-staging--ready-yellow)](https://github.com/eevans-d/SIST_AGENTICO_HOTELERO)
[![Coverage](https://img.shields.io/badge/coverage-22%25-red)](./agente-hotel-api/htmlcov/index.html)
[![Docker](https://img.shields.io/badge/docker-compose-blue)](./agente-hotel-api/docker-compose.yml)

**Sistema multiagente de IA para automatización de recepción hotelera** con integración WhatsApp, Gmail, NLP y PMS (QloApps).

---

## 📋 Estado del Proyecto

**Versión:** 0.1.0  
**Estado Actual:** 72% completo - STAGING READY con PMS mock  
**Branch Principal:** `feature/dlq-h2-green`

### Completitud por Componente

| Componente | Estado | Completitud |
|-----------|---------|-------------|
| Infraestructura Docker | ✅ Funcional | 95% |
| Backend Core (FastAPI) | ✅ Funcional | 90% |
| PMS Adapter (Mock) | ✅ Funcional | 100% |
| PMS Adapter (QloApps) | ✅ Funcional | 85% |
| WhatsApp Integration | ✅ Funcional | 90% |
| Gmail Integration | ✅ Funcional | 85% |
| NLP Engine (Rasa) | ✅ Funcional | 85% |
| Audio Processing (Whisper) | ✅ Funcional | 90% |
| Observabilidad | ✅ Funcional | 90% |
| Tests & QA | ❌ Insuficiente | 22% |

---

## 🚀 Quick Start

### Prerequisitos

- Docker & Docker Compose
- Python 3.12+
- Poetry (gestor de dependencias)

### Levantar Stack Local (ETAPA 1)

```bash
cd agente-hotel-api

# 1. Configurar entorno
cp .env.example .env
# Editar .env: PMS_TYPE=mock, DEBUG=true

# 2. Levantar servicios
make docker-up

# 3. Verificar salud
make health
curl http://localhost:8002/health/live
curl http://localhost:8002/health/ready

# 4. Ver dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
```

---

## 📚 Documentación Principal

- **[RESUMEN_EJECUTIVO_DEFINITIVO.md](./RESUMEN_EJECUTIVO_DEFINITIVO.md)** - Análisis exhaustivo del sistema (LEER PRIMERO)
- **[MASTER_PROJECT_GUIDE.md](./MASTER_PROJECT_GUIDE.md)** - Guía maestra del proyecto
- **[agente-hotel-api/INDEX.md](./agente-hotel-api/INDEX.md)** - Índice completo de documentación técnica
- **[.github/copilot-instructions.md](./.github/copilot-instructions.md)** - Instrucciones para AI Agents

### Documentación Técnica

- **[README-Infra.md](./agente-hotel-api/README-Infra.md)** - Infraestructura y observabilidad
- **[README-Database.md](./agente-hotel-api/README-Database.md)** - Base de datos y migraciones
- **[docs/supabase/](./agente-hotel-api/docs/supabase/)** - Integración Supabase
- **[docs/guides/](./agente-hotel-api/docs/guides/)** - Guías de desarrollo

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│   WhatsApp/     │
│   Gmail         │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Message  │
    │ Gateway  │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ Orchestrator  │
    │ (Core Logic)  │
    └───┬───┬───┬───┘
        │   │   │
    ┌───▼┐ ┌▼──┐ ┌▼────┐
    │NLP │ │PMS│ │Audio│
    │    │ │   │ │Proc │
    └────┘ └───┘ └─────┘
```

**Servicios Docker:**
- `agente-api` - FastAPI backend
- `postgres` - Base de datos
- `redis` - Cache & locks
- `prometheus` - Métricas
- `grafana` - Dashboards
- `alertmanager` - Alertas
- `jaeger` - Tracing distribuido
- `nginx` - Proxy reverso
- `qloapps` (opcional) - PMS real

---

## 🧪 Testing

```bash
# Tests unitarios
make test-unit

# Tests de integración
make test-integration

# Cobertura
make coverage-report
# Ver: htmlcov/index.html

# Smoke tests
make perf-smoke

# Tests DLQ
pytest tests/unit/test_dlq_service.py -v
```

**Estado Actual:**
- 177 archivos de test
- 245 clases de test
- Cobertura: 22% (objetivo: 70%+)

---

## 📊 Observabilidad

### Dashboards Disponibles

- **Grafana**: http://localhost:3000
  - Dashboard de Orchestrator
  - Dashboard de PMS Adapter
  - Dashboard de Circuit Breaker
  - Dashboard de Compliance

- **Prometheus**: http://localhost:9090
  - Métricas de aplicación
  - Alertas configuradas
  - SLO targets

- **Jaeger**: http://localhost:16686
  - Traces distribuidos
  - Correlación de requests
  - PII redaction automática

### Métricas Clave

```promql
# Latencia P95
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Circuit breaker state
pms_circuit_breaker_state
```

---

## 🔒 Seguridad

- JWT authentication
- Rate limiting (120 req/min per IP)
- Security headers (HSTS, CSP, COOP, COEP)
- PII redaction en traces
- Secrets rotation ready
- OWASP Top 10 validation

```bash
# Security scans
make security-fast        # Trivy HIGH/CRITICAL
make secret-scan-strict   # Secret detection
make owasp-scan          # OWASP Top 10
```

---

## 🛠️ Desarrollo

### Estructura del Proyecto

```
agente-hotel-api/
├── app/
│   ├── core/           # Settings, middleware, logging
│   ├── services/       # Business logic
│   ├── routers/        # API endpoints
│   ├── models/         # Pydantic schemas + ORM
│   └── monitoring/     # Metrics definitions
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── chaos/
├── docker/             # Config files for services
├── docs/               # Documentation
└── scripts/            # Automation scripts
```

### Comandos Útiles

```bash
# Desarrollo
make install        # Instalar dependencias
make fmt           # Formatear código
make lint          # Linting
make quick-check   # Lint + unit tests

# Docker
make docker-up     # Levantar stack
make docker-down   # Detener stack
make logs          # Ver logs

# Database
make db-upgrade    # Aplicar migraciones
make supabase-validate  # Validar Supabase

# Deployment
make preflight     # Validación pre-deployment
make deploy-staging     # Deploy a staging
```

---

## 📈 Roadmap

### ETAPA 1: Staging Local (Actual)
- ✅ Stack Docker funcional
- ✅ Health checks validados
- ✅ PMS mock operativo
- ⏳ Smoke tests (en progreso)
- ⏳ Cobertura 40%+ (pendiente)

### ETAPA 2: Producción
- Integración QloApps real
- WhatsApp Business Account aprobado
- Gmail OAuth2 configurado
- Cobertura 70%+
- Load testing 500 RPS
- Security audit completo

**Tiempo Estimado:** 6-8 semanas para producción completa

---

## 🤝 Contribución

Ver [CONTRIBUTING.md](./agente-hotel-api/CONTRIBUTING.md)

---

## 📝 Licencia

Proyecto privado - Todos los derechos reservados

---

## 📞 Soporte

- **Documentación**: Ver `docs/` y `MASTER_PROJECT_GUIDE.md`
- **Issues**: GitHub Issues
- **Logs**: `docker-compose logs agente-api`

---

**Última Actualización:** 2025-11-17  
**Mantenido por:** eevans-d
