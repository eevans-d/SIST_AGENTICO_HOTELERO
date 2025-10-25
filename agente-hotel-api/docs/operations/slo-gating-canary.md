# SLO Gating & Canary Deployment

**Objetivo**: Automatizar validación de SLOs (Service Level Objectives) antes de desplegar a producción. Detectar regresiones de performance/confiabilidad sin impactar usuarios.

**Estrategia**: Canary deployment a región aislada (staging) con métricas baseline vs canary; gate deploy si regresiones detectadas.

---

## 1. SLO Definitions

### 1.1 SLOs por Service

| Métrica | Objetivo | Umbral Alerta | Owner |
|---|---|---|---|
| **Availability** | 99.95% (4h 43m downtime/mes) | < 99.9% en 5m | SRE |
| **P95 Latency** | ≤ 2.0s (orchestrator E2E) | > 2.5s | Backend |
| **Error Rate** | ≤ 0.5% (5xx) | > 1% en 5m | Backend |
| **PMS Integration** | Circuit Breaker recovery < 30s | CB open > 1m | Integration |
| **Cache Hit Ratio** | ≥ 80% (availability queries) | < 70% | DevOps |
| **Rate Limit Rejects** | < 1% of legitimate traffic | > 10 rejects/min | Ops |

### 1.2 Error Budget

**Monthly Error Budget**: 100% - 99.95% = 0.05% = ~22 minutes downtime/mes

**Consumption**:
- Planned maintenance: 5 min → 23% of budget
- Incidents (PMS down, 5min): 5 min → 23% of budget
- **Remaining**: ~12 minutes for unplanned incidents

**Decision Rule**: If error budget < 10%, pause new feature deploys; focus on stability

---

## 2. Canary Deployment Strategy

### 2.1 Pre-Deploy Checks (GitHub Actions)

**When**: Before deploying to production  
**Where**: GitHub Actions in `deploy-fly.yml`  
**Inputs**: Baseline metrics (previous 15 min) + Canary metrics (current staging)

```yaml
name: SLO Gating - Pre-Deploy Validation

jobs:
  slo_validation:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch Baseline Metrics (Production, last 15 min)
        run: |
          # Query Prometheus in production
          # P95 latency, error rate, CB state
          
          BASELINE_P95=$(curl -s "http://prometheus.prod:9090/api/v1/query_range?query=histogram_quantile(0.95,rate(orchestrator_latency_seconds_bucket[5m]))&start=$(date -u -d '15 minutes ago' +%s)&end=$(date -u +%s)&step=60" \
            | jq '.data.result[0].values[-1][1]' -r)
          
          BASELINE_ERROR_RATE=$(curl -s "http://prometheus.prod:9090/api/v1/query_range?query=rate(http_requests_total{status=~\"5..\"}[5m])&start=$(date -u -d '15 minutes ago' +%s)&end=$(date -u +%s)&step=60" \
            | jq '.data.result[0].values[-1][1]' -r)
          
          echo "BASELINE_P95=$BASELINE_P95" >> $GITHUB_ENV
          echo "BASELINE_ERROR_RATE=$BASELINE_ERROR_RATE" >> $GITHUB_ENV

      - name: Fetch Canary Metrics (Staging, after deploy)
        run: |
          # Wait for staging to stabilize
          sleep 30
          
          CANARY_P95=$(curl -s "http://prometheus.staging:9090/api/v1/query?query=histogram_quantile(0.95,rate(orchestrator_latency_seconds_bucket[5m]))" \
            | jq '.data.result[0].value[1]' -r)
          
          CANARY_ERROR_RATE=$(curl -s "http://prometheus.staging:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])" \
            | jq '.data.result[0].value[1]' -r)
          
          echo "CANARY_P95=$CANARY_P95" >> $GITHUB_ENV
          echo "CANARY_ERROR_RATE=$CANARY_ERROR_RATE" >> $GITHUB_ENV

      - name: Compare & Gate
        run: |
          #!/bin/bash
          set -e
          
          echo "📊 SLO Comparison Report"
          echo "========================"
          echo ""
          
          # P95 Latency Check (allow 10% increase)
          P95_INCREASE=$(echo "scale=2; (($CANARY_P95 - $BASELINE_P95) / $BASELINE_P95) * 100" | bc -l)
          echo "P95 Latency:"
          echo "  Baseline: ${BASELINE_P95}s"
          echo "  Canary:   ${CANARY_P95}s"
          echo "  Increase: ${P95_INCREASE}%"
          
          if (( $(echo "$P95_INCREASE > 10" | bc -l) )); then
            echo "  ❌ FAILED: Increase > 10% threshold"
            exit 1
          else
            echo "  ✅ PASSED"
          fi
          
          echo ""
          
          # Error Rate Check (allow 100% increase or max 1%)
          ERROR_INCREASE=$(echo "scale=2; (($CANARY_ERROR_RATE - $BASELINE_ERROR_RATE) / ($BASELINE_ERROR_RATE + 0.0001)) * 100" | bc -l)
          echo "Error Rate:"
          echo "  Baseline: ${BASELINE_ERROR_RATE}%"
          echo "  Canary:   ${CANARY_ERROR_RATE}%"
          echo "  Increase: ${ERROR_INCREASE}%"
          
          if (( $(echo "$CANARY_ERROR_RATE > 0.01" | bc -l) )); then
            echo "  ❌ FAILED: Error rate > 1% absolute threshold"
            exit 1
          elif (( $(echo "$ERROR_INCREASE > 100" | bc -l) )); then
            echo "  ❌ FAILED: Increase > 100%"
            exit 1
          else
            echo "  ✅ PASSED"
          fi
          
          echo ""
          echo "🟢 All SLOs passed. OK to deploy to production."

      - name: Abort Deploy if SLO Failed
        if: failure()
        run: |
          echo "❌ SLO validation failed. Blocking production deploy."
          echo "Action required: Review regression, fix code, retry."
```

### 2.2 Traffic Routing (Canary %)

**Phase 1 (Canary 5%)**: Route 5% traffic → Wait 10 min, monitor

```bash
# Fly.io canary config (if scaling to multiple machines)
# flyctl scale count --vm=shared 1 # primary (95%)
# flyctl scale count --vm=shared 1 # canary (5%)
# Use Fly regions or Nginx upstream to split traffic
```

**Phase 2 (Canary 25%)**: If no errors, increase to 25%

**Phase 3 (Canary 100%)**: Complete rollout if stable for 30 min

---

## 3. Automated SLO Checks in CI/CD

### 3.1 Pre-Merge (PR) Checks

**When**: Pull request submitted  
**Check**: Unit test coverage + linting (lightweight)

```yaml
name: PR Checks

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Unit Tests
        run: make test
      - name: Check Coverage (min 70%)
        run: |
          COVERAGE=$(make test-coverage | grep "TOTAL" | awk '{print $4}' | tr -d '%')
          if (( $(echo "$COVERAGE < 70" | bc -l) )); then
            echo "❌ Coverage $COVERAGE% < 70% required"
            exit 1
          fi
```

### 3.2 Pre-Deploy (Main Branch) Checks

**When**: Merge to main (before deploy)  
**Checks**: Integration tests + SLO baselines

```yaml
name: Pre-Deploy Validation

on:
  push:
    branches: [main]

jobs:
  slo_baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build & Deploy to Staging
        run: |
          flyctl deploy -a agente-hotel-api-staging
          sleep 30
      
      - name: Smoke Tests
        run: |
          for i in {1..10}; do
            curl -f http://agente-hotel-api-staging.fly.dev/health/ready && break || sleep 6
          done
      
      - name: Integration Tests (5 min)
        run: make test-integration-quick
      
      - name: Load Test (30 RPS, 1 min)
        run: |
          # Use k6 or ghz for load testing
          docker run -v $PWD:/tests \
            loadimpact/k6 run /tests/tests/load/baseline.js \
            --vus 10 --duration 60s \
            --out csv=baseline-results.csv
      
      - name: Capture Baseline Metrics
        run: |
          # Save baseline to artifact for comparison during canary
          curl -s "http://prometheus.staging:9090/api/v1/query_range?query=..." > baseline-metrics.json
          
      - uses: actions/upload-artifact@v3
        with:
          name: baseline-metrics
          path: baseline-metrics.json
```

### 3.3 Canary Deployment Step

**When**: Triggered manually or after PR merge  
**Duration**: 30-45 minutes total

```yaml
name: Canary Deploy

on:
  workflow_dispatch:

jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Download Baseline Metrics
        uses: actions/download-artifact@v3
        with:
          name: baseline-metrics

      - name: Phase 1: Deploy Canary (5%)
        run: |
          # Scale secondary machine
          flyctl scale count --vm=shared 1 -a agente-hotel-api-canary
          flyctl deploy -a agente-hotel-api-canary
          sleep 30
          
          # Route 5% traffic via DNS or load balancer
          # (Detailed config depends on setup)

      - name: Phase 1: Monitor (10 min)
        run: |
          # Continuous validation
          for i in {1..60}; do
            ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\",job=\"canary\"}[1m])" \
              | jq '.data.result[0].value[1]' -r)
            
            if (( $(echo "$ERROR_RATE > 0.05" | bc -l) )); then
              echo "❌ Canary error rate too high: $ERROR_RATE. Rollback!"
              flyctl deploy -a agente-hotel-api  # Redeploy primary
              exit 1
            fi
            
            echo "✅ Canary OK (error rate: $ERROR_RATE)"
            sleep 10
          done

      - name: Phase 2: Increase to 25%
        run: |
          # Scale additional machines or adjust routing
          sleep 10

      - name: Phase 2: Monitor (10 min)
        run: |
          # Same validation loop
          sleep 600

      - name: Phase 3: Full Rollout
        run: |
          # Promote canary to primary
          echo "🟢 Promoting canary to production (100%)"
          flyctl scale count --vm=shared 2 -a agente-hotel-api
          # Keep canary running for quick rollback

      - name: Post-Deployment SLO Report
        run: |
          # Generate report
          cat > /tmp/slo_report.md <<EOF
          # Deployment SLO Report
          
          ## Deployment Details
          - SHA: ${{ github.sha }}
          - Time: $(date)
          - Duration: 45 min (Phase 1: 10m + Phase 2: 10m + Phase 3: 25m)
          
          ## Results
          - Canary 5%: ✅ PASSED (error rate < 0.5%, P95 latency stable)
          - Canary 25%: ✅ PASSED
          - Full Rollout: ✅ SUCCESS
          
          ## Metrics
          - P95 Latency: 1.8s → 1.9s (+5.6%)
          - Error Rate: 0.2% → 0.25% (+25%)
          - Cache Hit Ratio: 82% (stable)
          
          ## Links
          - Production Dashboard: http://localhost:3000/d/pms_health
          - Prometheus: http://localhost:9090
          - Logs: flyctl logs -a agente-hotel-api
          EOF
          
          # Post to Slack
          curl -X POST "${{ secrets.SLACK_WEBHOOK_OPS }}" \
            -H 'Content-Type: application/json' \
            -d @/tmp/slo_payload.json
```

---

## 4. Rollback Strategy

### 4.1 Automatic Rollback Triggers

**Condition 1: Error Rate Spike**
```
Error rate > 1% for 2 consecutive checks (every 10s)
→ Immediately rollback to previous version
```

**Condition 2: P95 Latency Spike**
```
P95 latency > 3.0s (baseline + 50%) for 1 min
→ Manually decide (auto not recommended, could be network)
```

**Condition 3: Circuit Breaker Open (PMS Down)**
```
CB state = "open" for > 5 min
→ If caused by canary change, rollback
→ If not, escalate to PMS team
```

### 4.2 Manual Rollback Procedure

```bash
#!/bin/bash
# scripts/rollback-deploy.sh

set -e

echo "🔄 Initiating rollback..."

# Get previous version (git tag or Fly release)
PREVIOUS_VERSION=$(git describe --tags --abbrev=0 | tail -1)

echo "Rolling back to version: $PREVIOUS_VERSION"

# Redeploy previous version
flyctl deploy -a agente-hotel-api \
  --image ghcr.io/eevans-d/agente-hotel-api:$PREVIOUS_VERSION

# Validate
sleep 30
curl -f https://agente-hotel-api.fly.dev/health/ready || {
  echo "❌ Rollback health check failed"
  exit 1
}

echo "✅ Rollback complete. Version: $PREVIOUS_VERSION"
echo ""
echo "Post-Rollback Actions:"
echo "1. Verify all dashboards green: http://localhost:3000"
echo "2. Check logs for errors: flyctl logs -a agente-hotel-api"
echo "3. Notify #ops-incidents on Slack"
echo "4. Create incident post-mortem"
```

---

## 5. SLO Dashboard & Reporting

### 5.1 SLO Status Dashboard

**URL**: http://localhost:3000/d/slo_compliance  
**Widgets**:
- Monthly SLO achievement (%) vs target
- Error budget burn rate (%)
- Availability timeline (daily)
- P95 latency trend (last 30 days)
- Deployment frequency + success rate

### 5.2 Weekly SLO Report

**Frequency**: Every Monday 09:00 UTC  
**Distribution**: Slack #sre-reports + email leadership

```markdown
# SLO Compliance Report - Week of Oct 21-27

## Summary
- **Availability**: 99.96% ✅ (Target: 99.95%)
- **P95 Latency**: 1.9s ✅ (Target: ≤2.0s)
- **Error Rate**: 0.3% ✅ (Target: ≤0.5%)
- **Error Budget Remaining**: 45 min / 22 min available

## Incidents
- Oct 23, 14:30: PMS timeout (5 min). Cause: QloApps maintenance.
- Oct 25, 11:00: High traffic spike (rate limit exceeded). Cause: Marketing campaign.

## Deployments
- 3 deployments this week
- Success rate: 100%
- Avg canary duration: 38 min
- 0 rollbacks

## Forecasting
- At current burn rate, error budget depleted by Nov 15
- Recommendation: Focus on stability next sprint
```

### 5.3 Quarterly Review

**Frequency**: End of Q  
**Review Committee**: SRE + Backend + Ops leads

**Agenda:**
1. Actual SLO achievement vs target
2. Incident trends + root causes
3. Capacity + growth projections
4. SLO adjustments for next quarter (if warranted)
5. Toil reduction initiatives

---

## 6. Setup Checklist

### 6.1 Prerequisites

- [ ] Prometheus + Grafana running and scraping metrics
- [ ] AlertManager configured with Slack webhooks
- [ ] Two Fly.io apps: `agente-hotel-api` (prod) + `agente-hotel-api-staging` (canary)
- [ ] GitHub Secrets: `PROMETHEUS_PROD_URL`, `PROMETHEUS_STAGING_URL`
- [ ] Baseline metrics captured (before first canary)

### 6.2 Configuration

- [ ] SLO thresholds documented: `docs/operations/slo-gating.md`
- [ ] Canary deployment workflow created: `.github/workflows/canary-deploy.yml`
- [ ] Baseline metrics artifact persisted (GitHub Actions)
- [ ] Rollback script tested: `scripts/rollback-deploy.sh`
- [ ] SLO dashboard configured in Grafana

### 6.3 Testing

- [ ] Canary deploy workflow tested (dry-run)
- [ ] Metrics collection validated (prometheus targets all green)
- [ ] SLO thresholds validated on current production traffic (no false positives)
- [ ] Slack notification tested (via AlertManager test alert)
- [ ] Team trained on runbook

---

## 7. Common SLO Violations & Fixes

| Violation | Likely Cause | Fix |
|---|---|---|
| **High P95 Latency** | DB query N+1, missing index | Add index, paginate results |
| **High Error Rate** | PMS timeout, circuit breaker open | Scale PMS, adjust CB thresholds |
| **Cache Hit Ratio < 70%** | Cache eviction, TTL too short | Increase cache size/TTL, monitor evictions |
| **Rate Limit Spikes** | DDoS or legitimate spike | Whitelist IPs, scale machines, activate CAPTCHA |

---

## 8. References

- **Error Budget**: https://sre.google/workbook/error-budgets/
- **Canary Deployments**: https://martinfowler.com/bliki/CanaryRelease.html
- **SLO Best Practices**: https://sre.google/workbook/slo-document-and-rating/

---

**Last Updated**: 2025-10-25  
**Maintained By**: SRE Team  
**Review Frequency**: Quarterly
