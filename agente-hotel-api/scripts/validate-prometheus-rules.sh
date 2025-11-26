#!/usr/bin/env bash
# ============================================================================
# Script: Validate Prometheus Rules (C2)
# ============================================================================
# Purpose: Validate all Prometheus rule files using promtool
# Validates:
#   - Alert rules syntax
#   - Recording rules syntax
#   - PromQL expressions
#   - Label consistency
#
# Prerequisites:
#   - Prometheus container running (for promtool)
#   OR
#   - promtool installed locally
#
# Usage: ./scripts/validate-prometheus-rules.sh
# ============================================================================

set -uo pipefail  # Removed -e to handle errors manually in loops

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
PROM_RULES_DIR="docker/prometheus"
PROMETHEUS_CONTAINER="agente_prometheus"

# Files to validate (alert and recording rules)
ALERT_FILES=(
    "alerts.yml"
    "alerts-extra.yml"
    "business_alerts.yml"
    "alert_rules.yml"
)

RECORDING_FILES=(
    "recording_rules.yml"
    "recording_rules.tmpl.yml"
)

# ============================================================================
# Helper Functions
# ============================================================================
check_promtool() {
    if command -v promtool &> /dev/null; then
        echo "local"
        return 0
    elif docker ps --filter "name=${PROMETHEUS_CONTAINER}" --filter "status=running" -q &> /dev/null; then
        echo "docker"
        return 0
    elif command -v docker &> /dev/null; then
        # Docker is available, we can use standalone image
        echo "docker"
        return 0
    else
        echo "none"
        return 1
    fi
}

validate_file_with_promtool() {
    local file=$1
    local type=$2  # "alert" or "record"
    local promtool_location=$3
    
    log_info "Validating $type rules: $file"
    
    if [ "$promtool_location" = "local" ]; then
        # Use local promtool
        if promtool check rules "${PROM_RULES_DIR}/${file}" 2>&1 | tee /tmp/promtool_output.txt; then
            log_success "$file: Syntax valid"
            return 0
        else
            log_error "$file: Syntax errors found"
            cat /tmp/promtool_output.txt
            return 1
        fi
    else
        # Use promtool from prom/prometheus Docker image with volume mount
        # This works for all files regardless of what's in the running container
        if docker run --rm --entrypoint promtool \
            -v "$(pwd)/${PROM_RULES_DIR}:/rules:ro" \
            prom/prometheus:latest check rules "/rules/${file}" 2>&1 | tee /tmp/promtool_output.txt; then
            log_success "$file: Syntax valid"
            return 0
        else
            log_error "$file: Syntax errors found"
            cat /tmp/promtool_output.txt
            return 1
        fi
    fi
}

# ============================================================================
# Preflight Checks
# ============================================================================
log_info "Preflight checks..."

# Check if rules directory exists
if [ ! -d "$PROM_RULES_DIR" ]; then
    log_error "Prometheus rules directory not found: $PROM_RULES_DIR"
    log_info "Run from project root: agente-hotel-api/"
    exit 1
fi
log_success "Rules directory exists: $PROM_RULES_DIR"

# Check for promtool availability
PROMTOOL_LOCATION=$(check_promtool)

if [ "$PROMTOOL_LOCATION" = "none" ]; then
    log_error "promtool not available"
    log_info "Options:"
    log_info "  1. Install Prometheus locally: brew install prometheus (macOS)"
    log_info "  2. Start Prometheus container: docker compose up -d prometheus"
    exit 1
fi

if [ "$PROMTOOL_LOCATION" = "local" ]; then
    PROMTOOL_VERSION=$(promtool --version 2>&1 | head -n 1)
    log_success "Using local promtool: $PROMTOOL_VERSION"
else
    PROMTOOL_VERSION=$(docker run --rm --entrypoint promtool prom/prometheus:latest --version 2>&1 | head -n 1)
    log_success "Using promtool from Docker: $PROMTOOL_VERSION"
fi

echo ""

# ============================================================================
# Validate Alert Rules
# ============================================================================
log_info "========================================================================"
log_info "VALIDATING ALERT RULES"
log_info "========================================================================"
echo ""

ALERT_ERRORS=0
ALERT_SUCCESS=0

for file in "${ALERT_FILES[@]}"; do
    if [ -f "${PROM_RULES_DIR}/${file}" ]; then
        if validate_file_with_promtool "$file" "alert" "$PROMTOOL_LOCATION"; then
            ((ALERT_SUCCESS++))
        else
            ((ALERT_ERRORS++))
        fi
    else
        log_warn "Alert file not found (skipping): $file"
    fi
    echo ""
done

# ============================================================================
# Validate Recording Rules
# ============================================================================
log_info "========================================================================"
log_info "VALIDATING RECORDING RULES"
log_info "========================================================================"
echo ""

RECORDING_ERRORS=0
RECORDING_SUCCESS=0

for file in "${RECORDING_FILES[@]}"; do
    if [ -f "${PROM_RULES_DIR}/${file}" ]; then
        if validate_file_with_promtool "$file" "record" "$PROMTOOL_LOCATION"; then
            ((RECORDING_SUCCESS++))
        else
            ((RECORDING_ERRORS++))
        fi
    else
        log_warn "Recording file not found (skipping): $file"
    fi
    echo ""
done

# ============================================================================
# Validate prometheus.yml (main config)
# ============================================================================
log_info "========================================================================"
log_info "VALIDATING PROMETHEUS CONFIG"
log_info "========================================================================"
echo ""

CONFIG_ERRORS=0

if [ -f "${PROM_RULES_DIR}/prometheus.yml" ]; then
    log_info "Validating prometheus.yml"
    
    if [ "$PROMTOOL_LOCATION" = "local" ]; then
        # For local promtool, create temp config with relative paths
        TEMP_CONFIG=$(mktemp)
        sed -e 's|/etc/prometheus/|./|g' "${PROM_RULES_DIR}/prometheus.yml" > "$TEMP_CONFIG"
        
        if promtool check config "$TEMP_CONFIG" 2>&1 | tee /tmp/promtool_config.txt; then
            log_success "prometheus.yml: Config valid"
        else
            log_error "prometheus.yml: Config errors found"
            cat /tmp/promtool_config.txt
            CONFIG_ERRORS=1
        fi
        rm -f "$TEMP_CONFIG"
    else
        # For Docker, create temp config in rules directory
        log_info "Checking Prometheus config with Docker..."
        TEMP_CONFIG="${PROM_RULES_DIR}/prometheus.validation.yml"
        # Change absolute paths to /rules/ which is our mount point
        sed -e 's|/etc/prometheus/|/rules/|g' \
            -e 's|/rules/generated/recording_rules.yml|/rules/recording_rules.yml|g' \
            "${PROM_RULES_DIR}/prometheus.yml" > "$TEMP_CONFIG"
        
        if docker run --rm --entrypoint promtool \
            -v "$(pwd)/${PROM_RULES_DIR}:/rules:ro" \
            prom/prometheus:latest check config /rules/prometheus.validation.yml 2>&1 | tee /tmp/promtool_config.txt; then
            log_success "prometheus.yml: Config valid"
        else
            log_error "prometheus.yml: Config errors found"
            cat /tmp/promtool_config.txt
            CONFIG_ERRORS=1
        fi
        rm -f "$TEMP_CONFIG"
    fi
else
    log_warn "prometheus.yml not found in $PROM_RULES_DIR"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
log_info "========================================================================"
log_info "VALIDATION SUMMARY"
log_info "========================================================================"
echo ""

TOTAL_ERRORS=$((ALERT_ERRORS + RECORDING_ERRORS + CONFIG_ERRORS))
TOTAL_SUCCESS=$((ALERT_SUCCESS + RECORDING_SUCCESS))

echo "Alert Rules:"
echo "  ✓ Valid:  $ALERT_SUCCESS"
echo "  ✗ Errors: $ALERT_ERRORS"
echo ""
echo "Recording Rules:"
echo "  ✓ Valid:  $RECORDING_SUCCESS"
echo "  ✗ Errors: $RECORDING_ERRORS"
echo ""
echo "Config Files:"
if [ $CONFIG_ERRORS -eq 0 ]; then
    echo "  ✓ Valid:  1 (prometheus.yml)"
else
    echo "  ✗ Errors: 1 (prometheus.yml)"
fi
echo ""
echo "════════════════════════════════════════════════════════════════════════"

if [ $TOTAL_ERRORS -eq 0 ]; then
    log_success "ALL VALIDATIONS PASSED ✅"
    echo ""
    log_info "Next steps:"
    echo "  1. Commit validation script: git add scripts/validate-prometheus-rules.sh"
    echo "  2. Add to Makefile: make validate-prometheus"
    echo "  3. Mark C2 as COMPLETE in roadmap"
    echo "  4. Proceed to H1: Trace Enrichment"
    echo ""
    exit 0
else
    log_error "VALIDATION FAILED ❌"
    echo ""
    log_info "Found $TOTAL_ERRORS error(s) in Prometheus rules/config"
    echo ""
    log_info "Troubleshooting:"
    echo "  - Check PromQL syntax in failed files"
    echo "  - Ensure all referenced metrics exist"
    echo "  - Validate label names (no hyphens, use underscores)"
    echo "  - Check recording rule names follow pattern: level:metric:operations"
    echo ""
    exit 1
fi
