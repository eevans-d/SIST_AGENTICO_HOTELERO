# 🏨 Agente Hotelero IA

![CI](https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/actions/workflows/ci.yml/badge.svg)
[![Tests](https://img.shields.io/badge/tests-46%2F46%20passing-success)](agente-hotel-api/tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25-brightgreen)](VALIDATION_REPORT_FASE_A.md)
[![Phase](https://img.shields.io/badge/phase-5%20complete-blue)](EXECUTIVE_SUMMARY.md)
[![Dev](https://img.shields.io/badge/dev-Phase%20A%20complete-success)](SESSION_SUMMARY_2025-10-04.md)
[![Status](https://img.shields.io/badge/status-deployment%20ready-green)](STATUS_DEPLOYMENT.md)

**Multi-service AI hotel receptionist** built with FastAPI, handling guest communications via WhatsApp, Gmail, and other channels. Integrates with QloApps PMS for reservation management using Docker Compose orchestration.

---

## 🎯 Quick Links

| 📚 Documentation | 🚀 Deployment | 🤖 AI Guides | 🛠️ Development |
|------------------|---------------|--------------|----------------|
| [📖 Documentation Index](DOCUMENTATION_INDEX.md) | [🚀 Deployment Plan](DEPLOYMENT_ACTION_PLAN.md) | [🤖 AI Instructions](.github/copilot-instructions.md) | [🧪 Phase A Report](VALIDATION_REPORT_FASE_A.md) |
| [🏗️ Infrastructure Guide](agente-hotel-api/README-Infra.md) | [✅ Deployment Status](STATUS_DEPLOYMENT.md) | [💡 Copilot Prompts](docs/) | [📋 Session Summary](SESSION_SUMMARY_2025-10-04.md) |
| [📊 Executive Summary](EXECUTIVE_SUMMARY.md) | [✅ Merge Complete](MERGE_COMPLETED.md) | [🔧 Contributing](agente-hotel-api/CONTRIBUTING.md) | [🗓️ Execution Plan](PLAN_EJECUCION_INMEDIATA.md) |

---

## ✨ Phase 5 Complete - Key Features

### 🎯 Multi-Tenancy System
- Dynamic tenant resolution with Postgres backend
- In-memory caching with auto-refresh
- Admin API endpoints for tenant management
- Feature flag gated for gradual rollout

### 🚦 Governance Automation
- **Preflight Risk Assessment**: Automated deployment readiness scoring
- **Canary Diff Analysis**: Baseline vs deployment comparison
- **CI Integration**: GitHub Actions workflows for automated checks

### 📊 Enhanced Observability
- 20+ Prometheus metrics (NLP, tenancy, gateway)
- Structured logging with correlation IDs
- Circuit breaker monitoring for PMS adapter
- Grafana dashboards + AlertManager

### 🎛️ Feature Flags
- Redis-backed configuration service
- Runtime toggles without redeployment
- Local cache for performance

---

## 🚀 Quick Start

### Prerequisites
- **Docker** and **Docker Compose**
- **Python 3.11+** (optional for local development)
- **Make** (for automation)

### 1. Clone Repository
```bash
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO
```

### 2. Setup Environment
```bash
cd agente-hotel-api
make dev-setup     # Creates .env from .env.example
make install       # Install dependencies
```

### 3. Start Services
```bash
# Option A: With Mock PMS (local dev)
make docker-up

# Option B: With Real PMS (production)
docker compose --profile pms up -d
```

### 4. Verify Health
```bash
make health        # Check all services
make logs          # View logs
```

### 5. Access Services
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

---

## �️ Development Environment

### Development Setup (Docker-based)

**New!** Complete development environment with hot-reload and testing tools:

```bash
cd agente-hotel-api
docker compose -f docker-compose.dev.yml up -d
```

**Services:**
- PostgreSQL (port 5434)
- Redis (port 6382)  
- Agente API (port 8000) with hot-reload

**Features:**
- ✅ 46/46 tests passing in 2.63s
- ✅ 73% code coverage
- ✅ Hot-reload (<2s)
- ✅ All dev dependencies included (pytest-cov, pytest-benchmark, pytest-watch)

**Quick Commands:**
```bash
# Run tests
docker compose -f docker-compose.dev.yml exec -T agente-api \
  python -m pytest tests/ -v

# Run tests with coverage
docker compose -f docker-compose.dev.yml exec -T agente-api \
  python -m pytest tests/ --cov=app --cov-report=term-missing

# Shell access
docker compose -f docker-compose.dev.yml exec agente-api /bin/bash
```

**Documentation:**
- [Phase A Validation Report](VALIDATION_REPORT_FASE_A.md) - Complete testing results
- [Session Summary](SESSION_SUMMARY_2025-10-04.md) - Development status
- [Execution Plan](PLAN_EJECUCION_INMEDIATA.md) - Detailed roadmap

---

## �📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX (Reverse Proxy)                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
┌─────▼──────┐       ┌────────▼────────┐
│  WhatsApp  │       │     Gmail       │
│  Webhooks  │       │   Integration   │
└─────┬──────┘       └────────┬────────┘
      │                       │
      └───────────┬───────────┘
                  │
         ┌────────▼────────┐
         │  Message        │
         │  Gateway        │
         │  (Normalize)    │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Orchestrator   │
         │  (Workflow)     │
         └────────┬────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼─────┐ ┌──▼──┐  ┌────▼──────┐
│ NLP       │ │ PMS │  │ Template  │
│ Engine    │ │ API │  │ Service   │
└───────────┘ └─────┘  └───────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼─────┐ ┌──▼──┐  ┌────▼──────┐
│ Postgres  │ │Redis│  │Prometheus │
│ (Sessions)│ │Cache│  │ (Metrics) │
└───────────┘ └─────┘  └───────────┘
```

**For detailed architecture**: See [README-Infra.md](agente-hotel-api/README-Infra.md)

---

## 🛠️ Development

### Common Commands
```bash
# Setup
make dev-setup              # Copy .env.example to .env
make install                # Install dependencies

# Development
make test                   # Run all tests (46/46)
make lint                   # Lint code (ruff)
make fmt                    # Format code
make preflight              # Risk assessment

# Docker
make docker-up              # Start all services
make docker-down            # Stop all services
make health                 # Health checks
make logs                   # View logs

# Quality
make security-fast          # Security scan
make canary-diff            # Canary analysis
```

**For complete command reference**: See [Makefile](agente-hotel-api/Makefile) (46 targets)

---

## 📚 Documentation

### 🎯 Start Here
- **New to the project?** → [Documentation Index](DOCUMENTATION_INDEX.md)
- **Want to deploy?** → [Deployment Action Plan](DEPLOYMENT_ACTION_PLAN.md)
- **Using AI assistants?** → [Copilot Instructions](.github/copilot-instructions.md)
- **Need architecture details?** → [Infrastructure Guide](agente-hotel-api/README-Infra.md)

### 📖 Role-Based Guides

| Role | Essential Docs |
|------|----------------|
| **Management** | [Executive Summary](EXECUTIVE_SUMMARY.md), [Deployment Status](STATUS_DEPLOYMENT.md) |
| **Developers** | [Copilot Instructions](.github/copilot-instructions.md), [Contributing](agente-hotel-api/CONTRIBUTING.md) |
| **DevOps/SRE** | [Deployment Plan](DEPLOYMENT_ACTION_PLAN.md), [Operations Manual](agente-hotel-api/docs/OPERATIONS_MANUAL.md) |
| **QA/Testers** | [DOD Checklist](agente-hotel-api/docs/DOD_CHECKLIST.md), [Test Documentation](agente-hotel-api/tests/) |
| **AI Assistants** | [Copilot Instructions](.github/copilot-instructions.md), [Architecture](agente-hotel-api/README-Infra.md) |

---

## 🧪 Testing

### Test Suite
```bash
make test  # Run all 46 tests
```

**Test Coverage**: 46/46 passing (100%)
- **Unit Tests**: Service-level testing
- **Integration Tests**: Cross-service workflows
- **E2E Tests**: Complete reservation flows
- **Mock Tests**: PMS mock server

**Test Organization**:
```
tests/
├── unit/           # 20+ unit tests
├── integration/    # 10+ integration tests
├── e2e/            # 5+ end-to-end tests
├── mocks/          # PMS mock server
└── performance/    # k6 smoke tests
```

---

## 🔒 Security

### Security Features
- ✅ Rate limiting (SlowAPI + Redis)
- ✅ Security headers middleware
- ✅ Input validation and sanitization
- ✅ Secret management via environment variables
- ✅ Circuit breaker for external services
- ✅ HMAC signature validation (WhatsApp webhooks)

### Security Scanning
```bash
make security-fast  # Trivy scan (HIGH/CRITICAL)
make lint           # Includes gitleaks secret scan
```

---

## 📈 Monitoring & Observability

### Metrics (Prometheus)
- Request rate and latency by endpoint
- PMS circuit breaker state
- Tenant resolution metrics
- NLP confidence scores
- Message normalization by channel

### Dashboards (Grafana)
- Service health overview
- Performance metrics
- Business metrics
- Alert visualization

### Logging (Structlog)
- JSON output for parsing
- Correlation IDs for tracing
- Automatic timing for external APIs

---

## 🚀 Deployment

### Current Status
- ✅ **Phase 5 Complete**: All features merged to main
- ✅ **Tests**: 46/46 passing (100%)
- ✅ **Preflight**: GO (risk score 30.0/50)
- ⚠️ **Configuration**: Pending production secrets
- ⏳ **Deployment**: Ready for staging

### Next Steps
1. **Configure production secrets** (.env)
2. **Deploy to staging** (4-8 hours + monitoring)
3. **Deploy to production** (2-4 hours + 48h monitoring)

**Full deployment guide**: See [Deployment Action Plan](DEPLOYMENT_ACTION_PLAN.md)

---

## 🤝 Contributing

We welcome contributions! Please see:
- [Contributing Guide](agente-hotel-api/CONTRIBUTING.md)
- [Definition of Done](agente-hotel-api/docs/DOD_CHECKLIST.md)
- [Copilot Instructions](.github/copilot-instructions.md) (for AI-assisted development)

### Development Workflow
1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run quality checks: `make test && make lint && make fmt`
5. Submit pull request

---

## 📞 Support & Resources

### Documentation
- 📚 [Complete Documentation Index](DOCUMENTATION_INDEX.md)
- 🤖 [AI Agent Instructions](.github/copilot-instructions.md)
- 🏗️ [Infrastructure Guide](agente-hotel-api/README-Infra.md)
- 🚨 [Troubleshooting Guide](TROUBLESHOOTING_AUTOCURACION.md)

### Project Links
- **Repository**: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO
- **Issues**: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/issues
- **PR #9** (Phase 5): https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/pull/9

---

## 📊 Project Status

```
╔════════════════════════════════════════════════════════╗
║              PHASE 5 COMPLETION STATUS                 ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  🎯 Phase: 5 (Multi-Tenancy & Governance) ✅           ║
║  📦 Status: DEPLOYMENT READY                           ║
║  🧪 Tests: 46/46 (100%) ✅                             ║
║  📝 Docs: COMPLETE ✅                                   ║
║  🚦 Preflight: GO (30.0/50) ✅                         ║
║  🔐 Security: VALIDATED ✅                             ║
║                                                        ║
║  Next: Production Configuration ⚙️                     ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

---

## 📄 License

**Private Repository** - All rights reserved

---

## 🎉 Acknowledgments

Built with:
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation
- **Redis** - Caching and feature flags
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards and visualization
- **Docker** - Containerization
- **GitHub Copilot** - AI pair programming

---

**Last Updated**: October 1, 2025  
**Version**: Phase 5 Complete  
**Status**: ✅ Deployment Ready
   - Escaneo seguridad rápido (Trivy modo light)
   - Build de imagen Docker (verificación)

Badge arriba indica estado de la última ejecución en rama `main`.

### Próximos (roadmap)
- Workflow `deploy.yml` (manual dispatch) para publicar imagen versionada
- Dependabot / Renovate para actualización de dependencias
- Escaneo deep (Trivy fs + SBOM) en pipeline nocturno

## Notas
- Logging estructurado con structlog y correlation IDs
- Circuit breaker y caché para PMS
- Rate limiting con Redis

Para más detalles ver `agente-hotel-api/README-Infra.md` y `.github/copilot-instructions.md`.
