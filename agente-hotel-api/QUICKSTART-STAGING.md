# 🚀 QUICK START: Deployment a Staging

**TL;DR**: Guía rápida para desplegar en staging en **30 minutos**.

---

## ⚡ Fast Track (Para Expertos)

```bash
# 1. Configurar secrets (5 min)
cp .env.example .env.staging
nano .env.staging  # Reemplazar TODOS los REPLACE_WITH_*

# 2. Ejecutar deployment automatizado (15 min)
./scripts/deploy-staging.sh

# 3. Verificar (5 min)
curl http://localhost:8002/health/ready
make health

# 4. Monitoring (5 min)
# Abrir en navegador:
# - Grafana: http://localhost:3000
# - Prometheus: http://localhost:9090
# - API: http://localhost:8002/metrics
```

**Si hay problemas**: Ver sección [Troubleshooting](#troubleshooting)

---

## 📝 Paso a Paso Detallado

### PASO 1: Preparar Secrets (5 min)

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Copiar template
cp .env.example .env.staging

# Generar secrets automáticamente
cat > /tmp/generate-secrets.sh << 'EOF'
#!/bin/bash
echo "# Secrets generados automáticamente - $(date)"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)"
echo "MYSQL_PASSWORD=$(openssl rand -base64 24)"
echo "MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 16)"
echo "WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 16)"
EOF

chmod +x /tmp/generate-secrets.sh
/tmp/generate-secrets.sh > /tmp/secrets.txt

# Copiar secrets al clipboard (manual)
cat /tmp/secrets.txt

# Editar .env.staging y reemplazar placeholders
nano .env.staging
```

**⚠️ CRÍTICO**: Reemplazar estos valores en `.env.staging`:
- `SECRET_KEY=REPLACE_WITH_SECURE_32_CHAR_HEX_KEY`
- `POSTGRES_PASSWORD=REPLACE_WITH_SECURE_POSTGRES_PASSWORD`
- `MYSQL_PASSWORD=REPLACE_WITH_SECURE_MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD=REPLACE_WITH_SECURE_MYSQL_ROOT_PASSWORD`
- `REDIS_PASSWORD=REPLACE_WITH_SECURE_REDIS_PASSWORD`
- `WHATSAPP_ACCESS_TOKEN=REPLACE_WITH_REAL_META_ACCESS_TOKEN` (si usas WhatsApp)
- `WHATSAPP_PHONE_NUMBER_ID=REPLACE_WITH_REAL_PHONE_NUMBER_ID` (si usas WhatsApp)
- `GMAIL_APP_PASSWORD=REPLACE_WITH_GMAIL_APP_PASSWORD` (si usas Gmail)

**Para staging inicial**: Usar `PMS_TYPE=mock` (no necesitas QloApps real)

### PASO 2: Deployment Automatizado (15 min)

```bash
# Ejecutar script automatizado
./scripts/deploy-staging.sh

# O con opciones:
# ./scripts/deploy-staging.sh --skip-backup  # Sin backup
# ./scripts/deploy-staging.sh --skip-tests   # Sin tests
```

**El script hará automáticamente**:
1. ✅ Validar pre-requisitos (Docker, jq, secrets)
2. ✅ Verificar git status
3. ✅ Backup de databases existentes
4. ✅ Build Docker images
5. ✅ Deploy stack completo (7 servicios)
6. ✅ Health checks
7. ✅ Smoke tests
8. ✅ Revisar logs

**Tiempo estimado**: 15-20 minutos

### PASO 3: Verificación (5 min)

```bash
# Health checks manuales
curl http://localhost:8002/health/live
# Esperado: {"status":"ok"}

curl http://localhost:8002/health/ready | jq '.'
# Esperado: {"status":"ready","database":"ok","redis":"ok","pms":"ok"}

# Ver servicios
docker ps --filter "name=agente" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check automatizado
make health
```

### PASO 4: Monitoreo (5 min)

**Abrir en navegador**:
- **API**: http://localhost:8002/metrics
- **Prometheus**: http://localhost:9090
  - Query: `rate(http_requests_total[5m])`
- **Grafana**: http://localhost:3000
  - User: `admin`
  - Pass: `admin` (cambiar en primer login)

**Ver logs en tiempo real**:
```bash
docker compose -f docker-compose.staging.yml logs -f agente-api
```

---

## 🎯 Checklist de Validación

### Inmediato (0-15 min)
- [ ] `curl http://localhost:8002/health/live` → HTTP 200
- [ ] `curl http://localhost:8002/health/ready` → todos "ok"
- [ ] `docker ps` → 7 contenedores running
- [ ] `docker logs agente_hotel_api` → sin errores críticos
- [ ] Grafana accesible → http://localhost:3000
- [ ] Prometheus accesible → http://localhost:9090

### Corto plazo (1 hora)
- [ ] Logs estables (sin errores) durante 30 min
- [ ] Memory usage < 70%
- [ ] CPU usage < 60%
- [ ] Response time P95 < 500ms
- [ ] Test webhook WhatsApp (si aplica)
- [ ] Test email notification (si aplica)

### Antes de Go-Live
- [ ] Load test con 10 usuarios concurrentes
- [ ] Monitoring baseline capturado
- [ ] Alerting configurado y probado
- [ ] Runbooks documentados
- [ ] Rollback procedure validado

---

## 🐛 Troubleshooting

### Issue 1: "Puerto 8002 ya está en uso"

```bash
# Ver qué usa el puerto
sudo lsof -i :8002

# Matar proceso
sudo kill -9 <PID>

# O cambiar puerto en docker-compose.staging.yml
# ports:
#   - "8003:8002"  # Cambiar puerto externo
```

### Issue 2: "Secret_KEY validation failed"

```bash
# Verificar placeholders en .env.staging
grep REPLACE_WITH .env.staging

# Si hay matches, editar y reemplazar
nano .env.staging

# Regenerar secret específico
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY"

# Actualizar .env.staging y recrear container
docker compose -f docker-compose.staging.yml up -d --force-recreate agente-api
```

### Issue 3: "Database connection failed"

```bash
# Verificar Postgres running
docker ps --filter "name=postgres"

# Ver logs
docker logs postgres | tail -50

# Test connection
docker exec postgres pg_isready -U agente_user

# Si falla, verificar password en .env.staging
grep POSTGRES .env.staging

# Recrear database
docker compose -f docker-compose.staging.yml down
docker volume rm agente-hotel-api_postgres_data
docker compose -f docker-compose.staging.yml up -d
```

### Issue 4: "Health check failing"

```bash
# Ver logs detallados
docker logs --tail 100 agente_hotel_api

# Buscar errores
docker logs agente_hotel_api 2>&1 | grep -i "error\|exception"

# Verificar variables de entorno
docker exec agente_hotel_api env | grep -E "POSTGRES|REDIS|PMS"

# Restart servicio
docker restart agente_hotel_api

# Esperar 30s y retry health check
sleep 30
curl http://localhost:8002/health/ready
```

### Issue 5: "Out of memory"

```bash
# Ver uso de recursos
docker stats --no-stream

# Si memory usage > 80%, aumentar límites
# Editar docker-compose.staging.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G  # Aumentar de 1G a 2G

# Recrear servicios
docker compose -f docker-compose.staging.yml up -d --force-recreate
```

---

## 🔄 Rollback Rápido

```bash
# Si algo falla, rollback inmediato:
docker compose -f docker-compose.staging.yml down

# Restaurar backup (si hiciste backup)
tar -xzf /opt/backups/agente-hotel/backup-pre-deploy-*.tar.gz

# O revertir commit
git log --oneline -5
git checkout <commit-hash-anterior>

# Redeploy
./scripts/deploy-staging.sh --skip-backup
```

---

## 📊 Comandos Útiles

```bash
# Ver estado
docker compose -f docker-compose.staging.yml ps

# Logs en tiempo real
docker compose -f docker-compose.staging.yml logs -f

# Logs de servicio específico
docker logs -f agente_hotel_api

# Restart servicio
docker compose -f docker-compose.staging.yml restart agente-api

# Stop todo
docker compose -f docker-compose.staging.yml down

# Rebuild y redeploy
docker compose -f docker-compose.staging.yml up -d --build

# Health check
make health

# Tests
make test-unit
poetry run pytest tests/test_health.py -v

# Backup manual
make backup

# Ver métricas
curl http://localhost:8002/metrics | grep http_requests_total
```

---

## 📞 Ayuda

Si necesitas ayuda:

1. **Revisar logs**: `docker logs agente_hotel_api`
2. **Ver documentación completa**: `DEPLOYMENT-STAGING-PLAN.md`
3. **Consultar troubleshooting**: Esta guía, sección superior
4. **Crear issue**: Si encuentras un bug real

---

## ✅ Success Criteria

**Deployment exitoso SI**:
- ✅ Health checks passing durante 15 min
- ✅ 0 errores en logs (últimas 100 líneas)
- ✅ Smoke tests 5/5 passing
- ✅ Monitoring dashboards accesibles
- ✅ Response time P95 < 500ms
- ✅ CPU < 60%, Memory < 70%

**Rollback requerido SI**:
- ❌ Health checks failing después de 5 min
- ❌ Errores críticos en logs
- ❌ Database connection errors
- ❌ Response time P95 > 2000ms
- ❌ Memory leaks (uso crece >10% cada 5 min)

---

## 🎉 Next Steps

Después de deployment exitoso:

1. **Monitorear 24h** → Capturar baseline metrics
2. **Load testing** → 100 usuarios concurrentes
3. **User testing** → Validar con equipo interno
4. **Documentation** → Actualizar runbooks
5. **Production planning** → Preparar deployment a prod

---

**Preparado por**: GitHub Copilot  
**Fecha**: 2025-10-17  
**Versión**: 1.0

🚀 **¡Listo para deployment!**
