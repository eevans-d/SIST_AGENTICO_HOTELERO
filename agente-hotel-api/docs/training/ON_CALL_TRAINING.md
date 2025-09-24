# On-Call Training Guide - Agente Hotelero IA

## 🎯 Objetivos del Training

Al completar este training, podrás:
- Responder efectivamente a incidentes de producción
- Utilizar runbooks para resolución sistemática
- Comprender los SLOs y su impacto en el negocio
- Comunicar apropiadamente durante incidentes
- Realizar post-mortems constructivos

## 📚 Materiales Requeridos

### Documentación
- [Governance Framework](../GOVERNANCE_FRAMEWORK.md)
- [Operations Manual](../OPERATIONS_MANUAL.md)
- Runbooks en `/docs/runbooks/`

### Herramientas
- Acceso a Grafana: http://localhost:3000
- Acceso a Prometheus: http://localhost:9090
- Slack channels: `#alerts`, `#incidents`, `#engineering`
- PagerDuty app instalada

### Comandos Esenciales
```bash
# Estado general del sistema
make health
make validate-slo-compliance

# Logs y debugging
docker logs agente-api --tail=100
make logs

# Chaos testing para practice
make chaos-db
make chaos-redis
```

## 🚨 Incident Response Fundamentals

### Severity Levels
| Level | Impact | Response Time | Examples |
|-------|---------|---------------|----------|
| **P0** | Complete outage | 5 min acknowledge | Service down, data loss |
| **P1** | Major degradation | 15 min acknowledge | SLO breach, major features down |
| **P2** | Minor issues | 2 hours acknowledge | Performance degradation |
| **P3** | Cosmetic/future | 24 hours acknowledge | UI issues, non-critical bugs |

### Response Process
1. **ACKNOWLEDGE** - Acknowledge alert immediately
2. **ASSESS** - Determine severity and impact
3. **ASSEMBLE** - Get the right people involved
4. **ACT** - Follow runbooks, implement fixes
5. **ANNOUNCE** - Communicate status to stakeholders

## 🔍 Investigation Skills

### Quick Triage Commands
```bash
# System health overview
make health

# Check recent errors
docker logs agente-api --since="10m" | grep -i error

# SLO status
make validate-slo-compliance

# Resource utilization
docker stats --no-stream

# Circuit breaker states
curl -s "http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state"
```

### Log Analysis Techniques
```bash
# Find error patterns
docker logs agente-api | grep -E "(ERROR|FATAL|Exception)" | tail -20

# Track specific request
docker logs agente-api | grep "correlation_id:abc123"

# Performance analysis
docker logs agente-api | grep "slow_query" | tail -10

# Count error types
docker logs agente-api --since="1h" | grep ERROR | awk '{print $5}' | sort | uniq -c
```

### Metrics Interpretation

#### Key Metrics to Monitor
```bash
# Success rate (should be > 99.5%)
orchestrator_success_rate_5m

# Error budget usage (alert if > 50%)
orchestrator_error_budget_used_ratio_30m

# Response times (P95 should be < 500ms)
histogram_quantile(0.95, http_request_duration_seconds)

# Circuit breaker state (0=closed, 1=half-open, 2=open)
pms_circuit_breaker_state
```

## 📖 Using Runbooks

### Available Runbooks
- [PMS Circuit Breaker Open](../runbooks/PMS_CIRCUIT_BREAKER_OPEN.md)
- [High Error Rate - Orchestrator](../runbooks/HIGH_ERROR_RATE_ORCHESTRATOR.md)
- [Database Connection Issues](../runbooks/DATABASE_CONNECTION_ISSUES.md)
- [Redis Cache Failure](../runbooks/REDIS_CACHE_FAILURE.md)

### Runbook Best Practices
1. **Follow sequentially** - Don't skip steps
2. **Document findings** - Note what you tried
3. **Communicate progress** - Update team every 15 minutes
4. **Escalate when stuck** - Don't waste time on unknown issues
5. **Update runbooks** - Add learnings after incidents

### Example: Following a Runbook
```bash
# Step 1: Acknowledge alert
curl -X POST "http://alertmanager:9093/api/v1/alerts" -d '...'

# Step 2: Check system status
make health

# Step 3: Identify root cause
docker ps | grep qloapps
docker logs qloapps-container --tail=50

# Step 4: Implement fix
docker-compose restart qloapps

# Step 5: Validate recovery
make health
```

## 💬 Communication Guidelines

### Internal Team Updates
```
Status: [Alert description] - [Current status]
Impact: [What's affected for users]  
ETA: [Expected resolution time]
Actions: [What you're currently doing]
Next Update: [When you'll update again]
```

### Stakeholder Communication
```
We're experiencing [brief description of issue].
Impact: [User-facing impact in business terms]
Status: [Investigating/Working on fix/Resolved]
Workaround: [If any available]
ETA: [Expected resolution]
```

### Resolution Communication
```
✅ RESOLVED: [Brief description]
Duration: [How long the incident lasted]
Root Cause: [Non-technical explanation]
Prevention: [What we're doing to prevent recurrence]
```

## 🎓 Practical Exercises

### Exercise 1: Basic Incident Response
**Scenario**: PMS circuit breaker has opened

1. Acknowledge the alert
2. Follow the PMS Circuit Breaker runbook
3. Practice communication templates
4. Document your actions

```bash
# Simulate the scenario
make chaos-db

# Follow runbook: docs/runbooks/PMS_CIRCUIT_BREAKER_OPEN.md
# Time yourself - should be < 15 minutes to first mitigation
```

### Exercise 2: SLO Investigation
**Scenario**: Success rate has dropped to 94%

1. Use SLO validation script
2. Identify which services are failing
3. Correlate with recent deployments
4. Plan mitigation strategy

```bash
# Check current SLO status
make validate-slo-compliance

# Investigate error sources
curl -s "http://localhost:9090/api/v1/query?query=rate(orchestrator_errors_total[5m]) by (endpoint)"
```

### Exercise 3: Escalation Decision
**Scenario**: Unknown database error, runbook doesn't help

Practice escalation decision-making:
- When to escalate vs. keep investigating?
- Who to escalate to?
- What information to provide?

## 🔧 Tools Training

### Grafana Navigation
1. **Main Dashboard**: Overview of system health
2. **SLO Dashboard**: Success rates, error budgets
3. **Resilience Dashboard**: Circuit breakers, chaos results
4. **Infrastructure**: Resource utilization, container health

### Prometheus Queries Training
```bash
# Basic success rate
rate(http_requests_total{status!~"5.."}[5m]) / rate(http_requests_total[5m])

# Error rate by endpoint
rate(http_requests_total{status=~"5.."}[5m]) by (endpoint)

# 95th percentile response time  
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Circuit breaker failure prediction
increase(pms_adapter_errors_total[1m]) / increase(pms_adapter_requests_total[1m])
```

### Docker Debugging
```bash
# Container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Resource usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Execute commands in container
docker exec -it agente-api bash

# Check container logs with filters
docker logs agente-api --since="1h" | grep -E "(ERROR|WARN)" | tail -20
```

## 📊 SLO and Error Budget Training

### Understanding SLOs
- **SLI**: Service Level Indicator (what we measure)
- **SLO**: Service Level Objective (target we aim for)  
- **SLA**: Service Level Agreement (contractual commitment)

### Error Budget Concepts
```
Error Budget = (1 - SLO) × Total Requests
Example: 99.5% SLO = 0.5% error budget

Monthly budget for 1M requests: 5,000 failed requests
```

### Burn Rate Analysis
- **Fast burn** (5m window): Detects immediate issues
- **Slow burn** (1h window): Detects gradual degradation

```bash
# Check current burn rates
make check-burn-rates

# Alert thresholds:
# Fast burn > 2.0 = Page immediately  
# Slow burn > 1.5 = Create ticket
```

## 🎯 Assessment Checklist

### Knowledge Check
- [ ] Can explain P0 vs P1 severity
- [ ] Knows when to escalate
- [ ] Can follow runbooks systematically
- [ ] Understands SLO/error budget concepts
- [ ] Can write clear incident communications

### Practical Skills
- [ ] Can acknowledge alerts quickly
- [ ] Can use Grafana dashboards effectively
- [ ] Can analyze logs for patterns
- [ ] Can execute recovery commands safely
- [ ] Can validate fixes properly

### Emergency Contacts
- [ ] Has PagerDuty app configured
- [ ] Knows escalation contacts
- [ ] Has access to all required tools
- [ ] Knows how to reach incident commander

## 📝 Certification

### Requirements
1. Complete all practical exercises
2. Shadow 2 real incidents
3. Lead 1 incident response (with backup)
4. Pass knowledge assessment (80%)
5. Update 1 runbook based on learnings

### Ongoing Development
- Monthly runbook review sessions
- Quarterly chaos engineering exercises
- Semi-annual incident response drills
- Continuous feedback and improvement

## 📞 Emergency Contacts

### Immediate Escalation
- **Incident Commander**: [Contact]
- **Engineering Manager**: [Contact]
- **On-call Backup**: [Contact]

### External Support
- **PMS Vendor**: [Support contact]
- **Cloud Provider**: [Support contact]
- **Security Team**: [Contact]

---

**Training Version**: 1.0
**Last Updated**: $(date)
**Next Review**: Quarterly
**Trainer**: SRE Team