# PROMPT 4: GUÍA DE TROUBLESHOOTING Y MANTENIMIENTO

## 1. PROBLEMAS COMUNES DE DESPLIEGUE

### Top 5 Errores Más Probables Durante Deployment

#### Error 1: Variables de Entorno Faltantes
**Síntoma:**
```
ValidationError: 6 validation errors for Settings
pms_api_key: Field required
whatsapp_access_token: Field required
```

**Solución paso a paso:**
```bash
# 1. Verificar variables de entorno en Railway
railway env list

# 2. Agregar variables faltantes
railway env set SECRET_KEY=$(openssl rand -hex 32)
railway env set WHATSAPP_ACCESS_TOKEN=your_token_here
railway env set PMS_API_KEY=your_pms_key_here
railway env set GMAIL_APP_PASSWORD=your_gmail_password
railway env set WHATSAPP_VERIFY_TOKEN=your_verify_token
railway env set WHATSAPP_APP_SECRET=your_app_secret

# 3. Redeploy service
railway deploy --service agente-api
```

**Logs a revisar:**
```bash
railway logs --service agente-api | grep -i "validation\|field required"
```

**Señales de alerta temprana:**
- Service fails to start after deployment
- Health checks returning 500 errors
- Environment validation errors in startup logs

#### Error 2: Database Connection Failed
**Síntoma:**
```
asyncpg.exceptions.InvalidAuthorizationSpecificationError: password authentication failed
sqlalchemy.exc.OperationalError: connection to server failed
```

**Solución paso a paso:**
```bash
# 1. Verificar conexión a PostgreSQL
railway run --service postgres psql $DATABASE_URL -c "SELECT 1;"

# 2. Verificar URL de conexión
railway env get POSTGRES_URL

# 3. Si falla, recrear base de datos
railway service delete postgres
railway service create postgres
railway env set POSTGRES_URL=${{Postgres.DATABASE_URL}}

# 4. Ejecutar migraciones
railway run alembic upgrade head
```

### Health Checks Específicos para este Sistema
```bash
#!/bin/bash
# scripts/comprehensive-health-check.sh

echo "🏥 Sistema Agéntico Hotelero - Health Check Completo"

BASE_URL="https://your-domain.com"

# 1. API Health Checks
echo "1️⃣ API Health Checks..."
response=$(curl -s -w "%{http_code}" "$BASE_URL/health/live")
if [[ "${response: -3}" == "200" ]]; then
    echo "✅ Liveness check OK"
else
    echo "❌ Liveness check FAILED (${response: -3})"
fi

# 2. Database Health
echo "2️⃣ Database Health..."
railway run --service postgres pg_isready -q && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL FAILED"
railway run --service mysql mysqladmin ping -s && echo "✅ MySQL OK" || echo "❌ MySQL FAILED"
railway run --service redis redis-cli ping | grep -q PONG && echo "✅ Redis OK" || echo "❌ Redis FAILED"

# 3. External APIs Health
echo "3️⃣ External APIs..."
whatsapp_status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: ******{WHATSAPP_ACCESS_TOKEN}" \
    "https://graph.facebook.com/v18.0/me")
[[ "$whatsapp_status" == "200" ]] && echo "✅ WhatsApp API OK" || echo "❌ WhatsApp API FAILED ($whatsapp_status)"

pms_status=$(curl -s -o /dev/null -w "%{http_code}" "$PMS_BASE_URL")
[[ "$pms_status" =~ ^[23] ]] && echo "✅ PMS OK" || echo "❌ PMS FAILED ($pms_status)"
```

## 2. SCRIPTS DE AUTOMATIZACIÓN

### Deployment Completo
```bash
#!/bin/bash
# scripts/full-deployment.sh

set -e

echo "🚀 Full Deployment Script"

# Pre-deployment checks
echo "1️⃣ Pre-deployment validation..."
make validate-deployment || {
    echo "❌ Pre-deployment validation failed"
    exit 1
}

# Create backup
echo "2️⃣ Creating backup..."
./scripts/comprehensive-backup.sh

# Deploy to production
echo "3️⃣ Deploying to production..."
railway deploy --stage production

# Test production
echo "4️⃣ Testing production..."
sleep 30
curl -f https://your-domain.com/health/ready || {
    echo "❌ Production deployment failed, initiating rollback..."
    railway rollback --stage production
    exit 1
}

echo "✅ Deployment completed successfully"
```

### Backup Automático
```bash
#!/bin/bash
# scripts/automated-backup.sh

set -e

BACKUP_BASE_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"

echo "📦 Automated Backup Process Started"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL Backup
echo "1️⃣ Backing up PostgreSQL..."
railway run --service postgres pg_dump $DATABASE_URL > "$BACKUP_DIR/postgres.sql"

# 2. MySQL Backup
echo "2️⃣ Backing up MySQL..."
railway run --service mysql mysqldump --single-transaction $MYSQL_DATABASE > "$BACKUP_DIR/mysql.sql"

# 3. Redis Backup
echo "3️⃣ Backing up Redis..."
railway run --service redis redis-cli --rdb "$BACKUP_DIR/redis.rdb"

# 4. Environment Variables Backup
echo "4️⃣ Backing up environment variables..."
railway env > "$BACKUP_DIR/environment.txt"

# 5. Compress backup
echo "5️⃣ Compressing backup..."
cd "$BACKUP_BASE_DIR"
tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP"
rm -rf "$TIMESTAMP"

echo "✅ Automated backup completed successfully"
```

### Rollback Rápido
```bash
#!/bin/bash
# scripts/quick-rollback.sh

echo "🔄 Quick Rollback initiated..."

# Get previous deployment
previous_deployment=$(railway deployments list --limit 2 --json | jq -r '.[1].id')

if [ -z "$previous_deployment" ]; then
    echo "❌ No previous deployment found"
    exit 1
fi

# Rollback
echo "Rolling back to deployment: $previous_deployment"
railway rollback $previous_deployment

# Verify rollback
echo "Verifying rollback..."
sleep 30
curl -f https://your-domain.com/health/ready || {
    echo "❌ Rollback verification failed"
    exit 1
}

echo "✅ Rollback completed successfully"
```

Este documento completo de troubleshooting y mantenimiento proporciona guías detalladas, scripts ejecutables y procedimientos paso a paso específicamente diseñados para el sistema Agente Hotelero.
