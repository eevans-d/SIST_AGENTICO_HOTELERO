#!/bin/bash
set -e

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                               ║"
echo "║                    🚀 FLY.IO DEPLOYMENT SCRIPT                               ║"
echo "║                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Pre-flight checks
echo "1️⃣  Checking git status..."
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    git status --short
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ Git working tree clean${NC}"
fi

# Check if flyctl is installed
echo ""
echo "2️⃣  Checking Fly CLI..."
if ! command -v flyctl &> /dev/null; then
    echo -e "${RED}❌ Fly CLI not found. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Fly CLI found: $(flyctl version | head -1)${NC}"

# Check if authenticated
echo ""
echo "3️⃣  Checking Fly authentication..."
if ! flyctl auth whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated. Running 'flyctl auth login'...${NC}"
    flyctl auth login
else
    echo -e "${GREEN}✅ Authenticated as: $(flyctl auth whoami)${NC}"
fi

# Optional: Run tests
echo ""
read -p "4️⃣  Run tests before deploy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running tests..."
    cd agente-hotel-api
    if command -v poetry &> /dev/null; then
        poetry run pytest tests/ -v --tb=short || {
            echo -e "${RED}❌ Tests failed. Aborting deployment.${NC}"
            exit 1
        }
    else
        echo -e "${YELLOW}⚠️  Poetry not found, skipping tests${NC}"
    fi
    cd ..
    echo -e "${GREEN}✅ Tests passed${NC}"
fi

# Deploy
echo ""
echo "5️⃣  Building & deploying to Fly.io..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
flyctl deploy --strategy rolling

# Wait for health checks
echo ""
echo "6️⃣  Waiting for health checks..."
sleep 10

# Verify deployment
echo ""
echo "7️⃣  Verifying deployment..."
flyctl status

# Test endpoints (if app URL is available)
echo ""
echo "8️⃣  Testing endpoints..."
if flyctl info --json &> /dev/null; then
    APP_URL=$(flyctl info --json 2>/dev/null | grep -o '"Hostname":"[^"]*"' | cut -d'"' -f4)
    if [ ! -z "$APP_URL" ]; then
        echo "Testing https://$APP_URL/health/live"
        if curl -f -s "https://$APP_URL/health/live" > /dev/null; then
            echo -e "${GREEN}✅ Health check passed${NC}"
        else
            echo -e "${RED}❌ Health check failed${NC}"
        fi
        
        echo "Testing https://$APP_URL/health/ready"
        if curl -f -s "https://$APP_URL/health/ready" > /dev/null; then
            echo -e "${GREEN}✅ Ready check passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Ready check failed (may be normal during startup)${NC}"
        fi
    fi
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                               ║"
echo "║                        ✅ DEPLOYMENT COMPLETE!                               ║"
echo "║                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Useful commands:"
echo "  • View logs:      flyctl logs -f"
echo "  • SSH into app:   flyctl ssh console"
echo "  • Check status:   flyctl status"
echo "  • Open dashboard: flyctl dashboard"
echo "  • Open app:       flyctl open"
echo ""
