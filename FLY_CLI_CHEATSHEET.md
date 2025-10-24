# 🚀 Fly CLI - Cheat Sheet (Referencia Rápida)

**Uso**: Comandos esenciales para trabajar 100% desde terminal VS Code

---

## ⚡ INSTALACIÓN Y SETUP

```bash
# Instalar Fly CLI
curl -L https://fly.io/install.sh | sh

# Agregar al PATH
echo 'export FLYCTL_INSTALL="$HOME/.fly"' >> ~/.bashrc
echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar
flyctl version

# Autenticar
flyctl auth login

# Confirmar
flyctl auth whoami
```

---

## 🔧 COMANDOS ESENCIALES (TOP 10)

```bash
# 1. DEPLOY (desplegar cambios)
flyctl deploy

# 2. LOGS (ver en vivo - MUY IMPORTANTE)
flyctl logs -f

# 3. STATUS (ver estado)
flyctl status

# 4. SSH (entrar al contenedor)
flyctl ssh console

# 5. SECRETS (gestionar variables sensibles)
flyctl secrets set KEY="value"
flyctl secrets list

# 6. RESTART (reiniciar app)
flyctl restart

# 7. SCALE (cambiar recursos)
flyctl scale memory 512
flyctl scale count 2

# 8. RELEASES (historial de deploys)
flyctl releases

# 9. ROLLBACK (volver a versión anterior)
flyctl releases rollback

# 10. INFO (ver detalles de la app)
flyctl info
```

---

## 🐛 WORKFLOW DEBUGGING (2 TERMINALES)

**Terminal 1** (logs permanentes):
```bash
flyctl logs -f
```

**Terminal 2** (comandos):
```bash
# Editar código en VS Code
code agente-hotel-api/app/main.py

# Deploy
flyctl deploy

# Ver errores en Terminal 1
# Corregir y repetir
```

---

## 🔍 DEBUGGING AVANZADO

```bash
# Entrar al contenedor
flyctl ssh console

# Dentro del contenedor:
cd /app
ls -la
env | grep DATABASE
python3
>>> import app
>>> # test cosas
exit
```

---

## 🎯 ERRORES COMUNES + FIXES

### Error: "App crashed"
```bash
# Ver error
flyctl logs | tail -50

# Fix común: falta dependencia
cd agente-hotel-api
poetry add <package>
cd ..
flyctl deploy
```

### Error: "Health checks failing"
```bash
# Ver cuál falla
flyctl status
curl https://tu-app.fly.dev/health/live

# Fix: aumentar grace_period en fly.toml
[checks.http]
  grace_period = "30s"

flyctl deploy
```

### Error: "Database connection failed"
```bash
# Verificar secret
flyctl secrets list

# Actualizar
flyctl secrets set DATABASE_URL="postgresql://..."
```

### Error: "Out of memory"
```bash
# Aumentar memoria
flyctl scale memory 512
```

---

## 📊 MONITOREO

```bash
# Status en vivo
flyctl status --watch

# Logs filtrados (solo errores)
flyctl logs -f | grep -i "error\|critical"

# Ver recursos
flyctl scale show

# Test endpoints
curl https://tu-app.fly.dev/health/live
curl https://tu-app.fly.dev/health/ready
curl https://tu-app.fly.dev/metrics
```

---

## 🚀 DEPLOY RÁPIDO (SCRIPT)

Crear `deploy-fly.sh`:

```bash
#!/bin/bash
set -e
echo "🚀 Deploying to Fly.io..."
flyctl deploy --strategy rolling
flyctl status
echo "✅ Done! View logs: flyctl logs -f"
```

Usar:
```bash
chmod +x deploy-fly.sh
./deploy-fly.sh
```

---

## 📝 COMANDOS AUXILIARES

```bash
# Abrir app en navegador
flyctl open

# Abrir dashboard Fly.io
flyctl dashboard

# Ver configuración
flyctl config show

# Validar fly.toml
flyctl config validate

# Ver todas tus apps
flyctl apps list

# Ver regiones disponibles
flyctl platform regions

# Importar secrets desde archivo
flyctl secrets import < .env.production
```

---

## ⏱️ TIEMPO POR ITERACIÓN

- **Primer deploy**: 5-10 minutos (incluye build)
- **Deploys posteriores**: 2-3 minutos
- **Rollback**: <1 minuto
- **Ver logs**: instantáneo
- **SSH**: <5 segundos

---

## 🎯 WORKFLOW COMPLETO

```bash
# 1. Hacer cambio en código (VS Code)
code agente-hotel-api/app/main.py

# 2. Commit
git add .
git commit -m "fix: issue"

# 3. Deploy
flyctl deploy

# 4. Ver logs
flyctl logs -f

# 5. Test
curl https://tu-app.fly.dev/health/live

# 6. Si falla, ver error en logs y repetir
```

---

## 🔐 MEJORES PRÁCTICAS

✅ **Secrets**: Usar `flyctl secrets set`, NUNCA commitear `.env`  
✅ **Logs**: Mantener terminal con `flyctl logs -f` siempre abierta  
✅ **Deploy**: Usar `--strategy rolling` (0 downtime)  
✅ **Testing**: Test local antes de deploy  
✅ **Rollback**: Siempre tener plan B con `flyctl releases rollback`  
✅ **Monitoreo**: Configurar alertas en Fly.io dashboard  

---

**📖 Documentación completa**: `PLAN_DEPLOYMENT_FLY_IO.md`  
**🔗 Fly.io Docs**: https://fly.io/docs/
