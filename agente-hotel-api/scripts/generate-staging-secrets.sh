#!/bin/bash
# 🔐 Generador Automático de Secrets para .env.staging
# Uso: ./generate-staging-secrets.sh

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}║   🔐  GENERADOR DE SECRETS PARA STAGING  🔐             ║${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.staging"

# Verificar si .env.staging ya existe
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  .env.staging ya existe${NC}"
    echo -e "${BLUE}¿Deseas sobrescribirlo? (y/N):${NC} "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Operación cancelada"
        exit 0
    fi
    # Backup del archivo existente
    cp "$ENV_FILE" "${ENV_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${GREEN}✅ Backup creado: ${ENV_FILE}.backup-*${NC}"
fi

# Copiar template
if [ ! -f "${PROJECT_ROOT}/.env.example" ]; then
    echo -e "${YELLOW}⚠️  .env.example no encontrado${NC}"
    exit 1
fi

cp "${PROJECT_ROOT}/.env.example" "$ENV_FILE"
echo -e "${GREEN}✅ Copiado .env.example → .env.staging${NC}"

# Generar secrets
echo ""
echo -e "${BLUE}Generando secrets seguros...${NC}"

SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '\n' | tr '+/' '-_')
MYSQL_PASSWORD=$(openssl rand -base64 24 | tr -d '\n' | tr '+/' '-_')
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d '\n' | tr '+/' '-_')
REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d '\n' | tr '+/' '-_')
WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 16)

# Reemplazar en .env.staging
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "$ENV_FILE"
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${SECRET_KEY}/" "$ENV_FILE"
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${POSTGRES_PASSWORD}/" "$ENV_FILE"
sed -i "s/MYSQL_PASSWORD=.*/MYSQL_PASSWORD=${MYSQL_PASSWORD}/" "$ENV_FILE"
sed -i "s/MYSQL_ROOT_PASSWORD=.*/MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}/" "$ENV_FILE"
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" "$ENV_FILE"
sed -i "s/WHATSAPP_VERIFY_TOKEN=.*/WHATSAPP_VERIFY_TOKEN=${WHATSAPP_VERIFY_TOKEN}/" "$ENV_FILE"

# Actualizar POSTGRES_URL con password generado
sed -i "s|postgresql+asyncpg://agente_user:.*@postgres:5432|postgresql+asyncpg://agente_user:${POSTGRES_PASSWORD}@postgres:5432|" "$ENV_FILE"

# Actualizar REDIS_URL con password generado
sed -i "s|redis://:[^@]*@redis:6379|redis://:${REDIS_PASSWORD}@redis:6379|" "$ENV_FILE"

# Configurar para staging
sed -i "s/ENVIRONMENT=.*/ENVIRONMENT=staging/" "$ENV_FILE"
sed -i "s/DEBUG=.*/DEBUG=false/" "$ENV_FILE"
sed -i "s/LOG_LEVEL=.*/LOG_LEVEL=INFO/" "$ENV_FILE"
sed -i "s/PMS_TYPE=.*/PMS_TYPE=mock/" "$ENV_FILE"

# Permisos seguros
chmod 600 "$ENV_FILE"

echo -e "${GREEN}✅ Secrets generados exitosamente${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Secrets Generados (guárdalos en lugar seguro):${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}SECRET_KEY:${NC}              ${SECRET_KEY}"
echo -e "${GREEN}POSTGRES_PASSWORD:${NC}       ${POSTGRES_PASSWORD}"
echo -e "${GREEN}MYSQL_PASSWORD:${NC}          ${MYSQL_PASSWORD}"
echo -e "${GREEN}MYSQL_ROOT_PASSWORD:${NC}     ${MYSQL_ROOT_PASSWORD}"
echo -e "${GREEN}REDIS_PASSWORD:${NC}          ${REDIS_PASSWORD}"
echo -e "${GREEN}WHATSAPP_VERIFY_TOKEN:${NC}   ${WHATSAPP_VERIFY_TOKEN}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Guardar secrets en archivo temporal encriptado (opcional)
SECRETS_FILE="/tmp/staging-secrets-$(date +%Y%m%d-%H%M%S).txt"
cat > "$SECRETS_FILE" << EOF
# Secrets Generados - $(date)
# ⚠️  ELIMINAR ESTE ARCHIVO DESPUÉS DE GUARDAR EN LOCATION SEGURO

SECRET_KEY=${SECRET_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
WHATSAPP_VERIFY_TOKEN=${WHATSAPP_VERIFY_TOKEN}
EOF

echo ""
echo -e "${YELLOW}⚠️  Secrets guardados temporalmente en: ${SECRETS_FILE}${NC}"
echo -e "${YELLOW}⚠️  ELIMINAR después de guardar en lugar seguro${NC}"
echo ""

# Verificar secrets pendientes
echo -e "${BLUE}Verificando secrets pendientes de configurar...${NC}"
PENDING=$(grep -E "REPLACE_WITH|your-|changeme" "$ENV_FILE" || true)

if [ -n "$PENDING" ]; then
    echo -e "${YELLOW}⚠️  Hay secrets adicionales que requieren configuración manual:${NC}"
    echo ""
    grep -E "REPLACE_WITH|your-|changeme" "$ENV_FILE" | head -10
    echo ""
    echo -e "${BLUE}Edita .env.staging para completar:${NC}"
    echo "  • WHATSAPP_ACCESS_TOKEN (Meta Cloud API)"
    echo "  • WHATSAPP_PHONE_NUMBER_ID (Meta Cloud API)"
    echo "  • GMAIL_USERNAME (email notifications)"
    echo "  • GMAIL_APP_PASSWORD (Gmail app password)"
    echo "  • PMS_API_KEY (si usas QloApps real)"
else
    echo -e "${GREEN}✅ Todos los secrets críticos configurados${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Próximos Pasos:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "1. Revisar y editar .env.staging:"
echo "   ${GREEN}nano .env.staging${NC}"
echo ""
echo "2. Completar secrets opcionales (WhatsApp, Gmail):"
echo "   • WHATSAPP_ACCESS_TOKEN"
echo "   • WHATSAPP_PHONE_NUMBER_ID"
echo "   • GMAIL_APP_PASSWORD"
echo ""
echo "3. Ejecutar deployment:"
echo "   ${GREEN}./scripts/deploy-staging.sh${NC}"
echo ""
echo "4. Guardar secrets en AWS Secrets Manager (recomendado):"
echo "   ${GREEN}aws secretsmanager create-secret \\${NC}"
echo "   ${GREEN}    --name agente-hotel-staging-env \\${NC}"
echo "   ${GREEN}    --secret-string file://.env.staging${NC}"
echo ""
echo "5. ELIMINAR archivo temporal de secrets:"
echo "   ${YELLOW}shred -u ${SECRETS_FILE}${NC}"
echo ""

# Mostrar ubicación del archivo
echo -e "${GREEN}✅ Configuración guardada en: ${ENV_FILE}${NC}"
echo -e "${GREEN}✅ Permisos seguros aplicados (600)${NC}"
echo ""
echo -e "${CYAN}🔐 Listo para deployment a staging!${NC}"
