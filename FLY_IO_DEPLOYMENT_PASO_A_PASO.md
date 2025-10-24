# 🚀 FLY.IO DEPLOYMENT - GUÍA PASO A PASO

**Fecha**: October 24, 2025  
**Sistema**: Agente Hotelero IA  
**Plataforma**: Fly.io  
**Región**: Miami (mia)  
**Estado**: Listo para deployment

---

## 📋 TABLA DE CONTENIDOS

1. [Paso 1: Autenticarse en Fly.io](#paso-1-autenticarse-en-flyio)
2. [Paso 2: Verificar Autenticación](#paso-2-verificar-autenticación)
3. [Paso 3: Configurar Secrets](#paso-3-configurar-secrets)
4. [Paso 4: Verificar Secrets](#paso-4-verificar-secrets)
5. [Paso 5: Primer Deployment](#paso-5-primer-deployment)
6. [Paso 6: Verificar Deployment](#paso-6-verificar-deployment)
7. [Bases de Datos Gratuitas (Opcional)](#bases-de-datos-gratuitas-opcional)
8. [Comandos de Referencia Rápida](#comandos-de-referencia-rápida)

---

## PASO 1: AUTENTICARSE EN FLY.IO

### 📌 Objetivo
Crear la conexión entre tu terminal y tu cuenta de Fly.io.

### 🎯 Comando Exacto

**Copia y pega esto en tu terminal de VS Code:**

```bash
flyctl auth login
```

### ✅ Qué Va a Pasar

1. Se abrirá automáticamente tu navegador (o mostrará una URL)
2. Se abrirá la página de login de Fly.io
3. Haz login con tu usuario y contraseña
4. Autoriza la aplicación
5. Verás un código de confirmación
6. Vuelve a la terminal
7. Debería aparecer: **"Logged in successfully"**

### ⏱️ Tiempo Estimado
**2-3 minutos**

### 🔴 Si Tienes Problemas

**Si no se abre el navegador automáticamente:**
- Copia la URL que aparezca en la terminal
- Pégala en tu navegador
- Completa el login
- Vuelve a la terminal

---

## PASO 2: VERIFICAR AUTENTICACIÓN

### 📌 Objetivo
Confirmar que estás autenticado correctamente.

### 🎯 Comando Exacto

**Copia y pega esto:**

```bash
flyctl auth whoami
```

### ✅ Resultado Esperado

Debería mostrar tu usuario de Fly.io, por ejemplo:
```
eevan-d
```

### ⏱️ Tiempo Estimado
**5 segundos**

### 🔴 Si No Funciona

Si muestra: `"not logged in"`
- Vuelve al **PASO 1** y completa el login
- O intenta: `flyctl auth logout` y luego `flyctl auth login` de nuevo

---

## PASO 3: CONFIGURAR SECRETS

### 📌 Objetivo
Guardar todas las credenciales y variables sensibles en Fly.io.

### 🎯 Comando Exacto

**Copia y pega esto:**

```bash
./setup-fly-secrets.sh
```

### ⏱️ Tiempo Estimado
**5-10 minutos**

### 📝 Instrucciones Detalladas

El script te hará preguntas. Aquí está exactamente qué responder:

---

### 3.1️⃣ SECRETS GENERADOS AUTOMÁTICAMENTE ✅

**Cuando veas estas preguntas, presiona ENTER (el script las genera automáticamente):**

```
Generating SECRET_KEY...
Setting secret: SECRET_KEY
```
→ **Presiona ENTER**

```
Generating JWT_SECRET_KEY...
Setting secret: JWT_SECRET_KEY
```
→ **Presiona ENTER**

```
Generating API_KEY_SECRET...
Setting secret: API_KEY_SECRET
```
→ **Presiona ENTER**

```
Generating WHATSAPP_VERIFY_TOKEN...
Setting secret: WHATSAPP_VERIFY_TOKEN
Use this token in Meta Dashboard: [TOKEN LARGO]
```
→ **Presiona ENTER** (guarda el token si usas WhatsApp)

---

### 3.2️⃣ SECRETS QUE DEBES PROPORCIONAR ⚠️

#### A) DATABASE_URL (PostgreSQL)

**Pregunta que verás:**
```
Enter DATABASE_URL (PostgreSQL connection string):
Example: postgresql://user:password@host:5432/dbname
DATABASE_URL: _
```

**¿Qué debes escribir?**

**OPCIÓN 1: Testing Local**
```
postgresql://postgres:postgres@localhost:5432/agente_hotel
```

**OPCIÓN 2: Producción (Recomendado)**
Necesitas un servicio externo. Ve a **SECCIÓN 7: Bases de Datos Gratuitas** al final de este documento.

**Ejemplo Real:**
```
postgresql://user123:abc123xyz@db.railway.app:5432/agente_hotel
```

**Después de copiar tu URL, pégala y presiona ENTER**

---

#### B) REDIS_URL

**Pregunta que verás:**
```
Enter REDIS_URL (Redis connection string):
Example: redis://default:password@host:6379/0
REDIS_URL: _
```

**¿Qué debes escribir?**

**OPCIÓN 1: Testing Local**
```
redis://localhost:6379/0
```

**OPCIÓN 2: Producción (Recomendado)**
Necesitas un servicio externo. Ve a **SECCIÓN 7: Bases de Datos Gratuitas** al final de este documento.

**Ejemplo Real:**
```
redis://default:abc123xyz@redis-12345.upstash.io:6379
```

**Después de copiar tu URL, pégala y presiona ENTER**

---

### 3.3️⃣ SECRETS OPCIONALES 🔹

**Para todas estas preguntas, si NO tienes el valor, presiona ENTER sin escribir nada:**

```
Enter PMS_API_KEY (QloApps or PMS system API key):
PMS_API_KEY (press Enter to skip): _
```
→ **Presiona ENTER** (a menos que uses un PMS real)

```
Enter PMS_API_SECRET (if required by your PMS):
PMS_API_SECRET (press Enter to skip): _
```
→ **Presiona ENTER**

```
Enter WHATSAPP_ACCESS_TOKEN (Meta WhatsApp Business token):
WHATSAPP_ACCESS_TOKEN (press Enter to skip): _
```
→ **Presiona ENTER**

```
Enter WHATSAPP_BUSINESS_ACCOUNT_ID:
WHATSAPP_BUSINESS_ACCOUNT_ID (press Enter to skip): _
```
→ **Presiona ENTER**

```
Enter path to Gmail credentials JSON file (press Enter to skip):
Gmail credentials path: _
```
→ **Presiona ENTER**

---

### 3.4️⃣ ÚLTIMO PASO: DEPLOY SECRETS

**Al final del script, verás:**
```
Deploy secrets now? (y/n) _
```

**Escribe: `y` y presiona ENTER**

Esto activará los secrets inmediatamente.

### ✅ Resultado Esperado

Debería mostrar:
```
✅ Secrets deployed and active!
```

---

## PASO 4: VERIFICAR SECRETS

### 📌 Objetivo
Confirmar que todos los secrets se guardaron correctamente.

### 🎯 Comando Exacto

**Copia y pega esto:**

```bash
flyctl secrets list
```

### ✅ Resultado Esperado

Debería mostrar una lista similar a:
```
NAME                           DIGEST
SECRET_KEY                     c5a4f9...
JWT_SECRET_KEY                 8d2b1e...
API_KEY_SECRET                 3f6c9a...
DATABASE_URL                   a1b2c3...
REDIS_URL                      d4e5f6...
WHATSAPP_VERIFY_TOKEN          9x8y7z...
```

### ⏱️ Tiempo Estimado
**5 segundos**

### 🔴 Si No Ves los Secrets

- Verifica que completaste el **PASO 3**
- Verifica que dijiste **"y"** a "Deploy secrets now?"
- Si aún no aparecen, intenta:
  ```bash
  flyctl secrets deploy
  ```

---

## PASO 5: PRIMER DEPLOYMENT

### 📌 Objetivo
Subir tu aplicación a Fly.io.

### 🎯 Comando Exacto

**Copia y pega esto:**

```bash
./deploy-fly.sh
```

### ⏱️ Tiempo Estimado
**5-15 minutos** (primera vez es más lenta porque compila la imagen Docker)

### 📋 Qué Hace el Script

1. ✅ Verifica que git está limpio
2. ✅ Verifica que flyctl está instalado
3. ✅ Verifica que estás autenticado
4. ⚠️ Pregunta si quieres ejecutar tests (recomendado: **n** para ir más rápido)
5. 🔨 Compila la imagen Docker
6. 📤 Sube la imagen a Fly.io
7. 🚀 Inicia la aplicación
8. ✅ Verifica los health checks
9. 🧪 Prueba los endpoints

### 📌 Durante el Deploy

Verás algo como esto (esto es NORMAL):

```
==> Building image with Docker
...
Successfully built abc123def456
...
==> Pushing image to fly.io registry
...
==> Creating release on agente-hotel-api
Release v123 created and started
...
==> Checking app status
✅ Health checks passed!
```

### ✅ Resultado Esperado

Al final verás:
```
✅ Deployment successful!
App URL: https://agente-hotel-api.fly.dev
```

### ⏱️ Tiempo de Espera Entre Comandos

Después de ejecutar el script, Fly.io necesita tiempo para:
1. Construir la imagen (2-5 min)
2. Subir la imagen (1-2 min)
3. Iniciar el contenedor (1-2 min)
4. Pasar health checks (30 seg - 1 min)

**Total: 5-10 minutos aproximadamente**

### 🔴 Si Hay Errores Durante el Deploy

**Error común: "Health check failed"**
- Espera 2-3 minutos más
- Intenta: `flyctl status`

**Error: "Docker build failed"**
- Verifica que tienes internet
- Intenta de nuevo: `./deploy-fly.sh`

**Error: "Permission denied"**
- Si sale esto, ejecuta: `chmod +x deploy-fly.sh` y vuelve a intentar

---

## PASO 6: VERIFICAR DEPLOYMENT

### 📌 Objetivo
Confirmar que tu app está funcionando en Fly.io.

### 6.1️⃣ Ver Status de la Aplicación

**Copia y pega esto:**

```bash
flyctl status
```

### ✅ Resultado Esperado

```
App
  Name     = agente-hotel-api
  Owner    = personal
  Hostname = agente-hotel-api.fly.dev
  Image    = registry.fly.io/agente-hotel-api:deployment-123
  Build ID = abc123

Instances
  ID       TASK   VERSION REGION STATUS      CHECKS                          RESTARTS CREATED
  abc123   app    123     mia    running     1 total, 1 passing              0        5m ago
```

---

### 6.2️⃣ Ver Logs en Tiempo Real

**Para ver lo que está pasando en tu app:**

```bash
flyctl logs -f
```

**Presiona CTRL+C para salir del seguimiento de logs**

---

### 6.3️⃣ Probar los Endpoints

**Prueba que tu app responde:**

```bash
curl https://agente-hotel-api.fly.dev/health/live
```

### ✅ Resultado Esperado

```json
{"status": "healthy", "timestamp": "2025-10-24T..."}
```

---

### 6.4️⃣ Ver Logs Recientes

**Si quieres ver los últimos logs (sin seguimiento en vivo):**

```bash
flyctl logs --limit 50
```

---

## BASES DE DATOS GRATUITAS (OPCIONAL)

### 📌 Si Necesitas PostgreSQL y Redis Externos

---

### OPCIÓN 1: POSTGRESQL CON RAILWAY

#### Paso 1: Crear Cuenta en Railway
- Ve a: https://railway.app
- Haz clic en "Start Project"
- Elige "Create New" → "Database" → "PostgreSQL"

#### Paso 2: Copiar Connection String
- En el dashboard de Railway, busca tu database PostgreSQL
- Ve a "Connect"
- Copia la URL (debería ser similar a):
  ```
  postgresql://postgres:PASSWORD@db.railway.app:5432/railway
  ```

#### Paso 3: Usar en setup-fly-secrets.sh
Cuando el script te pida DATABASE_URL, pega esta URL.

#### Costo
**Gratis** hasta cierto límite (más que suficiente para testing)

---

### OPCIÓN 2: REDIS CON UPSTASH

#### Paso 1: Crear Cuenta en Upstash
- Ve a: https://upstash.com
- Regístrate con GitHub o Email
- Haz clic en "Create Database"

#### Paso 2: Configurar la Base de Datos
- Elige "Redis"
- Región: Miami (same as Fly.io)
- Click "Create"

#### Paso 3: Copiar Connection String
- En el dashboard, ve a tu database
- Haz clic en "Connect"
- Copia la URL REST o REDIS (debería ser similar a):
  ```
  redis://default:YOUR_PASSWORD@redis-12345.upstash.io:6379
  ```

#### Paso 4: Usar en setup-fly-secrets.sh
Cuando el script te pida REDIS_URL, pega esta URL.

#### Costo
**Gratis** - 10,000 comandos/día

---

### RESUMEN RÁPIDO DE URLS

Si ya tienes las URLs, aquí está el formato exacto que necesitas:

**PostgreSQL:**
```
postgresql://username:password@host:5432/dbname
```

**Redis:**
```
redis://default:password@redis-host:6379/0
```

---

## COMANDOS DE REFERENCIA RÁPIDA

### 📊 Monitoreo

```bash
# Ver status de la app
flyctl status

# Ver logs en vivo (CTRL+C para salir)
flyctl logs -f

# Ver últimos 50 logs
flyctl logs --limit 50

# Ver metrics (CPU, memoria, etc.)
flyctl monitoring dashboards metrics
```

### 🔐 Secrets

```bash
# Listar todos los secrets
flyctl secrets list

# Establecer un nuevo secret
flyctl secrets set KEY=VALUE

# Eliminar un secret
flyctl secrets unset KEY

# Mostrar un secret específico (no recomendado)
flyctl secrets show KEY
```

### 🚀 Deployment

```bash
# Hacer un deployment (igual que ./deploy-fly.sh pero sin checks)
flyctl deploy

# Ver historial de deployments
flyctl releases list

# Hacer rollback al deployment anterior
flyctl releases rollback

# Restart la app
flyctl restart
```

### 🔌 Conexión

```bash
# Abrir terminal en el contenedor
flyctl ssh console

# Ejecutar comando en el contenedor
flyctl ssh console -C "command here"

# Abrir la app en navegador
flyctl open

# Abrir el dashboard en navegador
flyctl dashboard
```

### 📈 Escalado

```bash
# Ver configuración actual
flyctl scale show

# Escalar memoria
flyctl scale memory 1024

# Escalar cantidad de instancias
flyctl scale count 3
```

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Problema: "not logged in"

**Solución:**
```bash
flyctl auth logout
flyctl auth login
```

---

### Problema: "Health check failed"

**Solución:**
1. Espera 2-3 minutos (a veces tarda)
2. Verifica logs:
   ```bash
   flyctl logs -f
   ```
3. Si los logs muestran errores, busca DATABASE_URL o REDIS_URL

---

### Problema: "Docker build failed"

**Solución:**
1. Verifica que Dockerfile.production existe:
   ```bash
   ls -la agente-hotel-api/Dockerfile.production
   ```
2. Verifica que tienes requirements-prod.txt:
   ```bash
   ls -la agente-hotel-api/requirements-prod.txt
   ```
3. Intenta de nuevo: `./deploy-fly.sh`

---

### Problema: "Port already in use"

**Solución:**
Esto es raro en Fly.io. Intenta:
```bash
flyctl restart
```

---

### Problema: "Secrets not found"

**Solución:**
```bash
flyctl secrets deploy
flyctl status
```

---

## 📝 CHECKLIST FINAL

Antes de considerar el deployment completo, verifica:

- [ ] `flyctl auth whoami` muestra tu usuario
- [ ] `flyctl secrets list` muestra todos los secrets
- [ ] `flyctl status` muestra "running"
- [ ] `curl https://agente-hotel-api.fly.dev/health/live` responde
- [ ] `curl https://agente-hotel-api.fly.dev/health/ready` responde
- [ ] Los logs no muestran errores: `flyctl logs --limit 20`

---

## 🎉 ¡LISTO!

Tu app está en vivo en Fly.io. 

**URL de tu aplicación:**
```
https://agente-hotel-api.fly.dev
```

---

## 📞 PRÓXIMOS PASOS

1. **Configurar dominio personalizado** (opcional)
   - Ve al dashboard de Fly.io
   - Agrega tu dominio

2. **Configurar WhatsApp Webhook** (si lo necesitas)
   - URL webhook: `https://agente-hotel-api.fly.dev/api/webhooks/whatsapp`
   - Token: El que generó setup-fly-secrets.sh

3. **Monitoreo continuo**
   - Revisa logs regularmente: `flyctl logs -f`
   - Configura alertas en Fly.io

4. **Backups y Recuperación**
   - Documenta tus connection strings
   - Haz backups de tu base de datos periódicamente

---

## 📚 RECURSOS ADICIONALES

- **Documentación Fly.io**: https://fly.io/docs
- **Documentación FastAPI**: https://fastapi.tiangolo.com
- **Documentación Docker**: https://docs.docker.com

---

**Documento creado**: October 24, 2025  
**Versión**: 1.0  
**Autor**: GitHub Copilot  
**Sistema**: Agente Hotelero IA

---

## ✅ RESUMEN DE COMANDOS A EJECUTAR (EN ORDEN)

```bash
# 1. Login en Fly.io
flyctl auth login

# 2. Verificar login
flyctl auth whoami

# 3. Configurar secrets
./setup-fly-secrets.sh

# 4. Verificar secrets
flyctl secrets list

# 5. Hacer deployment
./deploy-fly.sh

# 6. Verificar deployment
flyctl status

# 7. Ver logs
flyctl logs -f

# 8. Probar endpoints
curl https://agente-hotel-api.fly.dev/health/live
curl https://agente-hotel-api.fly.dev/health/ready
```

---

**¿Preguntas? Consulta la sección 🆘 SOLUCIÓN DE PROBLEMAS**
