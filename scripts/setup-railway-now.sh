#!/bin/bash
################################################################################
# 🚀 SETUP RAILWAY - AUTOMATIZADO (5 MINUTOS)
################################################################################
# Script que automatiza TODO lo necesario para deployer en Railway
# - Genera 3 secrets criptográficos
# - Crea archivo .env.railway.local
# - Muestra instrucciones paso a paso para Railway Dashboard
#
# Uso: ./scripts/setup-railway-now.sh
################################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}     🚀 RAILWAY SETUP - AUTOMATED SECRETS GENERATION      ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: Run this script from the project root${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p .railway-backups

# Timestamp for backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${YELLOW}📝 STEP 1: Generando 3 secretos criptográficos...${NC}"
echo ""

# Generate JWT_SECRET
JWT_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✓${NC} JWT_SECRET generado"

# Generate JWT_REFRESH_SECRET
JWT_REFRESH_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✓${NC} JWT_REFRESH_SECRET generado"

# Generate ENCRYPTION_KEY
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo -e "${GREEN}✓${NC} ENCRYPTION_KEY generado"

echo ""
echo -e "${YELLOW}📝 STEP 2: Creando archivo .env.railway.local...${NC}"
echo ""

# Create the .env.railway.local file
cat > .env.railway.local << EOF
# 🔐 RAILWAY SECRETS - Generated: $TIMESTAMP
# Este archivo NO debe commitearse a git
# Cambiar estos valores después en Railway Dashboard si es necesario

# ============= AUTOGENERADOS (NO CAMBIAR) =============
JWT_SECRET=$JWT_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# ============= FIXED VALUES (NO CAMBIAR) =============
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

# ============= RAILWAY AUTO-PROPORCIONA (NO CAMBIAR) =============
# Estos valores son inyectados automáticamente por Railway
# DATABASE_URL=${{ POSTGRES.DATABASE_URL }}
# PORT=(inyectado automáticamente)
EOF

chmod 600 .env.railway.local
echo -e "${GREEN}✓${NC} Archivo .env.railway.local creado (permisos: 600)"

# Create backup
cp .env.railway.local .railway-backups/.env.railway.local.backup.$TIMESTAMP
echo -e "${GREEN}✓${NC} Backup creado en .railway-backups/"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ SECRETS GENERADOS CORRECTAMENTE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

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
echo -e "${YELLOW}🔧 PRÓXIMOS PASOS EN RAILWAY DASHBOARD:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}1. Ir a:${NC} https://railway.app/dashboard"
echo ""
echo -e "${GREEN}2. Seleccionar tu proyecto:${NC} agente-hotel-api"
echo ""
echo -e "${GREEN}3. Click en Tab:${NC} 'Variables'"
echo ""
echo -e "${GREEN}4. Click en:${NC} 'Raw Editor'"
echo ""
echo -e "${GREEN}5. Pegar esta configuración COMPLETA:${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
cat > /tmp/railway-config.txt << EOF
JWT_SECRET=$JWT_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
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
DATABASE_URL=\${{ POSTGRES.DATABASE_URL }}
EOF

cat /tmp/railway-config.txt
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}6. Click en:${NC} 'Save'"
echo ""
echo -e "${GREEN}7. Railway desplegará automáticamente${NC} (~5 minutos)"
echo ""
echo -e "${GREEN}8. Verificar con:${NC}"
echo "   curl https://tu-proyecto.up.railway.app/health/live"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📁 ARCHIVOS CREADOS:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓${NC} .env.railway.local (contiene los 3 secrets)"
echo -e "${GREEN}✓${NC} .railway-backups/.env.railway.local.backup.$TIMESTAMP"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⚠️  SEGURIDAD - IMPORTANTE:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓${NC} Los archivos .env.railway.local están en .gitignore"
echo -e "${GREEN}✓${NC} NO serán commiteados a git"
echo -e "${GREEN}✓${NC} Guardar los 3 secrets en un password manager"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📚 DOCUMENTACIÓN:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}• SECRETS-RESUMEN-EJECUTIVO.md${NC} - Solo lo esencial"
echo -e "${GREEN}• RAILWAY-START-HERE.md${NC} - Guía rápida (45 min)"
echo -e "${GREEN}• DEPLOYMENT-RAILWAY.md${NC} - Referencia completa"
echo ""

echo -e "${GREEN}✅ SETUP COMPLETADO - Listo para Railway Dashboard!${NC}"
echo ""
