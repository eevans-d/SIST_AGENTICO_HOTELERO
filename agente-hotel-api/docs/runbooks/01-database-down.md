# Runbook: Database Down or Degraded

**Severity**: CRITICAL  
**SLA**: 15 minutes to resolution  
**On-Call**: Database Team + Backend Team

---

## Symptoms

- API returns 500 errors
- Health check `/health/ready` fails with database connection errors
- Logs show: `asyncpg.exceptions.CannotConnectNowError`
- Metric: `up{job="postgres"}` = 0

## Detection

```promql
# Prometheus alert
up{job="postgres"} < 1
```

## Impact Assessment

- **User Impact**: Complete service outage, no reservations possible
- **Data Risk**: High (potential data loss if write operations in progress)
- **Revenue Impact**: $500/hour estimated loss

---

## Immediate Actions (0-5 minutes)

### 1. Verify Database Status

```bash
# Check container status
docker ps | grep postgres

# Check database logs
docker logs postgres-agente

# Try manual connection
docker exec -it postgres-agente psql -U agente_user -d agente_db
```

### 2. Check Recent Changes

```bash
# Check recent deployments
git log --since="2 hours ago" --oneline

# Check configuration changes
git diff HEAD~5 docker-compose.yml
```

### 3. Escalate if Down

- Alert database team via PagerDuty
- Post in #incidents Slack channel
- Notify stakeholders using incident communication template

---

## Investigation (5-15 minutes)

### Check Common Issues

#### A. Container Crashed
```bash
# Restart container
docker-compose restart postgres

# Verify startup
docker logs -f postgres-agente
```

#### B. Disk Space Full
```bash
# Check disk usage
df -h

# Check PostgreSQL data directory
docker exec postgres-agente du -sh /var/lib/postgresql/data
```

#### C. Connection Pool Exhausted
```bash
# Check active connections
docker exec postgres-agente psql -U agente_user -d agente_db -c "SELECT count(*) FROM pg_stat_activity;"

# Check max connections
docker exec postgres-agente psql -U agente_user -d agente_db -c "SHOW max_connections;"
```

#### D. Configuration Error
```bash
# Validate postgresql.conf
docker exec postgres-agente cat /var/lib/postgresql/data/postgresql.conf

# Check for syntax errors
docker exec postgres-agente postgres -C config_file
```

---

## Resolution Steps

### Option 1: Restart (Fastest - 2 minutes)

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api
docker-compose restart postgres

# Wait for health check
make health

# Verify API connectivity
curl http://localhost:8000/health/ready
```

### Option 2: Restore from Backup (5-10 minutes)

```bash
# List recent backups
ls -lth backups/

# Restore latest backup
./scripts/restore.sh backups/backup-YYYYMMDD.tar.gz

# Verify data integrity
docker exec postgres-agente psql -U agente_user -d agente_db -c "SELECT count(*) FROM sessions;"
```

### Option 3: Rebuild Container (10-15 minutes)

```bash
# Stop and remove container
docker-compose down postgres

# Remove volume (CAUTION: DATA LOSS)
docker volume rm agente-hotel-api_postgres_data

# Recreate with backup restore
docker-compose up -d postgres
./scripts/restore.sh backups/backup-latest.tar.gz
```

---

## Validation

### 1. Health Checks
```bash
# Check database health
docker exec postgres-agente pg_isready

# Check API health
curl http://localhost:8000/health/ready | jq .
```

### 2. Smoke Tests
```bash
# Run smoke tests
make test-smoke

# Check metrics
curl http://localhost:9090/api/v1/query?query=up{job="postgres"}
```

### 3. Monitor Logs
```bash
# Watch for errors
docker logs -f postgres-agente | grep ERROR

# Monitor API logs
docker logs -f agente-api | grep database
```

---

## Communication Template

**Initial Alert (within 5 minutes)**:
```
🚨 INCIDENT: Database Connectivity Issue
Severity: CRITICAL
Status: INVESTIGATING
Impact: Full service outage
ETA: Investigating, update in 10 minutes
```

**Update Template**:
```
📊 INCIDENT UPDATE: Database Issue
Status: [INVESTIGATING/IDENTIFIED/MONITORING]
Progress: [Description of actions taken]
Next Steps: [What we're doing next]
ETA: [Estimated time to resolution]
```

**Resolution Notice**:
```
✅ INCIDENT RESOLVED: Database Issue
Duration: XX minutes
Root Cause: [Brief description]
Actions Taken: [What we did]
Follow-up: Post-mortem scheduled for [date/time]
```

---

## Post-Incident

### 1. Create Post-Mortem
```bash
make post-mortem
# Fill out template with incident details
```

### 2. Action Items
- [ ] Review database monitoring alerts
- [ ] Verify backup restoration process
- [ ] Check connection pool settings
- [ ] Update runbook based on learnings
- [ ] Schedule team retrospective

### 3. Metrics to Track
- Time to detection (target: < 1 minute)
- Time to resolution (target: < 15 minutes)
- Data loss (target: 0 records)
- Similar incidents in last 30 days

---

## Prevention

- **Monitoring**: Enable proactive alerts for connection pool usage
- **Capacity**: Review max_connections setting monthly
- **Backups**: Verify automated backups daily
- **Testing**: Run DR drills quarterly
- **Documentation**: Keep connection strings in secrets manager

## Related Runbooks

- [02-high-api-latency.md](./02-high-api-latency.md)
- [07-redis-connection-issues.md](./07-redis-connection-issues.md)
- [10-deployment-failure.md](./10-deployment-failure.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: Database Team, SRE Team
