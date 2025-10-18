# 🗺️ MAPA DE RAILWAY - Visualización Completa

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAILWAY DEPLOYMENT MAP                       │
│                                                                 │
│  Tu Máquina Local          Railway Platform      Mi Base Datos  │
│  ──────────────────        ─────────────────     ──────────────│
│                                                                 │
│  1. Generar Secrets  ──→   2. Dashboard  ──→   3. PostgreSQL 14│
│     (3 openssl)            Variables    ─────  Auto-provisioned│
│     - JWT_SECRET           │            │                      │
│     - JWT_REFRESH          │  Raw Editor│                      │
│     - ENCRYPTION_KEY       │            │                      │
│                            │            │                      │
│  4. Git Push  ──→  5. Build  ──→  6. Run  ──→  7. Health Check│
│     (auto)       (Dockerfile)    (uvicorn)     /health/live    │
│                  - Instala deps               ✅ 200 OK        │
│                  - Copia código                              │
│                  - Build image                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 MAPA DE PROCESOS

```
TIMELINE: 15 MINUTOS TOTALES
═════════════════════════════════════════════════════════════════

TIEMPO    ACCIÓN                                    QUIÉN        ESTADO
────────  ──────────────────────────────────────────────────── ──────
0:00-0:05 Generar 3 secrets con openssl           TÚ          ⏱️
          ./scripts/setup-railway-now.sh
          
0:05-0:10 Ir a Railway Dashboard + pegar config   TÚ          ⏱️
          https://railway.app/dashboard
          → agente-hotel-api → Variables → Raw Editor
          
0:10-0:15 Railway auto-deploya                     RAILWAY     ⏳
          (5 minutos más)
          
0:15      ✅ VERIFICAR: curl /health/live         TÚ          ✅
```

---

## 📊 MAPA DE VARIABLES

```
CATEGORÍA                      FUENTE      N° VARS  ACCIÓN
────────────────────────────   ─────────   ────────  ──────────────
Secrets (Autogenerados)        TÚ          3         openssl rand
├─ JWT_SECRET
├─ JWT_REFRESH_SECRET
└─ ENCRYPTION_KEY

Configuración Fija             VALORES     10        Copiar/pegar
├─ JWT_ALGORITHM = HS256
├─ JWT_ACCESS_TOKEN_EXPIRE = 60
├─ ENVIRONMENT = production
├─ DEBUG = false
├─ LOG_LEVEL = INFO
├─ RATE_LIMIT_ENABLED = true
├─ RATE_LIMIT_MAX_REQUESTS = 120
├─ RATE_LIMIT_WINDOW_SECONDS = 60
├─ PMS_TYPE = mock
├─ PMS_BASE_URL = http://localhost:8080
└─ PMS_TIMEOUT = 30

Auto-Inyectadas por Railway    RAILWAY     2         NO TOCAR
├─ DATABASE_URL = ${{ POSTGRES.DATABASE_URL }}
└─ PORT = ${{ PORT }}

TOTAL VARIABLES INICIALES: 15
```

---

## 🔄 FLUJO DE DATOS

```
┌────────────────────────────────────────────────────────────┐
│ INPUT: TÚ ejecutas ./scripts/setup-railway-now.sh          │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ PROCESO: Script genera .env.railway.local                  │
│          - Crea 3 secrets con openssl                      │
│          - Agrega 10 valores de configuración              │
│          - Archivo formateado para Raw Editor              │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ OUTPUT: 3 valores para guardar en password manager         │
│         + archivo .env.railway.local (local backup)        │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ NEXT: Copiar configuración a Railway Dashboard Raw Editor  │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ RESULT: Railway deployea automáticamente                   │
└────────────────────────────────────────────────────────────┘
```

---

## 📍 UBICACIONES IMPORTANTES

```
TU MÁQUINA LOCAL:
─────────────────
📁 /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/
   ├─ 📄 SECRETS-RESUMEN-EJECUTIVO.md      ← LEE ESTO PRIMERO
   ├─ 📄 RAILWAY-START-HERE.md             ← Guía rápida
   ├─ 📄 DEPLOYMENT-RAILWAY.md             ← Referencia completa
   ├─ 📂 scripts/
   │  └─ 📜 setup-railway-now.sh           ← EJECUTA ESTO
   └─ 📄 .env.railway.local                ← Creado después

RAILWAY DASHBOARD:
──────────────────
🌐 https://railway.app/dashboard
   → Proyectos → agente-hotel-api
      → Tab: Variables
         → Button: Raw Editor
            → Pegar configuración
               → Save

GITHUB:
───────
📦 https://github.com/eevans-d/SIST_AGENTICO_HOTELERO
   ├─ ✅ railway.json                      ← Configuración build
   ├─ ✅ railway.toml                      ← Alternativa
   ├─ ✅ Procfile                          ← Fallback
   ├─ ✅ .env.railway                      ← Template variables
   ├─ ✅ scripts/setup-railway-now.sh      ← Script generator
   ├─ ✅ SECRETS-RESUMEN-EJECUTIVO.md      ← Este documento
   └─ ✅ agente-hotel-api/
      ├─ Dockerfile.production             ← Build instruction
      └─ app/main.py                       ← Aplicación

RAILWAY INFRASTRUCTURE:
───────────────────────
🗄️  PostgreSQL 14
   ├─ Host: auto.railway.app
   ├─ Port: auto.railway.app
   ├─ Database: auto-generated
   └─ DATABASE_URL: auto-injected

💻 Container agente-hotel-api
   ├─ Base image: python:3.12-slim
   ├─ Port: $PORT (auto)
   ├─ Health: GET /health/live
   └─ Domain: tu-proyecto.up.railway.app
```

---

## ✅ CHECKLIST DE VALIDACIÓN

### ANTES DE EJECUTAR SCRIPT
```
☐ Estoy en el directorio: /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
☐ Tengo acceso a terminal con openssl
☐ Cuota de almacenamiento disponible (< 1 MB needed)
☐ git está configurado
```

### DESPUÉS DE EJECUTAR SCRIPT
```
☐ Archivo .env.railway.local existe
☐ Archivo tiene permisos 600
☐ Backup creado en .railway-backups/
☐ 3 valores generados copiados en password manager
```

### EN RAILWAY DASHBOARD
```
☐ Proyecto agente-hotel-api visible
☐ PostgreSQL conectado
☐ Tab Variables accesible
☐ Raw Editor abierto
☐ Configuración pegada sin errores
☐ Click Save ejecutado
☐ Deploy iniciado (ver logs)
```

### POST-DEPLOY
```
☐ Build completado (~5 min)
☐ Servicio agente-hotel-api en estado "running"
☐ Acceder a: https://tu-proyecto.up.railway.app/health/live
☐ Respuesta: 200 OK + JSON
```

---

## 🎓 MAPEO DE ARCHIVOS A DOCUMENTOS

```
┌─ ¿QUÉ NECESITO AHORA?
│  └─→ 📄 SECRETS-RESUMEN-EJECUTIVO.md (ESTE ARCHIVO)
│      └─→ Ejecutar: ./scripts/setup-railway-now.sh
│
├─ ¿CÓMO LO HAGO EN 45 MINUTOS?
│  └─→ 📄 RAILWAY-START-HERE.md
│      └─→ Paso a paso visual
│
├─ ¿QUIERO TODA LA INFORMACIÓN?
│  └─→ 📄 DEPLOYMENT-RAILWAY.md
│      └─→ 700+ líneas de referencia completa
│
├─ ¿NECESITO NAVEGAR DOCUMENTOS?
│  └─→ 📄 RAILWAY-DOCUMENTATION-INDEX.md
│      └─→ Índice de navegación con casos de uso
│
├─ ¿QUIERO VER EL CONTEXTO HISTÓRICO?
│  └─→ 📄 RESUMEN-RAILWAY-DAY.md
│      └─→ Historia completa del trabajo realizado
│
└─ ¿NECESITO UN CHECKLIST INTERACTIVO?
   └─→ 📄 RAILWAY-DEPLOYMENT-CHECKLIST.md
       └─→ Checklist paso a paso con tiempos
```

---

## 🔐 SEGURIDAD - MAPA

```
┌──────────────────────────────────────────┐
│ DONDE VAN TUS SECRETOS                   │
├──────────────────────────────────────────┤
│                                          │
│  1. Generados aquí (máquina local)       │
│     └─→ ./scripts/setup-railway-now.sh   │
│                                          │
│  2. Guardados aquí (tu password manager) │
│     └─→ 1Password/Bitwarden/etc          │
│                                          │
│  3. Inyectados aquí (Railway Dashboard)  │
│     └─→ Variables → Raw Editor           │
│                                          │
│  4. NUNCA commiteados a git             │
│     └─→ .gitignore contiene .env.*       │
│                                          │
│  5. Nunca en logs públicos               │
│     └─→ Python logging auto-oculta       │
│                                          │
└──────────────────────────────────────────┘
```

---

## 📱 MAPA PARA MOBILE (si necesitas referencia rápida)

### TIENES QUE HACER (3 LÍNEAS):
```
1. ./scripts/setup-railway-now.sh
2. Railway Dashboard → Variables → Raw Editor → pegar
3. Save
```

### TIEMPO TOTAL:
```
Generación: 5 min
Configuración: 5 min
Deploy: 5 min
─────────────
Total: 15 min
```

### RESULTADO ESPERADO:
```
✅ GET /health/live → 200 OK
✅ API funcionando en Railway
✅ PostgreSQL 14 auto-provisioned
✅ Dominio público asignado
```

---

## 🚨 MAPA DE ERRORES COMUNES

```
PROBLEMA                    CAUSA                   SOLUCIÓN
─────────────────────────   ──────────────────────  ──────────────────
Script no ejecuta           No tiene permisos +x    chmod +x scripts/setup-railway-now.sh
                                                    
openssl: command not found  openssl no instalado    apt-get install openssl

Database connection fails   DATABASE_URL no set     Revisar Railway PostgreSQL conectado
                                                    
/health/live 500 error      Secrets incompletos     Revisar todas 15 variables puestas
                                                    
Port en conflicto           Port ya usado            Railway inyecta PORT, no usar hardcode
                                                    
Secrets commitados a git    .gitignore incompleto   .gitignore incluye .env.* y .env.*

API timeout                 PMS_BASE_URL invalido   PMS_TYPE=mock en producción inicial
```

---

## 🎯 RESUMEN VISUAL

```
╔═══════════════════════════════════════════════════════════════╗
║              YOUR RAILWAY JOURNEY (15 MINUTES)                ║
╚═══════════════════════════════════════════════════════════════╝

PASO 1: GENERAR                (5 min)
┌──────────────────────────────────────────────────────────┐
│ Tu Máquina                                               │
│                                                          │
│ $ ./scripts/setup-railway-now.sh                         │
│                                                          │
│ Output:                                                  │
│ ✓ JWT_SECRET=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB │
│ ✓ JWT_REFRESH_SECRET=xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW │
│ ✓ ENCRYPTION_KEY=bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH  │
└──────────────────────────────────────────────────────────┘

PASO 2: CONFIGURAR             (5 min)
┌──────────────────────────────────────────────────────────┐
│ Railway Dashboard                                        │
│                                                          │
│ 1. https://railway.app/dashboard                         │
│ 2. agente-hotel-api → Variables                          │
│ 3. Raw Editor                                            │
│ 4. Pegar 15 variables                                    │
│ 5. Save                                                  │
└──────────────────────────────────────────────────────────┘

PASO 3: DEPLOYER               (5 min)
┌──────────────────────────────────────────────────────────┐
│ Railway Automático                                       │
│                                                          │
│ Build: Dockerfile.production                             │
│ Run: uvicorn app.main:app --host 0.0.0.0 --port $PORT  │
│ Result: https://tu-proyecto.up.railway.app              │
│                                                          │
│ ✅ /health/live → 200 OK                                │
└──────────────────────────────────────────────────────────┘
```

---

## 💡 TIPS & TRICKS

```
✅ Si es primera vez en Railway:
   └─ Crear cuenta en https://railway.app
   └─ Crear nuevo proyecto
   └─ Agregar PostgreSQL (click "+ New service")

✅ Si necesitas copiar la config rápido:
   └─ Script crea /tmp/railway-config.txt
   └─ Copiar directamente desde ahí

✅ Si pierdes los secrets:
   └─ Ver en Railway Dashboard → Logs
   └─ NO aparecen por seguridad
   └─ Generar nuevos y poner nuevamente

✅ Si quieres probar localmente primero:
   └─ make dev-setup
   └─ make docker-up
   └─ Mismo .env.railway.local funciona

✅ Si Railways falla con "Port already in use":
   └─ Railway inyecta $PORT automáticamente
   └─ No hardcodear puerto en uvicorn
   └─ Ya está en railway.json (correcto)
```

---

**Última actualización**: 2025-10-17  
**Versión**: 2.0 (Mapa Visual)  
**Objetivo**: Visualización completa de todo el flujo Railway
