# Runbook: PMS Integration Failure

**Severity**: HIGH  
**SLA**: 30 minutes to mitigation  
**On-Call**: Backend Team + Integrations Team

---

## Symptoms

- PMS API calls failing
- Circuit breaker in OPEN state
- Reservation operations failing
- Metric: `pms_circuit_breaker_state = 1` (OPEN)

## Detection

```promql
# Circuit breaker open
pms_circuit_breaker_state{service="pms"} == 1

# High PMS error rate
rate(pms_api_calls_total{status="error"}[5m]) > 0.1
```

## Impact Assessment

- **User Impact**: Cannot check availability or make reservations
- **Business Impact**: Lost bookings, revenue impact
- **System Impact**: Degraded service, manual intervention needed

---

## Immediate Actions (0-10 minutes)

### 1. Verify PMS Status

```bash
# Check circuit breaker state
curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state

# Check recent PMS errors
docker logs agente-api --since 10m | grep "PMS"

# Manual PMS API test
curl -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/availability
```

### 2. Check PMS Service

```bash
# If self-hosted QloApps
docker ps | grep qloapps
docker logs qloapps --tail 50

# Check MySQL database
docker exec mysql-qloapps mysqladmin ping -p

# Test database connectivity
docker exec mysql-qloapps mysql -u qloapps_user -p -e "SHOW DATABASES;"
```

### 3. Quick Mitigation - Reset Circuit Breaker

```bash
# Force circuit breaker reset (if PMS is actually up)
curl -X POST http://localhost:8000/admin/circuit-breaker/reset

# Check state
curl http://localhost:8000/metrics | grep pms_circuit_breaker_state
```

---

## Investigation (10-30 minutes)

### Check Common Causes

#### A. PMS Service Down

```bash
# Check QloApps container
docker-compose ps qloapps

# Check QloApps logs
docker logs qloapps --tail 100 | grep -i error

# Check MySQL connectivity
docker exec qloapps nc -zv mysql-qloapps 3306
```

#### B. API Authentication Issues

```bash
# Test API key
curl -v -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/hotels

# Check for key expiration
grep "401\|403" logs/agente-api.log | tail -20

# Verify environment variable
docker exec agente-api env | grep PMS_API_KEY
```

#### C. Rate Limiting

```bash
# Check for 429 errors
docker logs agente-api | grep "429" | wc -l

# Check PMS rate limit headers
curl -I -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/availability | grep -i "rate-limit"

# Review request rate
curl 'http://localhost:9090/api/v1/query?query=rate(pms_api_calls_total[5m])'
```

#### D. Network Issues

```bash
# Test DNS resolution
docker exec agente-api nslookup qloapps.example.com

# Test connectivity
docker exec agente-api curl -v https://qloapps.example.com

# Check for firewall rules
sudo iptables -L | grep 443
```

#### E. Timeout Issues

```bash
# Check PMS API latency
curl 'http://localhost:9090/api/v1/query?query=pms_api_latency_seconds_sum'

# Check for timeout errors
docker logs agente-api | grep -i timeout | tail -20

# Test with longer timeout
curl --max-time 30 -H "Authorization: Bearer $PMS_API_KEY" \
  https://qloapps.example.com/api/availability
```

---

## Resolution Steps

### Option 1: Switch to Mock PMS (Emergency Fallback)

```bash
# Enable mock PMS adapter
docker exec agente-api sh -c 'echo "PMS_TYPE=mock" >> /app/.env'

# Restart service
docker-compose restart agente-api

# Verify mock adapter active
docker logs agente-api | grep "PMS adapter type: mock"
```

### Option 2: Restart PMS Service

```bash
# Restart QloApps
docker-compose restart qloapps

# Wait for health check
sleep 30

# Verify PMS is up
curl https://qloapps.example.com/health

# Reset circuit breaker
curl -X POST http://localhost:8000/admin/circuit-breaker/reset
```

### Option 3: Update API Credentials

```bash
# Update API key in .env
vi agente-hotel-api/.env
# PMS_API_KEY=new_key_here

# Restart service to reload config
docker-compose restart agente-api

# Test connection
curl http://localhost:8000/health/ready | jq .pms
```

### Option 4: Adjust Circuit Breaker Settings

```python
# app/core/settings.py
class Settings(BaseSettings):
    pms_circuit_breaker_failure_threshold: int = 10  # Increase from 5
    pms_circuit_breaker_recovery_timeout: int = 60   # Increase from 30
    pms_timeout: int = 30                            # Increase from 10

# Deploy configuration change
git commit -am "Adjust PMS circuit breaker settings"
make deploy-staging
```

---

## Validation

### 1. Test PMS Operations

```bash
# Test availability check
curl -X POST http://localhost:8000/api/v1/pms/availability \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in": "2024-11-01",
    "check_out": "2024-11-03",
    "room_type": 1
  }'

# Test reservation
curl -X POST http://localhost:8000/api/v1/pms/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "guest_name": "Test User",
    "email": "test@example.com",
    "check_in": "2024-11-01",
    "check_out": "2024-11-03",
    "room_type": 1
  }'
```

### 2. Check Metrics

```bash
# Circuit breaker state (should be 0 = CLOSED)
curl 'http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state'

# PMS success rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(pms_api_calls_total{status="success"}[5m]) /
  rate(pms_api_calls_total[5m])
'

# Average latency
curl 'http://localhost:9090/api/v1/query?query=
  rate(pms_api_latency_seconds_sum[5m]) /
  rate(pms_api_latency_seconds_count[5m])
'
```

### 3. End-to-End Test

```bash
# Run PMS integration tests
make test-pms-integration

# Check results
cat tests/integration/pms_test_results.txt
```

---

## Communication Template

**Initial Alert**:
```
🚨 INCIDENT: PMS Integration Failure
Severity: HIGH
Status: INVESTIGATING
Impact: Reservation operations unavailable
Root Cause: Investigating (Circuit breaker open)
Workaround: Mock adapter enabled for basic operations
ETA: 30 minutes to resolution
```

**Update**:
```
📊 PMS INTEGRATION UPDATE
Status: [INVESTIGATING/IDENTIFIED/MONITORING]
Root Cause: [PMS down/Auth issue/Rate limit/etc.]
Actions: [What we're doing]
Progress: [Circuit breaker state, error rate]
```

**Resolution**:
```
✅ RESOLVED: PMS Integration Restored
Duration: XX minutes
Root Cause: [Detailed explanation]
Fix: [PMS restarted/Credentials updated/etc.]
Validation: All PMS operations tested successfully
Monitoring: Extended monitoring for 1 hour
```

---

## Post-Incident

### 1. Review PMS Logs

```bash
# Extract PMS errors from incident window
docker logs qloapps --since "2024-10-15T10:00:00" --until "2024-10-15T11:00:00" \
  > /tmp/pms_incident_logs.txt

# Analyze error patterns
grep -i error /tmp/pms_incident_logs.txt | sort | uniq -c | sort -nr
```

### 2. Improve Monitoring

```yaml
# docker/prometheus/alerts.yml
- alert: PMSCircuitBreakerOpen
  expr: pms_circuit_breaker_state == 1
  for: 5m
  annotations:
    summary: "PMS circuit breaker is open"
    
- alert: PMSHighErrorRate
  expr: rate(pms_api_calls_total{status="error"}[5m]) > 0.1
  for: 2m
  annotations:
    summary: "PMS error rate > 10%"
```

### 3. Action Items

- [ ] Review PMS SLA and availability
- [ ] Implement PMS health check endpoint
- [ ] Add automated failover to mock adapter
- [ ] Improve circuit breaker logging
- [ ] Set up PMS-specific alert channel
- [ ] Document PMS API rate limits
- [ ] Create PMS troubleshooting guide

---

## Prevention

- **Monitoring**: PMS health check every 60s
- **Alerting**: Alert on circuit breaker open > 2min
- **Failover**: Automatic switch to mock adapter
- **Testing**: Weekly PMS integration tests
- **Documentation**: Maintain PMS API changelog

## PMS Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Availability | > 99.9% | < 99.5% | < 99% |
| Response Time | < 500ms | > 1s | > 3s |
| Error Rate | < 0.1% | > 1% | > 5% |
| Circuit Breaker | CLOSED | HALF_OPEN | OPEN |

## Related Runbooks

- [02-high-api-latency.md](./02-high-api-latency.md)
- [08-high-error-rate.md](./08-high-error-rate.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Integrations Team  
**Reviewers**: Backend Team, QloApps Team
