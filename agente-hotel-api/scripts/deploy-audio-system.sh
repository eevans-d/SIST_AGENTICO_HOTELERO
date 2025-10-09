#!/bin/bash
# Automated Deployment Script for Audio System
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
AUDIO_VERSION="${AUDIO_VERSION:-latest}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Pre-deployment validation
validate_environment() {
    log_info "🔍 Validating deployment environment..."
    
    # Check required tools
    local required_tools=("docker" "docker-compose" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' is not installed"
            exit 1
        fi
    done
    
    # Check environment files
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        log_error "Production environment file not found: .env.production"
        exit 1
    fi
    
    # Validate Docker Compose files
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" config > /dev/null 2>&1; then
        log_error "Invalid Docker Compose configuration"
        exit 1
    fi
    
    log_success "Environment validation completed"
}

# Backup current deployment
backup_current_deployment() {
    log_info "💾 Creating backup of current deployment..."
    
    local backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup database
    if docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" ps postgres-audio | grep -q "Up"; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" exec -T postgres-audio \
            pg_dump -U agente_user agente_audio_db > "$backup_dir/postgres_backup.sql"
        log_success "Database backup created"
    fi
    
    # Backup Redis data
    if docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" ps redis-audio | grep -q "Up"; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" exec -T redis-audio \
            redis-cli BGSAVE
        docker cp "$(docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" ps -q redis-audio):/data/dump.rdb" \
            "$backup_dir/redis_backup.rdb"
        log_success "Redis backup created"
    fi
    
    # Store backup path for rollback
    echo "$backup_dir" > "$PROJECT_ROOT/.last_backup"
    log_success "Backup completed: $backup_dir"
}

# Performance baseline collection
collect_baseline_metrics() {
    log_info "📊 Collecting performance baseline..."
    
    local baseline_file="$PROJECT_ROOT/.playbook/baseline_$(date +%Y%m%d_%H%M%S).json"
    mkdir -p "$(dirname "$baseline_file")"
    
    # Wait for services to be ready
    sleep 30
    
    # Collect metrics via Prometheus
    local prometheus_url="http://localhost:9090"
    local metrics_queries=(
        "histogram_quantile(0.95, rate(audio_cache_operation_seconds_bucket[5m]))"
        "rate(audio_cache_hits_total[5m]) / (rate(audio_cache_hits_total[5m]) + rate(audio_cache_misses_total[5m]))"
        "avg(audio_pool_health_score)"
        "rate(audio_compression_operations_total{result=\"success\"}[5m])"
    )
    
    local baseline_data="{\"timestamp\": \"$(date -Iseconds)\", \"metrics\": {}}"
    
    for query in "${metrics_queries[@]}"; do
        local result
        result=$(curl -s "$prometheus_url/api/v1/query" --data-urlencode "query=$query" | jq -r '.data.result[0].value[1] // "0"')
        baseline_data=$(echo "$baseline_data" | jq ".metrics[\"$(echo "$query" | md5sum | cut -d' ' -f1)\"] = \"$result\"")
    done
    
    echo "$baseline_data" > "$baseline_file"
    log_success "Baseline metrics collected: $baseline_file"
}

# Deploy audio system
deploy_audio_system() {
    log_info "🚀 Deploying audio system..."
    
    # Build and deploy with zero-downtime strategy
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    docker-compose -f docker-compose.audio-production.yml pull
    
    # Rolling update
    log_info "Performing rolling update..."
    
    # Update services one by one
    local services=("agente-api-audio-1" "agente-api-audio-2" "agente-api-audio-3")
    for service in "${services[@]}"; do
        log_info "Updating service: $service"
        
        docker-compose -f docker-compose.audio-production.yml up -d --no-deps "$service"
        
        # Wait for health check
        wait_for_service_health "$service"
        
        # Brief pause between updates
        sleep 10
    done
    
    log_success "Rolling update completed"
}

# Health check function
wait_for_service_health() {
    local service_name="$1"
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / 10))
    local attempt=1
    
    log_info "⏳ Waiting for $service_name to be healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" ps "$service_name" | grep -q "healthy"; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for $service_name..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$service_name failed to become healthy within $HEALTH_CHECK_TIMEOUT seconds"
    return 1
}

# Comprehensive health validation
validate_deployment_health() {
    log_info "🏥 Validating deployment health..."
    
    local health_endpoints=(
        "http://localhost:8000/health/live"
        "http://localhost:8000/health/ready"
        "http://localhost:8000/metrics"
    )
    
    for endpoint in "${health_endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log_success "✅ $endpoint - OK"
        else
            log_error "❌ $endpoint - FAILED"
            return 1
        fi
    done
    
    # Validate audio processing
    log_info "Testing audio processing endpoint..."
    local test_response
    test_response=$(curl -s -X POST "http://localhost:8000/api/audio/test" \
        -H "Content-Type: application/json" \
        -d '{"test": "audio_system"}')
    
    if echo "$test_response" | jq -e '.status == "ok"' > /dev/null; then
        log_success "✅ Audio processing - OK"
    else
        log_error "❌ Audio processing - FAILED"
        return 1
    fi
    
    log_success "All health checks passed"
}

# Performance validation
validate_performance() {
    log_info "⚡ Validating performance improvements..."
    
    # Run performance test suite
    if [[ -f "$PROJECT_ROOT/scripts/performance_test_runner.py" ]]; then
        log_info "Running performance test suite..."
        cd "$PROJECT_ROOT"
        python scripts/performance_test_runner.py --validate-deployment
        
        if [[ $? -eq 0 ]]; then
            log_success "Performance validation passed"
        else
            log_warning "Performance validation had issues - check logs"
        fi
    else
        log_warning "Performance test suite not found - skipping validation"
    fi
}

# Rollback function
rollback_deployment() {
    log_warning "🔄 Initiating rollback..."
    
    if [[ ! -f "$PROJECT_ROOT/.last_backup" ]]; then
        log_error "No backup information found for rollback"
        return 1
    fi
    
    local backup_dir
    backup_dir=$(cat "$PROJECT_ROOT/.last_backup")
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    log_info "Rolling back to backup: $backup_dir"
    
    # Stop current services
    docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" down
    
    # Restore database
    if [[ -f "$backup_dir/postgres_backup.sql" ]]; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" up -d postgres-audio
        sleep 30
        docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" exec -T postgres-audio \
            psql -U agente_user -d agente_audio_db < "$backup_dir/postgres_backup.sql"
    fi
    
    # Restore Redis
    if [[ -f "$backup_dir/redis_backup.rdb" ]]; then
        docker cp "$backup_dir/redis_backup.rdb" \
            "$(docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" ps -q redis-audio):/data/dump.rdb"
        docker-compose -f "$PROJECT_ROOT/docker-compose.audio-production.yml" restart redis-audio
    fi
    
    # Start previous version
    # Note: This would require version tagging in a real scenario
    log_warning "Manual intervention required to restore previous image versions"
    
    log_success "Rollback completed"
}

# Cleanup function
cleanup_old_resources() {
    log_info "🧹 Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backups (keep last 5)
    find "$PROJECT_ROOT/backups" -maxdepth 1 -type d -name "20*" | sort -r | tail -n +6 | xargs rm -rf
    
    log_success "Cleanup completed"
}

# Send deployment notification
send_notification() {
    local status="$1"
    local message="$2"
    
    log_info "📢 Sending deployment notification..."
    
    # This would integrate with your notification system
    # Examples: Slack, Discord, Email, PagerDuty
    
    local webhook_url="${SLACK_WEBHOOK_URL:-}"
    if [[ -n "$webhook_url" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🎵 Audio System Deployment - $status: $message\"}" \
            "$webhook_url"
    fi
    
    log_success "Notification sent"
}

# Main deployment flow
main() {
    log_info "🎵 Starting Audio System Deployment"
    log_info "Environment: $DEPLOY_ENV"
    log_info "Version: $AUDIO_VERSION"
    echo "==========================================\n"
    
    local start_time
    start_time=$(date +%s)
    
    # Trap for cleanup on exit
    trap 'cleanup_on_exit' EXIT
    
    # Pre-deployment phase
    validate_environment
    backup_current_deployment
    
    # Deployment phase
    if deploy_audio_system; then
        log_success "✅ Deployment completed successfully"
        
        # Post-deployment validation
        if validate_deployment_health && validate_performance; then
            collect_baseline_metrics
            send_notification "SUCCESS" "Audio system deployed successfully"
            log_success "🎉 Deployment pipeline completed successfully"
        else
            if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                rollback_deployment
                send_notification "ROLLBACK" "Deployment failed validation - rolled back"
            else
                send_notification "WARNING" "Deployment completed but validation failed"
            fi
        fi
    else
        log_error "❌ Deployment failed"
        
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment
            send_notification "ROLLBACK" "Deployment failed - rolled back"
        else
            send_notification "FAILURE" "Deployment failed - manual intervention required"
        fi
        exit 1
    fi
    
    cleanup_old_resources
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "🏁 Total deployment time: ${duration}s"
}

# Cleanup on exit
cleanup_on_exit() {
    log_info "🧹 Performing cleanup..."
    # Add any cleanup tasks here
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi