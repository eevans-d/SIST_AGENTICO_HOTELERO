# 🤖 GitHub Agente Hotelero IA Documentation

Welcome to the Agente Hotelero IA project documentation for AI agents, developers, and contributors.

## 📚 Documentation Files

### For AI Agents (🤖 Priority Files)

1. **[copilot-instructions.md](./copilot-instructions.md)** - Complete Technical Reference
   - System architecture (7-service Docker stack)
   - 5 core patterns with detailed examples
   - All services, workflows, and integrations
   - **Length**: 684 lines | **Read Time**: 45 min
   - **When to Use**: Understanding the complete system

2. **[AI-AGENT-QUICKSTART.md](./AI-AGENT-QUICKSTART.md)** - Quick Start Guide
   - 30-second project overview
   - First steps to productivity (30 min)
   - Common AI agent tasks with code patterns
   - Testing, debugging, and learning path
   - **Length**: 362 lines | **Read Time**: 15 min
   - **When to Use**: Starting work on the project

3. **[AI-AGENT-CONTRIBUTING.md](./AI-AGENT-CONTRIBUTING.md)** - Contribution Guidelines
   - Pre-commit checklist (make fmt, lint, test)
   - Architecture patterns for different change types
   - Code review checklist (14-point verification)
   - Common mistakes to avoid
   - Commit message format
   - **Length**: 553 lines | **Read Time**: 25 min
   - **When to Use**: Before making any contribution

### For Developers (👨‍💻 Reference Files)

- **[../DEVIATIONS.md](../DEVIATIONS.md)** - Architecture deviations and decisions
- **[../README-Infra.md](../README-Infra.md)** - Infrastructure and monitoring setup
- **[../Makefile](../Makefile)** - 46 development commands
- **[../docs/](../docs/)** - Operations manuals and runbooks

### For Operations (🔧 Deployment Files)

- **[../docker-compose.yml](../docker-compose.yml)** - Local development stack
- **[../docker-compose.staging.yml](../docker-compose.staging.yml)** - Staging deployment
- **[../scripts/deploy-staging.sh](../scripts/deploy-staging.sh)** - Automated deployment
- **[../scripts/](../scripts/)** - Backup, restore, health checks

---

## 🚀 Quick Start (5 Minutes)

### 1. Read This First
```bash
# For AI agents starting new work
cat .github/AI-AGENT-QUICKSTART.md | head -50

# For understanding full system
cat .github/copilot-instructions.md | head -100
```

### 2. Start Local Environment
```bash
cd agente-hotel-api
make dev-setup      # Creates .env
make docker-up      # Starts 7 services
make health         # Verify all healthy
```

### 3. Make Your First Change
```bash
# Run tests
make test           # Should see 28+ tests passing

# Make a change
# ... edit app/services/orchestrator.py ...

# Verify before commit
make fmt            # Format
make lint           # Lint
make test           # Test
git commit -m "FEAT: Your feature"
```

---

## 📋 Key Files by Use Case

### I want to...

**Understand the architecture**
→ Read: `copilot-instructions.md` → "Core Patterns" section

**Get started quickly**
→ Read: `AI-AGENT-QUICKSTART.md` → "First Steps"

**Contribute code**
→ Read: `AI-AGENT-CONTRIBUTING.md` → "Pre-Commit Checklist"

**Add a new intent handler**
→ Read: `AI-AGENT-QUICKSTART.md` → "Tarea: Agrega una nueva intención NLP"

**Fix a failing test**
→ Read: `AI-AGENT-QUICKSTART.md` → "Tarea: Arregla el error en el test X"

**Add monitoring metrics**
→ Read: `AI-AGENT-CONTRIBUTING.md` → "Metrics Contribution Guidelines"

**Debug an issue**
→ Read: `AI-AGENT-QUICKSTART.md` → "Debugging Common Issues"

**Deploy to staging**
→ Read: `../CHECKLIST-DEPLOYMENT-MANANA.md` (staging checklist)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    WhatsApp/Gmail                    │
│                    (Meta Cloud API)                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              agente-api (FastAPI)                   │
│         POST /api/webhooks/whatsapp                 │
│  ┌─────────────────────────────────────────────┐   │
│  │  MessageGateway → UnifiedMessage            │   │
│  │  ↓                                          │   │
│  │  NLP Engine → Intent Detection              │   │
│  │  ↓                                          │   │
│  │  Orchestrator → Intent Handler Dispatcher   │   │
│  │  ↓                                          │   │
│  │  PMS Adapter (Circuit Breaker + Cache)      │   │
│  │  ↓                                          │   │
│  │  Session Manager → Postgres                 │   │
│  │  ↓                                          │   │
│  │  TemplateService → Response                 │   │
│  └─────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────┬───────────┘
               │                          │
               ▼                          ▼
         ┌──────────────┐      ┌──────────────────┐
         │  PostgreSQL  │      │  Redis           │
         │  (Sessions)  │      │  (Cache/Locks)   │
         └──────────────┘      └──────────────────┘
         
┌────────────────────────────────────────────────────┐
│          Observability Stack                       │
│  Prometheus (metrics) + Grafana (dashboards)       │
│  AlertManager (alerts) + Jaeger (tracing)          │
└────────────────────────────────────────────────────┘
```

**Key Services**:
- **Orchestrator**: Coordinates message flow end-to-end
- **PMS Adapter**: Interfaces with QloApps hotel PMS (resilience + caching)
- **Session Manager**: Persists conversation state for multi-turn chats
- **NLP Engine**: Intent detection and entity extraction
- **Message Gateway**: Normalizes multi-channel communications

---

## 🧪 Testing Strategy

**Coverage Target**: 70% overall, 85% in critical services

**Test Categories**:
- **Unit Tests** (`tests/unit/`) - Service logic isolation (mocked dependencies)
- **Integration Tests** (`tests/integration/`) - Cross-service flows (shared fixtures)
- **E2E Tests** (`tests/e2e/`) - Complete reservation flows (full stack)
- **Chaos Tests** (`tests/chaos/`) - Resilience scenarios (circuit breaker, failures)

**Run Tests**:
```bash
make test              # All tests with coverage
make test tests/unit/  # Just unit tests
pytest -k "my_test" --verbose  # Specific test
```

---

## 📊 Deployment Status

**Current**: 8.9/10 deployment readiness ✅
- ✅ 28 tests passing
- ✅ 31% coverage
- ✅ 0 CVE CRITICAL vulnerabilities
- ✅ 0 linting errors
- ✅ 7/7 Docker services health-checked
- ✅ Automated deployment scripts ready
- ⏳ Staging deployment scheduled (tomorrow 09:00)

---

## 🎯 Common AI Agent Workflows

### Workflow 1: Fix a Bug
1. Read: `AI-AGENT-QUICKSTART.md` → "Tarea: Arregla el error"
2. Find failing test
3. Add logging to understand issue
4. Implement fix
5. Run `make test` to verify
6. Commit with `FIX:` prefix

### Workflow 2: Add a Feature
1. Read: `AI-AGENT-CONTRIBUTING.md` → "Cambios en `app/services/`"
2. Implement service logic with metrics + logging
3. Create integration test
4. Run `make test` with target coverage
5. Commit with `FEAT:` prefix

### Workflow 3: Improve Performance
1. Profile with Prometheus metrics
2. Identify bottleneck (DB query, external API, etc.)
3. Implement optimization (caching, indexing, etc.)
4. Verify with before/after metrics
5. Run `make test` to ensure no regression
6. Commit with `PERF:` prefix

---

## 📞 FAQ

**Q: Where do I start?**  
A: Read `AI-AGENT-QUICKSTART.md` first (15 min), then run local setup (10 min).

**Q: How do I add a new intent?**  
A: See `AI-AGENT-QUICKSTART.md` → "Tarea: Agrega una nueva intención NLP"

**Q: What's the pre-commit checklist?**  
A: See `AI-AGENT-CONTRIBUTING.md` → "Pre-Commit Checklist"

**Q: How do I debug?**  
A: See `AI-AGENT-QUICKSTART.md` → "Debugging Common Issues"

**Q: Where are the runbooks?**  
A: See `../docs/runbooks/` directory for operations manuals

**Q: How do I understand the metrics?**  
A: See `../README-Infra.md` with Prometheus queries

---

## 🔗 Document Map

```
.github/
├── README.md ← You are here
├── copilot-instructions.md (684 lines) - Complete technical reference
├── AI-AGENT-QUICKSTART.md (362 lines) - Quick start guide
└── AI-AGENT-CONTRIBUTING.md (553 lines) - Contribution guidelines

../
├── Makefile - 46 development commands
├── docker-compose.yml - Local development
├── docker-compose.staging.yml - Staging deployment
├── DEVIATIONS.md - Architecture decisions
├── README-Infra.md - Monitoring & infrastructure
├── docs/runbooks/ - Operations manuals
└── scripts/ - Deployment automation
```

---

## ✅ Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Architecture | ✅ Complete | 7-service Docker stack |
| Core Services | ✅ Complete | Orchestrator, PMS Adapter, NLP |
| Testing | ⚠️ 31% coverage | Target 70%+ |
| Documentation | ✅ Complete | 684 lines instructions |
| Deployment Scripts | ✅ Complete | Automated staging deploy |
| Monitoring Stack | ✅ Complete | Prometheus, Grafana, Jaeger |
| Local Setup | ✅ Working | Docker Compose with mocks |
| Staging Deploy | ⏳ Ready | Scheduled for tomorrow |

---

## 🚀 Next Steps

1. **If you're new**: Read `AI-AGENT-QUICKSTART.md`
2. **If contributing**: Read `AI-AGENT-CONTRIBUTING.md`
3. **If deploying**: Check `../CHECKLIST-DEPLOYMENT-MANANA.md`
4. **If debugging**: Check `AI-AGENT-QUICKSTART.md` → Debugging section

---

**Last Updated**: 2025-10-17  
**Status**: ✅ Ready for AI agent collaboration  
**Maintained By**: Backend AI Team  

---

## 📖 How to Read This Documentation

### For AI Agents (30-minute introduction)
1. This file (5 min) - Overview
2. `AI-AGENT-QUICKSTART.md` (15 min) - Quick start
3. Run local setup (10 min) - Hands-on
4. Make first commit (5 min) - Verify workflow

### For AI Agents (2-hour deep dive)
1. `copilot-instructions.md` (45 min) - Architecture
2. `AI-AGENT-CONTRIBUTING.md` (25 min) - Guidelines
3. Explore code (30 min) - Key services
4. Write a test (20 min) - Hands-on

### For AI Agents (4-week mastery path)
- Week 1: Read all documentation + local setup
- Week 2: Fix 3 failing tests + add 1 metric
- Week 3: Implement new intent handler (3-4 hours)
- Week 4: Full feature with tests (85%+ coverage)

---

**Questions?** Start with `AI-AGENT-QUICKSTART.md` → FAQ section.
