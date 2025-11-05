# P018: Deployment Automation & Rollback Guide

**Author:** AI Agent  
**Date:** October 15, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Introduction](#introduction)
2. [Deployment Strategies](#deployment-strategies)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Blue-Green Deployment](#blue-green-deployment)
5. [Canary Deployment](#canary-deployment)
6. [Automatic Rollback](#automatic-rollback)
7. [Database Migrations](#database-migrations)
8. [Deployment Validation](#deployment-validation)
9. [Monitoring & Observability](#monitoring--observability)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [References](#references)

---

## Introduction

This guide documents the automated deployment and rollback systems for the Agente Hotelero IA application. The system provides:

- **Zero-downtime deployments** via blue-green strategy
- **Gradual rollouts** with canary deployments
- **Automatic rollback** on failure detection
- **Safe database migrations** with backup/restore
- **Comprehensive validation** at each step
- **Full observability** of deployment process

### Key Features

✅ **Automated CI/CD Pipeline** (GitHub Actions)  
✅ **Blue-Green Zero-Downtime** deployment  
✅ **Canary with Auto-Promotion** (10% → 100%)  
✅ **Health-Based Auto-Rollback** (<5% error rate)  
✅ **Safe Migrations** with backup  
✅ **Deployment Validation** tests  
✅ **Prometheus Metrics** integration  
✅ **Slack Notifications** on events

---

## Deployment Strategies

### 1. Blue-Green Deployment

**Best for:** Production deployments requiring zero downtime

**How it works:**
1. Deploy new version to inactive environment (green)
2. Run health checks on green environment
3. Switch traffic from blue → green
4. Verify green is handling traffic correctly
5. Decommission old blue environment

**Advantages:**
- Instant rollback (switch traffic back)
- Zero downtime
- Full testing before traffic switch

**Usage:**
```bash
make deploy-staging IMAGE_TAG=myapp:v1.2.3
# or
./scripts/blue-green-deploy.sh --image myapp:v1.2.3 --environment production
```

### 2. Canary Deployment

**Best for:** Gradual rollouts with risk mitigation

**How it works:**
1. Deploy new version alongside stable version
2. Route 10% traffic to canary
3. Monitor metrics (error rate, latency)
4. If healthy: gradually increase to 25%, 50%, 100%
5. If unhealthy: abort and rollback

**Advantages:**
- Gradual risk exposure
- Real-world validation
- Automatic abort on failures

**Usage:**
```bash
make deploy-canary IMAGE_TAG=myapp:v1.2.3
# or
./scripts/canary-deploy.sh --image myapp:v1.2.3 --ramp-stages 10,25,50,100
```

### 3. Rolling Deployment

**Best for:** Kubernetes environments with multiple replicas

**How it works:**
1. Update pods one at a time
2. Wait for each pod to be healthy
3. Continue until all pods updated

**Not yet implemented** (future enhancement)

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/deploy.yml`

**Triggers:**
- Push to `main` → Deploy to staging
- Manual trigger → Deploy to production
- Pull request → Build and test only

**Pipeline Stages:**

```
┌─────────────────────────────────────┐
│  1. Pre-Deployment Checks           │
│     - Version detection             │
│     - Environment determination     │
│     - Deployment gates              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  2. Build & Test                    │
│     - Linting (ruff)                │
│     - Type checking (mypy)          │
│     - Unit tests                    │
│     - Integration tests             │
│     - Coverage report               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  3. Security Scanning               │
│     - Trivy vulnerability scan      │
│     - Secret detection (gitleaks)   │
│     - SARIF upload to GitHub        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  4. Build Docker Image              │
│     - Multi-stage build             │
│     - Tag with version/sha          │
│     - Push to registry              │
│     - Image scanning                │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  5. Deploy to Staging               │
│     - Blue-green deployment         │
│     - Health checks                 │
│     - Smoke tests                   │
└─────────────────────────────────────┘
              ↓ (Manual Approval)
┌─────────────────────────────────────┐
│  6. Deploy to Production            │
│     - Manual approval required      │
│     - Database backup               │
│     - Safe migrations               │
│     - Blue-green or canary          │
│     - Validation                    │
│     - Post-deployment monitoring    │
└─────────────────────────────────────┘
              ↓ (On Failure)
┌─────────────────────────────────────┐
│  7. Automatic Rollback              │
│     - Health detection              │
│     - Rollback to previous          │
│     - Database restore              │
│     - Notification                  │
└─────────────────────────────────────┘
```

### Manual Deployment Trigger

```bash
# Via GitHub CLI
gh workflow run deploy.yml \
  --ref main \
  -f environment=production \
  -f deployment_strategy=blue-green \
  -f skip_tests=false

# Via GitHub UI
# Actions → Automated Deployment Pipeline → Run workflow
```

---

## Blue-Green Deployment

### Script: `scripts/blue-green-deploy.sh`

**Features:**
- Automatic environment detection (blue/green)
- Pre-deployment validation
- Health check with retries
- Traffic switching
- Post-deployment validation
- Automatic cleanup

### Usage Examples

**Basic Deployment:**
```bash
./scripts/blue-green-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --environment staging
```

**Production with Extended Health Checks:**
```bash
./scripts/blue-green-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --environment production \
  --health-check-timeout 600 \
  --traffic-switch-delay 60
```

**Dry Run:**
```bash
./scripts/blue-green-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --environment staging \
  --dry-run
```

**Keep Old Environment:**
```bash
./scripts/blue-green-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --environment production \
  --keep-old
```

### Health Check Process

1. **Container Health** - Docker health command
2. **/health/live** - Basic liveness
3. **/health/ready** - Readiness (DB, Redis, PMS)
4. **/metrics** - Prometheus endpoint
5. **Response Time** - < 1s threshold

### Traffic Switching

The script updates the load balancer configuration to route traffic to the new environment. Implementation is infrastructure-specific (NGINX, AWS ALB, etc.).

---

## Canary Deployment

### Script: `scripts/canary-deploy.sh`

**Features:**
- Gradual traffic ramping
- Real-time metrics comparison
- Automatic promotion or abort
- Configurable thresholds

### Usage Examples

**Standard Canary (10% traffic):**
```bash
./scripts/canary-deploy.sh \
  --image agente-hotel-api:v1.2.3
```

**Custom Ramp with Auto-Promotion:**
```bash
./scripts/canary-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --ramp-stages 10,25,50,75,100 \
  --duration 600 \
  --auto-promote
```

**Immediate Promotion (after validation):**
```bash
./scripts/canary-deploy.sh \
  --image agente-hotel-api:v1.2.3 \
  --promote
```

### Metrics Comparison

The canary deployment compares:

| Metric | Threshold | Decision |
|--------|-----------|----------|
| **Error Rate** | < 5% increase | Abort if exceeded |
| **P95 Latency** | < 3s increase | Abort if exceeded |
| **Availability** | > 95% | Abort if below |

**Source:** Prometheus queries over 5-minute windows

### Abort vs Promote Logic

```
IF canary_error_rate > stable_error_rate + 0.05:
    ABORT and rollback
ELSE IF canary_latency_p95 > stable_latency_p95 + 3s:
    ABORT and rollback
ELSE IF canary_availability < 0.95:
    ABORT and rollback
ELSE:
    PROMOTE to next traffic stage
```

---

## Automatic Rollback

### Script: `scripts/auto-rollback.sh`

**Features:**
- Real-time health monitoring
- Automatic failure detection
- Rollback to last known good version
- State preservation
- Notifications (Slack, email)

### Trigger Conditions

Rollback is triggered when:

1. **Error Rate** > 5% (5xx responses)
2. **P95 Latency** > 3 seconds
3. **Availability** < 95%
4. **Health Checks** failing for > 2 minutes

### Usage Examples

**Automatic Rollback:**
```bash
./scripts/auto-rollback.sh \
  --environment production \
  --preserve-data \
  --notify
```

**Rollback to Specific Version:**
```bash
./scripts/auto-rollback.sh \
  --environment production \
  --rollback-to agente-hotel-api:rollback-20251015-140530
```

**Dry Run:**
```bash
./scripts/auto-rollback.sh \
  --environment staging \
  --dry-run
```

### Rollback Process

1. **Detect Failure** - Monitor Prometheus metrics
2. **Find Rollback Version** - Last known good image
3. **Backup Current State** - Incremental backup
4. **Execute Rollback** - Blue-green deployment with old image
5. **Verify Rollback** - Run smoke tests
6. **Send Notification** - Alert team via Slack

**Time to Rollback:** ~2-3 minutes (blue-green switch)

---

## Database Migrations

### Script: `scripts/safe-migration.sh`

**Features:**
- Automatic backup before migration
- Dry-run validation
- Online migrations (zero downtime)
- Rollback on failure
- Migration verification

### Usage Examples

**Safe Migration (with backup):**
```bash
./scripts/safe-migration.sh \
  --environment production \
  --backup-before \
  --dry-run false \
  --verify
```

**Dry Run (test migration):**
```bash
./scripts/safe-migration.sh \
  --environment staging \
  --backup-before \
  --dry-run true
```

### Migration Checklist

**Before Migration:**
- [ ] Backup database
- [ ] Test migration in staging
- [ ] Review migration SQL
- [ ] Plan rollback strategy
- [ ] Notify team

**During Migration:**
- [ ] Monitor database performance
- [ ] Check for lock timeouts
- [ ] Watch error logs
- [ ] Validate data integrity

**After Migration:**
- [ ] Run smoke tests
- [ ] Verify data
- [ ] Check application logs
- [ ] Monitor for anomalies

---

## Deployment Validation

### Test Suite: `tests/deployment/test_deployment_validation.py`

**Test Categories:**

#### 1. Smoke Tests
- Service reachability
- Health endpoints (/health/live, /health/ready)
- API endpoints responsive
- Database connectivity
- Redis connectivity
- Response time < 1s

#### 2. Integration Tests
- Full health check cycle
- Concurrent health checks
- API availability
- OpenAPI spec validation

#### 3. Rollback Verification
- Service healthy after rollback
- Data integrity preserved
- Performance at baseline

#### 4. Deployment Metrics
- Prometheus metrics available
- Deployment tracking metrics

### Running Tests

**All Deployment Tests:**
```bash
make deploy-test
# or
poetry run pytest tests/deployment/ -v
```

**Smoke Tests Only:**
```bash
poetry run pytest tests/deployment/ -v -m deployment
```

**Rollback Tests:**
```bash
poetry run pytest tests/deployment/ -v -m rollback
```

**After Deployment:**
```bash
make validate-deployment
```

---

## Monitoring & Observability

### Key Metrics

**Deployment Metrics:**
- `deployment_started_total` - Total deployments started
- `deployment_completed_total{status}` - Completed deployments (success/failure)
- `deployment_duration_seconds` - Time to complete deployment
- `rollback_triggered_total` - Total rollbacks

**Application Metrics:**
- `http_requests_total{status}` - Request count by status
- `http_request_duration_seconds` - Request latency histogram
- `up` - Service availability (0 or 1)
- `process_cpu_seconds_total` - CPU usage

### Grafana Dashboards

**Deployment Dashboard** (recommended):
- Deployment timeline
- Success/failure rate
- Rollback frequency
- MTTR (Mean Time To Recovery)
- Traffic split (canary vs stable)

**Application Dashboard** (from P016):
- Request rate and errors
- P95/P99 latency
- Availability SLO
- Resource usage

### Alerts

**Critical Alerts:**
- Deployment failure (→ Slack)
- Rollback triggered (→ Slack + PagerDuty)
- Error rate > 5% (→ Auto-rollback)
- Latency > 3s (→ Auto-rollback)

**Warning Alerts:**
- Deployment duration > 10min
- Health check retries > 5
- Traffic imbalance in canary

---

## Troubleshooting

### Common Issues

#### 1. Deployment Hangs During Health Checks

**Symptoms:** Health checks timeout after 5 minutes

**Possible Causes:**
- Database not reachable
- Redis connection issues
- PMS adapter circuit breaker open
- Application startup errors

**Solution:**
```bash
# Check container logs
make deploy-logs

# Check health endpoint directly
curl http://localhost:8001/health/ready

# Verify dependencies
docker ps | grep -E "postgres|redis"

# Check circuit breaker state
curl http://localhost:8001/metrics | grep circuit_breaker_state
```

#### 2. Traffic Switch Fails

**Symptoms:** NGINX reload fails or 502 errors

**Possible Causes:**
- NGINX configuration syntax error
- Upstream not responding
- Port conflict

**Solution:**
```bash
# Test NGINX config
docker exec nginx nginx -t

# Check upstream health
curl http://agente-api-blue:8000/health/live
curl http://agente-api-green:8000/health/live

# Check port bindings
netstat -tlnp | grep 800[12]
```

#### 3. Rollback Doesn't Restore Service

**Symptoms:** Service still unhealthy after rollback

**Possible Causes:**
- Database corruption
- Redis state issues
- Infrastructure problem (not code)

**Solution:**
```bash
# Check database
make db-health

# Restore from backup
./scripts/restore.sh --target production --backup latest

# Check infrastructure
docker ps -a
docker network ls
```

#### 4. Canary Metrics Not Available

**Symptoms:** Canary deployment fails to collect metrics

**Possible Causes:**
- Prometheus not scraping canary
- Deployment label missing
- Query syntax error

**Solution:**
```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets

# Verify labels on canary
curl http://agente-api-canary:8000/metrics | grep deployment

# Test query manually
curl -G http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=up{deployment="canary"}'
```

---

## Best Practices

### Development

1. **Always test in staging first**
   - Run full deployment in staging
   - Verify all health checks
   - Test rollback procedure

2. **Use semantic versioning**
   - Major.Minor.Patch (e.g., v1.2.3)
   - Tag releases in git
   - Document breaking changes

3. **Write deployment notes**
   - What changed
   - Migration steps
   - Rollback plan
   - Known issues

### Deployment

1. **Schedule deployments during low traffic**
   - Avoid peak hours
   - Consider timezone
   - Have rollback window

2. **Monitor actively during deployment**
   - Watch Grafana dashboards
   - Check error logs
   - Verify metrics

3. **Communicate with team**
   - Announce deployment in Slack
   - Have on-call ready
   - Document any issues

### Rollback

1. **Don't hesitate to rollback**
   - If in doubt, rollback
   - Better safe than sorry
   - Analyze post-mortem

2. **Preserve logs and data**
   - Capture logs before rollback
   - Save metrics snapshots
   - Keep failed deployment for analysis

3. **Understand root cause**
   - Why did deployment fail?
   - How to prevent next time?
   - Update deployment checklist

---

## References

### Internal Documentation

- **P016 - Observability Stack:** Monitoring and alerting setup
- **P017 - Chaos Engineering:** Resilience testing framework
- **OPERATIONS_MANUAL.md:** Operational procedures
- **HANDOVER_PACKAGE.md:** System overview

### External Resources

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Blue-Green Deployment Pattern](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Canary Releases](https://martinfowler.com/bliki/CanaryRelease.html)
- [Database Migrations Best Practices](https://www.braintrust.dev/blog/zero-downtime-migrations)

### Tools & Services

- **GitHub Actions:** CI/CD pipeline
- **Docker:** Containerization
- **Prometheus:** Metrics collection
- **Grafana:** Visualization
- **Slack:** Notifications

---

**Document Version:** 1.0.0  
**Last Updated:** October 15, 2025  
**Maintained By:** DevOps Team  
**Status:** ✅ Production Ready
