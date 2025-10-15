# Runbook: High API Latency

**Severity**: HIGH  
**SLA**: 30 minutes to mitigation  
**On-Call**: Backend Team + Infrastructure Team

---

## Symptoms

- Slow API responses (> 3s P95)
- Timeout errors in client applications
- User complaints about slow system
- Metric: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3`

## Detection

```promql
# P95 latency alert
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{job="agente-api"}[5m])
) > 3
```

## Impact Assessment

- **User Impact**: Degraded user experience, potential timeouts
- **Business Impact**: Reduced conversion rate, customer dissatisfaction
- **System Impact**: Potential cascade failures

---

## Immediate Actions (0-5 minutes)

### 1. Identify Slow Endpoints

```bash
# Check Grafana dashboard
open http://localhost:3000/d/api-performance

# Query top slow endpoints
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=topk(10, 
    histogram_quantile(0.95, 
      rate(http_request_duration_seconds_bucket[5m])
    ) by (endpoint)
  )'
```

### 2. Check System Resources

```bash
# CPU usage
docker stats --no-stream agente-api

# Memory usage
docker exec agente-api ps aux --sort=-%mem | head -10

# Check for memory leaks
docker exec agente-api cat /proc/meminfo
```

### 3. Quick Mitigation - Scale Up

```bash
# Increase replicas (if using compose with scale)
docker-compose up -d --scale agente-api=3

# Or restart to clear potential memory issues
docker-compose restart agente-api
```

---

## Investigation (5-30 minutes)

### Check Common Causes

#### A. Database Slow Queries

```bash
# Check slow query log
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT query, calls, mean_exec_time, max_exec_time 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;
"

# Check active queries
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
  FROM pg_stat_activity 
  WHERE state = 'active' 
  ORDER BY duration DESC;
"
```

#### B. External API Timeouts

```bash
# Check PMS adapter metrics
curl 'http://localhost:9090/api/v1/query?query=pms_api_latency_seconds_sum'

# Check circuit breaker state
curl 'http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state'

# Check WhatsApp API latency
curl 'http://localhost:9090/api/v1/query?query=whatsapp_api_latency_seconds'
```

#### C. Cache Performance

```bash
# Check Redis hit rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(redis_cache_hits_total[5m]) / 
  (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m]))
'

# Check Redis latency
docker exec redis-agente redis-cli --latency

# Check cache size
docker exec redis-agente redis-cli info memory
```

#### D. Thread/Connection Pool Saturation

```bash
# Check connection pool metrics
curl http://localhost:8000/metrics | grep "db_pool"

# Check async tasks
docker logs agente-api --tail=100 | grep "Task"
```

---

## Resolution Steps

### Option 1: Optimize Slow Endpoint (Immediate)

```bash
# Enable query caching for slow endpoint
# Edit app/services/pms_adapter.py
# Increase cache TTL for stable data

# Deploy hotfix
git checkout -b hotfix/latency-optimization
# Make changes
git commit -am "Optimize slow PMS queries with caching"
git push origin hotfix/latency-optimization
make deploy-staging
```

### Option 2: Circuit Breaker Adjustment

```bash
# If external API is slow, adjust circuit breaker
# Edit app/core/settings.py
# Reduce timeout or increase failure threshold temporarily

# Restart service
docker-compose restart agente-api
```

### Option 3: Database Query Optimization

```sql
-- Add missing index
CREATE INDEX CONCURRENTLY idx_sessions_tenant_id ON sessions(tenant_id);

-- Update statistics
ANALYZE sessions;

-- Vacuum if needed
VACUUM ANALYZE sessions;
```

### Option 4: Scale Horizontally

```bash
# Add more replicas (production)
kubectl scale deployment agente-api --replicas=5

# Or with Docker Compose
docker-compose up -d --scale agente-api=3
```

---

## Validation

### 1. Check Latency Metrics

```bash
# P50 latency
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.50, 
    rate(http_request_duration_seconds_bucket[5m])
  )'

# P95 latency
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, 
    rate(http_request_duration_seconds_bucket[5m])
  )'

# P99 latency
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.99, 
    rate(http_request_duration_seconds_bucket[5m])
  )'
```

### 2. Run Performance Tests

```bash
# Run load test
make test-load

# Check results
cat tests/load/results.txt
```

### 3. Monitor for 15 Minutes

```bash
# Watch metrics in real-time
watch -n 5 'curl -s http://localhost:8000/metrics | grep http_request_duration'
```

---

## Communication Template

**Initial Alert**:
```
⚠️ INCIDENT: High API Latency Detected
Severity: HIGH
Status: INVESTIGATING
Impact: Slow response times (P95: Xs)
Affected: All API endpoints
ETA: Investigating, update in 15 minutes
```

**Update Template**:
```
📊 LATENCY INCIDENT UPDATE
Current P95: Xs (target: <3s)
Root Cause: [Database queries/External API/Memory/etc.]
Actions: [What we're doing]
Progress: [Latency improvement observed]
```

**Resolution**:
```
✅ RESOLVED: API Latency Normalized
Duration: XX minutes
Final P95: Xs (target: <3s)
Root Cause: [Brief description]
Fix Applied: [What we changed]
```

---

## Post-Incident

### 1. Performance Analysis

```bash
# Generate performance report
python scripts/performance-analysis.py --since="2 hours ago"

# Check for patterns
grep "slow_query" logs/*.log | sort | uniq -c
```

### 2. Action Items

- [ ] Review and optimize identified slow queries
- [ ] Add database indexes where needed
- [ ] Tune cache TTL values
- [ ] Review external API timeout settings
- [ ] Consider implementing request queueing
- [ ] Update monitoring alerts

### 3. Preventive Measures

- Enable slow query logging permanently
- Set up automated performance regression tests
- Create capacity planning dashboard
- Schedule quarterly performance review

---

## Prevention

- **Monitoring**: Alert on P95 > 2s (warning), > 3s (critical)
- **Testing**: Run weekly load tests in staging
- **Optimization**: Monthly query performance review
- **Capacity**: Auto-scaling rules for high load
- **Caching**: Review cache strategy quarterly

## Performance Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| P50 | < 200ms | > 500ms | > 1s |
| P95 | < 1s | > 2s | > 3s |
| P99 | < 2s | > 3s | > 5s |
| Error Rate | < 0.1% | > 1% | > 5% |

## Related Runbooks

- [01-database-down.md](./01-database-down.md)
- [03-memory-leak.md](./03-memory-leak.md)
- [05-pms-integration-failure.md](./05-pms-integration-failure.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: Performance Team, SRE Team
