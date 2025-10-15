# Runbook: High Error Rate

**Severity**: CRITICAL  
**SLA**: 15 minutes to mitigation  
**On-Call**: Backend Team + SRE Team

---

## Symptoms

- High rate of 5xx errors
- Error rate > 5%
- Multiple failing endpoints
- Metric: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05`

## Detection

```promql
# High error rate alert
rate(http_requests_total{status=~"5.."}[5m]) / 
rate(http_requests_total[5m]) > 0.05
```

## Impact Assessment

- **User Impact**: Service failures, poor experience
- **Business Impact**: Lost transactions, reputation damage
- **System Impact**: Potential cascade failures

---

## Immediate Actions (0-5 minutes)

### 1. Identify Error Pattern

```bash
# Check recent errors
docker logs agente-api --since 10m | grep -i "error\|exception" | tail -50

# Check error distribution by endpoint
curl 'http://localhost:9090/api/v1/query?query=
  topk(10, rate(http_requests_total{status=~"5.."}[5m]))
'

# Check error types
curl http://localhost:8000/metrics | grep http_requests_total | grep "5"
```

### 2. Check System Health

```bash
# Overall health
curl http://localhost:8000/health/ready | jq .

# Dependencies status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Resource usage
docker stats --no-stream agente-api
```

### 3. Quick Mitigation - Circuit Breaker

```bash
# If external service causing errors, open circuit breaker
curl -X POST http://localhost:8000/admin/circuit-breaker/pms/open

# Or restart service to clear state
docker-compose restart agente-api
```

---

## Investigation (5-15 minutes)

### Check Common Causes

#### A. Database Errors

```bash
# Check database connectivity
docker exec postgres-agente pg_isready

# Check for connection errors
docker logs agente-api | grep -i "database\|postgres\|sqlalchemy" | tail -20

# Check active connections
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Check for lock waits
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;
"
```

#### B. External API Failures

```bash
# Check PMS errors
docker logs agente-api | grep "PMS" | grep -i "error" | tail -20

# Check WhatsApp errors
docker logs agente-api | grep "WhatsApp" | grep -i "error" | tail -20

# Check circuit breaker states
curl http://localhost:8000/metrics | grep circuit_breaker_state

# Test external APIs manually
curl -I https://qloapps.example.com/api/hotels
curl -I https://graph.facebook.com/v18.0/
```

#### C. Unhandled Exceptions

```bash
# Check for Python tracebacks
docker logs agente-api | grep "Traceback" -A 10 | tail -50

# Check for specific exceptions
docker logs agente-api | grep -E "Exception|Error" | sort | uniq -c | sort -nr | head -10

# Check exception types
curl http://localhost:8000/metrics | grep exceptions_total
```

#### D. Resource Exhaustion

```bash
# Check memory
docker stats agente-api --no-stream | awk '{print $3}'

# Check CPU
docker stats agente-api --no-stream | awk '{print $2}'

# Check file descriptors
docker exec agente-api sh -c "ls -1 /proc/self/fd | wc -l"

# Check for thread exhaustion
docker exec agente-api ps aux | wc -l
```

#### E. Recent Deployment Issues

```bash
# Check recent changes
git log --since="2 hours ago" --oneline

# Compare with previous version
git diff HEAD~1 app/

# Check deployment time correlation
docker inspect agente-api | jq '.[0].State.StartedAt'
```

---

## Resolution Steps

### Option 1: Rollback Recent Deployment

```bash
# If errors started after recent deploy
make rollback

# Verify error rate drops
watch -n 10 'curl -s http://localhost:8000/metrics | grep http_requests_total | grep "5"'
```

### Option 2: Fix Database Connection Pool

```python
# app/core/database.py
engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=20,        # Increase pool size
    max_overflow=10,     # Allow overflow
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

### Option 3: Add Error Handling for External APIs

```python
# app/services/pms_adapter.py
@retry_with_backoff(max_attempts=3, base_delay=1)
async def check_availability(self, ...):
    try:
        result = await self._api_call(...)
        return result
    except PMSError as e:
        logger.error(f"PMS error: {e}")
        # Return cached data if available
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Returning cached availability")
            return cached
        raise
```

### Option 4: Implement Global Exception Handler

```python
# app/main.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.state.correlation_id
        }
    )
```

### Option 5: Increase Resource Limits

```yaml
# docker-compose.yml
services:
  agente-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## Validation

### 1. Check Error Rate

```bash
# Current error rate (should be < 1%)
curl 'http://localhost:9090/api/v1/query?query=
  rate(http_requests_total{status=~"5.."}[5m]) /
  rate(http_requests_total[5m])
'

# Error count by status code
curl http://localhost:8000/metrics | grep http_requests_total | grep status=\"5

# Recent errors in logs
docker logs agente-api --since 5m | grep -c "ERROR"
```

### 2. Run Smoke Tests

```bash
# Test critical endpoints
make test-smoke

# Test full flow
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "guest_name": "Test User",
    "check_in": "2024-11-01",
    "check_out": "2024-11-03"
  }'
```

### 3. Monitor for 15 Minutes

```bash
# Watch error rate
watch -n 30 'curl -s "http://localhost:9090/api/v1/query?query=
  rate(http_requests_total{status=~\"5..\"}[5m]) /
  rate(http_requests_total[5m])
" | jq .'
```

---

## Communication Template

**Initial Alert**:
```
🚨 INCIDENT: High Error Rate Detected
Severity: CRITICAL
Status: INVESTIGATING
Impact: XX% of requests failing (threshold: 5%)
Affected: [List of failing endpoints]
ETA: Investigating, update in 10 minutes
```

**Update**:
```
📊 ERROR RATE UPDATE
Current Rate: XX% (was YY%)
Root Cause: [Database/External API/Code bug/etc.]
Actions: [What we're doing]
Progress: [Error rate trend]
Workarounds: [Any available alternatives]
```

**Resolution**:
```
✅ RESOLVED: Error Rate Normalized
Duration: XX minutes
Final Rate: XX% (target: <1%)
Root Cause: [Detailed explanation]
Fix: [Rollback/Config change/Code fix]
Validation: Smoke tests passing, error rate stable
```

---

## Post-Incident

### 1. Error Analysis

```bash
# Generate error report
python scripts/error-analysis.py --since="2 hours ago" > error_report.txt

# Categorize errors
docker logs agente-api | grep ERROR | awk '{print $NF}' | sort | uniq -c | sort -nr

# Identify error correlation
# Check if errors cluster by time, user, endpoint, etc.
```

### 2. Add Monitoring for Specific Errors

```python
# app/core/middleware.py
from prometheus_client import Counter

errors_by_type = Counter(
    'errors_by_type_total',
    'Errors by exception type',
    ['exception_type', 'endpoint']
)

@app.middleware("http")
async def error_tracking_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        errors_by_type.labels(
            exception_type=type(e).__name__,
            endpoint=request.url.path
        ).inc()
        raise
```

### 3. Implement Error Budget

```yaml
# SLO: 99.9% availability = 0.1% error budget
- alert: ErrorBudgetBurning
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[1h])) /
      sum(rate(http_requests_total[1h]))
    ) > 0.001
  for: 5m
  annotations:
    summary: "Error budget being depleted rapidly"
```

### 4. Action Items

- [ ] Add unit tests for error scenarios
- [ ] Implement circuit breakers for all external APIs
- [ ] Add retry logic with exponential backoff
- [ ] Improve error messages and logging
- [ ] Set up error aggregation dashboard
- [ ] Create error handling guidelines
- [ ] Schedule error handling review

---

## Prevention

- **Testing**: Test error paths in CI/CD
- **Monitoring**: Alert on error rate > 1% (warning), > 5% (critical)
- **Resilience**: Circuit breakers, retries, timeouts
- **Logging**: Structured error logging with context
- **Review**: Weekly error pattern analysis

## Error Rate Targets

| Window | Target | Warning | Critical |
|--------|--------|---------|----------|
| 5 minutes | < 0.1% | > 1% | > 5% |
| 1 hour | < 0.5% | > 2% | > 10% |
| 24 hours | < 1% | > 3% | > 15% |
| SLO (monthly) | 99.9% | 99.5% | 99% |

## Error Troubleshooting Checklist

- [ ] Check recent deployments
- [ ] Verify external API status
- [ ] Check database connectivity
- [ ] Review resource usage
- [ ] Examine error logs
- [ ] Test with curl/Postman
- [ ] Check circuit breaker states
- [ ] Verify configuration
- [ ] Review recent code changes
- [ ] Check for infrastructure issues

## Related Runbooks

- [01-database-down.md](./01-database-down.md)
- [05-pms-integration-failure.md](./05-pms-integration-failure.md)
- [09-circuit-breaker-open.md](./09-circuit-breaker-open.md)
- [10-deployment-failure.md](./10-deployment-failure.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: SRE Team, QA Team
