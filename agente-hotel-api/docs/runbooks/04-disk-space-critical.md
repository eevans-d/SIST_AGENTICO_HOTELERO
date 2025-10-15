# Runbook: Disk Space Critical

**Severity**: CRITICAL  
**SLA**: 15 minutes to mitigation  
**On-Call**: Infrastructure Team + Backend Team

---

## Symptoms

- Disk usage > 90%
- Container write failures
- Database errors: "No space left on device"
- Log rotation failures

## Detection

```bash
# Disk usage check
df -h | awk '$5 > 90 {print $0}'
```

```promql
# Prometheus alert
node_filesystem_avail_bytes{mountpoint="/"} / 
node_filesystem_size_bytes{mountpoint="/"} < 0.1
```

## Impact Assessment

- **Critical**: Service failure, data loss risk
- **Database**: Cannot write new data
- **Logs**: Cannot write logs, debugging impaired
- **Backups**: Cannot create backups

---

## Immediate Actions (0-5 minutes)

### 1. Identify Disk Usage

```bash
# Check overall usage
df -h

# Find large directories
du -sh /* | sort -hr | head -10

# Find large files
find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | head -20
```

### 2. Quick Space Recovery

```bash
# Clear Docker unused resources
docker system prune -af --volumes
docker volume prune -f

# Clear old logs
sudo journalctl --vacuum-time=1d

# Clear apt cache
sudo apt-get clean
```

### 3. Emergency Log Truncation

```bash
# Truncate large log files (keep last 1000 lines)
for log in /var/log/*.log; do
    tail -1000 "$log" > "$log.tmp" && mv "$log.tmp" "$log"
done

# Clear Docker container logs
sudo sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'
```

---

## Investigation (5-15 minutes)

### Check Common Causes

#### A. Log Files Growing

```bash
# Find largest log files
find /var/log -type f -exec du -h {} + | sort -rh | head -20

# Check Docker logs
du -sh /var/lib/docker/containers/*/* | sort -hr | head -10

# Application logs
ls -lSh logs/ | head -10
```

#### B. Database Growth

```bash
# PostgreSQL database size
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT pg_size_pretty(pg_database_size('agente_db'));
"

# Table sizes
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  SELECT schemaname, tablename, 
         pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables 
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
  LIMIT 10;
"
```

#### C. Docker Images/Volumes

```bash
# Docker disk usage
docker system df -v

# Old images
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | sort -k3 -hr

# Unused volumes
docker volume ls -qf dangling=true
```

#### D. Backup Files

```bash
# Find backup files
find / -name "*.backup" -o -name "*.bak" -o -name "*.sql.gz" 2>/dev/null | xargs du -sh

# Old backups
ls -lh /backups/ | head -20
```

---

## Resolution Steps

### Option 1: Cleanup Logs (Fastest)

```bash
# Rotate and compress logs
sudo logrotate -f /etc/logrotate.conf

# Clear old rotated logs
find /var/log -name "*.gz" -mtime +7 -delete
find /var/log -name "*.1" -mtime +3 -delete

# Truncate Docker logs
sudo sh -c 'echo "" > /var/lib/docker/containers/*/*-json.log'
```

### Option 2: Cleanup Docker Resources

```bash
# Remove all stopped containers
docker container prune -f

# Remove unused images
docker image prune -af

# Remove unused volumes
docker volume prune -f

# Remove build cache
docker builder prune -af
```

### Option 3: Archive Old Data

```bash
# Archive old database records
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '90 days';
  DELETE FROM lock_audit WHERE created_at < NOW() - INTERVAL '30 days';
  VACUUM FULL;
"

# Archive old backups
tar -czf /backups/archive-$(date +%Y%m).tar.gz /backups/*.sql.gz
rm /backups/*.sql.gz
```

### Option 4: Increase Disk Space

```bash
# Resize volume (cloud provider)
aws ec2 modify-volume --volume-id vol-xxx --size 100

# Extend filesystem
sudo resize2fs /dev/xvda1

# Verify
df -h
```

---

## Validation

### 1. Check Disk Usage

```bash
# Verify space freed
df -h

# Check inodes
df -i

# Verify services running
docker ps
```

### 2. Test Write Operations

```bash
# Test database write
docker exec postgres-agente psql -U agente_user -d agente_db -c "
  INSERT INTO sessions (id, tenant_id, data) 
  VALUES (gen_random_uuid(), 'test', '{}');
"

# Test log write
echo "Test log entry" | docker exec -i agente-api tee -a /app/logs/test.log
```

### 3. Monitor for Recurrence

```bash
# Watch disk usage
watch -n 60 df -h

# Check growth rate
du -sh /var/lib/docker/containers
```

---

## Communication Template

**Initial Alert**:
```
🚨 INCIDENT: Critical Disk Space
Severity: CRITICAL
Status: MITIGATING
Usage: XX% (Critical threshold: 90%)
Impact: Write operations may fail
Action: Clearing logs and unused Docker resources
```

**Update**:
```
📊 DISK SPACE UPDATE
Current Usage: XX% (was YY%)
Freed: XGB
Actions: [What was cleaned]
Status: [Safe/Still cleaning/Need more space]
```

**Resolution**:
```
✅ RESOLVED: Disk Space Normal
Final Usage: XX% (target: <80%)
Freed: XGB total
Actions: [Summary of cleanup]
Prevention: [Monitoring/Automation added]
```

---

## Post-Incident

### 1. Implement Log Rotation

```yaml
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 2. Automated Cleanup Script

```bash
# scripts/disk-cleanup.sh
#!/bin/bash
# Run daily via cron

# Docker cleanup
docker system prune -f --volumes --filter "until=24h"

# Log cleanup
find /var/log -name "*.gz" -mtime +7 -delete

# Old backups
find /backups -name "*.tar.gz" -mtime +30 -delete
```

### 3. Add Monitoring

```bash
# Add to prometheus alerts
- alert: DiskSpaceWarning
  expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.2
  for: 5m
  labels:
    severity: warning

- alert: DiskSpaceCritical
  expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
  for: 1m
  labels:
    severity: critical
```

### 4. Action Items

- [ ] Implement automated log rotation
- [ ] Set up daily cleanup cron job
- [ ] Configure Docker log limits
- [ ] Set up disk usage alerts (warning at 80%, critical at 90%)
- [ ] Review data retention policies
- [ ] Plan capacity increase if needed

---

## Prevention

- **Monitoring**: Alert at 80% (warning), 90% (critical)
- **Automation**: Daily cleanup scripts
- **Limits**: Docker log rotation configured
- **Retention**: 30-day policy for logs, 90-day for data
- **Capacity**: Monthly growth review

## Disk Usage Targets

| Usage | Action |
|-------|--------|
| < 70% | Normal |
| 70-80% | Review growth trends |
| 80-90% | Schedule cleanup |
| 90-95% | Immediate cleanup |
| > 95% | Emergency response |

## Related Runbooks

- [01-database-down.md](./01-database-down.md)
- [10-deployment-failure.md](./10-deployment-failure.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Infrastructure Team  
**Reviewers**: Backend Team, SRE Team
