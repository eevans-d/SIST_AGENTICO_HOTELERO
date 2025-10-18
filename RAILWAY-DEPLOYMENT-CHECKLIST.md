# ✅ Railway Deployment Checklist

**Proyecto**: SIST_AGENTICO_HOTELERO  
**Fecha**: 2025-10-18  
**Duración estimada**: 30-45 minutos

---

## 📋 Pre-Deployment (5 minutos)

### Verificar Configuración Local

- [ ] **railway.json existe y está commiteado**
  ```bash
  git ls-files railway.json
  # Debe mostrar: railway.json
  ```

- [ ] **railway.toml existe y está commiteado**
  ```bash
  git ls-files railway.toml
  # Debe mostrar: railway.toml
  ```

- [ ] **Procfile existe y está commiteado**
  ```bash
  git ls-files Procfile
  # Debe mostrar: Procfile
  ```

- [ ] **Dockerfile.production existe**
  ```bash
  ls agente-hotel-api/Dockerfile.production
  # Debe mostrar el archivo
  ```

- [ ] **requirements-prod.txt existe**
  ```bash
  ls agente-hotel-api/requirements-prod.txt
  # Si no existe, generar:
  cd agente-hotel-api && poetry export -f requirements.txt -o requirements-prod.txt --without-hashes
  ```

### Generar Secretos

- [ ] **Ejecutar script de generación**
  ```bash
  ./scripts/generate-railway-secrets.sh
  ```

- [ ] **Verificar archivo generado**
  ```bash
  ls -lh .env.railway.local
  # Debe mostrar: -rw------- (permisos 600)
  ```

- [ ] **Guardar secretos en password manager**
  - JWT_SECRET
  - JWT_REFRESH_SECRET
  - ENCRYPTION_KEY
  - WHATSAPP_WEBHOOK_VERIFY_TOKEN

---

## 🚂 Deployment en Railway (20 minutos)

### Crear Proyecto

- [ ] **Ir a Railway Dashboard**
  - URL: https://railway.app/dashboard

- [ ] **Click en "New Project"**

- [ ] **Seleccionar "Deploy from GitHub repo"**

- [ ] **Autorizar Railway en GitHub** (si es primera vez)

- [ ] **Seleccionar repositorio**
  - Repositorio: `eevans-d/SIST_AGENTICO_HOTELERO`
  - Rama: `main`

- [ ] **Esperar detección automática**
  - Railway debe detectar: Dockerfile.production
  - Builder: DOCKERFILE
  - Start command: Debe usar railway.json

### Agregar PostgreSQL

- [ ] **Click en "+ New" en el proyecto**

- [ ] **Seleccionar "Database" → "PostgreSQL"**

- [ ] **Esperar aprovisionamiento** (~2 minutos)
  - PostgreSQL 14
  - Base de datos: `railway`
  - Usuario: `postgres`
  - Password: auto-generado

- [ ] **Verificar variable DATABASE_URL**
  - Click en servicio PostgreSQL
  - Tab "Variables"
  - Debe mostrar: DATABASE_URL

### Configurar Variables de Entorno

- [ ] **Click en servicio `agente-hotel-api`**

- [ ] **Click en tab "Variables"**

- [ ] **Click en "Raw Editor"**

- [ ] **Copiar desde `.env.railway.local`** (o pegar uno por uno)

**Variables críticas mínimas**:

```bash
# Core
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
JWT_SECRET=<DE_.env.railway.local>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# PMS
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

- [ ] **Agregar referencia a DATABASE_URL**
  - Click en "+ New Variable"
  - Variable: `DATABASE_URL`
  - Value: `${{ POSTGRES.DATABASE_URL }}`
  - Click "Add"

- [ ] **Click en "Save"**

### Configurar Dominio Público

- [ ] **En servicio `agente-hotel-api`, ir a "Settings"**

- [ ] **Scroll a sección "Networking"**

- [ ] **Click en "Generate Domain"**

- [ ] **Anotar URL generada**
  - Formato: `https://tu-proyecto.up.railway.app`
  - Guardar URL para testing

### Deploy

- [ ] **Railway inicia build automáticamente**
  - Ver logs en tiempo real
  - Tab "Deployments" → Click en deployment activo

- [ ] **Esperar build completo** (~5-8 minutos)
  - Estado debe cambiar a: BUILDING → SUCCESS

- [ ] **Esperar deploy completo** (~1-2 minutos)
  - Estado debe cambiar a: DEPLOYING → LIVE

---

## ✅ Post-Deployment (10 minutos)

### Health Checks

- [ ] **Verificar health endpoint**
  ```bash
  curl https://tu-proyecto.up.railway.app/health/live
  ```
  
  **Respuesta esperada**:
  ```json
  {
    "status": "ok",
    "timestamp": "2025-10-18T...",
    "version": "0.1.0"
  }
  ```

- [ ] **Verificar readiness endpoint**
  ```bash
  curl https://tu-proyecto.up.railway.app/health/ready
  ```
  
  **Respuesta esperada**:
  ```json
  {
    "status": "ok",
    "checks": {
      "database": "ok",
      "redis": "ok"
    }
  }
  ```

- [ ] **Verificar metrics endpoint**
  ```bash
  curl https://tu-proyecto.up.railway.app/metrics
  ```
  
  **Debe mostrar**: Métricas Prometheus (texto plano)

### Logs

- [ ] **Revisar logs de inicio**
  - En Railway Dashboard → Servicio → Tab "Logs"
  - Buscar: "Application startup complete"
  - NO debe haber errores críticos

- [ ] **Verificar conexión a base de datos**
  - En logs, buscar: "Database connected"
  - NO debe haber: "connection refused", "authentication failed"

- [ ] **Verificar workers iniciados**
  - En logs, buscar: "Started server process"
  - Debe mostrar: 4 workers (UVICORN_WORKERS=4)

### Métricas

- [ ] **Verificar CPU usage**
  - En Railway Dashboard → Servicio → Tab "Metrics"
  - CPU debe estar: <50% en idle

- [ ] **Verificar Memory usage**
  - Memory debe estar: <300 MB en idle

- [ ] **Verificar Network**
  - Debe haber tráfico en gráficas de Network

### Smoke Tests

- [ ] **Test básico de API**
  ```bash
  curl https://tu-proyecto.up.railway.app/
  ```
  
  **Respuesta esperada**:
  ```json
  {
    "message": "Agente Hotel API",
    "version": "0.1.0",
    "status": "ok"
  }
  ```

- [ ] **Test de webhook (opcional)**
  ```bash
  curl -X POST https://tu-proyecto.up.railway.app/api/webhooks/whatsapp \
    -H "Content-Type: application/json" \
    -d '{"test": true}'
  ```
  
  **Debe responder**: 200 o 400 (no 500)

---

## 🔍 Monitoreo Continuo (Próximas 24h)

### Checks cada 1 hora

- [ ] **Health endpoint responde 200**
  ```bash
  curl -I https://tu-proyecto.up.railway.app/health/live
  ```

- [ ] **Logs no muestran errores críticos**
  - Railway Dashboard → Logs
  - Filtrar por: ERROR, CRITICAL

- [ ] **CPU/Memory estables**
  - Railway Dashboard → Metrics
  - CPU: <60%
  - Memory: <500 MB

### Checks cada 4 horas

- [ ] **Database está conectada**
  ```bash
  curl https://tu-proyecto.up.railway.app/health/ready | jq .checks.database
  ```

- [ ] **No hay circuit breaker abiertos**
  ```bash
  curl https://tu-proyecto.up.railway.app/metrics | grep pms_circuit_breaker_state
  # Valor esperado: 0 (closed)
  ```

### Checks cada 24 horas

- [ ] **Deployment sigue LIVE**
  - Railway Dashboard → Status debe ser: LIVE

- [ ] **Logs no muestran memory leaks**
  - Memory usage debe ser estable (no creciente)

- [ ] **Railway credits consumption**
  - Dashboard → Billing
  - Verificar consumo diario (~$0.50-1.00/día)

---

## 🐛 Troubleshooting

### Si build falla

```bash
# Ver logs de build
railway logs --deployment <DEPLOYMENT_ID>

# Verificar Dockerfile localmente
docker build -f agente-hotel-api/Dockerfile.production .

# Reintentar build
railway up --detach
```

### Si health check falla

```bash
# Ver logs de aplicación
railway logs --tail

# Verificar variables de entorno
railway variables

# Verificar DATABASE_URL existe
railway variables get DATABASE_URL
```

### Si servicio se reinicia constantemente

```bash
# Reducir workers (OOM posible)
railway variables set UVICORN_WORKERS=2

# Verificar memory usage
# Dashboard → Metrics → Memory
```

---

## 📊 Resultados Esperados

### Deployment Exitoso

✅ Build: SUCCESS en 5-8 minutos  
✅ Deploy: LIVE en 1-2 minutos  
✅ Health: 200 OK  
✅ Logs: Sin errores críticos  
✅ CPU: <50% idle  
✅ Memory: <300 MB idle  

### URL Pública

```
https://tu-proyecto.up.railway.app
```

### Servicios Desplegados

1. **agente-hotel-api** (FastAPI)
   - Workers: 4
   - Memory: ~300 MB
   - CPU: <50%

2. **PostgreSQL** (Database)
   - Version: 14
   - Memory: ~100 MB
   - Storage: ~50 MB

**Total Memory**: ~400 MB  
**Total CPU**: <60%

---

## 📝 Post-Deployment

### Documentar

- [ ] **Anotar URL pública**
- [ ] **Guardar secretos en password manager**
- [ ] **Documentar issues encontrados**
- [ ] **Actualizar DEPLOYMENT-RAILWAY.md con findings**

### Próximos Pasos

- [ ] **Agregar Redis** (opcional, mejora performance)
- [ ] **Configurar custom domain** (opcional)
- [ ] **Setup monitoring externo** (UptimeRobot, etc.)
- [ ] **Load testing** (50-100 concurrent users)

---

## 🎉 Checklist Completado

**Fecha**: _____________  
**Hora inicio**: _____________  
**Hora fin**: _____________  
**Duración**: _____________  
**URL pública**: _____________  
**Estado final**: ⬜ SUCCESS  ⬜ FAILED  

**Notas**:
```
[Agregar observaciones, issues, o aprendizajes aquí]
```

---

**Preparado por**: GitHub Copilot  
**Última actualización**: 2025-10-18  
**Validado**: ✅ Ready for deployment
