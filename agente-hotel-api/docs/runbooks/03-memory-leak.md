# Runbook: Memory Leak Detected

**Severity**: HIGH  
**SLA**: 1 hour to resolution  
**On-Call**: Backend Team + SRE Team

---

## Symptoms

- Continuous memory growth over time
- Container OOM (Out of Memory) kills
- Degrading performance over time
- Metric: `process_resident_memory_bytes > 2GB`

## Detection

```promql
# Memory usage alert
process_resident_memory_bytes{job="agente-api"} / 1024 / 1024 / 1024 > 2
```

## Impact Assessment

- **Service Impact**: Potential crashes, degraded performance
- **User Impact**: Slow responses, intermittent failures
- **System Impact**: Host resource exhaustion

---

## Immediate Actions (0-10 minutes)

### 1. Confirm Memory Leak

```bash
# Check current memory usage
docker stats agente-api --no-stream

# Check memory trend (last hour)
curl -G 'http://localhost:9090/api/v1/query_range' \
  --data-urlencode 'query=process_resident_memory_bytes{job="agente-api"}' \
  --data-urlencode 'start='$(date -d '1 hour ago' +%s) \
  --data-urlencode 'end='$(date +%s) \
  --data-urlencode 'step=60'
```

### 2. Take Memory Snapshot

```bash
# Get heap dump (Python)
docker exec agente-api python -m tracemalloc

# Get process info
docker exec agente-api ps aux | head -5

# Check for zombie processes
docker exec agente-api ps aux | grep defunct
```

### 3. Quick Mitigation - Restart Service

```bash
# Graceful restart
docker-compose restart agente-api

# Monitor recovery
watch -n 5 docker stats agente-api --no-stream
```

---

## Investigation (10-60 minutes)

### Check Common Causes

#### A. Connection Leaks

```bash
# Check database connections
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT count(*), state 
  FROM pg_stat_activity 
  GROUP BY state;
"

# Check Redis connections
docker exec redis-agente redis-cli info clients

# Check HTTP client connections
docker logs agente-api | grep "connection" | tail -20
```

#### B. Cache Growth

```bash
# Check Redis memory
docker exec redis-agente redis-cli info memory

# Check largest keys
docker exec redis-agente redis-cli --bigkeys

# Check in-memory caches
docker exec agente-api python -c "
import sys
sys.path.append('/app')
from app.services.feature_flag_service import get_feature_flag_service
# Check cache size
"
```

#### C. Circular References

```bash
# Enable Python garbage collector debug
docker exec agente-api python -c "
import gc
gc.set_debug(gc.DEBUG_LEAK)
print(len(gc.get_objects()))
"

# Check for unclosed resources
docker logs agente-api | grep "ResourceWarning"
```

#### D. Large Object Accumulation

```bash
# Profile memory usage
docker exec agente-api pip install memory_profiler
docker exec agente-api python -m memory_profiler app/main.py

# Check for large variables
docker exec agente-api python -c "
import objgraph
objgraph.show_most_common_types(limit=20)
"
```

---

## Resolution Steps

### Option 1: Fix Connection Leaks

```python
# Ensure async context managers
async with AsyncSessionFactory() as session:
    # Database operations
    pass

# Ensure HTTP client cleanup
async with httpx.AsyncClient() as client:
    # HTTP operations
    pass
```

### Option 2: Implement Memory Limits

```yaml
# docker-compose.yml
services:
  agente-api:
    mem_limit: 2g
    mem_reservation: 1g
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Option 3: Add Cache Eviction

```python
# app/services/feature_flag_service.py
import cachetools

# Use TTL cache instead of unbounded cache
cache = cachetools.TTLCache(maxsize=1000, ttl=300)
```

### Option 4: Enable Garbage Collection Tuning

```python
# app/main.py
import gc

# Tune garbage collection
gc.set_threshold(700, 10, 10)  # More aggressive collection

# Periodic forced collection
async def gc_task():
    while True:
        await asyncio.sleep(300)
        gc.collect()
```

---

## Validation

### 1. Monitor Memory Over Time

```bash
# Watch memory for 30 minutes
watch -n 60 'docker stats agente-api --no-stream | tail -1'

# Check memory trend
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(process_resident_memory_bytes[30m])'
```

### 2. Load Test

```bash
# Run sustained load test
make test-load-sustained DURATION=1800  # 30 minutes

# Monitor memory during test
watch -n 10 'docker stats agente-api --no-stream'
```

### 3. Leak Detection Test

```bash
# Run memory leak detection
pytest tests/memory/test_memory_leak.py --memcheck

# Check results
cat tests/memory/leak_report.txt
```

---

## Communication Template

**Initial Alert**:
```
⚠️ INCIDENT: Memory Leak Detected
Severity: HIGH
Status: INVESTIGATING
Impact: Memory usage at XGB (limit: 2GB)
Risk: Potential service crashes
Action: Service restarted, investigating root cause
```

**Update**:
```
📊 MEMORY LEAK UPDATE
Current Usage: XGB (was YGB at restart)
Growth Rate: X MB/hour
Root Cause: [Connection leak/Cache growth/etc.]
Fix: [Code change/Configuration/etc.]
Testing: [Load test in progress]
```

**Resolution**:
```
✅ RESOLVED: Memory Leak Fixed
Root Cause: [Detailed explanation]
Fix Applied: [Code changes deployed]
Validation: Load tested for 2 hours, stable at XMB
Monitoring: Extended monitoring for 24 hours
```

---

## Post-Incident

### 1. Code Review

```bash
# Search for potential leaks
grep -r "global " app/ | grep -v ".pyc"
grep -r "class.*:" app/ | grep -v "def "

# Check for missing context managers
grep -r "AsyncClient\(\)" app/ | grep -v "async with"
grep -r "AsyncSessionFactory\(\)" app/ | grep -v "async with"
```

### 2. Add Memory Monitoring

```python
# app/routers/metrics.py
from prometheus_client import Gauge

memory_usage_gauge = Gauge(
    'python_memory_usage_bytes',
    'Python memory usage by type',
    ['type']
)

@app.get("/metrics/memory")
async def memory_metrics():
    import tracemalloc
    tracemalloc.start()
    # ... collect stats
```

### 3. Action Items

- [ ] Add memory profiling to CI/CD
- [ ] Implement automated memory leak tests
- [ ] Review all async resource usage
- [ ] Add cache size limits
- [ ] Set up memory alerts (warning at 1.5GB)
- [ ] Schedule monthly memory audits

---

## Prevention

- **Limits**: Set container memory limits
- **Monitoring**: Alert on memory growth rate
- **Testing**: Include memory leak tests in CI/CD
- **Code Review**: Check for resource cleanup
- **Profiling**: Run memory profiler monthly

## Memory Targets

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Base Memory | 200-400MB | 800MB | 1.5GB |
| Peak Memory | < 1GB | 1.5GB | 2GB |
| Growth Rate | < 10MB/h | 50MB/h | 100MB/h |

## Related Runbooks

- [02-high-api-latency.md](./02-high-api-latency.md)
- [07-redis-connection-issues.md](./07-redis-connection-issues.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: SRE Team, Performance Team
