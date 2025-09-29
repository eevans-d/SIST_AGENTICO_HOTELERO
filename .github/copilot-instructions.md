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

## Advanced Service Architecture Deep Dive

### Core Service Components Detailed Analysis

#### 1. Orchestrator Service (`app/services/orchestrator.py`)
**Purpose**: Central coordination hub for all AI-driven hotel operations
**Key Responsibilities**:
- Message intent classification and routing
- Multi-service workflow coordination
- State management across conversation flows
- Error recovery and fallback strategies

**Integration Points**:
```python
# Primary service dependencies
- PMS Adapter: Room availability, reservations, guest data
- NLP Engine: Intent recognition, entity extraction  
- Session Manager: Conversation state persistence
- Template Service: Response generation and localization
- WhatsApp/Gmail Clients: Multi-channel messaging
```

**Critical Patterns**:
```python
# Orchestrator workflow example
async def process_guest_request(self, message: UnifiedMessage) -> OrchestrationResponse:
    # 1. Intent classification
    intent = await self.nlp_engine.classify_intent(message.text)
    
    # 2. Context retrieval
    session = await self.session_manager.get_session(message.user_id)
    
    # 3. Business logic routing
    if intent == "reservation_request":
        response = await self._handle_reservation_flow(message, session)
    elif intent == "inquiry":
        response = await self._handle_inquiry_flow(message, session)
    
    # 4. Response templating
    final_response = await self.template_service.format_response(response)
    
    # 5. Session state update
    await self.session_manager.update_session(session.id, response.state_changes)
    
    return final_response
```

#### 2. PMS Adapter (`app/services/pms_adapter.py`)
**Purpose**: QloApps PMS integration layer with resilience patterns
**Key Features**:
- Circuit breaker implementation for fault tolerance
- Redis-based response caching with intelligent TTL
- Comprehensive error handling and retry logic
- Rate limiting compliance with PMS API constraints

**Circuit Breaker Configuration**:
```python
# Circuit breaker thresholds
FAILURE_THRESHOLD = 5      # Failures before opening circuit
RECOVERY_TIMEOUT = 30      # Seconds before attempting recovery
SUCCESS_THRESHOLD = 3      # Successes needed to close circuit
```

**Caching Strategy**:
```python
# Cache TTL by operation type
CACHE_PATTERNS = {
    'room_availability': 300,      # 5 minutes
    'guest_profile': 1800,         # 30 minutes  
    'hotel_info': 3600,           # 1 hour
    'booking_policies': 7200       # 2 hours
}
```

#### 3. Session Manager (`app/services/session_manager.py`)
**Purpose**: Persistent conversation state management
**State Architecture**:
```python
class UserSession:
    user_id: str
    conversation_context: Dict
    current_intent: Optional[str]
    pending_actions: List[Action]
    guest_profile: Optional[GuestProfile]
    last_activity: datetime
    session_metadata: Dict
```

**Session Lifecycle**:
- **Creation**: On first user interaction
- **Updates**: After each conversation turn
- **Expiration**: Configurable TTL (default 24 hours)
- **Cleanup**: Background task removes expired sessions

#### 4. NLP Engine (`app/services/nlp_engine.py`)
**Purpose**: Natural language processing for intent recognition
**Capabilities**:
- Multi-language support (Spanish, English)
- Intent classification with confidence scoring
- Entity extraction (dates, room types, guest counts)
- Contextual understanding using conversation history

**Intent Categories**:
```python
SUPPORTED_INTENTS = {
    'reservation_request': 'Guest wants to make a booking',
    'availability_check': 'Guest checking room availability',
    'modification_request': 'Changes to existing reservation',
    'cancellation_request': 'Booking cancellation',
    'general_inquiry': 'Information about hotel services',
    'complaint': 'Guest complaint or issue report',
    'compliment': 'Positive feedback',
    'greeting': 'Conversation starter',
    'goodbye': 'Conversation ender'
}
```

#### 5. Feature Flag Service (`app/services/feature_flag_service.py`)
**Purpose**: Dynamic feature enablement and A/B testing
**Configuration**:
```python
# Feature flags for gradual rollouts
FEATURE_FLAGS = {
    'enable_audio_processing': True,
    'advanced_nlp_models': False,
    'predictive_pricing': True,
    'multi_language_support': True,
    'ai_upselling': False
}
```

### Message Processing Pipeline Deep Dive

#### 1. Webhook Reception (`app/routers/webhooks.py`)
**WhatsApp Webhook Processing**:
```python
@router.post("/whatsapp")
async def whatsapp_webhook(request: WebhookRequest):
    # 1. Signature verification (HMAC-SHA256)
    if not verify_webhook_signature(request.raw_body, request.headers):
        raise HTTPException(401, "Invalid signature")
    
    # 2. Message parsing and normalization
    unified_message = parse_whatsapp_message(request.data)
    
    # 3. Rate limiting check
    if await rate_limiter.is_rate_limited(unified_message.user_id):
        return rate_limit_response()
    
    # 4. Background processing
    background_tasks.add_task(process_message_async, unified_message)
    
    return {"status": "received"}
```

#### 2. Message Gateway (`app/services/message_gateway.py`)
**Purpose**: Unified message handling across channels
**Processing Flow**:
1. **Message Validation**: Schema validation, sanitization
2. **Channel Detection**: WhatsApp, Gmail, SMS identification
3. **User Identification**: Phone number, email mapping
4. **Security Checks**: Spam detection, abuse prevention
5. **Orchestrator Handoff**: Route to main processing engine

### Database Architecture & Patterns

#### Core Database Models
```python
# Primary entities
class UserSession(SQLAlchemyBase):
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    conversation_context: Mapped[Dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class LockAudit(SQLAlchemyBase):
    __tablename__ = "lock_audit"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    operation_type: Mapped[str] = mapped_column(String, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    holder_id: Mapped[str] = mapped_column(String, nullable=False)
```

#### Database Connection Management
```python
# Async connection pool configuration
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'connect_args': {
        'server_settings': {
            'application_name': 'agente-hotel-api',
            'jit': 'off'
        }
    }
}
```

### Security Framework Deep Dive

#### 1. Authentication & Authorization
```python
# JWT token configuration
JWT_CONFIG = {
    'algorithm': 'HS256',
    'access_token_expire_minutes': 1440,
    'refresh_token_expire_days': 30,
    'secret_key': 'MUST_BE_SET_IN_PRODUCTION'
}

# Rate limiting tiers
RATE_LIMITS = {
    'guest_messages': '10/minute',
    'admin_api': '100/minute',
    'webhook_endpoints': '1000/hour',
    'health_checks': '60/minute'
}
```

#### 2. Input Validation & Sanitization
```python
# Pydantic models for input validation
class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(..., regex=r'^[a-zA-Z0-9_+-]+$')
    channel: Literal['whatsapp', 'gmail', 'sms']
    metadata: Optional[Dict] = Field(default_factory=dict)
    
    @validator('text')
    def sanitize_text(cls, v):
        return bleach.clean(v, strip=True)
```

#### 3. Webhook Security
```python
def verify_whatsapp_signature(payload: bytes, signature: str) -> bool:
    """Verify WhatsApp webhook signature using HMAC-SHA256"""
    expected_signature = hmac.new(
        WHATSAPP_APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

### Monitoring & Observability Comprehensive Framework

#### 1. Prometheus Metrics Collection
```python
# Custom metrics definitions
METRICS_REGISTRY = {
    # Business metrics
    'guest_interactions_total': Counter('guest_interactions_total', ['channel', 'intent']),
    'reservations_created_total': Counter('reservations_created_total', ['room_type']),
    'pms_operations_total': Counter('pms_operations_total', ['operation', 'status']),
    
    # Performance metrics  
    'request_duration_seconds': Histogram('request_duration_seconds', ['endpoint']),
    'pms_response_time_seconds': Histogram('pms_response_time_seconds', ['operation']),
    'session_processing_time': Histogram('session_processing_time_seconds'),
    
    # Health metrics
    'circuit_breaker_state': Gauge('circuit_breaker_state', ['service']),
    'active_sessions_count': Gauge('active_sessions_count'),
    'redis_connection_pool_size': Gauge('redis_connection_pool_size')
}
```

#### 2. Structured Logging Framework
```python
# Logging configuration with correlation IDs
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'processors': [
        'structlog.stdlib.filter_by_level',
        'structlog.stdlib.add_logger_name',
        'structlog.stdlib.add_log_level', 
        'structlog.stdlib.PositionalArgumentsFormatter',
        'structlog.processors.TimeStamper',
        'structlog.processors.StackInfoRenderer',
        'structlog.processors.format_exc_info',
        'structlog.processors.UnicodeDecoder',
        'structlog.processors.JSONRenderer'
    ]
}
```

#### 3. Health Check Architecture
```python
# Comprehensive health check implementation
@router.get("/health/ready")
async def readiness_check():
    checks = await asyncio.gather(
        check_database_connection(),
        check_redis_connection(),
        check_pms_connectivity(),
        check_critical_services(),
        return_exceptions=True
    )
    
    failed_checks = [check for check in checks if isinstance(check, Exception)]
    
    if failed_checks:
        raise HTTPException(503, detail={
            'status': 'unhealthy',
            'failed_checks': len(failed_checks),
            'errors': [str(err) for err in failed_checks]
        })
    
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': settings.app_version,
        'checks_passed': len(checks)
    }
```

### Testing Framework Excellence

#### 1. Test Architecture Layers
```python
# Test configuration by type
TEST_CONFIGS = {
    'unit': {
        'database': 'sqlite:///:memory:',
        'redis': 'fakeredis',
        'external_apis': 'mocked'
    },
    'integration': {
        'database': 'postgresql://test_db',
        'redis': 'redis://localhost:6380',  # Test Redis instance
        'external_apis': 'test_endpoints'
    },
    'e2e': {
        'database': 'postgresql://e2e_db', 
        'redis': 'redis://localhost:6381',
        'external_apis': 'staging_endpoints'
    }
}
```

#### 2. Advanced Test Fixtures
```python
# Comprehensive test fixtures
@pytest.fixture
async def orchestrator_with_mocks():
    """Fully configured orchestrator with all dependencies mocked"""
    with patch.multiple(
        'app.services.pms_adapter.PMSAdapter',
        search_rooms=AsyncMock(return_value=mock_rooms),
        create_reservation=AsyncMock(return_value=mock_reservation),
        get_guest_profile=AsyncMock(return_value=mock_guest)
    ):
        orchestrator = OrchestrationService()
        yield orchestrator
```

#### 3. Performance Testing Patterns
```python
# Load testing configuration
LOAD_TEST_SCENARIOS = {
    'normal_load': {
        'concurrent_users': 50,
        'ramp_up_time': '2m',
        'test_duration': '10m',
        'target_rps': 10
    },
    'peak_load': {
        'concurrent_users': 200,
        'ramp_up_time': '5m', 
        'test_duration': '20m',
        'target_rps': 50
    },
    'stress_test': {
        'concurrent_users': 500,
        'ramp_up_time': '10m',
        'test_duration': '30m',
        'target_rps': 100
    }
}
```

## Deployment & Operations Excellence

### Container Architecture & Docker Patterns

#### 1. Multi-Stage Dockerfile Strategy
```dockerfile
# Production Dockerfile patterns
FROM python:3.12-slim as base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base as dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-dev

FROM base as production
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY app/ /app/
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Docker Compose Service Orchestration
```yaml
# Production docker-compose configuration
services:
  agente-api:
    build: 
      context: .
      dockerfile: Dockerfile.production
    environment:
      - ENV=production
      - LOG_LEVEL=info
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - agente-api
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.1'
```

### Infrastructure Monitoring Deep Dive

#### 1. Prometheus Configuration Excellence
```yaml
# prometheus.yml - Comprehensive scraping configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

scrape_configs:
  - job_name: 'agente-api'
    static_configs:
      - targets: ['agente-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
      
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### 2. Grafana Dashboard Configuration
```json
// Grafana dashboard for hotel agent metrics
{
  "dashboard": {
    "title": "Agente Hotelero - Operations Dashboard",
    "panels": [
      {
        "title": "Guest Interactions Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(guest_interactions_total[5m])",
            "legendFormat": "{{channel}} - {{intent}}"
          }
        ]
      },
      {
        "title": "PMS Circuit Breaker Status",
        "type": "singlestat",
        "targets": [
          {
            "expr": "circuit_breaker_state{service=\"pms_adapter\"}"
          }
        ]
      },
      {
        "title": "Response Time Percentiles",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      }
    ]
  }
}
```

### Advanced Error Handling & Recovery Patterns

#### 1. Circuit Breaker Implementation
```python
class CircuitBreaker:
    """Advanced circuit breaker with exponential backoff"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    async def call(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
                
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
            
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
```

#### 2. Retry Logic with Exponential Backoff
```python
class RetryHandler:
    """Intelligent retry handler with jitter"""
    
    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                    
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                if jitter:
                    delay *= (0.5 + random.random() * 0.5)  # Add jitter
                    
                logger.warning(
                    "Retry attempt failed, retrying after delay",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e)
                )
                await asyncio.sleep(delay)
```

### Database Operations & Migration Patterns

#### 1. Database Migration Management
```python
# Alembic migration patterns
"""Add session expiration tracking

Revision ID: abc123def456
Revises: def456ghi789
Create Date: 2024-01-15 10:30:00.000000
"""

def upgrade():
    op.add_column('user_sessions', 
        sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.create_index('idx_user_sessions_expires_at', 
        'user_sessions', ['expires_at'])
    
    # Data migration for existing records
    op.execute("""
        UPDATE user_sessions 
        SET expires_at = updated_at + INTERVAL '24 hours'
        WHERE expires_at IS NULL
    """)

def downgrade():
    op.drop_index('idx_user_sessions_expires_at')
    op.drop_column('user_sessions', 'expires_at')
```

#### 2. Database Connection Pool Optimization
```python
# Advanced connection pool configuration
DATABASE_POOL_CONFIG = {
    'pool_size': 20,           # Base connections
    'max_overflow': 30,        # Additional connections under load
    'pool_pre_ping': True,     # Validate connections before use
    'pool_recycle': 3600,      # Recycle connections every hour
    'pool_timeout': 20,        # Timeout for getting connection
    'echo': False,             # Set to True for SQL debugging
    'connect_args': {
        'server_settings': {
            'application_name': 'agente-hotel-api',
            'statement_timeout': '30000',  # 30 second query timeout
            'idle_in_transaction_session_timeout': '60000'
        }
    }
}
```

### Advanced Caching Strategies

#### 1. Multi-Layer Caching Architecture
```python
class CacheManager:
    """Multi-layer caching with Redis and in-memory layers"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute TTL
        
    async def get(self, key: str, cache_layer: str = 'auto') -> Optional[Any]:
        """Get value with cache layer fallback"""
        
        # Try memory cache first (fastest)
        if cache_layer in ['auto', 'memory']:
            if key in self.memory_cache:
                logger.debug("Cache hit - memory", key=key)
                return self.memory_cache[key]
        
        # Try Redis cache (network call)
        if cache_layer in ['auto', 'redis']:
            try:
                value = await self.redis_client.get(key)
                if value:
                    deserialized = json.loads(value)
                    # Populate memory cache for future requests
                    self.memory_cache[key] = deserialized
                    logger.debug("Cache hit - redis", key=key)
                    return deserialized
            except Exception as e:
                logger.warning("Redis cache error", key=key, error=str(e))
        
        logger.debug("Cache miss", key=key)
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in both cache layers"""
        try:
            # Set in Redis with TTL
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            
            # Set in memory cache
            self.memory_cache[key] = value
            
            logger.debug("Cache set", key=key, ttl=ttl)
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
```

#### 2. Intelligent Cache Invalidation
```python
class CacheInvalidator:
    """Smart cache invalidation based on data relationships"""
    
    INVALIDATION_PATTERNS = {
        'guest_profile_updated': [
            'guest_profile:{guest_id}',
            'guest_reservations:{guest_id}',
            'session_context:{user_id}'
        ],
        'room_availability_changed': [
            'room_search:*',
            'availability:*',
            'pricing:*'
        ],
        'hotel_policy_updated': [
            'hotel_info:*',
            'booking_policies:*'
        ]
    }
    
    async def invalidate_by_event(self, event: str, context: Dict[str, Any]):
        """Invalidate cache based on business events"""
        patterns = self.INVALIDATION_PATTERNS.get(event, [])
        
        for pattern in patterns:
            # Replace placeholders with actual values
            cache_key = pattern.format(**context)
            
            if '*' in cache_key:
                # Pattern matching for multiple keys
                await self._invalidate_pattern(cache_key)
            else:
                # Single key invalidation
                await self.cache_manager.delete(cache_key)
```

### Security Hardening & Compliance

#### 1. Advanced Input Validation
```python
class SecurityValidator:
    """Comprehensive input validation and sanitization"""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union|select|insert|update|delete|drop|create|alter)\s",
        r"(?i)(or|and)\s+\d+\s*=\s*\d+",
        r"(?i)'?\s*(or|and)\s+'?\w+",
        r"(?i)(exec|execute|sp_|xp_)"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed"
    ]
    
    @staticmethod
    def validate_user_input(text: str) -> bool:
        """Validate user input against security threats"""
        
        # Check for SQL injection
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning("SQL injection attempt detected", text=text[:100])
                return False
        
        # Check for XSS
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("XSS attempt detected", text=text[:100])
                return False
                
        return True
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text input while preserving functionality"""
        # Remove potentially dangerous HTML tags
        text = bleach.clean(
            text,
            tags=['b', 'i', 'u', 'em', 'strong'],  # Allowed tags
            attributes={},  # No attributes allowed
            strip=True
        )
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
```

#### 2. Rate Limiting & DDoS Protection
```python
class AdvancedRateLimiter:
    """Multi-tier rate limiting with sliding windows"""
    
    RATE_LIMIT_TIERS = {
        'guest_message': {
            'requests': 10,
            'window': 60,      # 10 requests per minute
            'burst_limit': 20  # Allow bursts up to 20
        },
        'api_call': {
            'requests': 100,
            'window': 60,      # 100 requests per minute
            'burst_limit': 150
        },
        'webhook': {
            'requests': 1000,
            'window': 3600,    # 1000 requests per hour
            'burst_limit': 1200
        }
    }
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        tier: str,
        request_weight: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        
        config = self.RATE_LIMIT_TIERS[tier]
        key = f"rate_limit:{tier}:{identifier}"
        
        # Use Redis sliding window counter
        pipe = self.redis_client.pipeline()
        
        # Remove expired entries
        cutoff = time.time() - config['window']
        pipe.zremrangebyscore(key, 0, cutoff)
        
        # Add current request
        now = time.time()
        pipe.zadd(key, {str(uuid.uuid4()): now})
        
        # Get current count
        pipe.zcard(key)
        
        # Set expiration
        pipe.expire(key, config['window'])
        
        results = await pipe.execute()
        current_count = results[2]
        
        # Check against limits
        limit_exceeded = current_count > config['requests']
        burst_exceeded = current_count > config['burst_limit']
        
        return not (limit_exceeded or burst_exceeded), {
            'current_count': current_count,
            'limit': config['requests'],
            'burst_limit': config['burst_limit'],
            'window': config['window'],
            'reset_time': now + config['window']
        }
```

### Operational Excellence & SLI/SLO Management

#### 1. Service Level Indicators (SLI) Definition
```python
SLI_DEFINITIONS = {
    'availability': {
        'description': 'Percentage of successful health checks',
        'query': '(sum(rate(health_check_success_total[5m])) / sum(rate(health_check_total[5m]))) * 100',
        'target': 99.9  # 99.9% availability
    },
    'latency': {
        'description': '95th percentile response time',
        'query': 'histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))',
        'target': 0.5   # 500ms p95 latency
    },
    'error_rate': {
        'description': 'Percentage of requests resulting in errors',
        'query': '(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100',
        'target': 0.1   # 0.1% error rate
    },
    'pms_integration_success': {
        'description': 'PMS operation success rate',
        'query': '(sum(rate(pms_operations_total{status="success"}[5m])) / sum(rate(pms_operations_total[5m]))) * 100',
        'target': 99.5  # 99.5% PMS integration success
    }
}
```

#### 2. Automated Alerting Rules
```yaml
# Alert rules configuration
groups:
  - name: hotel_agent.rules
    rules:
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m])) /
            sum(rate(http_requests_total[5m]))
          ) * 100 > 1
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% for the last 5 minutes"
          
      - alert: PMSCircuitBreakerOpen
        expr: circuit_breaker_state{service="pms_adapter"} == 2
        for: 1m
        labels:
          severity: critical
          team: integrations
        annotations:
          summary: "PMS circuit breaker is open"
          description: "PMS integration is failing, circuit breaker opened"
          
      - alert: HighMemoryUsage
        expr: |
          (
            container_memory_usage_bytes{name="agente-api"} /
            container_spec_memory_limit_bytes{name="agente-api"}
          ) * 100 > 80
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High memory usage in agente-api container"
          description: "Memory usage is {{ $value }}%"
```

## Final Implementation Checklist

### Pre-Production Verification
- [ ] **Security Audit**: Complete security scan with no HIGH/CRITICAL findings
- [ ] **Performance Testing**: Load tests pass under expected traffic patterns
- [ ] **Integration Testing**: All PMS integration scenarios validated
- [ ] **Monitoring Setup**: All SLIs tracked with appropriate alerting
- [ ] **Documentation**: API documentation complete and accurate
- [ ] **Rollback Plan**: Tested rollback procedures for all components
- [ ] **Environment Parity**: Production mirrors staging configuration
- [ ] **SSL/TLS**: Valid certificates installed and auto-renewal configured
- [ ] **Backup Strategy**: Database and configuration backups automated
- [ ] **Incident Response**: On-call procedures and runbooks prepared

This comprehensive enhancement provides maximum exhaustiveness, depth, precision, detail and efficiency for the entire project lifecycle.