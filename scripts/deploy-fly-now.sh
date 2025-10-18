#!/bin/bash
# =============================================================================
# SCRIPT DE DEPLOYMENT - FLY.IO
# =============================================================================
# Este script contiene todos los comandos necesarios para deployar
# tu Agente Hotelero IA en Fly.io con los secretos generados.
#
# IMPORTANTE: Reemplaza los valores "REEMPLAZAR_CON_..." con tus credenciales
# reales antes de ejecutar los comandos.
# =============================================================================

echo "=================================================="
echo "  AGENTE HOTELERO IA - DEPLOYMENT A FLY.IO"
echo "=================================================="
echo ""

# =============================================================================
# PASO 1: AUTENTICACIÓN
# =============================================================================
echo "✅ PASO 1: Autenticación en Fly.io"
echo ""
echo "Si ya tienes cuenta:"
echo "  flyctl auth login"
echo ""
echo "Si NO tienes cuenta:"
echo "  flyctl auth signup"
echo ""
read -p "Presiona ENTER cuando hayas completado la autenticación..."

# =============================================================================
# PASO 2: CREAR APLICACIÓN
# =============================================================================
echo ""
echo "✅ PASO 2: Crear aplicación (si no existe)"
echo ""
echo "Opción A - Launch interactivo:"
echo "  flyctl launch"
echo "  (Responde las preguntas, NO crees PostgreSQL aún)"
echo ""
echo "Opción B - Launch desde fly.toml existente:"
echo "  flyctl launch --no-deploy"
echo ""
read -p "Presiona ENTER cuando hayas creado la app..."

# =============================================================================
# PASO 3: CREAR POSTGRESQL
# =============================================================================
echo ""
echo "✅ PASO 3: Crear base de datos PostgreSQL"
echo ""
echo "Comando:"
echo "  flyctl postgres create --name agente-hotel-db --region mia"
echo ""
echo "Luego attachar a la app:"
echo "  flyctl postgres attach --app agente-hotel agente-hotel-db"
echo ""
echo "(Esto setea automáticamente DATABASE_URL como secret)"
echo ""
read -p "Presiona ENTER cuando hayas creado PostgreSQL..."

# =============================================================================
# PASO 4: SETEAR SECRETOS CRÍTICOS (OBLIGATORIO)
# =============================================================================
echo ""
echo "✅ PASO 4: Setear secretos críticos"
echo ""
echo "Copia y pega este comando:"
echo ""
cat << 'EOF'
flyctl secrets set \
  SECRET_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  JWT_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  JWT_REFRESH_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  ENCRYPTION_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
EOF
echo ""
read -p "Presiona ENTER cuando hayas seteado los secretos críticos..."

# =============================================================================
# PASO 5: SETEAR WHATSAPP (Reemplazar con tus valores reales)
# =============================================================================
echo ""
echo "✅ PASO 5: Setear credenciales de WhatsApp"
echo ""
echo "⚠️  REEMPLAZA los valores con tus credenciales reales de Meta:"
echo ""
cat << 'EOF'
flyctl secrets set \
  WHATSAPP_VERIFY_TOKEN=45428a63a31eab2be9643bc5d813ece2 \
  WHATSAPP_API_KEY=REEMPLAZAR_CON_TU_META_API_KEY \
  WHATSAPP_BUSINESS_ACCOUNT_ID=REEMPLAZAR_CON_TU_BUSINESS_ACCOUNT_ID \
  WHATSAPP_PHONE_ID=REEMPLAZAR_CON_TU_PHONE_ID \
  WHATSAPP_PHONE_NUMBER=REEMPLAZAR_CON_TU_NUMERO
EOF
echo ""
read -p "Presiona ENTER cuando hayas seteado WhatsApp (o SKIP si usarás mock)..."

# =============================================================================
# PASO 6: SETEAR EMAIL/SMTP (Reemplazar con tu email)
# =============================================================================
echo ""
echo "✅ PASO 6: Setear credenciales de Email"
echo ""
echo "⚠️  REEMPLAZA con tu email real:"
echo ""
cat << 'EOF'
flyctl secrets set \
  SMTP_PASSWORD=BIFB4mEwpvPJqPkea/xMlXxvmTsrr3dqwfZ2V5pL1Po= \
  SMTP_USER=REEMPLAZAR_CON_TU_EMAIL@gmail.com \
  SMTP_HOST=smtp.gmail.com \
  SMTP_PORT=587
EOF
echo ""
echo "Si usas Gmail OAuth (opcional):"
cat << 'EOF'
flyctl secrets set \
  GMAIL_CLIENT_ID=REEMPLAZAR_CON_TU_GMAIL_CLIENT_ID \
  GMAIL_CLIENT_SECRET=REEMPLAZAR_CON_TU_GMAIL_CLIENT_SECRET
EOF
echo ""
read -p "Presiona ENTER cuando hayas seteado Email (o SKIP si no usarás)..."

# =============================================================================
# PASO 7: SETEAR OPENAI (Para NLP)
# =============================================================================
echo ""
echo "✅ PASO 7: Setear OpenAI API Key"
echo ""
echo "⚠️  REEMPLAZA con tu API key real:"
echo ""
echo "flyctl secrets set OPENAI_API_KEY=REEMPLAZAR_CON_TU_OPENAI_API_KEY"
echo ""
read -p "Presiona ENTER cuando hayas seteado OpenAI (o SKIP si usarás mock)..."

# =============================================================================
# PASO 8: SETEAR PMS QLOAPPS (Opcional)
# =============================================================================
echo ""
echo "✅ PASO 8: Setear QloApps PMS (opcional)"
echo ""
echo "Si tienes QloApps, reemplaza y ejecuta:"
cat << 'EOF'
flyctl secrets set \
  PMS_API_KEY=REEMPLAZAR_CON_TU_QLOAPPS_API_KEY \
  PMS_BASE_URL=https://tu-qloapps.com/api \
  PMS_TYPE=qloapps
EOF
echo ""
echo "Si NO tienes QloApps, usa modo mock:"
echo "  (fly.toml ya tiene PMS_TYPE=mock por defecto)"
echo ""
read -p "Presiona ENTER para continuar..."

# =============================================================================
# PASO 9: SETEAR REDIS (Opcional)
# =============================================================================
echo ""
echo "✅ PASO 9: Setear Redis (opcional)"
echo ""
echo "Si usas Redis externo (Upstash, etc):"
cat << 'EOF'
flyctl secrets set \
  REDIS_PASSWORD=KZg82ONKfwE6mIsXk8jkDhnxOQEOhxaSyxyLPnv6d/w= \
  REDIS_URL=redis://:KZg82ONKfwE6mIsXk8jkDhnxOQEOhxaSyxyLPnv6d/w=@your-redis-host:6379/0
EOF
echo ""
echo "Si NO usas Redis, la app funcionará sin caché distribuido"
echo ""
read -p "Presiona ENTER para continuar..."

# =============================================================================
# PASO 10: VERIFICAR SECRETOS
# =============================================================================
echo ""
echo "✅ PASO 10: Verificar todos los secretos"
echo ""
echo "Comando:"
echo "  flyctl secrets list"
echo ""
echo "Deberías ver (mínimo):"
echo "  - SECRET_KEY"
echo "  - JWT_SECRET"
echo "  - JWT_REFRESH_SECRET"
echo "  - ENCRYPTION_KEY"
echo "  - DATABASE_URL (si attachaste PostgreSQL)"
echo ""
read -p "Presiona ENTER para continuar al deployment..."

# =============================================================================
# PASO 11: DEPLOY
# =============================================================================
echo ""
echo "✅ PASO 11: DEPLOY A PRODUCCIÓN"
echo ""
echo "Comando:"
echo "  flyctl deploy"
echo ""
echo "Esto tomará 3-5 minutos..."
echo ""
read -p "Presiona ENTER para ver el comando completo..."
echo ""
echo "=================================================="
echo "EJECUTA AHORA:"
echo "=================================================="
echo ""
echo "flyctl deploy --verbose"
echo ""
echo "=================================================="

# =============================================================================
# PASO 12: MONITOREO
# =============================================================================
echo ""
echo "✅ PASO 12: Monitorear deployment"
echo ""
echo "Ver logs en tiempo real:"
echo "  flyctl logs -f"
echo ""
echo "Ver status:"
echo "  flyctl status"
echo ""
echo "Verificar health:"
echo "  flyctl checks list"
echo ""
echo "Test endpoint:"
echo "  curl https://agente-hotel.fly.dev/health/live"
echo ""

# =============================================================================
# RESUMEN FINAL
# =============================================================================
echo ""
echo "=================================================="
echo "  ✅ DEPLOYMENT COMPLETO"
echo "=================================================="
echo ""
echo "Tu app está en:"
echo "  https://agente-hotel.fly.dev"
echo ""
echo "Health check:"
echo "  https://agente-hotel.fly.dev/health/live"
echo ""
echo "Métricas:"
echo "  https://agente-hotel.fly.dev/metrics"
echo ""
echo "Para acceder a consola:"
echo "  flyctl ssh console"
echo ""
echo "Para ver logs:"
echo "  flyctl logs -f"
echo ""
echo "Para escalar:"
echo "  flyctl scale count=2"
echo "  flyctl scale memory=2048"
echo ""
echo "¡LISTO! 🚀"
echo ""
