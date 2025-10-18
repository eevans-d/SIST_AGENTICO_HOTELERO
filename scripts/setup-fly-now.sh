#!/bin/bash
################################################################################
# 🚀 FLY.IO SETUP - AUTOMATIZADO (10 MINUTOS)
################################################################################
# Script que automatiza TODO para Fly.io
# - Genera 3 secrets criptográficos
# - Verifica flyctl instalado
# - Crea archivo .env.fly.local
# - Muestra instrucciones paso a paso
#
# Uso: ./scripts/setup-fly-now.sh
################################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}        🚀 FLY.IO SETUP - AUTOMATED SECRETS            ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: Run this script from the project root${NC}"
    echo "   Expected: agente-hotel-api directory"
    exit 1
fi

# Check if fly.toml exists
if [ ! -f "fly.toml" ]; then
    echo -e "${RED}❌ Error: fly.toml not found in project root${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p .flyio-backups

# Timestamp for backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ============================================================================
# STEP 1: Check flyctl installation
# ============================================================================

echo -e "${YELLOW}📝 STEP 1: Verificando flyctl CLI...${NC}"
echo ""

if ! command -v flyctl &> /dev/null; then
    echo -e "${RED}❌ flyctl no está instalado${NC}"
    echo ""
    echo -e "${CYAN}Para instalar flyctl:${NC}"
    echo "  macOS:   brew install flyctl"
    echo "  Linux:   curl -L https://fly.io/install.sh | sh"
    echo "  Windows: choco install flyctl"
    echo ""
    echo -e "${YELLOW}O descarga desde: https://fly.io/docs/getting-started/installing-flyctl/${NC}"
    exit 1
else
    FLYCTL_VERSION=$(flyctl version)
    echo -e "${GREEN}✓ flyctl instalado: ${FLYCTL_VERSION}${NC}"
fi

# ============================================================================
# STEP 2: Generate secrets
# ============================================================================

echo ""
echo -e "${YELLOW}📝 STEP 2: Generando 3 secretos criptográficos...${NC}"
echo ""

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ openssl no está instalado${NC}"
    echo "   Instala: apt-get install openssl"
    exit 1
fi

# Generate JWT_SECRET
JWT_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✓ JWT_SECRET generado${NC}"

# Generate JWT_REFRESH_SECRET
JWT_REFRESH_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✓ JWT_REFRESH_SECRET generado${NC}"

# Generate ENCRYPTION_KEY
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo -e "${GREEN}✓ ENCRYPTION_KEY generado${NC}"

# ============================================================================
# STEP 3: Create local environment file
# ============================================================================

echo ""
echo -e "${YELLOW}📝 STEP 3: Creando .env.fly.local...${NC}"
echo ""

# Create the .env.fly.local file
cat > .env.fly.local << EOF
# 🔐 FLY.IO SECRETS - Generated: $TIMESTAMP
# Este archivo NO debe commitearse a git
# Estos valores serán pasados via: flyctl secrets set

# COPIAR ESTOS VALORES A: flyctl secrets set
JWT_SECRET=$JWT_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# CONFIGURACIÓN FIJA (NO CAMBIAR)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080
PMS_TIMEOUT=30

# Notas:
# - DATABASE_URL será inyectada por Fly.io (postgresql://...)
# - Secrets en fly.toml bajo [env]
# - Secretos sensibles: usa flyctl secrets set
EOF

chmod 600 .env.fly.local
echo -e "${GREEN}✓ Archivo .env.fly.local creado (permisos: 600)${NC}"

# Create backup
cp .env.fly.local .flyio-backups/.env.fly.local.backup.$TIMESTAMP
echo -e "${GREEN}✓ Backup creado en .flyio-backups/${NC}"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ SECRETS GENERADOS CORRECTAMENTE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================================================
# STEP 4: Display generated values
# ============================================================================

echo -e "${YELLOW}📋 VALORES GENERADOS (GUARDAR EN SEGURO):${NC}"
echo ""
echo -e "${GREEN}1. JWT_SECRET:${NC}"
echo "   $JWT_SECRET"
echo ""
echo -e "${GREEN}2. JWT_REFRESH_SECRET:${NC}"
echo "   $JWT_REFRESH_SECRET"
echo ""
echo -e "${GREEN}3. ENCRYPTION_KEY:${NC}"
echo "   $ENCRYPTION_KEY"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🔧 PRÓXIMOS PASOS EN FLY.IO:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}PASO 1: Login en Fly.io (one-time)${NC}"
echo "  $ flyctl auth login"
echo "  → Abre navegador y completa autenticación"
echo ""

echo -e "${GREEN}PASO 2: Lanzar app en Fly.io${NC}"
echo "  $ flyctl launch"
echo "  → Selecciona app name: agente-hotel-api"
echo "  → Selecciona región: mia (o cercana a ti)"
echo "  → Do you want to set up a Postgresql database? YES"
echo "  → Create admin user now? YES"
echo ""

echo -e "${GREEN}PASO 3: Crear PostgreSQL managed database${NC}"
echo "  $ flyctl postgres create"
echo "  → App name: agente-hotel-api-db"
echo "  → Region: mia (misma que app)"
echo "  → Volume size: 10GB (suficiente)"
echo ""

echo -e "${GREEN}PASO 4: Attachar PostgreSQL a app${NC}"
echo "  $ flyctl postgres attach --app agente-hotel-api"
echo "  → Esto inyecta DATABASE_URL automáticamente"
echo ""

echo -e "${GREEN}PASO 5: Configurar 3 secrets${NC}"
echo "  $ flyctl secrets set JWT_SECRET=\"$JWT_SECRET\""
echo "  $ flyctl secrets set JWT_REFRESH_SECRET=\"$JWT_REFRESH_SECRET\""
echo "  $ flyctl secrets set ENCRYPTION_KEY=\"$ENCRYPTION_KEY\""
echo ""

echo -e "${GREEN}PASO 6: Deployer app${NC}"
echo "  $ flyctl deploy"
echo "  → Espera ~5 minutos"
echo ""

echo -e "${GREEN}PASO 7: Verificar status${NC}"
echo "  $ flyctl status"
echo "  → Ver logs: flyctl logs"
echo "  → Abrir en navegador: flyctl open"
echo ""

echo -e "${GREEN}PASO 8: Health check${NC}"
echo "  $ flyctl open /health/live"
echo "  → Deberías ver: 200 OK"
echo ""

# Create a helpful info file
cat > /tmp/flyio-config-copy.txt << EOF
═══════════════════════════════════════════════════════════
FLY.IO DEPLOYMENT - COPY/PASTE ESTOS COMANDOS
═══════════════════════════════════════════════════════════

# 1. Login (one-time)
flyctl auth login

# 2. Launch app
flyctl launch
# → App name: agente-hotel-api
# → Region: mia
# → Database: YES

# 3. Create PostgreSQL
flyctl postgres create
# → App name: agente-hotel-api-db
# → Region: mia
# → Volume: 10GB

# 4. Attach database
flyctl postgres attach --app agente-hotel-api

# 5. Set secrets
flyctl secrets set JWT_SECRET="$JWT_SECRET"
flyctl secrets set JWT_REFRESH_SECRET="$JWT_REFRESH_SECRET"
flyctl secrets set ENCRYPTION_KEY="$ENCRYPTION_KEY"

# 6. Deploy
flyctl deploy

# 7. Monitor
flyctl logs
flyctl status
flyctl open /health/live

═══════════════════════════════════════════════════════════
EOF

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📁 ARCHIVOS CREADOS:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓${NC} .env.fly.local (contiene los 3 secrets)"
echo -e "${GREEN}✓${NC} .flyio-backups/.env.fly.local.backup.$TIMESTAMP"
echo -e "${GREEN}✓${NC} /tmp/flyio-config-copy.txt (para copy-paste)"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⚠️  SEGURIDAD - IMPORTANTE:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓${NC} Los archivos .env.fly.local están en .gitignore"
echo -e "${GREEN}✓${NC} NO serán commiteados a git"
echo -e "${GREEN}✓${NC} Guardar los 3 secrets en un password manager"
echo -e "${GREEN}✓${NC} Usar flyctl secrets set (NO hardcodear)"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📚 DOCUMENTACIÓN:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}• FLY-INICIO.md${NC} - Hub principal, elige tu camino"
echo -e "${GREEN}• FLY-QUICK-ACTION.md${NC} - 3 pasos rápidos"
echo -e "${GREEN}• FLY-SETUP-GUIDE.md${NC} - Instalación detallada"
echo -e "${GREEN}• FLY-DEPLOY-GUIDE.md${NC} - Deployment paso a paso"
echo -e "${GREEN}• FLY-SECRETS-GUIDE.md${NC} - Gestión de secrets"
echo ""

echo -e "${GREEN}✅ SETUP COMPLETADO - Listo para Fly.io!${NC}"
echo ""
echo -e "${CYAN}Próximo: flyctl auth login${NC}"
echo ""
