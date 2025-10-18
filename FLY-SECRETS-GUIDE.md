# 🔐 FLY.IO SECRETS GUIDE - Gestión de Credenciales

**Cómo manejar secrets (contraseñas, tokens, keys) en Fly.io de forma segura**

---

## CONCEPTOS CLAVE

### ¿Qué es un "secret"?
Un valor sensible que NO debe estar en código ni git:
- Contraseñas
- API keys
- Tokens
- Encryption keys
- Database passwords

### Fly.io Secrets vs Railway
```
RAILWAY:                  FLY.IO:
- UI Dashboard           - CLI (flyctl)
- Copy-paste             - Más técnico
- Variables en UI        - flyctl secrets set
- Simples                - Más control
```

---

## TIPOS DE CONFIGURACIÓN EN FLY.IO

### 1. Non-Secret Variables (en fly.toml)
```toml
[env]
  ENVIRONMENT = "production"
  DEBUG = "false"
  LOG_LEVEL = "INFO"
  JWT_ALGORITHM = "HS256"
```

**Visibles en git**: SÍ (está en fly.toml)
**Usar para**: Configuración no sensible

---

### 2. Secrets (via CLI)
```bash
flyctl secrets set JWT_SECRET=valor
```

**Visibles en git**: NO (nunca se commitean)
**Usar para**: Valores sensibles

---

## CREAR SECRETS

### Paso 1: Generar valores seguros

```bash
# Ejecutar script (ya genera los 3 principales)
./scripts/setup-fly-now.sh

# Output:
# JWT_SECRET=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB=
# JWT_REFRESH_SECRET=xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ=
# ENCRYPTION_KEY=bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i=
```

---

### Paso 2: Configurar en Fly.io

#### Opción A: Uno por uno
```bash
flyctl secrets set JWT_SECRET="aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB="
flyctl secrets set JWT_REFRESH_SECRET="xL2pK9dM3qN8vC5eG7jB1aF4hI6sT0uW9xY2pZ="
flyctl secrets set ENCRYPTION_KEY="bF3rJ7mK9nP2sT5uV8wX1yZ4aB6cD8eF0gH2i="
```

#### Opción B: Múltiples a la vez
```bash
flyctl secrets set \
  JWT_SECRET="valor1" \
  JWT_REFRESH_SECRET="valor2" \
  ENCRYPTION_KEY="valor3"
```

#### Opción C: Desde archivo
```bash
# Crear archivo secretos.txt:
JWT_SECRET=valor1
JWT_REFRESH_SECRET=valor2
ENCRYPTION_KEY=valor3

# Importar:
flyctl secrets import < secretos.txt

# ⚠️ Luego eliminar el archivo:
rm secretos.txt
```

---

## VER SECRETS

### Listar nombres (sin valores)
```bash
flyctl secrets list
```

**Output**:
```
NAME                    DIGEST                          DATE
JWT_SECRET              8a3f52...                       2 seconds ago
JWT_REFRESH_SECRET      b4e2ff...                       1 second ago
ENCRYPTION_KEY          c5f1aa...                       Just now
```

### Ver valor de un secret (localmente vía SSH)
```bash
flyctl ssh console
printenv JWT_SECRET
exit
```

**Nota**: Los valores nunca se muestran en `flyctl secrets list`

---

## ACTUALIZAR SECRETS

### Cambiar un secret
```bash
# Solo reemplaza el nuevo valor
flyctl secrets set JWT_SECRET="nuevo_valor"
```

### Eliminar un secret
```bash
flyctl secrets unset JWT_SECRET
```

### Reemplazar todos los secrets
```bash
# Descartar los antiguos:
flyctl secrets unset JWT_SECRET JWT_REFRESH_SECRET ENCRYPTION_KEY

# Establecer nuevos:
flyctl secrets set \
  JWT_SECRET="nuevo1" \
  JWT_REFRESH_SECRET="nuevo2" \
  ENCRYPTION_KEY="nuevo3"
```

---

## SECRETOS REQUERIDOS PARA NUESTRO PROYECTO

### CRÍTICOS (Necesarios para deploy)
```bash
# Generar:
openssl rand -base64 32

# Configurar:
flyctl secrets set JWT_SECRET=<valor>
flyctl secrets set JWT_REFRESH_SECRET=<valor>
flyctl secrets set ENCRYPTION_KEY=<valor>
```

---

### OPCIONALES (Para integración futura)

#### WhatsApp (cuando agregues integración)
```bash
flyctl secrets set WHATSAPP_PHONE_NUMBER_ID=<tu_id>
flyctl secrets set WHATSAPP_ACCESS_TOKEN=<tu_token>
flyctl secrets set WHATSAPP_WEBHOOK_VERIFY_TOKEN=<tu_token>
```

#### Gmail (cuando agregues integración)
```bash
flyctl secrets set GMAIL_SERVICE_ACCOUNT_EMAIL=bot@project.iam.gserviceaccount.com
flyctl secrets set GMAIL_SERVICE_ACCOUNT_KEY=<tu_key_json>
```

#### QloApps real PMS (cuando agregues)
```bash
flyctl secrets set QLOAPPS_API_KEY=<tu_key>
flyctl secrets set QLOAPPS_PASSWORD=<tu_pass>
```

---

## INYECCIÓN AUTOMÁTICA

Después de `flyctl secrets set`, los valores están disponibles como:
```python
# En tu código Python
import os
jwt_secret = os.environ.get("JWT_SECRET")
```

### Variables No-Secret (fly.toml)
```python
# También disponibles:
environment = os.environ.get("ENVIRONMENT")  # From fly.toml [env]
debug_mode = os.environ.get("DEBUG")
```

---

## SECRETS vs ENVIRONMENT VARIABLES

### ARCHIVO: fly.toml (Para no-secrets)
```toml
[env]
  ENVIRONMENT = "production"
  DEBUG = "false"
```

Visible en git: SÍ
Usar para: Config no sensible

### CLI: flyctl secrets set (Para secrets)
```bash
flyctl secrets set JWT_SECRET="valor"
```

Visible en git: NO
Usar para: Contraseñas, tokens, keys

---

## ROTACIÓN DE SECRETS

### ¿Por qué rotar?
- Seguridad: Cambiar periódicamente
- Respuesta a incidente: Si un secret fue comprometido
- Compliance: Requisito en empresas

### Cómo rotar
```bash
# 1. Generar nuevo valor
openssl rand -base64 32

# 2. Actualizar en Fly.io
flyctl secrets set JWT_SECRET="nuevo_valor"

# 3. Redeploy (para que tome efecto)
flyctl deploy

# 4. Verificar logs
flyctl logs -f
```

---

## RECUPERACIÓN SI SE PIERDE

### ⚠️ Fly.io NO muestra valores de secrets antiguos

Si pierdes un secret:
1. **Opción A**: Generar uno nuevo (si es regenerable como JWT_SECRET)
2. **Opción B**: Restaurar de backup local (si guardaste)
3. **Opción C**: Reconstruir desde fuente (BD, API provider, etc)

**Recomendación**: Guardar los 3 secrets principales en password manager

---

## SEGURIDAD - BEST PRACTICES

### ✅ HACER

```bash
# ✓ Guardar en password manager
# ✓ Usar valores generados con openssl
# ✓ Rotar periódicamente (mensual recomendado)
# ✓ Usar flyctl secrets set (no hardcodear)
# ✓ Verificar .gitignore tiene .env* archivos
# ✓ Usar diferentes secrets por entorno (dev/staging/prod)
```

### ❌ NO HACER

```bash
# ✗ Commitar secrets a git
# ✗ Hardcodear valores en código
# ✗ Compartir secrets en chat
# ✗ Usar contraseñas simples
# ✗ Dejar secrets en archivos locales sin proteger
# ✗ Usar mismo secret en dev y prod
```

---

## SECRETOS POR ENTORNO

Si tienes múltiples entornos:

```bash
# Desarrollo (APP: agente-hotel-api-dev)
flyctl --app agente-hotel-api-dev secrets set JWT_SECRET="dev_value"

# Staging (APP: agente-hotel-api-staging)
flyctl --app agente-hotel-api-staging secrets set JWT_SECRET="staging_value"

# Producción (APP: agente-hotel-api-prod)
flyctl --app agente-hotel-api-prod secrets set JWT_SECRET="prod_value"
```

---

## INTEGRACIÓN CON GITHUB (AVANZADO)

Si usas GitHub Actions para deploy:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Fly.io
        uses: superfly/flyctl-actions@master
        with:
          args: "deploy"
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
          JWT_SECRET: ${{ secrets.JWT_SECRET }}
```

---

## TROUBLESHOOTING SECRETS

### ❌ "Secret not found"
```bash
# Verificar que existe
flyctl secrets list | grep JWT_SECRET

# Si no existe, crear:
flyctl secrets set JWT_SECRET="valor"
```

### ❌ "Changes take effect after redeploy"
```bash
# Después de cambiar un secret:
flyctl deploy
```

### ❌ "Application crashing after setting secret"
```bash
# Ver logs para diagnosticar
flyctl logs -f

# Posibles causas:
# - Secret vacío
# - Formato incorrecto
# - Nombre de variable erróneo
```

---

## REFERENCIA RÁPIDA

```bash
# Crear/actualizar
flyctl secrets set KEY="value"

# Listar
flyctl secrets list

# Eliminar
flyctl secrets unset KEY

# Ver en app
flyctl ssh console
printenv KEY
exit

# Importar múltiples
flyctl secrets import < file.txt

# Exportar nombres
flyctl secrets list --json > secrets.json
```

---

## ✅ CHECKLIST

```
☐ Generé 3 secrets con openssl
☐ Configuré con flyctl secrets set
☐ Verifiqué con flyctl secrets list
☐ Redeploy ejecutado
☐ App funcionando con secrets
☐ Guardé secrets en password manager
☐ .gitignore incluye archivos .env*
```

---

**Tiempo**: 10 minutos  
**Complejidad**: 🟡 Media

¡Los secrets están seguros!
