#!/bin/bash

# ============================================================================
# DEV SETUP SCRIPT - Agente Hotelero
# ============================================================================
# Configuración automática del entorno de desarrollo
# Autor: GitHub Copilot
# Fecha: October 4, 2025
#
# USO:
#   ./dev-setup.sh              # Setup completo
#   ./dev-setup.sh --minimal    # Setup mínimo (sin herramientas opcionales)
#   ./dev-setup.sh --help       # Mostrar ayuda
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MINIMAL_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║       🚀 AGENTE HOTELERO - DEV SETUP AUTOMÁTICO 🚀           ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 está instalado"
        return 0
    else
        log_error "$1 NO está instalado"
        return 1
    fi
}

# ============================================================================
# PREREQUISITOS
# ============================================================================

check_prerequisites() {
    log_info "Verificando prerrequisitos..."
    
    local all_good=true
    
    # Esenciales
    if ! check_command "docker"; then
        all_good=false
        echo "   → Instalar: https://docs.docker.com/get-docker/"
    fi
    
    if ! check_command "docker-compose"; then
        all_good=false
        echo "   → Instalar: https://docs.docker.com/compose/install/"
    fi
    
    if ! check_command "python3"; then
        all_good=false
        echo "   → Instalar: https://www.python.org/downloads/"
    fi
    
    if ! check_command "poetry"; then
        log_warning "Poetry no está instalado (recomendado)"
        echo "   → Instalar: curl -sSL https://install.python-poetry.org | python3 -"
    fi
    
    # Opcionales pero útiles
    if ! check_command "git"; then
        log_warning "Git no está instalado (recomendado)"
    fi
    
    if ! check_command "make"; then
        log_warning "Make no está instalado (recomendado)"
    fi
    
    # Docker daemon check
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon no está corriendo"
        echo "   → Iniciar Docker Desktop o ejecutar: sudo systemctl start docker"
        all_good=false
    fi
    
    echo ""
    
    if [ "$all_good" = false ]; then
        log_error "Faltan prerrequisitos esenciales. Por favor instálalos primero."
        exit 1
    fi
    
    log_success "Todos los prerrequisitos esenciales están instalados"
}

# ============================================================================
# ENVIRONMENT FILE
# ============================================================================

setup_env_file() {
    log_info "Configurando archivo .env..."
    
    if [ -f ".env" ]; then
        log_warning ".env ya existe. ¿Sobrescribir? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Manteniendo .env existente"
            return
        fi
    fi
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_success ".env creado desde .env.example"
        
        # Generar secretos aleatorios
        if command -v openssl &> /dev/null; then
            log_info "Generando secretos aleatorios..."
            
            JWT_SECRET=$(openssl rand -hex 32)
            ENCRYPTION_KEY=$(openssl rand -hex 32)
            
            # Reemplazar en .env (macOS compatible)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/jwt_secret_change_me_in_production/$JWT_SECRET/" .env
                sed -i '' "s/encryption_key_change_me_32_chars/$ENCRYPTION_KEY/" .env
            else
                sed -i "s/jwt_secret_change_me_in_production/$JWT_SECRET/" .env
                sed -i "s/encryption_key_change_me_32_chars/$ENCRYPTION_KEY/" .env
            fi
            
            log_success "Secretos generados y configurados"
        fi
    else
        log_error ".env.example no encontrado"
        exit 1
    fi
}

# ============================================================================
# PYTHON DEPENDENCIES
# ============================================================================

install_dependencies() {
    log_info "Instalando dependencias de Python..."
    
    if command -v poetry &> /dev/null; then
        poetry install --all-extras
        log_success "Dependencias instaladas con Poetry"
    else
        log_warning "Poetry no encontrado, usando pip..."
        if [ -f "requirements.txt" ]; then
            python3 -m pip install -r requirements.txt
            log_success "Dependencias instaladas con pip"
        else
            log_error "requirements.txt no encontrado"
        fi
    fi
}

# ============================================================================
# GIT HOOKS
# ============================================================================

setup_git_hooks() {
    if [ ! -d ".git" ]; then
        log_warning "No es un repositorio git, saltando hooks"
        return
    fi
    
    log_info "Configurando git hooks..."
    
    # Pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "🔍 Running pre-commit checks..."

# Run linter
make lint
if [ $? -ne 0 ]; then
    echo "❌ Linter failed. Please fix the issues."
    exit 1
fi

# Run tests
make test
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Please fix the issues."
    exit 1
fi

echo "✅ Pre-commit checks passed!"
EOF

    chmod +x .git/hooks/pre-commit
    log_success "Git hooks configurados"
}

# ============================================================================
# DOCKER SETUP
# ============================================================================

setup_docker() {
    log_info "Configurando Docker..."
    
    # Pull images
    log_info "Descargando imágenes de Docker (esto puede tardar)..."
    docker compose -f docker-compose.dev.yml pull --quiet
    
    # Build agente-api
    log_info "Construyendo imagen de agente-api..."
    docker compose -f docker-compose.dev.yml build --quiet
    
    log_success "Docker configurado"
}

# ============================================================================
# DATABASE INIT
# ============================================================================

init_database() {
    log_info "Inicializando base de datos..."
    
    # Start postgres
    docker compose -f docker-compose.dev.yml up -d postgres redis
    
    # Wait for postgres to be ready
    log_info "Esperando a que PostgreSQL esté listo..."
    sleep 5
    
    # Run migrations (if any)
    if [ -f "alembic.ini" ]; then
        log_info "Ejecutando migraciones..."
        poetry run alembic upgrade head || log_warning "No hay migraciones o falló"
    fi
    
    log_success "Base de datos inicializada"
}

# ============================================================================
# VALIDATE SETUP
# ============================================================================

validate_setup() {
    log_info "Validando setup..."
    
    # Start all services
    docker compose -f docker-compose.dev.yml up -d
    
    # Wait a bit
    sleep 10
    
    # Check health
    local healthy=true
    
    if ! docker compose -f docker-compose.dev.yml ps | grep -q "healthy"; then
        log_warning "Algunos servicios no están healthy todavía"
        healthy=false
    fi
    
    # Test API endpoint
    if curl -f http://localhost:8000/health/live &> /dev/null; then
        log_success "API está respondiendo"
    else
        log_warning "API no está respondiendo todavía"
        healthy=false
    fi
    
    if [ "$healthy" = true ]; then
        log_success "Setup validado correctamente"
    else
        log_warning "Setup completo pero algunos servicios necesitan más tiempo"
        log_info "Ejecuta 'docker compose -f docker-compose.dev.yml logs' para ver detalles"
    fi
}

# ============================================================================
# PRINT SUMMARY
# ============================================================================

print_summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║              ✅ SETUP COMPLETADO EXITOSAMENTE ✅              ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📋 SIGUIENTE PASOS:${NC}"
    echo ""
    echo "  1. Ver logs:"
    echo "     docker compose -f docker-compose.dev.yml logs -f"
    echo ""
    echo "  2. Acceder a servicios:"
    echo "     • API:        http://localhost:8000"
    echo "     • API Docs:   http://localhost:8000/docs"
    echo "     • Adminer:    http://localhost:8080 (usar --profile db-admin)"
    echo "     • Prometheus: http://localhost:9090 (usar --profile monitoring)"
    echo "     • Grafana:    http://localhost:3000 (usar --profile monitoring)"
    echo ""
    echo "  3. Comandos útiles:"
    echo "     make test     # Ejecutar tests"
    echo "     make lint     # Linter"
    echo "     make fmt      # Formatear código"
    echo "     make health   # Health check"
    echo ""
    echo "  4. Detener servicios:"
    echo "     docker compose -f docker-compose.dev.yml down"
    echo ""
    echo -e "${YELLOW}💡 TIP: Lee CONTRIBUTING.md para guías de desarrollo${NC}"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --minimal)
                MINIMAL_MODE=true
                shift
                ;;
            --help)
                echo "USO: ./dev-setup.sh [OPTIONS]"
                echo ""
                echo "OPTIONS:"
                echo "  --minimal    Setup mínimo (sin herramientas opcionales)"
                echo "  --help       Mostrar esta ayuda"
                exit 0
                ;;
            *)
                log_error "Opción desconocida: $1"
                echo "Usa --help para ver opciones disponibles"
                exit 1
                ;;
        esac
    done
    
    print_header
    
    # Run setup steps
    check_prerequisites
    setup_env_file
    install_dependencies
    
    if [ "$MINIMAL_MODE" = false ]; then
        setup_git_hooks
    fi
    
    setup_docker
    init_database
    validate_setup
    
    print_summary
}

# Run main
main "$@"
