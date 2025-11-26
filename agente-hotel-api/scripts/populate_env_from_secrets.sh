#!/bin/bash
# Script para poblar .env.supabase con credenciales de GitHub Secrets
# Uso: ./scripts/populate_env_from_secrets.sh

set -e

echo "🔐 Poblando .env.supabase con credenciales de GitHub Secrets..."

cd "$(dirname "$0")/.."

# Obtener secrets de GitHub
DATABASE_URL=$(gh secret list --json name,updatedAt | jq -r '.[] | select(.name=="DATABASE_URL") | .name' 2>/dev/null)
REDIS_URL_SECRET=$(gh secret list --json name,updatedAt | jq -r '.[] | select(.name=="REDIS_URL") | .name' 2>/dev/null)

if [ -z "$DATABASE_URL" ] || [ -z "$REDIS_URL_SECRET" ]; then
    echo "❌ Error: No se encontraron los secrets DATABASE_URL y/o REDIS_URL en GitHub"
    echo "   Ejecuta manualmente:"
    echo "   1. Abre: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/settings/secrets/actions"
    echo "   2. Copia DATABASE_URL y REDIS_URL"
    echo "   3. Edita .env.supabase reemplazando [PASSWORD] con los valores reales"
    exit 1
fi

echo "✅ Secrets encontrados en GitHub"
echo "⚠️  NOTA: gh CLI no puede leer los valores de los secrets por seguridad"
echo ""
echo "📋 Pasos manuales necesarios:"
echo "   1. Abre: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/settings/secrets/actions"
echo "   2. Busca DATABASE_URL → click 'Update' para ver el valor"
echo "   3. Busca REDIS_URL → click 'Update' para ver el valor"
echo "   4. Edita agente-hotel-api/.env.supabase:"
echo "      nano agente-hotel-api/.env.supabase"
echo "   5. Reemplaza [PASSWORD] en POSTGRES_URL con la contraseña de DATABASE_URL"
echo "   6. Reemplaza [PASSWORD] en REDIS_URL con la contraseña de REDIS_URL"
echo ""
echo "O ejecuta este comando si tienes las contraseñas:"
echo "   cd agente-hotel-api"
echo "   sed -i 's|postgresql+asyncpg://postgres.ofbsjfmnladfzbjmcxhx:\[PASSWORD\]|[TU_DATABASE_URL_COMPLETA]|' .env.supabase"
echo "   sed -i 's|rediss://default:\[PASSWORD\]|[TU_REDIS_URL_COMPLETA]|' .env.supabase"
