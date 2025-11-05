# Production Launch Runbook

**Version**: 1.0  
**Date**: 2024-10-15  
**Purpose**: Step-by-step production deployment procedures  
**Owner**: DevOps Team

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Launch Checklist](#pre-launch-checklist)
3. [Launch Timeline](#launch-timeline)
4. [Deployment Procedures](#deployment-procedures)
5. [Validation Procedures](#validation-procedures)
6. [Rollback Procedures](#rollback-procedures)
7. [Communication Plan](#communication-plan)
8. [Post-Launch Monitoring](#post-launch-monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose
This runbook provides detailed, step-by-step procedures for deploying the Agente Hotelero IA system to production.

### Scope
- Production deployment of agente-hotel-api
- Database migration execution
- Service health validation
- Post-deployment monitoring

### Assumptions
- ✅ Go/No-Go decision completed with **GO** or **GO WITH CAUTION**
- ✅ All infrastructure provisioned
- ✅ All team members trained
- ✅ Rollback plan tested

### Roles

**Launch Commander** (Overall ownership):
- Coordinates entire launch
- Makes go/abort decisions
- Communicates status

**Deployment Engineer** (Executes deployment):
- Runs deployment scripts
- Monitors progress
- Executes rollback if needed

**Database Engineer** (Manages migrations):
- Executes database migrations
- Validates data integrity
- Manages backup/restore

**Monitoring Engineer** (Watches metrics):
- Monitors dashboards continuously
- Reports anomalies immediately
- Validates health checks

**Communication Lead** (Stakeholder updates):
- Updates status page
- Sends stakeholder notifications
- Coordinates external communications

---

## Pre-Launch Checklist

### T-24 Hours: Final Validation

**Infrastructure**:
- [ ] Production servers accessible (SSH keys, VPN)
- [ ] DNS records configured and propagated
- [ ] SSL certificates valid (expiry > 90 days)
- [ ] Load balancer health checks configured
- [ ] Firewall rules reviewed and active

**Database**:
- [ ] Full backup completed successfully
- [ ] Backup validated (restore test)
- [ ] WAL archiving active
- [ ] Replication lag < 5 seconds
- [ ] Disk space > 50% free

**Application**:
- [ ] Docker images built and tagged
- [ ] Images pushed to registry
- [ ] Image security scan clean (no HIGH/CRITICAL)
- [ ] Environment variables configured
- [ ] Secrets rotated and validated

**Monitoring**:
- [ ] Prometheus scraping production endpoints
- [ ] Grafana dashboards functional
- [ ] AlertManager rules active
- [ ] PagerDuty integration tested
- [ ] Slack notifications working

**Team Readiness**:
- [ ] All team members available (no PTO)
- [ ] On-call schedule confirmed
- [ ] Incident response procedures reviewed
- [ ] Communication channels tested (Slack, phone)
- [ ] Rollback procedure reviewed

**Documentation**:
- [ ] This runbook current and accessible
- [ ] Rollback runbook ready
- [ ] Incident response runbooks ready
- [ ] Contact list up-to-date

### T-2 Hours: Team Briefing

**Meeting Duration**: 30 minutes  
**Attendees**: Launch Commander, all engineers

**Agenda**:
1. Review launch timeline
2. Confirm roles and responsibilities
3. Review validation checkpoints
4. Review rollback criteria
5. Review communication plan
6. Questions and concerns

**Outcomes**:
- [ ] All team members understand timeline
- [ ] All team members know their role
- [ ] All team members can access necessary systems
- [ ] Launch Commander confirms readiness

---

## Launch Timeline

### Timeline Overview

```
T-60min: Pre-deployment validation
T-45min: Create maintenance window
T-30min: Begin deployment
T-15min: Database migration
T-10min: Deploy application
T-5min:  Health checks
T+0min:  Go live (traffic cutover)
T+15min: Initial validation
T+30min: Full validation
T+60min: Monitoring handoff
T+2h:    Initial checkpoint
T+4h:    Secondary checkpoint
T+24h:   24-hour review
T+48h:   48-hour review
T+1wk:   One-week retrospective
```

### Detailed Timeline

---

#### **T-60 Minutes: Pre-Deployment Validation**

**Duration**: 15 minutes  
**Owner**: Deployment Engineer

**Tasks**:
```bash
# 1. Verify production access
ssh production-server-1
ssh production-server-2
ssh production-database

# 2. Check current system status
cd /opt/agente-hotel-api
docker compose ps
# All services should be "Up" and healthy

# 3. Verify disk space
df -h
# All mounts should have >30% free space

# 4. Check database status
docker compose exec postgres psql -U agente -c "SELECT version();"
docker compose exec postgres psql -U agente -c "SELECT pg_is_in_recovery();"
# Should return 'f' (not in recovery)

# 5. Verify monitoring
curl -s http://localhost:9090/-/healthy  # Prometheus
curl -s http://localhost:3000/api/health # Grafana

# 6. Review recent logs (no errors expected)
docker compose logs --tail=50 agente-api
```

**Validation**:
- [ ] SSH access confirmed to all servers
- [ ] All current services healthy
- [ ] Disk space adequate (>30% free)
- [ ] Database accessible and operational
- [ ] Monitoring stack operational
- [ ] No recent errors in logs

**Abort Criteria**:
- Cannot access production servers
- Current system unhealthy
- Disk space <20%
- Database unreachable or in recovery
- Monitoring down

---

#### **T-45 Minutes: Create Maintenance Window**

**Duration**: 5 minutes  
**Owner**: Communication Lead

**Tasks**:
```bash
# 1. Update status page (if GO WITH CAUTION or expecting brief downtime)
# Post message:
"Scheduled maintenance in progress. Expected duration: 30 minutes.
Service may be briefly unavailable. We'll update as work progresses."

# 2. Send Slack notification
# To: #agente-hotel-alerts, #engineering-all
"🚀 Production deployment starting in 45 minutes (T-45).
Launch Commander: [Name]
Deployment Engineer: [Name]
Status updates: #agente-hotel-launch"

# 3. Notify stakeholders (email)
To: Product, Customer Success, Support
Subject: "Production Launch - [Date] [Time]"
Body: "Production deployment beginning at [Time]. Expected duration 30 minutes.
Status page: [URL]. Contact: [Launch Commander email/phone]"
```

**Validation**:
- [ ] Status page updated
- [ ] Slack notifications sent
- [ ] Stakeholder email sent
- [ ] #agente-hotel-launch channel active

---

#### **T-30 Minutes: Begin Deployment**

**Duration**: 10 minutes  
**Owner**: Deployment Engineer

**Tasks**:
```bash
# 1. Pull latest code
cd /opt/agente-hotel-api
git fetch origin
git checkout main
git pull origin main

# 2. Verify correct version
git log --oneline -1
# Should match expected commit SHA

# 3. Pull new Docker images
docker compose pull

# 4. Verify images
docker images | grep agente-hotel-api
# Should show new version tag

# 5. Backup current config
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
cp docker-compose.yml docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)

# 6. Update environment (if needed)
# Review and apply any new environment variables
```

**Validation**:
- [ ] Code at correct commit SHA
- [ ] New Docker images pulled successfully
- [ ] Images match expected version
- [ ] Current config backed up
- [ ] Environment variables updated (if needed)

**Abort Criteria**:
- Wrong commit checked out
- Image pull fails
- Image security scan fails

---

#### **T-15 Minutes: Database Migration**

**Duration**: 5-10 minutes  
**Owner**: Database Engineer

**Pre-Migration**:
```bash
# 1. Final backup before migration
docker compose exec postgres pg_dump -U agente agente_db > backup_pre_migration_$(date +%Y%m%d-%H%M%S).sql
gzip backup_pre_migration_*.sql

# 2. Verify backup
ls -lh backup_pre_migration_*.sql.gz
# Should exist and have reasonable size

# 3. Check current schema version
docker compose exec postgres psql -U agente -d agente_db -c "SELECT version FROM alembic_version;"
# Note current version

# 4. Test migration on replica (if available) or staging
# Already done pre-launch, but confirm success
```

**Migration Execution**:
```bash
# 1. Run migration
docker compose exec agente-api alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, Add user_preferences table
# INFO  [alembic.runtime.migration] Running upgrade def456 -> ghi789, Add indexes for performance

# 2. Verify new schema version
docker compose exec postgres psql -U agente -d agente_db -c "SELECT version FROM alembic_version;"
# Should show new version

# 3. Validate migration success
docker compose exec agente-api python -c "
from app.core.database import SessionLocal
from app.models import *
db = SessionLocal()
# Run test queries
print('Users:', db.query(User).count())
print('Sessions:', db.query(Session).count())
db.close()
print('Migration validated successfully')
"
```

**Validation**:
- [ ] Pre-migration backup created
- [ ] Migration executed without errors
- [ ] Schema version updated correctly
- [ ] Test queries successful
- [ ] No data loss (record counts match expectations)

**Rollback Trigger**:
- Migration fails with error
- Data integrity check fails
- Schema version mismatch

---

#### **T-10 Minutes: Deploy Application**

**Duration**: 5 minutes  
**Owner**: Deployment Engineer

**Deployment**:
```bash
# 1. Deploy with zero-downtime (rolling update)
docker compose up -d --no-deps --build agente-api

# This will:
# - Build new containers
# - Start new containers
# - Health check new containers
# - Stop old containers only after new ones healthy

# 2. Watch deployment progress
docker compose ps
# Watch status change from "Up" to "Up (health: starting)" to "Up (healthy)"

# 3. Monitor logs in real-time
docker compose logs -f --tail=50 agente-api

# Look for:
# ✅ "Application startup complete"
# ✅ "Lifespan startup complete"
# ✅ "Uvicorn running on http://0.0.0.0:8000"
# ❌ Any ERROR or CRITICAL logs
```

**Validation**:
- [ ] New containers started
- [ ] Health checks passing
- [ ] No errors in startup logs
- [ ] Old containers stopped gracefully

**Abort Criteria**:
- Containers fail to start
- Health checks fail
- Critical errors in logs

---

#### **T-5 Minutes: Health Checks**

**Duration**: 5 minutes  
**Owner**: Monitoring Engineer

**Basic Health**:
```bash
# 1. Liveness check
curl -f http://localhost:8000/health/live
# Expected: {"status": "ok", "timestamp": "..."}

# 2. Readiness check
curl -f http://localhost:8000/health/ready
# Expected: {
#   "status": "ready",
#   "checks": {
#     "database": "healthy",
#     "redis": "healthy",
#     "pms": "healthy"
#   },
#   "version": "1.0.0"
# }

# 3. Metrics endpoint
curl -f http://localhost:9090/metrics | head -20
# Should return Prometheus metrics

# 4. API smoke test
curl -f -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "from": "+1234567890",
      "type": "text",
      "text": {"body": "test"}
    }]
  }'
# Expected: 200 OK
```

**Database Connectivity**:
```bash
# Test database connection from app
docker compose exec agente-api python -c "
from app.core.database import get_db
from sqlalchemy import text
db = next(get_db())
result = db.execute(text('SELECT 1')).scalar()
assert result == 1
print('Database connectivity: OK')
"
```

**Redis Connectivity**:
```bash
# Test Redis connection
docker compose exec agente-api python -c "
from app.core.redis_client import get_redis_client
redis = get_redis_client()
redis.ping()
print('Redis connectivity: OK')
"
```

**External Integrations**:
```bash
# Test PMS connectivity (using mock or real)
curl -f http://localhost:8000/api/v1/admin/health/pms
# Expected: {"status": "healthy", "latency_ms": 120}

# Test WhatsApp API
curl -f http://localhost:8000/api/v1/admin/health/whatsapp
# Expected: {"status": "healthy"}
```

**Validation**:
- [ ] Liveness check passing
- [ ] Readiness check passing
- [ ] Metrics endpoint responding
- [ ] API smoke test successful
- [ ] Database connectivity confirmed
- [ ] Redis connectivity confirmed
- [ ] PMS integration healthy
- [ ] WhatsApp integration healthy

**Rollback Trigger**:
- Any health check fails
- Database unreachable
- Redis unreachable
- Critical external service down

---

#### **T+0 Minutes: Go Live (Traffic Cutover)**

**Duration**: Immediate  
**Owner**: Deployment Engineer

**Tasks**:
```bash
# 1. Enable external traffic (if using load balancer drain mode)
# AWS ALB example:
aws elbv2 modify-target-group-attributes \
  --target-group-arn $TARGET_GROUP_ARN \
  --attributes Key=deregistration_delay.timeout_seconds,Value=30

# Or if using NGINX:
# Update nginx config to point to new backend
sudo nginx -s reload

# 2. Verify traffic flowing
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total[1m]) | jq'
# Should see increasing request rate

# 3. Monitor error rate
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[1m]) | jq'
# Should remain near zero
```

**Communication**:
```bash
# Slack notification
# To: #agente-hotel-launch, #engineering-all
"✅ Production deployment complete (T+0). Service is now live.
Initial health checks: PASS
Traffic cutover: COMPLETE
Monitoring: ACTIVE
Next checkpoint: T+15min"
```

**Validation**:
- [ ] Traffic flowing to new deployment
- [ ] Request rate as expected
- [ ] Error rate <0.1%
- [ ] Latency within SLAs (P95 < 1s)

---

#### **T+15 Minutes: Initial Validation**

**Duration**: 10 minutes  
**Owner**: Monitoring Engineer

**Metrics Check**:
```bash
# 1. Request rate (should match pre-deployment baseline)
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])' | jq

# 2. Error rate (should be <0.1%)
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])/rate(http_requests_total[5m])' | jq

# 3. Latency (P95 should be <1s)
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))' | jq

# 4. Database connections
curl -s 'http://localhost:9090/api/v1/query?query=postgres_connections_active' | jq

# 5. Redis operations
curl -s 'http://localhost:9090/api/v1/query?query=rate(redis_commands_total[5m])' | jq
```

**Functional Testing**:
```bash
# Run E2E test suite against production
cd /opt/agente-hotel-api/tests/e2e
pytest test_production_smoke.py -v

# Tests should include:
# - Health checks
# - WhatsApp message processing
# - PMS availability check
# - Session creation
# - Simple reservation inquiry
```

**User Validation** (if applicable):
- [ ] Internal user tests core workflows
- [ ] QA team validates critical paths
- [ ] No user-reported issues

**Validation**:
- [ ] Request rate normal
- [ ] Error rate <0.1%
- [ ] Latency within SLAs
- [ ] Database connections stable
- [ ] Redis operations normal
- [ ] E2E tests passing
- [ ] No alerts triggered

**Rollback Trigger**:
- Error rate >1%
- P95 latency >2s
- E2E tests failing
- Critical alerts fired

---

#### **T+30 Minutes: Full Validation**

**Duration**: 15 minutes  
**Owner**: Launch Commander

**Comprehensive Check**:
```bash
# 1. Review Grafana dashboards
# Open: http://grafana.example.com/d/agente-hotel-overview
# Check:
# - Request rate trends
# - Error rate (should be flat near zero)
# - Latency (P50, P95, P99)
# - Database performance
# - Redis performance
# - Circuit breaker states
# - PMS integration health

# 2. Review AlertManager (should be quiet)
# Open: http://alertmanager.example.com
# Verify: No firing alerts

# 3. Check logs for anomalies
docker compose logs --since 30m agente-api | grep -i error
docker compose logs --since 30m agente-api | grep -i critical
# Should return minimal or zero results

# 4. Validate business metrics
# Run custom query to check:
# - Messages processed
# - Sessions created
# - Successful PMS calls
# - Cache hit rate
```

**Stakeholder Validation**:
- [ ] Product team validates features work
- [ ] Customer success confirms no user issues
- [ ] Support team reports no incidents

**Communication**:
```bash
# Slack notification
# To: #agente-hotel-launch
"✅ T+30min checkpoint: All systems healthy
Request rate: [X] req/s (baseline: [Y] req/s)
Error rate: [X]% (target: <0.1%)
P95 latency: [X]ms (target: <1000ms)
Alerts: None
Next checkpoint: T+60min"
```

**Validation**:
- [ ] All dashboards green
- [ ] No alerts firing
- [ ] Logs clean (no errors/criticals)
- [ ] Business metrics normal
- [ ] Stakeholders satisfied

**Rollback Decision Point**:
- This is the final easy rollback point
- After this, rollback becomes more complex (data may have changed)
- Launch Commander makes GO/ABORT decision

**Abort Criteria**:
- Persistent elevated error rate
- Degraded user experience
- Stakeholder concerns
- Data integrity issues

---

#### **T+60 Minutes: Monitoring Handoff**

**Duration**: 15 minutes  
**Owner**: Launch Commander

**Tasks**:
```bash
# 1. Review launch status
# Compile metrics:
# - Total requests processed since launch
# - Error rate trend
# - Latency trend
# - Any incidents/anomalies
# - Rollback needed? (No)

# 2. Handoff to on-call team
# Brief on-call engineer:
# - Deployment successful
# - Current system status
# - What to watch for
# - When to escalate
# - Rollback procedure (if needed)

# 3. Update status page
# Post message:
"Deployment complete. All systems operational.
Thank you for your patience during maintenance."

# 4. Send stakeholder update
# To: Product, Customer Success, Support, Management
# Subject: "Production Launch Complete - [Date]"
# Body: "Production deployment completed successfully at [Time].
# All systems healthy. Monitoring continues for 48 hours.
# Metrics: [X] req/s, [Y]% errors, [Z]ms P95 latency.
# No user-reported issues. Team available 24/7 for support."
```

**Validation**:
- [ ] Launch status documented
- [ ] On-call engineer briefed
- [ ] Status page updated ("Operational")
- [ ] Stakeholders notified

---

#### **T+2 Hours: Initial Checkpoint**

**Duration**: 10 minutes  
**Owner**: On-Call Engineer

**Tasks**:
- Review dashboards (request rate, errors, latency)
- Check AlertManager (should be quiet)
- Review logs for any warnings
- Validate business metrics
- Report status in #agente-hotel-launch

**Validation**:
- [ ] All metrics within SLAs
- [ ] No alerts
- [ ] No anomalies in logs
- [ ] Business metrics normal

---

#### **T+4 Hours: Secondary Checkpoint**

**Duration**: 10 minutes  
**Owner**: On-Call Engineer

**Tasks**:
- Same as T+2h checkpoint
- If all clear, reduce monitoring frequency to every 4 hours

---

#### **T+24 Hours: 24-Hour Review**

**Duration**: 30 minutes  
**Owner**: Launch Commander + Team

**Meeting Agenda**:
1. Review 24h metrics
2. Any incidents or anomalies?
3. User feedback (if any)
4. Outstanding issues
5. Adjust monitoring if needed
6. Plan for 48h review

**Deliverable**:
- 24-hour status report
- Decision: Continue monitoring or declare stable

---

#### **T+48 Hours: 48-Hour Review**

**Duration**: 30 minutes  
**Owner**: Launch Commander + Team

**Meeting Agenda**:
1. Review 48h metrics
2. Compare to pre-launch baseline
3. User feedback summary
4. Any adjustments needed?
5. Declare launch success or identify issues

**Deliverable**:
- 48-hour status report
- Decision: Declare stable or extend monitoring

**If Stable**:
- Update status: "Launch successful"
- Return to normal monitoring cadence
- Schedule retrospective

---

#### **T+1 Week: Retrospective**

**Duration**: 60 minutes  
**Owner**: Engineering Lead

**Meeting Agenda**:
1. What went well?
2. What could be improved?
3. Any surprises?
4. Lessons learned
5. Action items for next launch

**Deliverable**:
- Retrospective document
- Updated runbook (if needed)
- Action items assigned

---

## Deployment Procedures

### Zero-Downtime Deployment

**Method**: Rolling update with health checks

**Steps**:
1. New containers start alongside old containers
2. New containers pass health checks
3. Load balancer begins sending traffic to new containers
4. Old containers drain existing connections
5. Old containers stop after drain period

**Configuration** (docker-compose.yml):
```yaml
services:
  agente-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 30s
        order: start-first  # Start new before stopping old
      rollback_config:
        parallelism: 1
        delay: 10s
```

**Validation**:
```bash
# Monitor health during deployment
watch -n 2 'docker compose ps'

# Should see:
# - Old containers: Up (healthy)
# - New containers: Up (health: starting) → Up (healthy)
# - Old containers: Exited (after new healthy)
```

---

## Validation Procedures

### Automated Validation Script

**Location**: `scripts/validate-deployment.sh`

**Usage**:
```bash
cd /opt/agente-hotel-api
./scripts/validate-deployment.sh production

# Output:
# ✅ Liveness check: PASS
# ✅ Readiness check: PASS
# ✅ Metrics endpoint: PASS
# ✅ Database connectivity: PASS
# ✅ Redis connectivity: PASS
# ✅ PMS integration: PASS
# ✅ E2E smoke tests: PASS (5/5)
# 
# VALIDATION: SUCCESS
# Deployment is healthy and operational.
```

**Script** (create if not exists):
```bash
#!/bin/bash
set -e

ENV=${1:-production}
API_URL="http://localhost:8000"

echo "🔍 Validating deployment in $ENV environment..."
echo ""

# 1. Liveness
echo -n "✓ Liveness check: "
if curl -sf $API_URL/health/live > /dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 2. Readiness
echo -n "✓ Readiness check: "
if curl -sf $API_URL/health/ready > /dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 3. Metrics
echo -n "✓ Metrics endpoint: "
if curl -sf $API_URL/metrics > /dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 4. Database
echo -n "✓ Database connectivity: "
if docker compose exec -T agente-api python -c "from app.core.database import engine; engine.connect()" 2>/dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 5. Redis
echo -n "✓ Redis connectivity: "
if docker compose exec -T agente-api python -c "from app.core.redis_client import get_redis_client; get_redis_client().ping()" 2>/dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 6. PMS Integration
echo -n "✓ PMS integration: "
if curl -sf $API_URL/api/v1/admin/health/pms > /dev/null; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

# 7. E2E Smoke Tests
echo -n "✓ E2E smoke tests: "
if pytest tests/e2e/test_production_smoke.py -q > /dev/null 2>&1; then
  echo "PASS"
else
  echo "FAIL"; exit 1
fi

echo ""
echo "✅ VALIDATION: SUCCESS"
echo "Deployment is healthy and operational."
exit 0
```

---

## Rollback Procedures

### When to Rollback

**Immediate Rollback** (within first 30 minutes):
- Error rate >5%
- P95 latency >3s
- Critical service down (database, Redis, PMS)
- Data corruption detected
- Security breach detected

**Considered Rollback** (30min - 2h):
- Error rate 1-5% (investigate first)
- P95 latency 2-3s
- Non-critical service degraded
- User-reported issues increasing

**No Rollback Needed** (after 2h, if stable):
- Error rate <1%
- Latency within SLAs
- No critical issues
- Fixable with hotfix

### Rollback Decision

**Decision Maker**: Launch Commander

**Process**:
1. Assess current state (metrics, logs, user impact)
2. Estimate fix time (minutes? hours?)
3. Compare: Fix forward vs rollback
4. If rollback chosen, announce immediately
5. Execute rollback procedure

### Automated Rollback

**Method**: Docker Compose rollback

**Steps**:
```bash
# 1. Announce rollback
# Slack: #agente-hotel-launch
"🚨 ROLLBACK INITIATED (T+[X]min)
Reason: [Error rate / latency / critical issue]
Commander: [Name]
Status updates every 5 minutes"

# 2. Execute rollback
docker compose rollback agente-api

# This will:
# - Stop current containers
# - Start previous version containers
# - Wait for health checks
# - Restore service

# 3. Monitor rollback
docker compose ps
docker compose logs -f agente-api

# 4. Validate rollback success
./scripts/validate-deployment.sh production

# 5. Rollback database (if needed)
# Only if migrations broke something
docker compose exec postgres psql -U agente -d agente_db < backup_pre_migration_[TIMESTAMP].sql

# 6. Announce completion
"✅ ROLLBACK COMPLETE (T+[Y]min)
Service restored to previous version.
Current status: [Healthy / Degraded]
Error rate: [X]%
Latency: [X]ms
Root cause investigation in progress."
```

**Validation After Rollback**:
- [ ] Services healthy
- [ ] Error rate <0.1%
- [ ] Latency back to normal
- [ ] No alerts firing
- [ ] Users can access service

**Post-Rollback**:
1. Conduct incident retrospective
2. Identify root cause
3. Fix issue
4. Re-test in staging
5. Schedule new launch date

---

## Communication Plan

### Internal Communication

**Slack Channels**:
- `#agente-hotel-launch`: Real-time launch updates (every milestone)
- `#agente-hotel-alerts`: Automated alerts and anomalies
- `#engineering-all`: High-level announcements

**Update Frequency**:
- Every major milestone (T-60, T-30, T-15, T+0, T+15, T+30, T+60)
- Every 4 hours after T+60 (if GO WITH CAUTION)
- Immediately if issues arise

**Template**:
```
[EMOJI] [Milestone] - [Status]
Time: T+[X]min
Status: [Green/Yellow/Red]
Key Metrics:
- Request rate: [X] req/s
- Error rate: [X]%
- P95 latency: [X]ms
Issues: [None / Description]
Next update: T+[Y]min
```

### External Communication

**Status Page** (status.agente-hotel.com):
- Update at: T-45 (maintenance notice), T+0 (complete), T+60 (operational)

**Stakeholder Emails**:
- **Pre-launch** (T-24h): "Production launch scheduled for [Date/Time]"
- **Launch start** (T-45): "Deployment in progress, expected duration 30 min"
- **Launch complete** (T+60): "Deployment successful, all systems operational"
- **If rollback** (Immediate): "Issue detected, service restored to previous version"

**User Communications** (if user-facing):
- In-app notification: "We've upgraded! You may need to refresh."
- Email (if significant): "New features available - [link to release notes]"

---

## Post-Launch Monitoring

### First 48 Hours

**Monitoring Intensity**:
- **0-2h**: Continuous (every 5-15 minutes)
- **2-24h**: Every 2 hours
- **24-48h**: Every 4 hours

**What to Monitor**:
1. **Request Rate**: Should match pre-launch baseline (±10%)
2. **Error Rate**: Should be <0.1%
3. **Latency**: P95 <1s, P99 <2s
4. **Database**: Connection pool, query performance
5. **Redis**: Hit rate, connection count
6. **PMS Integration**: Success rate, latency
7. **Circuit Breakers**: All closed
8. **Disk Space**: Should not increase abnormally
9. **Memory Usage**: Should be stable
10. **CPU Usage**: Should be <70%

**Dashboards**:
- Main overview: `http://grafana/d/agente-hotel-overview`
- Database: `http://grafana/d/postgres-dashboard`
- Redis: `http://grafana/d/redis-dashboard`
- Business metrics: `http://grafana/d/business-metrics`

**Alerts**:
All production alerts active (see `docker/alertmanager/config.yml`)

### Week 1

**Monitoring Cadence**:
- Daily check-in (15 minutes)
- Review metrics trends
- Check for anomalies
- User feedback review

**Focus Areas**:
- Performance trends (any degradation?)
- Error patterns (any new errors?)
- User feedback (any complaints?)
- Resource usage (any leaks?)

### Month 1

**Monitoring Cadence**:
- Weekly review (30 minutes)
- Compare to baseline
- Identify improvements
- Plan optimizations

---

## Troubleshooting

### Common Issues

#### Issue: Containers fail to start

**Symptoms**: `docker compose up` exits with error

**Diagnosis**:
```bash
docker compose logs agente-api
# Look for startup errors
```

**Common Causes**:
1. Missing environment variable
2. Database migration failed
3. Port already in use
4. Image pull failed

**Resolution**:
```bash
# 1. Check environment
docker compose config
# Verify all required vars present

# 2. Check ports
sudo netstat -tlnp | grep 8000
# Kill process if port in use

# 3. Re-pull images
docker compose pull

# 4. Retry deployment
docker compose up -d
```

---

#### Issue: Health checks failing

**Symptoms**: Containers in "unhealthy" state

**Diagnosis**:
```bash
docker compose ps
# Shows "(unhealthy)" status

docker compose logs agente-api | tail -50
# Check for errors
```

**Common Causes**:
1. Database unreachable
2. Redis unreachable
3. Application startup error
4. Health check endpoint broken

**Resolution**:
```bash
# 1. Test database
docker compose exec postgres pg_isready

# 2. Test Redis
docker compose exec redis redis-cli ping

# 3. Test health endpoint manually
docker compose exec agente-api curl -f http://localhost:8000/health/live

# 4. Check application logs
docker compose logs agente-api --tail=100 | grep -i error
```

---

#### Issue: High error rate

**Symptoms**: Prometheus shows error_rate >1%

**Diagnosis**:
```bash
# 1. Identify error types
docker compose logs agente-api | grep ERROR | tail -50

# 2. Check Grafana error dashboard
# Open: http://grafana/d/errors-dashboard

# 3. Query Prometheus for error breakdown
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])by(endpoint)' | jq
```

**Common Causes**:
1. Database connection pool exhausted
2. External service (PMS, WhatsApp) down
3. Application bug
4. Resource exhaustion

**Resolution**:
```bash
# 1. If database: increase pool size
# Edit docker-compose.yml:
# POSTGRES_POOL_SIZE=20  # increase from 10

# 2. If external service: verify connectivity
curl -f $PMS_API_URL/health
curl -f https://graph.facebook.com/v18.0/me?access_token=$WHATSAPP_TOKEN

# 3. If application bug: rollback
docker compose rollback agente-api

# 4. If resources: scale up
docker compose up -d --scale agente-api=3
```

---

#### Issue: High latency

**Symptoms**: P95 latency >2s

**Diagnosis**:
```bash
# 1. Check slow queries
docker compose exec postgres psql -U agente -d agente_db -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# 2. Check Redis performance
docker compose exec redis redis-cli --latency

# 3. Check PMS latency
curl -s http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(pms_api_latency_seconds_bucket[5m])) | jq
```

**Common Causes**:
1. Slow database queries
2. Redis connection issues
3. PMS API slow
4. Too many concurrent requests

**Resolution**:
```bash
# 1. Add database indexes (if missing)
docker compose exec postgres psql -U agente -d agente_db -c "
CREATE INDEX CONCURRENTLY idx_sessions_user_id ON sessions(user_id);
"

# 2. Increase cache TTL (reduce DB load)
# Edit .env: CACHE_TTL=600  # increase from 300

# 3. Scale horizontally
docker compose up -d --scale agente-api=3

# 4. Enable PMS rate limiting (if API overloaded)
# Edit .env: PMS_RATE_LIMIT=10  # requests per second
```

---

### Emergency Contacts

| Role | Name | Phone | Email | Backup |
|------|------|-------|-------|--------|
| **Launch Commander** | [Name] | [Phone] | [Email] | [Backup Name] |
| **CTO** | [Name] | [Phone] | [Email] | N/A |
| **Database DBA** | [Name] | [Phone] | [Email] | [Backup] |
| **Infrastructure** | [Name] | [Phone] | [Email] | [Backup] |
| **On-Call** | [Schedule Link] | PagerDuty | [Email] | [Schedule] |

---

## Appendix

### A. Pre-Launch Checklist (Full)

**Complete checklist**: `docs/P020-PRODUCTION-READINESS-CHECKLIST.md`

**Quick summary**: 145 items, 87 critical, target 100% critical + >95% overall

### B. Rollback Runbook

**Detailed rollback procedures**: `docs/ROLLBACK-PROCEDURES.md`

### C. Incident Response

**Incident runbooks**: `docs/runbooks/` (10 scenarios)

### D. Scripts

- `scripts/deploy.sh`: Automated deployment
- `scripts/validate-deployment.sh`: Validation checks
- `scripts/rollback.sh`: Automated rollback
- `scripts/health-check.sh`: Health validation

---

**Document Owner**: DevOps Team  
**Last Updated**: 2024-10-15  
**Next Review**: After each launch  
**Version**: 1.0  
**Status**: Active
