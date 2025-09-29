# PLAN DE DESPLIEGUE UNIVERSAL - SIST_AGENTICO_HOTELERO

## CHECKLIST PRE-DESPLIEGUE

- [ ] **Secrets validation**: Todos los REPLACE_WITH_* en .env reemplazados
- [ ] **Tests passing**: `make test` exitoso  
- [ ] **Security scan**: `make security-fast` sin HIGH/CRITICAL
- [ ] **Docker build**: `docker build -t agente-hotel:prod .` exitoso
- [ ] **Health checks**: /health/live y /health/ready funcionando
- [ ] **PMS connectivity**: QloApps API accesible y autenticado
- [ ] **External APIs**: WhatsApp webhook verificado, Gmail SMTP configurado
- [ ] **.gitignore/.dockerignore**: Secrets excluidos correctamente
- [ ] **Backup strategy**: Scripts backup/restore validados
- [ ] **Monitoring**: Prometheus/Grafana endpoints configurados
- [ ] **SSL certificates**: Certbot/Let's Encrypt para HTTPS
- [ ] **Resource limits**: Docker memory/CPU limits definidos

## PLATAFORMAS RECOMENDADAS

| Plataforma | Uso Ideal | MVP USD Estimado | Umbral Escalado | Justificación (evidencia) |
|------------|-----------|------------------|-----------------|---------------------------|
| **Railway** | Prototipo/MVP rápido | $20-50/mes | <1000 usuarios | FastAPI + Postgres + Redis todo managed. docker-compose.yml:48-180 compatible |
| **DigitalOcean App Platform** | Startup escalable | $50-100/mes | <5000 usuarios | Docker nativo, auto-scaling. Dockerfile.production:80 optimizado para production |
| **AWS ECS Fargate** | Enterprise/HA | $100-300/mes | >5000 usuarios | Multi-AZ, load balancer. docker/nginx/nginx.conf:1-50 preparado para LB |
| **Google Cloud Run** | Serverless cost-effective | $30-80/mes | Variable/burst | FastAPI async compatible. app/main.py:43 lifespan configurado |
| **Self-hosted VPS** | Control total/Argentina | $40-80/mes | Fijo | Makefile:50-95 Docker commands listos. scripts/deploy.sh para automation |

**JUSTIFICACIÓN**: Evidencia multi-servicio en docker-compose.yml requiere orchestration. FastAPI async + health checks (Dockerfile:42-43) compatible con cloud platforms.

## PIPELINE DE DESPLIEGUE MÍNIMA

### GitHub Actions (Recomendado - evidencia en .github/workflows/)

```yaml
# .github/workflows/deploy.yml - YA EXISTE
name: Deploy to Production
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd agente-hotel-api
          pip install -r requirements-prod.txt
      
      - name: Run tests
        run: |
          cd agente-hotel-api
          pytest tests/
      
      - name: Security scan
        run: |
          cd agente-hotel-api  
          make security-fast

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        run: |
          # Railway CLI deployment
          npx @railway/cli deploy --service agente-api
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### Script Shell Básico (Backup/Rollback)

```bash
#!/bin/bash
# scripts/deploy-production.sh

set -euo pipefail

echo "🚀 Production Deployment Started"

# 1. Pre-deployment validation
echo "1️⃣ Validating environment..."
./scripts/pre-deployment-validation.sh

# 2. Backup current state
echo "2️⃣ Creating backup..."
./scripts/backup.sh

# 3. Deploy new version
echo "3️⃣ Deploying application..."
docker-compose -f docker-compose.production.yml up -d --build

# 4. Health check validation
echo "4️⃣ Validating health..."
timeout 60s bash -c 'until curl -f http://localhost:8000/health/ready; do sleep 5; done'

# 5. Success notification
echo "✅ Deployment completed successfully"
```

## DB / MIGRATIONS / DOMINIOS

### Database Bootstrap Commands

```bash
# PostgreSQL (Agent Database)
createdb agente_hotel
psql agente_hotel -c "CREATE USER agente_user WITH PASSWORD 'secure_password';"
psql agente_hotel -c "GRANT ALL PRIVILEGES ON DATABASE agente_hotel TO agente_user;"

# MySQL (QloApps PMS) - from docker-compose.yml:30-33
docker-compose exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "
CREATE DATABASE IF NOT EXISTS qloapps;
CREATE USER IF NOT EXISTS 'qloapps'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON qloapps.* TO 'qloapps'@'%';
FLUSH PRIVILEGES;"

# Redis (Cache/Locks) - from docker-compose.yml:94-100
docker-compose exec redis redis-cli CONFIG SET requirepass "${REDIS_PASSWORD}"
```

### Migration Commands (Inferido de SQLAlchemy)

```bash
# Based on app/core/database.py patterns
cd agente-hotel-api

# Create migration (if using Alembic)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Domain Configuration

```bash
# SSL Certificate with Certbot (from .env.example:117-119)
certbot certonly --webroot -w /var/www/certbot \
  -d ${DOMAIN} \
  --email ${EMAIL_FOR_CERTBOT} \
  --agree-tos --no-eff-email

# NGINX Configuration (from docker/nginx/nginx.conf)
cp docker/nginx/nginx.conf /etc/nginx/sites-available/agente-hotel
ln -sf /etc/nginx/sites-available/agente-hotel /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## ROLLBACK & BACKUP

### Backup MVP Script (from scripts/backup.sh)

```bash
#!/bin/bash
# scripts/automated-backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Starting automated backup..."

# 1. PostgreSQL Backup
echo "1️⃣ Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dump -U agente_user agente_hotel > "$BACKUP_DIR/postgres.sql"

# 2. MySQL Backup  
echo "2️⃣ Backing up MySQL..."
docker-compose exec -T mysql mysqldump -u qloapps -p${MYSQL_PASSWORD} qloapps > "$BACKUP_DIR/mysql.sql"

# 3. Redis Backup
echo "3️⃣ Backing up Redis..."
docker-compose exec -T redis redis-cli --rdb "$BACKUP_DIR/redis.rdb"

# 4. Application Config Backup
echo "4️⃣ Backing up configurations..."
cp .env "$BACKUP_DIR/env.backup"
cp docker-compose.production.yml "$BACKUP_DIR/"

# 5. Compress and cleanup
tar -czf "/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "✅ Backup completed successfully"
```

### Rollback Steps

```bash
#!/bin/bash
# scripts/rollback.sh

set -euo pipefail

BACKUP_FILE="${1:-latest}"

echo "🔄 Starting rollback process..."

# 1. Stop current services
echo "1️⃣ Stopping services..."
docker-compose -f docker-compose.production.yml down

# 2. Restore from backup
echo "2️⃣ Restoring from backup: $BACKUP_FILE"
if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_FILE=$(ls -t /backups/*.tar.gz | head -1)
fi

tar -xzf "$BACKUP_FILE" -C /tmp/
BACKUP_DIR=$(find /tmp -name "backup_*" -type d | head -1)

# 3. Restore databases
echo "3️⃣ Restoring databases..."
docker-compose up -d postgres mysql redis
sleep 10

# PostgreSQL restore
docker-compose exec -T postgres psql -U agente_user -d agente_hotel < "$BACKUP_DIR/postgres.sql"

# MySQL restore  
docker-compose exec -T mysql mysql -u qloapps -p${MYSQL_PASSWORD} qloapps < "$BACKUP_DIR/mysql.sql"

# 4. Restart services
echo "4️⃣ Restarting services..."
docker-compose -f docker-compose.production.yml up -d

# 5. Verify rollback
echo "5️⃣ Verifying rollback..."
timeout 60s bash -c 'until curl -f http://localhost:8000/health/ready; do sleep 5; done'

echo "✅ Rollback completed successfully"
```

## DOCKERFILE MULTI-STAGE OPTIMIZADO

```dockerfile
# Dockerfile.universal - Optimizado basado en Dockerfile.production:1-80

# Stage 1: Build
FROM python:3.12-slim AS build
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --user -r requirements-prod.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install runtime dependencies (from Dockerfile:22-26)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl \
        espeak \
        ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Python packages from build stage
COPY --from=build /root/.local /root/.local

# Copy application code
COPY ./app ./app

# Security: non-root user (from Dockerfile:38-39)
RUN adduser --disabled-password --gecos '' --uid 1000 appuser \
    && chown -R appuser:appuser /app

# Environment variables (from Dockerfile:32-35)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH

# Health check (from Dockerfile:42-43)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

USER appuser
EXPOSE 8000

# Production command with configurable workers
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers=${UVICORN_WORKERS:-4}"]
```

## COMANDOS COPY-PASTE PARA DEPLOYMENT

```bash
# 1. Clone and setup
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api

# 2. Environment setup
cp .env.example .env.production
# EDIT .env.production - Replace all REPLACE_WITH_* values

# 3. Build and test locally
make install
make lint
make test
docker build -t agente-hotel:local -f Dockerfile.production .

# 4. Deploy to Railway (if using Railway)
npm install -g @railway/cli
railway login
railway link [project-id]
railway env set SECRET_KEY=$(openssl rand -hex 32)
railway env set PMS_API_KEY=your_pms_key
railway env set GMAIL_APP_PASSWORD=your_gmail_password
railway deploy

# 5. Deploy with Docker Compose (self-hosted)
docker-compose -f docker-compose.production.yml up -d --build

# 6. Verify deployment
curl -f https://your-domain.com/health/ready
curl -f https://your-domain.com/metrics

# 7. Setup monitoring
docker-compose exec grafana grafana-cli admin reset-admin-password newpassword
```

## ESTIMACIÓN DE COSTOS POR PLATAFORMA

**Railway**: $5/servicio/mes × 6 servicios = $30/mes base + $2/GB RAM = ~$50/mes total
**DigitalOcean**: $12/mes app + $15/mes managed DB + $15/mes Redis = ~$42/mes
**AWS ECS Fargate**: $30/mes compute + $25/mes RDS + $20/mes ElastiCache = ~$75/mes
**Google Cloud Run**: Pay-per-request, estimado $20-40/mes para MVP
**VPS Argentina**: $40-60/mes VPS + backup storage = ~$50-70/mes

**RECOMENDACIÓN**: Railway para MVP rápido, DigitalOcean para crecimiento, AWS para enterprise.