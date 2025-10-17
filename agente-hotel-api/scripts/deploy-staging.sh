#!/usr/bin/env bash

# Script de despliegue para ambiente de staging
# Autor: Copilot
# Fecha: 2025-10-07

set -e  # Detener en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio del proyecto
PROJECT_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")
cd "$PROJECT_DIR"

# Variables de entorno
STAGE=${1:-staging}
DOCKER_COMPOSE_FILE="docker-compose.${STAGE}.yml"
ENV_FILE=".env.${STAGE}"

# Funciones de utilidad
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

# Verificación de requisitos
check_requirements() {
    log_info "Verificando requisitos..."
    
    # Verificar archivo docker-compose
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        log_error "El archivo $DOCKER_COMPOSE_FILE no existe"
        exit 1
    fi
    
    # Verificar archivo .env
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "El archivo $ENV_FILE no existe. Se usarán valores por defecto"
        log_info "Creando archivo $ENV_FILE desde .env.example..."
        cp .env.example "$ENV_FILE"
    fi
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose no está instalado"
        exit 1
    fi
    
    log_success "Todos los requisitos verificados correctamente"
}

# Función para crear backup antes del despliegue
create_backup() {
    log_info "Creando backup antes del despliegue..."
    
    BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Exportar datos de postgres si el contenedor está corriendo
    if docker ps | grep -q postgres; then
        log_info "Exportando datos de PostgreSQL..."
        docker exec postgres pg_dump -U postgres agente_hotel > "$BACKUP_DIR/postgres_backup.sql" || \
            log_warning "No se pudo crear backup de PostgreSQL"
    fi
    
    # Backup de redis si está corriendo
    if docker ps | grep -q redis; then
        log_info "Exportando datos de Redis..."
        docker exec redis redis-cli SAVE || log_warning "No se pudo crear backup de Redis"
        docker cp redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb" || \
            log_warning "No se pudo copiar backup de Redis"
    fi
    
    # Copiar archivos de configuración
    cp "$ENV_FILE" "$BACKUP_DIR/" || log_warning "No se pudo copiar $ENV_FILE"
    cp "$DOCKER_COMPOSE_FILE" "$BACKUP_DIR/" || log_warning "No se pudo copiar $DOCKER_COMPOSE_FILE"
    
    log_success "Backup creado en $BACKUP_DIR"
}

# Validar configuración PMS
validate_pms_config() {
    log_info "Validando configuración de PMS..."
    
    # Extraer variables del archivo .env
    PMS_TYPE=$(grep -E '^PMS_TYPE=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '"')
    PMS_BASE_URL=$(grep -E '^PMS_BASE_URL=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '"')
    PMS_API_KEY=$(grep -E '^PMS_API_KEY=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '"')
    
    # Validar que tengan valores
    if [ "$PMS_TYPE" != "qloapps" ]; then
        log_warning "PMS_TYPE no está configurado como 'qloapps'"
        
        echo -n "¿Deseas configurar PMS_TYPE=qloapps ahora? (s/n): "
        read -r RESP
        if [[ "$RESP" =~ ^[Ss]$ ]]; then
            sed -i 's/^PMS_TYPE=.*/PMS_TYPE=qloapps/' "$ENV_FILE"
            log_success "PMS_TYPE actualizado a 'qloapps'"
        fi
    fi
    
    if [ -z "$PMS_BASE_URL" ] || [ "$PMS_BASE_URL" = "https://example.com" ]; then
        log_warning "PMS_BASE_URL no está configurado correctamente"
        
        echo -n "Ingresa la URL base de QloApps: "
        read -r NEW_URL
        if [ -n "$NEW_URL" ]; then
            sed -i "s|^PMS_BASE_URL=.*|PMS_BASE_URL=$NEW_URL|" "$ENV_FILE"
            log_success "PMS_BASE_URL actualizado a '$NEW_URL'"
        fi
    fi
    
    if [ -z "$PMS_API_KEY" ] || [ "$PMS_API_KEY" = "changeme" ]; then
        log_warning "PMS_API_KEY no está configurado correctamente"
        
        echo -n "Ingresa la API key de QloApps: "
        read -r NEW_KEY
        if [ -n "$NEW_KEY" ]; then
            sed -i "s|^PMS_API_KEY=.*|PMS_API_KEY=$NEW_KEY|" "$ENV_FILE"
            log_success "PMS_API_KEY actualizado"
        fi
    fi
    
    log_success "Configuración de PMS validada"
}

# Ejecutar pruebas antes del despliegue
run_preflight_tests() {
    log_info "Ejecutando pruebas previas al despliegue..."
    
    # Verificar conexión a QloApps
    log_info "Verificando conexión a QloApps..."
    set +e  # No detener en caso de error
    python scripts/setup_qloapps.py connection
    RESULT=$?
    set -e  # Restaurar comportamiento
    
    if [ $RESULT -ne 0 ]; then
        log_error "Error al conectar con QloApps"
        echo -n "¿Deseas continuar con el despliegue de todas formas? (s/n): "
        read -r RESP
        if [[ ! "$RESP" =~ ^[Ss]$ ]]; then
            log_error "Despliegue cancelado por el usuario"
            exit 1
        fi
    else
        log_success "Conexión a QloApps verificada correctamente"
    fi
    
    # Ejecutar pruebas de integración básicas
    log_info "Ejecutando pruebas básicas..."
    python -m pytest tests/unit/test_pms_adapter.py -v || \
        log_warning "Algunas pruebas fallaron, verifica los detalles"
}

# Desplegar con Docker Compose
deploy_application() {
    log_info "Desplegando aplicación en ambiente $STAGE..."
    
    # Verificar si hay contenedores corriendo
    if docker ps | grep -q agente-api; then
        log_info "Deteniendo contenedores existentes..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" --env-file "$ENV_FILE" down || \
            log_warning "No se pudieron detener todos los contenedores"
    fi
    
    # Construir y levantar contenedores
    log_info "Construyendo y levantando contenedores..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" --env-file "$ENV_FILE" build
    docker-compose -f "$DOCKER_COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    log_success "Aplicación desplegada correctamente"
}

# Verificar estado de servicios
check_services_health() {
    log_info "Verificando estado de los servicios..."
    sleep 5  # Esperar a que los servicios inicien
    
    # Verificar servicio API
    if docker ps | grep -q agente-api; then
        log_info "Verificando estado de API..."
        curl -s http://localhost:8000/health/live || \
            log_warning "No se puede acceder a /health/live"
        
        curl -s http://localhost:8000/health/ready || \
            log_warning "No se puede acceder a /health/ready"
    else
        log_error "El servicio API no está corriendo"
    fi
    
    # Verificar Prometheus
    if docker ps | grep -q prometheus; then
        log_info "Verificando estado de Prometheus..."
        curl -s http://localhost:9090/-/healthy || \
            log_warning "No se puede acceder a Prometheus health check"
    else
        log_warning "Prometheus no está corriendo"
    fi
    
    # Verificar Grafana
    if docker ps | grep -q grafana; then
        log_info "Verificando estado de Grafana..."
        curl -s http://localhost:3000/api/health || \
            log_warning "No se puede acceder a Grafana health check"
    else
        log_warning "Grafana no está corriendo"
    fi
    
    log_info "Verificación de servicios completada"
}

# Función principal
main() {
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}=== SCRIPT DE DESPLIEGUE PARA $STAGE ===${NC}"
    echo -e "${BLUE}=========================================${NC}"
    
    check_requirements
    create_backup
    validate_pms_config
    run_preflight_tests
    deploy_application
    check_services_health
    
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}=== DESPLIEGUE COMPLETADO CON ÉXITO ===${NC}"
    echo -e "${GREEN}=========================================${NC}"
    log_info "Verifica los logs con: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
}

# Ejecutar script
main