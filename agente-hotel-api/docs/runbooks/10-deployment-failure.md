# Runbook: Deployment Failure

**Severity**: CRITICAL  
**SLA**: 15 minutes to rollback  
**On-Call**: DevOps Team + Backend Team

---

## Symptoms

- Deployment pipeline failed
- New version not responding
- Health checks failing after deployment
- Blue-green switch not completing

## Detection

```bash
# CI/CD pipeline failure
# GitHub Actions workflow status: failed

# Health check failures
curl http://new-instance:8000/health/ready | jq .status
# Status: unhealthy

# Container not starting
docker ps | grep agente-api
# Status: Restarting
```

## Impact Assessment

- **Service Impact**: May be running old version (good) or partially deployed (bad)
- **User Impact**: Depends on deployment strategy (blue-green = no impact)
- **Data Impact**: Database migrations may be in inconsistent state

---

## Immediate Actions (0-5 minutes)

### 1. Assess Deployment State

```bash
# Check which version is live
curl http://localhost:8000/api/v1/version

# Check container status
docker ps -a | grep agente-api

# Check if traffic still on old version (blue-green)
curl http://localhost/api/v1/version  # Via NGINX
```

### 2. Identify Failure Stage

```bash
# Check CI/CD logs
gh workflow view deploy --log

# Or check GitHub Actions web UI
open https://github.com/$REPO/actions

# Identify failure stage:
# - Build failed
# - Tests failed
# - Deploy failed
# - Health check failed
# - Smoke test failed
```

### 3. Immediate Decision

```bash
# If traffic still on old version: SAFE
# - Investigate and fix
# - No user impact

# If traffic on new broken version: CRITICAL
# - Immediate rollback required
```

---

## Investigation (5-15 minutes)

### Check Common Failure Types

#### A. Build Failure

```bash
# Check build logs
docker logs $(docker ps -a | grep agente-api | awk '{print $1}') 2>&1 | grep -i error

# Common issues:
# - Missing dependencies
# - Import errors
# - Configuration errors
# - Environment variables missing

# Verify locally
make docker-build
```

#### B. Test Failure

```bash
# Check test results
pytest --tb=short --last-failed

# Check specific failing tests
cat .github/workflows/deploy.yml | grep "pytest"

# Review test logs from CI/CD
gh run view --log | grep "FAILED"
```

#### C. Database Migration Failure

```bash
# Check migration status
docker exec agente-api alembic current

# Check migration logs
docker logs agente-api | grep "alembic\|migration"

# Check database connectivity
docker exec postgres-agente psql -U agente_user -d agente_db -c "SELECT version();"
```

#### D. Health Check Failure

```bash
# Check health endpoint
curl -v http://localhost:8000/health/ready

# Check detailed health status
curl http://localhost:8000/health/ready | jq .

# Common issues:
# - Database not reachable
# - Redis not reachable
# - PMS not reachable (if check_pms_in_readiness=true)
# - Missing environment variables
```

#### E. Configuration Error

```bash
# Check environment variables
docker exec agente-api env | grep -E "DATABASE|REDIS|PMS|WHATSAPP"

# Verify settings load
docker exec agente-api python -c "
from app.core.settings import settings
print(f'Environment: {settings.environment}')
print(f'Debug: {settings.debug}')
"

# Check for validation errors
docker logs agente-api | grep "ValidationError\|SettingsError"
```

---

## Resolution Steps

### Option 1: Automatic Rollback (Fastest - 2 minutes)

```bash
# Trigger automatic rollback
make rollback

# Or use rollback script directly
./scripts/auto-rollback.sh

# This will:
# 1. Switch NGINX to previous version
# 2. Stop new containers
# 3. Clean up failed deployment
# 4. Verify old version health

# Monitor rollback
watch -n 2 'curl -s http://localhost/api/v1/version'
```

### Option 2: Manual Rollback

```bash
# Identify previous good version
docker images | grep agente-api | head -5

# Get previous version tag
PREVIOUS_VERSION=$(git describe --tags --abbrev=0 HEAD~1)

# Rollback to previous version
docker-compose down agente-api
docker-compose up -d agente-api:$PREVIOUS_VERSION

# Switch NGINX upstream
./scripts/blue-green-deploy.sh --switch-to-previous

# Verify
curl http://localhost/health/ready
```

### Option 3: Fix Forward (If Issue is Minor)

```bash
# For config-only issues, hotfix and redeploy

# Fix configuration
vi agente-hotel-api/.env
# or
vi docker-compose.yml

# Restart with fix
docker-compose restart agente-api

# Verify health
curl http://localhost:8000/health/ready
```

### Option 4: Database Migration Recovery

```bash
# If migration failed mid-way

# Check current migration
docker exec agente-api alembic current

# Downgrade to previous version
docker exec agente-api alembic downgrade -1

# Or restore database backup
./scripts/restore.sh backups/pre-deploy-backup.tar.gz

# Verify database state
docker exec postgres-agente psql -U agente_user -d agente_db -c "\dt"
```

---

## Validation

### 1. Service Health

```bash
# Check health endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Verify version
curl http://localhost:8000/api/v1/version

# Check all dependencies
curl http://localhost:8000/health/ready | jq '.checks'
```

### 2. Run Smoke Tests

```bash
# Automated smoke tests
make test-smoke

# Manual smoke tests
# 1. Check availability
curl -X POST http://localhost:8000/api/v1/pms/availability \
  -H "Content-Type: application/json" \
  -d '{"hotel_id": 1, "check_in": "2024-11-01", "check_out": "2024-11-03"}'

# 2. Test webhook
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# 3. Check metrics
curl http://localhost:8000/metrics | grep http_requests_total
```

### 3. Monitor Metrics

```bash
# Check error rate
curl 'http://localhost:9090/api/v1/query?query=
  rate(http_requests_total{status=~"5.."}[5m])
'

# Check response time
curl 'http://localhost:9090/api/v1/query?query=
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
'

# Monitor for 15 minutes
watch -n 60 'make health'
```

---

## Communication Template

**Initial Alert**:
```
🚨 INCIDENT: Deployment Failure
Severity: CRITICAL
Status: ROLLING BACK
Deployment: [Version/Commit SHA]
Failure Stage: [Build/Test/Deploy/Health Check]
Impact: [No user impact (blue-green) / Service degraded]
Action: Automatic rollback in progress
ETA: 5 minutes to rollback completion
```

**Update**:
```
📊 DEPLOYMENT FAILURE UPDATE
Rollback Status: [In progress/Completed]
Current Version: [Previous stable version]
Root Cause: [Initial diagnosis]
Service Status: [Operational/Degraded]
Next Steps: [Investigation/Fix/Retry]
```

**Resolution**:
```
✅ RESOLVED: Rollback Successful
Duration: XX minutes
Final Version: [Previous stable version]
Root Cause: [Detailed explanation]
Fix Required: [What needs to be fixed]
Redeployment: Planned for [date/time] after fix
```

---

## Post-Incident

### 1. Root Cause Analysis

```bash
# Generate deployment report
python scripts/deployment-analysis.py \
  --deployment-id $DEPLOYMENT_ID \
  --output deployment_failure_report.json

# Review all deployment steps
cat .github/workflows/deploy.yml

# Check pre-flight report
cat .playbook/preflight_report.json
```

### 2. Fix Root Cause

```bash
# Common fixes:

# Missing dependency
poetry add missing-package

# Test failure
# Fix code, ensure tests pass locally
pytest tests/

# Configuration error
# Update .env.example with required variables
# Update settings.py with validation

# Migration issue
# Test migration locally
alembic upgrade head
```

### 3. Add Safeguards

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      # Add pre-deployment validation
      - name: Pre-flight Check
        run: make preflight READINESS_SCORE=8.0
        
      # Add deployment validation
      - name: Post-Deploy Validation
        run: |
          sleep 30  # Wait for startup
          make validate-deployment
          
      # Add automatic rollback trigger
      - name: Rollback on Failure
        if: failure()
        run: make rollback
```

### 4. Update Runbook

```bash
# Add specific failure case to runbook
echo "## New Failure Type: [Description]" >> docs/runbooks/10-deployment-failure.md
echo "### Detection" >> docs/runbooks/10-deployment-failure.md
echo "### Resolution" >> docs/runbooks/10-deployment-failure.md
```

### 5. Action Items

- [ ] Fix root cause of deployment failure
- [ ] Add test for failure scenario
- [ ] Update CI/CD pipeline with learnings
- [ ] Improve pre-flight checks
- [ ] Test deployment in staging
- [ ] Schedule retry deployment
- [ ] Update deployment documentation
- [ ] Review deployment SLOs

---

## Prevention

- **Testing**: Comprehensive test suite (unit, integration, e2e)
- **Pre-flight**: Automated readiness checks before deploy
- **Staging**: Always deploy to staging first
- **Blue-Green**: Zero-downtime deployment strategy
- **Validation**: Post-deployment smoke tests
- **Rollback**: Automatic rollback on health check failure

## Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing locally
- [ ] Pre-flight checks green
- [ ] Staging deployment successful
- [ ] Database migration tested
- [ ] Rollback plan ready

**During Deployment**:
- [ ] Monitor deployment logs
- [ ] Watch health checks
- [ ] Monitor error rates
- [ ] Verify new version responding
- [ ] Run smoke tests

**Post-Deployment**:
- [ ] Validate all endpoints
- [ ] Check metrics for anomalies
- [ ] Monitor for 30 minutes
- [ ] Confirm in Slack #deployments
- [ ] Update deployment log

## Deployment Metrics

| Metric | Target | Warning |
|--------|--------|---------|
| Deployment Success Rate | > 95% | < 90% |
| Rollback Time | < 5 min | > 10 min |
| Deployment Duration | < 15 min | > 30 min |
| Post-Deploy Errors | 0 | > 0 |

## Related Runbooks

- [08-high-error-rate.md](./08-high-error-rate.md)
- [01-database-down.md](./01-database-down.md)

## Additional Resources

- **CI/CD Pipeline**: `.github/workflows/deploy.yml`
- **Deployment Scripts**: `scripts/blue-green-deploy.sh`, `scripts/auto-rollback.sh`
- **Deployment Guide**: `docs/P018-DEPLOYMENT-AUTOMATION-GUIDE.md`
- **Operations Manual**: `docs/OPERATIONS_MANUAL.md`

---

**Last Updated**: 2024-10-15  
**Owner**: DevOps Team  
**Reviewers**: Backend Team, SRE Team
