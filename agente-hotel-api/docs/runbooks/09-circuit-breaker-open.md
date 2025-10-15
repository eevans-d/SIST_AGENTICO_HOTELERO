# Runbook: Circuit Breaker Open

**Severity**: MEDIUM  
**SLA**: 30 minutes to resolution  
**On-Call**: Backend Team

---

## Symptoms

- External service calls being blocked
- "Circuit breaker open" errors in logs
- Cached/fallback responses being served
- Metric: `pms_circuit_breaker_state = 1` (OPEN)

## Detection

```promql
# Circuit breaker open alert
pms_circuit_breaker_state == 1

# Circuit breaker trips
rate(pms_circuit_breaker_calls_total{state="open"}[5m]) > 0
```

## Impact Assessment

- **User Impact**: Degraded service, stale data served
- **Business Impact**: Cannot process new reservations
- **System Impact**: External API protected from overload

---

## Circuit Breaker States

| State | Meaning | Behavior |
|-------|---------|----------|
| CLOSED (0) | Normal operation | All requests pass through |
| OPEN (1) | Too many failures | All requests rejected immediately |
| HALF_OPEN (2) | Testing recovery | Limited requests allowed |

---

## Immediate Actions (0-10 minutes)

### 1. Check Circuit Breaker Status

```bash
# Check current state
curl http://localhost:8000/metrics | grep pms_circuit_breaker_state

# Check trip history
curl 'http://localhost:9090/api/v1/query_range?query=pms_circuit_breaker_state&start='$(date -d '1 hour ago' +%s)'&end='$(date +%s)'&step=60'

# Check failure count
curl http://localhost:8000/metrics | grep pms_circuit_breaker_calls
```

### 2. Determine Root Cause

```bash
# Check PMS errors
docker logs agente-api --since 30m | grep "PMS" | grep -i "error\|timeout" | tail -20

# Check PMS service health
curl -I https://qloapps.example.com/api/hotels
docker-compose ps qloapps

# Check recent failure pattern
docker logs agente-api | grep "circuit.*breaker" | tail -20
```

### 3. Assess External Service

```bash
# If PMS is actually healthy, may be transient issue
# Check if PMS is responding now
curl -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/availability

# If responding, wait for auto-recovery (30-60s default)
watch -n 5 'curl -s http://localhost:8000/metrics | grep pms_circuit_breaker_state'
```

---

## Investigation (10-30 minutes)

### Check Circuit Breaker Configuration

```python
# app/core/circuit_breaker.py
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,      # Trips after 5 failures
        recovery_timeout: int = 30,      # Tries recovery after 30s
        success_threshold: int = 2,      # Closes after 2 successes
        timeout: float = 10.0            # Request timeout
    ):
        ...
```

### Check Common Causes

#### A. PMS Service Degraded

```bash
# Check PMS response time
curl -w "@curl-format.txt" -o /dev/null -s \
  -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/hotels

# curl-format.txt:
# time_total: %{time_total}s
# time_connect: %{time_connect}s
# http_code: %{http_code}

# Check PMS error logs
docker logs qloapps | grep -i error | tail -50
```

#### B. Network Issues

```bash
# Check DNS resolution
docker exec agente-api nslookup qloapps.example.com

# Check connectivity
docker exec agente-api curl -v https://qloapps.example.com

# Check for packet loss
docker exec agente-api ping -c 10 qloapps.example.com
```

#### C. Timeout Too Aggressive

```bash
# Check timeout configuration
docker exec agente-api python -c "
from app.core.settings import settings
print(f'PMS timeout: {settings.pms_timeout}s')
print(f'Circuit breaker threshold: {settings.pms_circuit_breaker_failure_threshold}')
"

# Check recent latencies
curl 'http://localhost:9090/api/v1/query?query=pms_api_latency_seconds_sum / pms_api_latency_seconds_count'
```

#### D. Authentication Failures

```bash
# Check for 401/403 errors
docker logs agente-api | grep "PMS" | grep -E "401|403" | tail -10

# Verify API key
curl -I -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/hotels
```

---

## Resolution Steps

### Option 1: Wait for Auto-Recovery (Recommended)

```bash
# Circuit breaker will automatically try HALF_OPEN after recovery_timeout
# Default: 30 seconds

# Monitor state transition
watch -n 5 'curl -s http://localhost:8000/metrics | grep pms_circuit_breaker_state'

# Expected transition: OPEN (1) → HALF_OPEN (2) → CLOSED (0)
# If successful requests in HALF_OPEN, will close
# If failures continue, will reopen
```

### Option 2: Manual Reset (Use with Caution)

```bash
# Only if confirmed PMS is healthy and ready
# Force circuit breaker to CLOSED state
curl -X POST http://localhost:8000/admin/circuit-breaker/pms/reset

# Monitor for stability
watch -n 5 'curl -s http://localhost:8000/metrics | grep pms_circuit_breaker_state'
```

### Option 3: Adjust Circuit Breaker Settings

```python
# app/services/pms_adapter.py
self.circuit_breaker = CircuitBreaker(
    failure_threshold=10,      # Increase tolerance (was 5)
    recovery_timeout=60,       # Longer recovery time (was 30)
    success_threshold=3,       # More confirmations (was 2)
    timeout=20.0              # Longer timeout (was 10)
)
```

```bash
# Deploy configuration change
git commit -am "Adjust PMS circuit breaker thresholds"
make deploy-staging
# Test in staging first
make deploy-production
```

### Option 4: Switch to Fallback Mode

```bash
# Enable mock PMS adapter temporarily
docker exec agente-api sh -c 'echo "PMS_TYPE=mock" >> /app/.env'
docker-compose restart agente-api

# Or use cached responses
curl -X POST http://localhost:8000/admin/feature-flags \
  -H "Content-Type: application/json" \
  -d '{"key": "pms.cache_fallback", "enabled": true}'
```

---

## Validation

### 1. Monitor Circuit Breaker State

```bash
# Check state (should be 0 = CLOSED)
curl http://localhost:8000/metrics | grep pms_circuit_breaker_state

# Check success rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(pms_circuit_breaker_calls_total{result="success"}[5m]) /
  rate(pms_circuit_breaker_calls_total[5m])
'
```

### 2. Test PMS Operations

```bash
# Test availability check
curl -X POST http://localhost:8000/api/v1/pms/availability \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in": "2024-11-01",
    "check_out": "2024-11-03"
  }'

# Check for circuit breaker errors
docker logs agente-api | grep "circuit.*breaker" | tail -5
```

### 3. Load Test

```bash
# Run sustained load to verify stability
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/api/v1/pms/availability \
    -H "Content-Type: application/json" \
    -d '{"hotel_id": 1, "check_in": "2024-11-01", "check_out": "2024-11-03"}' &
done
wait

# Check circuit breaker didn't trip
curl http://localhost:8000/metrics | grep pms_circuit_breaker_state
```

---

## Communication Template

**Initial Alert**:
```
⚠️ INCIDENT: PMS Circuit Breaker Open
Severity: MEDIUM
Status: MONITORING
Impact: PMS operations using cached data
Root Cause: [External API failures/Timeouts/etc.]
Action: Monitoring auto-recovery (30-60s)
```

**Update**:
```
📊 CIRCUIT BREAKER UPDATE
State: [OPEN/HALF_OPEN/CLOSED]
PMS Health: [Degraded/Recovering/Healthy]
Actions: [Waiting for recovery/Manual reset/etc.]
Impact: [Cached data being served/Operations resumed]
```

**Resolution**:
```
✅ RESOLVED: Circuit Breaker Closed
Duration: XX minutes
State Transitions: OPEN → HALF_OPEN → CLOSED
Root Cause: [Detailed explanation]
Fix: [Auto-recovery/Manual intervention/Config change]
Validation: PMS operations tested successfully
```

---

## Post-Incident

### 1. Analyze Circuit Breaker Metrics

```bash
# Generate circuit breaker report
curl 'http://localhost:9090/api/v1/query_range?query=pms_circuit_breaker_state' \
  > circuit_breaker_report.json

# Check trip frequency
docker logs agente-api | grep "Circuit breaker opened" | wc -l

# Identify failure patterns
docker logs agente-api | grep "PMS.*error" | awk '{print $NF}' | sort | uniq -c
```

### 2. Add Circuit Breaker Dashboard

```json
// Grafana dashboard
{
  "title": "Circuit Breaker Status",
  "panels": [
    {
      "title": "Circuit Breaker State",
      "targets": [
        {
          "expr": "pms_circuit_breaker_state",
          "legendFormat": "State (0=closed, 1=open, 2=half-open)"
        }
      ]
    },
    {
      "title": "Circuit Breaker Calls",
      "targets": [
        {
          "expr": "rate(pms_circuit_breaker_calls_total[5m])",
          "legendFormat": "{{result}}"
        }
      ]
    }
  ]
}
```

### 3. Implement Alerting

```yaml
# docker/prometheus/alerts.yml
- alert: CircuitBreakerOpen
  expr: pms_circuit_breaker_state == 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "PMS circuit breaker has been open for 5 minutes"
    
- alert: CircuitBreakerFlapping
  expr: changes(pms_circuit_breaker_state[15m]) > 5
  labels:
    severity: warning
  annotations:
    summary: "Circuit breaker state changing frequently"
```

### 4. Action Items

- [ ] Review circuit breaker thresholds
- [ ] Analyze PMS failure patterns
- [ ] Implement better fallback strategy
- [ ] Add circuit breaker metrics to dashboard
- [ ] Test circuit breaker behavior under load
- [ ] Document circuit breaker recovery procedures
- [ ] Set up automated notifications

---

## Prevention

- **Monitoring**: Alert when circuit opens for > 5min
- **Thresholds**: Review and tune based on PMS SLA
- **Fallback**: Implement robust caching strategy
- **Testing**: Simulate circuit breaker scenarios monthly
- **Documentation**: Maintain PMS dependency map

## Circuit Breaker Best Practices

1. **Don't manually reset prematurely** - Let auto-recovery work
2. **Monitor state transitions** - Frequent flapping indicates issues
3. **Have fallback strategy** - Cache, mock data, or alternative service
4. **Tune thresholds** - Based on external service characteristics
5. **Test regularly** - Chaos engineering for circuit breaker paths

## Circuit Breaker Metrics

| Metric | Description | Alert On |
|--------|-------------|----------|
| `pms_circuit_breaker_state` | Current state (0/1/2) | = 1 for > 5min |
| `pms_circuit_breaker_calls_total` | Total calls by result | High failure rate |
| `pms_circuit_breaker_state_changes_total` | State transitions | > 5 in 15min |

## Related Runbooks

- [05-pms-integration-failure.md](./05-pms-integration-failure.md)
- [08-high-error-rate.md](./08-high-error-rate.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: SRE Team, Reliability Team
