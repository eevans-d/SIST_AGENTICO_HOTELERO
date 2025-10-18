# 🔑 SECRETS QUE NECESITAS AHORA - Resumen Ejecutivo

**Para Railway Deployment - Hoy mismo**  
**Solo lo ESENCIAL, nada más**

---

## 📌 DATOS QUE DEBES OBTENER (13 ITEMS)

### ✅ PASO 1: Generar Secretos (Tú genera estos)

Abre terminal y ejecuta estos comandos:

#### 1️⃣ JWT_SECRET
```bash
openssl rand -base64 32
```
**Salida ejemplo**: `8kR2pL9qM4xN3vJ7cB6dF5eH1wG8iT9sA0pZ2xL=`  
**Copiar en**: `JWT_SECRET`

---

#### 2️⃣ JWT_REFRESH_SECRET (Opcional pero recomendado)
```bash
openssl rand -base64 32
```
**Salida ejemplo**: `xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ=`  
**Copiar en**: `JWT_REFRESH_SECRET`

---

#### 3️⃣ ENCRYPTION_KEY (Opcional pero recomendado)
```bash
openssl rand -base64 32
```
**Salida ejemplo**: `bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i=`  
**Copiar en**: `ENCRYPTION_KEY`

---

### ✅ PASO 2: Valores FIJOS (Solo copiar, no cambiar)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| **JWT_ALGORITHM** | `HS256` | Algoritmo para firmar JWT |
| **JWT_ACCESS_TOKEN_EXPIRE_MINUTES** | `60` | Duración token acceso |
| **ENVIRONMENT** | `production` | Modo producción |
| **DEBUG** | `false` | Sin debug (seguro) |
| **LOG_LEVEL** | `INFO` | Normal logging |
| **RATE_LIMIT_ENABLED** | `true` | Protección contra abuso |
| **RATE_LIMIT_MAX_REQUESTS** | `120` | Máximo 120 requests |
| **RATE_LIMIT_WINDOW_SECONDS** | `60` | Por minuto |
| **PMS_TYPE** | `mock` | Simulado (no real aún) |
| **PMS_BASE_URL** | `http://localhost:8080` | Servidor PMS |
| **PMS_TIMEOUT** | `30` | Timeout 30 segundos |

---

### ✅ PASO 3: Railway AUTO-PROPORCIONA (No hagas nada)

| Variable | Dónde obtener |
|----------|---------------|
| **DATABASE_URL** | Railway → PostgreSQL → Variables |
| **PORT** | Railway inyecta automáticamente |
| **POSTGRES_PASSWORD** | Railway genera automáticamente |

---

## 🎯 RESUMEN TOTAL

### TIENES QUE GENERAR (3 comandos openssl)
```bash
openssl rand -base64 32  # JWT_SECRET
openssl rand -base64 32  # JWT_REFRESH_SECRET
openssl rand -base64 32  # ENCRYPTION_KEY
```

### TIENES QUE COPIAR (11 valores fijos)
```
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
```

### RAILWAY PROPORCIONA (3 valores automáticos)
```
DATABASE_URL = ${{ POSTGRES.DATABASE_URL }}
PORT = (inyectado)
POSTGRES_PASSWORD = (auto-generado)
```

---

## 📊 TABLA RÁPIDA

| Secret | Fuente | Valor/Acción |
|--------|--------|--------------|
| 1. JWT_SECRET | TÚ | `openssl rand -base64 32` |
| 2. JWT_REFRESH_SECRET | TÚ | `openssl rand -base64 32` |
| 3. ENCRYPTION_KEY | TÚ | `openssl rand -base64 32` |
| 4. JWT_ALGORITHM | FIJO | `HS256` |
| 5. JWT_ACCESS_TOKEN_EXPIRE_MINUTES | FIJO | `60` |
| 6. ENVIRONMENT | FIJO | `production` |
| 7. DEBUG | FIJO | `false` |
| 8. LOG_LEVEL | FIJO | `INFO` |
| 9. RATE_LIMIT_ENABLED | FIJO | `true` |
| 10. RATE_LIMIT_MAX_REQUESTS | FIJO | `120` |
| 11. RATE_LIMIT_WINDOW_SECONDS | FIJO | `60` |
| 12. PMS_TYPE | FIJO | `mock` |
| 13. PMS_BASE_URL | FIJO | `http://localhost:8080` |
| 14. PMS_TIMEOUT | FIJO | `30` |
| 15. DATABASE_URL | RAILWAY | `${{ POSTGRES.DATABASE_URL }}` |

---

## 🚀 PASO A PASO PARA CONFIGURAR EN RAILWAY

### 1. Generar los 3 secretos (5 minutos)
```bash
# En tu terminal, ejecutar:
openssl rand -base64 32  # Copiar
openssl rand -base64 32  # Copiar
openssl rand -base64 32  # Copiar
```

### 2. Ir a Railway Dashboard (1 minuto)
https://railway.app/dashboard → Tu Proyecto → agente-hotel-api

### 3. Click en Tab "Variables" (30 segundos)

### 4. Click en "Raw Editor" (30 segundos)

### 5. Pegar toda esta configuración:
```
JWT_SECRET=COLOCA_AQUI_PRIMER_OPENSSL
JWT_REFRESH_SECRET=COLOCA_AQUI_SEGUNDO_OPENSSL
ENCRYPTION_KEY=COLOCA_AQUI_TERCER_OPENSSL
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

### 6. Click en "Save" (30 segundos)

### 7. Deploy automático (Railway hace esto solo)

### ✅ LISTO - API funcionando en 10 minutos

---

## 🔐 SEGURIDAD - NO OLVIDES

✅ **GUARDAR los 3 secrets generados**:
- Copiar en un password manager
- NO perder (son únicos)
- NO commitear a git

✅ **Cambiar después (Fase 2)**:
- Si necesitas WhatsApp
- Si necesitas Gmail
- Si necesitas QloApps real

---

## 📝 EJEMPLO REAL

Si ejecutas los openssl commands, obtendrás algo así:

```bash
$ openssl rand -base64 32
aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB=

$ openssl rand -base64 32
xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ3aB=

$ openssl rand -base64 32
bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i3jK=
```

Entonces configurarías:
```
JWT_SECRET=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB=
JWT_REFRESH_SECRET=xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ3aB=
ENCRYPTION_KEY=bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i3jK=
(... resto igual)
```

---

## ✅ CHECKLIST RÁPIDO

- [ ] Ejecutar 3 comandos `openssl rand -base64 32`
- [ ] Copiar los 3 valores generados
- [ ] Ir a Railway Dashboard
- [ ] Entrar a Variables del servicio agente-hotel-api
- [ ] Pegar la configuración en Raw Editor
- [ ] Guardar
- [ ] Esperar deploy automático (~5 min)
- [ ] Verificar: `curl https://tu-proyecto.up.railway.app/health/live`

---

## ✅ PARA DESPUÉS (NO AHORA)

Si en el futuro necesitas:

**WhatsApp**:
- Crear app en Meta Developer
- Obtener ACCESS_TOKEN y PHONE_NUMBER_ID
- Cambiar WHATSAPP_ENABLED=true

**Gmail**:
- Crear App Password en Google
- Obtener credenciales
- Cambiar GMAIL_ENABLED=true

**QloApps Real**:
- Instalar/Configurar QloApps
- Obtener API_KEY
- Cambiar PMS_TYPE=qloapps

---

**Total tiempo ahora**: ~15 minutos  
**Complejidad**: 🟢 MUY SIMPLE

¡Eso es TODO lo que necesitas para hoy! 🚀
