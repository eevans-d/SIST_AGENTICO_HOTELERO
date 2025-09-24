# Runbook: Circuit Breaker Open - PMS Service

## 🚨 Alert: PMS Circuit Breaker Open

### Quick Reference
- **Alert**: `pms_circuit_breaker_state == 2`
- **Severity**: P1 (Major service impairment)
- **Impact**: Guest reservations and check-ins unavailable
- **Response Time**: 15 minutes

## Immediate Actions (First 5 minutes)

### 1. Acknowledge Alert
```bash
# Acknowledge in monitoring system
curl -X POST "http://alertmanager:9093/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"labels":{"alertname":"PMSCircuitBreakerOpen","acknowledged":"true"}}]}'
```

### 2. Check System Status
```bash
# Quick health check
make health

# Check PMS connectivity
curl -f http://localhost:8000/health/ready
```

### 3. Gather Initial Information
```bash
# Check circuit breaker metrics
curl -s "http://prometheus:9090/api/v1/query?query=pms_circuit_breaker_state"

# Check recent error rates
curl -s "http://prometheus:9090/api/v1/query?query=rate(pms_adapter_errors_total[5m])"

# Check PMS response times
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,pms_adapter_duration_seconds)"
```

## Investigation Steps

### 4. Analyze Root Cause

#### Check PMS Service Health
```bash
# If using QloApps in Docker
docker ps | grep qloapps
docker logs qloapps-container --tail=50

# Check database connectivity
docker exec qloapps-container mysqladmin ping -h mysql -u root -p
```

#### Check Network Connectivity
```bash
# Test PMS endpoint from agent container
docker exec agente-api curl -v -m 5 http://qloapps/api/v1/health

# Check DNS resolution
docker exec agente-api nslookup qloapps
```

#### Check Resource Utilization
```bash
# Check memory usage
docker stats --no-stream

# Check disk usage
df -h

# Check network interfaces
netstat -i
```

### 5. Common Root Causes & Solutions

#### Cause: PMS Service Down
**Symptoms:**
- Connection refused errors
- PMS container not running
- Database connectivity issues

**Resolution:**
```bash
# Restart PMS service
docker-compose restart qloapps

# Check database
docker-compose restart mysql

# Verify recovery
make health
```

#### Cause: Database Issues
**Symptoms:**
- MySQL connection errors
- Slow query performance
- Lock timeouts

**Resolution:**
```bash
# Check MySQL status
docker exec mysql mysqladmin status

# Check slow queries
docker exec mysql mysqladmin processlist

# Restart if needed
docker-compose restart mysql

# Clear query cache
docker exec mysql mysql -e "RESET QUERY CACHE;"
```

#### Cause: Network Partitioning
**Symptoms:**
- Intermittent connectivity
- Timeout errors
- DNS resolution failures

**Resolution:**
```bash
# Restart Docker networking
docker network prune -f
docker-compose down && docker-compose up -d

# Check bridge networks
docker network ls
docker network inspect bridge
```

#### Cause: Rate Limiting
**Symptoms:**
- 429 status codes
- Rate limit exceeded errors
- Consistent failure pattern

**Resolution:**
```bash
# Check rate limit configuration
grep -r "rate_limit" app/

# Temporarily increase limits in PMS
# (coordinate with PMS admin)

# Enable request throttling
# Update app/services/pms_adapter.py with backoff
```

## Recovery Actions

### 6. Manual Circuit Breaker Reset
```bash
# Force circuit breaker to half-open state
# (Only if root cause is resolved)
curl -X POST "http://localhost:8000/admin/circuit-breaker/reset" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 7. Gradual Traffic Recovery
```bash
# Monitor during recovery
watch -n 5 'curl -s http://prometheus:9090/api/v1/query?query=pms_circuit_breaker_state'

# Check error rates stabilize
curl -s "http://prometheus:9090/api/v1/query?query=rate(pms_adapter_errors_total[1m])"
```

### 8. Validate Full Recovery
```bash
# Run synthetic transactions
make test-pms-integration

# Check SLO compliance
curl -s "http://prometheus:9090/api/v1/query?query=orchestrator_success_rate_5m"

# Verify guest-facing functionality
curl -X POST "http://localhost:8000/api/v1/reservations/check" \
  -H "Content-Type: application/json" \
  -d '{"room_type":"standard","check_in":"2024-01-01","check_out":"2024-01-02"}'
```

## Communication

### 9. Status Updates

#### Internal Team
```
Status: PMS Circuit Breaker Open - Investigating
Impact: Guest reservations temporarily unavailable
ETA: Investigating, updates every 15 minutes
Actions: [List current actions]
```

#### Stakeholders
```
Issue: Technical issue affecting reservation system
Impact: New reservations temporarily unavailable
Workaround: Manual reservation process activated
ETA: Working to resolve within 1 hour
```

#### Resolution Communication
```
Resolution: PMS service restored
Impact: All systems operational
Root Cause: [Brief description]
Prevention: [Actions to prevent recurrence]
```

## Post-Incident Actions

### 10. Document Findings
```bash
# Create incident report
cp docs/templates/incident-report.md "reports/incidents/pms-circuit-breaker-$(date +%Y%m%d_%H%M%S).md"

# Update runbook if needed
# Note any new learnings or procedures
```

### 11. Review & Improve
- Update monitoring thresholds if needed
- Adjust circuit breaker parameters
- Add additional health checks
- Schedule post-mortem meeting

## Prevention

### 12. Monitoring Improvements
```bash
# Add predictive alerts
# Update prometheus/alerts.yml with:
# - pms_cb_failure_ratio_1m > 0.3 (warning)
# - pms_cb_failure_ratio_5m > 0.2 (warning)
```

### 13. Circuit Breaker Tuning
```python
# Update app/core/circuit_breaker.py
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 0.5,  # 50% failure rate
    "recovery_timeout": 30,    # 30 seconds
    "expected_exception": (PMSError, PMSTimeoutError)
}
```

## Escalation

### When to Escalate
- Circuit breaker remains open > 1 hour
- Multiple circuit breakers open simultaneously
- Data consistency issues detected
- Unable to identify root cause within 30 minutes

### Escalation Contacts
- **Technical Lead**: [Contact info]
- **Infrastructure Team**: [Contact info]
- **PMS Vendor Support**: [Contact info]
- **On-call Manager**: [Contact info]

## Testing This Runbook

### Monthly Validation
```bash
# Simulate PMS failure
make chaos-db

# Follow runbook procedures
# Verify all commands work
# Update any outdated information
```

---

**Last Updated**: $(date)
**Next Review**: Monthly
**Tested**: ✅ [Date of last test]
**Owner**: SRE Team