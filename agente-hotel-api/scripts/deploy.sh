#!/bin/bash
# Production Deployment Script with Backup and Rollback
# Usage: ./deploy.sh [environment] [version]

set -euo pipefail

# ============================================================================
# Configuration and Constants
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/var/log/agente-hotel-deploy.log"
BACKUP_DIR="/opt/backups/agente-hotel"
ENVIRONMENT="${1:-production}"
VERSION="${2:-$(git rev-parse --short HEAD)}"
COMPOSE_FILE="docker-compose.production.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging and Utility Functions  
# ============================================================================

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Pre-deployment Validation
# ============================================================================

validate_environment() {
    log_info "🔍 Validating deployment environment..."
    
    # Check required tools
    for tool in docker git curl; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' not found"
            exit 1
        fi
    done
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not available"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        log_error "Production environment file .env.production not found"
        exit 1
    fi
    
    # Check compose file
    if [[ ! -f "$PROJECT_ROOT/$COMPOSE_FILE" ]]; then
        log_error "Docker compose file $COMPOSE_FILE not found"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# ============================================================================
# Backup Functions
# ============================================================================

create_backup() {
    log_info "📦 Creating backup before deployment..."
    
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/${backup_timestamp}_${VERSION}"
    
    mkdir -p "$backup_path"
    
    # Database backup
    if docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        log_info "Backing up PostgreSQL database..."
        docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U agente_user agente_hotel > "$backup_path/postgres_backup.sql"
    fi
    
    # QloApps database backup
    if docker compose -f "$COMPOSE_FILE" ps mysql | grep -q "Up"; then
        log_info "Backing up MySQL database..."
        docker compose -f "$COMPOSE_FILE" exec -T mysql mysqldump -u qloapps -p"${MYSQL_PASSWORD}" qloapps > "$backup_path/mysql_backup.sql"
    fi
    
    # Application configuration backup
    cp -r "$PROJECT_ROOT/.env.production" "$backup_path/"
    
    # Store current image tags
    docker compose -f "$COMPOSE_FILE" images > "$backup_path/current_images.txt"
    
    echo "$backup_path" > "$PROJECT_ROOT/.last_backup"
    log_success "Backup created at $backup_path"
}

# ============================================================================
# Rollback Function
# ============================================================================

rollback() {
    log_error "🔄 Deployment failed. Initiating rollback..."
    
    if [[ -f "$PROJECT_ROOT/.last_backup" ]]; then
        local backup_path=$(cat "$PROJECT_ROOT/.last_backup")
        
        if [[ -d "$backup_path" ]]; then
            log_info "Rolling back to backup: $backup_path"
            
            # Stop current containers
            docker compose -f "$COMPOSE_FILE" down --remove-orphans
            
            # Restore configuration
            cp "$backup_path/.env.production" "$PROJECT_ROOT/"
            
            # Restore databases if needed
            if [[ -f "$backup_path/postgres_backup.sql" ]]; then
                docker compose -f "$COMPOSE_FILE" up -d postgres
                sleep 10
                docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U agente_user -d agente_hotel < "$backup_path/postgres_backup.sql"
            fi
            
            if [[ -f "$backup_path/mysql_backup.sql" ]]; then
                docker compose -f "$COMPOSE_FILE" up -d mysql
                sleep 10
                docker compose -f "$COMPOSE_FILE" exec -T mysql mysql -u qloapps -p"${MYSQL_PASSWORD}" qloapps < "$backup_path/mysql_backup.sql"
            fi
            
            # Start services
            docker compose -f "$COMPOSE_FILE" up -d
            
            log_success "Rollback completed"
        else
            log_error "Backup path not found: $backup_path"
        fi
    else
        log_error "No backup information found for rollback"
    fi
    
    exit 1
}

# ============================================================================
# Health Check Functions
# ============================================================================

wait_for_health() {
    local service_url="$1"
    local max_attempts=30
    local attempt=1
    
    log_info "⏳ Waiting for service health check: $service_url"
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url" > /dev/null; then
            log_success "Service is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - Service not ready yet..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Service failed to become healthy after $max_attempts attempts"
    return 1
}

validate_deployment() {
    log_info "🔍 Validating deployment..."
    
    # Check that all services are running
    local failed_services=""
    for service in agente-api postgres redis qloapps mysql; do
        if ! docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            failed_services="$failed_services $service"
        fi
    done
    
    if [[ -n "$failed_services" ]]; then
        log_error "The following services failed to start:$failed_services"
        return 1
    fi
    
    # Health check for main API
    if ! wait_for_health "http://localhost:8000/health/ready"; then
        log_error "API health check failed"
        return 1
    fi
    
    # Basic smoke test
    log_info "Running smoke tests..."
    if ! curl -f -s "http://localhost:8000/health/live" | grep -q "status"; then
        log_error "Smoke test failed"
        return 1
    fi
    
    log_success "Deployment validation passed"
    return 0
}

# ============================================================================
# Main Deployment Logic
# ============================================================================

main() {
    log_info "🚀 Starting deployment to $ENVIRONMENT (version: $VERSION)"
    
    # Set up error handling
    trap rollback ERR
    
    # Pre-deployment validation
    validate_environment
    
    # Create backup
    create_backup
    
    # Update code
    log_info "📥 Updating application code..."
    cd "$PROJECT_ROOT"
    git fetch origin
    git checkout "$VERSION"
    
    # Build and deploy
    log_info "🔨 Building and starting services..."
    docker compose -f "$COMPOSE_FILE" build --no-cache agente-api
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
    
    # Wait for services to be ready
    sleep 30
    
    # Validate deployment
    if ! validate_deployment; then
        log_error "Deployment validation failed"
        rollback
    fi
    
    # Clean up old Docker images
    log_info "🧹 Cleaning up old Docker images..."
    docker image prune -f
    
    # Final success message
    log_success "🎉 Deployment completed successfully!"
    log_info "Services are available at:"
    log_info "  - API: http://localhost:8000"
    log_info "  - Health: http://localhost:8000/health/ready"
    log_info "  - Metrics: http://localhost:8000/metrics"
    
    # Remove rollback trap
    trap - ERR
}

# ============================================================================
# Script Execution
# ============================================================================

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")" || {
    # If we can't create the log directory, use local logging
    LOG_FILE="./deploy.log"
    log_warning "Could not create log directory, using local file: $LOG_FILE"
}

# Execute main function
main "$@"
