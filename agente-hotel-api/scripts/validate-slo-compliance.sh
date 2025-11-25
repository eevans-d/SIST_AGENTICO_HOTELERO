#!/bin/bash

# SLO Compliance Validator
# Validates current system performance against defined SLOs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load guardrails configuration
source "$SCRIPT_DIR/guardrails.conf"

# Configuration
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
SLO_CONFIG_FILE="$SCRIPT_DIR/slo-config.yaml"
REPORT_DIR="$PROJECT_ROOT/reports/slo"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Ensure report directory exists
mkdir -p "$REPORT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🎯 SLO Compliance Validation Suite"
echo "📊 Prometheus URL: $PROMETHEUS_URL"
echo "⏰ Timestamp: $(date)"
echo ""

# Function to query Prometheus
query_prometheus() {
    local query="$1"
    local result
    
    result=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" 2>/dev/null | \
        jq -r '.data.result[0].value[1] // "null"' 2>/dev/null || echo "null")
    
    echo "$result"
}

# Function to check SLO compliance
check_slo() {
    local name="$1"
    local query="$2"
    local threshold="$3"
    local comparison="$4"  # "gt" or "lt"
    local unit="${5:-}"
    
    local current_value
    current_value=$(query_prometheus "$query")
    
    if [ "$current_value" = "null" ]; then
        echo -e "${YELLOW}⚠️  $name: No data available${NC}"
        return 2  # Unknown status
    fi
    
    local status="UNKNOWN"
    local color="$YELLOW"
    local symbol="⚠️"
    
    if [ "$comparison" = "gt" ]; then
        if (( $(echo "$current_value >= $threshold" | bc -l) )); then
            status="✅ PASS"
            color="$GREEN"
            symbol="✅"
        else
            status="❌ FAIL"
            color="$RED"
            symbol="❌"
        fi
    elif [ "$comparison" = "lt" ]; then
        if (( $(echo "$current_value <= $threshold" | bc -l) )); then
            status="✅ PASS"
            color="$GREEN"
            symbol="✅"
        else
            status="❌ FAIL"
            color="$RED"
            symbol="❌"
        fi
    fi
    
    printf "${color}${symbol} %-30s %8.2f%s (target: %s %.2f%s)${NC}\n" \
        "$name:" "$current_value" "$unit" "$comparison" "$threshold" "$unit"
    
    # Return status for summary
    case "$status" in
        *PASS*) return 0 ;;
        *FAIL*) return 1 ;;
        *) return 2 ;;
    esac
}

# Main SLO checks
echo "🎯 === PRIMARY SLOs ==="
echo ""

# Track results
total_checks=0
passed_checks=0
failed_checks=0
unknown_checks=0

# Orchestrator Success Rate
echo "🔄 Orchestrator Service:"
if check_slo "Success Rate (5m)" "orchestrator_success_rate_5m * 100" "99.5" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

if check_slo "Success Rate (30m)" "orchestrator_success_rate_30m * 100" "99.5" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# PMS Adapter Performance
echo "🏨 PMS Adapter Service:"
if check_slo "Response Time P95" "histogram_quantile(0.95, pms_adapter_duration_seconds) * 1000" "500" "lt" "ms"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

if check_slo "Success Rate (5m)" "pms_adapter_success_rate_5m * 100" "99.0" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# WhatsApp Client
echo "📱 WhatsApp Client:"
if check_slo "Message Success Rate" "whatsapp_message_success_rate * 100" "99.9" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# Database Performance
echo "🗄️  Database:"
if check_slo "Availability" "database_up * 100" "99.9" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

if check_slo "Connection Pool Usage" "database_connections_active / database_connections_max * 100" "80" "lt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# Redis Cache
echo "🔄 Redis Cache:"
if check_slo "Hit Ratio" "redis_cache_hit_ratio * 100" "70" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

if check_slo "Availability" "redis_up * 100" "99.5" "gt" "%"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# Secondary SLOs
echo "🎯 === SECONDARY SLOs ==="
echo ""

# Health Checks
echo "🏥 Health Checks:"
if check_slo "Response Time" "health_check_duration_seconds * 1000" "1000" "lt" "ms"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# Audio Processing
echo "🎤 Audio Processing:"
if check_slo "Processing Time P95" "histogram_quantile(0.95, audio_processing_duration_seconds)" "10" "lt" "s"; then
    ((passed_checks++))
else
    case $? in
        1) ((failed_checks++)) ;;
        2) ((unknown_checks++)) ;;
    esac
fi
((total_checks++))

echo ""

# Error Budget Analysis
echo "📊 === ERROR BUDGET ANALYSIS ==="
echo ""

# Calculate error budget consumption
error_budget_used=$(query_prometheus "orchestrator_error_budget_used_ratio_30m * 100")
if [ "$error_budget_used" != "null" ]; then
    if (( $(echo "$error_budget_used <= 50" | bc -l) )); then
        printf "${GREEN}✅ Error Budget Used: %8.2f%% (healthy)${NC}\n" "$error_budget_used"
    elif (( $(echo "$error_budget_used <= 80" | bc -l) )); then
        printf "${YELLOW}⚠️  Error Budget Used: %8.2f%% (monitor closely)${NC}\n" "$error_budget_used"
    else
        printf "${RED}❌ Error Budget Used: %8.2f%% (CRITICAL)${NC}\n" "$error_budget_used"
    fi
else
    echo -e "${YELLOW}⚠️  Error Budget: No data available${NC}"
fi

# Burn rate analysis
fast_burn=$(query_prometheus "orchestrator_burn_rate_fast")
slow_burn=$(query_prometheus "orchestrator_burn_rate_slow")

echo ""
echo "🔥 Burn Rate Analysis:"
if [ "$fast_burn" != "null" ]; then
    if (( $(echo "$fast_burn <= 2" | bc -l) )); then
        printf "${GREEN}✅ Fast Burn Rate (5m): %8.2f (normal)${NC}\n" "$fast_burn"
    elif (( $(echo "$fast_burn <= 4" | bc -l) )); then
        printf "${YELLOW}⚠️  Fast Burn Rate (5m): %8.2f (elevated)${NC}\n" "$fast_burn"
    else
        printf "${RED}❌ Fast Burn Rate (5m): %8.2f (CRITICAL)${NC}\n" "$fast_burn"
    fi
fi

if [ "$slow_burn" != "null" ]; then
    if (( $(echo "$slow_burn <= 1.5" | bc -l) )); then
        printf "${GREEN}✅ Slow Burn Rate (1h): %8.2f (normal)${NC}\n" "$slow_burn"
    else
        printf "${YELLOW}⚠️  Slow Burn Rate (1h): %8.2f (elevated)${NC}\n" "$slow_burn"
    fi
fi

echo ""

# Summary
echo "📋 === COMPLIANCE SUMMARY ==="
echo ""

compliance_percentage=$(( (passed_checks * 100) / total_checks ))

printf "Total Checks: %d\n" "$total_checks"
printf "${GREEN}Passed: %d${NC}\n" "$passed_checks"
printf "${RED}Failed: %d${NC}\n" "$failed_checks"
printf "${YELLOW}Unknown: %d${NC}\n" "$unknown_checks"
printf "Compliance: %d%%\n" "$compliance_percentage"

echo ""

# Overall status
if [ "$failed_checks" -eq 0 ] && [ "$unknown_checks" -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL SLOs COMPLIANT${NC}"
    exit_code=0
elif [ "$failed_checks" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  SLOs COMPLIANT (some metrics unavailable)${NC}"
    exit_code=0
elif [ "$compliance_percentage" -ge 80 ]; then
    echo -e "${YELLOW}⚠️  PARTIAL COMPLIANCE - Monitor closely${NC}"
    exit_code=1
else
    echo -e "${RED}❌ SLO BREACH - Immediate action required${NC}"
    exit_code=2
fi

# Generate detailed report
cat > "$REPORT_DIR/slo-compliance-${TIMESTAMP}.md" << EOF
# SLO Compliance Report

**Generated**: $(date)
**Report ID**: ${TIMESTAMP}

## Summary
- **Total Checks**: ${total_checks}
- **Passed**: ${passed_checks}
- **Failed**: ${failed_checks}
- **Unknown**: ${unknown_checks}
- **Compliance**: ${compliance_percentage}%

## Error Budget Status
- **Used**: ${error_budget_used}%
- **Fast Burn Rate**: ${fast_burn}
- **Slow Burn Rate**: ${slow_burn}

## Recommendations
$(if [ "$failed_checks" -gt 0 ]; then
    echo "- **URGENT**: Address failed SLO checks immediately"
    echo "- Review incident response procedures"
    echo "- Consider enabling circuit breakers or degraded mode"
fi)

$(if [ "$error_budget_used" != "null" ] && (( $(echo "$error_budget_used > 80" | bc -l) )); then
    echo "- **CRITICAL**: Error budget nearly exhausted"
    echo "- Halt all non-critical deployments"
    echo "- Focus on reliability improvements"
fi)

$(if [ "$compliance_percentage" -lt 100 ]; then
    echo "- Monitor failed metrics closely"
    echo "- Consider adjusting SLO targets if consistently unrealistic"
    echo "- Improve monitoring coverage for unknown metrics"
fi)

## Next Steps
1. Address any failed SLO checks
2. Update alerting thresholds if needed
3. Schedule SLO review meeting if compliance < 90%
4. Plan capacity increases if approaching limits

---
*Generated by SLO Compliance Validator*
EOF

echo "📄 Detailed report: $REPORT_DIR/slo-compliance-${TIMESTAMP}.md"
echo ""

exit $exit_code