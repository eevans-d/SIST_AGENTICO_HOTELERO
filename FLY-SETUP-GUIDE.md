# 📋 FLY.IO SETUP GUIDE - Paso a Paso

**Guía completa de instalación, desde cero hasta listo para deployer**

---

## REQUISITO: Instalar flyctl CLI

### Opción 1: macOS (Homebrew)
```bash
brew install flyctl
flyctl version
```

### Opción 2: Linux (Universal installer)
```bash
curl -L https://fly.io/install.sh | sh
flyctl version
```

### Opción 3: Windows (Chocolatey)
```bash
choco install flyctl
flyctl version
```

### Opción 4: Manual (todas las plataformas)
Descargar desde: https://github.com/superfly/flyctl/releases

---

## PASO 1: Crear cuenta Fly.io

### Opción A: Via CLI (recomendado)
```bash
flyctl auth signup
```

**Qué pasa**:
- Se abre navegador
- Creas cuenta (email + contraseña)
- Regresas a terminal logueado

### Opción B: Via Web
Ir a: https://fly.io
Click "Sign Up"

---

## PASO 2: Login en Fly.io

```bash
flyctl auth login
```

**Verificar login**:
```bash
flyctl whoami
# Output: tu-email@example.com
```

---

## PASO 3: Preparar proyecto

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO

# Generar secrets
./scripts/setup-fly-now.sh

# Output:
# ✓ JWT_SECRET=...
# ✓ JWT_REFRESH_SECRET=...
# ✓ ENCRYPTION_KEY=...
```

---

## PASO 4: Lanzar app en Fly.io

### Comando
```bash
flyctl launch
```

### Responder preguntas
```
? App Name                    →  agente-hotel-api
? Region                      →  mia (Miami, América Latina cercano)
                                 (opciones: sfo, cdg, sin, syd, etc)
? Do you want to set up a Postgresql database?  →  yes
? PostgreSQL: Select plan    →  development (gratis para dev)
? Create admin user now?     →  yes
```

### Output
```
Created app agente-hotel-api
Wrote config to /root/fly.toml
```

---

## PASO 5: Crear PostgreSQL Managed

### Comando
```bash
flyctl postgres create
```

### Responder preguntas
```
? App Name                   →  agente-hotel-api-db
? Region                     →  mia (misma que app)
? Volume size (GB)          →  10 (suficiente para desarrollo)
? Enable HA?                →  no (no necesario ahora)
? Superuser password        →  (genera automático)
```

### Output
```
? Would you like to deploy postgres-staging?  →  yes
```

**Esperar**: ~3-5 minutos

---

## PASO 6: Attachar PostgreSQL

```bash
flyctl postgres attach --app agente-hotel-api
```

**Qué pasa**:
- Crea usuario automáticamente
- Inyecta DATABASE_URL en la app
- Todo configurado!

**Verificar**:
```bash
flyctl config show
# Deberías ver DATABASE_URL en [env]
```

---

## PASO 7: Configurar Secrets

```bash
# Copiar los 3 valores que generaste en PASO 3

flyctl secrets set JWT_SECRET="aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB="
flyctl secrets set JWT_REFRESH_SECRET="xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ="
flyctl secrets set ENCRYPTION_KEY="bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i="
```

**Verificar**:
```bash
flyctl secrets list

# Output:
NAME                    DIGEST                          DATE
JWT_SECRET              8a3f...                         2 seconds ago
JWT_REFRESH_SECRET      b4e2...                         1 second ago
ENCRYPTION_KEY          c5f1...                         Just now
```

---

## ✅ LISTO PARA DEPLOYER

Tu app está configurada y lista para:
```bash
flyctl deploy
```

---

## RESUMEN COMANDOS SETUP

```bash
# 1. Install flyctl (one-time)
brew install flyctl  # or apt-get / choco

# 2. Create account & login
flyctl auth signup   # or flyctl auth login

# 3. Generate secrets
./scripts/setup-fly-now.sh

# 4. Launch app
flyctl launch

# 5. Create PostgreSQL
flyctl postgres create

# 6. Attach database
flyctl postgres attach --app agente-hotel-api

# 7. Set secrets
flyctl secrets set JWT_SECRET="..."
flyctl secrets set JWT_REFRESH_SECRET="..."
flyctl secrets set ENCRYPTION_KEY="..."

# 8. Deploy (en documento FLY-DEPLOY-GUIDE.md)
flyctl deploy
```

---

## 🆘 PROBLEMAS EN SETUP

### ❌ "flyctl: command not found"
Instala flyctl (ver arriba según tu SO)

### ❌ "App agente-hotel-api already exists"
Usa nombre diferente:
```bash
flyctl launch --name agente-hotel-api-prod
```

### ❌ "Authentication failed"
Login nuevamente:
```bash
flyctl auth logout
flyctl auth login
```

### ❌ "No regions available"
Espera unos minutos, puede haber problema temporal

### ❌ "PostgreSQL attach failed"
Espera 30 segundos y reintenta:
```bash
flyctl postgres attach --app agente-hotel-api
```

---

## ✨ PRÓXIMO PASO

Ir a: [`FLY-DEPLOY-GUIDE.md`](./FLY-DEPLOY-GUIDE.md)

---

**Tiempo total**: ~25 minutos  
**Status**: Setup completado, listo para deploy
