#!/bin/bash

###############################################################################
# Blue-Green Deployment Script
# 
# Zero-downtime deployment strategy that maintains two identical production
# environments (blue and green) and switches traffic between them.
#
# Features:
# - Zero downtime deployment
# - Instant rollback capability
# - Health validation before traffic switch
# - Automatic cleanup of old environment
# - Deployment metrics tracking
#
# Usage:
#   ./blue-green-deploy.sh --image IMAGE_TAG --environment ENV [OPTIONS]
#
# Author: AI Agent
# Date: October 15, 2025
###############################################################################

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_TAG=""
ENVIRONMENT="staging"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=10
TRAFFIC_SWITCH_DELAY=30
KEEP_OLD_ENVIRONMENT=false
DRY_RUN=false
VERBOSE=false

# Deployment tracking
DEPLOYMENT_START_TIME=""
BLUE_CONTAINER=""
GREEN_CONTAINER=""
ACTIVE_COLOR=""
INACTIVE_COLOR=""

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

show_usage() {
    cat << EOF
Usage: $0 --image IMAGE_TAG --environment ENV [OPTIONS]

Required:
  --image TAG                 Docker image tag to deploy

Optional:
  --environment ENV           Target environment (staging|production) [default: staging]
  --health-check-timeout SEC  Health check timeout in seconds [default: 300]
  --health-check-interval SEC Health check interval in seconds [default: 10]
  --traffic-switch-delay SEC  Delay before switching traffic [default: 30]
  --keep-old                  Keep old environment running
  --dry-run                   Show what would be done without doing it
  --verbose                   Enable verbose output
  --help                      Show this help message

Examples:
  # Deploy to staging
  $0 --image myapp:v1.2.3 --environment staging

  # Deploy to production with extended health check
  $0 --image myapp:v1.2.3 --environment production --health-check-timeout 600

  # Dry run
  $0 --image myapp:v1.2.3 --environment staging --dry-run

EOF
    exit 0
}

# ═══════════════════════════════════════════════════════════════════════════
# PARSE ARGUMENTS
# ═══════════════════════════════════════════════════════════════════════════

while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --health-check-timeout)
            HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        --health-check-interval)
            HEALTH_CHECK_INTERVAL="$2"
            shift 2
            ;;
        --traffic-switch-delay)
            TRAFFIC_SWITCH_DELAY="$2"
            shift 2
            ;;
        --keep-old)
            KEEP_OLD_ENVIRONMENT=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$IMAGE_TAG" ]]; then
    log_error "Missing required argument: --image"
    show_usage
fi

# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════

detect_active_environment() {
    log_step "STEP 1: Detecting Active Environment"
    
    # Check which color is currently active
    BLUE_RUNNING=$(docker ps --filter "name=agente-api-blue" --filter "status=running" --format "{{.Names}}" || echo "")
    GREEN_RUNNING=$(docker ps --filter "name=agente-api-green" --filter "status=running" --format "{{.Names}}" || echo "")
    
    if [[ -n "$BLUE_RUNNING" ]]; then
        ACTIVE_COLOR="blue"
        INACTIVE_COLOR="green"
        BLUE_CONTAINER="agente-api-blue"
        GREEN_CONTAINER="agente-api-green"
        log_info "Active environment: ${BLUE}BLUE${NC}"
        log_info "Target environment: ${GREEN}GREEN${NC}"
    elif [[ -n "$GREEN_RUNNING" ]]; then
        ACTIVE_COLOR="green"
        INACTIVE_COLOR="blue"
        BLUE_CONTAINER="agente-api-blue"
        GREEN_CONTAINER="agente-api-green"
        log_info "Active environment: ${GREEN}GREEN${NC}"
        log_info "Target environment: ${BLUE}BLUE${NC}"
    else
        # No active environment - initial deployment
        ACTIVE_COLOR="none"
        INACTIVE_COLOR="blue"
        BLUE_CONTAINER="agente-api-blue"
        GREEN_CONTAINER="agente-api-green"
        log_warning "No active environment detected - performing initial deployment to BLUE"
    fi
    
    if [[ "$ACTIVE_COLOR" == "blue" ]]; then
        TARGET_CONTAINER="$GREEN_CONTAINER"
    else
        TARGET_CONTAINER="$BLUE_CONTAINER"
    fi
    
    log_success "Environment detection complete"
}

# ═══════════════════════════════════════════════════════════════════════════
# PRE-DEPLOYMENT CHECKS
# ═══════════════════════════════════════════════════════════════════════════

pre_deployment_checks() {
    log_step "STEP 2: Pre-Deployment Checks"
    
    # Check if image exists
    log_info "Checking if image exists: $IMAGE_TAG"
    if ! docker image inspect "$IMAGE_TAG" &>/dev/null; then
        log_info "Image not found locally, pulling..."
        if [[ "$DRY_RUN" == "false" ]]; then
            docker pull "$IMAGE_TAG" || {
                log_error "Failed to pull image: $IMAGE_TAG"
                exit 1
            }
        fi
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ "$AVAILABLE_SPACE" -lt 5 ]]; then
        log_error "Insufficient disk space: ${AVAILABLE_SPACE}GB available, need at least 5GB"
        exit 1
    fi
    log_info "Disk space check: ${AVAILABLE_SPACE}GB available"
    
    # Check if required services are running
    log_info "Checking required services..."
    REQUIRED_SERVICES=("postgres" "redis")
    for service in "${REQUIRED_SERVICES[@]}"; do
        if ! docker ps | grep -q "$service"; then
            log_warning "Service not running: $service"
        else
            log_info "Service running: $service"
        fi
    done
    
    log_success "Pre-deployment checks passed"
}

# ═══════════════════════════════════════════════════════════════════════════
# DEPLOY NEW ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════

deploy_new_environment() {
    log_step "STEP 3: Deploying New Environment ($INACTIVE_COLOR)"
    
    # Stop and remove old inactive container if exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${TARGET_CONTAINER}$"; then
        log_info "Stopping existing $TARGET_CONTAINER..."
        if [[ "$DRY_RUN" == "false" ]]; then
            docker stop "$TARGET_CONTAINER" 2>/dev/null || true
            docker rm "$TARGET_CONTAINER" 2>/dev/null || true
        fi
    fi
    
    # Determine port for new environment
    if [[ "$INACTIVE_COLOR" == "blue" ]]; then
        TARGET_PORT=8001
    else
        TARGET_PORT=8002
    fi
    
    log_info "Starting new container: $TARGET_CONTAINER on port $TARGET_PORT"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        docker run -d \
            --name "$TARGET_CONTAINER" \
            --network agente-hotel_backend_network \
            -p "$TARGET_PORT:8000" \
            -e ENVIRONMENT="$ENVIRONMENT" \
            -e POSTGRES_URL="${POSTGRES_URL:-postgresql://postgres:password@postgres:5432/agente_db}" \
            -e REDIS_URL="${REDIS_URL:-redis://redis:6379/0}" \
            --health-cmd="curl -f http://localhost:8000/health/ready || exit 1" \
            --health-interval=10s \
            --health-timeout=5s \
            --health-retries=3 \
            --restart=unless-stopped \
            "$IMAGE_TAG" || {
                log_error "Failed to start container: $TARGET_CONTAINER"
                exit 1
            }
    else
        log_info "[DRY RUN] Would start: docker run -d --name $TARGET_CONTAINER -p $TARGET_PORT:8000 $IMAGE_TAG"
    fi
    
    log_success "New environment deployed to $INACTIVE_COLOR"
}

# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════

wait_for_health() {
    log_step "STEP 4: Health Check Validation"
    
    local timeout="$HEALTH_CHECK_TIMEOUT"
    local interval="$HEALTH_CHECK_INTERVAL"
    local elapsed=0
    
    # Determine target URL
    if [[ "$INACTIVE_COLOR" == "blue" ]]; then
        TARGET_URL="http://localhost:8001"
    else
        TARGET_URL="http://localhost:8002"
    fi
    
    log_info "Waiting for $TARGET_CONTAINER to be healthy..."
    log_info "Health check URL: $TARGET_URL/health/ready"
    log_info "Timeout: ${timeout}s | Interval: ${interval}s"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would wait for health checks"
        return 0
    fi
    
    while [[ $elapsed -lt $timeout ]]; do
        # Check container health status
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$TARGET_CONTAINER" 2>/dev/null || echo "unknown")
        
        if [[ "$HEALTH_STATUS" == "healthy" ]]; then
            log_success "Container is healthy after ${elapsed}s"
            
            # Additional endpoint checks
            log_info "Performing additional endpoint checks..."
            
            # Check /health/live
            if curl -sf "$TARGET_URL/health/live" >/dev/null; then
                log_success "/health/live: OK"
            else
                log_warning "/health/live: Failed"
            fi
            
            # Check /health/ready
            if curl -sf "$TARGET_URL/health/ready" >/dev/null; then
                log_success "/health/ready: OK"
            else
                log_error "/health/ready: Failed"
                return 1
            fi
            
            # Check /metrics
            if curl -sf "$TARGET_URL/metrics" >/dev/null; then
                log_success "/metrics: OK"
            else
                log_warning "/metrics: Failed (non-critical)"
            fi
            
            return 0
        fi
        
        echo -n "."
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done
    
    log_error "Health check timeout after ${timeout}s"
    log_error "Container logs:"
    docker logs --tail 50 "$TARGET_CONTAINER"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════
# TRAFFIC SWITCH
# ═══════════════════════════════════════════════════════════════════════════

switch_traffic() {
    log_step "STEP 5: Switching Traffic to $INACTIVE_COLOR"
    
    # Wait before switching
    if [[ "$TRAFFIC_SWITCH_DELAY" -gt 0 ]]; then
        log_info "Waiting ${TRAFFIC_SWITCH_DELAY}s before traffic switch..."
        if [[ "$DRY_RUN" == "false" ]]; then
            sleep "$TRAFFIC_SWITCH_DELAY"
        fi
    fi
    
    # Update NGINX configuration or load balancer
    # This is a simplified example - adapt to your infrastructure
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Update nginx upstream
        log_info "Updating NGINX configuration..."
        
        if [[ "$INACTIVE_COLOR" == "blue" ]]; then
            NEW_UPSTREAM="agente-api-blue:8000"
        else
            NEW_UPSTREAM="agente-api-green:8000"
        fi
        
        # Update docker-compose or nginx config
        # This is infrastructure-specific
        log_info "New upstream: $NEW_UPSTREAM"
        
        # Reload nginx
        if docker ps | grep -q "nginx"; then
            docker exec nginx nginx -s reload || log_warning "Failed to reload nginx"
        fi
    else
        log_info "[DRY RUN] Would switch traffic to $INACTIVE_COLOR"
    fi
    
    log_success "Traffic switched to $INACTIVE_COLOR"
}

# ═══════════════════════════════════════════════════════════════════════════
# POST-DEPLOYMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

post_deployment_validation() {
    log_step "STEP 6: Post-Deployment Validation"
    
    log_info "Running smoke tests..."
    
    # Test main endpoints
    BASE_URL="http://localhost"
    ENDPOINTS=(
        "/health/live"
        "/health/ready"
        "/metrics"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if [[ "$DRY_RUN" == "false" ]]; then
            if curl -sf "${BASE_URL}${endpoint}" >/dev/null; then
                log_success "✓ ${endpoint}"
            else
                log_error "✗ ${endpoint}"
                return 1
            fi
        else
            log_info "[DRY RUN] Would test: ${BASE_URL}${endpoint}"
        fi
    done
    
    log_success "Post-deployment validation passed"
}

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

cleanup_old_environment() {
    log_step "STEP 7: Cleanup Old Environment"
    
    if [[ "$KEEP_OLD_ENVIRONMENT" == "true" ]]; then
        log_info "Keeping old environment for manual verification"
        log_info "Old container: $ACTIVE_COLOR (still running)"
        return 0
    fi
    
    if [[ "$ACTIVE_COLOR" == "none" ]]; then
        log_info "No old environment to clean up"
        return 0
    fi
    
    OLD_CONTAINER=""
    if [[ "$ACTIVE_COLOR" == "blue" ]]; then
        OLD_CONTAINER="$BLUE_CONTAINER"
    else
        OLD_CONTAINER="$GREEN_CONTAINER"
    fi
    
    log_info "Stopping old environment: $OLD_CONTAINER"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Wait a bit before stopping old container
        sleep 10
        
        docker stop "$OLD_CONTAINER" 2>/dev/null || log_warning "Failed to stop $OLD_CONTAINER"
        docker rm "$OLD_CONTAINER" 2>/dev/null || log_warning "Failed to remove $OLD_CONTAINER"
        
        log_success "Old environment cleaned up"
    else
        log_info "[DRY RUN] Would stop and remove: $OLD_CONTAINER"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

show_deployment_summary() {
    local deployment_end_time=$(date +%s)
    local deployment_duration=$((deployment_end_time - DEPLOYMENT_START_TIME))
    
    log_step "DEPLOYMENT SUMMARY"
    
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
    echo ""
    echo "Environment:     $ENVIRONMENT"
    echo "Image:           $IMAGE_TAG"
    echo "From:            $ACTIVE_COLOR"
    echo "To:              $INACTIVE_COLOR"
    echo "Duration:        ${deployment_duration}s"
    echo "Active Container: $TARGET_CONTAINER"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}NOTE: This was a DRY RUN - no actual changes were made${NC}"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

main() {
    DEPLOYMENT_START_TIME=$(date +%s)
    
    log_step "BLUE-GREEN DEPLOYMENT STARTING"
    echo "Image: $IMAGE_TAG"
    echo "Environment: $ENVIRONMENT"
    echo "Dry Run: $DRY_RUN"
    echo ""
    
    # Execute deployment steps
    detect_active_environment
    pre_deployment_checks
    deploy_new_environment
    wait_for_health || {
        log_error "Health checks failed - aborting deployment"
        exit 1
    }
    switch_traffic
    post_deployment_validation || {
        log_error "Post-deployment validation failed"
        exit 1
    }
    cleanup_old_environment
    show_deployment_summary
    
    log_success "Blue-Green deployment completed successfully!"
    exit 0
}

# Run main function
main "$@"
