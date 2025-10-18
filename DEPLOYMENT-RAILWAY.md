# 🚂 Deployment a Railway - Agente Hotelero IA

**Última actualización**: 2025-10-18  
**Versión Railway CLI**: 3.x  
**Estado**: ✅ Configuración completada y validada

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Pre-requisitos](#pre-requisitos)
3. [Configuración Railway](#configuración-railway)
4. [Variables de Entorno](#variables-de-entorno)
5. [Proceso de Deployment](#proceso-de-deployment)
6. [Monitoreo y Health Checks](#monitoreo-y-health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Costos Estimados](#costos-estimados)

---

## 🎯 Resumen Ejecutivo

### ¿Qué es Railway?

Railway es una plataforma PaaS (Platform as a Service) que permite desplegar aplicaciones con configuración mínima. Detecta automáticamente el tipo de proyecto y maneja la infraestructura.

### ¿Por qué Railway?

✅ **Deployment ultra-rápido** (5-10 minutos)  
✅ **Auto-escalado** incluido  
✅ **Base de datos PostgreSQL** integrada  
✅ **Monitoreo** built-in  
✅ **CI/CD automático** desde GitHub  
✅ **Gratis para empezar** ($5 crédito inicial)

### Estado del Proyecto

- ✅ Dockerfile optimizado para producción
- ✅ railway.json configurado
- ✅ railway.toml configurado (alternativa)
- ✅ Procfile configurado (fallback)
- ✅ Health checks implementados
- ✅ Variables de entorno documentadas

---

## 🔧 Pre-requisitos

### 1. Cuenta Railway

Crear cuenta en: https://railway.app/

**Opciones de autenticación**:
- GitHub (recomendado - permite CI/CD automático)
- Email/Password

### 2. Railway CLI (Opcional)

```bash
# Instalación con npm
npm install -g @railway/cli

# O con Homebrew (macOS/Linux)
brew install railway

# Verificar instalación
railway --version
```

### 3. Repositorio GitHub

- ✅ Repositorio: `eevans-d/SIST_AGENTICO_HOTELERO`
- ✅ Rama principal: `main`
- ✅ Archivos de configuración commiteados

### 4. Secretos/Credenciales

Necesitarás los siguientes secretos (ver sección [Variables de Entorno](#variables-de-entorno)):

**Críticos**:
- `JWT_SECRET` - Para autenticación
- `POSTGRES_PASSWORD` - Base de datos

**WhatsApp** (opcional):
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`

**Gmail** (opcional):
- `GMAIL_APP_PASSWORD`

---

## ⚙️ Configuración Railway

### Archivos de Configuración Creados

#### 1. `railway.json` (Principal)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "agente-hotel-api/Dockerfile.production",
    "watchPatterns": [
      "agente-hotel-api/app/**",
      "agente-hotel-api/pyproject.toml",
      "agente-hotel-api/requirements-prod.txt"
    ]
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4",
    "healthcheckPath": "/health/live",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Explicación**:
- **builder**: Usa Dockerfile para construir la imagen
- **dockerfilePath**: Ruta al Dockerfile de producción
- **watchPatterns**: Archivos que disparan rebuild automático
- **startCommand**: Comando para iniciar la aplicación
- **healthcheckPath**: Endpoint para health checks
- **healthcheckTimeout**: 5 minutos para inicialización
- **restartPolicyType**: Reiniciar solo en fallos
- **restartPolicyMaxRetries**: Máximo 10 intentos

#### 2. `railway.toml` (Alternativa)

Formato TOML para configuración Railway (más legible):

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "agente-hotel-api/Dockerfile.production"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4"
healthcheckPath = "/health/live"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

#### 3. `Procfile` (Fallback)

Si Railway no detecta el Dockerfile, usa este comando:

```
web: cd agente-hotel-api && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
```

### ¿Cuál usar?

Railway prioriza en este orden:
1. `railway.json` (más específico)
2. `railway.toml` (más legible)
3. `Procfile` (compatibilidad Heroku)
4. Auto-detección (Dockerfile, package.json, etc.)

**Recomendación**: Usa `railway.json` (ya configurado) ✅

---

## 🔐 Variables de Entorno

### Variables Requeridas

Railway necesita las siguientes variables configuradas en el dashboard:

#### Aplicación Core

```bash
# Entorno
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Seguridad (GENERAR NUEVOS VALORES)
JWT_SECRET=<GENERAR_CON_openssl_rand_-base64_32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

#### Base de Datos PostgreSQL

Railway proporciona PostgreSQL automáticamente. Las variables se inyectan automáticamente:

```bash
# Railway inyecta automáticamente:
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# O configurar manualmente:
POSTGRES_HOST=${{ POSTGRES.RAILWAY_PRIVATE_DOMAIN }}
POSTGRES_PORT=5432
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<AUTO_GENERADO_POR_RAILWAY>
```

#### Redis (Opcional - Agregar servicio)

```bash
REDIS_HOST=${{ REDIS.RAILWAY_PRIVATE_DOMAIN }}
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<AUTO_GENERADO_SI_SE_AGREGA>
```

#### WhatsApp (Opcional)

```bash
WHATSAPP_ACCESS_TOKEN=<TOKEN_DE_META>
WHATSAPP_PHONE_NUMBER_ID=<PHONE_ID_DE_META>
WHATSAPP_API_VERSION=v21.0
WHATSAPP_WEBHOOK_VERIFY_TOKEN=<TOKEN_CUSTOM>
```

#### Gmail (Opcional)

```bash
GMAIL_ENABLED=false
GMAIL_APP_PASSWORD=<APP_PASSWORD_DE_GMAIL>
GMAIL_FROM_EMAIL=tu-email@gmail.com
```

#### PMS Adapter

```bash
# Modo mock para desarrollo
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080
PMS_TIMEOUT=30
PMS_HOTEL_ID=1

# Modo real (cuando esté listo)
# PMS_TYPE=qloapps
# PMS_BASE_URL=https://tu-qloapps.com
# PMS_API_KEY=<API_KEY_QLOAPPS>
```

#### Audio Processing (Opcional)

```bash
AUDIO_PROCESSOR_ENABLED=false
TTS_ENGINE=espeak
STT_ENGINE=whisper
```

### 🔑 Generar Secretos Seguros

```bash
# JWT Secret (32 bytes, base64)
openssl rand -base64 32

# JWT Refresh Secret (32 bytes, base64)
openssl rand -base64 32

# WhatsApp Webhook Verify Token (16 bytes, hex)
openssl rand -hex 16

# Encryption Key (32 bytes, base64)
openssl rand -base64 32
```

---

## 🚀 Proceso de Deployment

### Opción A: Deployment desde Web UI (Recomendado)

#### Paso 1: Crear Proyecto

1. Ir a https://railway.app/dashboard
2. Click en **"New Project"**
3. Seleccionar **"Deploy from GitHub repo"**
4. Autorizar Railway a acceder a tu GitHub
5. Seleccionar repositorio: `eevans-d/SIST_AGENTICO_HOTELERO`
6. Seleccionar rama: `main`

#### Paso 2: Agregar PostgreSQL

1. En el proyecto, click en **"+ New"**
2. Seleccionar **"Database"** → **"PostgreSQL"**
3. Railway crea automáticamente:
   - PostgreSQL 14
   - Base de datos `railway`
   - Usuario `postgres`
   - Password auto-generado
   - Variable `DATABASE_URL` inyectada

#### Paso 3: Configurar Variables de Entorno

1. Click en el servicio `agente-hotel-api`
2. Click en tab **"Variables"**
3. Agregar variables una por una o usar **"Raw Editor"**:

```bash
# Core
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
JWT_SECRET=<GENERAR_CON_COMANDO_ARRIBA>
JWT_ALGORITHM=HS256

# PMS
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080

# Rate Limiting
RATE_LIMIT_ENABLED=true
```

4. Click en **"Add Reference Variable"** para DATABASE_URL:
   - Variable: `DATABASE_URL`
   - Reference: `${{ POSTGRES.DATABASE_URL }}`

#### Paso 4: Configurar Networking

1. En el servicio, click en **"Settings"**
2. Scroll a **"Networking"**
3. Click en **"Generate Domain"**
4. Railway genera URL pública: `https://tu-proyecto.up.railway.app`

#### Paso 5: Deploy

1. Railway detecta automáticamente cambios en GitHub
2. Inicia build con Dockerfile.production
3. Muestra logs en tiempo real
4. Cuando termine, el servicio está **LIVE** ✅

**Duración**: ~5-10 minutos

#### Paso 6: Verificar Deployment

```bash
# Health check
curl https://tu-proyecto.up.railway.app/health/live

# Respuesta esperada:
{
  "status": "ok",
  "timestamp": "2025-10-18T10:00:00Z",
  "version": "0.1.0"
}
```

---

### Opción B: Deployment desde CLI

#### Paso 1: Login

```bash
railway login
```

Abre navegador para autenticación.

#### Paso 2: Inicializar Proyecto

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO

# Link a proyecto existente
railway link

# O crear nuevo proyecto
railway init
```

#### Paso 3: Agregar PostgreSQL

```bash
railway add --database postgres
```

#### Paso 4: Configurar Variables

```bash
# Agregar variable individual
railway variables set JWT_SECRET="$(openssl rand -base64 32)"

# O cargar desde archivo
railway variables set --file .env.railway
```

#### Paso 5: Deploy

```bash
railway up
```

Railway:
1. Sube código
2. Construye Dockerfile
3. Despliega servicio
4. Muestra URL pública

#### Paso 6: Ver Logs

```bash
railway logs
```

---

## 📊 Monitoreo y Health Checks

### Health Check Endpoints

Railway chequea automáticamente `/health/live` cada 30 segundos.

**Endpoints disponibles**:

1. **`GET /health/live`** - Liveness (siempre 200)
   ```bash
   curl https://tu-proyecto.up.railway.app/health/live
   ```

2. **`GET /health/ready`** - Readiness (200 si deps OK)
   ```bash
   curl https://tu-proyecto.up.railway.app/health/ready
   ```

3. **`GET /metrics`** - Prometheus metrics
   ```bash
   curl https://tu-proyecto.up.railway.app/metrics
   ```

### Monitoreo en Railway Dashboard

1. **Logs**: Ver logs en tiempo real
   - Click en servicio → Tab **"Logs"**
   - Filtrar por nivel (ERROR, WARNING, INFO)

2. **Metrics**: CPU, Memory, Network
   - Click en servicio → Tab **"Metrics"**
   - Ver uso de recursos en tiempo real

3. **Deployments**: Historial de deployments
   - Click en servicio → Tab **"Deployments"**
   - Ver builds exitosos/fallidos

### Alerts

Railway NO tiene alerting nativo. Opciones:

1. **Integrar con Prometheus** (requiere plan Pro)
2. **Usar webhook** a servicio externo (PagerDuty, Slack)
3. **Cron job** externo que chequee health endpoint

---

## 🐛 Troubleshooting

### Problema 1: Build Fallido

**Síntoma**: Railway no puede construir el Dockerfile

**Causa posible**:
- Dockerfile.production no encontrado
- Dependencias faltantes en requirements-prod.txt

**Solución**:
```bash
# Verificar que existe
ls agente-hotel-api/Dockerfile.production

# Verificar sintaxis
docker build -f agente-hotel-api/Dockerfile.production .

# Ver logs en Railway Dashboard
railway logs --deployment <DEPLOYMENT_ID>
```

### Problema 2: Start Command Failed

**Síntoma**: Build OK pero servicio no inicia

**Causa posible**:
- Puerto incorrecto (debe ser `$PORT` de Railway)
- Variables de entorno faltantes
- Base de datos no conectada

**Solución**:
```bash
# Verificar variables en dashboard
railway variables

# Verificar DATABASE_URL existe
railway variables get DATABASE_URL

# Ver logs de inicio
railway logs --tail
```

### Problema 3: Health Check Timeout

**Síntoma**: Railway marca servicio como "unhealthy"

**Causa posible**:
- Aplicación tarda >300s en iniciar
- Endpoint /health/live no responde
- Puerto incorrecto

**Solución**:
```bash
# Verificar endpoint localmente
docker run -p 8000:8000 <IMAGE> &
curl http://localhost:8000/health/live

# Ajustar timeout en railway.json
"healthcheckTimeout": 600  # 10 minutos
```

### Problema 4: Base de Datos no Conecta

**Síntoma**: Error "connection refused" en logs

**Causa posible**:
- DATABASE_URL mal configurado
- PostgreSQL service no iniciado
- Network policy bloqueando conexión

**Solución**:
```bash
# Verificar PostgreSQL está corriendo
railway status

# Reiniciar PostgreSQL
railway restart --service postgres

# Verificar variable DATABASE_URL
railway variables get DATABASE_URL
```

### Problema 5: Port Already in Use

**Síntoma**: Error "address already in use"

**Causa posible**:
- Start command usa puerto fijo (8000) en vez de `$PORT`

**Solución**:

Editar `railway.json`:
```json
"startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4"
```

✅ **Correcto**: `--port $PORT` (variable de Railway)  
❌ **Incorrecto**: `--port 8000` (hardcoded)

### Problema 6: Out of Memory

**Síntoma**: Servicio se reinicia constantemente

**Causa posible**:
- Workers configurados muy alto (4 workers en plan Hobby = OOM)
- Memory leaks en código

**Solución**:
```bash
# Reducir workers en railway.json
"startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"

# O upgrade a plan Pro con más RAM
```

### Problema 7: GitHub CI/CD no Dispara

**Síntoma**: Push a main pero Railway no hace rebuild

**Causa posible**:
- Webhook de GitHub no configurado
- Archivos modificados no están en watchPatterns

**Solución**:
```bash
# Verificar webhooks en GitHub
# Settings → Webhooks → Railway debe aparecer

# Agregar más patterns en railway.json
"watchPatterns": [
  "agente-hotel-api/app/**",
  "agente-hotel-api/pyproject.toml",
  "agente-hotel-api/requirements-prod.txt",
  "agente-hotel-api/Dockerfile.production"
]

# Deploy manual si es urgente
railway up --detach
```

---

## 💰 Costos Estimados

### Plan Hobby (Gratis - Trial)

**Incluye**:
- $5 crédito inicial (500 GB-hours)
- 1 servicio concurrente
- 512 MB RAM
- 1 vCPU
- PostgreSQL incluido (512 MB RAM)

**Duración estimada**: ~300-500 horas con 1 servicio

**Ideal para**: Development, testing, MVP

### Plan Pro ($20/mes)

**Incluye**:
- $20 crédito mensual (2000 GB-hours)
- Servicios ilimitados
- 8 GB RAM por servicio
- 8 vCPU por servicio
- PostgreSQL con backups
- Custom domains

**Ideal para**: Staging, producción pequeña

### Plan Team ($50/mes)

**Incluye**:
- $50 crédito mensual (5000 GB-hours)
- Todo de Pro +
- Múltiples proyectos
- Team collaboration
- Priority support

**Ideal para**: Producción mediana, equipos

### Estimación para este Proyecto

**Configuración recomendada**:
- 1 servicio FastAPI (agente-hotel-api)
- 1 PostgreSQL
- 1 Redis (opcional)

**Costos mensuales estimados**:

| Plan | Servicios | RAM Total | Costo |
|------|-----------|-----------|-------|
| **Hobby** (Trial) | 2 (API + DB) | 1 GB | Gratis (~15 días) |
| **Pro** | 3 (API + DB + Redis) | 2 GB | $5-10/mes |
| **Pro** (Optimized) | 3 servicios | 4 GB | $15-20/mes |

**Cálculo**:
- API (2 workers, 1 GB RAM): ~$3-5/mes
- PostgreSQL (1 GB RAM): ~$2-3/mes
- Redis (512 MB RAM): ~$1-2/mes
- **Total**: ~$6-10/mes en plan Pro

---

## 📝 Checklist de Deployment

### Pre-Deployment

- [x] railway.json creado
- [x] railway.toml creado (alternativa)
- [x] Procfile creado (fallback)
- [x] Dockerfile.production optimizado
- [x] requirements-prod.txt actualizado
- [ ] Secretos generados (JWT_SECRET, etc.)
- [ ] Variables de entorno documentadas

### Durante Deployment

- [ ] Proyecto creado en Railway
- [ ] Repositorio GitHub conectado
- [ ] PostgreSQL agregado
- [ ] Variables de entorno configuradas
- [ ] Domain público generado
- [ ] Build completado exitosamente
- [ ] Servicio en estado "LIVE"

### Post-Deployment

- [ ] Health check responde 200
- [ ] Logs no muestran errores críticos
- [ ] Database conectada exitosamente
- [ ] API responde a requests
- [ ] Metrics endpoint accesible
- [ ] Monitoreo configurado
- [ ] Alerting configurado (opcional)

---

## 🔗 Links Útiles

- **Railway Dashboard**: https://railway.app/dashboard
- **Railway Docs**: https://docs.railway.app
- **Railway CLI**: https://docs.railway.app/develop/cli
- **Railway Status**: https://status.railway.app
- **Railway Discord**: https://discord.gg/railway

---

## 🎯 Próximos Pasos

### Ahora (Deployment Inicial)

1. ✅ Configuración completada
2. 🔄 Push configuración a GitHub
3. ⏳ Crear proyecto en Railway (15 min)
4. ⏳ Configurar variables (10 min)
5. ⏳ Primer deployment (5-10 min)

### Mañana (Post-Deployment)

- Verificar logs por 24h
- Monitorear uso de recursos
- Load testing básico
- Documentar findings

### Próxima Semana (Optimización)

- Agregar Redis para caching
- Configurar custom domain
- Implementar CI/CD completo
- Backup strategy

---

**Preparado por**: GitHub Copilot  
**Fecha**: 2025-10-18  
**Validado**: ✅ Configuración lista para deployment  
**Próximo paso**: Push a GitHub y crear proyecto en Railway
