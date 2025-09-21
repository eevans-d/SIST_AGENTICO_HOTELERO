# AI Agent Instructions for Agente Hotelero IA System

## System Overview
This is a multi-service hotel receptionist AI agent built with FastAPI, designed to handle guest communications via WhatsApp, Gmail, and other channels. The system integrates with QloApps PMS for reservation management and uses Docker Compose for orchestration.

## Architecture & Core Components

### Service Architecture
- **agente-api**: Main FastAPI application handling AI orchestration and guest communications
- **qloapps**: QloApps PMS for hotel management (MySQL-backed)
- **postgres**: Agent database for sessions, locks, and metadata 
- **redis**: Caching, rate limiting, and distributed locks
- **Monitoring stack**: Prometheus, Grafana, AlertManager

### Key Service Patterns
- **Orchestrator Pattern**: `app/services/orchestrator.py` coordinates all AI workflows
- **Adapter Pattern**: `app/services/pms_adapter.py` abstracts PMS interactions with circuit breaker
- **Unified Messaging**: `app/models/unified_message.py` normalizes multi-channel communications
- **Session Management**: Persistent guest conversation state in `session_manager.py`

## Essential Development Workflows

### Docker Commands (via Makefile)
```bash
make docker-up      # Start full stack with --build
make docker-down    # Stop and remove containers
make health         # Run health checks across services
make backup         # Backup databases
make logs           # Follow all service logs
```

### Environment Setup
```bash
make dev-setup      # Copies .env.example to .env (edit with secrets)
make install        # Auto-detects uv/poetry/npm for deps
```

### Code Quality
```bash
make fmt            # Ruff format + Prettier
make lint           # Ruff check --fix + gitleaks security scan
```

## Configuration Patterns

### Settings Architecture
- `app/core/settings.py` uses Pydantic with validation
- Enum-based configuration (Environment, LogLevel, TTSEngine)
- Production secret validation prevents deploy with dummy values
- All secrets use `SecretStr` type

### Network Architecture
- **frontend_network**: NGINX public exposure
- **backend_network**: Internal service communication
- Services communicate via container names (e.g., `postgres:5432`)

## Critical Integration Points

### PMS Integration (`pms_adapter.py`)
- Circuit breaker pattern for resilience
- Redis caching with cache hit/miss metrics
- Comprehensive error handling: `PMSError`, `PMSAuthError`, `PMSRateLimitError`
- Prometheus metrics: latency, operations, circuit breaker state

### WhatsApp Integration (`whatsapp_client.py`)
- Meta Cloud API v18.0
- Audio message transcription workflow
- Media download capabilities

### Message Processing Flow
1. Webhook receives message → `UnifiedMessage` model
2. Audio messages → `AudioProcessor` for STT
3. Text → `NLPEngine` for intent recognition
4. `Orchestrator` coordinates PMS calls and response generation
5. `TemplateService` for consistent responses

## Logging & Monitoring

### Structured Logging
- Uses `structlog` with JSON output
- Correlation IDs via middleware (`correlation_id_middleware`)
- All external API calls logged with timing

### Health Checks
- `/health/live`: Basic liveness
- `/health/ready`: Dependency readiness (DB, Redis, PMS)
- Container health checks in docker-compose.yml

## Testing Structure

### Test Organization
- `tests/unit/`: Service-level unit tests
- `tests/integration/`: Cross-service integration tests  
- `tests/e2e/`: End-to-end reservation flows
- `tests/mocks/`: PMS mock server for testing

### Key Testing Patterns
- `conftest.py` provides test app fixture
- Async test patterns with `pytest-asyncio`

## Code Conventions

### File Organization
- Services in `app/services/` (business logic)
- Models in `app/models/` (Pydantic schemas, SQLAlchemy)
- Core utilities in `app/core/` (settings, logging, middleware)
- Routers in `app/routers/` (FastAPI endpoints)

### Error Handling
- Custom exceptions in `app/exceptions/`
- Global exception handler in middleware
- Circuit breaker for external service calls

### Security
- Rate limiting via slowapi with Redis backend
- Security headers middleware
- Input validation and sanitization

## Development Tips

- **Always use absolute paths** when referencing services in Docker
- **Environment variables** are validated at startup - check logs for missing configs
- **Redis locks** are used for reservation conflicts - see `lock_service.py`
- **Audio processing** requires TTS engine configuration (espeak/coqui)
- **PMS operations** are cached aggressively - use cache invalidation patterns

## Common Patterns to Follow

When adding new services:
1. Add health check endpoint
2. Include Prometheus metrics
3. Use structured logging with correlation IDs
4. Implement circuit breaker for external calls
5. Add comprehensive error handling
6. Write both unit and integration tests