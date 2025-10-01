# AI Agent Instructions for Agente Hotelero IA System# AI Agent Instructions for Agente Hotelero IA System



## System Overview## System Overview

Multi-service hotel receptionist AI agent (FastAPI) handling WhatsApp/Gmail communications with QloApps PMS integration. Uses Docker Compose orchestration with comprehensive observability stack (Prometheus/Grafana/AlertManager).This is a multi-service hotel receptionist AI agent built with FastAPI, designed to handle guest communications via WhatsApp, Gmail, and other channels. The system integrates with QloApps PMS for reservation management and uses Docker Compose for orchestration.



## Architecture Fundamentals## Architecture & Core Components



### Service Boundaries### Service Architecture

- **agente-api**: FastAPI async app with lifespan-managed services (`app/main.py`)- **agente-api**: Main FastAPI application handling AI orchestration and guest communications

- **qloapps + mysql**: PMS backend (profiles-gated; use `PMS_TYPE=mock` for local dev)- **qloapps**: QloApps PMS for hotel management (MySQL-backed)

- **postgres**: Agent DB (sessions, locks, tenant mapping) via SQLAlchemy async- **postgres**: Agent database for sessions, locks, and metadata 

- **redis**: Cache, rate limiting (slowapi), distributed locks, feature flags- **redis**: Caching, rate limiting, and distributed locks

- **Monitoring**: Prometheus scrapes `/metrics`; Grafana dashboards; AlertManager- **Monitoring stack**: Prometheus, Grafana, AlertManager



### Core Patterns (Read These Files First)### Key Service Patterns

- **Orchestrator**: `orchestrator.py` coordinates message→NLP→PMS→response flow; includes retry logic and feature flag checks- **Orchestrator Pattern**: `app/services/orchestrator.py` coordinates all AI workflows

- **PMS Adapter**: `pms_adapter.py` wraps external PMS calls with circuit breaker (`CircuitBreaker` class), Redis caching, and Prometheus metrics (`pms_api_latency_seconds`, `pms_circuit_breaker_state`)- **Adapter Pattern**: `app/services/pms_adapter.py` abstracts PMS interactions with circuit breaker

- **Message Gateway**: `message_gateway.py` normalizes inbound payloads to `UnifiedMessage`; resolves tenant via dynamic or static service- **Unified Messaging**: `app/models/unified_message.py` normalizes multi-channel communications

- **Dynamic Tenancy**: `dynamic_tenant_service.py` with in-memory cache + background refresh; activated via feature flag `tenancy.dynamic.enabled`- **Session Management**: Persistent guest conversation state in `session_manager.py`

- **Feature Flags**: `feature_flag_service.py` with Redis-backed cache; use `DEFAULT_FLAGS` dict for fallback

## Essential Development Workflows

## Critical Development Workflows

### Docker Commands (via Makefile)

### Dependency Management (Auto-Detection)```bash

```bashmake docker-up      # Start full stack with --build

make install  # Detects uv → poetry → npm; uses Poetry in this projectmake docker-down    # Stop and remove containers

poetry install --all-extras  # Manual alternativemake health         # Run health checks across services

```make backup         # Backup databases

make logs           # Follow all service logs

### Docker Stack (Local Dev with PMS Mock)```

```bash

make dev-setup     # Creates .env from .env.example### Environment Setup

make docker-up     # Builds and starts stack (uses PMS_TYPE=mock by default)```bash

make health        # Validates /health/ready across servicesmake dev-setup      # Copies .env.example to .env (edit with secrets)

make logs          # Tail all container logsmake install        # Auto-detects uv/poetry/npm for deps

make docker-down   # Teardown```

```

### Code Quality

**Profile-Gated QloApps**: Real PMS requires `--profile pms` flag; default config uses mock adapter to avoid pull/auth issues.```bash

make fmt            # Ruff format + Prettier

### Code Quality & Securitymake lint           # Ruff check --fix + gitleaks security scan

```bash```

make fmt                # Ruff format (line-length 120) + prettier

make lint               # Ruff check --fix + gitleaks secret scan## Configuration Patterns

make security-fast      # Trivy HIGH/CRITICAL scan (vuln+secrets)

make test               # pytest via Poetry (uses aiosqlite for in-memory DB tests)### Settings Architecture

```- `app/core/settings.py` uses Pydantic with validation

- Enum-based configuration (Environment, LogLevel, TTSEngine)

### Governance & Pre-Deploy Checks- Production secret validation prevents deploy with dummy values

```bash- All secrets use `SecretStr` type

make preflight          # Runs scripts/preflight.py → .playbook/preflight_report.json

make canary-diff        # Baseline vs canary P95/error rate diff (PromQL-based)### Network Architecture

make pre-deploy-check   # Combined security-fast + SLO validation + resilience tests- **frontend_network**: NGINX public exposure

```- **backend_network**: Internal service communication

- Services communicate via container names (e.g., `postgres:5432`)

## Configuration & Environment

## Critical Integration Points

### Settings Architecture (`app/core/settings.py`)

- **Pydantic v2** with `SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`### PMS Integration (`pms_adapter.py`)

- **Enums for type safety**: `Environment`, `LogLevel`, `TTSEngine`, `PMSType`- Circuit breaker pattern for resilience

- **SecretStr for sensitive data**: `pms_api_key`, `whatsapp_access_token`, etc.- Redis caching with cache hit/miss metrics

- **Dynamic postgres_url construction**: Fallback to individual `postgres_host`/`postgres_port` if `postgres_url` not set- Comprehensive error handling: `PMSError`, `PMSAuthError`, `PMSRateLimitError`

- **Toggles**: `check_pms_in_readiness` (controls PMS check in `/health/ready`), `debug` (disables rate limiting)- Prometheus metrics: latency, operations, circuit breaker state



### Feature Flag Patterns### WhatsApp Integration (`whatsapp_client.py`)

```python- Meta Cloud API v18.0

# In services: always await async getter- Audio message transcription workflow

ff = await get_feature_flag_service()- Media download capabilities

if await ff.is_enabled("nlp.fallback.enhanced", default=True):

    # Enhanced fallback logic### Message Processing Flow

1. Webhook receives message → `UnifiedMessage` model

# In message gateway: use DEFAULT_FLAGS to avoid import cycles2. Audio messages → `AudioProcessor` for STT

use_dynamic = DEFAULT_FLAGS.get("tenancy.dynamic.enabled", True)3. Text → `NLPEngine` for intent recognition

```4. `Orchestrator` coordinates PMS calls and response generation

5. `TemplateService` for consistent responses

## Integration Patterns

## Logging & Monitoring

### PMS Adapter Circuit Breaker

- **State machine**: `CircuitState.CLOSED` → `OPEN` (after 5 failures) → `HALF_OPEN` (after 30s recovery)### Structured Logging

- **Metrics**: `pms_circuit_breaker_state` (0=closed, 1=open, 2=half-open), `pms_circuit_breaker_calls_total{state,result}`- Uses `structlog` with JSON output

- **Cache invalidation**: `_invalidate_cache_pattern("availability:*")` after mutations- Correlation IDs via middleware (`correlation_id_middleware`)

- **Retry decorator**: `@retry_with_backoff` in `app/core/retry.py` with exponential backoff- All external API calls logged with timing



### Rate Limiting (SlowAPI + Redis)### Health Checks

- **Applied per-endpoint**: `@app.state.limiter.limit("120/minute")` on webhook routes- `/health/live`: Basic liveness

- **Debug bypass**: Rate limits ignored when `settings.debug=True` (no Redis required for tests)- `/health/ready`: Dependency readiness (DB, Redis, PMS)

- **Test isolation**: `conftest.py` sets `storage_uri="memory://"` for in-memory rate limiting- Container health checks in docker-compose.yml



### Multi-Tenant Resolution## Testing Structure

1. **Dynamic service** (`dynamic_tenant_service.py`): Queries `Tenant` + `TenantUserIdentifier` from Postgres; caches in-memory with auto-refresh (300s default)

2. **Metrics**: `tenant_resolution_total{result=hit|default|miss_strict}`, `tenants_active_total`, `tenant_refresh_latency_seconds`### Test Organization

3. **Admin endpoints**: `/admin/tenants` (CRUD), `/admin/tenants/refresh` (force cache refresh)- `tests/unit/`: Service-level unit tests

4. **Fallback chain**: Dynamic → Static → "default" tenant- `tests/integration/`: Cross-service integration tests  

- `tests/e2e/`: End-to-end reservation flows

## Observability- `tests/mocks/`: PMS mock server for testing



### Prometheus Metrics (Key Patterns)### Key Testing Patterns

```python- `conftest.py` provides test app fixture

# Histogram for latency tracking- Async test patterns with `pytest-asyncio`

pms_latency = Histogram("pms_api_latency_seconds", "PMS API latency", ["endpoint", "method"])

with pms_latency.labels(endpoint="/api/availability", method="GET").time():## Code Conventions

    result = await self.client.get("/api/availability")

### File Organization

# Counter for operations- Services in `app/services/` (business logic)

pms_operations.labels(operation="check_availability", status="success").inc()- Models in `app/models/` (Pydantic schemas, SQLAlchemy)

- Core utilities in `app/core/` (settings, logging, middleware)

# Gauge for stateful metrics- Routers in `app/routers/` (FastAPI endpoints)

circuit_breaker_state.set(0)  # 0=closed, 1=open, 2=half-open

```### Error Handling

- Custom exceptions in `app/exceptions/`

### Structured Logging (`structlog` + JSON)- Global exception handler in middleware

- **Correlation IDs**: `correlation_id_middleware` injects `X-Request-ID` into context- Circuit breaker for external service calls

- **Logged automatically**: All HTTP requests, external API calls, circuit breaker state changes

- **Pattern**: `logger.info("message", key=value)` → JSON output with correlation_id### Security

- Rate limiting via slowapi with Redis backend

### Health Checks- Security headers middleware

- **/health/live**: Always returns 200 (k8s liveness)- Input validation and sanitization

- **/health/ready**: Checks Postgres, Redis, optionally PMS (via `check_pms_in_readiness`)

- **Container healthchecks**: All Docker services have `healthcheck` stanzas## Development Tips



## Testing Conventions- **Always use absolute paths** when referencing services in Docker

- **Environment variables** are validated at startup - check logs for missing configs

### Async Test Setup (`pytest-asyncio`)- **Redis locks** are used for reservation conflicts - see `lock_service.py`

```python- **Audio processing** requires TTS engine configuration (espeak/coqui)

@pytest_asyncio.fixture- **PMS operations** are cached aggressively - use cache invalidation patterns

async def test_client():

    from app.main import app## Common Patterns to Follow

    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

    async with AsyncClient(app=app, base_url="http://test") as client:When adding new services:

        yield client1. Add health check endpoint

```2. Include Prometheus metrics

3. Use structured logging with correlation IDs

### Database Testing4. Implement circuit breaker for external calls

- **SQLite fallback**: `aiosqlite` for in-memory tests (see `tests/unit/test_dynamic_tenant_service.py`)5. Add comprehensive error handling

- **Schema creation**: Services call `Base.metadata.create_all()` in `start()` method (migration-free bootstrap for dev/test)6. Write both unit and integration tests

### Mock PMS Server
- **Location**: `tests/mocks/pms_mock_server.py`
- **Usage**: Pytest fixture or standalone process; mimics QloApps API responses

## Code Organization Anti-Patterns (Avoid These)

1. **Import cycles**: Don't import `feature_flag_service` in `message_gateway.py`; use `DEFAULT_FLAGS` dict directly
2. **Pydantic v1 validators**: Use `@field_validator` (v2), not `@validator` (v1)
3. **Sync DB operations in async code**: Always use `AsyncSessionFactory` and `asyncpg`
4. **Hardcoded secrets**: All production secrets must be `SecretStr` and fail validation if not overridden

## Deployment & Governance

### Pre-Flight Risk Assessment
**Script**: `scripts/preflight.py` (Python)
**Invocation**: `make preflight READINESS_SCORE=7.5 MVP_SCORE=7.0`
**Output**: `.playbook/preflight_report.json` with `decision: GO|NO_GO|GO_WITH_CAUTION`
**CI Integration**: `.github/workflows/preflight.yml` runs on PR, blocks merge if NO_GO

### Canary Diff Analysis
**Script**: `scripts/canary-deploy.sh` (Bash + PromQL)
**Metrics Compared**: P95 latency (`histogram_quantile(0.95, rate(...))`), error rate
**Thresholds**: P95 ≤ 10% increase, error rate ≤ 50% increase (configurable via env)
**Output**: `.playbook/canary_diff_report.json` with `status: PASS|FAIL`

### Docker Compose Profiles
- **Default**: Starts agente-api, postgres, redis, monitoring (no QloApps)
- **PMS profile**: `docker compose --profile pms up` includes qloapps + mysql
- **Rationale**: Local dev uses mock PMS adapter; staging/prod use real PMS

## Quick Reference

### Key Files for Onboarding
1. `app/main.py` → FastAPI app initialization, lifespan manager, middleware stack
2. `app/services/orchestrator.py` → End-to-end message processing logic
3. `app/services/pms_adapter.py` → External integration patterns (circuit breaker, cache, metrics)
4. `app/core/settings.py` → Configuration schema with type validation
5. `Makefile` → All dev commands (46 targets including resilience/chaos tests)

### Common Tasks
- **Add new endpoint**: Create router in `app/routers/`, include in `main.py`, add rate limit decorator if public
- **Add new metric**: Define in service module, use labels for dimensions, document in `README-Infra.md`
- **Add new feature flag**: Update `DEFAULT_FLAGS` dict in `feature_flag_service.py`, use `is_enabled()` async method
- **Change PMS behavior**: Implement in `QloAppsAdapter` class, add cache key pattern, update circuit breaker metrics
