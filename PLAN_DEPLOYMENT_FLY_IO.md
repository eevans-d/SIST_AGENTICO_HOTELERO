# 🚀 PLAN DEPLOYMENT FLY.IO - Sistema Agente Hotelero

**Documento**: Plan Deployment Fly.io  
**Fecha**: 2025-10-30  
**Status**: READY FOR EXECUTION  
**System Readiness**: 9.8/10 ⭐  

---

## 📋 TABLA DE CONTENIDOS

1. [Pre-Requisitos](#pre-requisitos)
2. [Fase 1: Instalación Fly CLI](#fase-1-instalación-fly-cli)
3. [Fase 2: Verificación Pre-Deploy](#fase-2-verificación-pre-deploy)
4. [Fase 3: Configuración Fly.io](#fase-3-configuración-flyio)
5. [Fase 4: Secrets & Variables](#fase-4-secrets--variables)
6. [Fase 5: Deployment](#fase-5-deployment)
7. [Fase 6: Validación & Monitoreo](#fase-6-validación--monitoreo)

---

## 📌 PRE-REQUISITOS

### Verificar Antes de Iniciar

```bash
# 1. Verificar Git está limpio (0 changes)
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
git status
# Debe mostrar: "nothing to commit, working tree clean"

# 2. Verificar sistema está healthy
docker ps
# Debe mostrar 7 servicios corriendo (prod o staging)

# 3. Verificar Docker está instalado
docker --version
# Debe mostrar: Docker version XX.XX.XX

# 4. Verificar acceso a GitHub
git remote -v
# Debe mostrar: origin pointing to eevans-d/SIST_AGENTICO_HOTELERO
```

### Requisitos Necesarios

- ✅ **Cuenta Fly.io**: [https://fly.io/app/sign-up](https://fly.io/app/sign-up)
  - Crea cuenta GRATUITA (includes $3/mo free credit)
  - Verifica email
  - Genera auth token

- ✅ **Fly CLI**: Instalaremos en FASE 1

- ✅ **Docker**: Ya debe estar instalado (lo hemos usado)

- ✅ **Git**: Ya debe estar configurado

---

## 🔧 FASE 1: INSTALACIÓN FLY CLI

### Paso 1.1: Descargar e Instalar Fly CLI

**Para Linux (tu sistema):**

```bash
# Descargar el installer
curl -L https://fly.io/install.sh | sh

# El script instalará Fly CLI en: ~/.fly/bin/flyctl
# Se agregará automáticamente al PATH

# Verificar instalación
which flyctl
# Debe mostrar ruta de instalación, ej: /home/eevan/.fly/bin/flyctl
```

### Paso 1.2: Verificar Instalación

```bash
# Verificar versión
flyctl version
# Debe mostrar: Fly CLI vX.X.X

# Verificar que está en PATH
echo $PATH | grep -i fly
# Debe mostrar ruta con fly

# Test rápido
flyctl --help
# Debe mostrar help menu completo
```

### Paso 1.3: Autenticarse con Fly.io

```bash
# Login interactivo
flyctl auth login

# Pasos:
# 1. Se abrirá navegador automáticamente
# 2. Login en Fly.io con tu cuenta
# 3. Autoriza acceso a Fly CLI
# 4. Vuelve a terminal - verás "Logged in successfully"

# Verificar autenticación
flyctl auth whoami
# Debe mostrar tu usuario de Fly.io
```

---

## ✅ FASE 2: VERIFICACIÓN PRE-DEPLOY

### Paso 2.1: Revisar Archivos Críticos

```bash
# Verificar estructura necesaria
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Debe existir: Dockerfile
ls -la Dockerfile
# -rw-r--r-- 1 eevan eevan XXXX XXX XX XX:XX Dockerfile

# Debe existir: .dockerignore
ls -la .dockerignore
# -rw-r--r-- 1 eevan eevan XXXX XXX XX XX:XX .dockerignore

# Debe existir: pyproject.toml
ls -la pyproject.toml
# -rw-r--r-- 1 eevan eevan XXXX XXX XX XX:XX pyproject.toml

# Debe existir: app/main.py
ls -la app/main.py
# -rw-r--r-- 1 eevan eevan XXXX XXX XX XX:XX app/main.py
```

### Paso 2.2: Verificar Dockerfile Está Optimizado

```bash
# Ver contenido del Dockerfile
head -30 agente-hotel-api/Dockerfile

# Debe tener:
# - FROM python:3.12-slim (o versión similar)
# - WORKDIR /app
# - COPY . .
# - RUN pip install -r requirements.txt (o poetry)
# - EXPOSE 8002 (puerto correcto)
# - CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Paso 2.3: Verificar app/main.py Escucha en 0.0.0.0

```bash
# Buscar configuración de host en main.py
grep -n "host\|0.0.0.0\|uvicorn" agente-hotel-api/app/main.py

# Debe mostrar algo como:
# uvicorn.run(app, host="0.0.0.0", port=8002)
# O en FastAPI: app.run(host="0.0.0.0", port=8002)
```

### Paso 2.4: Verificar Variables de Entorno Necesarias

```bash
# Ver .env.fly (archivo ejemplo)
cat .env.fly

# Debe contener (como mínimo):
# ENVIRONMENT=production
# DEBUG=false
# DATABASE_URL=postgresql://...
# REDIS_URL=redis://...
# SECRET_KEY=...
# (otros valores específicos)
```

---

## 🏗️ FASE 3: CONFIGURACIÓN FLY.IO

### Paso 3.1: Crear fly.toml (Configuración Principal)

```bash
# Opción 1: Generar automáticamente (RECOMENDADO)
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO

# Iniciar wizard de Fly
flyctl launch

# Pasos interactivos:
# 1. "App Name": Enter → genera nombre automático (ej: agente-hotel-123)
#    O escribe nombre personalizado: "agente-hotel-prod"
# 2. "Region": Elige región cercana (ej: mex = México, fra = Frankfurt)
# 3. "Database": Pregunta si quieres PostgreSQL - Responde: N (usaremos externo)
# 4. "Redis": Pregunta si quieres Redis - Responde: N (usaremos externo)
# 5. Revisar configuración - Responde: Y

# Resultado: Se creará fly.toml
```

### Paso 3.2: Editar fly.toml (Post-Generación)

```bash
# Abrir fly.toml en VS Code
code fly.toml

# ESTRUCTURA RECOMENDADA:
```

**Contenido optimalizado para fly.toml:**

```toml
# fly.toml file generated for agente-hotel-prod

app = "agente-hotel-prod"
primary_region = "mex"  # O tu región preferida

[build]
  dockerfile = "agente-hotel-api/Dockerfile"
  
[env]
  ENVIRONMENT = "production"
  DEBUG = "false"
  LOG_LEVEL = "info"
  PYTHONUNBUFFERED = "1"

[[services]]
  protocol = "tcp"
  internal_port = 8002
  
  [services.concurrency]
    type = "connections"
    hard_limit = 1000
    soft_limit = 800
  
  [services.tcp_checks]
    enabled = true
    grace_period = "5s"
    interval = "10s"
    timeout = "5s"

[checks]
  [checks.http]
    type = "http"
    interval = "10s"
    timeout = "5s"
    grace_period = "10s"
    method = "get"
    path = "/health/live"
    expected_status_codes = [200]

[[vm]]
  memory = "512mb"
  cpus = 1

[deploy]
  release_command = "alembic upgrade head"  # Si uses migrations
  strategy = "rolling"
```

### Paso 3.3: Verificar fly.toml

```bash
# Validar sintaxis TOML
flyctl config show

# Debe mostrar config sin errores
# Si hay errores, corregir en el editor
```

---

## 🔐 FASE 4: SECRETS & VARIABLES

### Paso 4.1: Preparar Variables de Entorno

```bash
# Crear archivo con todas las variables (TEMPORAL, NO COMMITEAR)
# Este archivo se usará SOLO para setup inicial

cat > /tmp/fly_env_setup.sh << 'EOF'
#!/bin/bash

# VARIABLES PRODUCCIÓN - Reemplaza con tus valores reales
export FLY_APP="agente-hotel-prod"

# Database (Usa servicio externo, ej: Supabase, Railway)
export DATABASE_URL="postgresql://user:pass@host:5432/db_name"

# Redis (Usa servicio externo, ej: Redis Cloud, Upstash)
export REDIS_URL="redis://default:pass@host:6379/0"

# Security
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export API_KEY_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# PMS Configuration
export PMS_TYPE="qloapps"  # O "mock" para testing
export PMS_BASE_URL="https://tu-pms.ejemplo.com"
export PMS_API_KEY="tu_api_key_aqui"

# Application Settings
export ENVIRONMENT="production"
export DEBUG="false"
export LOG_LEVEL="info"
export CORS_ORIGINS="https://tu-dominio.com"

# WhatsApp Integration
export WHATSAPP_BUSINESS_ACCOUNT_ID="tu_account_id"
export WHATSAPP_ACCESS_TOKEN="tu_token"

echo "✅ Variables loaded. Use: source /tmp/fly_env_setup.sh"
EOF

# Hacer ejecutable
chmod +x /tmp/fly_env_setup.sh

# Cargar variables (cuando estés listo)
# source /tmp/fly_env_setup.sh
```

### Paso 4.2: Establecer Secrets en Fly.io

```bash
# IMPORTANTE: Primero carga las variables
source /tmp/fly_env_setup.sh

# Establecer todos los secrets de una vez
flyctl secrets set \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  SECRET_KEY="$SECRET_KEY" \
  API_KEY_SECRET="$API_KEY_SECRET" \
  PMS_TYPE="$PMS_TYPE" \
  PMS_BASE_URL="$PMS_BASE_URL" \
  PMS_API_KEY="$PMS_API_KEY" \
  WHATSAPP_BUSINESS_ACCOUNT_ID="$WHATSAPP_BUSINESS_ACCOUNT_ID" \
  WHATSAPP_ACCESS_TOKEN="$WHATSAPP_ACCESS_TOKEN"

# Verificar que se establecieron
flyctl secrets list
# Debe mostrar todos los secrets (valores ocultos)
```

### Paso 4.3: Establecer Variables No-Secret

```bash
# Estas son variables no sensibles que se pueden mostrar en logs
flyctl config set \
  ENVIRONMENT=production \
  DEBUG=false \
  LOG_LEVEL=info \
  CORS_ORIGINS="https://tu-dominio.com"

# Verificar
flyctl config show
```

---

## 🚀 FASE 5: DEPLOYMENT

### Paso 5.1: Primer Deployment (Build & Deploy)

```bash
# Ir a raíz del proyecto
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO

# Hacer deploy (primero build, luego deploy)
flyctl deploy

# Pasos que hará:
# 1. Detectar Dockerfile
# 2. Build image Docker
# 3. Push a registry Fly.io
# 4. Crear instancia en tu región
# 5. Iniciar contenedor
# 6. Esperar health checks
# 7. Asignar URL

# Tiempo esperado: 5-10 minutos para primer deployment
```

### Paso 5.2: Monitorear Deployment en Vivo

```bash
# En otra terminal, ver logs en vivo
flyctl logs -a agente-hotel-prod

# Verás:
# [info] Starting Gunicorn master process with pid: XX
# [info] Listening at: http://0.0.0.0:8002
# [info] Worker spawned (pid: XX)
# [info] Booted in X.XXs
# [info] Initializing services...
```

### Paso 5.3: Verificar Deployment Exitoso

```bash
# Ver status
flyctl status

# Debe mostrar:
# App: agente-hotel-prod
# Owner: tu-usuario
# Status: running ✓
# Primary Region: mex
# Instances:
#   ID          VERSION  REGION  STATUS  HEALTH CHECKS        RESTARTS  CREATED
#   xxxxx       XX       mex     run     3 total, 3 passing   0         Xs ago

# Ver URL pública
flyctl info

# Debe mostrar:
# Hostname: agente-hotel-prod.fly.dev
# URL: https://agente-hotel-prod.fly.dev
```

---

## ✅ FASE 6: VALIDACIÓN & MONITOREO

### Paso 6.1: Tests de Sanidad

```bash
# Test 1: Health check (liveness)
curl https://agente-hotel-prod.fly.dev/health/live
# Debe retornar: {"status": "ok"} (200)

# Test 2: Readiness check
curl https://agente-hotel-prod.fly.dev/health/ready
# Debe retornar: {"status": "ready", ...} (200)

# Test 3: Metrics endpoint
curl https://agente-hotel-prod.fly.dev/metrics
# Debe mostrar métricas Prometheus
```

### Paso 6.2: Monitoreo en Fly.io Dashboard

```bash
# Abrir dashboard en navegador
flyctl open

# O manualmente:
# https://fly.io/apps/agente-hotel-prod

# Verás:
# - Metrics (CPU, Memory, Network)
# - Logs en vivo
# - Instances status
# - Deployment history
```

### Paso 6.3: Configurar Alertas (Opcional pero Recomendado)

```bash
# Ver opciones de alerting
flyctl help alerts

# Crear alerta para high memory
flyctl alerts add memory \
  --threshold 80 \
  --operator ">" \
  --value 80

# Crear alerta para restarts
flyctl alerts add restarts \
  --threshold 3 \
  --window "1h"
```

### Paso 6.4: Escalar Aplicación (si necesario)

```bash
# Ver instancias actuales
flyctl scale show

# Aumentar a 2 instancias
flyctl scale count 2

# Aumentar memoria (si lo necesitas)
flyctl scale memory 1024  # 1GB

# Ver cambios
flyctl scale show
```

---

## 🔄 DEPLOYMENTS FUTUROS (RÁPIDOS)

Después del primer deploy, los futuros son más rápidos:

```bash
# Deploy incremental (solo cambios)
flyctl deploy --strategy rolling

# Deploy sin rebuild (solo si cambias vars de entorno)
flyctl restart

# Ver historial de deployments
flyctl history

# Rollback si algo falla
flyctl releases rollback
```

---

## 📊 TROUBLESHOOTING COMÚN

### ❌ Error: "Database connection failed"

```bash
# 1. Verificar DATABASE_URL es correcto
flyctl secrets list | grep DATABASE_URL

# 2. Verificar conectividad desde terminal local
psql "$DATABASE_URL" -c "SELECT 1"

# 3. Si está en subnet privado, configurar Network
flyctl network list
```

### ❌ Error: "Health check failed"

```bash
# 1. Ver logs
flyctl logs -a agente-hotel-prod | grep -i health

# 2. Verificar puerto 8002 es correcto en app/main.py
grep "8002" agente-hotel-api/app/main.py

# 3. Aumentar grace period en fly.toml
# grace_period = "30s"  # Aumentar tiempo de startup
```

### ❌ Error: "Out of memory"

```bash
# Aumentar memoria asignada
flyctl scale memory 512

# O en fly.toml:
# [[vm]]
#   memory = "512mb"
#   cpus = 1
```

---

## 📝 CHECKLIST PRE-DEPLOYMENT

Antes de ejecutar cada fase, verifica:

```
PRE-REQUISITOS:
☐ Cuenta Fly.io creada y email verificado
☐ Git status = "clean" (git status muestra nothing to commit)
☐ Docker installado (docker --version)
☐ Sistema healthy (docker ps muestra 7 servicios)

FASE 1 (Fly CLI):
☐ Fly CLI instalado (which flyctl)
☐ Autenticado (flyctl auth whoami muestra usuario)

FASE 2 (Pre-Deploy):
☐ Dockerfile existe en agente-hotel-api/
☐ app/main.py escucha en 0.0.0.0:8002
☐ .env.fly tiene todas variables necesarias

FASE 3 (Configuración):
☐ fly.toml creado y válido (flyctl config show)
☐ fly.toml tiene valores correctos (región, puerto 8002)

FASE 4 (Secrets):
☐ DATABASE_URL correcto y testeado
☐ REDIS_URL correcto y testeado
☐ Secrets establecidos en Fly (flyctl secrets list)

FASE 5 (Deploy):
☐ En raíz del proyecto: cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
☐ Ejecutar: flyctl deploy
☐ Deployment exitoso (0 errors en logs)

FASE 6 (Validación):
☐ Health checks pasan: curl https://APP.fly.dev/health/live
☐ App responde: curl https://APP.fly.dev/metrics
☐ Dashboard muestra instancia "running"
```

---

## 🎯 PRÓXIMOS PASOS (ORDEN RECOMENDADO)

1. **HOY**: Instalar Fly CLI + Autenticar (FASE 1)
2. **HOY**: Verificación pre-deploy (FASE 2)
3. **HOY o MAÑANA**: Crear fly.toml (FASE 3)
4. **ANTES DE DEPLOY**: Preparar secrets (FASE 4)
5. **DEPLOYMENT**: Ejecutar flyctl deploy (FASE 5)
6. **POST-DEPLOY**: Validar + Monitorear (FASE 6)

**Tiempo total estimado**: 30-45 minutos (includes testing)

---

## 📞 RECURSOS ÚTILES

- **Fly.io Docs**: https://fly.io/docs/
- **Fly Python Guide**: https://fly.io/docs/languages-and-frameworks/python/
- **Fly CLI Reference**: https://fly.io/docs/hands-on/
- **Community Support**: https://community.fly.io/

---

**✨ ¿Listo para empezar FASE 1? Ejecuta en terminal:**

```bash
curl -L https://fly.io/install.sh | sh
```

**Estado**: ✅ PLAN READY - WAITING FOR YOUR COMMAND TO PROCEED
