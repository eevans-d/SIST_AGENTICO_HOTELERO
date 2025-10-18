#!/bin/bash
# ============================================================================
# Railway Secrets Generator
# ============================================================================
# Genera secretos crypto-secure para deployment en Railway
# Uso: ./scripts/generate-railway-secrets.sh
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║           🔐 Railway Secrets Generator 🔐                 ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║  Genera secretos crypto-secure para Railway deployment    ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ Error: openssl no está instalado${NC}"
    echo "Instalar con: sudo apt-get install openssl"
    exit 1
fi

# Output file
OUTPUT_FILE=".env.railway.local"
TEMPLATE_FILE=".env.railway"

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}❌ Error: $TEMPLATE_FILE no encontrado${NC}"
    exit 1
fi

# Backup existing file if exists
if [ -f "$OUTPUT_FILE" ]; then
    BACKUP_FILE="${OUTPUT_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}⚠️  Archivo existente encontrado, creando backup...${NC}"
    cp "$OUTPUT_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup guardado: $BACKUP_FILE${NC}"
    echo ""
fi

echo -e "${BLUE}🔧 Generando secretos crypto-secure...${NC}"
echo ""

# Generate secrets
JWT_SECRET=$(openssl rand -base64 32)
JWT_REFRESH_SECRET=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)
WHATSAPP_WEBHOOK_VERIFY_TOKEN=$(openssl rand -hex 16)

# Copy template to output
cp "$TEMPLATE_FILE" "$OUTPUT_FILE"

# Replace placeholders with generated secrets
sed -i "s|JWT_SECRET=<GENERAR_CON_openssl_rand_-base64_32>|JWT_SECRET=${JWT_SECRET}|g" "$OUTPUT_FILE"
sed -i "s|JWT_REFRESH_SECRET=<GENERAR_CON_openssl_rand_-base64_32>|JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}|g" "$OUTPUT_FILE"
sed -i "s|ENCRYPTION_KEY=<GENERAR_CON_openssl_rand_-base64_32>|ENCRYPTION_KEY=${ENCRYPTION_KEY}|g" "$OUTPUT_FILE"
sed -i "s|WHATSAPP_WEBHOOK_VERIFY_TOKEN=<GENERAR_CON_openssl_rand_-hex_16>|WHATSAPP_WEBHOOK_VERIFY_TOKEN=${WHATSAPP_WEBHOOK_VERIFY_TOKEN}|g" "$OUTPUT_FILE"

# Set secure permissions
chmod 600 "$OUTPUT_FILE"

echo -e "${GREEN}✅ Secretos generados exitosamente${NC}"
echo ""

# Display generated secrets
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Secretos Generados                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}JWT_SECRET:${NC}"
echo "$JWT_SECRET"
echo ""
echo -e "${GREEN}JWT_REFRESH_SECRET:${NC}"
echo "$JWT_REFRESH_SECRET"
echo ""
echo -e "${GREEN}ENCRYPTION_KEY:${NC}"
echo "$ENCRYPTION_KEY"
echo ""
echo -e "${GREEN}WHATSAPP_WEBHOOK_VERIFY_TOKEN:${NC}"
echo "$WHATSAPP_WEBHOOK_VERIFY_TOKEN"
echo ""

# Next steps
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Próximos Pasos                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}1. Archivo generado:${NC} $OUTPUT_FILE"
echo -e "${YELLOW}2. Permisos establecidos:${NC} 600 (solo lectura por owner)"
echo ""
echo -e "${GREEN}Opción A: Configurar en Railway Web UI${NC}"
echo "   1. Ir a https://railway.app/dashboard"
echo "   2. Abrir tu proyecto"
echo "   3. Click en el servicio"
echo "   4. Click en tab 'Variables'"
echo "   5. Copiar/pegar los secretos arriba"
echo ""
echo -e "${GREEN}Opción B: Usar Railway CLI${NC}"
echo "   railway variables set --file $OUTPUT_FILE"
echo ""
echo -e "${RED}⚠️  IMPORTANTE:${NC}"
echo "   - NO commitear $OUTPUT_FILE a git (ya en .gitignore)"
echo "   - Guardar secretos en password manager"
echo "   - Eliminar backups antiguos después de validar"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Secretos listos para Railway deployment           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
