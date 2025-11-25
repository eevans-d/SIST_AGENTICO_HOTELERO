#!/usr/bin/env bash
# ============================================================================
# QUICK START: C1 Validation
# ============================================================================
# Este script te guía paso a paso para completar la validación de C1
# Solo necesitas tus credenciales de PagerDuty y Gmail
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          C1: SPOF AlertManager Fix - Quick Start Validation           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# PASO 1: Verificar archivos
# ============================================================================
echo -e "${YELLOW}► PASO 1: Verificando archivos de configuración...${NC}"

if [ ! -f "docker/alertmanager/config.yml" ]; then
    echo "❌ ERROR: docker/alertmanager/config.yml no encontrado"
    echo "   ¿Estás en el directorio correcto? (debe ser agente-hotel-api/)"
    exit 1
fi

if [ ! -f ".env.example" ]; then
    echo "❌ ERROR: .env.example no encontrado"
    exit 1
fi

echo "✅ Archivos encontrados"
echo ""

# ============================================================================
# PASO 2: Crear .env desde plantilla (si no existe)
# ============================================================================
echo -e "${YELLOW}► PASO 2: Creando archivo .env...${NC}"

if [ -f ".env" ]; then
    echo "⚠️  .env ya existe. ¿Quieres sobrescribirlo? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Usando .env existente"
    else
        cp .env.example .env
        echo "✅ .env recreado desde .env.example"
    fi
else
    cp .env.example .env
    echo "✅ .env creado desde .env.example"
fi
echo ""

# ============================================================================
# PASO 3: Solicitar credenciales
# ============================================================================
echo -e "${YELLOW}► PASO 3: Configurando credenciales...${NC}"
echo ""
echo "Necesito 3 credenciales:"
echo "  1. PagerDuty Integration Key (32 chars, empieza con 'R')"
echo "  2. Gmail App Password (16 chars, SIN espacios)"
echo "  3. Email donde recibir alertas"
echo ""

# PagerDuty
echo -e "${BLUE}1️⃣  PagerDuty Integration Key:${NC}"
echo "   Obtener desde: https://www.pagerduty.com/"
echo "   Services → Tu servicio → Integrations → Events API v2 → Integration Key"
echo ""
read -p "   Pega tu Integration Key: " PAGERDUTY_KEY

if [ -z "$PAGERDUTY_KEY" ]; then
    echo "❌ ERROR: PagerDuty key vacía. Abortando."
    exit 1
fi

# Gmail App Password
echo ""
echo -e "${BLUE}2️⃣  Gmail App Password:${NC}"
echo "   Obtener desde: https://myaccount.google.com/apppasswords"
echo "   (Requiere 2FA habilitado)"
echo ""
read -p "   Pega tu App Password (16 chars): " GMAIL_APP_PASSWORD

if [ -z "$GMAIL_APP_PASSWORD" ]; then
    echo "❌ ERROR: Gmail App Password vacía. Abortando."
    exit 1
fi

# Gmail account
echo ""
echo -e "${BLUE}3️⃣  Configuración de Email:${NC}"
read -p "   Tu email de Gmail (username): " GMAIL_USERNAME
read -p "   Email donde RECIBIR alertas: " ALERT_EMAIL_TO

if [ -z "$GMAIL_USERNAME" ] || [ -z "$ALERT_EMAIL_TO" ]; then
    echo "❌ ERROR: Emails vacíos. Abortando."
    exit 1
fi

# ============================================================================
# PASO 4: Actualizar .env
# ============================================================================
echo ""
echo -e "${YELLOW}► PASO 4: Actualizando .env con tus credenciales...${NC}"

# Backup
cp .env .env.backup
echo "✅ Backup creado: .env.backup"

# Reemplazar valores
sed -i "s|PAGERDUTY_INTEGRATION_KEY=.*|PAGERDUTY_INTEGRATION_KEY=${PAGERDUTY_KEY}|g" .env
sed -i "s|SMTP_USERNAME=.*|SMTP_USERNAME=${GMAIL_USERNAME}|g" .env
sed -i "s|SMTP_PASSWORD=.*|SMTP_PASSWORD=${GMAIL_APP_PASSWORD}|g" .env
sed -i "s|ALERT_EMAIL_TO=.*|ALERT_EMAIL_TO=${ALERT_EMAIL_TO}|g" .env

echo "✅ .env actualizado con credenciales"
echo ""

# Verificar
echo -e "${YELLOW}► Verificando configuración...${NC}"
if grep -q "REPLACE_WITH" .env; then
    echo "⚠️  ADVERTENCIA: Aún hay valores REPLACE_WITH en .env"
    echo "   Revisa manualmente: nano .env"
else
    echo "✅ No se encontraron valores placeholder"
fi
echo ""

# ============================================================================
# PASO 5: Reiniciar AlertManager
# ============================================================================
echo -e "${YELLOW}► PASO 5: Reiniciando AlertManager...${NC}"

if docker compose ps alertmanager > /dev/null 2>&1; then
    docker compose restart alertmanager
    echo "✅ AlertManager reiniciado"
    
    echo "Esperando 5 segundos para que inicie..."
    sleep 5
    
    # Verificar logs
    if docker compose logs alertmanager | grep -q "Listening on :9093"; then
        echo "✅ AlertManager arrancó correctamente"
    else
        echo "⚠️  No se pudo confirmar inicio. Revisa logs:"
        echo "   docker compose logs alertmanager"
    fi
else
    echo "⚠️  AlertManager no está corriendo. Iniciando todo el stack..."
    echo "   docker compose up -d"
    echo "   (Esto puede tomar varios minutos)"
fi
echo ""

# ============================================================================
# PASO 6: Ejecutar validación
# ============================================================================
echo -e "${YELLOW}► PASO 6: Ejecutando validación automática...${NC}"
echo ""

if [ -x "scripts/validate-alertmanager-spof-fix.sh" ]; then
    echo "Ejecutando script de validación..."
    echo "════════════════════════════════════════════════════════════════════════"
    ./scripts/validate-alertmanager-spof-fix.sh
    VALIDATION_EXIT_CODE=$?
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
    
    if [ $VALIDATION_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Validación automática EXITOSA${NC}"
    else
        echo -e "${YELLOW}⚠️  Validación automática encontró problemas (exit code: $VALIDATION_EXIT_CODE)${NC}"
        echo "   Revisa output arriba para detalles"
    fi
else
    echo "❌ Script de validación no encontrado o no es ejecutable"
    echo "   Ejecuta: chmod +x scripts/validate-alertmanager-spof-fix.sh"
    exit 1
fi

# ============================================================================
# PASO 7: Instrucciones finales
# ============================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      VALIDACIÓN MANUAL REQUERIDA                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Verifica que la alerta 'TestSPOFFix' llegó a los 3 canales:"
echo ""
echo "1️⃣  PagerDuty:"
echo "   → Abre: https://www.pagerduty.com/"
echo "   → Busca incidente: 'SPOF Fix Validation Test Alert'"
echo "   → Debe tener severity 'critical'"
echo ""
echo "2️⃣  Email:"
echo "   → Revisa bandeja de entrada: ${ALERT_EMAIL_TO}"
echo "   → Busca asunto: 'TestSPOFFix'"
echo "   → (También revisa carpeta de Spam)"
echo ""
echo "3️⃣  Webhook:"
echo "   → Ejecuta: docker logs agente-api | grep TestSPOFFix"
echo "   → Debe mostrar: POST /api/v1/alerts/webhook 200 OK"
echo ""
echo -e "${GREEN}Si los 3 canales recibieron la alerta → ✅ C1 COMPLETADO${NC}"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Si TODO OK → Marcar C1 como COMPLETE en roadmap"
echo "   2. Hacer commit de cambios (NO .env, solo .env.example)"
echo "   3. Continuar con C2: Prometheus Rules Validation"
echo ""
echo "📚 Documentación completa:"
echo "   - GUIA_VALIDACION_C1_SPOF_FIX.md"
echo "   - docs/setup/ALERTMANAGER_SPOF_FIX_SETUP.md"
echo ""
echo "🆘 Si tienes problemas:"
echo "   - Revisa: VALIDACION_C1_RESUMEN_EJECUTIVO.md"
echo "   - Sección 'Troubleshooting Rápido'"
echo ""

exit 0
