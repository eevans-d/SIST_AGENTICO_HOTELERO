# PROMPT 2: PLAN DE DESPLIEGUE PERSONALIZADO

## 1. PREPARACIÓN PRE-DESPLIEGUE

### Checklist Completo de Verificación de Código
```bash
# 1. Verificación de dependencias y formato
make install
make fmt
make lint

# 2. Tests completos
make test                    # Unit tests
make performance-test        # Load testing with K6
make security-fast          # Security vulnerability scan

# 3. Validación de Docker containers
make build-production       # Build production image
make test-production-image  # Test production container

# 4. Validación de configuración
make validate-deployment    # Comprehensive pre-deployment validation
make validate-slo-compliance # SLO compliance check
make validate-guardrails    # Safety mechanisms validation

# 5. Backup de datos actual (si aplica)
make backup                 # Database backup
```

### Configuraciones Específicas para Producción
```bash
# Crear archivo .env.production desde template
cp .env.example .env.production

# Variables críticas para Argentina/Producción:
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
DEBUG=false

# Timezone para Argentina
TZ=America/Argentina/Buenos_Aires

# Dominio específico para Argentina
DOMAIN=agente-hotel.com.ar
EMAIL_FOR_CERTBOT=admin@agente-hotel.com.ar

# SSL/TLS configurado para producción
NGINX_SSL_PROTOCOLS="TLSv1.2 TLSv1.3"

# Resource limits para servidor argentino típico
POSTGRES_POOL_SIZE=15
REDIS_POOL_SIZE=25
```

### Variables de Entorno para Producción (con valores ejemplo)
```bash
# .env.production - Template para Argentina
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
ENVIRONMENT=production
DEBUG=false
APP_NAME=Agente Hotel Receptionist
VERSION=1.0.0

# Database Production Settings
POSTGRES_DB=agente_hotel_prod
POSTGRES_USER=agente_prod_user
POSTGRES_PASSWORD=Arg3nt1n4_S3cur3_P4ssw0rd_2024!
POSTGRES_URL=postgresql+asyncpg://agente_prod_user:Arg3nt1n4_S3cur3_P4ssw0rd_2024!@postgres:5432/agente_hotel_prod

# MySQL for QloApps
MYSQL_DATABASE=qloapps_prod
MYSQL_USER=qloapps_prod
MYSQL_PASSWORD=QloApps_Pr0d_P4ss_2024!
MYSQL_ROOT_PASSWORD=MySQL_R00t_Arg3nt1n4_2024!

# Redis Production
REDIS_PASSWORD=R3d1s_Arg3nt1n4_P4ss_2024!
REDIS_URL=redis://:R3d1s_Arg3nt1n4_P4ss_2024!@redis:6379/0

# WhatsApp Business API (Argentina)
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxx_Argentina_Token
WHATSAPP_PHONE_NUMBER_ID=549xxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=Argentina_Hotel_Verify_Token_2024
WHATSAPP_APP_SECRET=whatsapp_app_secret_argentina_2024

# Gmail para notificaciones (Argentina)
GMAIL_USERNAME=recepcion@hotel-argentina.com.ar
GMAIL_APP_PASSWORD=gmail_app_password_16_chars

# PMS QloApps
PMS_BASE_URL=http://qloapps:80
PMS_API_KEY=qloapps_api_key_argentina_hotel_2024

# Monitoring & Alerts para Argentina
GRAFANA_ADMIN_PASSWORD=Grafana_Arg3nt1n4_Adm1n_2024!
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T01/B01/argentina_hotel_alerts
ALERT_EMAIL_TO=operaciones@hotel-argentina.com.ar
```

### Scripts de Build Optimizados para Deployment
```bash
#!/bin/bash
# scripts/deploy-argentina.sh

set -e

echo "🇦🇷 Iniciando despliegue para Argentina..."

# 1. Pre-deployment validation
echo "1️⃣ Validando pre-requisitos..."
make validate-deployment || {
    echo "❌ Validación falló. Abortando despliegue."
    exit 1
}

# 2. Backup actual
echo "2️⃣ Creando backup de seguridad..."
make backup

# 3. Build production image
echo "3️⃣ Construyendo imagen de producción..."
make build-production

# 4. Deploy with zero downtime
echo "4️⃣ Desplegando con zero downtime..."
docker-compose -f docker-compose.production.yml up -d --no-deps agente-api

# 5. Health check validation
echo "5️⃣ Validando health checks..."
sleep 30
curl -f http://localhost:8000/health/ready || {
    echo "❌ Health check falló. Iniciando rollback..."
    docker-compose -f docker-compose.production.yml rollback
    exit 1
}

echo "✅ Despliegue completado exitosamente para Argentina!"
```

### Archivos que Deben ser Excluidos
```bash
# .dockerignore
node_modules/
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/
.env
.env.local
.env.development
logs/
*.log
.DS_Store
Thumbs.db
.vscode/
.idea/
*.swp
*.swo
reports/
k6-v*
```

```bash
# .gitignore adicional para producción
.env.production
secrets/
backups/
ssl-certs/
production-logs/
monitoring-data/
```

## 2. ESTRATEGIA DE HOSTING PARA ARGENTINA

### Recomendación Específica de Plataforma
**PLATAFORMA RECOMENDADA: Railway** 

### Justificación Técnica
1. **Latencia**: Servidores en US-East que dan buena latencia a Argentina (160-200ms)
2. **Docker Native**: Soporte nativo para Docker containers
3. **Database incluida**: PostgreSQL, MySQL y Redis managed
4. **Auto-scaling**: Escalado automático basado en CPU/RAM
5. **SSL gratuito**: Certificates automáticos
6. **Easy deployment**: Git-based deployment
7. **Monitoring**: Métricas integradas
8. **Argentina-friendly**: Acepta tarjetas argentinas

### Configuración Paso a Paso para Railway

#### Paso 1: Setup Railway Project
```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login y crear proyecto
railway login
railway init
```

#### Paso 2: Configurar Servicios
```bash
# Crear servicio principal
railway service create agente-api

# Crear bases de datos
railway service create postgres
railway service create mysql  
railway service create redis
```

#### Paso 3: Variables de Entorno en Railway
```bash
# Set production environment variables
railway env set SECRET_KEY=your_secret_key_here
railway env set ENVIRONMENT=production
railway env set DEBUG=false

# Database URLs (Railway auto-generates these)
railway env set POSTGRES_URL=${{Postgres.DATABASE_URL}}
railway env set MYSQL_URL=${{MySQL.DATABASE_URL}}  
railway env set REDIS_URL=${{Redis.REDIS_URL}}

# External APIs
railway env set WHATSAPP_ACCESS_TOKEN=your_token
railway env set PMS_API_KEY=your_pms_key
railway env set GMAIL_APP_PASSWORD=your_gmail_password
```

#### Paso 4: Railway Configuration File
```json
// railway.json
{
  "build": {
    "dockerfile": "Dockerfile.production"
  },
  "deploy": {
    "healthcheck": {
      "path": "/health/live",
      "timeout": 30
    },
    "restartPolicy": "always"
  }
}
```

### Costos Estimados Mensuales (USD)
- **Hobby Plan (Desarrollo)**: $0/mes - 5GB transfer, 1GB RAM
- **Pro Plan (Producción)**: $20/mes - 100GB transfer, 8GB RAM, priority support
- **Database PostgreSQL**: $5-15/mes según uso
- **Database MySQL**: $5-15/mes según uso  
- **Redis**: $5-10/mes según uso
- **Total Estimado**: $35-60 USD/mes

### Límites del Plan Gratuito y Cuándo Upgrader
**Plan Gratuito (Hobby):**
- ✅ Hasta 5GB transfer mensual
- ✅ 1GB RAM, 1 vCPU
- ✅ SSL automático
- ❌ No custom domains
- ❌ Solo 1 servicio concurrent

**Cuándo Upgrader a Pro:**
- Tráfico > 5GB/mes (aprox 100 usuarios activos/día)
- Necesitas custom domain (.com.ar)
- Requieres más de 1GB RAM
- Necesitas priority support
- Multiple servicios concurrentes

## 3. PROCESO DE DESPLIEGUE DETALLADO

### Comandos Git Exactos para Preparar el Deploy
```bash
# 1. Preparar rama de producción
git checkout main
git pull origin main
git checkout -b release/v1.0.0

# 2. Preparar archivos de producción
cp .env.example .env.production
# Editar .env.production con credenciales reales

# 3. Pre-deployment validation
make validate-deployment

# 4. Commit release preparation
git add .env.production railway.json
git commit -m "feat: prepare production release v1.0.0"
git push origin release/v1.0.0

# 5. Merge to main para trigger deployment
git checkout main
git merge release/v1.0.0
git tag v1.0.0
git push origin main --tags
```

### Configuración de Repositorio para Auto-Deploy
```bash
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
        
      - name: Deploy to Railway
        run: railway deploy --service agente-api
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### Pasos Manuales Necesarios
1. **Configurar WhatsApp Webhook URL** en Meta Developer Console
2. **Verificar dominio personalizado** en Railway dashboard  
3. **Configurar DNS records** para dominio .com.ar
4. **Setup monitoring alerts** en Grafana/AlertManager
5. **Probar integración PMS** con QloApps production

### Configuración de Dominio Personalizado
```bash
# En Railway Dashboard > Settings > Domains
# 1. Agregar custom domain: agente-hotel.com.ar
# 2. Configurar CNAME record en tu DNS provider:
#    CNAME agente-hotel.com.ar -> railway.app

# 3. Verificar SSL certificate
curl -I https://agente-hotel.com.ar/health/live
```

### Setup de Base de Datos en Producción
```bash
# Railway auto-provision databases, pero puedes configurar:

# PostgreSQL initialization
railway run --service postgres psql -c "
CREATE DATABASE agente_hotel_prod;
CREATE USER agente_prod_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE agente_hotel_prod TO agente_prod_user;
"

# MySQL para QloApps
railway run --service mysql mysql -e "
CREATE DATABASE qloapps_prod;
CREATE USER 'qloapps_prod'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON qloapps_prod.* TO 'qloapps_prod'@'%';
FLUSH PRIVILEGES;
"
```

## 4. VERIFICACIÓN POST-DESPLIEGUE

### URLs y Endpoints para Testear
```bash
# Health checks
curl https://agente-hotel.com.ar/health/live
curl https://agente-hotel.com.ar/health/ready

# WhatsApp webhook verification
curl "https://agente-hotel.com.ar/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=test123"

# Admin dashboard (protected)
curl -H "Authorization: Bearer your_jwt_token" https://agente-hotel.com.ar/admin/dashboard

# Metrics (internal)
curl https://agente-hotel.com.ar/metrics

# Test actual WhatsApp integration
# Enviar mensaje de prueba desde número configurado
```

### Comandos para Verificar que Todo Funciona
```bash
#!/bin/bash
# scripts/post-deploy-verification.sh

BASE_URL="https://agente-hotel.com.ar"

echo "🔍 Verificando despliegue post-deployment..."

# 1. Health checks
echo "1️⃣ Health checks..."
curl -f $BASE_URL/health/live || echo "❌ Liveness check failed"
curl -f $BASE_URL/health/ready || echo "❌ Readiness check failed"

# 2. Database connectivity
echo "2️⃣ Database connectivity..."
curl -f $BASE_URL/health/ready | jq '.database' || echo "❌ Database check failed"

# 3. Redis connectivity  
echo "3️⃣ Redis connectivity..."
curl -f $BASE_URL/health/ready | jq '.redis' || echo "❌ Redis check failed"

# 4. PMS connectivity
echo "4️⃣ PMS connectivity..."
curl -f $BASE_URL/health/ready | jq '.pms' || echo "❌ PMS check failed"

# 5. SSL certificate
echo "5️⃣ SSL certificate..."
curl -I $BASE_URL | grep "HTTP/2 200" || echo "❌ SSL/HTTPS failed"

echo "✅ Verificación completada!"
```

### Logs Críticos a Revisar
```bash
# Railway logs
railway logs --service agente-api

# Buscar errores críticos
railway logs --service agente-api | grep -i "error\|exception\|failed"

# Verificar startup logs
railway logs --service agente-api | head -50

# Verificar database connections
railway logs --service agente-api | grep -i "database\|postgres\|redis"

# WhatsApp integration logs
railway logs --service agente-api | grep -i "whatsapp\|webhook"
```

### Tests de Funcionalidad Básicos
```bash
# Test WhatsApp webhook
curl -X POST https://agente-hotel.com.ar/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=test_signature" \
  -d '{"object":"whatsapp_business_account","entry":[{"changes":[{"value":{"messages":[{"from":"549xxxxxxxxx","text":{"body":"Hola"},"timestamp":"1234567890","type":"text"}]}}]}]}'

# Test Gmail integration (si está configurado)
curl -X POST https://agente-hotel.com.ar/admin/test-email \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Test PMS integration
curl https://agente-hotel.com.ar/admin/pms/status \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 5. ROLLBACK Y RECOVERY

### Cómo Hacer Rollback si Algo Falla
```bash
#!/bin/bash
# scripts/rollback.sh

echo "🔄 Iniciando rollback de emergencia..."

# 1. Rollback usando Railway
railway rollback --service agente-api

# 2. O usando Docker (si es self-hosted)
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --scale agente-api=0
docker-compose -f docker-compose.production.yml run --rm backup-restore
docker-compose -f docker-compose.production.yml up -d

# 3. Verificar rollback exitoso
sleep 30
curl -f https://agente-hotel.com.ar/health/live || {
    echo "❌ Rollback failed! Manual intervention required"
    exit 1
}

echo "✅ Rollback completado exitosamente"
```

### Backup de Configuraciones
```bash
#!/bin/bash
# scripts/backup-config.sh

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup environment variables
railway env > $BACKUP_DIR/railway-env.txt

# Backup docker configurations
cp docker-compose.production.yml $BACKUP_DIR/
cp Dockerfile.production $BACKUP_DIR/

# Backup database schema
railway run --service postgres pg_dump $DATABASE_URL > $BACKUP_DIR/postgres-schema.sql
railway run --service mysql mysqldump --all-databases > $BACKUP_DIR/mysql-schema.sql

echo "✅ Configuration backup saved to $BACKUP_DIR"
```

### Recovery Plan Básico
```bash
#!/bin/bash
# scripts/disaster-recovery.sh

echo "🚨 Iniciando disaster recovery..."

# 1. Restore desde backup más reciente
LATEST_BACKUP=$(ls -1t backups/ | head -1)
echo "Restoring from backup: $LATEST_BACKUP"

# 2. Restore databases
railway run --service postgres psql < backups/$LATEST_BACKUP/postgres-schema.sql
railway run --service mysql mysql < backups/$LATEST_BACKUP/mysql-schema.sql

# 3. Restore environment variables
railway env set --file backups/$LATEST_BACKUP/railway-env.txt

# 4. Redeploy application
railway deploy --service agente-api

# 5. Verify recovery
sleep 60
curl -f https://agente-hotel.com.ar/health/ready || {
    echo "❌ Recovery failed! Escalating to manual intervention"
    # Send alert to operations team
    curl -X POST $SLACK_WEBHOOK_URL -d "{\"text\":\"🚨 DISASTER RECOVERY FAILED - Manual intervention required\"}"
    exit 1
}

echo "✅ Disaster recovery completed successfully"
```

## Comandos Copy-Paste Ready

### Setup Completo Inicial
```bash
# 1. Clone and setup
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api

# 2. Install dependencies
pip install poetry
poetry install --all-extras --no-root

# 3. Setup Railway
npm install -g @railway/cli
railway login
railway init

# 4. Deploy to production
make validate-deployment
railway deploy
```

### Monitoreo Continuo
```bash
# Watch logs in real-time
railway logs --service agente-api --follow

# Monitor health checks every 30 seconds
watch -n 30 'curl -s https://agente-hotel.com.ar/health/ready | jq'

# Monitor error rates
railway logs --service agente-api | grep -i error | wc -l
```