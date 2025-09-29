# AI Agent Instructions for Agente Hotelero IA System

## System Overview
This is a multi-service hotel receptionist AI agent built with FastAPI, designed to handle guest communications via WhatsApp, Gmail, and other channels. The system integrates with QloApps PMS for reservation management and uses Docker Compose for orchestration.

**Key Technologies**: FastAPI, SQLAlchemy, Redis, PostgreSQL, Docker, Prometheus, Grafana
**Language**: Python 3.12+
**Package Manager**: Poetry
**Code Quality**: Ruff (linting & formatting), pytest (testing), pre-commit hooks

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

### Quick Start (First Time Setup)
```bash
# 1. Clone and navigate to API directory
cd agente-hotel-api/

# 2. Install dependencies (requires Python 3.12+)
pip install poetry
poetry install --all-extras --no-root

# 3. Setup environment
make dev-setup      # Copies .env.example to .env (edit with secrets)

# 4. Start development stack
make docker-up      # Start full stack with --build

# 5. Verify everything works
make health         # Run health checks across services
```

### Daily Development Commands
```bash
# Code quality (run before committing)
make fmt            # Ruff format + Prettier
make lint           # Ruff check --fix + gitleaks security scan

# Testing
make test           # Run full test suite (unit + integration + e2e)
poetry run pytest tests/unit/          # Unit tests only
poetry run pytest tests/integration/   # Integration tests only
poetry run pytest tests/e2e/          # E2E tests only

# Development server
make docker-up      # Start full stack with --build
make docker-down    # Stop and remove containers
make logs           # Follow all service logs

# Database operations
make backup         # Backup databases
make restore        # Restore from backup
```

### Docker Services & Ports
- **agente-api**: 8000 (FastAPI application)
- **postgres**: 5432 (Agent database)
- **redis**: 6379 (Cache & sessions)
- **qloapps**: 3306/80 (PMS system)
- **prometheus**: 9090 (Metrics)
- **grafana**: 3000 (Dashboards)
- **nginx**: 80/443 (Reverse proxy)

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

## Testing Strategy & Patterns

### Test Structure & Organization
```
tests/
├── conftest.py              # Shared fixtures & test app setup
├── unit/                    # Service-level unit tests (fast, isolated)
│   ├── test_orchestrator.py
│   ├── test_pms_adapter.py
│   └── test_session_manager.py
├── integration/             # Cross-service integration tests
│   ├── test_pms_integration.py
│   └── test_orchestrator.py
├── e2e/                     # End-to-end reservation flows
│   └── test_reservation_flow.py
├── mocks/                   # PMS mock server for testing
└── performance/             # Load testing scripts
    └── load-test.js
```

### Testing Best Practices
- **Unit Tests**: Mock external dependencies, test business logic in isolation
- **Integration Tests**: Test service interactions with real dependencies
- **E2E Tests**: Full workflow testing from webhook to response
- **Use async test patterns**: `pytest-asyncio` for async functions
- **Mock PMS calls**: Use `tests/mocks/` for consistent PMS responses
- **Test fixtures**: Leverage `conftest.py` for reusable test setup

### Writing Tests
```python
# Unit test example
@pytest.mark.asyncio
async def test_orchestrator_handles_reservation_request(mock_pms):
    # Arrange
    orchestrator = OrchestrationService()
    message = UnifiedMessage(text="I need a room for tonight")
    
    # Act
    response = await orchestrator.process_message(message)
    
    # Assert
    assert response.intent == "reservation_request"
    mock_pms.search_rooms.assert_called_once()

# Integration test with real dependencies
@pytest.mark.integration
async def test_full_reservation_flow(test_app):
    # Test actual webhook -> PMS -> response flow
    response = await test_app.post("/webhooks/whatsapp", json=webhook_data)
    assert response.status_code == 200
```

### Running Tests Efficiently
```bash
# Fast feedback loop (unit tests only)
poetry run pytest tests/unit/ -v

# Integration tests (requires services running)
make docker-up && poetry run pytest tests/integration/ -v

# Full test suite with coverage
poetry run pytest --cov=app --cov-report=html

# Watch mode for TDD
poetry run pytest-watch tests/unit/
```

## Code Conventions & Style Guide

### File Organization
```
app/
├── main.py                  # FastAPI app entry point
├── core/                    # Core utilities & configuration
│   ├── settings.py          # Pydantic settings with validation
│   ├── logging.py           # Structured logging setup
│   └── middleware.py        # CORS, correlation IDs, etc.
├── models/                  # Data models
│   ├── unified_message.py   # Multi-channel message normalization
│   ├── database.py          # SQLAlchemy models 
│   └── schemas.py           # Pydantic response schemas
├── services/                # Business logic (main implementation)
│   ├── orchestrator.py      # AI workflow coordination
│   ├── pms_adapter.py       # PMS integration with circuit breaker
│   ├── session_manager.py   # Guest conversation state
│   ├── whatsapp_client.py   # WhatsApp API integration
│   └── nlp_engine.py        # Intent recognition & NLP
├── routers/                 # FastAPI endpoints
│   ├── webhooks.py          # WhatsApp/Gmail webhooks
│   ├── health.py            # Health checks
│   └── admin.py             # Admin dashboard
├── exceptions/              # Custom exception classes
└── utils/                   # Helper functions
```

### Python Code Style
- **Line length**: 120 characters (configured in pyproject.toml)
- **Type hints**: Always use type hints for function parameters and returns
- **Async/await**: Use async patterns consistently for I/O operations
- **Error handling**: Use custom exceptions in `app/exceptions/`
- **Logging**: Structured logging with correlation IDs for traceability

### Naming Conventions
- **Classes**: PascalCase (`OrchestrationService`, `UnifiedMessage`)
- **Functions/variables**: snake_case (`process_message`, `user_session`)
- **Constants**: SCREAMING_SNAKE_CASE (`MAX_RETRY_ATTEMPTS`)
- **Files**: snake_case (`pms_adapter.py`, `session_manager.py`)
- **Environment variables**: SCREAMING_SNAKE_CASE (`REDIS_URL`, `PMS_API_KEY`)

### Function/Method Patterns
```python
# Good: Clear, typed, documented
async def process_reservation_request(
    self, 
    message: UnifiedMessage, 
    user_session: UserSession
) -> OrchestrationResponse:
    """Process a guest reservation request through the PMS.
    
    Args:
        message: Normalized message from any channel
        user_session: Current guest conversation state
        
    Returns:
        Response with reservation status and next actions
        
    Raises:
        PMSError: When PMS integration fails
        ValidationError: When message format is invalid
    """
    logger.info("Processing reservation request", 
                user_id=user_session.user_id,
                correlation_id=message.correlation_id)
    
    try:
        # Implementation...
        return response
    except PMSError as e:
        logger.error("PMS integration failed", error=str(e))
        raise
```

### Import Organization
```python
# 1. Standard library
import asyncio
from datetime import datetime
from typing import Optional, List

# 2. Third party
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local imports
from app.core.settings import settings
from app.models.unified_message import UnifiedMessage
from app.services.pms_adapter import PMSAdapter
from app.exceptions import PMSError
```

## Environment Setup & Configuration

### Required Environment Variables (.env)
```bash
# Core Application
APP_NAME=agente-hotel-api
ENV=development  # development, staging, production
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database & Cache
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/agente_db
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# WhatsApp Integration
WHATSAPP_VERIFY_TOKEN=your-verify-token
WHATSAPP_APP_SECRET=your-app-secret
WHATSAPP_ACCESS_TOKEN=your-access-token

# PMS Integration
PMS_BASE_URL=http://qloapps:80/api
PMS_API_KEY=your-pms-api-key
CHECK_PMS_IN_READINESS=true

# Monitoring & Performance
PROMETHEUS_ENABLED=true
RATE_LIMIT_ENABLED=true

# Audio Processing (Optional)
TTS_ENGINE=espeak  # espeak, coqui
```

### Environment-Specific Settings
- **Development**: Use `.env` file, DEBUG=true, detailed logging
- **Production**: Use environment variables, DEBUG=false, structured JSON logs
- **Testing**: Use in-memory databases, mock external services

### Troubleshooting Environment Issues
```bash
# Check environment variables are loaded
poetry run python -c "from app.core.settings import settings; print(settings.model_dump())"

# Verify database connection
poetry run python -c "from app.models.database import engine; print('DB OK' if engine else 'DB FAIL')"

# Test Redis connection
poetry run python -c "import redis; r=redis.from_url('redis://localhost:6379'); print(r.ping())"

# Check PMS connectivity
curl -H "Authorization: Bearer $PMS_API_KEY" $PMS_BASE_URL/health
```

## Security & Error Handling

### Security Patterns
- **Rate limiting**: Via slowapi with Redis backend (`app/core/middleware.py`)
- **Input validation**: All inputs validated via Pydantic models
- **Secret management**: Use `SecretStr` type, never log secrets
- **Security headers**: CORS, CSRF protection in middleware
- **API authentication**: JWT tokens for admin endpoints
- **Webhook validation**: HMAC signature verification for WhatsApp

### Error Handling Strategy
```python
# Custom exceptions hierarchy
from app.exceptions import (
    PMSError,           # PMS integration failures
    PMSAuthError,       # PMS authentication issues
    PMSRateLimitError,  # PMS rate limiting
    ValidationError,    # Input validation failures
    SessionError,       # User session issues
)

# Error handling with circuit breaker
try:
    result = await pms_adapter.search_rooms(criteria)
except PMSError as e:
    # Circuit breaker will open after consecutive failures
    logger.error("PMS operation failed", error=str(e), correlation_id=message.correlation_id)
    return fallback_response()
```

### Logging Best Practices
```python
import structlog

logger = structlog.get_logger(__name__)

# Good: Structured logging with context
logger.info(
    "Processing reservation request",
    user_id=session.user_id,
    correlation_id=message.correlation_id,
    room_type=request.room_type,
    duration_ms=processing_time
)

# Bad: Unstructured logging
logger.info(f"User {user_id} requested room type {room_type}")
```

### Common Error Scenarios & Solutions
1. **PMS Connection Failure**: Circuit breaker activates, return cached data or graceful degradation
2. **WhatsApp Webhook Signature Validation**: Check `WHATSAPP_APP_SECRET` configuration
3. **Redis Connection Loss**: Fallback to in-memory session storage
4. **Database Connection Issues**: Health check fails, container restart triggers
5. **Rate Limit Exceeded**: Return 429 with retry-after header

## Debugging & Troubleshooting

### Debugging Development Issues
```bash
# View real-time logs with correlation tracking
make logs | grep "correlation_id=abc123"

# Debug specific service container
docker exec -it agente-api-container bash
poetry run python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn app.main:app

# Database debugging
docker exec -it postgres-container psql -U postgres -d agente_db
SELECT * FROM user_sessions WHERE user_id = 'user123';

# Redis debugging  
docker exec -it redis-container redis-cli
KEYS session:*
GET session:user123
```

### Performance Debugging
```bash
# Monitor metrics in real-time
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana

# Check circuit breaker status
curl http://localhost:8000/metrics | grep circuit_breaker

# Profile API endpoints
poetry run python -m cProfile -o profile.stats app/main.py
```

### Common Issues & Solutions
| Issue | Symptoms | Solution |
|-------|----------|----------|
| PMS Integration Timeout | 504 errors, circuit breaker open | Check `PMS_BASE_URL` and network connectivity |
| WhatsApp Webhook Failures | 401/403 errors | Verify `WHATSAPP_APP_SECRET` and signature validation |
| High Memory Usage | Container OOM kills | Check for memory leaks in async operations |
| Slow Response Times | High latency metrics | Review database queries and PMS caching |
| Redis Connection Issues | Session loss, rate limiting disabled | Check Redis container health and connection string |

## Common Development Patterns

### When Adding New Services
1. **Health check endpoint**: Implement `/health/live` and `/health/ready`
2. **Prometheus metrics**: Add custom metrics for monitoring
3. **Structured logging**: Use correlation IDs and structured logs
4. **Circuit breaker**: Implement for external API calls
5. **Comprehensive error handling**: Custom exceptions with proper error messages
6. **Test coverage**: Write unit, integration, and e2e tests
7. **Documentation**: Update API docs and this instruction file

### Service Implementation Template
```python
from app.core.logging import get_logger
from app.core.metrics import metrics_counter, metrics_histogram
from app.exceptions import ServiceError

logger = get_logger(__name__)

class NewService:
    def __init__(self):
        self.metrics = {
            'operations': metrics_counter('new_service_operations_total'),
            'latency': metrics_histogram('new_service_latency_seconds')
        }
    
    @metrics_histogram('new_service_operation_duration')
    async def perform_operation(self, request: RequestModel) -> ResponseModel:
        """Perform service operation with full observability."""
        correlation_id = request.correlation_id
        
        logger.info("Starting operation", 
                   correlation_id=correlation_id,
                   operation="perform_operation")
        
        try:
            # Business logic here
            result = await self._do_work(request)
            
            self.metrics['operations'].labels(status='success').inc()
            logger.info("Operation completed successfully", 
                       correlation_id=correlation_id,
                       result_count=len(result))
            
            return result
            
        except Exception as e:
            self.metrics['operations'].labels(status='error').inc()
            logger.error("Operation failed", 
                        correlation_id=correlation_id,
                        error=str(e))
            raise ServiceError(f"Operation failed: {e}") from e
```

### Database Patterns
```python
# Use async sessions consistently
async def get_user_session(db: AsyncSession, user_id: str) -> Optional[UserSession]:
    result = await db.execute(
        select(UserSession).where(UserSession.user_id == user_id)
    )
    return result.scalar_one_or_none()

# Transaction patterns with proper error handling
async def update_session_with_transaction(
    db: AsyncSession, 
    session_id: str, 
    data: dict
) -> UserSession:
    async with db.begin():
        session = await get_user_session(db, session_id)
        if not session:
            raise SessionError(f"Session {session_id} not found")
        
        for key, value in data.items():
            setattr(session, key, value)
        
        await db.commit()
        return session
```

### Caching Patterns
```python
# Redis caching with TTL and error handling
async def get_cached_pms_data(key: str) -> Optional[dict]:
    try:
        cached = await redis_client.get(f"pms:{key}")
        return json.loads(cached) if cached else None
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning("Cache read failed", key=key, error=str(e))
        return None

async def set_cached_pms_data(key: str, data: dict, ttl: int = 300):
    try:
        await redis_client.setex(
            f"pms:{key}", 
            ttl, 
            json.dumps(data, default=str)
        )
    except redis.RedisError as e:
        logger.warning("Cache write failed", key=key, error=str(e))
```

## Performance & Scalability

### Performance Best Practices
- **Async everywhere**: Use async/await for all I/O operations
- **Connection pooling**: Configure appropriate pool sizes for DB and Redis
- **Caching strategy**: Cache PMS responses aggressively (5-minute TTL)
- **Circuit breakers**: Prevent cascade failures from external services
- **Rate limiting**: Protect against abuse and ensure fair usage
- **Batch operations**: Group database operations when possible

### Monitoring Key Metrics
```python
# Application metrics to track
- orchestrator_requests_total (counter)
- orchestrator_request_duration_seconds (histogram)
- pms_circuit_breaker_state (gauge)
- session_cache_hit_ratio (gauge)
- webhook_processing_time (histogram)
- error_rate_by_service (counter)

# Infrastructure metrics to monitor
- container_memory_usage
- postgres_connections_active  
- redis_memory_usage
- nginx_request_rate
```

### Load Testing & Capacity Planning
```bash
# Run performance tests
cd tests/performance/
k6 run load-test.js

# Monitor during load testing
make performance-test        # Run load tests
make analyze-performance     # Generate performance report
make stress-test            # Run stress tests with chaos engineering
```

## Development Tips & Best Practices

### Git Workflow
- **Feature branches**: Always work on feature branches, never directly on main
- **Conventional commits**: Use conventional commit format (`feat:`, `fix:`, `docs:`)
- **PR template**: Fill out the PR template completely
- **Code review**: At least one approval required
- **CI/CD**: All tests must pass before merge

### IDE Setup Recommendations
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### Docker Development Tips
- **Always use absolute paths** when referencing services in Docker
- **Environment variables** are validated at startup - check logs for missing configs
- **Redis locks** are used for reservation conflicts - see `lock_service.py`
- **Audio processing** requires TTS engine configuration (espeak/coqui)
- **PMS operations** are cached aggressively - use cache invalidation patterns
- **Health checks** are crucial for container orchestration
- **Use multi-stage builds** for production Docker images

### Quick Reference Commands
```bash
# Essential daily commands
make install        # Install dependencies
make fmt           # Format code  
make lint          # Lint code
make test          # Run tests
make docker-up     # Start services
make logs          # View logs
make health        # Check service health

# Debugging commands
make debug-db      # Connect to database
make debug-redis   # Connect to Redis
make debug-logs    # Tail filtered logs
make metrics       # View Prometheus metrics

# Performance commands
make performance-test     # Load testing
make stress-test         # Stress testing
make security-scan       # Security scanning
```