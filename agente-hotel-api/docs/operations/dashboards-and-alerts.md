# Dashboards, Alertas & Monitoreo

**Objetivo**: Visibilidad completa de la aplicación en producción. Detectar y alertar sobre anomalías antes de que impacten usuarios.

**Stack**: Prometheus (metrics) + Grafana (dashboards) + AlertManager (routing/notifications)

---

## 1. Dashboards Grafana

### 1.1 Dashboard: PMS Integration Health

**URL Local**: http://localhost:3000/d/pms_health  
**Métricas**:
- Circuit breaker state (gauge: 0=closed, 1=open, 2=half-open)
- PMS API latency (histogram p50, p95, p99)
- PMS error rate (counter: 5xx vs timeouts)
- Cache hit ratio (hits / (hits + misses))
- Time to recovery after CB open (recovery_timeout)

**Alertas Associated**:
- `CircuitBreakerOpen`: pms_circuit_breaker_state == 1 for 30s
- `HighPMSLatency`: histogram_quantile(0.95, pms_api_latency_seconds) > 2s
- `PMSErrorRate`: rate(pms_errors_total[5m]) > 0.1  # 10% error rate

**Owner**: Backend Platform Team

---

### 1.2 Dashboard: Orchestrator & NLP

**URL Local**: http://localhost:3000/d/orchestrator  
**Métricas**:
- Intent detection accuracy (intents_detected_total{confidence>0.8} / total)
- Fallback rate (nlp_fallbacks_total / total)
- E2E latency (orchestrator_latency_seconds: p50, p95, p99)
- Messages processed (message_gateway_messages_total)
- Response types (text vs audio vs error)

**Alertas Associated**:
- `LowIntentConfidence`: count(intents_detected{confidence<0.6}) > 100 in 5m
- `HighFallbackRate`: rate(nlp_fallbacks_total[5m]) > 0.2  # >20% fallbacks
- `SlowOrchestrator`: histogram_quantile(0.95, orchestrator_latency_seconds) > 3s

**Owner**: NLP & ML Team

---

### 1.3 Dashboard: HTTP & Rate Limiting

**URL Local**: http://localhost:3000/d/http_health  
**Métricas**:
- Request volume (http_requests_total by endpoint, status)
- Status code distribution (2xx, 4xx, 5xx rates)
- Rate limit violations (http_requests_status_429_total)
- Endpoint latency (http_request_duration_seconds by endpoint)
- Webhook queue depth (if async processing)

**Alertas Associated**:
- `HighErrorRate`: rate(http_requests_total{status=~"5.."}[5m]) > 0.05  # >5% 5xx
- `RateLimitExceeded`: rate(http_requests_status_429_total[5m]) > 10  # >10 429s/min
- `SlowEndpoint`: histogram_quantile(0.95, http_request_duration_seconds{endpoint="/api/webhooks/whatsapp"}) > 2s

**Owner**: DevOps Team

---

### 1.4 Dashboard: Multi-Tenancy & Sessions

**URL Local**: http://localhost:3000/d/tenancy  
**Métricas**:
- Active tenants (tenants_active_total)
- Tenant resolution cache hits (tenant_resolution_total{result="hit"} / total)
- Session count (sessions_active)
- Session lock conflicts (lock_conflicts_total)
- Tenant resolution latency (tenant_resolution_latency_seconds)

**Alertas Associated**:
- `TenantResolutionFailing`: rate(tenant_resolution_total{result="miss_strict"}[5m]) > 0.5
- `SessionLockContention`: rate(lock_conflicts_total[5m]) > 100
- `TenantCacheMissSpike`: rate(tenant_resolution_total{result="miss_strict"}[1m]) > previous 1m by 2x

**Owner**: SRE Team

---

### 1.5 Dashboard: Database & Infrastructure

**URL Local**: http://localhost:3000/d/infra  
**Métricas**:
- PostgreSQL connection pool (pg_connection_pool_usage)
- Redis memory usage (redis_memory_bytes)
- Disk usage (node_filesystem_avail_bytes)
- CPU & memory (node_cpu_seconds_total, node_memory_available_bytes)
- Uptime (up{job="agente-api"})

**Alertas Associated**:
- `DatabaseConnectionPoolExhausted`: pg_connection_pool_usage > 0.9
- `HighMemoryUsage`: node_memory_available_bytes / node_memory_total_bytes < 0.2
- `DiskUsage>80%`: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.8
- `InstanceDown`: up{job="agente-api"} == 0 for 2m

**Owner**: Infrastructure Team

---

## 2. Alert Rules (AlertManager)

**Archivo**: `docker/alertmanager/config.yml`

### 2.1 Alert Grouping & Routing

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: [alertname, severity, job]
  group_wait: 10s          # Wait 10s for alerts to group
  group_interval: 10m      # Re-send grouped alerts every 10m
  repeat_interval: 12h     # Escalate if not resolved in 12h
  
  routes:
    # High-severity incidents → Immediate PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
      group_wait: 0s        # No batching, immediate
      group_interval: 5m
      repeat_interval: 1h

    # Database alerts → Database team + PagerDuty (secondary)
    - match:
        team: database
      receiver: 'database_team'
      group_interval: 5m

    # Rate limiting → On-call + Slack #ops
    - match:
        alertname: RateLimitExceeded
      receiver: 'ops_slack'
      group_interval: 15m

receivers:
  # Default: Slack #alerts
  - name: 'default'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_ALERTS}'
        channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'

  # PagerDuty for critical
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        description: 'Severity: {{ .GroupLabels.severity }}'

  # Database team email
  - name: 'database_team'
    email_configs:
      - to: 'database-team@example.com'
        smarthost: 'smtp.sendgrid.net:587'
        auth_username: 'apikey'
        auth_password: '${SENDGRID_API_KEY}'

  # Slack #ops channel
  - name: 'ops_slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_OPS}'
        channel: '#ops'
```

### 2.2 Alert Definitions (Prometheus)

**Archivo**: `docker/prometheus/alert-rules.yml`

```yaml
groups:
  - name: agente_api
    interval: 30s
    rules:
      # ============ CIRCUIT BREAKER ALERTS ============
      - alert: CircuitBreakerOpen
        expr: pms_circuit_breaker_state{state="open"} == 1
        for: 30s
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "PMS Circuit Breaker OPEN"
          description: "PMS adapter circuit breaker is OPEN. Check PMS health."
          runbook: "docs/operations/incident-pms-down.md"

      - alert: CircuitBreakerHalfOpen
        expr: pms_circuit_breaker_state{state="half_open"} == 1
        for: 1m
        labels:
          severity: info
          team: backend
        annotations:
          summary: "PMS Circuit Breaker HALF_OPEN (recovering)"
          description: "PMS adapter is testing recovery from CB state."

      # ============ API LATENCY ALERTS ============
      - alert: HighPMSLatency
        expr: histogram_quantile(0.95, rate(pms_api_latency_seconds_bucket[5m])) > 2
        for: 2m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "PMS API P95 latency > 2s (current: {{ $value | humanize }}s)"
          description: "PMS adapter is slow. Check PMS service and network."

      - alert: HighOrchestrationLatency
        expr: histogram_quantile(0.95, rate(orchestrator_latency_seconds_bucket[5m])) > 3
        for: 2m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Orchestrator E2E P95 latency > 3s (current: {{ $value | humanize }}s)"
          description: "End-to-end message processing is slow. Check logs for bottlenecks."

      # ============ ERROR RATE ALERTS ============
      - alert: HighHTTPErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 3m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "HTTP 5xx error rate > 5% (current: {{ $value | humanizePercentage }})"
          description: "Service experiencing elevated error rate. Check app logs."
          runbook: "docs/operations/incident-db-down.md"

      - alert: HighPMSErrorRate
        expr: rate(pms_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "PMS error rate > 10% (current: {{ $value | humanizePercentage }})"
          description: "PMS adapter is experiencing errors. Check PMS health & CB state."
          runbook: "docs/operations/incident-pms-down.md"

      # ============ RATE LIMITING ALERTS ============
      - alert: RateLimitExceeded
        expr: rate(http_requests_status_429_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "Rate limit violations > 10/min (current: {{ $value | humanize }})"
          description: "Webhook endpoints are receiving too many requests. Possible DDoS or legitimate spike."
          runbook: "docs/operations/incident-high-traffic.md"

      # ============ DATABASE ALERTS ============
      - alert: DatabaseConnectionPoolExhausted
        expr: pg_connection_pool_usage > 0.9
        for: 1m
        labels:
          severity: critical
          team: database
        annotations:
          summary: "DB connection pool > 90% (current: {{ $value | humanizePercentage }})"
          description: "PostgreSQL connection pool nearly exhausted. May lead to connection refused errors."

      - alert: InstanceDown
        expr: up{job="agente-api"} == 0
        for: 2m
        labels:
          severity: critical
          team: ops
        annotations:
          summary: "Instance DOWN: {{ $labels.instance }}"
          description: "Agente API instance is unreachable for 2+ minutes."

      # ============ NLP/TENANCY ALERTS ============
      - alert: HighFallbackRate
        expr: rate(nlp_fallbacks_total[5m]) / rate(messages_gateway_messages_total[5m]) > 0.2
        for: 5m
        labels:
          severity: warning
          team: nlp
        annotations:
          summary: "NLP fallback rate > 20% (current: {{ $value | humanizePercentage }})"
          description: "Intent detection confidence is low. Review NLP model or training data."

      - alert: TenantResolutionFailing
        expr: rate(tenant_resolution_total{result="miss_strict"}[5m]) > 0.5
        for: 3m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Tenant resolution failures > 50% (current: {{ $value | humanizePercentage }})"
          description: "Dynamic tenant resolution is failing frequently. Check Postgres and cache."

      # ============ INFRASTRUCTURE ALERTS ============
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_available_bytes / node_memory_total_bytes)) > 0.85
        for: 5m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "Memory usage > 85% (current: {{ $value | humanizePercentage }})"
          description: "System memory is running low. Check for memory leaks or increase capacity."

      - alert: DiskUsageHigh
        expr: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.8
        for: 10m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "Disk usage > 80% (current: {{ $value | humanizePercentage }})"
          description: "Disk space is running low. Clean up logs or increase capacity."
```

---

## 3. Slack Integration

### 3.1 Setup Slack Webhooks

**Step 1**: Create Slack App  
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Agente Hotel Alerts"
4. Workspace: your Slack workspace

**Step 2**: Enable Incoming Webhooks
1. Navigate to "Incoming Webhooks"
2. Toggle "Activate Incoming Webhooks" → ON
3. Click "Add New Webhook to Workspace"
4. Select channel (e.g., #alerts, #ops)
5. Copy Webhook URL: `https://hooks.slack.com/services/T.../B.../...`

**Step 3**: Add to Secrets
```bash
# For development
export SLACK_WEBHOOK_ALERTS="https://hooks.slack.com/services/T.../B.../..."
export SLACK_WEBHOOK_OPS="https://hooks.slack.com/services/T.../B.../..."

# For production (GitHub Secrets)
# Add to repo: Settings → Secrets and variables → Actions → New secret
gh secret set SLACK_WEBHOOK_ALERTS --body "https://hooks.slack.com/services/..."
```

### 3.2 Slack Alert Message Format

AlertManager automatically formats:

```
🚨 Alert: CircuitBreakerOpen
Severity: warning
Service: agente-api

PMS Circuit Breaker OPEN. Check PMS health.

Time: 2025-10-25T14:30:00Z
Dashboard: http://localhost:3000/d/pms_health
Runbook: docs/operations/incident-pms-down.md
```

---

## 4. PagerDuty Integration (Critical Only)

### 4.1 Setup PagerDuty

**Step 1**: Create Integration  
1. Go to https://app.pagerduty.com/services
2. Click "New Service"
3. Name: "Agente Hotel API"
4. Escalation Policy: (select on-call rotation)
5. Integration: "Prometheus"

**Step 2**: Obtain Service Key
1. Service page → "Integrations"
2. Copy Integration Key (looks like: `P...`)

**Step 3**: Add to Secrets
```bash
gh secret set PAGERDUTY_SERVICE_KEY --body "P..."
```

### 4.2 Alert Severity Mapping

| Prometheus Severity | PagerDuty Severity | Action |
|---|---|---|
| critical | critical | Page on-call engineer immediately |
| warning | warning | Create incident, notify team |
| info | info | Log, no notification |

---

## 5. Health Check Endpoint

**Endpoint**: `GET /health/metrics`  
**Purpose**: Expone métricas en formato Prometheus

```bash
curl http://localhost:8002/health/metrics | grep pms_circuit_breaker_state
# Output:
# pms_circuit_breaker_state{state="closed"} 0.0
# pms_circuit_breaker_state_total 150
```

---

## 6. Dashboard Setup (Manual or Grafana-as-Code)

### 6.1 Manual Setup (via UI)

1. **Access Grafana**: http://localhost:3000 (admin/admin)
2. **Add Data Source**: 
   - Configuration → Data Sources → New
   - Type: Prometheus
   - URL: http://prometheus:9090
   - Save & Test

3. **Import Dashboards**:
   - Dashboards → Browse → Import
   - Upload JSON files from repo

4. **Create Alerts**:
   - Grafana Alerts → New Alert Rule
   - Configure thresholds, notifications

### 6.2 Grafana-as-Code (Provisioning)

**File**: `docker/grafana/provisioning/dashboards/dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'Agente Hotel Dashboards'
    orgId: 1
    folder: 'Production'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/json
```

**Dashboard JSON**: `docker/grafana/provisioning/dashboards/json/pms_health.json`

```json
{
  "dashboard": {
    "title": "PMS Integration Health",
    "panels": [
      {
        "title": "Circuit Breaker State",
        "targets": [
          {
            "expr": "pms_circuit_breaker_state"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},      # 0=closed (green)
                {"color": "yellow", "value": 1},     # 2=half_open (yellow)
                {"color": "red", "value": 2}         # 1=open (red)
              ]
            }
          }
        }
      }
    ]
  }
}
```

---

## 7. Canary Gating (Optional SLO Checks)

**Purpose**: Prevent deploying if metrics are bad

**File**: `.github/workflows/deploy-fly.yml` (new step after smoke test)

```yaml
      - name: SLO Validation (Canary Gating)
        if: success()
        run: |
          # Query Prometheus: P95 latency increase should be <10%
          BASELINE_P95=$(curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(orchestrator_latency_seconds_bucket{env='staging'}[5m]))" \
            | jq '.data.result[0].value[1]' -r)
          
          CANARY_P95=$(curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(orchestrator_latency_seconds_bucket{env='production'}[5m]))" \
            | jq '.data.result[0].value[1]' -r)
          
          # Check if increase is >10%
          INCREASE=$(echo "scale=4; (($CANARY_P95 - $BASELINE_P95) / $BASELINE_P95) * 100" | bc)
          
          if (( $(echo "$INCREASE > 10" | bc -l) )); then
            echo "❌ SLO FAILED: P95 increased by ${INCREASE}%"
            exit 1
          else
            echo "✅ SLO PASSED: P95 increase only ${INCREASE}%"
          fi
```

---

## 8. Monitoring Checklist

### 8.1 Before Production Deploy

- [ ] All 5 dashboards configured (PMS, Orchestrator, HTTP, Multi-Tenancy, Infra)
- [ ] Alert rules loaded in Prometheus
- [ ] AlertManager routes configured (Slack, PagerDuty, email)
- [ ] Slack webhooks working (test message sent)
- [ ] PagerDuty integration tested (test incident created + resolved)
- [ ] Health endpoints returning metrics: `/health/metrics`, `/health/live`, `/health/ready`
- [ ] Prometheus scraping all endpoints successfully (Targets page shows green)
- [ ] Grafana data source connected + test query working

### 8.2 Post-Deploy Validation

- [ ] Production dashboards showing live data
- [ ] No spam alerts (thresholds validated on production traffic)
- [ ] Slack/PagerDuty notifications delivering within 1 min
- [ ] Team knows escalation path (who to page, when to escalate)
- [ ] Runbooks accessible from alerts (embedded links)

### 8.3 Ongoing Monitoring

- [ ] Weekly: Review alert noise → tune thresholds
- [ ] Monthly: Validate dashboard accuracy → update if queries stale
- [ ] Quarterly: Incident simulation drill → verify runbooks work
- [ ] Annually: Capacity planning → project growth trends

---

## 9. Quick Commands

```bash
# Check Prometheus scrape status
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets'

# Query metric from CLI
curl 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result'

# Test Slack webhook
curl -X POST "$SLACK_WEBHOOK_ALERTS" \
  -H 'Content-Type: application/json' \
  -d '{"text":"✅ Test alert from Agente Hotel"}'

# View AlertManager status
curl http://localhost:9093/api/v1/status | jq '.status'

# Trigger test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "labels": {"alertname": "TestAlert", "severity": "warning"},
      "annotations": {"summary": "This is a test alert"}
    }]
  }'
```

---

**Last Updated**: 2025-10-25  
**Maintained By**: SRE & Backend Teams  
**Review Frequency**: Monthly
