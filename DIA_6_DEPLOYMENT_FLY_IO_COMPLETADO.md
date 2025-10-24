# 🏨 AGENTE HOTELERO IA - DEPLOYMENT FLY.IO COMPLETADO

**Fecha de Creación**: October 24, 2025  
**Última Actualización**: October 24, 2025  
**Estado**: ✅ EN PRODUCCIÓN - São Paulo, Brasil  
**URL**: https://agente-hotel-api.fly.dev

---

## 📋 TABLA DE CONTENIDOS

1. [Estado Actual](#estado-actual)
2. [Información de Deployment](#información-de-deployment)
3. [Secrets Configurados](#secrets-configurados)
4. [Acceso a la Aplicación](#acceso-a-la-aplicación)
5. [Monitoreo y Logs](#monitoreo-y-logs)
6. [Comandos Principales](#comandos-principales)
7. [Próximos Pasos](#próximos-pasos)
8. [Solución de Problemas](#solución-de-problemas)
9. [Información Importante](#información-importante)

---

## 🟢 ESTADO ACTUAL

### ✅ Deployment Exitoso
- **Región**: São Paulo, Brasil (gru)
- **Estado**: RUNNING
- **Máquinas**: 2 (alta disponibilidad)
- **Imagen Docker**: agente-hotel-api:deployment-01K8AEGVPVEGGZ37VGK99HFD85
- **Tamaño**: 2.4 GB
- **Health Check**: ✅ PASANDO

### 📊 Configuración
- **Puerto Interno**: 8000
- **Protocolo**: HTTPS (force_https = true)
- **Auto-stop**: Si (cuando está inactiva)
- **Auto-start**: Sí (cuando recibe solicitudes)
- **Modo**: shared-cpu-1x, 1GB RAM

### 🌐 IPs Asignadas
- **IPv4 Compartido**: 66.241.124.44
- **IPv6 Dedicado**: 2a09:8280:1::a9:2798:0
- **Hostname**: agente-hotel-api.fly.dev

---

## 📦 INFORMACIÓN DE DEPLOYMENT

### Tecnología
- **Framework**: FastAPI (Python 3.12)
- **ORM**: SQLAlchemy 2.0+ async
- **Base de Datos**: PostgreSQL (local testing)
- **Cache**: Redis (local testing)
- **Contenedor**: Docker (optimizado para producción)
- **Orquestación**: Fly.io (2 máquinas con rolling deployment)

### Dockerfile
```dockerfile
# Ubicación: /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/Dockerfile
# Multi-stage build simplificado
# Base: Python 3.12-slim
# Expone puerto 8000
# Usuario: appuser (no-root)
```

### fly.toml
```toml
# Ubicación: /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/fly.toml
app = 'agente-hotel-api'
primary_region = 'gru'
dockerfile = 'Dockerfile'
internal_port = 8000
force_https = true
```

---

## 🔐 SECRETS CONFIGURADOS

Todos los secrets se encuentran en **Fly.io** (no en el código):

| Secret | Status | Propósito |
|--------|--------|-----------|
| `SECRET_KEY` | ✅ Configurado | Generado automáticamente (32 caracteres) |
| `JWT_SECRET_KEY` | ✅ Configurado | Para tokens JWT |
| `API_KEY_SECRET` | ✅ Configurado | Para autenticación de API |
| `WHATSAPP_VERIFY_TOKEN` | ✅ Configurado | Webhook verification de WhatsApp |
| `DATABASE_URL` | ✅ Configurado | PostgreSQL: `postgresql://postgres:postgres@localhost:5432/agente_hotel` |
| `REDIS_URL` | ✅ Configurado | Redis: `redis://localhost:6379/0` |

**Nota**: Los DATABASE_URL y REDIS_URL actuales son para testing local. Para producción, usar:
- **PostgreSQL Externo**: Railway, Vercel Postgres, Render, etc.
- **Redis Externo**: Upstash, Redis Cloud, etc.

---

## 🌐 ACCESO A LA APLICACIÓN

### URL Principal
```
https://agente-hotel-api.fly.dev
```

### Endpoints Disponibles

#### Health Checks
```bash
# Liveness (¿está viva?)
curl https://agente-hotel-api.fly.dev/health/live

# Readiness (¿está lista para recibir tráfico?)
curl https://agente-hotel-api.fly.dev/health/ready

# Response esperado:
{"alive": true, "timestamp": "2025-10-24T..."}
```

#### Métricas
```bash
# Prometheus metrics
curl https://agente-hotel-api.fly.dev/metrics
```

#### API Endpoints
```bash
# Ver documentación interactiva (Swagger UI)
https://agente-hotel-api.fly.dev/docs

# Ver esquema OpenAPI
https://agente-hotel-api.fly.dev/openapi.json
```

---

## 📊 MONITOREO Y LOGS

### Ver Logs en Tiempo Real
```bash
flyctl logs -f
```

### Ver Últimos Logs (sin seguimiento)
```bash
flyctl logs -n
```

### Ver Estado de la App
```bash
flyctl status
```

### Abrir Dashboard en Navegador
```bash
flyctl dashboard
```

### Dashboard URL Directo
```
https://fly.io/apps/agente-hotel-api
```

---

## 🎮 COMANDOS PRINCIPALES

### Deployment
```bash
# Ver status actual
flyctl status

# Hacer nuevo deployment
flyctl deploy

# Deploy sin esperar (detach)
flyctl deploy --detach

# Ver historial de releases
flyctl releases list

# Hacer rollback a versión anterior
flyctl releases rollback

# Deshacer último rollback
flyctl releases rollback --force
```

### Secrets
```bash
# Listar todos los secrets
flyctl secrets list

# Agregar/actualizar un secret
flyctl secrets set KEY=VALUE

# Eliminar un secret
flyctl secrets unset KEY

# Mostrar valor de un secret (NO RECOMENDADO)
flyctl secrets show KEY
```

### Logs y Monitoreo
```bash
# Logs en vivo (CTRL+C para salir)
flyctl logs -f

# Últimos N logs
flyctl logs -n

# Logs de máquina específica
flyctl logs --machine <MACHINE_ID>
```

### Máquinas
```bash
# Ver todas las máquinas
flyctl machines list

# Conectar por SSH
flyctl ssh console

# Ejecutar comando en máquina
flyctl ssh console -C "command here"

# Reiniciar máquina
flyctl machines restart <MACHINE_ID>
```

### Escalado
```bash
# Ver configuración actual
flyctl scale show

# Cambiar memoria
flyctl scale memory 2048

# Cambiar cantidad de máquinas
flyctl scale count 3

# Cambiar CPU
flyctl scale vm-cpus 2
```

### App
```bash
# Abrir app en navegador
flyctl open

# Abrir dashboard en navegador
flyctl dashboard

# Restart toda la app
flyctl restart

# Recrear app
flyctl reboot
```

---

## 🚀 PRÓXIMOS PASOS

### Fase 1: INMEDIATA (Esta semana)

#### 1.1 Validar Health Checks
```bash
flyctl status
# Verificar que ambas máquinas muestren "passing"
```

#### 1.2 Pruebas Iniciales
```bash
# Test endpoint de salud
curl https://agente-hotel-api.fly.dev/health/live

# Test métricas
curl https://agente-hotel-api.fly.dev/metrics

# Test documentación
open https://agente-hotel-api.fly.dev/docs
```

#### 1.3 Monitorear Logs (1 hora)
```bash
flyctl logs -f
# Buscar cualquier error o warning
```

---

### Fase 2: CORTO PLAZO (Próximos 3-7 días)

#### 2.1 Bases de Datos Productivas
**Actualmente**: Testing local  
**Objetivo**: Bases de datos externas

**PostgreSQL**:
- Opción A: Railway (railway.app) - Recomendado
- Opción B: Vercel Postgres (vercel.com)
- Opción C: Render (render.com)

**Redis**:
- Opción A: Upstash (upstash.com) - Recomendado
- Opción B: Redis Cloud (redis.com)

**Pasos**:
1. Crear cuenta en proveedor
2. Crear base de datos
3. Copiar connection string
4. Actualizar secrets:
   ```bash
   flyctl secrets set DATABASE_URL="postgresql://..."
   flyctl secrets set REDIS_URL="redis://..."
   ```
5. Hacer nuevo deployment: `flyctl deploy`

#### 2.2 Integración WhatsApp
- [ ] Obtener credentials de Meta
- [ ] Configurar WHATSAPP_ACCESS_TOKEN
- [ ] Configurar WHATSAPP_BUSINESS_ACCOUNT_ID
- [ ] Configurar webhook URL: `https://agente-hotel-api.fly.dev/api/webhooks/whatsapp`
- [ ] Test con número de prueba

#### 2.3 Integración Gmail
- [ ] Si es necesario, configurar GMAIL_CREDENTIALS
- [ ] Test envío de correos

---

### Fase 3: MEDIANO PLAZO (Próximas 2-4 semanas)

#### 3.1 Dominio Personalizado
```bash
# Agregar dominio
flyctl certs add tudominio.com

# Verificar DNS
flyctl certs show tudominio.com
```

#### 3.2 Escalado
- Monitorear uso de CPU/memoria
- Si es necesario: `flyctl scale memory 2048`

#### 3.3 Backups
- Configurar backups automáticos de PostgreSQL
- Documentar procedimiento de recuperación

#### 3.4 CI/CD
- Configurar GitHub Actions para auto-deploy
- Tests automáticos antes de deploy

---

### Fase 4: LARGO PLAZO (Próximo mes)

#### 4.1 Optimizaciones
- A/B testing de configuraciones
- Análisis de logs para mejoras
- Optimización de queries

#### 4.2 Disaster Recovery
- Plan de recuperación ante fallos
- Documentación de procedimientos
- Simulacros

#### 4.3 Seguridad
- Auditoría de código
- Escaneo de vulnerabilidades
- Actualización de dependencias

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Problema: App No Responde

**Verificar status:**
```bash
flyctl status
```

**Ver logs:**
```bash
flyctl logs -f
```

**Común**: Health check tomando tiempo  
**Solución**: Esperar 60-90 segundos, luego reintentar

---

### Problema: Errores en Logs

**Ver detalles:**
```bash
flyctl logs -f | grep ERROR
```

**Cause común**: DATABASE_URL o REDIS_URL inválidos  
**Solución**: Verificar secrets con `flyctl secrets list`

---

### Problema: Secret No se Actualiza

**Solución**:
```bash
# Verificar que está configurado
flyctl secrets list

# Si no aparece, agregarlo
flyctl secrets set KEY=VALUE

# Hacer nuevo deploy para aplicar
flyctl deploy
```

---

### Problema: Health Checks Fallando

**Común**: Puerto incorrecto o app no iniciada  
**Solución**:
```bash
# Conectar por SSH y revisar
flyctl ssh console

# Dentro del contenedor:
curl http://localhost:8000/health/live
```

---

### Problema: Máquina Detenida

**Ver estado:**
```bash
flyctl status
```

**Si muestra "stopped"**:
```bash
# Reiniciar
flyctl machines restart <MACHINE_ID>

# O simplemente hacer deploy
flyctl deploy
```

---

## ℹ️ INFORMACIÓN IMPORTANTE

### Para el Futuro

#### 1. Ubicación Geográfica
- **Región Actual**: São Paulo, Brasil (gru)
- **Razón**: Cercana a Argentina (ubicación del usuario)
- **Ventaja**: Baja latencia para usuarios en Sudamérica
- **Si necesita cambiar**: Editar `fly.toml` → `primary_region = 'otro_codigo'`

#### 2. Costos
- **Máquinas**: $3/mes por shared-cpu-1x con 1GB RAM
- **Current**: 2 máquinas = ~$6/mes
- **Almacenamiento**: Incluido (3GB)
- **Bandwidth**: Primeros 100GB gratuitos/mes

#### 3. Escalado
- **Actual**: 1 vCPU compartido, 1GB RAM
- **Para producción**: Considerar upgrade a shared-cpu-2x o performance

#### 4. Auto-stop/Start
- La app se detiene automáticamente cuando está inactiva
- Se reinicia cuando recibe una solicitud
- Esto **reduce costos** pero **agrega latencia** en primer request

#### 5. Datos Críticos
- **Git Branch**: main
- **GitHub Repo**: SIST_AGENTICO_HOTELERO
- **Org**: eevans-d
- **Email Fly.io**: eevans.d@gmail.com

---

### Archivos Importantes

```
Raíz del proyecto:
├── Dockerfile (para Fly.io) ← IMPORTANTE
├── fly.toml (configuración Fly.io) ← IMPORTANTE
├── requirements-prod.txt (dependencias)
├── pyproject.toml (proyecto Poetry)
├── deploy-fly.sh (script deployment local)
├── setup-fly-secrets.sh (script secrets)
├── FLY_CLI_CHEATSHEET.md (referencia rápida)
└── FLY_IO_DEPLOYMENT_PASO_A_PASO.md (guía paso a paso)

Subcarpeta agente-hotel-api/:
├── Dockerfile.production (original, no se usa)
├── app/ (código de la aplicación)
├── requirements-prod.txt (en subcarpeta)
├── pyproject.toml (en subcarpeta)
└── docker/
```

---

### Cómo Hacerle Cambios

#### Cambio en Código
```bash
# 1. Editar archivo
vim agente-hotel-api/app/main.py

# 2. Commit
git add agente-hotel-api/
git commit -m "Fix: descripción del cambio"

# 3. Push
git push origin main

# 4. Deploy a Fly.io
flyctl deploy

# 5. Verificar
flyctl status
flyctl logs -f
```

#### Cambio en Secrets
```bash
flyctl secrets set NEW_KEY=NEW_VALUE
flyctl deploy
```

#### Cambio en Configuración (fly.toml)
```bash
# Editar fly.toml
vim fly.toml

# Commit
git add fly.toml
git commit -m "Config: cambio en fly.toml"

# Push
git push origin main

# Deploy
flyctl deploy
```

---

### Monitoreo Recomendado

**Diario**:
- [ ] Verificar status: `flyctl status`
- [ ] Revisar logs recientes: `flyctl logs -n`

**Semanal**:
- [ ] Ejecutar health checks
- [ ] Revisar uso de recursos

**Mensual**:
- [ ] Actualizar dependencias
- [ ] Revisar logs para patrones de errores
- [ ] Verificar costos

---

## 📞 COMANDOS DE EMERGENCIA

### Si Todo Falla
```bash
# 1. Ver qué pasó
flyctl status
flyctl logs -f

# 2. Hacer rollback
flyctl releases rollback

# 3. Reiniciar todo
flyctl machines restart --signal=SIGKILL

# 4. Último recurso: recrear
flyctl apps destroy agente-hotel-api -y
# (Perderás todos los datos si usas almacenamiento local)
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

- [x] App deployada en Fly.io
- [x] Región: São Paulo, Brasil (gru)
- [x] 2 máquinas running
- [x] Health checks pasando
- [x] HTTPS habilitado
- [x] 6 secrets configurados
- [x] Dockerfile optimizado
- [x] fly.toml configurado
- [ ] Bases de datos productivas (PRÓXIMO)
- [ ] WhatsApp integrado (PRÓXIMO)
- [ ] Dominio personalizado (PRÓXIMO)

---

## 📚 REFERENCIAS

- **Fly.io Docs**: https://fly.io/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Docker Docs**: https://docs.docker.com
- **GitHub**: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO

---

## 📝 HISTORIAL DE CAMBIOS

| Fecha | Cambio | Estado |
|-------|--------|--------|
| Oct 24, 2025 | Deployment inicial a Fly.io | ✅ Completado |
| Oct 24, 2025 | Configuración de secrets | ✅ Completado |
| Oct 24, 2025 | Documento maestro creado | ✅ Completado |
| Oct XX, 2025 | Bases de datos productivas | ⏳ Próximo |
| Oct XX, 2025 | WhatsApp integrado | ⏳ Próximo |

---

**Documento creado con ❤️ por GitHub Copilot**  
**Última revisión**: October 24, 2025  
**Próxima revisión sugerida**: October 31, 2025
