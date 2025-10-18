# 🔧 FLY.IO TROUBLESHOOTING - Guía de Problemas y Soluciones

**Soluciones para problemas comunes en Fly.io**

---

## 🚨 PROBLEMAS DE INSTALACIÓN

### ❌ flyctl no encontrado / comando no reconocido

**Síntomas:**
```
zsh: command not found: flyctl
bash: flyctl: command not found
```

**Soluciones:**

1. **Reinstalar flyctl**
   ```bash
   # macOS con Homebrew
   brew install flyctl
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows con Chocolatey
   choco install flyctl
   ```

2. **Agregar a PATH (Linux/macOS)**
   ```bash
   export PATH="$HOME/.fly/bin:$PATH"
   # Agregar a ~/.bashrc o ~/.zshrc permanentemente
   echo 'export PATH="$HOME/.fly/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Verificar instalación**
   ```bash
   flyctl version
   which flyctl
   ```

---

### ❌ Error: "auth required"

**Síntomas:**
```
Error: auth required
```

**Soluciones:**

1. **Login**
   ```bash
   flyctl auth login
   ```

2. **Verificar token**
   ```bash
   flyctl auth token
   ```

3. **Logout y re-login**
   ```bash
   flyctl auth logout
   flyctl auth login
   ```

4. **Regenerar token si expiró**
   ```bash
   # En https://web.fly.io/user/personal_access_tokens
   # Generar nuevo token y copiar
   flyctl auth token
   ```

---

## 🚨 PROBLEMAS DE DEPLOYMENT

### ❌ Error: "Build failed" o "Docker build error"

**Síntomas:**
```
Error: build failed
[error] Step X/Y: RUN ... exited with code 1
```

**Soluciones:**

1. **Verificar Dockerfile**
   ```bash
   # Asegúrate que existe
   ls -la Dockerfile
   
   # Verificar que build context es correcto en fly.toml
   cat fly.toml | grep -A 5 "\[build\]"
   ```

2. **Test local de Docker build**
   ```bash
   # Build localmente primero
   docker build -f Dockerfile -t test-build .
   
   # Si falla, ver error completo
   docker build -f Dockerfile -t test-build . 2>&1 | tail -50
   ```

3. **Limpiar caché de build**
   ```bash
   flyctl deploy --build-only
   
   # O forzar rebuild sin caché
   # (editar fly.toml y cambiar Dockerfile)
   ```

4. **Verificar dependencias**
   ```bash
   # Si es Python, verificar requirements.txt
   cat requirements.txt | head -20
   
   # Si es Node, verificar package.json
   cat package.json
   ```

5. **Ver logs detallados**
   ```bash
   flyctl deploy --verbose
   ```

---

### ❌ Error: "App took too long to start" o Health check failed

**Síntomas:**
```
Error: failed to wait for app to become ready
Health check status: critical
```

**Soluciones:**

1. **Aumentar timeout de health check**
   ```toml
   # En fly.toml
   [services.tcp_checks.interval]
   grace_period = "60s"  # Aumentar de 30s a 60s
   ```

2. **Verificar que app escucha en puerto correcto**
   ```python
   # app/main.py (FastAPI)
   if __name__ == "__main__":
       uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
   ```

3. **Testear localmente**
   ```bash
   # Correr app local
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Test en otra terminal
   curl http://localhost:8000/health/live
   ```

4. **Ver logs de la app**
   ```bash
   flyctl logs -f
   
   # Esperar 30-60 segundos para ver inicio
   ```

5. **Aumentar tiempo de readiness**
   ```toml
   [[services.http_checks]]
   interval = 30000  # ms
   timeout = 5000
   grace_period = 60000  # Aumentar
   ```

---

### ❌ Error: "Port already in use" o "Bind address in use"

**Síntomas:**
```
Error: failed to bind port 8000
Address already in use
```

**Soluciones:**

1. **Cambiar puerto en fly.toml**
   ```toml
   [[services]]
   internal_port = 8001  # Cambiar de 8000
   ```

2. **Verificar que app usa puerto correcto**
   ```bash
   # En docker run o uvicorn
   uvicorn app.main:app --port 8001
   ```

3. **Verificar máquinas en ejecución**
   ```bash
   flyctl machines list
   
   # Ver proceso en máquina
   flyctl ssh console
   lsof -i :8000  # Ver qué usa el puerto
   kill -9 PID
   ```

---

## 🚨 PROBLEMAS DE DATABASE

### ❌ Error: "Database connection refused"

**Síntomas:**
```
psycopg2.OperationalError: could not connect to server
asyncpg.exceptions.CannotConnectNowError
```

**Soluciones:**

1. **Verificar que PostgreSQL está attachado**
   ```bash
   flyctl status
   # Ver si DATABASE_URL aparece
   
   flyctl config show
   ```

2. **Recrear attachment si falla**
   ```bash
   # Listar bases datos
   flyctl postgres list
   
   # Detach
   flyctl postgres detach -a APP_NAME
   
   # Re-attach
   flyctl postgres attach --app APP_NAME DB_NAME
   ```

3. **Testear conexión directamente**
   ```bash
   # Proxy a la BD
   flyctl proxy 5432:5432 -a APP_NAME-db &
   
   # En otra terminal
   psql -h localhost -U postgres -d APP_NAME
   \dt  # Listar tablas
   exit
   ```

4. **Ver credenciales**
   ```bash
   # SSH a app
   flyctl ssh console
   
   # Ver variable DATABASE_URL
   printenv | grep DATABASE
   
   # Verificar conexión
   curl -s https://fly.io/docs/postgres/connecting
   exit
   ```

---

### ❌ Error: "Database does not exist"

**Síntomas:**
```
psycopg2.Error: database "app_name" does not exist
```

**Soluciones:**

1. **Crear base de datos**
   ```bash
   flyctl postgres create
   ```

2. **Verificar nombre de BD**
   ```bash
   flyctl postgres list
   
   # Ver en fly.toml
   grep -i database fly.toml
   ```

3. **Conectar y crear tablas**
   ```bash
   # Via proxy
   flyctl proxy 5432:5432 -a APP_NAME-db &
   
   # Crear tablas
   psql -h localhost -U postgres -d APP_NAME -f schema.sql
   ```

---

## 🚨 PROBLEMAS DE SECRETS

### ❌ Error: Secret no está disponible en app

**Síntomas:**
```
KeyError: 'JWT_SECRET'
NameError: name 'JWT_SECRET' not found
```

**Soluciones:**

1. **Verificar que secret está seteado**
   ```bash
   flyctl secrets list
   # Debería ver JWT_SECRET en la lista
   ```

2. **Setear secret si falta**
   ```bash
   flyctl secrets set JWT_SECRET=your_secret_here
   
   # Verificar
   flyctl secrets list
   ```

3. **Forzar redeploy después de setear**
   ```bash
   flyctl deploy --force-machines
   ```

4. **Ver valor (vía SSH)**
   ```bash
   flyctl ssh console
   printenv JWT_SECRET
   exit
   ```

5. **Verificar sintaxis en código**
   ```python
   # Python
   import os
   jwt_secret = os.getenv("JWT_SECRET")
   if not jwt_secret:
       raise ValueError("JWT_SECRET not set")
   ```

---

### ❌ Error: "Authentication failed" con APIs externas

**Síntomas:**
```
httpx.HTTPError: 401 Unauthorized
WhatsApp authentication failed
```

**Soluciones:**

1. **Verificar que secret está seteado**
   ```bash
   flyctl secrets list | grep -i whatsapp
   ```

2. **Setear todos los secrets necesarios**
   ```bash
   flyctl secrets set \
     WHATSAPP_API_KEY=... \
     WHATSAPP_PHONE_ID=... \
     GMAIL_CLIENT_ID=...
   ```

3. **Verificar formato de secrets**
   ```bash
   # En app, testear
   flyctl ssh console
   printenv | grep WHATSAPP
   exit
   ```

4. **No incluir comillas en values**
   ```bash
   # ❌ Mal
   flyctl secrets set JWT_SECRET="secret-value"
   
   # ✅ Bien
   flyctl secrets set JWT_SECRET=secret-value
   ```

---

## 🚨 PROBLEMAS DE RENDIMIENTO

### ❌ App muy lento o timeout

**Síntomas:**
```
504 Gateway Timeout
request timed out
response took > 30 seconds
```

**Soluciones:**

1. **Ver CPU y memoria**
   ```bash
   flyctl metrics cpu
   flyctl metrics memory
   ```

2. **Escalar memoria si es necesario**
   ```bash
   flyctl scale memory=2048  # 2 GB
   ```

3. **Escalar instancias**
   ```bash
   flyctl scale count=2  # 2 instancias
   ```

4. **Ver logs para identificar cuello de botella**
   ```bash
   flyctl logs -f
   
   # Buscar operaciones lentas
   grep "duration" | tail -50
   ```

5. **Optimizar queries a BD**
   ```python
   # Agregar índices
   # Usar connection pooling (AsyncPooling en SQLAlchemy)
   # Caché (Redis) para queries frecuentes
   ```

---

### ❌ "Out of memory" (OOM)

**Síntomas:**
```
137 exit code
OOMKilled
```

**Soluciones:**

1. **Aumentar memoria asignada**
   ```bash
   flyctl scale memory=2048
   ```

2. **Optimizar uso de memoria en app**
   ```python
   # Evitar cargar todo en memoria
   # Usar streaming para archivos grandes
   # Limpiar caches periodicamente
   ```

3. **Ver consumo actual**
   ```bash
   flyctl metrics memory
   
   # SSH y monitorear
   flyctl ssh console
   free -h
   top
   exit
   ```

---

## 🚨 PROBLEMAS DE RED

### ❌ Error: "Cannot reach external service" o API timeout

**Síntomas:**
```
httpx.ConnectError: Failed to establish connection
Timeout connecting to external service
```

**Soluciones:**

1. **Verificar conectividad**
   ```bash
   flyctl ssh console
   
   # Test DNS
   nslookup api.example.com
   
   # Test conectividad
   curl -v https://api.example.com
   
   exit
   ```

2. **Ver logs de app**
   ```bash
   flyctl logs -f | grep -i "error\|timeout"
   ```

3. **Aumentar timeout en requests**
   ```python
   import httpx
   
   client = httpx.AsyncClient(timeout=30.0)  # 30 segundos
   ```

4. **Usar circuit breaker**
   ```python
   # Ya implementado en pms_adapter.py
   # Verifica que está habilitado
   ```

---

## 🚨 PROBLEMAS DE DEPLOY

### ❌ Rollback necesario

**Síntomas:**
```
App se descompuso después de deploy
Necesito volver a versión anterior
```

**Soluciones:**

1. **Ver releases**
   ```bash
   flyctl releases
   ```

2. **Ver detalles de release**
   ```bash
   flyctl releases info
   ```

3. **Rollback**
   ```bash
   flyctl releases rollback
   
   # O rollback a específico
   flyctl releases rollback --version=3
   ```

4. **Verificar status**
   ```bash
   flyctl status
   flyctl logs -f
   ```

---

### ❌ Deploy se traba o nunca termina

**Síntomas:**
```
Deployment stuck at 30%
No progreso por 10+ minutos
```

**Soluciones:**

1. **Cancelar deploy actual**
   ```bash
   # En otra terminal
   Ctrl+C  (si está en flyctl deploy)
   
   # O
   flyctl machines list
   # Ver máquinas, si necesario terminar manualmente
   ```

2. **Forzar nuevo deploy**
   ```bash
   flyctl deploy --force-machines
   ```

3. **Ver logs de build**
   ```bash
   flyctl logs -f
   
   # O build local
   docker build -f Dockerfile -t test .
   ```

---

## 🚨 PROBLEMAS DE LOGS

### ❌ No veo logs

**Síntomas:**
```
flyctl logs -f
(ningún output)
```

**Soluciones:**

1. **Verificar que app está corriendo**
   ```bash
   flyctl status
   # Status debe ser "Running"
   ```

2. **Ver últimos logs**
   ```bash
   flyctl logs --num=50
   ```

3. **Logs de máquina específica**
   ```bash
   flyctl machines list
   flyctl logs -i MACHINE_ID
   ```

4. **Aumentar verbosidad en código**
   ```python
   # En settings.py
   LOG_LEVEL = "DEBUG"  # en desarrollo
   ```

---

## 🚨 PROBLEMAS DE MONITOREO

### ❌ Métricas no disponibles

**Síntomas:**
```
No metrics available
Prometheus no tiene datos
```

**Soluciones:**

1. **Verificar que app expone métricas**
   ```python
   # En app/main.py
   from prometheus_client import make_asgi_app
   app.mount("/metrics", make_asgi_app())
   ```

2. **Test local**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **En Fly.io**
   ```bash
   flyctl ssh console
   curl localhost:8000/metrics
   exit
   ```

---

## 🔍 DIAGNOSTICS RÁPIDO

### Script para troubleshoot completo

```bash
#!/bin/bash

echo "=== FLY.IO DIAGNOSTICS ==="

echo -e "\n1. Auth status"
flyctl whoami

echo -e "\n2. App status"
flyctl status

echo -e "\n3. Config"
flyctl config show

echo -e "\n4. Secrets"
flyctl secrets list

echo -e "\n5. Metrics"
flyctl metrics cpu
flyctl metrics memory

echo -e "\n6. Logs (últimas 20 líneas)"
flyctl logs --num=20

echo -e "\n7. Machines"
flyctl machines list

echo -e "\n=== END DIAGNOSTICS ==="
```

Guardar como `diagnose.sh` y ejecutar:
```bash
chmod +x diagnose.sh
./diagnose.sh
```

---

## 📚 RECURSOS ÚTILES

- **Docs oficiales**: https://fly.io/docs
- **Status page**: https://status.fly.io
- **Slack community**: https://slack.fly.io
- **GitHub issues**: https://github.com/superfly/flyctl/issues

---

## ❓ ¿AÚN NO FUNCIONA?

1. **Recopilar información**
   ```bash
   ./diagnose.sh > diagnostics.txt
   flyctl logs --num=100 > logs.txt
   ```

2. **Contactar soporte**
   - Incluir `diagnostics.txt` y `logs.txt`
   - Describir qué intentaste
   - Incluir error exacto

3. **Comunidad Slack**
   - Más rápido para problemas comunes
   - Muchos usuarios ayudando

---

**Última actualización**: 2025-10-18

**¡Suerte con tu deployment! 🚀**
