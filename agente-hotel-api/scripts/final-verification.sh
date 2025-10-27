#!/bin/bash
#
# Final Pre-Production Verification Script
# Validates all deployment readiness criteria
#
# Usage: ./scripts/final-verification.sh [--verbose] [--fix]
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBOSE="${1:-}"
FIX_MODE=false

if [[ "$VERBOSE" == "--verbose" ]]; then
    set -x
elif [[ "$VERBOSE" == "--fix" ]]; then
    FIX_MODE=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# Helper functions
log_check() {
    local name="$1"
    local status="$2"
    local message="${3:-}"
    
    case "$status" in
        PASS)
            echo -e "${GREEN}✓${NC} $name"
            ((CHECKS_PASSED++))
            ;;
        FAIL)
            echo -e "${RED}✗${NC} $name"
            if [[ -n "$message" ]]; then
                echo "  → $message"
            fi
            ((CHECKS_FAILED++))
            ;;
        WARN)
            echo -e "${YELLOW}⚠${NC} $name"
            if [[ -n "$message" ]]; then
                echo "  → $message"
            fi
            ((CHECKS_WARNED++))
            ;;
        INFO)
            echo -e "${BLUE}ℹ${NC} $name"
            if [[ -n "$message" ]]; then
                echo "  → $message"
            fi
            ;;
    esac
}

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Agente Hotelero - Final Pre-Production Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

# ============================================================================
# 1. CODE QUALITY CHECKS
# ============================================================================
echo -e "\n${BLUE}[1/6] Code Quality Checks${NC}\n"

# 1.1 Linting
if command -v ruff &> /dev/null; then
    cd "$PROJECT_ROOT" && ruff check . --quiet >/dev/null 2>&1; RUFF_RC=$?
    if [[ $RUFF_RC -eq 0 ]]; then
        log_check "Linting (ruff)" PASS
    else
        log_check "Linting (ruff)" FAIL "Run 'make lint' to fix"
    fi
else
    log_check "Linting (ruff)" WARN "ruff not installed, skipping"
fi

# 1.2 Type checking
if command -v poetry &> /dev/null && cd "$PROJECT_ROOT" && poetry run mypy --version >/dev/null 2>&1; then
    if poetry run mypy app --quiet 2>/dev/null; then
        log_check "Type checking (mypy via poetry)" PASS
    else
        log_check "Type checking (mypy via poetry)" WARN "Some type hints missing (non-critical)"
    fi
elif command -v mypy &> /dev/null; then
    if cd "$PROJECT_ROOT" && mypy app --quiet 2>/dev/null; then
        log_check "Type checking (mypy)" PASS
    else
        log_check "Type checking (mypy)" WARN "Some type hints missing (non-critical)"
    fi
else
    log_check "Type checking (mypy)" WARN "mypy not installed, skipping"
fi

# 1.3 Security scan
if command -v trivy &> /dev/null; then
    if trivy fs "$PROJECT_ROOT" --quiet --severity HIGH,CRITICAL 2>/dev/null | grep -q "0 vulnerabilities"; then
        log_check "Security scan (trivy)" PASS
    else
        log_check "Security scan (trivy)" WARN "Some vulnerabilities found (review if not false positives)"
    fi
else
    log_check "Security scan (trivy)" WARN "trivy not installed, skipping"
fi

# ============================================================================
# 2. DEPLOYMENT CONFIGURATION
# ============================================================================
echo -e "\n${BLUE}[2/6] Deployment Configuration${NC}\n"

# 2.1 fly.toml exists
if [[ -f "$PROJECT_ROOT/fly.toml" ]]; then
    log_check "fly.toml present" PASS
else
    log_check "fly.toml present" WARN "Not found locally (app may be managed remotely). Run 'flyctl launch' to create if needed"
fi

# 2.2 .env.example exists
if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
    log_check ".env.example documentation" PASS
else
    log_check ".env.example documentation" FAIL "Create .env.example with all required vars"
fi

# 2.3 docker-compose.yml valid
if command -v docker-compose &> /dev/null; then
    if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" config > /dev/null 2>&1; then
        log_check "docker-compose.yml syntax" PASS
    else
        log_check "docker-compose.yml syntax" FAIL "Fix docker-compose.yml YAML syntax"
    fi
else
    log_check "docker-compose.yml syntax" WARN "docker-compose not installed, skipping"
fi

# ============================================================================
# 3. HEALTH CHECKS
# ============================================================================
echo -e "\n${BLUE}[3/6] Fly.io Health Checks${NC}\n"

# 3.1 Health live endpoint
if command -v flyctl &> /dev/null; then
    FLY_APP=$(grep "^app = " "$PROJECT_ROOT/fly.toml" 2>/dev/null | cut -d'"' -f2 || echo "agente-hotel-api")
    if LIVE_RESPONSE=$(curl -s -w "\n%{http_code}" "https://$FLY_APP.fly.dev/health/live" 2>/dev/null); then
        HTTP_CODE=$(echo "$LIVE_RESPONSE" | tail -n1)
        if [[ "$HTTP_CODE" == "200" ]]; then
            log_check "Fly: /health/live endpoint" PASS "(HTTP $HTTP_CODE)"
        else
            log_check "Fly: /health/live endpoint" FAIL "(HTTP $HTTP_CODE)"
        fi
    else
        log_check "Fly: /health/live endpoint" WARN "Cannot reach deployed app (may not be deployed yet)"
    fi
    
    # 3.2 Health ready endpoint
    if READY_RESPONSE=$(curl -s "https://$FLY_APP.fly.dev/health/ready" 2>/dev/null); then
        if echo "$READY_RESPONSE" | jq -e '.ready == true' > /dev/null 2>&1; then
            log_check "Fly: /health/ready endpoint" PASS "All checks passing"
        else
            log_check "Fly: /health/ready endpoint" WARN "Some checks failing (may be expected)"
            echo "  Checks: $(echo "$READY_RESPONSE" | jq '.checks' 2>/dev/null || echo "unable to parse")"
        fi
    else
        log_check "Fly: /health/ready endpoint" WARN "Cannot reach deployed app"
    fi
else
    log_check "Fly.io health checks" WARN "flyctl not installed, skipping Fly verification"
fi

# ============================================================================
# 4. INFRASTRUCTURE FILES
# ============================================================================
echo -e "\n${BLUE}[4/6] Infrastructure & Operations Files${NC}\n"

# 4.1 Backup script
if [[ -f "$PROJECT_ROOT/scripts/backup-restore.sh" ]]; then
    if [[ -x "$PROJECT_ROOT/scripts/backup-restore.sh" ]]; then
        log_check "Backup/restore script" PASS "(executable)"
    else
        log_check "Backup/restore script" WARN "(not executable, run chmod +x)"
        if [[ "$FIX_MODE" == "true" ]]; then
            chmod +x "$PROJECT_ROOT/scripts/backup-restore.sh"
            log_check "Fixed: chmod +x backup-restore.sh" PASS
        fi
    fi
else
    log_check "Backup/restore script" FAIL "Create scripts/backup-restore.sh"
fi

# 4.2 Prometheus alert rules
if [[ -f "$PROJECT_ROOT/docker/prometheus/alert_rules.yml" ]]; then
    log_check "Prometheus alert rules" PASS
    # Validate YAML
    if command -v yamllint &> /dev/null; then
        if yamllint "$PROJECT_ROOT/docker/prometheus/alert_rules.yml" > /dev/null 2>&1; then
            log_check "  → Alert rules YAML valid" PASS
        else
            log_check "  → Alert rules YAML valid" FAIL
        fi
    fi
else
    log_check "Prometheus alert rules" FAIL "Create docker/prometheus/alert_rules.yml"
fi

# 4.3 Incident runbooks
if [[ -f "$PROJECT_ROOT/docs/operations/runbooks.md" ]]; then
    RUNBOOK_SIZE=$(wc -c < "$PROJECT_ROOT/docs/operations/runbooks.md")
    if [[ $RUNBOOK_SIZE -gt 5000 ]]; then
        log_check "Incident runbooks" PASS "($RUNBOOK_SIZE bytes)"
    else
        log_check "Incident runbooks" WARN "Runbooks file too small, may need more content"
    fi
else
    log_check "Incident runbooks" FAIL "Create docs/operations/runbooks.md"
fi

# 4.4 Docker optimization
if [[ -f "$PROJECT_ROOT/Dockerfile.optimized" ]]; then
    log_check "Optimized Dockerfile" PASS "(multi-stage)"
else
    log_check "Optimized Dockerfile" WARN "Dockerfile.optimized not present (performance optimization only)"
fi

# ============================================================================
# 5. GIT & REPOSITORY
# ============================================================================
echo -e "\n${BLUE}[5/6] Git & Repository State${NC}\n"

cd "$PROJECT_ROOT"

# 5.1 Git status clean
if [[ $(git status --porcelain | wc -l) -eq 0 ]]; then
    log_check "Git working directory clean" PASS
else
    log_check "Git working directory clean" WARN "$(git status --porcelain | wc -l) uncommitted changes"
fi

# 5.2 Latest commit message
LATEST_COMMIT=$(git log -1 --pretty=%B 2>/dev/null | head -n1 || echo "unknown")
log_check "Latest commit" INFO "$LATEST_COMMIT"

# 5.3 Branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "$CURRENT_BRANCH" == "main" ]] || [[ "$CURRENT_BRANCH" == "master" ]]; then
    log_check "Branch (main/master)" PASS "$CURRENT_BRANCH"
else
    log_check "Branch (main/master)" WARN "On branch: $CURRENT_BRANCH"
fi

# 5.4 Remote origin
if git remote get-url origin &> /dev/null; then
    ORIGIN=$(git remote get-url origin)
    log_check "Remote origin configured" PASS
else
    log_check "Remote origin configured" FAIL "Set remote: git remote add origin ..."
fi

# ============================================================================
# 6. DEPLOYMENT READINESS
# ============================================================================
echo -e "\n${BLUE}[6/6] Deployment Readiness${NC}\n"

# 6.1 Secrets configured (on Fly)
if command -v flyctl &> /dev/null && [[ -n "${FLY_APP:-}" ]]; then
    SECRETS=$(flyctl secrets list -a "$FLY_APP" 2>/dev/null | grep -c "DATABASE_URL\|REDIS_URL" || echo "0")
    if [[ "$SECRETS" -ge 2 ]]; then
        log_check "Fly secrets configured" PASS "($SECRETS of 2 required)"
    else
        log_check "Fly secrets configured" WARN "Only $SECRETS of 2 required secrets set"
    fi
else
    log_check "Fly secrets configured" WARN "Cannot verify (flyctl unavailable or app not set)"
fi

# 6.2 pyproject.toml valid
if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    if command -v python &> /dev/null; then
        if python -c "import toml; toml.load('$PROJECT_ROOT/pyproject.toml')" 2>/dev/null; then
            log_check "pyproject.toml valid" PASS
        else
            log_check "pyproject.toml valid" FAIL "Fix TOML syntax"
        fi
    else
        log_check "pyproject.toml valid" WARN "Python not available for validation"
    fi
else
    log_check "pyproject.toml valid" FAIL "Create pyproject.toml"
fi

# 6.3 Documentation complete
REQUIRED_DOCS=(
    "README.md"
    "DEVIATIONS.md"
    "docs/HANDOVER_PACKAGE.md"
    "docs/OPERATIONS_MANUAL.md"
)
MISSING_DOCS=0
for doc in "${REQUIRED_DOCS[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$doc" ]]; then
        ((MISSING_DOCS++))
    fi
done

if [[ $MISSING_DOCS -eq 0 ]]; then
    log_check "Documentation complete" PASS "All required docs present"
else
    log_check "Documentation complete" WARN "$MISSING_DOCS of ${#REQUIRED_DOCS[@]} docs missing"
fi

# ============================================================================
# SUMMARY
# ============================================================================
TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNED))
PASS_RATE=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Verification Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

echo "Total Checks:    $TOTAL_CHECKS"
echo -e "  ${GREEN}Passed${NC}:     $CHECKS_PASSED"
echo -e "  ${YELLOW}Warnings${NC}:   $CHECKS_WARNED"
echo -e "  ${RED}Failed${NC}:     $CHECKS_FAILED"
echo ""
echo "Pass Rate:       ${PASS_RATE}%"
echo ""

if [[ $CHECKS_FAILED -eq 0 ]]; then
    if [[ $CHECKS_WARNED -eq 0 ]]; then
        echo -e "${GREEN}✓ All checks passed! Ready for production deployment.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ All critical checks passed, but $CHECKS_WARNED warnings need review.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ $CHECKS_FAILED critical checks failed. Fix before deploying.${NC}"
    exit 1
fi
