# Runbook: Redis Connection Issues

**Severity**: MEDIUM  
**SLA**: 30 minutes to resolution  
**On-Call**: Backend Team + Infrastructure Team

---

## Symptoms

- Cache operations failing
- Rate limiting not working
- Distributed locks failing
- Metric: `redis_up = 0`

## Detection

```promql
# Redis down
redis_up == 0

# High Redis error rate
rate(redis_errors_total[5m]) > 1
```

## Impact Assessment

- **Cache**: Performance degradation (database load increases)
- **Rate Limiting**: Bypass mode (potential abuse)
- **Locks**: Distributed locks unavailable (reservation conflicts)
- **Feature Flags**: Fallback to defaults

---

## Immediate Actions (0-5 minutes)

### 1. Verify Redis Status

```bash
# Check container status
docker ps | grep redis

# Check Redis logs
docker logs redis-agente --tail 50

# Test connection
docker exec redis-agente redis-cli ping
```

### 2. Check Service Degradation

```bash
# Check cache hit rate (should drop to 0%)
curl 'http://localhost:9090/api/v1/query?query=redis_cache_hit_rate'

# Check API still responding (should use cache-miss path)
curl http://localhost:8000/health/ready

# Check for lock errors
docker logs agente-api | grep "lock" | tail -20
```

### 3. Quick Mitigation - Restart Redis

```bash
# Restart Redis container
docker-compose restart redis

# Wait for startup
sleep 5

# Verify connection
docker exec redis-agente redis-cli ping
```

---

## Investigation (5-30 minutes)

### Check Common Causes

#### A. Redis Container Crashed

```bash
# Check exit status
docker ps -a | grep redis

# Check logs for crash
docker logs redis-agente | grep -i "error\|fatal\|crash"

# Check system logs
sudo journalctl -u docker | grep redis | tail -50
```

#### B. Out of Memory

```bash
# Check Redis memory usage
docker exec redis-agente redis-cli info memory

# Check maxmemory setting
docker exec redis-agente redis-cli CONFIG GET maxmemory

# Check eviction policy
docker exec redis-agente redis-cli CONFIG GET maxmemory-policy

# Check for OOM kills
dmesg | grep -i "out of memory" | grep redis
```

#### C. Connection Pool Exhausted

```bash
# Check connected clients
docker exec redis-agente redis-cli INFO clients

# Check max clients
docker exec redis-agente redis-cli CONFIG GET maxclients

# Check connection errors from app
docker logs agente-api | grep "redis.*connection" | tail -20
```

#### D. Network Issues

```bash
# Test connectivity from app container
docker exec agente-api nc -zv redis 6379

# Check Docker network
docker network inspect backend_network | grep redis

# Check for network errors
docker logs redis-agente | grep "network\|connection"
```

#### E. Disk Full (AOF/RDB Issues)

```bash
# Check disk usage
df -h | grep docker

# Check AOF status
docker exec redis-agente redis-cli INFO persistence

# Check for write errors
docker exec redis-agente redis-cli INFO errorstats
```

---

## Resolution Steps

### Option 1: Restart Redis (Fastest)

```bash
# Stop Redis
docker-compose stop redis

# Optional: Clear data if corrupted
# docker volume rm agente-hotel-api_redis_data

# Start Redis
docker-compose up -d redis

# Wait for ready
docker exec redis-agente redis-cli ping

# Verify app reconnects
docker logs -f agente-api | grep redis
```

### Option 2: Increase Memory Limit

```yaml
# docker-compose.yml
services:
  redis:
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    mem_limit: 2g
```

```bash
# Apply changes
docker-compose up -d redis

# Verify settings
docker exec redis-agente redis-cli CONFIG GET maxmemory
```

### Option 3: Fix Connection Pool

```python
# app/core/redis_client.py
redis_pool = redis.asyncio.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    max_connections=50,  # Increase from default
    decode_responses=True,
    socket_keepalive=True,
    socket_keepalive_options={
        socket.TCP_KEEPIDLE: 60,
        socket.TCP_KEEPINTVL: 10,
        socket.TCP_KEEPCNT: 3
    }
)
```

### Option 4: Enable Persistence Recovery

```bash
# If AOF corrupted
docker exec redis-agente redis-check-aof --fix /data/appendonly.aof

# If RDB corrupted
docker exec redis-agente redis-check-rdb /data/dump.rdb

# Restart after fix
docker-compose restart redis
```

---

## Validation

### 1. Test Redis Operations

```bash
# Test SET/GET
docker exec redis-agente redis-cli SET test "hello"
docker exec redis-agente redis-cli GET test
docker exec redis-agente redis-cli DEL test

# Test cache from app
curl http://localhost:8000/api/v1/cache/test

# Test distributed lock
curl -X POST http://localhost:8000/admin/locks/test
```

### 2. Check Metrics

```bash
# Redis uptime
docker exec redis-agente redis-cli INFO server | grep uptime

# Cache hit rate (should recover)
curl 'http://localhost:9090/api/v1/query?query=
  rate(redis_cache_hits_total[5m]) /
  (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m]))
'

# Connection count
docker exec redis-agente redis-cli INFO clients | grep connected_clients
```

### 3. Monitor for Stability

```bash
# Watch Redis stats
watch -n 5 'docker exec redis-agente redis-cli INFO stats'

# Monitor memory
watch -n 5 'docker exec redis-agente redis-cli INFO memory | grep used_memory_human'
```

---

## Communication Template

**Initial Alert**:
```
⚠️ INCIDENT: Redis Connection Issues
Severity: MEDIUM
Status: INVESTIGATING
Impact: Cache unavailable, performance degraded
Mitigation: API operating in cache-bypass mode
ETA: 30 minutes to resolution
```

**Update**:
```
📊 REDIS INCIDENT UPDATE
Status: [INVESTIGATING/RESTARTING/MONITORING]
Root Cause: [OOM/Crash/Network/etc.]
Actions: [Redis restarted/Memory increased/etc.]
Impact: [Cache hit rate recovering, locks restored]
```

**Resolution**:
```
✅ RESOLVED: Redis Connection Restored
Duration: XX minutes
Root Cause: [Detailed explanation]
Fix: [Restart/Configuration change/etc.]
Validation: Cache operations tested, hit rate normal
Performance: API latency back to normal
```

---

## Post-Incident

### 1. Analyze Redis Slowlog

```bash
# Check slow commands
docker exec redis-agente redis-cli SLOWLOG GET 10

# Review command stats
docker exec redis-agente redis-cli INFO commandstats

# Identify expensive operations
docker exec redis-agente redis-cli --bigkeys
```

### 2. Optimize Redis Configuration

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### 3. Add Redis Monitoring

```yaml
# docker/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 4. Implement Graceful Degradation

```python
# app/core/redis_client.py
async def get_with_fallback(key: str):
    try:
        return await redis_client.get(key)
    except RedisError as e:
        logger.warning(f"Redis unavailable: {e}, using fallback")
        return await database.get(key)  # Fallback to DB
```

### 5. Action Items

- [ ] Set up Redis memory alerts (warning at 80%, critical at 90%)
- [ ] Configure Redis persistence (AOF + RDB)
- [ ] Implement connection retry logic
- [ ] Add Redis exporter for detailed metrics
- [ ] Set up automated Redis backups
- [ ] Review cache key patterns for optimization
- [ ] Test failover to read replica

---

## Prevention

- **Monitoring**: Alert on Redis down, high memory, slow commands
- **Limits**: Set maxmemory with appropriate eviction policy
- **Persistence**: Configure AOF for durability
- **Backups**: Daily Redis snapshots
- **Testing**: Monthly Redis failover drills

## Redis Health Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Uptime | 99.9% | < 99.5% | < 99% |
| Memory Usage | < 70% | 80% | 90% |
| Hit Rate | > 80% | < 70% | < 50% |
| Latency | < 1ms | > 5ms | > 10ms |
| Connected Clients | < 80% max | 90% | 100% |

## Redis Commands Reference

```bash
# Info commands
INFO server     # Server info
INFO clients    # Client connections
INFO memory     # Memory usage
INFO stats      # Statistics
INFO persistence # Persistence status

# Diagnostic commands
SLOWLOG GET 10  # Slow queries
CLIENT LIST     # Connected clients
MEMORY DOCTOR   # Memory analysis
DBSIZE          # Key count
```

## Related Runbooks

- [01-database-down.md](./01-database-down.md)
- [03-memory-leak.md](./03-memory-leak.md)

---

**Last Updated**: 2024-10-15  
**Owner**: Backend Team  
**Reviewers**: Infrastructure Team, SRE Team
