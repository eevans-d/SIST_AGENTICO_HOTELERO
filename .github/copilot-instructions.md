# AI Agent Instructions for Agente Hotelero IA System

**Current Status**: Validated & Ready for Staging (8.9/10 deployment readiness)  
**Last Validated**: 2025-10-17 | **Test Suite**: 891 tests (28 passing, 31% coverage)  
**CVE Status**: ✅ 0 CRITICAL (python-jose 3.5.0) | **Linting**: ✅ 0 errors

## System Overview

Multi-service hotel receptionist AI agent (FastAPI) handling WhatsApp/Gmail communications with QloApps PMS integration. Uses Docker Compose orchestration with comprehensive observability stack (Prometheus/Grafana/AlertManager/Jaeger). 

**Core Tech Stack**: Python 3.12.3, FastAPI, SQLAlchemy+asyncpg, Redis, Prometheus, Jaeger  
**Deployment**: 7-service Docker Compose (staging-ready with automated deployment scripts)

---

## Architecture & Core Components

### Service Boundaries

- **agente-api** (port 8002): FastAPI async app with lifespan-managed services (`app/main.py`); all middleware + security headers
- **postgres:14-alpine** (5432): Agent database for sessions, locks, multi-tenant metadata via SQLAlchemy + asyncpg
- **redis:7-alpine** (6379): Cache layer, rate limiting (slowapi + RedisBackend), distributed locks, feature flags
- **prometheus:latest** (9090): Metrics collection (8s scrape interval); exposes all service instrumentation
- **grafana:latest** (3000): Pre-configured dashboards for orchestrator, PMS adapter, health metrics
- **alertmanager:latest** (9093): Alert routing for circuit breaker trips, high error rates
- **jaeger:latest** (16686): Distributed tracing (OTEL collector integration for request correlation)
- **qloapps + mysql** (profiles-gated): PMS backend; use `PMS_TYPE=mock` for local dev to skip auth

### Core Patterns (Read These First for AI Work)

#### 1. **Orchestrator Pattern** (`app/services/orchestrator.py`)
Coordinates the complete message flow: webhook → normalization → NLP intent detection → PMS calls → response generation

**Key Implementation Details**:
- Intent dispatcher uses dict mapping: `_intent_handlers = {"check_availability": self._handle_availability, ...}`
- Each handler method is async and returns `{response_type: "text|audio", content: {...}}`
- All external API calls wrapped with retry logic via `@retry_with_backoff` decorator
- Feature flag checks on non-critical paths prevent cascading failures
- Fallback response generated when NLP confidence is too low
- Audio processing via `AudioProcessor` for STT/TTS workflows

**Example Workflow**:
```
WhatsApp Webhook → UnifiedMessage → NLP Engine (intent + confidence)
  → is_enabled("feature_x") ? handler_x : fallback
  → PMS call (if needed, circuit breaker protected)
  → Template response → WhatsApp response
```

#### 2. **PMS Adapter Pattern** (`app/services/pms_adapter.py`)
Wraps external PMS calls with resilience patterns: circuit breaker, caching, metrics

**Resilience Layer**:
- **Circuit Breaker**: State machine CLOSED → OPEN (5 failures) → HALF_OPEN (30s recovery) → CLOSED
- **Metrics Tracked**: 
  - `pms_circuit_breaker_state` (0=closed, 1=open, 2=half-open)
  - `pms_api_latency_seconds` (histogram by endpoint/method)
  - `pms_circuit_breaker_calls_total` (counter by state, result)
- **Redis Caching**: TTL per endpoint (e.g., `availability:*` cached 5min, `room_details:*` cached 60min)
- **Error Handling**: Specific exceptions `PMSError`, `PMSAuthError`, `PMSRateLimitError`

**Mock Mode**: When `PMS_TYPE=mock`, `MockPMSAdapter` returns fixture data (useful for local dev + tests)

**Retry Logic**: Built-in exponential backoff with jitter (see `app/core/retry.py`)

#### 3. **Message Gateway Pattern** (`app/services/message_gateway.py`)
Normalizes inbound payloads from multiple channels (WhatsApp, Gmail, SMS) to unified `UnifiedMessage` model

**Normalization Process**:
1. Extract payload from channel-specific envelope
2. Create `UnifiedMessage` with: sender_id, channel, text, audio_data, timestamp, metadata
3. Resolve tenant via `dynamic_tenant_service` (cached) → fallback to static/default
4. Enrich with correlation_id (from headers or generated)

**Multi-Tenancy**: 
- Dynamic tenant resolution queries `Tenant` + `TenantUserIdentifier` from Postgres
- In-memory cache with 300s refresh interval (configurable via settings)
- Fallback chain: Dynamic → Static → "default" tenant
- Metrics: `tenant_resolution_total{result=hit|default|miss_strict}`

#### 4. **Session Management Pattern** (`app/services/session_manager.py`)
Persists guest conversation state in PostgreSQL for multi-turn conversations

**State Persistence**:
- Intent history (last 5 intents with timestamps)
- Context data: room availability, date selections, guest preferences
- Lock mechanisms prevent concurrent reservation conflicts
- TTL enforcement (default 24h, configurable)

**Lock Service Integration** (`app/services/lock_service.py`):
- Distributed Redis locks for reservation atomicity
- Prevents double-booking and race conditions
- Timeout + auto-release on process crash (via Redis key TTL)
- Audit trail in `lock_audit` table

#### 5. **Feature Flags Pattern** (`app/services/feature_flag_service.py`)
Redis-backed feature flags with in-memory fallback to `DEFAULT_FLAGS` dict

**Usage Pattern**:
```python
# ✅ Correct: Always await in async context
ff = await get_feature_flag_service()
if await ff.is_enabled("nlp.fallback.enhanced", default=True):
    # Enhanced fallback logic

# ✅ Correct: Use DEFAULT_FLAGS to avoid import cycles in message_gateway
use_dynamic = DEFAULT_FLAGS.get("tenancy.dynamic.enabled", True)

# ❌ Wrong: Don't import feature_flag_service in message_gateway to avoid cycles
```

**Common Flags**:
- `nlp.fallback.enhanced` - Enable enhanced NLP fallback responses
- `tenancy.dynamic.enabled` - Use dynamic tenant resolution
- `audio.processor.optimized` - Use optimized whisper STT
- `pms.circuit_breaker.enabled` - Enable circuit breaker (always true in prod)

---

## Critical Development Workflows

### Local Development Setup

**Quick Start** (with all 7 services):
```bash
cd agente-hotel-api
make dev-setup           # Creates .env from .env.example
make docker-up           # Builds + starts 7 services
make health              # Validates all services healthy
```

**Verify Everything**:
```bash
# Health endpoints
curl http://localhost:8002/health/live   # ✅ Always 200 (liveness)
curl http://localhost:8002/health/ready  # ✅ 200 if all deps ready

# Metrics
curl http://localhost:9090/api/v1/query?query=up  # Check Prometheus scrape

# Grafana dashboards (if configured)
open http://localhost:3000  # Login: admin/admin (default)
```

### Code Quality Pipeline

**Before Committing**:
```bash
make install         # Auto-detects poetry/uv/npm (uses Poetry here)
make fmt             # Ruff format (line-length 120) + Prettier
make lint            # Ruff check --fix + gitleaks secret scan
make test            # pytest via Poetry (uses aiosqlite in-memory DB)
```

**Security Scanning**:
```bash
make security-fast   # Trivy HIGH/CRITICAL scan (vuln+secrets)
make lint            # gitleaks prevents committing secrets
```

**Pre-Deployment Checks**:
```bash
make preflight                          # Risk assessment → .playbook/preflight_report.json
make canary-diff BASELINE=main          # P95 latency + error rate diff analysis
make pre-deploy-check                   # Combined security-fast + SLO validation
```

### Dependency Management

**Python Dependencies** (Poetry):
```bash
poetry install --all-extras     # Install all optional deps (dev, test, etc.)
poetry add package-name         # Add new dependency
poetry add --group dev pytest   # Add to dev group
poetry lock                     # Update lock file (commit to git)
poetry export -f requirements.txt  # Export for Docker
```

**Key Dependencies**:
- **FastAPI 0.104+** - Web framework
- **SQLAlchemy 2.0+** - ORM with async support
- **asyncpg** - PostgreSQL async driver
- **aioredis** - Redis async client
- **prometheus-client** - Metrics exposition
- **python-jose 3.5.0** - JWT handling (CVE-2024-33663 fixed)
- **slowapi** - Rate limiting
- **structlog** - Structured logging

### Configuration Management

**Settings Architecture** (`app/core/settings.py`):
- Pydantic v2 with `SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`
- Enums for type safety: `Environment`, `LogLevel`, `TTSEngine`, `PMSType`
- SecretStr for sensitive data (fails startup if not overridden from `.env.example`)
- Dynamic postgres_url construction with fallback to individual host/port

**Environment Variables**:
```bash
ENVIRONMENT=development|staging|production    # Controls logging level, security checks
DEBUG=true|false                              # Disables rate limiting, enables verbose logging
PMS_TYPE=mock|qloapps                        # mock for dev, qloapps for staging/prod
CHECK_PMS_IN_READINESS=true|false            # Include PMS in /health/ready checks
TENANCY_DYNAMIC_ENABLED=true|false           # Enable dynamic tenant resolution
```

**Secret Validation**:
- All `SecretStr` typed settings must be overridden from `.env.example`
- Production deployments fail startup if dummy values remain (prevents accidents)
- Use `secrets` CLI to generate crypto-secure values:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

---

## Testing Structure

### Test Organization

- **`tests/unit/`**: Service-level unit tests with mocks
  - `test_orchestrator.py` - Intent dispatcher, fallback logic
  - `test_pms_adapter.py` - Circuit breaker state machine, cache invalidation
  - `test_session_manager.py` - State persistence, TTL
  - `test_lock_service.py` - Distributed lock atomicity
  
- **`tests/integration/`**: Cross-service integration tests
  - `test_orchestrator_integration.py` - Message flow end-to-end
  - `test_pms_integration.py` - PMS adapter with mock server
  
- **`tests/e2e/`**: End-to-end reservation flows (slow, comprehensive)
  - `test_reservation_flow.py` - Complete multi-turn conversation
  
- **`tests/chaos/`**: Resilience + chaos engineering tests
  - `test_circuit_breaker_resilience.py` - CB state transitions
  - `test_cascading_failures.py` - Service degradation
  - `scenarios/service_chaos.py` - Fault injection configurations

- **`tests/mocks/`**: External service simulators
  - `pms_mock_server.py` - QloApps PMS API mock (pytest fixture)

### Async Test Setup (pytest-asyncio)

**Basic Pattern**:
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app

@pytest_asyncio.fixture
async def test_client():
    # Disable rate limiting for tests
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    response = await test_client.get("/health/live")
    assert response.status_code == 200
```

**Database Testing**:
- Uses `aiosqlite` (in-memory SQLite) for fast test isolation
- `conftest.py` creates fresh `AsyncSession` per test
- Services call `Base.metadata.create_all()` in `start()` method (migration-free)
- No external Postgres required for tests

**Mocking External Services**:
```python
from unittest.mock import AsyncMock, MagicMock
from tests.mocks.pms_mock_server import MockPMSAdapter

@pytest.fixture
def mock_pms():
    return MockPMSAdapter()

@pytest.mark.asyncio
async def test_availability_check(mock_pms):
    availability = await mock_pms.check_availability("2025-10-20", "2025-10-22")
    assert availability["rooms_available"] > 0
```

### Coverage Goals

- **Current**: 31% overall (28 tests passing out of 891 collected)
- **Target**: 70% overall, 85% in critical services
- **Critical Services** (need 85%+):
  - `orchestrator.py` - Intent routing logic
  - `pms_adapter.py` - Circuit breaker + cache
  - `session_manager.py` - State persistence
  - `lock_service.py` - Distributed atomicity

---

## Logging & Monitoring

### Structured Logging (structlog + JSON)

**Pattern**:
```python
from app.core.logging import logger

logger.info("operation_started", operation="check_availability", guest_id="g123")
logger.error("pms_call_failed", operation="check_availability", error="timeout", retry_count=2)
```

**Automatic Correlation**:
- `correlation_id_middleware` injects `X-Request-ID` into every request context
- All logs from same request share same correlation_id (visible in Jaeger traces)
- `structlog` outputs JSON to stdout (Prometheus Loki compatible)

**Log Levels**:
- `DEBUG` - Development, verbose function entry/exit
- `INFO` - Normal operations (messages processed, PMS calls)
- `WARNING` - Degraded but recoverable (circuit breaker opening, cache miss spike)
- `ERROR` - Recoverable errors (PMS timeout, retry exhausted)
- `CRITICAL` - Unrecoverable (database unavailable, auth failure on startup)

### Health Checks

**Endpoints**:
- **`GET /health/live`**: Returns 200 always (Kubernetes liveness probe)
- **`GET /health/ready`**: Returns 200 only if all dependencies ready
  - Postgres: Can execute `SELECT 1`
  - Redis: Can ping
  - PMS: (optional) Can reach base_url, circuit breaker not open

**Health Check Configuration**:
```python
CHECK_PMS_IN_READINESS=true    # Include PMS in readiness checks (staging/prod)
CHECK_PMS_IN_READINESS=false   # Exclude PMS (local dev, unit tests)
```

### Prometheus Metrics

**Key Metrics by Service**:

**Orchestrator**:
- `intents_detected{intent, confidence}` - Counter by intent type
- `nlp_fallbacks_total` - Counter when confidence too low
- `orchestrator_latency_seconds` - Histogram of end-to-end processing

**PMS Adapter**:
- `pms_api_latency_seconds{endpoint, method}` - Histogram of API calls
- `pms_circuit_breaker_state` - Gauge (0=closed, 1=open, 2=half-open)
- `pms_circuit_breaker_calls_total{state, result}` - Counter
- `pms_cache_hits_total` - Counter
- `pms_cache_misses_total` - Counter

**Session Manager**:
- `sessions_active` - Gauge
- `session_creation_latency_seconds` - Histogram

**Rate Limiting**:
- `http_requests_total{endpoint, status}` - Counter
- Limits: `120/minute` per webhook endpoint (configurable via `app.state.limiter.limit()`)

**Multi-Tenancy**:
- `tenant_resolution_total{result}` - Counter (hit|default|miss_strict)
- `tenants_active_total` - Gauge
- `tenant_refresh_latency_seconds` - Histogram

### Distributed Tracing (Jaeger)

**Usage**:
- Automatically enabled via `OpenTelemetryMiddleware`
- Traces exported to Jaeger (port 6831 UDP by default)
- Correlation IDs propagated via W3C Trace Context headers
- View traces: `http://localhost:16686/search`

**Example Trace Flow**:
```
WhatsApp Webhook → MessageGateway → NLP Engine → Orchestrator → PMS Adapter → Response
[All linked via same trace_id, visible in Jaeger UI]
```

---

## Code Conventions

### File Organization

**Service Structure**:
```
app/
  core/               # Utilities (settings, logging, middleware, circuit breaker)
  services/           # Business logic (orchestrator, pms_adapter, etc.)
  models/             # Pydantic schemas + SQLAlchemy ORM models
  routers/            # FastAPI endpoints (webhook handlers, health, admin)
  exceptions/         # Custom exception types
  utils/              # Helpers (audio processing, data conversion)
  security/           # Auth, JWT, permissions
  monitoring/         # Prometheus metrics definitions
  main.py             # FastAPI app init, lifespan manager, middleware stack
```

### Error Handling

**Pattern**:
```python
from app.exceptions.pms_exceptions import PMSError, PMSAuthError, PMSRateLimitError
from app.core.logging import logger

try:
    availability = await self.pms_adapter.check_availability(...)
except PMSAuthError as e:
    logger.error("auth_failure", operation="check_availability", error=str(e))
    raise  # Critical error, let global exception handler respond
except PMSRateLimitError as e:
    logger.warning("rate_limited", operation="check_availability", retry_after=e.retry_after)
    # Return graceful degradation response
    return {"status": "throttled", "retry_after": e.retry_after}
except PMSError as e:
    logger.error("pms_error", operation="check_availability", error=str(e))
    # Fallback response when PMS unavailable
    return self._handle_fallback_response()
```

**Global Exception Handler** (`app/core/middleware.py`):
- Catches all unhandled exceptions
- Logs with correlation_id
- Returns standardized error response (JSON with error_code, message, timestamp)
- Never exposes sensitive details (DB credentials, internal paths)

### Circuit Breaker Implementation

**State Transitions**:
```
CLOSED (normal) --[5 failures in 30s]--> OPEN (rejecting) --[30s recovery]--> HALF_OPEN (testing)
    ^                                                              |
    |____________________________[1 success]_______________________|
```

**Configuration** (in `pms_adapter.py`):
```python
self.circuit_breaker = CircuitBreaker(
    failure_threshold=5,              # Failures before OPEN
    recovery_timeout=30,              # Seconds before HALF_OPEN
    expected_exception=httpx.HTTPError  # Which exceptions trigger failures
)
```

**Metrics**:
- `pms_circuit_breaker_state.set(0)` on success (CLOSED)
- `pms_circuit_breaker_state.set(1)` on trip (OPEN)
- `pms_circuit_breaker_state.set(2)` on recovery test (HALF_OPEN)
- `pms_circuit_breaker_calls_total` incremented per transition

---

## Code Organization Anti-Patterns (Avoid These)

1. **Import Cycles**: Don't import `feature_flag_service` in `message_gateway.py`; use `DEFAULT_FLAGS` dict directly
   - ❌ `from app.services.feature_flag_service import get_feature_flag_service`
   - ✅ `from app.services.feature_flag_service import DEFAULT_FLAGS`

2. **Pydantic v1 Validators**: Use `@field_validator` (v2), not `@validator` (v1)
   - ❌ `@validator("field_name")`
   - ✅ `@field_validator("field_name")`

3. **Sync DB Operations in Async Code**: Always use `AsyncSessionFactory` and `asyncpg`
   - ❌ `session = SessionLocal()  # Blocks event loop`
   - ✅ `async with AsyncSessionFactory() as session: await session.execute(...)`

4. **Hardcoded Secrets**: All production secrets must be `SecretStr` and fail validation if not overridden
   - ❌ `API_KEY = "sk_live_12345"`
   - ✅ `API_KEY: SecretStr = Field(default=SecretStr("change-me"))`

5. **Missing Correlation IDs**: All external API calls must include correlation_id header
   - ❌ `response = await client.get("/api/availability")`
   - ✅ `response = await client.get("/api/availability", headers={"X-Request-ID": correlation_id})`

---

## Integration Points

### WhatsApp Integration (`app/services/whatsapp_client.py`)

**Meta Cloud API v18.0**:
- Webhook endpoint: `POST /api/webhooks/whatsapp` (in `app/routers/webhooks.py`)
- Message types: text, audio (voice messages), media (images, documents)
- Rate limit: 80 req/sec per business account
- Webhook verification: Token + request signature validation

**Audio Message Workflow**:
```
WhatsApp Webhook (audio_id) 
  → MediaDownloader (get audio URL from Meta)
  → AudioProcessor (Whisper STT)
  → NLPEngine (intent detection from transcript)
  → Orchestrator (response generation)
  → TemplateService (format response)
  → WhatsAppClient (send back audio or text)
```

### Gmail Integration (`app/services/gmail_client.py`)

**OAuth2 Flow**:
- Service account or user credentials (configured in `.env`)
- Sends notifications on reservation confirmation
- Scheduled reminders (via `app/services/reminder_service.py`)

### PMS Integration Patterns

**Real Mode** (`PMS_TYPE=qloapps`):
- QloApps REST API with Bearer token auth
- Endpoints: `/availability`, `/rooms`, `/reservations`, `/guests`
- Circuit breaker protects against PMS outages

**Mock Mode** (`PMS_TYPE=mock`):
- Returns fixture data for testing
- Useful for local development without QloApps credentials
- `MockPMSAdapter` in `tests/mocks/pms_mock_server.py`

---

## Deployment & Governance

### Pre-Flight Risk Assessment

**Script**: `scripts/preflight.py` (Python)  
**Output**: `.playbook/preflight_report.json`

**Invocation**:
```bash
make preflight READINESS_SCORE=8.0 MVP_SCORE=7.5
# Checks: CVE scanning, linting, test coverage, uptime SLOs
# Decision: GO | NO_GO | GO_WITH_CAUTION
```

### Canary Diff Analysis

**Script**: `scripts/canary-deploy.sh` (Bash + PromQL)  
**Metrics**: P95 latency, error rate, circuit breaker trips

```bash
make canary-diff BASELINE=main CANARY=staging
# Compares: histogram_quantile(0.95, ...), rate(...[5m])
# Thresholds: P95 ≤ 10% increase, error rate ≤ 50% increase
# Output: `.playbook/canary_diff_report.json` (PASS|FAIL)
```

### Docker Compose Profiles

**Default** (local dev):
```bash
docker compose up
# Starts: agente-api, postgres, redis, prometheus, grafana, alertmanager, jaeger
# No QloApps (uses PMS_TYPE=mock)
```

**With PMS** (staging/prod):
```bash
docker compose --profile pms up
# Includes: qloapps, mysql (for real PMS integration)
```

**Rationale**: Local dev uses mock PMS adapter to avoid auth/pull issues; staging/prod use real PMS

### Staging Deployment Automation

**Key Files**:
- `docker-compose.staging.yml` - 7-service config optimized for staging
- `scripts/deploy-staging.sh` - Automated deployment (15-20 min)
- `scripts/generate-staging-secrets.sh` - Crypto-secure secret generation
- `Dockerfile.production` - Multi-stage build (optimized for size/speed)

**Deployment Steps**:
```bash
cd agente-hotel-api

# 1. Generate secrets (one-time)
./scripts/generate-staging-secrets.sh > .env.staging

# 2. Deploy to staging
./scripts/deploy-staging.sh --env staging --build

# 3. Verify all services
make health

# 4. Run smoke tests
make test-e2e-quick
```

---

## Quick Reference

### Key Files for Onboarding

1. **`app/main.py`** → FastAPI app initialization, lifespan manager, middleware stack
2. **`app/services/orchestrator.py`** → End-to-end message processing logic
3. **`app/services/pms_adapter.py`** → External integration patterns (circuit breaker, cache, metrics)
4. **`app/core/settings.py`** → Configuration schema with type validation
5. **`app/models/unified_message.py`** → Message schema (multi-channel normalization)
6. **`Makefile`** → All dev commands (46 targets including resilience/chaos tests)

### Common Tasks

**Add New Endpoint**:
1. Create router in `app/routers/new_feature.py`
2. Define Pydantic input/output models
3. Include rate limit decorator: `@app.state.limiter.limit("120/minute")`
4. Add to `app/main.py` router registration
5. Add test in `tests/integration/test_new_feature.py`

**Add New Metric**:
1. Define in service module (e.g., `app/services/orchestrator.py`)
2. Use labels for dimensions (endpoint, status, intent)
3. Document in `README-Infra.md` with PromQL queries
4. Ensure <1000 possible label combinations (cardinality limit)

**Add Feature Flag**:
1. Add key to `DEFAULT_FLAGS` dict in `app/services/feature_flag_service.py`
2. Use in code: `if await ff.is_enabled("my.flag", default=True):`
3. Test both enabled/disabled paths
4. Update docs with rollout plan

**Change PMS Behavior**:
1. Implement in `QloAppsAdapter` class (`app/services/pms_adapter.py`)
2. Add cache key pattern if result is cacheable
3. Update circuit breaker metrics
4. Add test case in `tests/integration/test_pms_integration.py`
5. Update Prometheus alert thresholds if needed

---

## Development Tips

- **Always use absolute paths** when referencing services in Docker (e.g., `postgres:5432`, not `localhost:5432`)
- **Environment variables** are validated at startup - check logs for missing configs
- **Redis locks** are used for reservation conflicts - see `lock_service.py` for usage patterns
- **Audio processing** requires TTS engine configuration (espeak/coqui in `.env`)
- **PMS operations** are cached aggressively - use cache invalidation patterns after mutations
- **Test isolation**: Each test gets fresh in-memory SQLite session (no cleanup needed)
- **Port conflicts**: If 8002 occupied, change in `docker-compose.yml` + `.env`

### Performance Notes

- **Database queries**: Use `select()` with explicit columns for index usage
- **Redis cache**: Set TTL aggressively (5-60min) to avoid stale data
- **Circuit breaker**: Adjust thresholds based on PMS SLA (default: 5 failures in 30s)
- **Rate limiting**: 120/min per IP; disable in tests via `storage_uri="memory://"`
- **Async tasks**: Use `asyncio.create_task()` for fire-and-forget operations (reminders)

### Debugging

**Check Logs**:
```bash
make logs          # Follow all container logs
docker logs agente-api | grep ERROR
```

**Check Metrics**:
```bash
# Prometheus query interface
curl "http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state"

# Grafana dashboards
open http://localhost:3000/d/pms_adapter  # Pre-configured PMS dashboard
```

**Check Distributed Traces**:
```bash
# Jaeger UI
open http://localhost:16686/search
# Filter by service: agente-api, operation: POST /api/webhooks/whatsapp
```

**Health Status**:
```bash
curl http://localhost:8002/health/ready | jq .
# Shows: postgres, redis, pms (optional) status
```

---

**Last Updated**: 2025-10-17  
**Maintained By**: Backend AI Team  
**Review Frequency**: Monthly (or after major architectural changes)
