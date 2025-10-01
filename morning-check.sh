#!/bin/bash

# Morning Check Script - Quick verification before starting work
# Usage: ./morning-check.sh

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "   🌅 BUENOS DÍAS - Morning Verification Check"
echo "═══════════════════════════════════════════════════════════════"
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check 1: Git Status
echo "📋 1. Git Status Check..."
if git status | grep -q "nothing to commit, working tree clean"; then
    echo -e "${GREEN}✅ Git working tree is clean${NC}"
else
    echo -e "${YELLOW}⚠️  Git working tree has changes${NC}"
    git status -s
fi
echo

# Check 2: Git Sync
echo "📋 2. Git Sync Check..."
git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✅ Local is synced with origin/main${NC}"
else
    echo -e "${YELLOW}⚠️  Local is out of sync with origin/main${NC}"
    echo "   Run: git pull origin main"
fi
echo

# Check 3: Latest Commits
echo "📋 3. Latest Commits (last 5)..."
git log --oneline -5
echo

# Check 4: Documentation Files
echo "📋 4. Documentation Files..."
DOC_COUNT=$(ls -1 *.md *.txt 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Found $DOC_COUNT documentation files in root${NC}"
echo

# Check 5: Key Files Exist
echo "📋 5. Key Files Check..."
KEY_FILES=(
    "START_HERE_TOMORROW.md"
    "DEPLOYMENT_ACTION_PLAN.md"
    "QUICK_REFERENCE.md"
    "END_OF_DAY_REPORT.md"
    "FINAL_STATUS.txt"
)

for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file${NC}"
    fi
done
echo

# Check 6: Project Structure
echo "📋 6. Project Structure..."
if [ -d "agente-hotel-api" ]; then
    echo -e "${GREEN}✅ agente-hotel-api directory exists${NC}"
    if [ -f "agente-hotel-api/Makefile" ]; then
        echo -e "${GREEN}✅ Makefile found${NC}"
    fi
    if [ -f "agente-hotel-api/pyproject.toml" ]; then
        echo -e "${GREEN}✅ pyproject.toml found${NC}"
    fi
else
    echo -e "${RED}❌ agente-hotel-api directory not found${NC}"
fi
echo

# Check 7: Docker
echo "📋 7. Docker Availability..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker is installed${NC}"
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✅ Docker daemon is running${NC}"
        RUNNING=$(docker ps --format "{{.Names}}" | wc -l)
        echo "   Running containers: $RUNNING"
    else
        echo -e "${YELLOW}⚠️  Docker daemon is not running${NC}"
    fi
else
    echo -e "${RED}❌ Docker is not installed${NC}"
fi
echo

# Check 8: Python Environment
echo "📋 8. Python Environment..."
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}✅ Poetry is installed${NC}"
    cd agente-hotel-api
    if poetry env info &> /dev/null; then
        echo -e "${GREEN}✅ Poetry virtualenv exists${NC}"
    else
        echo -e "${YELLOW}⚠️  Poetry virtualenv not initialized${NC}"
        echo "   Run: cd agente-hotel-api && poetry install"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  Poetry is not installed${NC}"
fi
echo

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "   📊 VERIFICATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo
echo "Current Branch:    $(git branch --show-current)"
echo "Latest Commit:     $(git log --oneline -1)"
echo "Documentation:     $DOC_COUNT files"
echo "Status:            Ready for Phase 1 Configuration"
echo
echo "═══════════════════════════════════════════════════════════════"
echo "   🚀 NEXT STEPS"
echo "═══════════════════════════════════════════════════════════════"
echo
echo "1. Read: START_HERE_TOMORROW.md"
echo "2. Plan: DEPLOYMENT_ACTION_PLAN.md"
echo "3. Commands: QUICK_REFERENCE.md"
echo
echo "To start Phase 1:"
echo "  cd agente-hotel-api"
echo "  make preflight"
echo
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Morning check complete! Ready to start working.${NC}"
echo "═══════════════════════════════════════════════════════════════"
