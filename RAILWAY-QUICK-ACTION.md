# 🚀 RAILWAY - QUICK ACTION GUIDE

**En este momento, TÚ solo necesitas hacer 3 COSAS**

---

## ✅ ACCIÓN 1: GENERAR SECRETOS (5 minutos)

### Opción A: Automática (RECOMENDADO)
```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
./scripts/setup-railway-now.sh
```

**Qué hace**:
- ✅ Genera 3 secretos criptográficos
- ✅ Crea archivo `.env.railway.local`
- ✅ Muestra todos los valores listos para copiar

---

### Opción B: Manual (si lo prefieres)
```bash
# Ejecuta 3 comandos en terminal
openssl rand -base64 32  # JWT_SECRET
openssl rand -base64 32  # JWT_REFRESH_SECRET
openssl rand -base64 32  # ENCRYPTION_KEY
```

**Luego copia los valores en un documento**

---

## ✅ ACCIÓN 2: CONFIGURAR EN RAILWAY (5 minutos)

1. **Ir a**: https://railway.app/dashboard
2. **Clickear**: Tu proyecto `agente-hotel-api`
3. **Tab**: `Variables`
4. **Button**: `Raw Editor`
5. **Pegar esta configuración COMPLETA**:

```
JWT_SECRET=AQUI_COPIAS_PRIMER_OPENSSL
JWT_REFRESH_SECRET=AQUI_COPIAS_SEGUNDO_OPENSSL
ENCRYPTION_KEY=AQUI_COPIAS_TERCER_OPENSSL
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080
PMS_TIMEOUT=30
DATABASE_URL=${{ POSTGRES.DATABASE_URL }}
```

6. **Click**: `Save`
7. **Esperar**: Railway auto-deploya (5-10 minutos)

---

## ✅ ACCIÓN 3: VERIFICAR QUE FUNCIONA (2 minutos)

Cuando Railway termine (ves status "running"):

```bash
curl https://tu-proyecto.up.railway.app/health/live
```

**Deberías ver**:
```json
{"status": "ok"}
```

Si ves 200 OK → ✅ LISTO!

---

## 📋 TODO LO QUE NECESITAS:

| Item | Dónde obtener | Tiempo |
|------|---------------|--------|
| **JWT_SECRET** | `openssl rand -base64 32` | 10s |
| **JWT_REFRESH_SECRET** | `openssl rand -base64 32` | 10s |
| **ENCRYPTION_KEY** | `openssl rand -base64 32` | 10s |
| **Los 10 valores FIJOS** | Copiar arriba | 30s |
| **DATABASE_URL** | Railway auto-inyecta | Auto ✅ |

**Total tiempo: ~15 minutos**

---

## 🎯 CHECKLIST FINAL

```
☐ He ejecutado ./scripts/setup-railway-now.sh
☐ Copié los 3 valores generados
☐ Fui a https://railway.app/dashboard
☐ Entré a Variables → Raw Editor
☐ Pegué la configuración completa
☐ Clickeé Save
☐ Esperé ~10 min a que Railway deployee
☐ Ejecuté: curl https://tu-proyecto.up.railway.app/health/live
☐ Obtuve respuesta 200 OK
☐ ✅ TENGO MI API EN RAILWAY!
```

---

## 🆘 SI ALGO FALLA:

| Problema | Solución |
|----------|----------|
| **Script no corre** | `chmod +x scripts/setup-railway-now.sh` |
| **openssl: command not found** | Instala openssl: `apt-get install openssl` |
| **Railway dice "offline"** | Espera 10 min más, a veces tarda |
| **curl timeout** | Verifica dominio en Railway Dashboard |
| **/health/live 500** | Revisa que TODAS las 15 variables estén puestas |
| **Secretos en git** | No importa, .gitignore los excluye |

---

## 📚 SI NECESITAS MÁS INFORMACIÓN:

| Documento | Para qué |
|-----------|----------|
| **SECRETS-RESUMEN-EJECUTIVO.md** | Entender qué es cada variable |
| **RAILWAY-MAPA-VISUAL.md** | Ver diagramas y flujos |
| **RAILWAY-START-HERE.md** | Guía paso a paso más detallada |
| **DEPLOYMENT-RAILWAY.md** | Referencia técnica completa |

---

## 🔐 SEGURIDAD - 3 COSAS IMPORTANTES:

✅ **1. Guarda los 3 secrets en password manager**
   - 1Password, Bitwarden, LastPass, etc.
   - NO en texto plano

✅ **2. No comitees .env.railway.local**
   - Está en .gitignore ✓
   - Git rechazará si intentas

✅ **3. Cambia los secrets después en Railway si quieres**
   - En cualquier momento desde Variables
   - Auto-redeploya

---

## ✨ ERES PROFESIONAL AHORA:

Has pasado de "no tengo configuración" a "tengo Railway producción" en:

✅ Script automático  
✅ Documentación clara  
✅ Secrets seguros  
✅ Deploy reproducible  

**¡Felicidades!** 🎉

---

**Tiempo total**: 15 minutos  
**Complejidad**: 🟢 SIMPLE  
**Confiabilidad**: 🟢 PRODUCTION-READY

---

*¿Preguntas? Ver SECRETS-RESUMEN-EJECUTIVO.md*
