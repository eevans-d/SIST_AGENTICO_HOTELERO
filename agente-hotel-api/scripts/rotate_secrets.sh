#!/bin/bash
# Script para rotar secrets de forma segura

set -e

echo "🔄 Rotación de Secrets"
echo "====================="
echo ""

# 1. Generar nuevos secrets
echo "Generando nuevos secrets..."
NEW_JWT_SECRET=$(openssl rand -hex 32)
NEW_API_KEY=$(openssl rand -hex 16)

echo "Nuevos secrets generados (guárdalos de forma segura):"
echo "JWT_SECRET: $NEW_JWT_SECRET"
echo "API_KEY: $NEW_API_KEY"
echo ""

# 2. Backup de configuración actual
echo "Creando backup de configuración actual..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 3. Actualizar .env
echo "Actualizando configuración..."
sed -i.bak "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT_SECRET/" .env
sed -i.bak "s/API_KEY=.*/API_KEY=$NEW_API_KEY/" .env

echo "✅ Secrets rotados exitosamente"
echo "⚠️  No olvides actualizar los secrets en:"
echo "   - Docker secrets"
echo "   - Variables de entorno de producción"
echo "   - Documentación de secrets"
