#!/usr/bin/env bash
# ============================================================================
# Script: Validate AlertManager SPOF Fix (C1)
# ============================================================================
# Purpose: Send test alert to verify redundant notification channels
# Expected Behavior:
#   ✅ PagerDuty receives incident
#   ✅ Email alert sent to ALERT_EMAIL_TO
#   ✅ Webhook notification to agente-api:8000 (original channel)
#
# Prerequisites:
#   1. PAGERDUTY_INTEGRATION_KEY configured in .env
#   2. SMTP_USERNAME + SMTP_PASSWORD configured (Gmail App Password)
#   3. docker compose up -d (all services running)
#
# Usage: ./scripts/validate-alertmanager-spof-fix.sh
# ============================================================================

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# ============================================================================
# Configuration
# ============================================================================
ALERTMANAGER_URL="http://localhost:9093"
PROMETHEUS_URL="http://localhost:9090"
TEST_ALERT_LABEL="testspoffix_$(date +%s)"

# ============================================================================
# Preflight Checks
# ============================================================================
log_info "Preflight checks..."

# Check if AlertManager is running
if ! curl -sf "${ALERTMANAGER_URL}/-/healthy" > /dev/null 2>&1; then
    log_error "AlertManager not reachable at ${ALERTMANAGER_URL}"
    log_info "Run: docker compose up -d alertmanager"
    exit 1
fi
log_success "AlertManager is healthy"

# Check if Prometheus is running
if ! curl -sf "${PROMETHEUS_URL}/-/healthy" > /dev/null 2>&1; then
    log_error "Prometheus not reachable at ${PROMETHEUS_URL}"
    log_info "Run: docker compose up -d prometheus"
    exit 1
fi
log_success "Prometheus is healthy"

# Check .env for required variables
if [ -f .env ]; then
    log_success ".env file exists"
    
    # Check PagerDuty
    if grep -q "PAGERDUTY_INTEGRATION_KEY=REPLACE_WITH" .env 2>/dev/null; then
        log_error "PAGERDUTY_INTEGRATION_KEY not configured in .env"
        log_warn "Get key from: https://www.pagerduty.com/ → Services → Integrations → Events API v2"
        log_warn "Update .env with real integration key"
        exit 1
    elif ! grep -q "PAGERDUTY_INTEGRATION_KEY=" .env 2>/dev/null; then
        log_warn "PAGERDUTY_INTEGRATION_KEY not found in .env (using default from docker-compose?)"
    else
        log_success "PAGERDUTY_INTEGRATION_KEY configured"
    fi
    
    # Check SMTP
    if grep -q "SMTP_PASSWORD=REPLACE_WITH" .env 2>/dev/null; then
        log_error "SMTP_PASSWORD not configured in .env"
        log_warn "For Gmail: https://support.google.com/accounts/answer/185833"
        log_warn "Create App Password and update .env"
        exit 1
    elif ! grep -q "SMTP_PASSWORD=" .env 2>/dev/null; then
        log_warn "SMTP_PASSWORD not found in .env (using default from docker-compose?)"
    else
        log_success "SMTP_PASSWORD configured"
    fi
else
    log_warn ".env file not found - relying on docker-compose defaults"
fi

# ============================================================================
# Check AlertManager Configuration
# ============================================================================
log_info "Checking AlertManager configuration..."

ALERTMANAGER_CONFIG=$(curl -sf "${ALERTMANAGER_URL}/api/v1/status" | jq -r '.data.config.original' 2>/dev/null || echo "")

if [ -z "$ALERTMANAGER_CONFIG" ]; then
    log_error "Could not retrieve AlertManager config"
    exit 1
fi

# Check for multiple receivers in critical-alerts route
if echo "$ALERTMANAGER_CONFIG" | grep -q "pagerduty_configs:" && \
   echo "$ALERTMANAGER_CONFIG" | grep -q "email_configs:" && \
   echo "$ALERTMANAGER_CONFIG" | grep -q "webhook_configs:"; then
    log_success "SPOF fix confirmed: critical-alerts has 3 channels (PagerDuty + Email + Webhook)"
else
    log_error "SPOF fix NOT applied: critical-alerts missing redundant channels"
    log_warn "Expected: pagerduty_configs, email_configs, webhook_configs"
    log_warn "Check: docker/alertmanager/config.yml"
    exit 1
fi

# ============================================================================
# Send Test Alert
# ============================================================================
log_info "Sending test alert to AlertManager..."

TEST_PAYLOAD=$(cat <<EOF
[
  {
    "labels": {
      "alertname": "TestSPOFFix",
      "severity": "critical",
      "service": "agente-api",
      "test_id": "${TEST_ALERT_LABEL}"
    },
    "annotations": {
      "summary": "SPOF Fix Validation Test Alert",
      "description": "This is a test alert to verify redundant notification channels (PagerDuty + Email + Webhook). If you receive this in multiple channels, the SPOF fix is working correctly."
    },
    "startsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "endsAt": "$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)"
  }
]
EOF
)

RESPONSE=$(curl -sf -X POST \
    -H "Content-Type: application/json" \
    -d "$TEST_PAYLOAD" \
    "${ALERTMANAGER_URL}/api/v1/alerts" || echo "FAILED")

if [ "$RESPONSE" = "FAILED" ]; then
    log_error "Failed to send test alert to AlertManager"
    exit 1
fi

log_success "Test alert sent successfully"

# ============================================================================
# Verify Alert Received
# ============================================================================
log_info "Waiting 5 seconds for alert processing..."
sleep 5

# Check if alert appears in AlertManager
ACTIVE_ALERTS=$(curl -sf "${ALERTMANAGER_URL}/api/v1/alerts" | \
    jq -r --arg test_id "$TEST_ALERT_LABEL" \
    '.data[] | select(.labels.test_id == $test_id) | .status.state' || echo "")

if [ "$ACTIVE_ALERTS" = "active" ]; then
    log_success "Test alert is active in AlertManager"
else
    log_warn "Test alert not found in active alerts (may have been processed quickly)"
fi

# ============================================================================
# Validation Instructions
# ============================================================================
echo ""
log_info "========================================================================"
log_info "MANUAL VALIDATION REQUIRED"
log_info "========================================================================"
echo ""
echo "The test alert 'TestSPOFFix' was sent to AlertManager."
echo ""
echo "✅ Check the following channels for the alert:"
echo ""
echo "1. 🟢 PagerDuty Incident:"
echo "   - Login to https://www.pagerduty.com/"
echo "   - Check Incidents tab for 'SPOF Fix Validation Test Alert'"
echo "   - Expected: New incident with severity 'critical'"
echo ""
echo "2. 📧 Email Alert:"
echo "   - Check inbox for ALERT_EMAIL_TO (from .env)"
echo "   - Subject should contain 'TestSPOFFix'"
echo "   - Expected: Email from AlertManager with alert details"
echo ""
echo "3. 🔗 Webhook Notification:"
echo "   - Check agente-api logs: docker logs agente-api | grep TestSPOFFix"
echo "   - Expected: POST to /webhooks/alerts with alert payload"
echo ""
echo "4. 📊 AlertManager UI:"
echo "   - Open: ${ALERTMANAGER_URL}/#/alerts"
echo "   - Expected: 'TestSPOFFix' alert visible with status 'firing'"
echo ""
log_info "========================================================================"
log_info "If ALL 3 channels received the alert → SPOF fix is SUCCESSFUL ✅"
log_info "If ONLY webhook received alert → SPOF fix FAILED ❌"
log_info "========================================================================"
echo ""

# ============================================================================
# Cleanup Instructions
# ============================================================================
log_info "To silence/resolve the test alert:"
echo "  1. In PagerDuty: Resolve the incident manually"
echo "  2. In AlertManager: Wait 5 minutes for auto-expiry (or restart AlertManager)"
echo ""

# ============================================================================
# Report Summary
# ============================================================================
log_success "Validation script completed"
log_info "Next steps:"
echo "  1. Verify alert in all 3 channels (PagerDuty, Email, Webhook)"
echo "  2. If successful, mark task C1 as COMPLETE in roadmap"
echo "  3. Document PagerDuty Integration Key and Gmail App Password setup in README"
echo "  4. Proceed to C2 (Prometheus rules validation)"
echo ""

exit 0
