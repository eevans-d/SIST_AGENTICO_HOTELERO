#!/usr/bin/env bash
set -euo pipefail

###############################################
# Canary Deploy Script - Production Ready
# Objetivo: realizar despliegue progresivo validando métricas
# Usage: ./canary-deploy.sh [env] [version] [traffic_percentage]
###############################################

# ============================================================================
# Configuration
# ============================================================================

ENV="${1:-staging}"
VERSION="${2:-$(git rev-parse --short HEAD)}"
TRAFFIC_PERCENTAGE="${3:-10}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="./canary-deploy.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Deployment configuration
HEALTH_CHECK_URL="http://localhost:8000/health/ready"
PROMETHEUS_URL="http://localhost:9090"
CANARY_DURATION_MINUTES=10
ROLLBACK_ON_ERROR_RATE_THRESHOLD=5.0  # 5% error rate triggers rollback
ROLLBACK_ON_LATENCY_P95_THRESHOLD=2000  # 2000ms P95 latency triggers rollback

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
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Utility Functions
# ============================================================================

check_prerequisites() {
    log_info "🔍 Checking prerequisites..."
    
    # Check required tools
    for tool in docker curl jq; do
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
    
    # Check Prometheus is accessible
    if ! curl -s "$PROMETHEUS_URL/api/v1/status/config" > /dev/null; then
        log_warning "Prometheus not accessible at $PROMETHEUS_URL - metrics validation will be limited"
    fi
    
    log_success "Prerequisites check passed"
}

build_canary_image() {
    log_info "🔨 Building canary image for version $VERSION..."
    
    cd "$PROJECT_ROOT"
    
    # Build the new version
    docker build -f Dockerfile.production -t "agente-hotel-api:canary-$VERSION" .
    
    # Tag as canary
    docker tag "agente-hotel-api:canary-$VERSION" "agente-hotel-api:canary"
    
    log_success "Canary image built successfully"
}

deploy_canary() {
    log_info "🐤 Deploying canary version..."
    
    cd "$PROJECT_ROOT"
    
    # Create canary compose override
    cat > docker-compose.canary.yml << EOF
version: '3.8'
services:
  agente-api-canary:
    build:
      context: .
      dockerfile: Dockerfile.production
    image: agente-hotel-api:canary
    container_name: agente-api-canary
    env_file: .env.production
    environment:
      - SERVICE_NAME=agente-api-canary
      - CANARY_VERSION=$VERSION
    networks:
      - backend_network
    ports:
      - "8001:8000"  # Different port for canary
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 15s
      timeout: 5s
      retries: 3
    labels:
      - "deployment.type=canary"
      - "deployment.version=$VERSION"
      - "deployment.traffic_percentage=$TRAFFIC_PERCENTAGE"

networks:
  backend_network:
    external: true
EOF
    
    # Deploy canary
    docker compose -f docker-compose.canary.yml up -d agente-api-canary
    
    # Wait for canary to be healthy
    local attempt=1
    local max_attempts=12
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://localhost:8001/health/ready" > /dev/null; then
            log_success "Canary deployment is healthy"
            return 0
        fi
        
        log_info "Waiting for canary to be ready... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    log_error "Canary deployment failed health check after $max_attempts attempts"
    return 1
}

configure_traffic_routing() {
    log_info "🚦 Configuring traffic routing ($TRAFFIC_PERCENTAGE% to canary)..."
    
    # In a real production environment, this would configure a load balancer
    # For demonstration purposes, we'll create a simple nginx configuration
    
    cat > /tmp/nginx-canary.conf << EOF
upstream backend {
    # Main production servers (90% traffic)
    server agente-api:8000 weight=90;
    # Canary server (10% traffic)
    server agente-api-canary:8000 weight=$TRAFFIC_PERCENTAGE;
}

server {
    listen 80;
    server_name localhost;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # Add canary headers for monitoring
        add_header X-Canary-Routing "enabled" always;
        add_header X-Traffic-Split "$TRAFFIC_PERCENTAGE%" always;
    }
    
    # Health check endpoint that doesn't use load balancing
    location /health/ {
        proxy_pass http://agente-api:8000;
        proxy_set_header Host \$host;
    }
    
    # Canary-specific health check
    location /canary/health/ {
        proxy_pass http://agente-api-canary:8000/health/;
        proxy_set_header Host \$host;
    }
}
EOF
    
    log_success "Traffic routing configured"
}

monitor_canary_metrics() {
    log_info "📊 Monitoring canary metrics for $CANARY_DURATION_MINUTES minutes..."
    
    local start_time=$(date +%s)
    local end_time=$((start_time + CANARY_DURATION_MINUTES * 60))
    local check_interval=30  # Check every 30 seconds
    
    while [[ $(date +%s) -lt $end_time ]]; do
        # Check error rate
        local error_rate=$(query_error_rate)
        log_info "Current error rate: ${error_rate}%"
        
        if (( $(echo "$error_rate > $ROLLBACK_ON_ERROR_RATE_THRESHOLD" | bc -l) )); then
            log_error "Error rate threshold exceeded: ${error_rate}% > ${ROLLBACK_ON_ERROR_RATE_THRESHOLD}%"
            return 1
        fi
        
        # Check P95 latency
        local p95_latency=$(query_p95_latency)
        log_info "Current P95 latency: ${p95_latency}ms"
        
        if (( $(echo "$p95_latency > $ROLLBACK_ON_LATENCY_P95_THRESHOLD" | bc -l) )); then
            log_error "Latency threshold exceeded: ${p95_latency}ms > ${ROLLBACK_ON_LATENCY_P95_THRESHOLD}ms"
            return 1
        fi
        
        # Check canary health
        if ! curl -f -s "http://localhost:8001/health/live" > /dev/null; then
            log_error "Canary health check failed"
            return 1
        fi
        
        local remaining_time=$(( (end_time - $(date +%s)) / 60 ))
        log_info "Canary monitoring continues... ${remaining_time} minutes remaining"
        
        sleep $check_interval
    done
    
    log_success "Canary monitoring completed successfully"
    return 0
}

query_error_rate() {
    # Query Prometheus for error rate (if available)
    local query="rate(http_requests_total{status=~\"5..\"}[5m])/rate(http_requests_total[5m])*100"
    local result=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=$query" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
    echo "${result:-0}"
}

query_p95_latency() {
    # Query Prometheus for P95 latency (if available)
    local query="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))*1000"
    local result=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=$query" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
    echo "${result:-0}"
}

promote_canary() {
    log_info "🚀 Promoting canary to production..."
    
    cd "$PROJECT_ROOT"
    
    # Tag canary as the new production version
    docker tag "agente-hotel-api:canary-$VERSION" "agente-hotel-api:latest"
    docker tag "agente-hotel-api:canary-$VERSION" "agente-hotel-api:production"
    
    # Update production deployment
    docker compose -f docker-compose.production.yml pull agente-api
    docker compose -f docker-compose.production.yml up -d agente-api
    
    # Wait for production to stabilize
    sleep 30
    
    # Verify production health
    if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
        log_success "Production deployment is healthy"
        
        # Clean up canary deployment
        docker compose -f docker-compose.canary.yml down
        rm -f docker-compose.canary.yml
        
        log_success "Canary promotion completed successfully"
        return 0
    else
        log_error "Production deployment health check failed after promotion"
        return 1
    fi
}

rollback_canary() {
    log_error "🔄 Rolling back canary deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop and remove canary deployment
    docker compose -f docker-compose.canary.yml down || true
    rm -f docker-compose.canary.yml /tmp/nginx-canary.conf
    
    # Remove canary images
    docker rmi "agente-hotel-api:canary-$VERSION" "agente-hotel-api:canary" || true
    
    log_error "Canary deployment rolled back"
}

# ============================================================================
# Main Canary Deployment Logic
# ============================================================================

main() {
    log_info "🐤 Starting canary deployment for env=$ENV version=$VERSION traffic=$TRAFFIC_PERCENTAGE%"
    
    # Set up error handling
    trap rollback_canary ERR
    
    # Validation and prerequisites
    check_prerequisites
    
    # Build and deploy canary
    build_canary_image
    deploy_canary
    
    # Configure traffic routing (in production, this would be done via load balancer)
    configure_traffic_routing
    
    # Monitor canary metrics
    if monitor_canary_metrics; then
        log_success "Canary metrics validation passed"
        
        # Promote canary to production
        if promote_canary; then
            log_success "🎉 Canary deployment completed successfully!"
            log_info "Version $VERSION is now running in production"
        else
            log_error "Canary promotion failed"
            rollback_canary
            exit 1
        fi
    else
        log_error "Canary metrics validation failed"
        rollback_canary
        exit 1
    fi
    
    # Remove rollback trap
    trap - ERR
}

# ============================================================================
# Script Execution
# ============================================================================

echo "Canary deployment started at $(date)" > "$LOG_FILE"
main "$@"
