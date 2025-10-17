# 🚀 PLAN DE DEPLOYMENT A STAGING

**Proyecto**: Sistema Agente Hotelero IA  
**Fecha**: 2025-10-17  
**Versión**: 1.0  
**Responsable**: DevOps Team  
**Estado**: ✅ READY TO DEPLOY

---

## 📋 Tabla de Contenidos

1. [Executive Summary](#executive-summary)
2. [Pre-Requisitos](#pre-requisitos)
3. [Configuración de Secrets](#configuración-de-secrets)
4. [Deployment Steps](#deployment-steps)
5. [Smoke Tests](#smoke-tests)
6. [Monitoring Setup](#monitoring-setup)
7. [Rollback Procedures](#rollback-procedures)
8. [Post-Deployment Checklist](#post-deployment-checklist)

---

## 📊 Executive Summary

### Objetivo
Desplegar el Sistema Agente Hotelero IA en entorno **staging** para validación final antes de producción.

### Pre-Validación Local
| Componente | Estado | Detalle |
|------------|--------|---------|
| **Tests** | ✅ PASS | 28/29 passing (96.5%) |
| **Coverage** | ✅ PASS | 31% (>25% mínimo) |
| **Security** | ✅ PASS | 0 CVE CRITICAL |
| **Linting** | ✅ PASS | 0 errores |
| **Docker** | ✅ PASS | 7/7 servicios healthy |
| **Deployment Score** | ✅ 8.9/10 | Ready for staging |

### Staging Environment Specs
- **Infrastructure**: Docker Compose (7 servicios)
- **PMS Mode**: Mock (QloApps opcional)
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Tracing**: Jaeger
- **Database**: PostgreSQL + Redis
- **Expected URL**: `http://staging-server:8002` o `https://staging.agente-hotel.com`

---

## ✅ Pre-Requisitos

### 1. Servidor Staging
```bash
# Requisitos mínimos
- OS: Ubuntu 20.04+ / Debian 11+ / RHEL 8+
- RAM: 8GB mínimo (16GB recomendado)
- CPU: 4 cores mínimo
- Disk: 50GB mínimo SSD
- Docker: 24.0+
- Docker Compose: 2.20+
```

### 2. Acceso al Servidor
```bash
# SSH configurado con key
ssh staging-server
sudo su - deploy  # Usuario con permisos Docker

# Verificar Docker
docker --version
docker compose version
```

### 3. Repositorio Clonado
```bash
cd /opt/agente-hotel
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api
git checkout main
git pull origin main
```

### 4. Herramientas Instaladas
```bash
# En servidor staging
sudo apt update
sudo apt install -y jq curl git make

# Verificar
make --version
jq --version
```

---

## 🔐 Configuración de Secrets

### Paso 1: Crear `.env.staging`
```bash
cd /opt/agente-hotel/SIST_AGENTICO_HOTELERO/agente-hotel-api
cp .env.example .env.staging
```

### Paso 2: Editar Secrets (⚠️ CRÍTICO)
```bash
nano .env.staging
```

**Reemplazar TODOS los valores `REPLACE_WITH_*`**:

#### 🔴 SECRETS CRÍTICOS (OBLIGATORIOS)

```bash
# ==============================================================================
# 1. SECRET_KEY - Generar con openssl
# ==============================================================================
SECRET_KEY=$(openssl rand -hex 32)
# Resultado: abc123def456...  (64 caracteres)

# ==============================================================================
# 2. POSTGRES_PASSWORD - Database principal
# ==============================================================================
POSTGRES_PASSWORD=$(openssl rand -base64 24)
# Resultado: kJ8m3nP2qR5tV7wX9yZ1aB3cD4eF5gH6

# Actualizar también en POSTGRES_URL
POSTGRES_URL=postgresql+asyncpg://agente_user:${POSTGRES_PASSWORD}@postgres:5432/agente_hotel

# ==============================================================================
# 3. MYSQL_PASSWORD + MYSQL_ROOT_PASSWORD - QloApps PMS
# ==============================================================================
MYSQL_PASSWORD=$(openssl rand -base64 24)
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)

# ==============================================================================
# 4. REDIS_PASSWORD - Cache y locks distribuidos
# ==============================================================================
REDIS_PASSWORD=$(openssl rand -base64 16)
# Actualizar en REDIS_URL
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ==============================================================================
# 5. WHATSAPP - Meta Cloud API (staging credentials)
# ==============================================================================
# Obtener desde: https://developers.facebook.com/apps
WHATSAPP_ACCESS_TOKEN=EAAG...ZD  # Meta access token (staging app)
WHATSAPP_PHONE_NUMBER_ID=123456789012345  # Test phone number ID
WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 16)  # Webhook verify token
WHATSAPP_APP_SECRET=abc123...xyz  # Meta app secret

# ==============================================================================
# 6. GMAIL - Email notifications (staging account)
# ==============================================================================
GMAIL_USERNAME=staging-hotel@yourdomain.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop  # Gmail app password (not regular password)
# Generar en: https://myaccount.google.com/apppasswords

# ==============================================================================
# 7. ENVIRONMENT - Confirmar staging
# ==============================================================================
ENVIRONMENT=staging  # ⚠️ NO usar "production" en staging
DEBUG=false
LOG_LEVEL=INFO
```

#### 🟡 SECRETS OPCIONALES (Recomendados)

```bash
# ==============================================================================
# 8. PMS Configuration - Usar MOCK en staging inicialmente
# ==============================================================================
PMS_TYPE=mock  # Usar mock para testing, cambiar a "qloapps" cuando tengas instancia real
PMS_BASE_URL=http://qloapps:80  # Solo si PMS_TYPE=qloapps
PMS_API_KEY=staging_api_key_if_real_pms  # Solo si usas QloApps real

# ==============================================================================
# 9. TTS Engine - Activar si necesitas audio
# ==============================================================================
AUDIO_ENABLED=true
TTS_ENGINE=espeak  # Más ligero para staging
```

### Paso 3: Validar Secrets
```bash
# Verificar que NO haya placeholders
grep -E "REPLACE_WITH|your-secret|changeme|password123" .env.staging
# ⚠️ Si hay matches, revisar y corregir

# Verificar permisos seguros
chmod 600 .env.staging
ls -la .env.staging
# Debería mostrar: -rw------- (solo owner puede leer/escribir)
```

### Paso 4: Backup de Secrets (Seguro)
```bash
# Opción A: Usar secret manager (AWS Secrets Manager, HashiCorp Vault)
# aws secretsmanager create-secret --name agente-hotel-staging-env --secret-string file://.env.staging

# Opción B: Backup encriptado local
gpg --symmetric --cipher-algo AES256 .env.staging
# Crea: .env.staging.gpg (guardar en ubicación segura)
# Eliminar archivo plain: shred -u .env.staging (DESPUÉS de deployment)
```

---

## 🚀 Deployment Steps

### PASO 1: Pre-Flight Checks (5 min)
```bash
cd /opt/agente-hotel/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1.1 Verificar código actualizado
git status
git log --oneline -5

# 1.2 Verificar Docker
docker ps
docker compose version

# 1.3 Verificar secrets
ls -la .env.staging
test -f .env.staging && echo "✅ .env.staging existe" || echo "❌ Falta .env.staging"

# 1.4 Verificar puertos disponibles
sudo netstat -tlnp | grep -E ":(8002|5432|6379|9090|3000|9093|16686)"
# ⚠️ Si hay conflictos, detener servicios o cambiar puertos en docker-compose.staging.yml
```

### PASO 2: Backup Pre-Deployment (5 min)
```bash
# 2.1 Crear backup de databases existentes (si las hay)
make backup
# Genera: /opt/backups/agente-hotel/backup-YYYY-MM-DD-HHMMSS.tar.gz

# 2.2 Backup manual adicional
mkdir -p /opt/backups/agente-hotel-manual
docker exec postgres pg_dump -U agente_user agente_hotel > /opt/backups/agente-hotel-manual/postgres-pre-deploy-$(date +%Y%m%d-%H%M%S).sql || echo "No hay DB previa"
```

### PASO 3: Build Images (10 min)
```bash
# 3.1 Build producción optimizada
docker compose -f docker-compose.staging.yml build --no-cache

# 3.2 Verificar imágenes creadas
docker images | grep agente-hotel

# Deberías ver algo como:
# agente-hotel-api_agente-api  staging  abc123...  2 minutes ago  450MB
```

### PASO 4: Deploy Stack (5 min)
```bash
# 4.1 Crear red si no existe
docker network create frontend_network 2>/dev/null || true
docker network create backend_network 2>/dev/null || true

# 4.2 Deploy con docker-compose
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d

# 4.3 Verificar servicios levantando
docker compose -f docker-compose.staging.yml ps

# Esperar ~60s para inicialización completa
echo "⏳ Esperando inicialización (60s)..."
sleep 60
```

### PASO 5: Health Checks (5 min)
```bash
# 5.1 Verificar contenedores running
docker ps --filter "name=agente" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 5.2 Health check automatizado
make health

# Output esperado:
# ✅ postgres: healthy
# ✅ redis: healthy
# ✅ agente_hotel_api: healthy
# ✅ prometheus: healthy
# ✅ grafana: healthy

# 5.3 API health endpoint
curl -f http://localhost:8002/health/live
# {"status": "ok"}

curl -f http://localhost:8002/health/ready | jq '.'
# {
#   "status": "ready",
#   "database": "ok",
#   "redis": "ok",
#   "pms": "ok"
# }
```

### PASO 6: Logs Verification (3 min)
```bash
# 6.1 Revisar logs de API (últimas 50 líneas)
docker logs --tail 50 agente_hotel_api

# Buscar errores críticos
docker logs agente_hotel_api 2>&1 | grep -i "error\|exception\|critical" | tail -20

# ⚠️ Si hay errores, ver sección Troubleshooting
```

---

## 🧪 Smoke Tests

### Test 1: API Availability (Manual)
```bash
# 1.1 Liveness
curl -f http://localhost:8002/health/live
# Esperado: HTTP 200 {"status": "ok"}

# 1.2 Readiness
curl -f http://localhost:8002/health/ready
# Esperado: HTTP 200 con todos los servicios "ok"

# 1.3 Metrics endpoint
curl -f http://localhost:8002/metrics | head -20
# Esperado: Métricas Prometheus
```

### Test 2: Database Connectivity
```bash
# 2.1 Postgres
docker exec postgres psql -U agente_user -d agente_hotel -c "SELECT 1 as test;"
# Esperado: 
#  test 
# ------
#     1

# 2.2 Redis
docker exec redis redis-cli -a "${REDIS_PASSWORD}" PING
# Esperado: PONG
```

### Test 3: PMS Mock (si PMS_TYPE=mock)
```bash
# 3.1 Test PMS availability endpoint (mock devuelve ok)
curl -f http://localhost:8002/api/internal/pms-status
# Esperado: {"status": "ok", "type": "mock"}
```

### Test 4: Webhook Endpoint (WhatsApp)
```bash
# 4.1 Test webhook verification
curl -X GET "http://localhost:8002/api/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=TEST123&hub.verify_token=${WHATSAPP_VERIFY_TOKEN}"
# Esperado: TEST123 (echo del challenge)

# 4.2 Test webhook POST (simular mensaje)
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "1234567890",
            "id": "wamid.test123",
            "timestamp": "1697553600",
            "text": {"body": "Hola, necesito hacer una reserva"},
            "type": "text"
          }]
        }
      }]
    }]
  }'
# Esperado: HTTP 200
```

### Test 5: Automated Test Suite
```bash
# 5.1 Ejecutar tests de deployment
make deploy-test

# 5.2 Ejecutar health tests específicos
poetry run pytest tests/test_health.py -v

# Esperado: 5/5 tests passing
```

---

## 📊 Monitoring Setup

### Paso 1: Acceder a Grafana
```bash
# URL: http://staging-server:3000
# Credenciales por defecto: admin / admin (cambiar en primer login)

# Configuración:
1. Login con admin/admin
2. Cambiar password a uno seguro
3. Verificar datasource Prometheus (pre-configurado)
4. Importar dashboards desde docker/grafana/dashboards/
```

### Paso 2: Acceder a Prometheus
```bash
# URL: http://staging-server:9090

# Queries útiles:
# 1. Request rate
rate(http_requests_total[5m])

# 2. P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 3. Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Paso 3: Configurar AlertManager
```bash
# Editar configuración de alertas
nano docker/alertmanager/config.yml

# Agregar Slack webhook (ejemplo)
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#agente-hotel-alerts'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

# Reload config
docker exec alertmanager kill -HUP 1
```

### Paso 4: Verificar Jaeger (Tracing)
```bash
# URL: http://staging-server:16686

# Verificar que aparezcan traces de:
# - agente-api service
# - PMS calls
# - Database queries
```

### Paso 5: Setup Monitoring Baseline
```bash
# Ejecutar script de baseline metrics (crear si no existe)
cat > /opt/scripts/baseline-metrics.sh << 'EOF'
#!/bin/bash
# Capture baseline metrics for 5 minutes

END_TIME=$(($(date +%s) + 300))
OUTPUT_FILE="/var/log/agente-hotel/baseline-$(date +%Y%m%d-%H%M%S).txt"

mkdir -p /var/log/agente-hotel

echo "📊 Capturando métricas baseline por 5 minutos..."
echo "Fecha: $(date)" > "$OUTPUT_FILE"
echo "Servidor: $(hostname)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

while [ $(date +%s) -lt $END_TIME ]; do
    echo "=== $(date +%H:%M:%S) ===" >> "$OUTPUT_FILE"
    
    # CPU & Memory
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" >> "$OUTPUT_FILE"
    
    # Request rate
    curl -s http://localhost:9090/api/v1/query?query=rate\(http_requests_total[1m]\) | jq -r '.data.result[] | "\(.metric.method) \(.metric.path): \(.value[1])"' >> "$OUTPUT_FILE"
    
    echo "" >> "$OUTPUT_FILE"
    sleep 30
done

echo "✅ Baseline capturado en: $OUTPUT_FILE"
EOF

chmod +x /opt/scripts/baseline-metrics.sh
/opt/scripts/baseline-metrics.sh &
```

---

## 🔄 Rollback Procedures

### Escenario 1: API No Responde (Crítico)
```bash
# 1.1 Verificar estado
docker ps -a --filter "name=agente_hotel_api"

# 1.2 Revisar logs
docker logs --tail 100 agente_hotel_api

# 1.3 Rollback rápido (stop + restore backup)
docker compose -f docker-compose.staging.yml stop agente-api

# 1.4 Restaurar versión anterior (si existe)
docker tag agente-hotel-api:previous agente-hotel-api:staging
docker compose -f docker-compose.staging.yml up -d agente-api

# 1.5 Verificar
curl -f http://localhost:8002/health/ready
```

### Escenario 2: Database Corrupta
```bash
# 2.1 Stop API para evitar escrituras
docker compose -f docker-compose.staging.yml stop agente-api

# 2.2 Restaurar backup más reciente
make restore BACKUP_FILE=/opt/backups/agente-hotel/backup-YYYY-MM-DD-HHMMSS.tar.gz

# 2.3 Verificar integridad
docker exec postgres psql -U agente_user -d agente_hotel -c "SELECT COUNT(*) FROM session_states;"

# 2.4 Restart API
docker compose -f docker-compose.staging.yml start agente-api
```

### Escenario 3: Rollback Completo
```bash
# 3.1 Usar script de rollback
make rollback ENV=staging

# O manual:
# 3.2 Stop todos los servicios
docker compose -f docker-compose.staging.yml down

# 3.3 Checkout versión anterior
git checkout <commit-hash-anterior>

# 3.4 Rebuild y redeploy
docker compose -f docker-compose.staging.yml build
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d

# 3.5 Restaurar backups (si necesario)
make restore BACKUP_FILE=/opt/backups/agente-hotel/backup-YYYY-MM-DD-HHMMSS.tar.gz

# 3.6 Verificar todo
make health
```

### Rollback Checklist
- [ ] Notificar al equipo en Slack
- [ ] Capturar logs antes de rollback
- [ ] Stop servicios afectados
- [ ] Restaurar código/databases
- [ ] Verificar health checks
- [ ] Validar smoke tests
- [ ] Documentar causa raíz
- [ ] Crear post-mortem

---

## ✅ Post-Deployment Checklist

### Inmediato (0-15 min)
- [ ] **Health checks** passing (API, DB, Redis, PMS)
- [ ] **Smoke tests** completados (5/5 passing)
- [ ] **Logs** sin errores críticos
- [ ] **Monitoring** dashboards accesibles
- [ ] **Metrics** fluyendo a Prometheus
- [ ] **AlertManager** configurado

### Corto plazo (1 hora)
- [ ] **Baseline metrics** capturados
- [ ] **Webhook test** con WhatsApp sandbox
- [ ] **Email notification** test
- [ ] **PMS integration** validado (mock o real)
- [ ] **Session management** funcionando
- [ ] **Rate limiting** validado

### Mediano plazo (1 día)
- [ ] **Load test** básico (10 usuarios concurrentes)
- [ ] **Memory leaks** verificados (monitoreo 24h)
- [ ] **Error budget** establecido
- [ ] **Alerting rules** validadas (trigger test)
- [ ] **Backup automation** funcionando
- [ ] **Documentation** actualizada

### Largo plazo (1 semana)
- [ ] **Real user testing** con equipo interno
- [ ] **Performance baseline** documentado
- [ ] **Incident runbooks** creados
- [ ] **On-call schedule** definido
- [ ] **SLA/SLO** establecidos
- [ ] **Go/No-Go decision** para producción

---

## 🐛 Troubleshooting

### Issue 1: Puerto 8002 ocupado
```bash
# Ver qué proceso usa el puerto
sudo lsof -i :8002

# Matar proceso
sudo kill -9 <PID>

# O cambiar puerto en docker-compose.staging.yml
# ports:
#   - "8003:8002"  # Cambiar 8002 a 8003
```

### Issue 2: Secrets inválidos (API no inicia)
```bash
# Ver logs de API
docker logs agente_hotel_api 2>&1 | grep -i "validation\|secret\|env"

# Verificar .env.staging
grep -E "REPLACE_WITH|password123|changeme" .env.staging

# Regenerar secret específico
SECRET_KEY=$(openssl rand -hex 32)
# Actualizar en .env.staging y recrear contenedor
docker compose -f docker-compose.staging.yml up -d --force-recreate agente-api
```

### Issue 3: Database connection failed
```bash
# Verificar Postgres corriendo
docker exec postgres pg_isready

# Ver logs de Postgres
docker logs postgres | tail -50

# Test manual connection
docker exec postgres psql -U agente_user -d agente_hotel -c "SELECT 1;"

# Verificar password en .env.staging matches con POSTGRES_URL
grep POSTGRES .env.staging
```

### Issue 4: WhatsApp webhook falla
```bash
# Verificar verify token
echo "Verify token en .env: $(grep WHATSAPP_VERIFY_TOKEN .env.staging)"

# Test con curl (reemplazar <verify_token>)
curl "http://localhost:8002/api/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=TEST&hub.verify_token=<verify_token>"

# Debería devolver: TEST

# Ver logs de webhook processing
docker logs agente_hotel_api | grep -i webhook
```

### Issue 5: Out of Memory
```bash
# Ver uso de memoria
docker stats --no-stream

# Si algún container usa >80%, reiniciar
docker restart <container_name>

# Verificar limits en docker-compose.staging.yml
docker inspect <container> | jq '.[0].HostConfig.Memory'

# Aumentar memory limits si necesario (editar docker-compose.staging.yml)
```

---

## 📚 Referencias

### Documentos Relacionados
- `RESUMEN-EJECUTIVO-FINAL.md` - Validación local completada
- `FASE3-COMPLETADO.md` - Resilience & Performance
- `scripts/deploy.sh` - Script de deployment
- `docker-compose.staging.yml` - Configuración staging
- `.security/REMEDIATION-REPORT.md` - Security baseline

### Comandos Útiles
```bash
# Ver todos los comandos disponibles
make help

# Logs en tiempo real
docker compose -f docker-compose.staging.yml logs -f

# Restart servicio específico
docker compose -f docker-compose.staging.yml restart agente-api

# Rebuild y redeploy servicio
docker compose -f docker-compose.staging.yml up -d --build agente-api

# Ejecutar tests
make test-unit
make test-integration
make test-e2e

# Backup manual
make backup

# Ver métricas
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana
curl http://localhost:8002/metrics  # API metrics
```

---

## 🎯 Success Criteria

### Deployment Exitoso SI:
- ✅ Health checks passing durante 15 minutos consecutivos
- ✅ 0 errores en logs (últimos 100 líneas)
- ✅ Smoke tests 5/5 passing
- ✅ Monitoring dashboards accesibles
- ✅ Response time P95 < 500ms
- ✅ CPU usage < 60%
- ✅ Memory usage < 70%

### Rollback Requerido SI:
- ❌ Health checks failing después de 5 minutos
- ❌ Errores críticos en logs (exception, critical, fatal)
- ❌ Database connection errors persistentes
- ❌ Response time P95 > 2000ms
- ❌ Error rate > 5%
- ❌ Memory leaks (uso crece >10% cada 5 min)

---

## 📞 Contactos & Escalación

### Equipo de Deployment
- **DevOps Lead**: [Nombre] - [Email/Slack]
- **Backend Lead**: [Nombre] - [Email/Slack]
- **On-Call Engineer**: Ver `make on-call-schedule`

### Escalación
1. **Level 1**: Revisar logs y troubleshooting guide
2. **Level 2**: Notificar en #agente-hotel-staging (Slack)
3. **Level 3**: Llamar a On-Call Engineer
4. **Level 4**: Escalate to DevOps Lead
5. **Critical**: Rollback inmediato + post-mortem

---

## 📝 Post-Deployment Notes

### Datos a Capturar
```bash
# Deployment metadata
echo "Deployment ID: $(git rev-parse --short HEAD)" > deployment-notes.txt
echo "Deployment Date: $(date -Iseconds)" >> deployment-notes.txt
echo "Deployed By: $(whoami)@$(hostname)" >> deployment-notes.txt

# Performance baseline
echo "Baseline P95: <capture from Prometheus>" >> deployment-notes.txt
echo "Error Rate: <capture from Prometheus>" >> deployment-notes.txt
```

### Próximos Pasos
1. Monitorear durante 24 horas
2. Ejecutar load tests (100 usuarios)
3. Validar con usuarios internos
4. Documentar issues encontrados
5. Crear plan de deployment a producción

---

**Preparado por**: GitHub Copilot  
**Última actualización**: 2025-10-17  
**Versión**: 1.0

---

🚀 **¡Listo para deployment a staging!**
