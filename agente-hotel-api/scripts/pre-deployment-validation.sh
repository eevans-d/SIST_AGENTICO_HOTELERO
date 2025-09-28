#!/bin/bash
# Pre-Deployment Validation Script
# Comprehensive validation before production deployment

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="./pre-deployment-validation.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validation results
VALIDATION_PASSED=true
VALIDATION_ISSUES=()

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[✓]${NC} $1"
}

log_warning() {
    log "${YELLOW}[⚠]${NC} $1"
    VALIDATION_ISSUES+=("WARNING: $1")
}

log_error() {
    log "${RED}[✗]${NC} $1"
    VALIDATION_ISSUES+=("ERROR: $1")
    VALIDATION_PASSED=false
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_environment_files() {
    log_info "🔍 Validating environment configuration..."
    
    # Check .env.production exists
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        log_error "Production environment file .env.production not found"
        return
    fi
    
    # Check critical environment variables
    local required_vars=(
        "SECRET_KEY"
        "PMS_API_KEY"
        "WHATSAPP_ACCESS_TOKEN"
        "WHATSAPP_VERIFY_TOKEN"
        "WHATSAPP_APP_SECRET"
        "GMAIL_APP_PASSWORD"
        "POSTGRES_PASSWORD"
        "MYSQL_PASSWORD"
        "MYSQL_ROOT_PASSWORD"
    )
    
    source "$PROJECT_ROOT/.env.production"
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
        elif [[ "${!var}" == *"_here"* ]] || [[ "${!var}" == *"dev-"* ]] || [[ "${!var}" == "generate_secure_key_here" ]]; then
            log_error "Environment variable $var contains placeholder/development value: ${!var}"
        else
            log_success "Environment variable $var is properly configured"
        fi
    done
    
    # Check ENVIRONMENT is set to production
    if [[ "${ENVIRONMENT:-}" != "production" ]]; then
        log_error "ENVIRONMENT variable is not set to 'production': ${ENVIRONMENT:-not set}"
    else
        log_success "Environment is correctly set to production"
    fi
}

validate_docker_configuration() {
    log_info "🐳 Validating Docker configuration..."
    
    # Check Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return
    fi
    
    # Check Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return
    fi
    
    # Check Docker Compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        return
    fi
    
    # Validate docker-compose.production.yml
    if [[ ! -f "$PROJECT_ROOT/docker-compose.production.yml" ]]; then
        log_error "Production Docker Compose file not found"
        return
    fi
    
    # Validate compose file syntax
    if ! docker compose -f "$PROJECT_ROOT/docker-compose.production.yml" config > /dev/null; then
        log_error "Docker Compose file has syntax errors"
        return
    fi
    
    # Check Dockerfile.production exists
    if [[ ! -f "$PROJECT_ROOT/Dockerfile.production" ]]; then
        log_error "Production Dockerfile not found"
        return
    fi
    
    log_success "Docker configuration is valid"
}

validate_code_quality() {
    log_info "🔍 Validating code quality..."
    
    cd "$PROJECT_ROOT"
    
    # Check git status
    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "There are uncommitted changes in the repository"
    else
        log_success "Repository is clean"
    fi
    
    # Check we're on a tagged version or main branch
    local current_branch=$(git branch --show-current)
    local current_commit=$(git rev-parse HEAD)
    
    if [[ "$current_branch" != "main" ]] && ! git tag --contains "$current_commit" &> /dev/null; then
        log_warning "Not on main branch or tagged commit. Current: $current_branch"
    else
        log_success "On main branch or tagged commit"
    fi
    
    # Run linting if ruff is available
    if command -v ruff &> /dev/null; then
        log_info "Running code linting..."
        if ruff check . --quiet; then
            log_success "Code linting passed"
        else
            log_error "Code linting failed"
        fi
    else
        log_warning "Ruff not available for linting"
    fi
}

validate_security() {
    log_info "🔒 Validating security configuration..."
    
    # Check for secrets in code (basic check)
    local secrets_found=false
    
    # Check settings.py for hardcoded secrets
    if grep -r "SecretStr(" "$PROJECT_ROOT/app/" | grep -v "SecretStr$" | grep -v "# No default"; then
        log_error "Hardcoded secrets found in code"
        secrets_found=true
    fi
    
    if ! $secrets_found; then
        log_success "No hardcoded secrets found in application code"
    fi
    
    # Check file permissions on sensitive files
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        local perms=$(stat -c "%a" "$PROJECT_ROOT/.env.production")
        if [[ "$perms" != "600" ]] && [[ "$perms" != "644" ]]; then
            log_warning "Environment file has permissive permissions: $perms"
        else
            log_success "Environment file has appropriate permissions"
        fi
    fi
}

validate_tests() {
    log_info "🧪 Validating test suite..."
    
    cd "$PROJECT_ROOT"
    
    # Check if test directory exists
    if [[ ! -d "tests" ]]; then
        log_error "Tests directory not found"
        return
    fi
    
    # Check for test files
    local test_count=$(find tests -name "test_*.py" | wc -l)
    if [[ $test_count -eq 0 ]]; then
        log_error "No test files found"
        return
    fi
    
    log_success "Found $test_count test files"
    
    # Try to run a quick test validation
    if command -v python3 &> /dev/null; then
        if python3 -c "import pytest" 2>/dev/null; then
            log_info "Running basic test validation..."
            # Just validate test discovery, don't run all tests as they may require infrastructure
            if python3 -m pytest --collect-only -q tests/ > /dev/null 2>&1; then
                log_success "Test discovery successful"
            else
                log_warning "Test discovery issues found"
            fi
        else
            log_warning "pytest not available for test validation"
        fi
    else
        log_warning "Python not available for test validation"
    fi
}

validate_dependencies() {
    log_info "📦 Validating dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Check requirements files exist
    for req_file in "requirements-prod.txt" "pyproject.toml"; do
        if [[ ! -f "$req_file" ]]; then
            log_error "Dependency file $req_file not found"
        else
            log_success "Dependency file $req_file exists"
        fi
    done
    
    # Check for known vulnerable packages (basic check)
    if [[ -f "requirements-prod.txt" ]]; then
        # This is a basic check - in production you'd use tools like safety or snyk
        if grep -E "(django==1\.|flask==0\.|requests==2\.6)" requirements-prod.txt; then
            log_warning "Potentially vulnerable package versions detected"
        else
            log_success "No obviously vulnerable packages detected"
        fi
    fi
}

validate_infrastructure_readiness() {
    log_info "🏗️ Validating infrastructure readiness..."
    
    # Check if necessary scripts exist
    local required_scripts=(
        "scripts/deploy.sh"
        "scripts/health-check.sh"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$script" ]]; then
            log_error "Required script $script not found"
        elif [[ ! -x "$PROJECT_ROOT/$script" ]]; then
            log_error "Script $script is not executable"
        else
            log_success "Script $script is available and executable"
        fi
    done
    
    # Check for backup directory
    if [[ ! -d "/opt/backups" ]] && [[ ! -w "$(dirname /opt/backups)" ]]; then
        log_warning "Backup directory /opt/backups not available or not writable"
    fi
}

validate_monitoring_config() {
    log_info "📊 Validating monitoring configuration..."
    
    # Check Grafana dashboards
    if [[ -d "$PROJECT_ROOT/docker/grafana/dashboards" ]]; then
        local dashboard_count=$(find "$PROJECT_ROOT/docker/grafana/dashboards" -name "*.json" | wc -l)
        if [[ $dashboard_count -gt 0 ]]; then
            log_success "Found $dashboard_count Grafana dashboards"
        else
            log_warning "No Grafana dashboards found"
        fi
    else
        log_warning "Grafana dashboards directory not found"
    fi
    
    # Check Prometheus configuration
    if [[ -f "$PROJECT_ROOT/docker/prometheus/prometheus.yml" ]]; then
        log_success "Prometheus configuration found"
    else
        log_warning "Prometheus configuration not found"
    fi
}

# ============================================================================
# Main Validation Function
# ============================================================================

run_all_validations() {
    log_info "🚀 Starting pre-deployment validation..."
    echo "Validation started at $(date)" > "$LOG_FILE"
    
    validate_environment_files
    validate_docker_configuration
    validate_code_quality
    validate_security
    validate_tests
    validate_dependencies
    validate_infrastructure_readiness
    validate_monitoring_config
    
    log_info "📋 Validation Summary:"
    
    if [[ ${#VALIDATION_ISSUES[@]} -eq 0 ]]; then
        log_success "No issues found during validation"
    else
        log_info "Found ${#VALIDATION_ISSUES[@]} issues:"
        for issue in "${VALIDATION_ISSUES[@]}"; do
            echo "  - $issue"
        done
    fi
    
    if $VALIDATION_PASSED; then
        log_success "🎉 Pre-deployment validation PASSED - Ready for deployment!"
        echo
        log_info "Next steps:"
        log_info "  1. Run: ./scripts/deploy.sh production"
        log_info "  2. Monitor deployment logs"
        log_info "  3. Verify health endpoints after deployment"
        return 0
    else
        log_error "❌ Pre-deployment validation FAILED - Fix issues before deployment!"
        echo
        log_info "Please address the ERROR items listed above before proceeding with deployment."
        return 1
    fi
}

# ============================================================================
# Script Execution
# ============================================================================

# Change to project directory
cd "$PROJECT_ROOT"

# Run all validations
run_all_validations

exit $?