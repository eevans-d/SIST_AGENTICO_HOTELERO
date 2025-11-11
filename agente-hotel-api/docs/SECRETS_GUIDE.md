# 🔐 GUÍA COMPLETA DE SECRETS Y CREDENCIALES OBLIGATORIAS

**Fecha**: 2025-11-09  
**Versión**: 1.0  
**Sistema**: Agente Hotelero IA - API Backend

---

## ⚠️ IMPORTANTE - LEER PRIMERO

Esta guía documenta **TODAS** las credenciales y secrets que **TÚ DEBES OBTENER MANUALMENTE** antes de desplegar el sistema a producción. Los valores marcados como `REPLACE_WITH_*` en `.env.example` son placeholders de desarrollo y **NUNCA deben usarse en producción**.

**Reglas Críticas**:
1. ✅ **NUNCA** commitear archivos `.env` o `.env.production` al repositorio
2. ✅ **SIEMPRE** usar contraseñas fuertes (mínimo 16 caracteres, mayúsculas, minúsculas, números, símbolos)
3. ✅ **ROTAR** secrets cada 90 días en producción
4. ✅ **USAR** gestores de secrets (Vault, AWS Secrets Manager, etc.) en producción
5. ✅ **VALIDAR** cada secret antes de desplegar con `make validate-deployment`

---

## 📋 ÍNDICE DE SECRETS POR CATEGORÍA

1. [Secrets de Aplicación Core](#1-secrets-de-aplicación-core)
2. [Integración WhatsApp Business API](#2-integración-whatsapp-business-api)
3. [Base de Datos PostgreSQL](#3-base-de-datos-postgresql)
4. [Base de Datos MySQL (QloApps)](#4-base-de-datos-mysql-qloapps)
5. [Redis Cache](#5-redis-cache)
6. [PMS QloApps](#6-pms-qloapps)
7. [Gmail Integration](#7-gmail-integration)
8. [Monitoreo Grafana](#8-monitoreo-grafana)
9. [Alerting (Opcional)](#9-alerting-opcional)
10. [SSL/TLS (Producción)](#10-ssltls-producción)

---

## 1. SECRETS DE APLICACIÓN CORE

### 1.1 `SECRET_KEY` (CRÍTICO)
**Variable**: `SECRET_KEY`  
**Uso**: Firmado de tokens JWT, sesiones, cookies seguras  
**Tipo**: String hexadecimal de 64 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Cómo Generarlo

```bash
# Método 1: OpenSSL (recomendado)
openssl rand -hex 32

# Método 2: Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Método 3: Usando el script del proyecto
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api
./scripts/generate-staging-secrets.sh | grep SECRET_KEY
```

#### ✅ Ejemplo Válido
```bash
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

#### ❌ NO USAR
```bash
SECRET_KEY=REPLACE_WITH_SECURE_32_CHAR_HEX_KEY  # Placeholder de desarrollo
SECRET_KEY=mi-clave-secreta  # Demasiado débil
SECRET_KEY=12345678  # Muy corto
```

#### 🔒 Seguridad
- ✅ Cambiar cada 90 días en producción
- ✅ Único por ambiente (dev/staging/prod)
- ✅ Nunca reutilizar entre proyectos
- ⚠️ Si se filtra, **ROTAR INMEDIATAMENTE** y revocar todos los tokens JWT

---

## 2. INTEGRACIÓN WHATSAPP BUSINESS API

### 2.1 `WHATSAPP_ACCESS_TOKEN` (CRÍTICO)
**Variable**: `WHATSAPP_ACCESS_TOKEN`  
**Uso**: Autenticación con Meta Cloud API para enviar/recibir mensajes  
**Tipo**: Token Bearer de larga duración  
**Dónde obtenerlo**: **Meta Business Developer Console**

#### 📝 Cómo Obtenerlo

1. **Acceder a Meta for Developers**
   - URL: https://developers.facebook.com/
   - Iniciar sesión con tu cuenta de Facebook/Meta

2. **Crear o Seleccionar App**
   - Ir a "My Apps" → "Create App" (si no existe)
   - Tipo: Business
   - Nombre: "Agente Hotelero WhatsApp"

3. **Configurar WhatsApp Business API**
   - En el dashboard de la app → "Add Product" → "WhatsApp"
   - Sección "API Setup" → "Temporary Access Token" (para testing)
   - Para producción → "System User" → "Generate New Token" → Seleccionar permisos:
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`

4. **Generar Token Permanente**
   - Crear System User en Business Settings
   - Generar token con expiración "Never" (60 días renovable automáticamente)
   - **COPIAR Y GUARDAR** el token (solo se muestra una vez)

#### ✅ Ejemplo Válido
```bash
WHATSAPP_ACCESS_TOKEN=EAAMZCxyz123ABCdefGHIjklMNOpqrSTUvwxYZ1234567890abcdefGHIJKLmnoPQRstUVWxyZ
```

#### 🔒 Seguridad
- ✅ Token de System User (no de usuario personal)
- ✅ Permisos mínimos necesarios (principio de menor privilegio)
- ✅ Monitorear uso en Meta Business Dashboard
- ⚠️ Si se filtra, revocar en Meta Console inmediatamente

---

### 2.2 `WHATSAPP_PHONE_NUMBER_ID` (CRÍTICO)
**Variable**: `WHATSAPP_PHONE_NUMBER_ID`  
**Uso**: Identificador del número de teléfono de WhatsApp Business  
**Tipo**: String numérico (15-20 dígitos)  
**Dónde obtenerlo**: **Meta Business Developer Console**

#### 📝 Cómo Obtenerlo

1. **En Meta for Developers**
   - Dashboard de tu app → WhatsApp → "API Setup"
   - Sección "Phone Numbers"
   - Copiar el "Phone number ID" (NO el número de teléfono)

2. **Verificación**
   - Aparece como: `123456789012345`
   - NO confundir con el número de teléfono: `+1234567890`

#### ✅ Ejemplo Válido
```bash
WHATSAPP_PHONE_NUMBER_ID=103845762109384
```

---

### 2.3 `WHATSAPP_VERIFY_TOKEN` (CRÍTICO)
**Variable**: `WHATSAPP_VERIFY_TOKEN`  
**Uso**: Validación del webhook al configurar WhatsApp Business API  
**Tipo**: String arbitrario (mínimo 16 caracteres)  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Cómo Generarlo

```bash
# Método 1: Aleatorio seguro
openssl rand -base64 24

# Método 2: UUID
python3 -c "import uuid; print(str(uuid.uuid4()))"

# Método 3: String personalizado
echo "mi-hotel-webhook-verify-token-2025"
```

#### 📋 Uso en Configuración de Webhook

1. **Generar token** (guardarlo para el `.env`)
2. **Configurar en Meta Console**:
   - App Dashboard → WhatsApp → "Configuration"
   - Webhook URL: `https://tu-dominio.com/api/webhooks/whatsapp`
   - Verify Token: **PEGAR EL MISMO TOKEN** que pusiste en `.env`
   - Subscribed Fields: `messages`, `message_status`

#### ✅ Ejemplo Válido
```bash
WHATSAPP_VERIFY_TOKEN=XyZ789AbC123DeF456GhI789JkL012MnO
```

---

### 2.4 `WHATSAPP_APP_SECRET` (CRÍTICO)
**Variable**: `WHATSAPP_APP_SECRET`  
**Uso**: Validación de firmas de webhooks (seguridad contra replay attacks)  
**Tipo**: String hexadecimal de 32 caracteres  
**Dónde obtenerlo**: **Meta Business Developer Console**

#### 📝 Cómo Obtenerlo

1. **En Meta for Developers**
   - Dashboard de tu app → "Settings" → "Basic"
   - Campo "App Secret" → "Show" (requiere reautenticación)
   - **COPIAR** el secret

#### ✅ Ejemplo Válido
```bash
WHATSAPP_APP_SECRET=a1b2c3d4e5f67890abcdef1234567890
```

#### 🔒 Seguridad
- ✅ Usado para validar firma `X-Hub-Signature-256` en webhooks
- ✅ Nunca exponer en logs o errores
- ⚠️ Si se filtra, regenerar en Meta Console (invalidará webhooks anteriores)

---

## 3. BASE DE DATOS POSTGRESQL

### 3.1 `POSTGRES_PASSWORD` (CRÍTICO)
**Variable**: `POSTGRES_PASSWORD`  
**Uso**: Contraseña del usuario PostgreSQL del agente  
**Tipo**: String con mínimo 16 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Cómo Generarlo

```bash
# Método 1: Aleatorio fuerte (recomendado)
openssl rand -base64 32

# Método 2: Usando pwgen (si está instalado)
pwgen -s 32 1

# Método 3: Python secrets
python3 -c "import secrets; import string; chars = string.ascii_letters + string.digits + string.punctuation; print(''.join(secrets.choice(chars) for _ in range(32)))"
```

#### ✅ Ejemplo Válido
```bash
POSTGRES_PASSWORD=Xk9pL#m2@vQr8$Tn4&Yz6!Bc1%Df3^Gh5
```

#### ❌ NO USAR
```bash
POSTGRES_PASSWORD=password  # Muy común
POSTGRES_PASSWORD=agente123  # Predecible
POSTGRES_PASSWORD=12345678  # Solo números
```

#### 🔒 Seguridad
- ✅ Mínimo 16 caracteres
- ✅ Combinar mayúsculas, minúsculas, números y símbolos
- ✅ Cambiar cada 90 días
- ✅ No reutilizar en otros sistemas

---

### 3.2 `POSTGRES_URL` (CRÍTICO - Auto-construido)
**Variable**: `POSTGRES_URL`  
**Uso**: Connection string completo para SQLAlchemy  
**Tipo**: DSN PostgreSQL con asyncpg  
**Dónde obtenerlo**: **LO CONSTRUYES TÚ**

#### 📝 Formato

```bash
POSTGRES_URL=postgresql+asyncpg://<usuario>:<password>@<host>:<puerto>/<base_datos>
```

#### ✅ Ejemplo Válido (Docker local)
```bash
POSTGRES_URL=postgresql+asyncpg://agente_user:Xk9pL#m2@vQr8$Tn4@postgres:5432/agente_hotel
```

#### ✅ Ejemplo Válido (Supabase Pooler - RECOMENDADO)
```bash
POSTGRES_URL=postgresql+asyncpg://postgres.abcdefghijklmno:MI_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

#### 🔒 Seguridad para Supabase
- ✅ **SIEMPRE** usar el pooler (puerto `6543`) en producción
- ✅ Incluir `?sslmode=require` al final
- ✅ Configurar `USE_SUPABASE=true` en `.env`
- ✅ Reducir pool size cuando uses Supabase:
  ```bash
  POSTGRES_POOL_SIZE=5
  POSTGRES_MAX_OVERFLOW=5
  ```

#### 📋 Componentes a Reemplazar

| Componente | Descripción | Ejemplo |
|------------|-------------|---------|
| `<usuario>` | Usuario Postgres | `agente_user` (local) o `postgres.abcd1234` (Supabase) |
| `<password>` | Password generado | `Xk9pL#m2@vQr8$Tn4` |
| `<host>` | Hostname | `postgres` (Docker) o `aws-0-us-east-1.pooler.supabase.com` |
| `<puerto>` | Puerto | `5432` (directo) o `6543` (Supabase pooler) |
| `<base_datos>` | Nombre DB | `agente_hotel` (local) o `postgres` (Supabase) |

---

## 4. BASE DE DATOS MYSQL (QLOAPPS)

### 4.1 `MYSQL_PASSWORD` (CRÍTICO)
**Variable**: `MYSQL_PASSWORD`  
**Uso**: Contraseña del usuario MySQL de QloApps  
**Tipo**: String con mínimo 16 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Generación
```bash
openssl rand -base64 32
```

#### ✅ Ejemplo Válido
```bash
MYSQL_PASSWORD=Rm7nH!k3@Wp9$Lq2&Yt8%Cx5^Bv1#Df4
```

---

### 4.2 `MYSQL_ROOT_PASSWORD` (CRÍTICO)
**Variable**: `MYSQL_ROOT_PASSWORD`  
**Uso**: Contraseña root de MySQL (administrativo)  
**Tipo**: String con mínimo 16 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Generación
```bash
openssl rand -base64 32
```

#### ✅ Ejemplo Válido
```bash
MYSQL_ROOT_PASSWORD=Zq4tK@n8#Yr2$Fm6!Jp9%Hd3^Lw7&Bx1
```

#### 🔒 Seguridad
- ✅ **NUNCA** usar root en la aplicación (solo para mantenimiento)
- ✅ Diferente de `MYSQL_PASSWORD`
- ✅ Guardar en vault separado

---

## 5. REDIS CACHE

### 5.1 `REDIS_PASSWORD` (CRÍTICO)
**Variable**: `REDIS_PASSWORD`  
**Uso**: Autenticación Redis para cache y locks distribuidos  
**Tipo**: String con mínimo 16 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Generación
```bash
openssl rand -base64 24
```

#### ✅ Ejemplo Válido
```bash
REDIS_PASSWORD=Ab9Cd2Ef5Gh8Ij1Kl4Mn7Op0Qr3St6
```

#### 📋 Uso en Connection String
```bash
REDIS_URL=redis://:Ab9Cd2Ef5Gh8Ij1Kl4Mn7Op0Qr3St6@redis:6379/0
```

#### 🔒 Seguridad
- ✅ Configurar en `redis.conf`:
  ```conf
  requirepass Ab9Cd2Ef5Gh8Ij1Kl4Mn7Op0Qr3St6
  ```
- ✅ Deshabilitar comandos peligrosos:
  ```conf
  rename-command FLUSHDB ""
  rename-command FLUSHALL ""
  rename-command CONFIG ""
  ```

---

## 6. PMS QLOAPPS

### 6.1 `PMS_API_KEY` (CRÍTICO)
**Variable**: `PMS_API_KEY`  
**Uso**: Autenticación con la API REST de QloApps  
**Tipo**: String alfanumérico (32-64 caracteres)  
**Dónde obtenerlo**: **Panel Admin de QloApps**

#### 📝 Cómo Obtenerlo

1. **Acceder a QloApps Admin**
   - URL: `https://tu-qloapps.com/admin123` (el sufijo puede variar)
   - Credenciales de administrador

2. **Generar API Key**
   - Menú: "Advanced Parameters" → "Webservice"
   - Activar webservice: "YES"
   - "Add New Key"
   - Key Description: "Agente Hotelero API"
   - Status: "Enabled"
   - Permissions: Seleccionar los recursos necesarios:
     - ✅ `hotels` (GET)
     - ✅ `rooms` (GET, POST, PUT)
     - ✅ `bookings` (GET, POST, PUT)
     - ✅ `customers` (GET, POST)
     - ✅ `availability` (GET)
   - **COPIAR** la API key generada (32 caracteres)

#### ✅ Ejemplo Válido
```bash
PMS_API_KEY=A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
```

#### 🔒 Seguridad
- ✅ Permisos mínimos necesarios (no dar acceso completo)
- ✅ IP whitelist en QloApps si es posible
- ✅ Monitorear logs de acceso en QloApps

---

### 6.2 `PMS_BASE_URL` (REQUERIDO)
**Variable**: `PMS_BASE_URL`  
**Uso**: URL base de la instalación de QloApps  
**Tipo**: URL HTTP/HTTPS  
**Dónde obtenerlo**: **Instalación de QloApps**

#### ✅ Ejemplo Válido (Docker)
```bash
PMS_BASE_URL=http://qloapps:80
```

#### ✅ Ejemplo Válido (Producción)
```bash
PMS_BASE_URL=https://pms.tu-hotel.com
```

---

## 7. GMAIL INTEGRATION

### 7.1 `GMAIL_APP_PASSWORD` (CRÍTICO)
**Variable**: `GMAIL_APP_PASSWORD`  
**Uso**: Autenticación SMTP para enviar emails de confirmación/recordatorios  
**Tipo**: Contraseña de aplicación de 16 caracteres (generada por Google)  
**Dónde obtenerlo**: **Google Account Security**

#### 📝 Cómo Obtenerlo

1. **Habilitar Verificación en 2 Pasos**
   - URL: https://myaccount.google.com/security
   - Sección "Signing in to Google"
   - "2-Step Verification" → Activar (si no está activa)

2. **Generar App Password**
   - URL: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other" → Nombre: "Agente Hotelero"
   - Click "Generate"
   - **COPIAR** la contraseña de 16 caracteres (sin espacios)

#### ✅ Ejemplo Válido
```bash
GMAIL_APP_PASSWORD=abcdefghijklmnop
```

#### ❌ NO USAR
```bash
GMAIL_APP_PASSWORD=tu-password-de-gmail  # Contraseña regular NO funciona
```

#### 📋 Configuración Completa
```bash
GMAIL_USERNAME=hotel-reception@tu-hotel.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
```

#### 🔒 Seguridad
- ✅ Usar cuenta de servicio (no personal)
- ✅ Revocar app password si ya no se usa
- ✅ Monitorear actividad en Google Account

---

## 8. MONITOREO GRAFANA

### 8.1 `GRAFANA_ADMIN_PASSWORD` (CRÍTICO)
**Variable**: `GRAFANA_ADMIN_PASSWORD`  
**Uso**: Contraseña del usuario admin de Grafana  
**Tipo**: String con mínimo 12 caracteres  
**Dónde obtenerlo**: **LO GENERAS TÚ**

#### 📝 Generación
```bash
openssl rand -base64 18
```

#### ✅ Ejemplo Válido
```bash
GRAFANA_ADMIN_PASSWORD=Kp8Rt#Yq2@Nm5$Lw9!Hx3
```

#### 🔒 Seguridad
- ✅ Cambiar contraseña default `admin` inmediatamente
- ✅ Habilitar autenticación OAuth si es posible
- ✅ Restringir acceso por IP (firewall)

---

## 9. ALERTING (OPCIONAL PERO RECOMENDADO)

### 9.1 `SLACK_WEBHOOK_URL` (OPCIONAL)
**Variable**: `SLACK_WEBHOOK_URL`  
**Uso**: Enviar alertas críticas a canal de Slack  
**Tipo**: URL webhook de Slack  
**Dónde obtenerlo**: **Slack App Configuration**

#### 📝 Cómo Obtenerlo

1. **Crear Slack App**
   - URL: https://api.slack.com/apps
   - "Create New App" → "From scratch"
   - Nombre: "Agente Hotel Alerts"
   - Workspace: Tu workspace

2. **Activar Incoming Webhooks**
   - Features → "Incoming Webhooks" → Activate
   - "Add New Webhook to Workspace"
   - Seleccionar canal: `#agente-hotel-alerts`
   - **COPIAR** Webhook URL

#### ✅ Ejemplo Válido
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
SLACK_CHANNEL=#agente-hotel-alerts
```

---

### 9.2 `SMTP_PASSWORD` (OPCIONAL)
**Variable**: `SMTP_PASSWORD`  
**Uso**: Contraseña SMTP para enviar alertas por email  
**Tipo**: String (depende del proveedor)  
**Dónde obtenerlo**: **Proveedor SMTP**

#### 📋 Configuración Completa
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.abc123xyz789...
ALERT_EMAIL_TO=ops@tu-hotel.com
ALERT_EMAIL_FROM=agente-alerts@tu-hotel.com
```

---

## 10. SSL/TLS (PRODUCCIÓN)

### 10.1 `DOMAIN` (REQUERIDO)
**Variable**: `DOMAIN`  
**Uso**: Dominio para certificados SSL Let's Encrypt  
**Tipo**: FQDN (Fully Qualified Domain Name)  
**Dónde obtenerlo**: **Registrar dominio o usar subdominio existente**

#### ✅ Ejemplo Válido
```bash
DOMAIN=agente.tu-hotel.com
EMAIL_FOR_CERTBOT=admin@tu-hotel.com
```

#### 📋 Pasos Previos al Deployment

1. **Registrar Dominio** (si no tienes)
   - Proveedores: Namecheap, GoDaddy, CloudFlare, etc.
   - Costo: ~$10-20/año

2. **Configurar DNS**
   - Crear registro A apuntando a tu servidor:
     ```
     agente.tu-hotel.com  →  A  →  123.45.67.89
     ```
   - Esperar propagación DNS (hasta 48 horas)

3. **Verificar Propagación**
   ```bash
   dig agente.tu-hotel.com
   nslookup agente.tu-hotel.com
   ```

---

## 📋 CHECKLIST PRE-DEPLOYMENT

Antes de ejecutar `make deploy-production`, verificar:

### Secrets Críticos (OBLIGATORIOS)
- [ ] `SECRET_KEY` generado con `openssl rand -hex 32`
- [ ] `WHATSAPP_ACCESS_TOKEN` obtenido de Meta Console
- [ ] `WHATSAPP_PHONE_NUMBER_ID` copiado de Meta Console
- [ ] `WHATSAPP_VERIFY_TOKEN` generado y configurado en Meta
- [ ] `WHATSAPP_APP_SECRET` obtenido de Meta Console
- [ ] `POSTGRES_PASSWORD` generado con mínimo 16 caracteres
- [ ] `POSTGRES_URL` construido correctamente
- [ ] `MYSQL_PASSWORD` generado
- [ ] `MYSQL_ROOT_PASSWORD` generado
- [ ] `REDIS_PASSWORD` generado
- [ ] `PMS_API_KEY` obtenido de QloApps Admin
- [ ] `GMAIL_APP_PASSWORD` generado en Google Account

### Secrets Opcionales (RECOMENDADOS)
- [ ] `GRAFANA_ADMIN_PASSWORD` generado
- [ ] `SLACK_WEBHOOK_URL` configurado (alertas)
- [ ] `SMTP_PASSWORD` configurado (emails)
- [ ] `DOMAIN` registrado y DNS configurado

### Validaciones
- [ ] Ningún secret contiene `REPLACE_WITH_*`
- [ ] Todas las passwords tienen mínimo 16 caracteres
- [ ] WhatsApp webhook verificado en Meta Console
- [ ] Gmail app password funciona (test SMTP)
- [ ] QloApps API key tiene permisos correctos
- [ ] DNS propagado para SSL (si aplica)

---

## 🛠️ COMANDOS DE VALIDACIÓN

### 1. Generar todos los secrets automáticamente
```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api
./scripts/generate-staging-secrets.sh > .env.production
```

**⚠️ IMPORTANTE**: Este comando genera secrets aleatorios para bases de datos y Redis, pero **NO puede generar** los secrets externos (WhatsApp, Gmail, PMS) que **TÚ DEBES OBTENER MANUALMENTE**.

### 2. Validar configuración antes de desplegar
```bash
make validate-deployment
```

Este comando verifica:
- ✅ No hay valores `REPLACE_WITH_*`
- ✅ Passwords cumplen requisitos mínimos
- ✅ Variables críticas están definidas
- ✅ Formato de URLs es correcto

### 3. Test de conexión a servicios externos
```bash
# Test WhatsApp API
curl -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN" \
  "https://graph.facebook.com/v18.0/$WHATSAPP_PHONE_NUMBER_ID"

# Test Gmail SMTP
python3 scripts/test_smtp.py

# Test QloApps API
curl -H "Authorization: Bearer $PMS_API_KEY" \
  "$PMS_BASE_URL/api"
```

---

## 🚨 QUÉ HACER SI UN SECRET SE FILTRA

### 1. Identificar el Secret Comprometido
Ejemplos de fuentes de filtración:
- ❌ Commit accidental en Git
- ❌ Logs expuestos públicamente
- ❌ Variables de entorno en CI/CD mal configurado
- ❌ Screenshot compartido con secret visible

### 2. Rotación Inmediata (Por Tipo)

#### WhatsApp Access Token
```bash
# 1. Revocar en Meta Console
https://developers.facebook.com/ → Tu App → Settings → Advanced → Revoke

# 2. Generar nuevo token
Dashboard → WhatsApp → API Setup → Generate New Token

# 3. Actualizar .env.production
WHATSAPP_ACCESS_TOKEN=<nuevo_token>

# 4. Reiniciar servicios
make deploy-production
```

#### SECRET_KEY (JWT)
```bash
# 1. Generar nuevo
openssl rand -hex 32

# 2. Actualizar .env.production
SECRET_KEY=<nuevo_secret>

# 3. IMPORTANTE: Invalidará TODAS las sesiones activas
# 4. Notificar a usuarios de re-autenticación
make deploy-production
```

#### Database Passwords
```bash
# 1. Cambiar password en PostgreSQL
docker exec -it postgres psql -U postgres
ALTER USER agente_user PASSWORD 'nueva_password_super_segura';

# 2. Actualizar .env.production
POSTGRES_PASSWORD=nueva_password_super_segura
POSTGRES_URL=postgresql+asyncpg://agente_user:nueva_password_super_segura@postgres:5432/agente_hotel

# 3. Reiniciar
make deploy-production
```

### 3. Post-Mortem
- [ ] Documentar cómo ocurrió la filtración
- [ ] Implementar prevención (pre-commit hooks, secret scanning)
- [ ] Auditar logs de acceso durante período de exposición
- [ ] Notificar a stakeholders si aplica

---

## 📚 RECURSOS ADICIONALES

### Documentación Oficial
- [Meta WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [QloApps Webservice Documentation](https://qloapps.com/qlo-reservation-system/qlo-api-documentation/)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Let's Encrypt SSL](https://letsencrypt.org/getting-started/)

### Scripts del Proyecto
- `scripts/generate-staging-secrets.sh` - Generación automática de secrets
- `scripts/validate-deployment.sh` - Validación pre-deployment
- `scripts/test_smtp.py` - Test de Gmail SMTP
- `scripts/rotate-secrets.sh` - Rotación asistida de secrets

### Gestores de Secrets Recomendados
- **HashiCorp Vault** (self-hosted, open source)
- **AWS Secrets Manager** (cloud)
- **Azure Key Vault** (cloud)
- **Google Secret Manager** (cloud)
- **1Password Secrets Automation** (SaaS)

---

## 📞 SOPORTE

Si necesitas ayuda con la configuración de secrets:

1. **Revisar logs de validación**:
   ```bash
   make validate-deployment
   ```

2. **Consultar documentación específica** en `docs/`:
   - `docs/INTEGRATION-SUPABASE.md` - Supabase setup
   - `docs/DEPLOYMENT-GUIDE.md` - Deployment completo
   - `docs/TROUBLESHOOTING.md` - Solución de problemas

3. **Verificar variables de entorno cargadas**:
   ```bash
   docker-compose config
   ```

---

**Última actualización**: 2025-11-09  
**Mantenido por**: Backend AI Team  
**Versión del documento**: 1.0
