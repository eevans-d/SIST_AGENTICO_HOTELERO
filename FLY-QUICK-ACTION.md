# 🚀 FLY.IO - QUICK ACTION (20 minutos)

**Rápido, simple, directo. De cero a producción en 20 minutos.**

---

## ✅ ACCIÓN 1: PREPARACIÓN (5 minutos)

### Paso 1: Instalar flyctl (si no tienes)

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
choco install flyctl
```

Verificar:
```bash
flyctl version
```

---

### Paso 2: Generar secretos

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
./scripts/setup-fly-now.sh
```

**Output**: 3 valores copiados en pantalla

```
JWT_SECRET=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB=
JWT_REFRESH_SECRET=xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ=
ENCRYPTION_KEY=bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i=
```

✅ Copia estos 3 valores

---

## ✅ ACCIÓN 2: LOGIN & LAUNCH (10 minutos)

### Paso 1: Login en Fly.io

```bash
flyctl auth login
```

**Qué pasa**: Se abre navegador, completa login

---

### Paso 2: Lanzar app

```bash
flyctl launch
```

**Preguntas del script**:

```
? App Name  →  agente-hotel-api
? Region  →  mia (o elige cercana a ti)
? Do you want to set up a Postgresql database?  →  yes
? Create admin user now?  →  yes
```

**Output**:
- App creada
- fly.toml actualizado
- Espera ~2 minutos

---

### Paso 3: Crear PostgreSQL

```bash
flyctl postgres create
```

**Preguntas**:
```
? App Name  →  agente-hotel-api-db
? Region  →  mia
? Volume size  →  10 (GB)
? Enable HA?  →  no (para dev/staging)
```

**Output**:
- PostgreSQL creado
- Espera ~2 minutos

---

### Paso 4: Attachar database

```bash
flyctl postgres attach --app agente-hotel-api
```

**Output**:
- DATABASE_URL inyectada automáticamente
- Listo!

---

## ✅ ACCIÓN 3: CONFIGURAR SECRETS (2 minutos)

```bash
# Reemplaza CON LOS VALORES QUE GENERASTE EN ACCIÓN 1

flyctl secrets set JWT_SECRET=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB=
flyctl secrets set JWT_REFRESH_SECRET=xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ=
flyctl secrets set ENCRYPTION_KEY=bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i=
```

**Verificar**:
```bash
flyctl secrets list
```

✅ Deberías ver 3 secrets listados

---

## ✅ ACCIÓN 4: DEPLOY (5 minutos)

```bash
flyctl deploy
```

**Qué pasa**:
1. Build image (2-3 min)
2. Push a Fly.io (1 min)
3. Deploy & start (1 min)
4. Health check automático

**Ver progreso**:
```bash
flyctl logs
```

---

## ✅ ACCIÓN 5: VERIFICACIÓN (1 minuto)

### Verificar status

```bash
flyctl status
```

**Expected output**:
```
app: agente-hotel-api
      hostname: agente-hotel-api.fly.dev
      deployment: agente-hotel-api RUNNING
```

### Test endpoint

```bash
flyctl open /health/live
```

**Expected**:
```
200 OK
{"status": "ok"}
```

---

## 🎉 ¡LISTO!

Tu app está en:
```
https://agente-hotel-api.fly.dev
```

---

## 📋 COMANDOS ÚTILES

```bash
# Ver logs
flyctl logs

# Ver status
flyctl status

# Abrir en navegador
flyctl open

# Abrir ruta específica
flyctl open /health/live

# Escalar (más instancias)
flyctl scale count=2

# Ver secrets
flyctl secrets list

# SSH a instancia
flyctl ssh console

# Redeploy
flyctl deploy --strategy=rolling

# Rollback
flyctl releases
flyctl releases rollback
```

---

## 🆘 SI ALGO FALLA

| Problema | Solución |
|----------|----------|
| **flyctl: command not found** | Instala flyctl (ver Acción 1, Paso 1) |
| **App already exists** | Usa nombre diferente en `flyctl launch` |
| **Database attach fails** | Espera 30s y reintenta |
| **Build timeout** | Redeploya: `flyctl deploy` |
| **Health check fails** | Ver logs: `flyctl logs` |

---

## 📚 ¿NECESITAS MÁS DETALLE?

- `ANALISIS-RAILWAY-VS-FLYIO.md` - Entender Fly.io
- `FLY-SETUP-GUIDE.md` - Setup paso a paso
- `FLY-DEPLOY-GUIDE.md` - Deployment detallado
- `FLY-SECRETS-GUIDE.md` - Secrets explicado
- `FLY-TROUBLESHOOTING.md` - Problemas y soluciones

---

**Tiempo total**: ~20 minutos ✅

**¡Tu app está en producción!** 🚀
