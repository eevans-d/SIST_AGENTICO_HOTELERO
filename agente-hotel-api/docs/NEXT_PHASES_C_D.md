# Next Phases: Option C & D Implementation Plan

## Phase Overview

After completing **Option B (QloApps PMS Real Integration)**, we proceed with:

- **Option C**: Deployment & Production Testing
- **Option D**: Enhanced Template Service

---

## OPTION C: Deployment & Production Testing

### Objectives
1. Deploy system to staging environment
2. Validate real QloApps integration
3. Conduct load testing
4. Monitor system performance
5. Execute canary deployment to production

### Phase C.1: Staging Environment Setup

#### Tasks
- [ ] Configure staging QloApps instance
  - [ ] Generate staging API key
  - [ ] Configure hotel and room types
  - [ ] Set up test data (rooms, availability)

- [ ] Update staging environment variables
  ```bash
  PMS_TYPE=qloapps
  PMS_BASE_URL=https://qloapps-staging.yourhotel.com
  PMS_API_KEY=<staging_api_key>
  PMS_HOTEL_ID=1
  CHECK_PMS_IN_READINESS=true
  ```

- [ ] Deploy to staging with Docker Compose
  ```bash
  make deploy ENV=staging
  # or
  docker compose -f docker-compose.production.yml up -d
  ```

- [ ] Verify all services are healthy
  ```bash
  make health
  curl https://staging.agente-hotel.com/health/ready
  ```

**Expected Outcome**: All services running, PMS connection verified

### Phase C.2: Integration Testing in Staging

#### Test Scenarios

##### Test 1: Availability Check
- [ ] Check availability via WhatsApp webhook
  - [ ] Send test message: "¿Tienen habitaciones disponibles para el 15 de enero?"
  - [ ] Verify NLP intent: `check_availability`
  - [ ] Verify PMS API call in logs
  - [ ] Validate response contains room types and prices

##### Test 2: Reservation Creation
- [ ] Create booking via messaging flow
  - [ ] Check availability
  - [ ] Provide guest information
  - [ ] Confirm booking
  - [ ] Verify booking created in QloApps admin
  - [ ] Check confirmation message sent

##### Test 3: Booking Retrieval
- [ ] Query existing reservation
  - [ ] Send message: "¿Cuál es el estado de mi reserva REF12345?"
  - [ ] Verify booking details returned
  - [ ] Check data accuracy against QloApps

##### Test 4: Cancellation Flow
- [ ] Cancel test reservation
  - [ ] Request cancellation via message
  - [ ] Confirm cancellation
  - [ ] Verify status updated in QloApps
  - [ ] Check cache invalidated

##### Test 5: Circuit Breaker
- [ ] Simulate PMS failures
  - [ ] Stop QloApps service temporarily
  - [ ] Send availability request
  - [ ] Verify circuit breaker opens after 5 failures
  - [ ] Check fallback response
  - [ ] Restart QloApps
  - [ ] Verify circuit breaker recovers to HALF_OPEN then CLOSED

**Testing Tools**:
```bash
# Run integration tests
make test

# Run specific PMS tests
pytest tests/integration/test_qloapps_integration.py -v

# Run end-to-end tests
pytest tests/e2e/test_reservation_flow.py -v --skip-mock
```

### Phase C.3: Performance & Load Testing

#### Load Test Scenarios

##### Scenario 1: Normal Load
- **Users**: 50 concurrent
- **Duration**: 10 minutes
- **Operations**: 70% availability, 20% booking, 10% queries

##### Scenario 2: Peak Load
- **Users**: 200 concurrent
- **Duration**: 5 minutes
- **Operations**: Same distribution

##### Scenario 3: Spike Test
- **Users**: 10 → 500 → 10
- **Duration**: 15 minutes
- **Pattern**: Gradual ramp-up, sudden spike, gradual decline

**Load Testing Tools**:
```bash
# Install locust
pip install locust

# Run load test (create locustfile.py)
locust -f tests/load/locustfile.py --host=https://staging.agente-hotel.com
```

**Key Metrics to Monitor**:
- Request latency (P50, P95, P99)
- Error rate (< 1% target)
- PMS API latency
- Cache hit rate (> 70% target)
- Circuit breaker state transitions
- Database connection pool usage
- Redis memory usage

### Phase C.4: Monitoring & Alerting Validation

#### Grafana Dashboards
- [ ] Verify dashboards load correctly
  - [ ] Application metrics dashboard
  - [ ] PMS integration dashboard
  - [ ] Business metrics dashboard

- [ ] Validate metrics collection
  - [ ] Check Prometheus scraping
  - [ ] Verify metrics appear in graphs
  - [ ] Test time range selection

#### AlertManager
- [ ] Configure alert rules
  ```yaml
  # alerts/pms_alerts.yml
  groups:
    - name: pms_alerts
      rules:
        - alert: PMSHighErrorRate
          expr: rate(pms_errors_total[5m]) > 0.1
          for: 2m
          annotations:
            summary: "PMS error rate > 10%"
        
        - alert: PMSCircuitBreakerOpen
          expr: pms_circuit_breaker_state > 0
          for: 1m
          annotations:
            summary: "PMS circuit breaker OPEN"
  ```

- [ ] Test alert firing
  - [ ] Simulate PMS failures
  - [ ] Verify alerts fire in AlertManager
  - [ ] Check notification delivery (email/Slack)

### Phase C.5: Canary Deployment to Production

#### Pre-Deployment Checklist
- [ ] All staging tests pass ✅
- [ ] Load testing results acceptable ✅
- [ ] Monitoring dashboards validated ✅
- [ ] Alerts configured and tested ✅
- [ ] Backup of production database created ✅
- [ ] Rollback plan documented ✅

#### Canary Deployment Steps

1. **Deploy Canary (10% traffic)**
   ```bash
   make canary-deploy CANARY_WEIGHT=10
   ```

2. **Monitor Canary Metrics (15 minutes)**
   - [ ] Compare baseline vs canary error rates
   - [ ] Compare latency (P95 < 10% increase threshold)
   - [ ] Check PMS circuit breaker state

3. **Validate Canary Health**
   ```bash
   make canary-diff  # Runs scripts/canary-deploy.sh
   # Output: .playbook/canary_diff_report.json
   ```

4. **Progressive Rollout**
   - [ ] 10% → 25% (15 min observation)
   - [ ] 25% → 50% (15 min observation)
   - [ ] 50% → 100% (final rollout)

5. **Post-Deployment Validation**
   - [ ] Run smoke tests
   - [ ] Check error logs
   - [ ] Verify PMS integration working
   - [ ] Monitor metrics for 24 hours

**Rollback Trigger Conditions**:
- Error rate > 2x baseline
- P95 latency > 1.5x baseline
- Circuit breaker opens
- Critical business metric degradation

**Rollback Command**:
```bash
make rollback
```

### Phase C.6: Production Monitoring Plan

#### Daily Checks (Automated)
- Health check dashboard review
- Error rate < 1%
- PMS circuit breaker CLOSED
- Cache hit rate > 70%

#### Weekly Checks
- Performance trends review
- Resource utilization analysis
- Cost optimization opportunities
- Security scan results

#### Monthly Checks
- Capacity planning review
- Feature usage analysis
- Technical debt assessment
- Dependency updates

---

## OPTION D: Enhanced Template Service

### Objectives
1. Audit current template system
2. Implement multi-language support
3. Add template versioning
4. Create A/B testing capability
5. Build template management admin UI

### Phase D.1: Current State Audit

#### Tasks
- [ ] Review `app/services/template_service.py`
  - [ ] Document current template structure
  - [ ] Identify hardcoded strings
  - [ ] List supported message types

- [ ] Analyze template usage patterns
  - [ ] Query template usage from logs
  - [ ] Identify most frequent templates
  - [ ] Find pain points (missing templates, inflexible formatting)

- [ ] Assess multi-language needs
  - [ ] English (current primary)
  - [ ] Spanish (high priority)
  - [ ] Portuguese (future consideration)

**Deliverable**: Audit report with findings and recommendations

### Phase D.2: Enhanced Template Architecture

#### New Template Structure

```python
# app/models/template.py

from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel

class TemplateCategory(str, Enum):
    GREETING = "greeting"
    AVAILABILITY = "availability"
    BOOKING = "booking"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    ERROR = "error"
    FALLBACK = "fallback"

class TemplateVersion(BaseModel):
    version: int
    content: str
    created_at: datetime
    is_active: bool
    variant: Optional[str] = None  # For A/B testing

class Template(BaseModel):
    id: str
    category: TemplateCategory
    language: str
    versions: List[TemplateVersion]
    metadata: Dict[str, Any]
```

#### Database Schema

```sql
-- templates table
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- template_versions table
CREATE TABLE template_versions (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES templates(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    variant VARCHAR(50),  -- For A/B testing (e.g., 'control', 'variant_a')
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(template_id, version)
);

-- template_usage_stats table
CREATE TABLE template_usage_stats (
    id SERIAL PRIMARY KEY,
    template_version_id INTEGER REFERENCES template_versions(id),
    used_at TIMESTAMP DEFAULT NOW(),
    response_time_ms INTEGER,
    user_satisfaction_score INTEGER,  -- Optional: from user feedback
    conversion BOOLEAN  -- Did it lead to booking?
);
```

### Phase D.3: Multi-Language Support Implementation

#### Tasks

- [ ] Extract all current templates
  ```python
  # Current (hardcoded)
  def get_availability_response(rooms):
      return f"We have {len(rooms)} rooms available"
  
  # Enhanced (templated)
  def get_availability_response(rooms, language="en"):
      return template_service.render(
          "availability.success",
          language=language,
          context={"room_count": len(rooms)}
      )
  ```

- [ ] Create translation files
  ```yaml
  # templates/en/availability.yaml
  availability:
    success: "We have {{room_count}} room(s) available"
    no_rooms: "Sorry, no rooms available for those dates"
    error: "Unable to check availability. Please try again."
  
  # templates/es/availability.yaml
  availability:
    success: "Tenemos {{room_count}} habitación(es) disponible(s)"
    no_rooms: "Lo sentimos, no hay habitaciones disponibles para esas fechas"
    error: "No se pudo verificar disponibilidad. Intente nuevamente."
  ```

- [ ] Implement template loader
  ```python
  # app/services/enhanced_template_service.py
  
  class EnhancedTemplateService:
      def __init__(self):
          self.templates: Dict[str, Dict[str, Template]] = {}
          self.load_templates()
      
      def load_templates(self):
          """Load templates from database and YAML files"""
          pass
      
      def render(self, template_key: str, language: str = "en", 
                 context: Dict = None) -> str:
          """Render template with context variables"""
          pass
      
      def get_template_version(self, template_key: str, 
                               language: str, variant: str = None) -> TemplateVersion:
          """Get specific template version (for A/B testing)"""
          pass
  ```

- [ ] Integrate with NLP engine for language detection
  ```python
  # Detect user language from message
  detected_language = nlp_engine.detect_language(message.text)
  
  # Use appropriate template
  response = template_service.render(
      "greeting.welcome",
      language=detected_language,
      context={"name": guest_name}
  )
  ```

### Phase D.4: Template Versioning System

#### Implementation

```python
# app/services/template_version_service.py

class TemplateVersionService:
    async def create_version(self, template_id: str, content: str) -> TemplateVersion:
        """Create new template version"""
        # Increment version number
        # Mark old version as inactive
        # Save new version as active
        pass
    
    async def rollback_version(self, template_id: str, version: int) -> bool:
        """Rollback to previous version"""
        pass
    
    async def compare_versions(self, template_id: str, 
                               version_a: int, version_b: int) -> Dict:
        """Compare two versions for diff"""
        pass
    
    async def get_version_history(self, template_id: str) -> List[TemplateVersion]:
        """Get all versions with metadata"""
        pass
```

#### Admin API Endpoints

```python
# app/routers/admin_templates.py

@router.post("/admin/templates")
async def create_template(template: TemplateCreate):
    """Create new template"""
    pass

@router.put("/admin/templates/{template_id}/versions")
async def create_template_version(template_id: str, content: str):
    """Create new version of existing template"""
    pass

@router.post("/admin/templates/{template_id}/rollback/{version}")
async def rollback_template(template_id: str, version: int):
    """Rollback to specific version"""
    pass

@router.get("/admin/templates/{template_id}/history")
async def get_template_history(template_id: str):
    """Get version history"""
    pass
```

### Phase D.5: A/B Testing Framework

#### Implementation

```python
# app/services/ab_testing_service.py

class ABTestingService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def assign_variant(self, user_id: str, experiment_id: str) -> str:
        """Assign user to A/B test variant (sticky assignment)"""
        # Check if user already assigned
        assigned = await self.redis.get(f"ab:{experiment_id}:{user_id}")
        if assigned:
            return assigned
        
        # New assignment (50/50 split by default)
        variant = "control" if hash(user_id) % 2 == 0 else "variant_a"
        await self.redis.setex(
            f"ab:{experiment_id}:{user_id}",
            86400 * 30,  # 30 days
            variant
        )
        return variant
    
    async def track_outcome(self, user_id: str, experiment_id: str, 
                           outcome: str, metadata: Dict = None):
        """Track experiment outcome (e.g., conversion)"""
        variant = await self.get_variant(user_id, experiment_id)
        
        # Log to database for analysis
        await self.db.execute(
            """
            INSERT INTO ab_test_outcomes 
            (experiment_id, user_id, variant, outcome, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            """,
            experiment_id, user_id, variant, outcome, metadata
        )
```

#### Usage Example

```python
# In orchestrator or message handler

# Assign variant for greeting message experiment
variant = await ab_testing_service.assign_variant(
    user_id=message.from_id,
    experiment_id="greeting_v2"
)

# Get appropriate template version
greeting = await template_service.render(
    "greeting.welcome",
    language="en",
    variant=variant,
    context={"name": guest_name}
)

# Track if user proceeds with booking
if booking_created:
    await ab_testing_service.track_outcome(
        user_id=message.from_id,
        experiment_id="greeting_v2",
        outcome="conversion",
        metadata={"booking_id": booking.id}
    )
```

### Phase D.6: Template Management Admin UI

#### Frontend Components

```typescript
// Simple React/Vue components for template management

interface TemplateManagerProps {
  templates: Template[];
  onCreateTemplate: (template: TemplateCreate) => void;
  onUpdateTemplate: (id: string, content: string) => void;
  onRollback: (id: string, version: number) => void;
}

// Components:
// 1. TemplateList - Browse all templates
// 2. TemplateEditor - Edit template content with preview
// 3. TemplateVersionHistory - View and rollback versions
// 4. ABTestDashboard - Monitor A/B test performance
```

#### Admin UI Routes

```
/admin/templates              - List all templates
/admin/templates/new          - Create new template
/admin/templates/{id}         - View/edit template
/admin/templates/{id}/history - Version history
/admin/templates/ab-tests     - A/B test dashboard
```

#### Quick Admin Panel (FastAPI + Jinja2)

For MVP, use server-side rendering:

```python
# app/routers/admin_ui.py

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/templates", response_class=HTMLResponse)
async def templates_dashboard(request: Request):
    all_templates = await template_service.get_all_templates()
    return templates.TemplateResponse(
        "templates_dashboard.html",
        {"request": request, "templates": all_templates}
    )
```

### Phase D.7: Testing & Validation

#### Template Testing Framework

```python
# tests/unit/test_enhanced_templates.py

@pytest.mark.asyncio
async def test_template_rendering():
    service = EnhancedTemplateService()
    
    result = service.render(
        "availability.success",
        language="en",
        context={"room_count": 3}
    )
    
    assert result == "We have 3 room(s) available"

@pytest.mark.asyncio
async def test_multi_language_templates():
    service = EnhancedTemplateService()
    
    en = service.render("greeting.welcome", language="en", context={"name": "John"})
    es = service.render("greeting.welcome", language="es", context={"name": "John"})
    
    assert "Hello" in en
    assert "Hola" in es

@pytest.mark.asyncio
async def test_ab_testing_assignment():
    ab_service = ABTestingService(mock_redis)
    
    # Same user should get same variant
    variant1 = await ab_service.assign_variant("user_123", "exp_001")
    variant2 = await ab_service.assign_variant("user_123", "exp_001")
    
    assert variant1 == variant2
```

### Phase D.8: Rollout Plan

1. **Week 1**: Architecture & database setup
2. **Week 2**: Multi-language support implementation
3. **Week 3**: Template versioning system
4. **Week 4**: A/B testing framework
5. **Week 5**: Admin UI (MVP)
6. **Week 6**: Testing & documentation
7. **Week 7**: Gradual rollout to production

---

## Success Criteria

### Option C: Deployment & Testing
- [ ] Staging environment fully operational
- [ ] All integration tests pass
- [ ] Load testing results within acceptable limits
- [ ] Zero-downtime production deployment achieved
- [ ] Monitoring and alerting validated
- [ ] 24-hour post-deployment stability

### Option D: Enhanced Template Service
- [ ] Multi-language support for 2+ languages
- [ ] Template versioning with rollback capability
- [ ] A/B testing framework operational
- [ ] Admin UI for template management
- [ ] 95%+ code coverage for new features
- [ ] Documentation complete

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| C.1 Staging Setup | 2 days | QloApps staging instance |
| C.2 Integration Testing | 3 days | C.1 complete |
| C.3 Load Testing | 2 days | C.2 complete |
| C.4 Monitoring Validation | 1 day | C.3 complete |
| C.5 Canary Deployment | 1 day | All C phases complete |
| C.6 Production Monitoring | Ongoing | C.5 complete |
| **Option C Total** | **~10 days** | |
| | | |
| D.1 Current Audit | 2 days | None |
| D.2 Architecture Design | 2 days | D.1 complete |
| D.3 Multi-Language | 5 days | D.2 complete |
| D.4 Template Versioning | 3 days | D.2 complete |
| D.5 A/B Testing | 4 days | D.2 complete |
| D.6 Admin UI | 5 days | D.3-D.5 complete |
| D.7 Testing | 3 days | D.6 complete |
| D.8 Rollout | 2 days | D.7 complete |
| **Option D Total** | **~26 days** | |

---

## Resources Needed

### Option C
- Staging QloApps instance
- Load testing tool (Locust/K6)
- Production credentials (with approval)
- Monitoring access (Grafana/Prometheus)

### Option D
- Frontend developer (for admin UI, if complex)
- Translation services (for multi-language templates)
- Database migrations approval
- UX review for template editor

---

## Risk Mitigation

### Option C Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| PMS staging unavailable | High | Have mock fallback ready |
| Load test reveals issues | Medium | Buffer time for optimization |
| Production deployment fails | High | Rollback plan documented |

### Option D Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Template migration complexity | Medium | Gradual migration, keep old system |
| Translation quality issues | Low | Professional translation service |
| A/B testing adds latency | Low | Cache variant assignments |

---

**Document Version**: 1.0  
**Created**: 2025-01-07  
**Status**: Planning Phase  
**Next Review**: After Option C completion
