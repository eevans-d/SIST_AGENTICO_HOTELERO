# Alert Validation Guide - Staging Environment

## Overview

Este documento describe el proceso de validación de las 8 nuevas alertas añadidas en el audit de Fases 1-3.

**Alertas a validar**:
- **Session Alerts** (4): SessionsHighWarning, SessionsHighCritical, SessionLeakDetected, SessionCleanupFailures
- **Lock Service Alerts** (4): LockConflictsHigh, LockConflictsCritical, LockExtensionsExceeded, LockOperationsFailureRate

## Prerequisites

1. **Staging environment running** con todos los servicios:
   ```bash
   cd agente-hotel-api
   docker compose -f docker-compose.staging.yml up -d
   ```

2. **Python dependencies**:
   ```bash
   pip install aiohttp requests prometheus-api-client
   ```

3. **Access to Prometheus**:
   - URL: `http://localhost:9090` (local)
   - URL: `http://staging-prometheus.hotelero.local:9090` (remote staging)

## Validation Methods

### Method 1: Automated Script (Recommended)

**Script**: `scripts/validate-alerts-staging.py`

**Basic execution**:
```bash
python scripts/validate-alerts-staging.py \
  --prometheus-url http://localhost:9090 \
  --api-url http://localhost:8002
```

**Output**: `.playbook/alert_validation_report.json`

**Example report**:
```json
{
  "timestamp": "2025-11-08T08:00:00",
  "total_alerts_tested": 8,
  "alerts": {
    "SessionsHighWarning": {
      "tested": true,
      "threshold_exceeded": false,
      "alert_firing": false,
      "current_value": 42,
      "status": "PASS"
    },
    ...
  },
  "summary": {
    "passed": 6,
    "failed": 0,
    "pending": 0,
    "skipped": 2
  }
}
```

### Method 2: Manual Validation via Prometheus UI

1. **Access Prometheus**: `http://localhost:9090`

2. **Check alert status**:
   - Navigate to **Status > Rules**
   - Filter by group: `session_alerts` or `lock_alerts`
   - Verify alert definitions loaded correctly

3. **Query current metrics**:
   ```promql
   # Session metrics
   session_active_total
   deriv(session_active_total[30m])
   increase(session_cleanup_total{result="error"}[1h])
   
   # Lock metrics
   sum(rate(lock_conflicts_total[5m]))
   sum(rate(lock_extensions_total{result="max_reached"}[5m]))
   sum(rate(lock_operations_total{result!="success"}[5m])) / sum(rate(lock_operations_total[5m]))
   ```

4. **Check firing alerts**:
   - Navigate to **Alerts**
   - Filter by state: `Pending`, `Firing`
   - Verify alert annotations (summary, description, runbook_url)

### Method 3: Manual Load Generation

**Generate session load** (to trigger SessionsHighWarning):
```bash
# Using load testing tool (k6, locust, etc.)
k6 run --vus 150 --duration 15m tests/load/session_load.js

# Or using curl in loop
for i in {1..150}; do
  curl -X POST http://localhost:8002/api/webhooks/whatsapp \
    -H "Content-Type: application/json" \
    -d "{\"from\": \"test_user_$i\", \"body\": \"hola\"}" &
done
```

**Generate lock conflicts** (to trigger LockConflictsHigh):
```bash
# Concurrent reservation requests for same dates
for i in {1..100}; do
  curl -X POST http://localhost:8002/api/webhooks/whatsapp \
    -H "Content-Type: application/json" \
    -d "{\"from\": \"test_user_$i\", \"body\": \"reservar 2025-12-20 a 2025-12-22\"}" &
done
```

## Validation Checklist

### Session Alerts

- [ ] **SessionsHighWarning** (>100 sessions for 10m)
  - **Expected**: Warning alert fires when sustained >100 active sessions
  - **Validation**: Query `session_active_total`, generate load if needed
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **SessionsHighCritical** (>200 sessions for 5m)
  - **Expected**: Critical alert fires when sustained >200 active sessions
  - **Validation**: Query `session_active_total`, typically SKIP in staging
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **SessionLeakDetected** (deriv >0.5/min for 1h)
  - **Expected**: Warning alert fires on sustained growth
  - **Validation**: Query `deriv(session_active_total[30m])`, requires 1h observation
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **SessionCleanupFailures** (>3 errors/hour)
  - **Expected**: Warning alert fires on cleanup task failures
  - **Validation**: Query `increase(session_cleanup_total{result="error"}[1h])`
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

### Lock Service Alerts

- [ ] **LockConflictsHigh** (>0.5 conflicts/sec for 10m)
  - **Expected**: Warning alert fires on high conflict rate
  - **Validation**: Query `sum(rate(lock_conflicts_total[5m]))`
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **LockConflictsCritical** (>2 conflicts/sec for 5m)
  - **Expected**: Critical alert fires on very high conflict rate
  - **Validation**: Same query, higher threshold
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **LockExtensionsExceeded** (>0.2 max_reached/sec for 10m)
  - **Expected**: Warning alert fires when locks frequently hit max extensions
  - **Validation**: Query `sum(rate(lock_extensions_total{result="max_reached"}[5m]))`
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

- [ ] **LockOperationsFailureRate** (>10% failures for 10m)
  - **Expected**: Warning alert fires on high failure rate
  - **Validation**: Query failure rate calculation
  - **Status**: ✅ PASS / ⏸️ SKIP / ❌ FAIL

## Expected Results

### Baseline (No Load)

With normal staging traffic:
- `session_active_total`: 0-50 sessions
- `lock_conflicts_total` rate: 0-0.1 conflicts/sec
- `session_cleanup_total{result="error"}`: 0 errors/hour
- `lock_operations_total` failure rate: <1%

**Expected alert state**: All alerts INACTIVE

### With Synthetic Load

After generating 150 concurrent sessions:
- `session_active_total`: 100-150 sessions
- **SessionsHighWarning**: Should fire after 10 minutes
- Other alerts: Remain inactive (thresholds not exceeded)

### Production-Only Tests

Some alerts require production-level load:
- **SessionsHighCritical** (>200 sessions): Typically SKIP in staging
- **SessionLeakDetected** (1h sustained growth): Requires long observation period

## Troubleshooting

### Alert not firing despite threshold exceeded

**Possible causes**:
1. **`for` duration not met**: Alert requires sustained condition (e.g., 10m for SessionsHighWarning)
2. **Prometheus scrape interval**: Default 15s, metrics may have delay
3. **Alert evaluation interval**: Default 1m, check `/api/v1/rules` for last evaluation

**Solution**:
```bash
# Check alert state
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname == "SessionsHighWarning")'

# Check evaluation interval
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name == "session_alerts")'
```

### Metrics not available

**Possible causes**:
1. Service not instrumented yet (metrics never exposed)
2. Prometheus not scraping target
3. Metric name changed

**Solution**:
```bash
# Check targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job == "agente-api")'

# Search for metric
curl http://localhost:9090/api/v1/label/__name__/values | jq '.data[] | select(contains("session_"))'
```

### High false positive rate

**Possible causes**:
1. Thresholds too aggressive for staging environment
2. Cleanup task not running (sessions accumulate)
3. Lock TTL too short (excessive extensions)

**Solution**: Adjust thresholds in `docker/prometheus/alerts.yml` and reload:
```bash
docker compose -f docker-compose.staging.yml exec prometheus kill -HUP 1
```

## Acceptance Criteria

✅ **PASS**: Alert validation successful if:
1. All 8 alerts loaded in Prometheus (`/api/v1/rules`)
2. Alert definitions syntactically correct (no eval errors)
3. Baseline metrics within expected ranges (no false positives)
4. Alerts fire correctly when thresholds artificially triggered
5. Alert annotations complete (summary, description, runbook_url, dashboard)

⏸️ **SKIP**: Acceptable for production-only tests:
- SessionsHighCritical (requires 200+ sessions)
- SessionLeakDetected (requires 1h observation)

❌ **FAIL**: Requires investigation if:
- Alert not loaded in Prometheus
- Metrics not exposed (target down)
- False positives under normal load
- Alert doesn't fire when threshold exceeded for required duration

## Next Steps

After successful validation:
1. **Document thresholds** in runbooks (Point 5)
2. **Create Grafana dashboard** with alert panels (Point 6)
3. **Configure AlertManager** routing (email/Slack notifications)
4. **Schedule regular validation** (weekly in staging, monthly in production)

## Related Documentation

- **Alert definitions**: `docker/prometheus/alerts.yml` (lines 298-378)
- **Metrics implementation**: `app/services/session_manager.py`, `app/services/lock_service.py`
- **Runbooks** (pending): `docs/runbooks/SESSION_ALERTS.md`, `docs/runbooks/LOCK_ALERTS.md`
