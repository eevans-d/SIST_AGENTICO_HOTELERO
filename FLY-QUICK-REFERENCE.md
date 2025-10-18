# ⚡ FLY.IO QUICK REFERENCE - Cheatsheet de Comandos

**Referencia rápida de todos los comandos útiles**

---

## AUTENTICACIÓN

```bash
# Login
flyctl auth login

# Signup
flyctl auth signup

# Logout
flyctl auth logout

# Ver usuario
flyctl whoami

# Ver token
flyctl auth token
```

---

## APPS

```bash
# Crear app
flyctl launch

# Listar apps
flyctl apps list

# Ver detalles app
flyctl info

# Ver status
flyctl status

# Eliminar app
flyctl apps destroy APP_NAME
```

---

## DEPLOYMENT

```bash
# Deploy
flyctl deploy

# Deploy con estrategia rolling
flyctl deploy --strategy=rolling

# Deploy sin cache
flyctl deploy --build-only

# Force deploy
flyctl deploy --force

# Deploy específico
flyctl deploy -a APP_NAME
```

---

## RELEASES & ROLLBACK

```bash
# Ver releases
flyctl releases

# Ver detalles release
flyctl releases info

# Rollback
flyctl releases rollback

# Rollback específico
flyctl releases rollback --version=N
```

---

## LOGS

```bash
# Ver logs (continuo)
flyctl logs

# Ver logs con filter
flyctl logs -f

# Últimas N líneas
flyctl logs --num=50

# Específico de instancia
flyctl logs -i INSTANCE_ID

# Seguimiento en tiempo real
flyctl logs -f
```

---

## SSH & CONSOLE

```bash
# Acceder a consola
flyctl ssh console

# SSH a instancia específica
flyctl ssh console -s INSTANCE_ID

# Ejecutar comando
flyctl ssh console -c "ls -la /app"

# Salir
exit
```

---

## SECRETS

```bash
# Listar secrets
flyctl secrets list

# Crear/actualizar secret
flyctl secrets set KEY=VALUE

# Crear múltiples
flyctl secrets set KEY1=VALUE1 KEY2=VALUE2

# Eliminar secret
flyctl secrets unset KEY

# Importar desde archivo
flyctl secrets import < secrets.txt

# Ver en app (via SSH)
flyctl ssh console
printenv JWT_SECRET
exit
```

---

## CONFIGURACIÓN

```bash
# Ver configuración actual
flyctl config show

# Ver fly.toml
cat fly.toml

# Editar fly.toml
flyctl config set ENV_NAME=VALUE

# Ver variables de entorno
flyctl config show --json
```

---

## ESCALAMIENTO

```bash
# Escalar instancias
flyctl scale count=2

# Escalar memoria
flyctl scale memory=2048

# Ver opción VM sizes
# shared-cpu-1x, shared-cpu-2x, dedicated-cpu-1x, etc

# Información de scaling
flyctl scale show
```

---

## REGIONES

```bash
# Listar regiones disponibles
flyctl regions list

# Ver región actual
flyctl regions show

# Agregar región
flyctl regions add SFO

# Remover región
flyctl regions remove MIA

# Cambiar región primaria
flyctl regions update --primary SFO
```

---

## MONITOREO & MÉTRICAS

```bash
# Ver métricas CPU
flyctl metrics cpu

# Ver métricas memoria
flyctl metrics memory

# Ver ancho de banda
flyctl metrics bandwidth

# Ver conexiones
flyctl metrics virgins

# Todas las métricas
flyctl metrics
```

---

## POSTGRES (Si usas)

```bash
# Crear PostgreSQL
flyctl postgres create

# Listar bases de datos
flyctl postgres list

# Attachar a app
flyctl postgres attach --app APP_NAME

# Detach from app
flyctl postgres detach APP_NAME

# Conectar a BD
flyctl postgres connect -a APP_NAME-db

# Backup
flyctl postgres backup -a APP_NAME-db
```

---

## DOMINIOS & SSL

```bash
# Listar certificados
flyctl certs list

# Crear certificado
flyctl certs create DOMAIN

# Ver estado certificado
flyctl certs check DOMAIN

# Eliminar certificado
flyctl certs remove DOMAIN
```

---

## VOLUMES

```bash
# Listar volumes
flyctl volumes list

# Crear volume
flyctl volumes create DATA

# Attached volumes
flyctl volumes show

# Snapshots
flyctl volumes snapshots
```

---

## MACHINE (Bajo nivel)

```bash
# Listar máquinas
flyctl machines list

# Ver máquina
flyctl machines show MACHINE_ID

# Parar máquina
flyctl machines stop MACHINE_ID

# Iniciar máquina
flyctl machines start MACHINE_ID

# Reiniciar
flyctl machines restart MACHINE_ID
```

---

## RED & PROXY

```bash
# Proxy local
flyctl proxy 5432:5432 -a APP_NAME-db

# Exponer puerto localmente
flyctl proxy 8000:8000
```

---

## BILLING & ACCOUNT

```bash
# Ver plan
flyctl billing show

# Ver usage
flyctl billing show --detailed

# Cambiar plan
flyctl billing plan
```

---

## HELP

```bash
# Ayuda general
flyctl help

# Ayuda comando específico
flyctl deploy --help

# Lista de todos los comandos
flyctl --help

# Versión
flyctl version

# Docs
flyctl info

# URL documentación
# https://fly.io/docs
```

---

## ÚTILES COMBINADAS

```bash
# Deploy + Ver logs
flyctl deploy && flyctl logs -f

# Setup completo para nueva app
flyctl launch
flyctl postgres create
flyctl postgres attach --app APP_NAME
flyctl secrets set JWT_SECRET=...
flyctl deploy

# Monitoreo en vivo
flyctl logs -f & flyctl metrics cpu

# Ver status y logs
flyctl status && flyctl logs --num=20

# SSH + Diagnosticar
flyctl ssh console
ps aux  # Ver procesos
top    # Monitor
curl localhost:8000/health/live  # Test app
exit
```

---

## FUNCIONES AVANZADAS

```bash
# Enable console access
flyctl console enable

# Disable console access
flyctl console disable

# Send signal to app
flyctl machines signal MACHINE_ID

# Wait for app to be ready
flyctl wait-ready

# Get app details in JSON
flyctl info --json

# List images
flyctl images list
```

---

## INSTALACIÓN LOCALE

```bash
# Si quieres usar Fly API en scripts
pip install flyctl
```

---

## ALIASES ÚTILES

Agregar a `.bashrc` o `.zshrc`:

```bash
alias fly="flyctl"
alias fls="flyctl status"
alias fll="flyctl logs -f"
alias flm="flyctl machines list"
alias flc="flyctl config show"
```

Luego:
```bash
fly ls   # flyctl apps list
fls      # flyctl status
fll      # flyctl logs -f
```

---

## DOCUMENTACIÓN COMPLETA

```
https://fly.io/docs
https://fly.io/docs/flyctl
https://fly.io/docs/reference/flyctl
```

---

## ¿MÁS AYUDA?

```bash
# Support
flyctl open community

# Slack community
https://slack.fly.io
```

---

**Última actualización**: 2025-10-18

**Guarda este archivo para referencia rápida!**
