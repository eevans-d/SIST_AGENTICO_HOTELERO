# 🚀 FLY.IO DEPLOYMENT GUIDE - El Deploy Final

**Después del setup, es hora de deployer. Este documento te guía a través de todo.**

---

## PASO 1: Verificar que todo está listo

### Checklist pre-deploy
```bash
# ✓ Secrets configurados
flyctl secrets list

# ✓ APP creada
flyctl apps list

# ✓ PostgreSQL attachado
flyctl config show | grep DATABASE

# ✓ Dockerfile presente
ls -la agente-hotel-api/Dockerfile.production
```

---

## PASO 2: Deploy inicial

### Comando
```bash
flyctl deploy
```

### Qué hace:
1. **Build image**: Construye Docker (2-3 min)
2. **Push a Fly.io**: Sube a registry (1 min)
3. **Deploy**: Inicia la app (1-2 min)
4. **Health check**: Verifica /health/live

### Ver progreso:
```bash
# En otra terminal, mientras se deployea:
flyctl logs -f

# Output esperado:
# [info] App started successfully
# [info] Health checks passing
```

---

## PASO 3: Monitorear deployment

### Ver status en vivo
```bash
flyctl status
```

**Expected output**:
```
app: agente-hotel-api
      hostname: agente-hotel-api.fly.dev
      deployment: agente-hotel-api RUNNING
        Instances: 1 desired, 1 running
```

### Ver logs detallados
```bash
flyctl logs -f
```

**Press Ctrl+C** para salir

---

## PASO 4: Verificar que funciona

### Health check
```bash
curl https://agente-hotel-api.fly.dev/health/live
```

**Expected response**:
```json
{"status": "ok"}
```

### Verificar dominio
```bash
flyctl open /health/live
```

**Debería abrir en navegador y mostrar 200 OK**

---

## PASO 5: Monitoreo post-deploy

### Ver métricas
```bash
flyctl metrics virgins
```

### Ver consola de la app
```bash
flyctl ssh console
```

### Ver variables
```bash
flyctl config show
```

### Ver secrets (no muestra valores)
```bash
flyctl secrets list
```

---

## ESCALAMIENTO (OPCIONAL)

### Aumentar instancias
```bash
# Escalar a 2 instancias
flyctl scale count=2

# Ver status
flyctl status
```

### Cambiar región (AVANZADO)
```bash
# Ver regiones disponibles
flyctl regions list

# Cambiar región
flyctl regions add sfo  # Agrega San Francisco
flyctl regions remove mia  # Quita Miami
```

---

## UPDATES & REDEPLOY

### Hacer cambios al código
1. Editar código
2. Commit a git
3. Redeploy:
```bash
flyctl deploy
```

### Estrategias de deployment
```bash
# Rolling deployment (recomendado)
flyctl deploy --strategy=rolling

# Immediate (menos safe)
flyctl deploy --strategy=immediate

# Bluegreen deployment
flyctl deploy --strategy=bluegreen
```

---

## ROLLBACK (Si algo falla)

### Ver histórico de releases
```bash
flyctl releases
```

### Rollback a versión anterior
```bash
flyctl releases rollback
```

---

## LOGS Y DEBUGGING

### Ver logs en vivo
```bash
flyctl logs -f
```

### Ver últimas N líneas
```bash
flyctl logs --num=100
```

### Acceder por SSH para debugging
```bash
flyctl ssh console

# Dentro de la consola SSH:
cd /app
python -c "import app.main"
exit
```

---

## CUSTOM DOMAIN (AVANZADO)

### Agregar dominio personalizado
```bash
# Verificar dominio
flyctl certs create api.tudominio.com

# Ver estado
flyctl certs check api.tudominio.com
```

### Actualizar DNS
Depende del proveedor DNS, pero típicamente:
- Crear CNAME: `api.tudominio.com` → `agente-hotel-api.fly.dev`

---

## MONITOREO CONTINUO

### Health checks automáticos
Fly.io ya tiene healthchecks configurados en fly.toml:
```toml
[[services.tcp_checks]]
grace_period = "30s"
interval = "15s"
timeout = "10s"

[[services.http_checks]]
path = "/health/live"
interval = "10s"
```

Si una instancia falla:
- Fly.io detecta automáticamente
- Reinicia la instancia
- Notifica si configuras alertas

---

## ALERTS (OPCIONAL - ENTERPRISE)

Fly.io Enterprise permite:
- Alertas por email
- Integración con Slack
- Custom thresholds

---

## TROUBLESHOOTING DEPLOYMENT

### ❌ "Build failed"
```bash
# Ver logs detallados
flyctl logs --num=50

# Verificar Dockerfile
cat agente-hotel-api/Dockerfile.production

# Reintento:
flyctl deploy --force
```

### ❌ "Health check failing"
```bash
# Verificar que app inicia
flyctl ssh console
curl localhost:8000/health/live
exit

# Si no responde:
flyctl logs -f  # Ver por qué falla
```

### ❌ "Database connection refused"
```bash
# Verificar DATABASE_URL está set
flyctl config show

# Si no aparece:
flyctl postgres attach --app agente-hotel-api

# Redeploy
flyctl deploy
```

### ❌ "Out of memory"
```bash
# Escalar recursos (si necesita más RAM)
# Esto se configura en fly.toml:
[app]
  env = {VM_SIZE = "shared-cpu-2x"}  # Más RAM

# Redeploy
flyctl deploy
```

### ❌ "Port in use"
```bash
# El puerto 8000 debe ser el que usa la app
# En fly.toml:
[[services.ports]]
  handlers = ["http"]
  port = 80
  internal_port = 8000  # <-- Debe ser 8000
```

---

## COMANDOS ÚTILES POST-DEPLOY

```bash
# Ver todo
flyctl status

# Ver logs
flyctl logs -f

# Abrir en browser
flyctl open

# SSH access
flyctl ssh console

# Listar secrets
flyctl secrets list

# Ver configuración
flyctl config show

# Redeploy
flyctl deploy

# Rollback
flyctl releases rollback

# Escalar
flyctl scale count=2

# Monitoreo
flyctl metrics virgins
flyctl metrics memory
flyctl metrics bandwidth
```

---

## ✅ DEPLOYMENT COMPLETADO

Tu app está en:
```
https://agente-hotel-api.fly.dev
```

---

## PRÓXIMOS PASOS

- Monitor continuo: `flyctl logs -f`
- Configurar custom domain (opcional)
- Agregar alertas (si empresarial)
- Escalar cuando sea necesario

---

**Tiempo**: ~10 minutos  
**Status**: ✅ App en PRODUCCIÓN

¡Felicidades! 🎉
