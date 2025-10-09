#!/bin/bash

# Deploy Script para Agente Hotelero IA System
# Automatiza el despliegue completo del sistema en producción

set -euo pipefail

# Configuración de colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables de configuración
ENVIRONMENT=${1:-production}
PROJECT_NAME="agente-hotelero"
BACKUP_DIR="/var/backups/agente-hotel"
LOG_FILE="/var/log/agente-hotel/deploy.log"
CONFIG_DIR="$(dirname "$(realpath "$0")")"
PROJECT_ROOT="$(dirname "$CONFIG_DIR")"

# Función para logging
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Función para manejo de errores
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Función para verificar prerequisitos
check_prerequisites() {
    log "INFO" "Verificando prerequisitos del sistema..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker no está instalado"
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose no está instalado"
    fi
    
    # Verificar espacio en disco
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 5000000 ]; then  # 5GB mínimo
        error_exit "Espacio insuficiente en disco (mínimo 5GB requerido)"
    fi
    
    # Verificar memoria RAM
    local available_memory=$(free -k | grep "^Mem:" | awk '{print $2}')
    if [ "$available_memory" -lt 4000000 ]; then  # 4GB mínimo
        error_exit "Memoria RAM insuficiente (mínimo 4GB requerido)"
    fi
    
    log "INFO" "Prerequisitos verificados correctamente"
}

# Función para validar configuración
validate_configuration() {
    log "INFO" "Validando configuración del entorno..."
    
    local env_file="$PROJECT_ROOT/.env.$ENVIRONMENT"
    
    if [ ! -f "$env_file" ]; then
        error_exit "Archivo de configuración no encontrado: $env_file"
    fi
    
    # Variables requeridas
    local required_vars=(
        "POSTGRES_PASSWORD"
        "MYSQL_ROOT_PASSWORD"
        "QLOAPPS_DB_PASSWORD"
        "SECRET_KEY"
        "ENCRYPTION_KEY"
        "JWT_SECRET_KEY"
        "WHATSAPP_VERIFY_TOKEN"
        "WHATSAPP_ACCESS_TOKEN"
        "GRAFANA_ADMIN_PASSWORD"
        "ADMIN_EMAIL"
        "ADMIN_PASSWORD"
    )
    
    # Cargar variables de entorno
    source "$env_file"
    
    # Verificar variables requeridas
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error_exit "Variable de entorno requerida no definida: $var"
        fi
    done
    
    log "INFO" "Configuración validada correctamente"
}

# Función para crear directorios necesarios
create_directories() {
    log "INFO" "Creando estructura de directorios..."
    
    local directories=(
        "/data/postgres"
        "/data/redis"
        "/data/mysql"
        "/data/qloapps"
        "/data/prometheus"
        "/data/grafana"
        "/data/alertmanager"
        "/var/log/agente-hotel"
        "/var/backups/postgres"
        "/var/backups/mysql"
        "/var/backups/agente-hotel"
        "/etc/ssl/agente-hotel"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            sudo mkdir -p "$dir"
            sudo chown -R $(whoami):$(whoami) "$dir"
            log "INFO" "Directorio creado: $dir"
        fi
    done
}

# Función para configurar SSL
setup_ssl() {
    log "INFO" "Configurando certificados SSL..."
    
    local ssl_dir="/etc/ssl/agente-hotel"
    local domain=${QLOAPPS_DOMAIN:-localhost}
    
    if [ ! -f "$ssl_dir/server.crt" ] || [ ! -f "$ssl_dir/server.key" ]; then
        log "INFO" "Generando certificados SSL auto-firmados..."
        
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/server.key" \
            -out "$ssl_dir/server.crt" \
            -subj "/C=ES/ST=Madrid/L=Madrid/O=Hotel/CN=$domain"
        
        sudo chmod 600 "$ssl_dir/server.key"
        sudo chmod 644 "$ssl_dir/server.crt"
        
        log "INFO" "Certificados SSL generados correctamente"
    else
        log "INFO" "Certificados SSL ya existen"
    fi
}

# Función para realizar backup pre-deployment
create_backup() {
    log "INFO" "Creando backup pre-deployment..."
    
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/pre_deploy_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup de base de datos PostgreSQL (si existe)
    if docker ps | grep -q postgres-agente-prod; then
        log "INFO" "Realizando backup de PostgreSQL..."
        docker exec postgres-agente-prod pg_dump -U agente_user agente_db > "$backup_path/postgres_backup.sql"
    fi
    
    # Backup de base de datos MySQL (si existe)
    if docker ps | grep -q mysql-qloapps-prod; then
        log "INFO" "Realizando backup de MySQL..."
        docker exec mysql-qloapps-prod mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" qloapps_db > "$backup_path/mysql_backup.sql"
    fi
    
    # Backup de configuración
    cp -r "$PROJECT_ROOT/.env.$ENVIRONMENT" "$backup_path/"
    
    log "INFO" "Backup creado en: $backup_path"
}

# Función para construir imágenes
build_images() {
    log "INFO" "Construyendo imágenes Docker..."
    
    cd "$PROJECT_ROOT"
    
    # Construir imagen de la aplicación
    docker build -f Dockerfile.production -t "$PROJECT_NAME:$ENVIRONMENT" .
    
    log "INFO" "Imágenes construidas correctamente"
}

# Función para ejecutar tests de pre-deployment
run_pre_deployment_tests() {
    log "INFO" "Ejecutando tests de pre-deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Tests de unidad
    log "INFO" "Ejecutando tests de unidad..."
    docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim bash -c "
        pip install poetry &&
        poetry install --no-root &&
        poetry run pytest tests/unit/ -v
    "
    
    # Tests de integración (con servicios mock)
    log "INFO" "Ejecutando tests de integración..."
    docker-compose -f docker-compose.test.yml up -d
    sleep 30
    
    docker run --rm --network agente-hotel-test -v "$(pwd):/app" -w /app python:3.11-slim bash -c "
        pip install poetry &&
        poetry install --no-root &&
        poetry run pytest tests/integration/ -v
    "
    
    docker-compose -f docker-compose.test.yml down
    
    log "INFO" "Tests ejecutados correctamente"
}

# Función para deployment principal
deploy_services() {
    log "INFO" "Iniciando deployment de servicios..."
    
    cd "$PROJECT_ROOT"
    
    # Cargar variables de entorno
    export $(cat ".env.$ENVIRONMENT" | xargs)
    
    # Detener servicios existentes
    log "INFO" "Deteniendo servicios existentes..."
    docker-compose -f deploy/docker-compose.production.yml down || true
    
    # Deployment por etapas
    log "INFO" "Desplegando servicios de base de datos..."
    docker-compose -f deploy/docker-compose.production.yml up -d postgres-prod redis-prod mysql-qloapps-prod
    
    # Esperar a que las bases de datos estén listas
    log "INFO" "Esperando a que las bases de datos estén listas..."
    sleep 60
    
    # Verificar salud de bases de datos
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec postgres-agente-prod pg_isready -U agente_user -d agente_db > /dev/null 2>&1; then
            log "INFO" "PostgreSQL está listo"
            break
        fi
        log "INFO" "Esperando PostgreSQL... (intento $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error_exit "PostgreSQL no respondió en tiempo esperado"
    fi
    
    # Desplegar QloApps
    log "INFO" "Desplegando QloApps PMS..."
    docker-compose -f deploy/docker-compose.production.yml up -d qloapps-prod
    sleep 60
    
    # Desplegar aplicación principal
    log "INFO" "Desplegando aplicación principal..."
    docker-compose -f deploy/docker-compose.production.yml up -d agente-api
    
    # Desplegar servicios de monitoreo
    log "INFO" "Desplegando servicios de monitoreo..."
    docker-compose -f deploy/docker-compose.production.yml up -d prometheus-prod grafana-prod alertmanager-prod
    
    # Desplegar proxy reverso
    log "INFO" "Desplegando proxy reverso..."
    docker-compose -f deploy/docker-compose.production.yml up -d nginx-prod
    
    log "INFO" "Deployment completado"
}

# Función para verificar salud del sistema
health_check() {
    log "INFO" "Verificando salud del sistema..."
    
    local services=(
        "http://localhost:8000/health/ready:Aplicación Principal"
        "http://localhost:3000:Grafana"
        "http://localhost:9090:Prometheus"
        "http://localhost:80:QloApps"
    )
    
    local all_healthy=true
    
    for service in "${services[@]}"; do
        local url=$(echo "$service" | cut -d: -f1-2)
        local name=$(echo "$service" | cut -d: -f3)
        
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|302"; then
            log "INFO" "$name: ✓ Saludable"
        else
            log "ERROR" "$name: ✗ No responde"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log "INFO" "Todos los servicios están saludables"
        return 0
    else
        log "ERROR" "Algunos servicios no están respondiendo"
        return 1
    fi
}

# Función para configurar monitoreo post-deployment
setup_monitoring() {
    log "INFO" "Configurando monitoreo post-deployment..."
    
    # Configurar dashboards de Grafana
    sleep 30  # Esperar a que Grafana esté completamente iniciado
    
    # Importar dashboards predefinidos
    local grafana_url="http://admin:${GRAFANA_ADMIN_PASSWORD}@localhost:3000"
    
    # Dashboard principal del hotel
    curl -X POST \
        -H "Content-Type: application/json" \
        -d @"$PROJECT_ROOT/monitoring/dashboards/hotel_operations.json" \
        "$grafana_url/api/dashboards/db" || log "WARN" "No se pudo importar dashboard de operaciones"
    
    # Dashboard técnico
    curl -X POST \
        -H "Content-Type: application/json" \
        -d @"$PROJECT_ROOT/monitoring/dashboards/technical_metrics.json" \
        "$grafana_url/api/dashboards/db" || log "WARN" "No se pudo importar dashboard técnico"
    
    log "INFO" "Monitoreo configurado"
}

# Función para limpiar recursos obsoletos
cleanup() {
    log "INFO" "Limpiando recursos obsoletos..."
    
    # Remover imágenes sin usar
    docker image prune -f
    
    # Remover volúmenes huérfanos
    docker volume prune -f
    
    # Remover redes no utilizadas
    docker network prune -f
    
    log "INFO" "Limpieza completada"
}

# Función para mostrar información post-deployment
show_deployment_info() {
    log "INFO" "=== INFORMACIÓN DEL DEPLOYMENT ==="
    log "INFO" "Entorno: $ENVIRONMENT"
    log "INFO" "Aplicación Principal: http://localhost:8000"
    log "INFO" "QloApps PMS: http://localhost"
    log "INFO" "Grafana: http://localhost:3000 (admin/${GRAFANA_ADMIN_PASSWORD})"
    log "INFO" "Prometheus: http://localhost:9090"
    log "INFO" "AlertManager: http://localhost:9093"
    log "INFO" ""
    log "INFO" "Logs en tiempo real:"
    log "INFO" "  docker-compose -f deploy/docker-compose.production.yml logs -f"
    log "INFO" ""
    log "INFO" "Estado de servicios:"
    log "INFO" "  docker-compose -f deploy/docker-compose.production.yml ps"
    log "INFO" "=================================="
}

# Función principal
main() {
    log "INFO" "Iniciando deployment de Agente Hotelero IA System"
    log "INFO" "Entorno: $ENVIRONMENT"
    
    # Crear directorio de logs si no existe
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    sudo chown -R $(whoami):$(whoami) "$(dirname "$LOG_FILE")"
    
    # Verificar prerequisitos
    check_prerequisites
    
    # Validar configuración
    validate_configuration
    
    # Crear directorios necesarios
    create_directories
    
    # Configurar SSL
    setup_ssl
    
    # Crear backup pre-deployment
    create_backup
    
    # Construir imágenes
    build_images
    
    # Ejecutar tests pre-deployment
    if [ "${SKIP_TESTS:-false}" != "true" ]; then
        run_pre_deployment_tests
    else
        log "WARN" "Tests omitidos (SKIP_TESTS=true)"
    fi
    
    # Deployment principal
    deploy_services
    
    # Verificar salud del sistema
    local max_health_attempts=5
    local health_attempt=1
    
    while [ $health_attempt -le $max_health_attempts ]; do
        log "INFO" "Verificación de salud (intento $health_attempt/$max_health_attempts)..."
        
        if health_check; then
            break
        fi
        
        if [ $health_attempt -eq $max_health_attempts ]; then
            error_exit "Sistema no está saludable después de $max_health_attempts intentos"
        fi
        
        sleep 30
        ((health_attempt++))
    done
    
    # Configurar monitoreo
    setup_monitoring
    
    # Limpiar recursos obsoletos
    cleanup
    
    # Mostrar información del deployment
    show_deployment_info
    
    log "INFO" "Deployment completado exitosamente"
}

# Manejo de señales
trap 'log "ERROR" "Deployment interrumpido"; exit 1' INT TERM

# Verificar argumentos
if [ $# -gt 1 ]; then
    echo "Uso: $0 [environment]"
    echo "Entornos disponibles: production, staging"
    exit 1
fi

# Ejecutar función principal
main "$@"