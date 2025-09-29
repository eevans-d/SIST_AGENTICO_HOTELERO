# AI Agent Instructions for Agente Hotelero IA System

## System Overview
This is a multi-service hotel receptionist AI agent built with FastAPI, designed to handle guest communications via WhatsApp, Gmail, and other channels. The system integrates with QloApps PMS for reservation management and uses Docker Compose for orchestration.

## Tool Calling Guidelines
<tool_calling>
When working with this repository, you have the capability to call multiple tools in a single response. For maximum efficiency, whenever you need to perform multiple independent operations, ALWAYS invoke all relevant tools simultaneously rather than sequentially. This is especially important when exploring the repository, reading files, viewing directories, validating changes, or working on related tasks.
</tool_calling>

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

## Project-Specific Conventions

### Naming Patterns
- **Services**: Descriptive names ending in `_service.py` (e.g., `orchestrator_service.py`)
- **Models**: Pydantic models for API schemas, SQLAlchemy models for database entities
- **Exceptions**: Custom exceptions in `app/exceptions/` following pattern `<Domain>Error`
- **Tests**: Test files prefixed with `test_` and grouped by functionality
- **Environment variables**: UPPERCASE with underscores (e.g., `WHATSAPP_VERIFY_TOKEN`)

### Response Patterns
- All API responses use consistent Pydantic models
- Error responses include correlation IDs for traceability
- Health check responses follow standard format with detailed dependency status
- Webhook responses include proper HTTP status codes and validation

### Async/Await Conventions
- All database operations are async
- External API calls use httpx async client
- Background tasks use FastAPI's BackgroundTasks
- Redis operations are async where possible

### Configuration Management
- Settings centralized in `app/core/settings.py` using Pydantic Settings
- Environment-specific settings with validation
- Secret values use SecretStr to prevent accidental logging
- Default values only for non-production settings

## Development Tips

- **Always use absolute paths** when referencing services in Docker
- **Environment variables** are validated at startup - check logs for missing configs
- **Redis locks** are used for reservation conflicts - see `lock_service.py`
- **Audio processing** requires TTS engine configuration (espeak/coqui)
- **PMS operations** are cached aggressively - use cache invalidation patterns
- **Use the Makefile**: All common operations have make targets - run `make help` for full list
- **Poetry vs pip**: Project uses Poetry for dependency management - prefer `poetry add` over `pip install`
- **Testing isolation**: Each test category can be run independently for faster feedback loops
- **Docker-first development**: All services run in containers - use `make docker-up` for full stack

## Common Patterns to Follow

When adding new services:
1. Add health check endpoint
2. Include Prometheus metrics
3. Use structured logging with correlation IDs
4. Implement circuit breaker for external calls
5. Add comprehensive error handling
6. Write both unit and integration tests

## Development Workflow & CI/CD

### GitHub Actions Workflows
- **CI Pipeline** (`.github/workflows/ci.yml`): Runs on every PR and push to main
  - Poetry dependency installation
  - Ruff linting and formatting
  - Pytest test suite (unit, integration, e2e)
  - Trivy security scanning (fast mode)
  - Docker image build verification
- **Deploy Pipeline** (`.github/workflows/deploy.yml`): Manual dispatch for production deployments
- **Nightly Security** (`.github/workflows/nightly-security.yml`): Deep security scans
- **SLO Compliance** (`.github/workflows/slo-compliance.yml`): Service level objective monitoring

### Pre-commit Hooks
The project uses pre-commit hooks (`.pre-commit-config.yaml`) for:
- Ruff linting and formatting
- Git security scanning
- Ensure consistent code quality before commits

### Testing Philosophy
- **Unit tests** (`tests/unit/`): Fast, isolated component testing
- **Integration tests** (`tests/integration/`): Service interaction testing
- **E2E tests** (`tests/e2e/`): Full workflow validation
- **Performance tests** (`tests/performance/`): Load and stress testing with k6
- **Mock services** (`tests/mocks/`): PMS and external API mocking

### Code Quality Standards
- **Line length**: 120 characters (configured in ruff)
- **Python version**: 3.12+ required
- **Import sorting**: Handled by ruff
- **Type hints**: Required for all public APIs
- **Docstrings**: Required for all public functions/classes

## Deployment & Operations

### Container Strategy
- **Development**: `Dockerfile` with hot reload and debug capabilities
- **Production**: `Dockerfile.production` with multi-stage build and security hardening
- **Orchestration**: Docker Compose with separate development and production configurations

### Environment Configuration
- **Development**: `.env` file (copy from `.env.example`)
- **Production**: Environment variables injected by deployment platform
- **Settings validation**: Strict validation in `app/core/settings.py` prevents deployment with missing secrets

### Monitoring & Observability
- **Metrics**: Prometheus metrics exported at `/metrics`
- **Health checks**: `/health/live` (basic) and `/health/ready` (dependencies)
- **Logging**: Structured JSON logs with correlation IDs
- **Alerting**: Grafana dashboards with AlertManager integration
- **Performance**: SLO compliance monitoring and error budget tracking

## Security Practices

### Input Validation & Sanitization
- All user inputs validated with Pydantic models
- XSS prevention with bleach sanitization
- Rate limiting implemented with slowapi + Redis
- Security headers middleware for all responses

### Secrets Management
- No hardcoded secrets in code (validated in CI)
- SecretStr type for all sensitive configuration
- Production deployment validation prevents dummy values

### Authentication & Authorization
- JWT tokens with configurable expiration
- Password hashing with bcrypt via passlib
- Role-based access control for admin endpoints

## Troubleshooting Quick Reference

### Common Commands
```bash
# Quick health check
make health

# View all service logs
make logs

# Run specific test categories
make test  # All tests
pytest tests/unit/  # Unit tests only
pytest tests/integration/  # Integration tests only

# Performance testing
make performance-test  # Load testing with k6
make stress-test       # Stress testing to find limits

# Security validation
make security-fast     # Quick security scan
make security-scan     # Comprehensive security analysis

# Database operations
make backup    # Backup all databases
make restore   # Restore from backup
```

### Service Dependencies
- **PostgreSQL**: Main application database
- **Redis**: Caching, rate limiting, distributed locks
- **QloApps PMS**: External hotel management system (with circuit breaker)
- **WhatsApp Business API**: Guest communication channel
- **Gmail API**: Email communication channel

### Performance Baselines
- **Response time**: P95 < 500ms for API endpoints
- **Throughput**: 100+ RPS sustained load
- **Error rate**: < 0.1% under normal conditions
- **Circuit breaker**: Trips at 50% error rate over 30s window