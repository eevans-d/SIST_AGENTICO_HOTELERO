#!/bin/bash
# Script para configurar secrets en Fly.io de forma segura
# Uso: ./setup-fly-secrets.sh

set -e

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                               ║"
echo "║                   🔐 FLY.IO SECRETS CONFIGURATION                            ║"
echo "║                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo -e "${RED}❌ Fly CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check authentication
echo "Checking Fly authentication..."
if ! flyctl auth whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated. Running 'flyctl auth login'...${NC}"
    flyctl auth login
fi
echo -e "${GREEN}✅ Authenticated as: $(flyctl auth whoami)${NC}"
echo ""

# Function to generate secure random string
generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Function to set secret
set_secret() {
    local key=$1
    local value=$2
    echo -e "${BLUE}Setting secret: $key${NC}"
    flyctl secrets set "$key=$value" --stage
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 SECURITY SECRETS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate and set SECRET_KEY
echo -e "${YELLOW}Generating SECRET_KEY...${NC}"
SECRET_KEY=$(generate_secret)
set_secret "SECRET_KEY" "$SECRET_KEY"

# Generate and set JWT_SECRET_KEY
echo -e "${YELLOW}Generating JWT_SECRET_KEY...${NC}"
JWT_SECRET_KEY=$(generate_secret)
set_secret "JWT_SECRET_KEY" "$JWT_SECRET_KEY"

# Generate and set API_KEY_SECRET
echo -e "${YELLOW}Generating API_KEY_SECRET...${NC}"
API_KEY_SECRET=$(generate_secret)
set_secret "API_KEY_SECRET" "$API_KEY_SECRET"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 DATABASE & REDIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# DATABASE_URL
echo -e "${YELLOW}Enter DATABASE_URL (PostgreSQL connection string):${NC}"
echo "Example: postgresql://user:password@host:5432/dbname"
read -p "DATABASE_URL: " DATABASE_URL
if [ ! -z "$DATABASE_URL" ]; then
    set_secret "DATABASE_URL" "$DATABASE_URL"
else
    echo -e "${RED}⚠️  DATABASE_URL skipped (required for production)${NC}"
fi

# REDIS_URL
echo ""
echo -e "${YELLOW}Enter REDIS_URL (Redis connection string):${NC}"
echo "Example: redis://default:password@host:6379/0"
read -p "REDIS_URL: " REDIS_URL
if [ ! -z "$REDIS_URL" ]; then
    set_secret "REDIS_URL" "$REDIS_URL"
else
    echo -e "${RED}⚠️  REDIS_URL skipped (required for production)${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏨 PMS CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# PMS_API_KEY
echo -e "${YELLOW}Enter PMS_API_KEY (QloApps or PMS system API key):${NC}"
read -p "PMS_API_KEY (press Enter to skip): " PMS_API_KEY
if [ ! -z "$PMS_API_KEY" ]; then
    set_secret "PMS_API_KEY" "$PMS_API_KEY"
fi

# PMS_API_SECRET
echo ""
echo -e "${YELLOW}Enter PMS_API_SECRET (if required by your PMS):${NC}"
read -p "PMS_API_SECRET (press Enter to skip): " PMS_API_SECRET
if [ ! -z "$PMS_API_SECRET" ]; then
    set_secret "PMS_API_SECRET" "$PMS_API_SECRET"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 WHATSAPP INTEGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# WHATSAPP_ACCESS_TOKEN
echo -e "${YELLOW}Enter WHATSAPP_ACCESS_TOKEN (Meta WhatsApp Business token):${NC}"
read -p "WHATSAPP_ACCESS_TOKEN (press Enter to skip): " WHATSAPP_ACCESS_TOKEN
if [ ! -z "$WHATSAPP_ACCESS_TOKEN" ]; then
    set_secret "WHATSAPP_ACCESS_TOKEN" "$WHATSAPP_ACCESS_TOKEN"
fi

# WHATSAPP_BUSINESS_ACCOUNT_ID
echo ""
echo -e "${YELLOW}Enter WHATSAPP_BUSINESS_ACCOUNT_ID:${NC}"
read -p "WHATSAPP_BUSINESS_ACCOUNT_ID (press Enter to skip): " WHATSAPP_BUSINESS_ACCOUNT_ID
if [ ! -z "$WHATSAPP_BUSINESS_ACCOUNT_ID" ]; then
    set_secret "WHATSAPP_BUSINESS_ACCOUNT_ID" "$WHATSAPP_BUSINESS_ACCOUNT_ID"
fi

# WHATSAPP_VERIFY_TOKEN
echo ""
echo -e "${YELLOW}Generating WHATSAPP_VERIFY_TOKEN...${NC}"
WHATSAPP_VERIFY_TOKEN=$(generate_secret)
set_secret "WHATSAPP_VERIFY_TOKEN" "$WHATSAPP_VERIFY_TOKEN"
echo -e "${GREEN}✅ Use this token in Meta Dashboard: $WHATSAPP_VERIFY_TOKEN${NC}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📧 GMAIL INTEGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# GMAIL_CREDENTIALS
echo -e "${YELLOW}Enter path to Gmail credentials JSON file (press Enter to skip):${NC}"
read -p "Gmail credentials path: " GMAIL_CREDS_PATH
if [ ! -z "$GMAIL_CREDS_PATH" ] && [ -f "$GMAIL_CREDS_PATH" ]; then
    GMAIL_CREDENTIALS=$(cat "$GMAIL_CREDS_PATH")
    set_secret "GMAIL_CREDENTIALS" "$GMAIL_CREDENTIALS"
    echo -e "${GREEN}✅ Gmail credentials loaded from file${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SECRETS CONFIGURATION COMPLETE (STAGED)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Staged secrets (will be deployed on next deploy):"
flyctl secrets list

echo ""
echo "⚠️  IMPORTANT:"
echo "   • Secrets are STAGED but not yet active"
echo "   • Deploy your app to activate: flyctl deploy"
echo "   • Or deploy secrets only: flyctl secrets deploy"
echo ""
echo "🔍 To view current secrets: flyctl secrets list"
echo "🗑️  To remove a secret: flyctl secrets unset SECRET_NAME"
echo ""

read -p "Deploy secrets now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deploying secrets..."
    flyctl secrets deploy
    echo -e "${GREEN}✅ Secrets deployed and active!${NC}"
else
    echo -e "${YELLOW}Secrets staged. Deploy with: flyctl deploy${NC}"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                               ║"
echo "║                  ✅ SECRETS CONFIGURATION FINISHED                           ║"
echo "║                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
