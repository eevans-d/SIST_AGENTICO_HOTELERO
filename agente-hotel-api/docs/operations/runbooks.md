# Runbooks & Incident Response

## Quick Incident Matrix

| Incident | Alert | Root Cause | Mitigation | Recovery |
|----------|-------|-----------|-----------|----------|
| PMS Down | PMSCircuitBreakerOpen | PMS service unavailable | Workfow rolls back to mock mode or manual responses | Verify PMS URL, auth, and network; redeploy |
| DB Down | DatabaseDown | Postgres crashed or network issue | App returns 503; readiness fails | Restore from backup or contact DB provider |
| Redis Down | RedisDown | Redis OOM or crashed | Cache disabled; rate limiting in-memory | Check Redis memory; restart; scale up |
| High Latency | HighOrchestrationLatency | NLP slowness or PMS timeout | Rate limiting kicks in; queue builds | Analyze bottleneck; optimize; scale horizontally |
| High Errors | HighErrorRate | Bad data, timeouts, or crashes | Monitor logs; error rate dashboard | Identify cause; patch & redeploy |
| High Traffic | RateLimitSpike | Spike in requests or bot activity | Rate limit returns 429; users experience delays | Scale machines; investigate traffic source |

---

## Runbook: PMS Integration Down

**Alert**: `PMSCircuitBreakerOpen`  
**Severity**: 🔴 CRITICAL  
**Stakeholders**: Backend, PMS Team  
**RTO**: 5–15 min  

### Symptoms

- `/health/ready` returns 503 (pms check fails)
- Customers report "Cannot check availability" errors
- `pms_circuit_breaker_state` = 1 in Prometheus

### Investigation (1–2 min)

1. **Check PMS connectivity**:
   ```bash
   curl -v https://qloapps.yourdomain.com/api/health
   # or check from app logs:
   # docker logs agente-api | grep -i pms | tail -20
   ```

2. **Check logs**:
   ```bash
   (Comando de logs) | grep -i pms
   ```

3. **Check DNS & Network**:
   ```bash
   nslookup qloapps.yourdomain.com
   nc -zv qloapps.yourdomain.com 443
   ```

### Mitigation (2–5 min)

**Option A: Rollback to Mock Mode (temporary)**

```bash
# Set PMS_TYPE=mock to disable PMS checks temporarily
(Comando para actualizar variable de entorno PMS_TYPE)

# Notify customers: availability checks unavailable; using mock data
# Dashboard shows "degraded mode"
```

**Option B: Point to Backup PMS Instance**

```bash
# If you have a backup PMS:
(Comando para actualizar variable de entorno PMS_BASE_URL)
```

### Recovery (5–15 min)

1. **Restore PMS Service**
   - Contact PMS admin; verify startup logs
   - Check DB connectivity for PMS
   - Verify API keys and credentials

2. **Redeploy with PMS_TYPE=qloapps**
   ```bash
   (Comando para actualizar variable de entorno PMS_TYPE)
   (Comando de deploy)
   ```

3. **Verify Circuit Breaker Recovers**
   ```bash
   # Wait for half-open recovery (~30s)
   # Check: pms_circuit_breaker_state should return to 0 (CLOSED)
   curl localhost:9090/api/v1/query?query=pms_circuit_breaker_state
   ```

### Post-Incident

- [ ] RCA: Why did PMS go down?
- [ ] Prevention: Add PMS monitoring + health endpoint
- [ ] Alerting: Send P1 alert to PMS team when circuit breaks

---

## Runbook: Database Connection Failed

**Alert**: `DatabaseDown`  
**Severity**: 🔴 CRITICAL  
**Stakeholders**: Backend, Database Team, Ops  
**RTO**: 10–30 min  

### Symptoms

- `/health/ready` returns 503 (database check fails)
- App logs: `sqlalchemy.exc.OperationalError: connection refused`
- Sessions cannot be created; guests see "Service unavailable"

### Investigation (1–2 min)

1. **Check if Postgres is running** (local Docker):
   ```bash
   docker ps | grep postgres
   docker logs agente-postgres | tail -20
   ```

2. **Test connection**:
   ```bash
   psql -h postgres -U agente_user -d agente_hotel -c "SELECT 1"
   ```

3. **Check DB status**:
   ```bash
   (Comando de estado de DB)
   # or check from dashboard
   ```

### Mitigation (2–5 min)

**Option A: Restart Postgres**

```bash
# Local Docker:
docker-compose restart postgres

# Remote DB:
(Comando de conexión a DB)
```

**Option B: Failover to Backup DB** (if available)

```bash
# Update DATABASE_URL to point to backup:
(Comando para actualizar variable de entorno DATABASE_URL)
(Comando de deploy)
```

### Recovery (5–30 min)

1. **Restore Database from Backup**
   ```bash
   ./agente-hotel-api/scripts/backup-restore.sh restore backups/agente-hotel-api_LATEST.sql.gz
   ```

2. **Verify Data Integrity**
   ```bash
   psql -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM sessions;"
   ```

3. **Redeploy App**
   ```bash
   (Comando de deploy)
   ```

4. **Monitor readiness**
   ```bash
   curl <APP_URL>/health/ready
   ```

### Post-Incident

- [ ] Analyze Postgres logs for crash cause
- [ ] Check DB disk space and memory
- [ ] Review connection pool settings
- [ ] Enable automated backups if not already active

---

## Runbook: High Request Latency

**Alert**: `HighOrchestrationLatency` (P95 > 3s)  
**Severity**: 🟡 WARNING  
**Stakeholders**: Backend, Performance Team  
**RTO**: 5–10 min (performance improvement)  

### Symptoms

- Dashboard shows P95 latency trending up (>3s)
- Customers report slow response times
- Orchestrator processing takes longer than usual

### Investigation (2–5 min)

1. **Check NLP Engine Performance**
   ```bash
   # Is NLP slow? Check Whisper STT or intent detection latency
   # Look for: nlp_engine_latency_seconds in Prometheus
   ```

2. **Check PMS API Latency**
   ```bash
   # Is PMS slow?
   # Metric: pms_api_latency_seconds
   ```

3. **Check Database Queries**
   ```bash
   # Enable slow query log on Postgres:
   psql -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"  # 1s threshold
   docker-compose restart postgres
   ```

### Mitigation (5–10 min)

**Option A: Scale Up Machines**

```bash
# Increase VM size temporarily
(Comando de escalado vertical)
```

**Option B: Enable Caching Aggressively**

```bash
# Increase PMS cache TTL
# In app/core/settings.py, update PMS_CACHE_TTL and redeploy
(Comando para actualizar variable de entorno PMS_CACHE_TTL_SECONDS)
```

**Option C: Disable NLP for Non-Critical Paths**

```bash
# Temporarily disable audio processing
(Comando para actualizar variable de entorno AUDIO_ENABLED)
```

### Recovery (5–15 min)

1. **Profile Slow Endpoints**
   ```bash
   # Use Jaeger traces to identify bottleneck
   # http://localhost:16686/search
   ```

2. **Optimize Identified Bottleneck**
   - NLP: Cache embeddings; use smaller model (tiny vs base)
   - PMS: Increase cache TTL; batch requests
   - DB: Add index; optimize query

3. **Monitor Latency Drop**
   ```bash
   # Watch P95 trend back down below 3s
   ```

### Post-Incident

- [ ] Document performance improvements made
- [ ] Add performance regression test to CI
- [ ] Review auto-scaling thresholds

---

## Runbook: High Traffic / Rate Limiting

**Alert**: `RateLimitSpike` (>10 req/s)  
**Severity**: 🟡 WARNING  
**Stakeholders**: Backend, Traffic Team  
**RTO**: 2–5 min  

### Symptoms

- `slowapi_limiter_hits_total` increasing rapidly
- Customers see 429 (Too Many Requests) errors
- One or few IPs causing spike

### Investigation (1–2 min)

1. **Check Request Source**
   ```bash
   # From nginx/app logs: identify source IP
   docker logs agente-api | grep -i "429" | tail -10
   ```

2. **Is It Legitimate Traffic?**
   - Batch imports? → Expected
   - Bot scanning? → Block IP
   - New feature spike? → Expected

### Mitigation (2–5 min)

**Option A: Increase Rate Limit**

```bash
# Increase Slowapi limit from 120/min to 300/min
# In app/core/settings.py or via env var
(Comando para actualizar variable de entorno RATE_LIMIT_PER_MINUTE)
```

**Option B: Scale Machines Horizontally**

```bash
# Add more machines to distribute load
(Comando de escalado horizontal)
```

**Option C: Block Suspicious IP**

```bash
# Add nginx rule to block IP
# In docker/nginx/nginx.conf:
# deny 192.168.1.100;
docker-compose restart nginx
```

### Recovery (5–10 min)

1. **Monitor Rate Limit Hits**
   - Should drop after scaling/limits adjusted

2. **Investigate Traffic Source**
   - Legitimate growth? → Permanent scaling
   - Anomaly? → Block or investigate

3. **Update Capacity Planning**
   - Based on spike size, adjust autoscaling min/max

### Post-Incident

- [ ] Document traffic pattern and causes
- [ ] Adjust rate limiting strategy if needed
- [ ] Set up DDoS mitigation if bot activity detected

---

## Game Day Scenario

**Objective**: Test incident response procedures  
**Duration**: 2 hours  
**Participants**: Backend team + on-call rotation  

### Scenario 1: PMS Goes Down (30 min)

1. **Trigger**: Shut down PMS mock server or firewall rule
2. **Discover**: Alerts fire; team notices readiness failing
3. **Respond**: Follow PMS Runbook mitigation steps
4. **Recover**: Restore PMS and verify circuit breaker resets
5. **Debrief**: What worked? What to improve?

### Scenario 2: Database Unavailable (30 min)

1. **Trigger**: Simulate DB network partition
2. **Discover**: Database health check fails
3. **Respond**: Attempt restore from backup
4. **Recover**: Verify data consistency and app functionality
5. **Debrief**: Backup/restore procedure validity?

### Scenario 3: High Latency Spike (30 min)

1. **Trigger**: Introduce artificial delay in NLP engine
2. **Discover**: Latency dashboard shows P95 > 3s
3. **Respond**: Identify bottleneck; scale or disable feature
4. **Recover**: Monitor latency drop; restore normal operations
5. **Debrief**: Scaling response adequate?

---

## Escalation Matrix

| Issue | First Response | Escalate If | Next Level |
|-------|---|---|---|
| PMS Down | On-call Backend | >15 min | PMS Team Lead |
| DB Down | On-call Backend | >10 min | Ops/DB Lead |
| High Latency | Perf Team | Unresolved after 20 min | Architecture Review |
| High Traffic | On-call Backend | Sustained >1h | Capacity Planning |
| Security Alert | On-call Ops | Confirmed breach | CISO + Legal |

---

## Resources

- [Prometheus Alerting](https://prometheus.io/docs/alerting/)
- [Grafana On-Call](https://grafana.com/products/oncall/)
- [PagerDuty Integration](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-loki-loki-rule/)
- [PostgreSQL Recovery](https://www.postgresql.org/docs/current/backup-restore.html)
