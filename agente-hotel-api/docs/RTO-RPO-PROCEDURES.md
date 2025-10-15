# RTO/RPO Procedures

**Purpose**: Define Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO) for the Agente Hotelero IA system, with detailed procedures for achieving these targets.

---

## Table of Contents

1. [Overview](#overview)
2. [RTO/RPO Definitions](#rtorpo-definitions)
3. [Service Tier Classification](#service-tier-classification)
4. [Backup Strategy](#backup-strategy)
5. [Recovery Procedures](#recovery-procedures)
6. [Testing & Validation](#testing--validation)
7. [Disaster Recovery Plan](#disaster-recovery-plan)

---

## Overview

### Purpose
RTO and RPO objectives ensure that critical business services can be recovered within acceptable timeframes with minimal data loss in the event of a disaster.

### Scope
This document covers all components of the Agente Hotelero IA system:
- API Service (agente-api)
- Database (PostgreSQL)
- Cache (Redis)
- PMS Integration (QloApps)
- Monitoring Stack (Prometheus, Grafana)

### Stakeholders
- **Engineering**: Implements and maintains recovery procedures
- **Operations**: Executes recovery procedures during incidents
- **Management**: Approves RTO/RPO targets and resources
- **Business**: Defines acceptable downtime and data loss

---

## RTO/RPO Definitions

### Recovery Time Objective (RTO)
**Definition**: Maximum acceptable time to restore service after an outage.

**Measurement**: Time from incident detection to full service restoration.

**Example**: If RTO = 1 hour, service must be fully operational within 1 hour of failure.

### Recovery Point Objective (RPO)
**Definition**: Maximum acceptable amount of data loss measured in time.

**Measurement**: Time between last backup and failure.

**Example**: If RPO = 15 minutes, we can lose at most 15 minutes of data.

### Relationship
```
Incident → Detection → Recovery Actions → Service Restored
         ← RPO →      ←    RTO    →
```

---

## Service Tier Classification

### Tier 1 (Critical) - Mission Critical

**Services**: 
- agente-api (API service)
- postgres (Database)
- Core business logic

**Business Impact**: Complete service outage, revenue loss

**RTO**: 1 hour
**RPO**: 15 minutes

**Justification**: 
- Direct revenue impact
- Customer-facing service
- Regulatory requirements

**Recovery Priority**: Highest

---

### Tier 2 (High) - Business Critical

**Services**:
- redis (Cache)
- PMS integration
- WhatsApp integration

**Business Impact**: Degraded service, manual workarounds possible

**RTO**: 4 hours
**RPO**: 1 hour

**Justification**:
- Significant user impact
- Business operations affected
- Temporary workarounds available

**Recovery Priority**: High

---

### Tier 3 (Medium) - Important

**Services**:
- Monitoring (Prometheus, Grafana)
- AlertManager
- Backup systems

**Business Impact**: Reduced visibility, operational inconvenience

**RTO**: 24 hours
**RPO**: 24 hours

**Justification**:
- Operational tools
- No direct user impact
- Can operate without temporarily

**Recovery Priority**: Medium

---

### Tier 4 (Low) - Non-Critical

**Services**:
- Development environments
- Testing infrastructure
- Documentation sites

**Business Impact**: Minimal, no production impact

**RTO**: 1 week
**RPO**: 1 week

**Justification**:
- Non-production services
- No customer impact
- Can be recreated if needed

**Recovery Priority**: Low

---

## Backup Strategy

### Database (PostgreSQL) - Tier 1

#### Backup Schedule
```bash
# Full backup daily at 3:00 AM UTC
0 3 * * * /app/scripts/backup.sh full

# Incremental backup every 4 hours
0 */4 * * * /app/scripts/backup.sh incremental

# Point-in-time recovery (WAL archiving) - continuous
# Configured in postgresql.conf:
# archive_mode = on
# archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
```

#### Backup Retention
- **Full backups**: 30 days
- **Incremental backups**: 7 days
- **WAL archives**: 7 days
- **Off-site copies**: 90 days

#### Backup Validation
```bash
# Automated daily validation
0 4 * * * /app/scripts/validate-backup.sh

# Quarterly restore test to separate environment
# Scheduled via calendar
```

#### Recovery Procedure
```bash
# Quick recovery (from last full backup)
# RTO: ~30 minutes, RPO: up to 24 hours
./scripts/restore.sh backups/postgres-full-latest.tar.gz

# Point-in-time recovery (from WAL)
# RTO: ~1 hour, RPO: up to 15 minutes
./scripts/restore-pitr.sh --target-time "2024-10-15 14:30:00"
```

#### Achieving RPO = 15 minutes
- **Method 1**: WAL archiving every 15 minutes
- **Method 2**: Streaming replication to standby
- **Method 3**: Cloud provider snapshots every 15 minutes

**Recommended**: Combination of Method 1 + Method 2

---

### Redis (Cache) - Tier 2

#### Backup Schedule
```bash
# RDB snapshot every hour
0 * * * * redis-cli BGSAVE

# AOF (Append-Only File) - continuous
# Configured in redis.conf:
# appendonly yes
# appendfsync everysec
```

#### Backup Retention
- **RDB snapshots**: 24 hours (24 files)
- **AOF file**: Rolling, last 48 hours

#### Recovery Procedure
```bash
# Restore from RDB snapshot
# RTO: ~10 minutes, RPO: up to 1 hour
docker cp backups/dump.rdb redis:/data/dump.rdb
docker-compose restart redis

# Restore from AOF
# RTO: ~20 minutes, RPO: up to 1 second
docker cp backups/appendonly.aof redis:/data/appendonly.aof
docker-compose restart redis
```

#### Note on Cache Recovery
- Redis is a cache, not primary data store
- Data can be rebuilt from database if necessary
- Recovery priority lower than database
- **Alternative**: Skip recovery, rebuild cache automatically (RTO: 0, RPO: N/A)

---

### Application Configuration - Tier 1

#### Backup Schedule
```bash
# Version controlled in Git
# All configuration in .env files
# Backed up with application code

# Secrets backed up separately
# Encrypted backups daily
0 2 * * * /app/scripts/backup-secrets.sh
```

#### Recovery Procedure
```bash
# Configuration from Git
git clone https://github.com/org/agente-hotel-api.git
cd agente-hotel-api
git checkout production

# Secrets from encrypted backup
./scripts/restore-secrets.sh backups/secrets-latest.enc

# Deploy
docker-compose up -d
```

---

### PMS Database (QloApps/MySQL) - Tier 2

#### Backup Schedule
```bash
# Full backup daily at 2:00 AM UTC
0 2 * * * /app/scripts/backup-pms.sh

# Binary log backup every 2 hours
0 */2 * * * /app/scripts/backup-pms-binlog.sh
```

#### Backup Retention
- **Full backups**: 30 days
- **Binary logs**: 7 days

#### Recovery Procedure
```bash
# Restore from backup
# RTO: ~2 hours, RPO: up to 2 hours
./scripts/restore-pms.sh backups/qloapps-latest.sql.gz

# Point-in-time recovery from binary logs
./scripts/restore-pms-pitr.sh --target-time "2024-10-15 14:00:00"
```

---

## Recovery Procedures

### Scenario 1: Complete Database Loss

**Symptoms**: Database unavailable, data corruption, accidental deletion

**RTO Target**: 1 hour
**RPO Target**: 15 minutes

**Procedure**:

1. **Assess Damage** (5 minutes)
```bash
# Verify database is truly unrecoverable
docker exec postgres pg_isready
docker logs postgres | grep -i "error\|corruption"

# Check if partial recovery possible
# If yes, attempt repair first
# If no, proceed to full recovery
```

2. **Prepare Recovery Environment** (10 minutes)
```bash
# Stop current database container
docker-compose stop postgres

# Remove corrupted data (if necessary)
docker volume rm agente-hotel-api_postgres_data

# Create new volume
docker volume create agente-hotel-api_postgres_data
```

3. **Restore Latest Backup** (20 minutes)
```bash
# Start fresh database container
docker-compose up -d postgres

# Wait for startup
sleep 30

# Restore from backup
./scripts/restore.sh backups/postgres-full-latest.tar.gz

# Verify basic connectivity
docker exec postgres psql -U agente_user -d agente_db -c "SELECT 1;"
```

4. **Apply WAL Archives (Point-in-Time Recovery)** (15 minutes)
```bash
# Apply WAL archives to recover to specific point
./scripts/restore-pitr.sh --target-time "$(date -u -d '5 minutes ago' +'%Y-%m-%d %H:%M:%S')"

# This recovers data up to 15 minutes ago (RPO target)
```

5. **Validate Recovery** (10 minutes)
```bash
# Verify table counts
docker exec postgres psql -U agente_user -d agente_db -c "
  SELECT schemaname, tablename, 
         (SELECT count(*) FROM pg_tables) as table_count
  FROM pg_tables 
  WHERE schemaname = 'public';
"

# Verify recent data
docker exec postgres psql -U agente_user -d agente_db -c "
  SELECT MAX(created_at) FROM sessions;
  SELECT MAX(created_at) FROM reservations;
"

# Run application smoke tests
make test-smoke
```

6. **Restart Application** (5 minutes)
```bash
# Start application services
docker-compose up -d agente-api

# Verify health
curl http://localhost:8000/health/ready

# Monitor logs
docker logs -f agente-api
```

**Total Time**: ~60 minutes (within RTO)
**Data Loss**: Up to 15 minutes (within RPO)

---

### Scenario 2: Complete Application Failure

**Symptoms**: Application crashed, container won't start, corrupted code

**RTO Target**: 1 hour
**RPO Target**: 0 (no data loss, database intact)

**Procedure**:

1. **Assess Situation** (5 minutes)
```bash
# Check container status
docker ps -a | grep agente-api

# Check logs
docker logs agente-api --tail 100

# Check disk space
df -h

# Check if database is healthy
curl http://localhost:8000/health/ready | jq .database
```

2. **Quick Fix Attempts** (10 minutes)
```bash
# Try restart
docker-compose restart agente-api

# If restart fails, try rebuild
docker-compose build agente-api
docker-compose up -d agente-api

# Check if successful
curl http://localhost:8000/health/ready
```

3. **Rollback to Previous Version** (20 minutes)
```bash
# If rebuild fails, rollback
./scripts/blue-green-deploy.sh --switch-to-previous

# Or manual rollback
PREVIOUS_VERSION=$(git describe --tags --abbrev=0 HEAD~1)
docker pull agente-hotel-api:$PREVIOUS_VERSION
docker-compose up -d agente-api

# Verify
curl http://localhost:8000/health/ready
```

4. **Full Recovery** (if rollback fails) (25 minutes)
```bash
# Clone clean repository
cd /tmp
git clone https://github.com/org/agente-hotel-api.git
cd agente-hotel-api
git checkout $(git describe --tags --abbrev=0)

# Restore configuration
./scripts/restore-secrets.sh

# Deploy fresh
docker-compose build
docker-compose up -d

# Verify
curl http://localhost:8000/health/ready
```

5. **Validate** (5 minutes)
```bash
# Run smoke tests
make test-smoke

# Check critical endpoints
curl -X POST http://localhost:8000/api/v1/pms/availability \
  -H "Content-Type: application/json" \
  -d '{"hotel_id": 1, "check_in": "2024-11-01", "check_out": "2024-11-03"}'

# Monitor metrics
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=up{job="agente-api"}'
```

**Total Time**: ~65 minutes (close to RTO, may need to optimize)
**Data Loss**: 0 minutes (database intact)

---

### Scenario 3: Infrastructure Failure (Complete Data Center Loss)

**Symptoms**: Entire cloud region unavailable, all services down

**RTO Target**: 4 hours (extended due to complexity)
**RPO Target**: 15 minutes (from off-site backups)

**Procedure**:

1. **Activate Disaster Recovery Plan** (15 minutes)
```bash
# Notify stakeholders
./scripts/send-notification.sh "DR activation: primary region down"

# Switch DNS to DR region (pre-configured)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://dr-dns-change.json

# DNS propagation: 5-15 minutes
```

2. **Deploy Infrastructure in DR Region** (60 minutes)
```bash
# Use infrastructure as code
cd terraform/dr-region
terraform init
terraform apply -auto-approve

# This creates:
# - VPC and networking
# - EC2 instances / ECS cluster
# - Load balancers
# - Security groups
```

3. **Restore Database** (90 minutes)
```bash
# Download latest backup from S3
aws s3 cp s3://backups/postgres-latest.tar.gz /tmp/

# Deploy database
docker-compose -f docker-compose.dr.yml up -d postgres

# Restore from backup
./scripts/restore.sh /tmp/postgres-latest.tar.gz

# Apply WAL archives for point-in-time recovery
aws s3 sync s3://backups/wal-archive/ /tmp/wal-archive/
./scripts/restore-pitr.sh --wal-dir /tmp/wal-archive/
```

4. **Deploy Application** (45 minutes)
```bash
# Pull latest Docker images
docker pull agente-hotel-api:latest

# Restore configuration
./scripts/restore-secrets.sh

# Deploy full stack
docker-compose -f docker-compose.dr.yml up -d

# Verify health
curl http://dr-instance/health/ready
```

5. **Validate & Switch Traffic** (30 minutes)
```bash
# Run comprehensive tests
make test-e2e

# Check all integrations
./scripts/test-integrations.sh

# Monitor for 15 minutes
watch -n 30 './scripts/health-check.sh'

# If all good, complete DNS switch (already done in step 1)
# Update status page
curl -X POST https://api.statuspage.io/v1/pages/PAGE_ID/incidents \
  -d '{"incident": {"status": "resolved", "body": "Service restored in DR region"}}'
```

**Total Time**: ~240 minutes (4 hours - within extended RTO)
**Data Loss**: ~15-30 minutes (within acceptable range for DR scenario)

---

## Testing & Validation

### Backup Testing Schedule

| Test Type | Frequency | RTO Validation | RPO Validation |
|-----------|-----------|----------------|----------------|
| Automated Backup Verification | Daily | Yes | Yes |
| Restore to Non-Prod | Weekly | Yes | No |
| Full DR Drill (Database) | Monthly | Yes | Yes |
| Complete DR Drill (All Systems) | Quarterly | Yes | Yes |
| Chaos Engineering Test | Monthly | Yes | No |

### Automated Validation Script

```bash
#!/bin/bash
# scripts/validate-backup.sh

set -e

BACKUP_FILE=$(ls -t backups/postgres-full-*.tar.gz | head -1)
TEST_CONTAINER="postgres-test-$(date +%s)"

echo "Testing backup: $BACKUP_FILE"

# Start test database
docker run -d --name $TEST_CONTAINER \
  -e POSTGRES_USER=agente_user \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=agente_db \
  postgres:15

sleep 10

# Restore backup
docker cp $BACKUP_FILE $TEST_CONTAINER:/tmp/backup.tar.gz
docker exec $TEST_CONTAINER tar -xzf /tmp/backup.tar.gz -C /tmp
docker exec $TEST_CONTAINER psql -U agente_user -d agente_db -f /tmp/backup.sql

# Verify data
RESULT=$(docker exec $TEST_CONTAINER psql -U agente_user -d agente_db -t -c "SELECT COUNT(*) FROM sessions;")

if [ "$RESULT" -gt 0 ]; then
  echo "✅ Backup validation successful"
  VALIDATION_STATUS="success"
else
  echo "❌ Backup validation failed"
  VALIDATION_STATUS="failed"
fi

# Cleanup
docker stop $TEST_CONTAINER
docker rm $TEST_CONTAINER

# Log result
echo "$(date -u +%Y-%m-%d_%H:%M:%S),${BACKUP_FILE},${VALIDATION_STATUS}" >> /var/log/backup-validation.log

# Alert if failed
if [ "$VALIDATION_STATUS" == "failed" ]; then
  ./scripts/send-alert.sh "Backup validation failed for $BACKUP_FILE"
  exit 1
fi

exit 0
```

### Quarterly DR Drill Checklist

- [ ] Schedule drill with team (2 weeks notice)
- [ ] Notify stakeholders (no impact to production)
- [ ] Document start time
- [ ] Simulate failure scenario
- [ ] Execute recovery procedures
- [ ] Time each step
- [ ] Validate recovered data
- [ ] Test all integrations
- [ ] Document lessons learned
- [ ] Update procedures based on findings
- [ ] Measure actual RTO/RPO
- [ ] Compare with targets
- [ ] Create action items for gaps

---

## Disaster Recovery Plan

### DR Readiness Checklist

#### Infrastructure
- [ ] DR region configured in cloud provider
- [ ] Infrastructure as code (Terraform/CloudFormation) tested
- [ ] Network connectivity between regions verified
- [ ] DNS failover configured
- [ ] Load balancer health checks configured

#### Data
- [ ] Off-site backups verified (S3/GCS/Azure Blob)
- [ ] Backup encryption validated
- [ ] Cross-region replication enabled
- [ ] Backup retention policy enforced
- [ ] Recovery procedures documented

#### Application
- [ ] Docker images in multiple registries
- [ ] Configuration secrets backed up
- [ ] Dependencies documented
- [ ] Deployment automation tested
- [ ] Health checks validated

#### Documentation
- [ ] DR procedures documented
- [ ] Contact list updated
- [ ] Escalation path defined
- [ ] Communication templates ready
- [ ] Post-DR validation checklist

#### Team
- [ ] DR roles assigned
- [ ] Team members trained
- [ ] On-call rotation includes DR knowledge
- [ ] External vendors contacted if needed

---

### RTO/RPO Monitoring

#### Metrics to Track

```promql
# Backup age (should be < 24 hours)
time() - last_successful_backup_timestamp_seconds < 86400

# Backup size trend
backup_size_bytes

# Restore test success rate
backup_restore_test_success_total / backup_restore_test_total

# Last restore test time (should be < 7 days)
time() - last_restore_test_timestamp_seconds < 604800
```

#### Alerts

```yaml
# docker/prometheus/alerts.yml

- alert: BackupTooOld
  expr: time() - last_successful_backup_timestamp_seconds > 86400
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "Database backup is more than 24 hours old"

- alert: BackupValidationFailed
  expr: backup_validation_status == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Backup validation failed"

- alert: RestoreTestOverdue
  expr: time() - last_restore_test_timestamp_seconds > 604800
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Restore test not run in over 7 days"
```

---

## Compliance & Audit

### Regulatory Requirements
- **GDPR**: Data backup and recovery procedures documented
- **HIPAA** (if applicable): Encrypted backups, audit logs
- **PCI-DSS** (if applicable): Secure backup storage, access controls

### Audit Trail
```bash
# All backup/restore operations logged
/var/log/backup.log
/var/log/restore.log

# Format: timestamp, operation, user, result, duration
2024-10-15 03:00:01,backup,root,success,1234s
2024-10-15 14:30:15,restore,oncall,success,3456s
```

### Quarterly Compliance Report
- Backup success rate
- Restore test results
- RTO/RPO adherence
- DR drill outcomes
- Action items from tests

---

**Document Owner**: @sre-lead  
**Last Updated**: 2024-10-15  
**Next Review**: 2025-01-15  
**Compliance**: GDPR, ISO 27001
