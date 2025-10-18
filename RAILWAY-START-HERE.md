# 🚀 RAILWAY DEPLOYMENT - START HERE

**Última actualización**: 2025-10-18  
**Estado**: ✅ Configuración 100% lista  
**Duración**: 45 minutos

---

## 🎯 3 PASOS SIMPLES

### PASO 1: Generar Secretos (5 minutos)

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
./scripts/generate-railway-secrets.sh
```

**Output esperado**:
- Archivo: `.env.railway.local` (con secretos reales)
- Secretos mostrados en pantalla (copiar estos)

**Guardar secretos en**:
- Password manager
- Nota segura
- NO commitear a git (ya excluido)

---

### PASO 2: Crear Proyecto en Railway (20 minutos)

#### Opción A: Web UI (Recomendado)

1. **Ir a Railway**: https://railway.app/dashboard

2. **New Project** → **Deploy from GitHub repo**

3. **Seleccionar**:
   - Repo: `eevans-d/SIST_AGENTICO_HOTELERO`
   - Rama: `main`

4. **Railway detecta automáticamente**:
   - Builder: DOCKERFILE ✅
   - Start command: uvicorn app.main:app... ✅

5. **Agregar PostgreSQL**:
   - Click "+ New" → Database → PostgreSQL
   - Esperar ~2 minutos

6. **Configurar Variables**:
   - Click servicio → Tab "Variables" → "Raw Editor"
   - Pegar desde `.env.railway.local` generado en Paso 1
   - Agregar referencia: `DATABASE_URL = ${{ POSTGRES.DATABASE_URL }}`

7. **Generar Domain**:
   - Settings → Networking → Generate Domain
   - Anotar URL: `https://tu-proyecto.up.railway.app`

8. **Deploy automático**:
   - Railway inicia build (~5-8 min)
   - Ver logs en tiempo real

#### Opción B: CLI (Avanzado)

```bash
# Instalar CLI
npm install -g @railway/cli

# Login
railway login

# Iniciar proyecto
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
railway init

# Agregar PostgreSQL
railway add --database postgres

# Configurar variables
railway variables set --file .env.railway.local

# Deploy
railway up

# Ver logs
railway logs
```

---

### PASO 3: Verificar Deployment (5 minutos)

```bash
# Health check
curl https://tu-proyecto.up.railway.app/health/live

# Respuesta esperada:
# {
#   "status": "ok",
#   "timestamp": "2025-10-18T...",
#   "version": "0.1.0"
# }
```

**En Railway Dashboard**:
- ✅ Status: LIVE (verde)
- ✅ Logs: Sin errores críticos
- ✅ Metrics: CPU < 50%, Memory < 300 MB

---

## 📚 DOCUMENTACIÓN COMPLETA

### Si necesitas más detalles:

1. **Guía Paso a Paso**: `RAILWAY-DEPLOYMENT-CHECKLIST.md`
   - Checklist completo con todos los checks

2. **Guía Completa**: `DEPLOYMENT-RAILWAY.md`
   - 7,500 líneas de documentación técnica
   - Troubleshooting de 7 escenarios

3. **Resumen Ejecutivo**: `RAILWAY-RESUMEN-EJECUTIVO.md`
   - Problema vs Solución
   - Comparativa Staging vs Railway

4. **Resumen del Día**: `RESUMEN-RAILWAY-DAY.md`
   - Todo el trabajo realizado hoy
   - Estadísticas completas

---

## 🐛 PROBLEMAS COMUNES

### Build falla
```bash
# Ver logs
railway logs --deployment <ID>

# Verificar localmente
docker build -f agente-hotel-api/Dockerfile.production .
```

### Health check timeout
```bash
# Verificar endpoint localmente
curl http://localhost:8000/health/live

# Ajustar timeout en railway.json
"healthcheckTimeout": 600
```

### Variables faltantes
```bash
# Listar variables actuales
railway variables

# Verificar DATABASE_URL
railway variables get DATABASE_URL
```

---

## 💰 COSTOS

| Plan | Costo | Servicios | Ideal para |
|------|-------|-----------|------------|
| **Hobby** | Gratis | 2 | Testing (15 días) |
| **Pro** | $5-10/mes | 3 | MVP, Staging |
| **Team** | $20/mes | ∞ | Producción |

---

## ✅ CHECKLIST RÁPIDO

- [ ] Generar secretos (`./scripts/generate-railway-secrets.sh`)
- [ ] Crear proyecto Railway (web UI)
- [ ] Agregar PostgreSQL
- [ ] Configurar variables (de `.env.railway.local`)
- [ ] Generar domain público
- [ ] Esperar build (~5-8 min)
- [ ] Verificar health check

**Duración total**: ~45 minutos

---

## 🎉 ¡LISTO!

Cuando termines:
- URL pública: `https://tu-proyecto.up.railway.app`
- Status: LIVE ✅
- API funcionando 🚀

**Próximo paso**: Monitorear por 24h (ver RAILWAY-DEPLOYMENT-CHECKLIST.md sección "Monitoreo Continuo")

---

**Ayuda rápida**:
- Railway Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app
