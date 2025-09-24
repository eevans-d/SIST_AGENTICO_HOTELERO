# Runbook: High Error Rate - Orchestrator Service

## 🚨 Alert: Orchestrator Error Rate High

### Quick Reference
- **Alert**: `orchestrator_success_rate_5m < 95%`
- **Severity**: P1 (SLO breach imminent)
- **Impact**: Guest experience degradation
- **Response Time**: 15 minutes

## Immediate Actions (First 5 minutes)

### 1. Triage Severity
```bash
# Check current error rate
curl -s "http://prometheus:9090/api/v1/query?query=orchestrator_success_rate_5m"

# Check error budget consumption
curl -s "http://prometheus:9090/api/v1/query?query=orchestrator_error_budget_used_ratio_30m"

# If error budget > 80%, escalate immediately
```

### 2. Identify Error Sources
```bash
# Check error distribution by endpoint
curl -s "http://prometheus:9090/api/v1/query?query=rate(orchestrator_errors_total[5m]) by (endpoint)"

# Check error types
curl -s "http://prometheus:9090/api/v1/query?query=rate(orchestrator_errors_total[5m]) by (error_type)"

# Check upstream service health
make health
```

### 3. Quick System Check
```bash
# Check container health
docker ps --filter name=agente-api

# Check resource utilization
docker stats agente-api --no-stream

# Check recent logs for patterns
docker logs agente-api --tail=100 | grep -i error
```

## Investigation Phase

### 4. Analyze Error Patterns

#### Check Common Error Sources
```bash
# PMS integration errors
curl -s "http://prometheus:9090/api/v1/query?query=rate(pms_adapter_errors_total[5m])"

# WhatsApp client errors  
curl -s "http://prometheus:9090/api/v1/query?query=rate(whatsapp_errors_total[5m])"

# Database connection errors
curl -s "http://prometheus:9090/api/v1/query?query=rate(database_errors_total[5m])"

# Audio processing errors
curl -s "http://prometheus:9090/api/v1/query?query=rate(audio_processor_errors_total[5m])"
```

#### Analyze Request Characteristics
```bash
# Check request volume
curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total[5m])"

# Check response times
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95, http_request_duration_seconds)"

# Check concurrent requests
curl -s "http://prometheus:9090/api/v1/query?query=http_requests_in_flight"
```

### 5. Root Cause Analysis

#### Scenario A: PMS Integration Issues
**Symptoms:**
- PMS adapter errors high
- Reservation operations failing
- Circuit breaker may be open

**Actions:**
```bash
# Check PMS circuit breaker state
curl -s "http://prometheus:9090/api/v1/query?query=pms_circuit_breaker_state"

# If circuit breaker open, follow PMS runbook
# docs/runbooks/PMS_CIRCUIT_BREAKER_OPEN.md

# If PMS healthy, check adapter logic
docker logs agente-api | grep -i "pms_adapter" | tail -20
```

#### Scenario B: High Traffic Load
**Symptoms:**
- Request rate significantly elevated
- Response times increasing
- Resource utilization high

**Actions:**
```bash
# Check traffic patterns
curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total[5m]) > 100"

# Scale horizontally if possible
docker-compose up -d --scale agente-api=2

# Enable request throttling
# Update nginx configuration to limit requests
sudo nginx -s reload
```

#### Scenario C: Database Performance
**Symptoms:**
- Database query timeouts
- Connection pool exhaustion
- Slow query patterns

**Actions:**
```bash
# Check database connections
curl -s "http://prometheus:9090/api/v1/query?query=database_connections_active"

# Check slow queries
docker exec postgres psql -U postgres -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 5;"

# Check connection pool
docker logs agente-api | grep -i "connection pool"
```

#### Scenario D: External Service Degradation
**Symptoms:**
- WhatsApp API errors
- Gmail API errors
- Third-party service timeouts

**Actions:**
```bash
# Check WhatsApp service status
curl -v "https://graph.facebook.com/v18.0/me" \
  -H "Authorization: Bearer $WHATSAPP_TOKEN"

# Check Gmail API status
# Visit: https://status.developers.google.com/

# Implement graceful degradation
export ENABLE_FALLBACK_MODE=true
docker-compose restart agente-api
```

## Recovery Actions

### 6. Immediate Mitigation

#### Enable Circuit Breakers
```bash
# Force circuit breakers to more aggressive settings
curl -X POST "http://localhost:8000/admin/circuit-breaker/config" \
  -H "Content-Type: application/json" \
  -d '{
    "failure_threshold": 0.3,
    "recovery_timeout": 60,
    "half_open_max_calls": 5
  }'
```

#### Implement Request Throttling
```bash
# Update nginx rate limiting
sudo tee /etc/nginx/conf.d/rate_limit.conf << EOF
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
EOF

sudo nginx -s reload
```

#### Scale Resources
```bash
# Increase container resources
docker-compose stop agente-api
docker-compose up -d --scale agente-api=2

# Or update resource limits
# docker-compose.yml:
# resources:
#   limits:
#     memory: 1G
#     cpus: '1.0'
```

### 7. Monitor Recovery
```bash
# Watch error rate improvement
watch -n 10 'curl -s "http://prometheus:9090/api/v1/query?query=orchestrator_success_rate_5m"'

# Monitor system resources
watch -n 5 'docker stats --no-stream'

# Check for error rate stabilization
curl -s "http://prometheus:9090/api/v1/query?query=deriv(orchestrator_success_rate_5m[2m])"
```

## Validation & Communication

### 8. Validate Recovery
```bash
# Run synthetic tests
curl -X POST "http://localhost:8000/webhooks/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{"test": "synthetic_transaction"}'

# Check SLO compliance
curl -s "http://prometheus:9090/api/v1/query?query=orchestrator_success_rate_5m >= 99.5"

# Verify end-to-end functionality
make test-e2e-quick
```

### 9. Communication Templates

#### Status Update
```
Alert: High error rate in orchestrator service
Current Status: [Investigating/Mitigating/Resolving]
Error Rate: [X]% (Target: <5%)
Impact: [Description of guest impact]
ETA: [Expected resolution time]
Actions: [Current mitigation steps]
```

#### Resolution Update
```
Resolution: Orchestrator error rate normalized
Final Error Rate: [X]% (within SLO)
Root Cause: [Brief technical summary]
Duration: [Total incident time]
Prevention: [Steps to prevent recurrence]
```

## Post-Incident Actions

### 10. Post-Mortem Process
```bash
# Create incident report
mkdir -p reports/incidents
cp docs/templates/post-mortem-template.md \
   "reports/incidents/orchestrator-errors-$(date +%Y%m%d_%H%M%S).md"

# Collect incident data
curl -s "http://prometheus:9090/api/v1/query_range?query=orchestrator_success_rate_5m&start=$(date -d '2 hours ago' +%s)&end=$(date +%s)&step=60" \
  > "reports/incidents/metrics-$(date +%Y%m%d_%H%M%S).json"
```

### 11. Improve Monitoring
```yaml
# Add to prometheus/alerts.yml
groups:
  - name: orchestrator.predictive
    rules:
    - alert: OrchestratorErrorRateIncreasing
      expr: deriv(orchestrator_success_rate_5m[10m]) < -0.01
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "Orchestrator error rate trending upward"
        
    - alert: OrchestratorErrorBudgetBurning
      expr: orchestrator_burn_rate_fast > 1.5
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "Error budget burning faster than expected"
```

### 12. Update Runbooks
- Document new failure patterns discovered
- Update recovery procedures based on what worked
- Add new monitoring queries that were useful
- Schedule team training on lessons learned

## Prevention Strategies

### 13. Proactive Measures
```bash
# Implement canary deployments
# Update CI/CD pipeline to include gradual rollouts

# Add chaos engineering
make chaos-orchestrator

# Implement request retries with exponential backoff
# Update client libraries with retry logic

# Add bulkhead pattern
# Isolate critical operations from non-critical ones
```

### 14. Capacity Planning
```bash
# Analyze traffic patterns
curl -s "http://prometheus:9090/api/v1/query?query=predict_linear(http_requests_total[1h], 3600)"

# Plan for peak loads
# Update auto-scaling policies
# Pre-warm resources during known busy periods
```

## Escalation Criteria

### Immediate Escalation Required
- Error rate > 50% for > 5 minutes
- Complete service outage
- Data corruption suspected
- Security incident detected

### Escalation Contacts
- **Incident Commander**: [Contact]
- **Engineering Manager**: [Contact]  
- **Product Owner**: [Contact]
- **External Vendor Support**: [Contact]

---

**Last Updated**: $(date)
**Next Review**: Monthly
**Tested**: ✅ [Date of last test]
**Owner**: Engineering Team