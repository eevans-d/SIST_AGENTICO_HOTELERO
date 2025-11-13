# AlertManager SPOF Fix - Setup Guide

**Task**: C1 - SPOF AlertManager  
**Priority**: CRITICAL (P0)  
**Effort**: 2h  
**Status**: IMPLEMENTATION COMPLETE ✅ | VALIDATION PENDING ⏳

---

## Overview

### The Problem
All AlertManager notifications were routing through a single webhook to `agente-api:8000`. If the API fails, the entire alerting system goes silent → **cascading failure** (critical alerts never reach oncall team).

### The Solution
Added **redundant notification channels**:
1. **PagerDuty** - External incident management (primary critical path)
2. **Email (SMTP)** - Direct email to oncall (secondary critical path)
3. **Webhook** - Original agente-api endpoint (tertiary, for system automation)

### Impact
- **Before**: 1 failure point → 100% alerting outage
- **After**: 3 independent channels → requires 3 simultaneous failures for outage

---

## Configuration Changes Applied

### 1. AlertManager Config (`docker/alertmanager/config.yml`)

**Critical Alerts Receiver** (severity=critical):
```yaml
- name: 'critical-alerts'
  pagerduty_configs:
    - service_key: '${PAGERDUTY_INTEGRATION_KEY}'
      description: '{{ .CommonAnnotations.summary }}'
      severity: 'critical'
      details:
        firing: '{{ template "slack.default.text" . }}'
        cluster: 'production'
        service: '{{ .GroupLabels.service }}'
  email_configs:
    - to: '${ALERT_EMAIL_TO}'
      from: '${ALERT_EMAIL_FROM}'
      smarthost: '${SMTP_HOST}:${SMTP_PORT}'
      auth_username: '${SMTP_USERNAME}'
      auth_password: '${SMTP_PASSWORD}'
      headers:
        Subject: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
  webhook_configs:
    - url: 'http://agente-api:8000/webhooks/alerts'
      send_resolved: true
```

**Warning Alerts Receiver** (severity=warning):
```yaml
- name: 'warning-alerts'
  email_configs:
    - to: '${ALERT_EMAIL_TO}'
      from: '${ALERT_EMAIL_FROM}'
      smarthost: '${SMTP_HOST}:${SMTP_PORT}'
      auth_username: '${SMTP_USERNAME}'
      auth_password: '${SMTP_PASSWORD}'
      headers:
        Subject: '⚠️  WARNING: {{ .GroupLabels.alertname }}'
  webhook_configs:
    - url: 'http://agente-api:8000/webhooks/alerts'
      send_resolved: true
```

### 2. Environment Variables (`.env.example` updated)

Added new section with comprehensive documentation:
```bash
# ==============================================================================
# Alerting Configuration (FASE 1 - SPOF Fix)
# ==============================================================================
# ✅ CRITICAL: PagerDuty Integration for SPOF fix
# Get Integration Key from: https://www.pagerduty.com/
# Services → Agente Hotelero API → Integrations → Events API v2 → Integration Key
PAGERDUTY_INTEGRATION_KEY=REPLACE_WITH_PAGERDUTY_INTEGRATION_KEY

# ✅ CRITICAL: Email Alerts (Redundancia AlertManager)
# Para AlertManager críticas: oncall-critical@example.com
# Para AlertManager warnings: ops-warnings@example.com
ALERT_EMAIL_TO=ops@yourdomain.com
ALERT_EMAIL_FROM=agente-alerts@yourdomain.com

# SMTP Configuration for Email Alerts
# ⚠️ Gmail: Use App Password (https://support.google.com/accounts/answer/185833)
# NOT your regular Gmail password!
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=REPLACE_WITH_GMAIL_APP_PASSWORD
```

---

## Setup Instructions

### Step 1: Configure PagerDuty (15 minutes)

#### 1.1 Create PagerDuty Account
1. Sign up at https://www.pagerduty.com/ (free trial available)
2. Create a new service: **"Agente Hotelero API - Production"**
3. Set escalation policy (who gets notified and when)

#### 1.2 Get Integration Key
1. Go to: **Services → Agente Hotelero API → Integrations**
2. Click **"New Integration"**
3. Select **"Events API v2"** (NOT v1)
4. Copy the **Integration Key** (format: `R012345ABCDEFGHIJKLMNOP`)

#### 1.3 Add to .env
```bash
# In agente-hotel-api/.env
PAGERDUTY_INTEGRATION_KEY=R012345ABCDEFGHIJKLMNOP
```

**⚠️ Security Note**: Never commit this key to git. It's already in `.gitignore` patterns.

---

### Step 2: Configure Gmail SMTP (10 minutes)

#### 2.1 Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** (required for App Passwords)

#### 2.2 Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select app: **"Mail"**, device: **"Other (Custom name)"**
3. Enter: **"Agente Hotelero AlertManager"**
4. Click **Generate**
5. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

#### 2.3 Add to .env
```bash
# In agente-hotel-api/.env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxxyyyyzzzzwwww  # 16-char App Password (no spaces)
ALERT_EMAIL_TO=oncall@yourdomain.com  # Where alerts should go
ALERT_EMAIL_FROM=agente-alerts@yourdomain.com  # From address
```

**⚠️ Common Mistakes**:
- ❌ Using regular Gmail password → Auth will fail
- ❌ Copying App Password with spaces → Remove spaces
- ❌ Not enabling 2FA → App Passwords option won't appear

---

### Step 3: Restart AlertManager

```bash
cd agente-hotel-api

# Restart AlertManager to load new config
docker compose restart alertmanager

# Verify it started successfully
docker compose logs alertmanager | grep -i "listening"
# Expected: level=info msg="Listening on :9093"

# Check for config errors
docker compose logs alertmanager | grep -i error
# Expected: No output (empty)
```

---

## Validation

### Automated Validation Script

```bash
cd agente-hotel-api

# Run validation script (sends test alert)
./scripts/validate-alertmanager-spof-fix.sh
```

**Expected Output**:
```
ℹ Preflight checks...
✓ AlertManager is healthy
✓ Prometheus is healthy
✓ .env file exists
✓ PAGERDUTY_INTEGRATION_KEY configured
✓ SMTP_PASSWORD configured
ℹ Checking AlertManager configuration...
✓ SPOF fix confirmed: critical-alerts has 3 channels (PagerDuty + Email + Webhook)
ℹ Sending test alert to AlertManager...
✓ Test alert sent successfully
ℹ Waiting 5 seconds for alert processing...
✓ Test alert is active in AlertManager

========================================================================
MANUAL VALIDATION REQUIRED
========================================================================

The test alert 'TestSPOFFix' was sent to AlertManager.

✅ Check the following channels for the alert:

1. 🟢 PagerDuty Incident:
   - Login to https://www.pagerduty.com/
   - Check Incidents tab for 'SPOF Fix Validation Test Alert'
   - Expected: New incident with severity 'critical'

2. 📧 Email Alert:
   - Check inbox for ALERT_EMAIL_TO
   - Subject: 'TestSPOFFix'
   - Expected: Email from AlertManager with alert details

3. 🔗 Webhook Notification:
   - Check agente-api logs: docker logs agente-api | grep TestSPOFFix
   - Expected: POST to /webhooks/alerts with alert payload

4. 📊 AlertManager UI:
   - Open: http://localhost:9093/#/alerts
   - Expected: 'TestSPOFFix' alert visible with status 'firing'

========================================================================
If ALL 3 channels received the alert → SPOF fix is SUCCESSFUL ✅
If ONLY webhook received alert → SPOF fix FAILED ❌
========================================================================
```

### Manual Verification Checklist

- [ ] **PagerDuty**: Incident created with title "SPOF Fix Validation Test Alert"
- [ ] **Email**: Received at `ALERT_EMAIL_TO` address with subject containing "TestSPOFFix"
- [ ] **Webhook**: `docker logs agente-api` shows POST to `/webhooks/alerts` with test alert payload
- [ ] **AlertManager UI**: Alert visible at http://localhost:9093/#/alerts

**Success Criteria**: All 3 channels must receive the test alert within 30 seconds.

---

## Troubleshooting

### PagerDuty Issues

#### "Integration Key Invalid"
```bash
# Check .env has correct format (no quotes, no spaces)
grep PAGERDUTY_INTEGRATION_KEY .env
# Expected: PAGERDUTY_INTEGRATION_KEY=R012345ABCDEFGHIJKLMNOP

# Verify in docker-compose
docker compose config | grep PAGERDUTY_INTEGRATION_KEY
# Should show the actual key (not REPLACE_WITH...)
```

#### "No Incident Created"
1. Check PagerDuty service status: https://status.pagerduty.com/
2. Verify Integration Type is **Events API v2** (not v1)
3. Check AlertManager logs:
   ```bash
   docker compose logs alertmanager | grep -i pagerduty
   # Look for 401 (bad key) or 429 (rate limit)
   ```

---

### Email Issues

#### "SMTP Authentication Failed"
```bash
# Test SMTP connection manually
docker run --rm -it --network agente-hotel-api_default \
  alpine/mail:latest \
  -S smtp=smtp://smtp.gmail.com:587 \
  -S smtp-use-starttls \
  -S smtp-auth=login \
  -S smtp-auth-user=your-email@gmail.com \
  -S smtp-auth-password=xxxxyyyyzzzzwwww \
  -s "Test Alert" \
  -r agente-alerts@yourdomain.com \
  oncall@yourdomain.com <<< "Test message body"
```

**Common Fixes**:
- ✅ Ensure App Password is 16 chars with no spaces
- ✅ Check 2FA is enabled on Google account
- ✅ Verify `SMTP_USERNAME` is full email (not just username)
- ✅ Try regenerating App Password if still failing

#### "Email Not Received"
1. Check spam folder
2. Verify `ALERT_EMAIL_TO` is correct
3. Check AlertManager logs:
   ```bash
   docker compose logs alertmanager | grep -i smtp
   # Look for 535 (auth failed) or 550 (rejected)
   ```

---

### Webhook Issues

#### "Webhook Not Received by agente-api"
```bash
# Check if agente-api is running
docker compose ps agente-api
# Expected: State=Up

# Check agente-api logs for webhook endpoint
docker compose logs agente-api | grep "POST /webhooks/alerts"
# Expected: 200 OK responses

# Verify network connectivity
docker compose exec alertmanager wget -qO- http://agente-api:8000/health/live
# Expected: {"status":"healthy"}
```

---

## Rollback Procedure

If the SPOF fix causes issues, rollback:

```bash
cd agente-hotel-api

# 1. Restore original config
git checkout docker/alertmanager/config.yml

# 2. Restart AlertManager
docker compose restart alertmanager

# 3. Verify original webhook-only behavior
curl -sf http://localhost:9093/api/v1/status | \
  jq '.data.config.original' | \
  grep -c "webhook_configs:"
# Expected: 1 (only webhook, no PagerDuty or Email)
```

**Note**: Rollback removes redundancy. Monitor alerts closely until fix is re-applied.

---

## Monitoring & Maintenance

### Key Metrics to Watch

```promql
# Alert notification success rate (by receiver)
rate(alertmanager_notifications_total{integration=~"pagerduty|email|webhook"}[5m])

# Alert notification failures (by receiver)
rate(alertmanager_notifications_failed_total{integration=~"pagerduty|email|webhook"}[5m])

# AlertManager queue depth (alerts waiting to send)
alertmanager_notification_queue_length
```

### Grafana Dashboard

Create dashboard with panels for:
1. **Notification Success Rate** (by channel: PagerDuty, Email, Webhook)
2. **Notification Latency** (P50, P95, P99 by channel)
3. **Failed Notifications** (count and rate by channel)
4. **Queue Depth** (alerts pending delivery)

---

## Production Checklist

Before deploying to production:

- [ ] PagerDuty Integration Key configured with correct escalation policy
- [ ] Gmail App Password generated (NOT regular password)
- [ ] Test alert verified in all 3 channels (PagerDuty + Email + Webhook)
- [ ] AlertManager UI shows all 3 receivers configured: http://localhost:9093/#/status
- [ ] Prometheus metrics exporting notification stats (check `/metrics`)
- [ ] Grafana dashboard created for notification monitoring
- [ ] Oncall team notified of new PagerDuty service
- [ ] Runbook updated with new alerting architecture
- [ ] .env secrets NOT committed to git (verify: `git status --ignored`)

---

## Next Steps

Once C1 is validated:
1. ✅ Mark task **C1** as COMPLETE in `ROADMAP_FASE_1_REMEDIATION.md`
2. ➡️ Proceed to **C2**: Prometheus Rules Validation (1h effort)
3. 📝 Update `OPERATIONS_MANUAL.md` with new alerting architecture
4. 📊 Create Grafana dashboard for notification monitoring

---

## References

- **PagerDuty Events API v2**: https://developer.pagerduty.com/docs/ZG9jOjExMDI5NTgw-events-api-v2-overview
- **Gmail App Passwords**: https://support.google.com/accounts/answer/185833
- **AlertManager Configuration**: https://prometheus.io/docs/alerting/latest/configuration/
- **SMTP Troubleshooting**: https://support.google.com/a/answer/176600

---

**Last Updated**: 2025-01-17  
**Validated By**: AI Agent (automated validation script)  
**Production Ready**: Pending manual validation of test alert in all 3 channels
