# 🔐 Guía de Configuración de Credenciales de Producción

**Fecha**: 11 de Octubre, 2025  
**Propósito**: Configurar credenciales reales para deployment a producción  
**Archivo**: `.env.production`

---

## 📋 CREDENCIALES NECESARIAS

### 1. 📱 **WhatsApp Business API** (Meta/Facebook)

Para obtener estas credenciales necesitas:
1. Cuenta de Meta Business verificada
2. Aplicación de WhatsApp Business configurada
3. Número de teléfono de WhatsApp Business

**Variables a configurar en `.env.production`**:
```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=1234567890123456
WHATSAPP_VERIFY_TOKEN=tu_token_seguro_aqui_min_32_chars
WHATSAPP_APP_SECRET=abcdef1234567890abcdef1234567890
```

**Cómo obtenerlas**:
- **ACCESS_TOKEN**: Meta Business Suite → WhatsApp → Configuración → Tokens de acceso
- **PHONE_NUMBER_ID**: Meta Business Suite → WhatsApp → Números de teléfono → ID del número
- **VERIFY_TOKEN**: Crear uno seguro (puedes generar con: `openssl rand -hex 32`)
- **APP_SECRET**: Meta Business Suite → Configuración de la aplicación → Secreto de la aplicación

**Documentación**: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started

---

### 2. 📧 **Gmail Integration**

Para enviar correos desde Gmail necesitas:
1. Cuenta de Gmail activa
2. App Password generado (no usar contraseña regular)

**Variables a configurar en `.env.production`**:
```bash
GMAIL_USERNAME=hotel-reception@tudominio.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

**Cómo obtenerlas**:
- **GMAIL_USERNAME**: Tu dirección de Gmail
- **GMAIL_APP_PASSWORD**: 
  1. Ir a https://myaccount.google.com/security
  2. Habilitar verificación en dos pasos
  3. Buscar "Contraseñas de aplicaciones"
  4. Generar contraseña para "Correo"
  5. Copiar la contraseña generada (16 caracteres con espacios)

**Documentación**: https://support.google.com/accounts/answer/185833

---

### 3. 🏨 **PMS Integration (QloApps)**

Si quieres integración real con QloApps:

**Variables a configurar en `.env.production`**:
```bash
PMS_TYPE=qloapps  # Cambiar de 'mock' a 'qloapps'
PMS_API_URL=https://tu-qloapps.com/api
PMS_API_KEY=tu_api_key_qloapps
```

**Cómo obtenerlas**:
- **PMS_API_URL**: URL de tu instalación de QloApps + /api
- **PMS_API_KEY**: QloApps → Panel Admin → Configuración → API → Generar clave

**Nota**: Si no tienes QloApps instalado, puedes dejar `PMS_TYPE=mock` por ahora

**Documentación QloApps**: Ver `docs/deployment/QLOAPPS_SETUP.md`

---

### 4. 🔐 **Database & Redis**

**Variables a configurar en `.env.production`**:
```bash
POSTGRES_PASSWORD=tu_password_seguro_aqui_min_16_chars
REDIS_PASSWORD=tu_password_redis_seguro_min_16_chars
```

**Generar contraseñas seguras**:
```bash
# Generar contraseña PostgreSQL
openssl rand -base64 32

# Generar contraseña Redis
openssl rand -base64 32
```

**Requisitos**:
- Mínimo 16 caracteres
- Mezcla de mayúsculas, minúsculas, números y símbolos
- Sin caracteres especiales que puedan causar problemas en URLs

---

### 5. 🔑 **JWT Secret**

**Variable a configurar en `.env.production`**:
```bash
JWT_SECRET_KEY=tu_jwt_secret_super_seguro_min_32_chars
```

**Generar**:
```bash
openssl rand -hex 32
```

---

### 6. 🌐 **Domain & SSL**

**Variables a configurar en `.env.production`**:
```bash
DOMAIN=tuhotel.com
SSL_EMAIL=admin@tuhotel.com
```

**Requisitos**:
- Dominio registrado y apuntando a tu servidor
- Email válido para certificados SSL (Let's Encrypt)

---

## 🚀 CONFIGURACIÓN RÁPIDA

### Opción A: Configuración Completa (Producción Real)
Configurar TODAS las credenciales anteriores para deployment en producción real.

### Opción B: Staging con Mock (Recomendado para primeras pruebas)
Configurar solo lo esencial:
```bash
# Mantener valores mock para testing
PMS_TYPE=mock
WHATSAPP_ACCESS_TOKEN=test_token_staging
GMAIL_APP_PASSWORD=test_password_staging

# Pero usar contraseñas seguras para DB
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

---

## ✅ VALIDACIÓN DE CONFIGURACIÓN

Después de actualizar `.env.production`, ejecutar:

```bash
# Validar que no quedan placeholders
grep "REPLACE_WITH_" .env.production

# Si devuelve resultados, aún faltan credenciales por configurar
# Si no devuelve nada, ¡todo está listo! ✅
```

---

## 📝 NOTAS DE SEGURIDAD

### ⚠️ IMPORTANTE:
1. **NUNCA** commitear `.env.production` al repositorio Git
2. Verificar que `.env.production` está en `.gitignore`
3. Usar contraseñas únicas (no reutilizar)
4. Rotar credenciales cada 90 días
5. Guardar credenciales en sistema de gestión de secretos (1Password, Vault, etc)

### 🔒 Archivo ya está en .gitignore:
```bash
# Verificar
grep ".env.production" .gitignore
```

---

## 🎯 PRÓXIMOS PASOS

Una vez que `.env.production` esté configurado:

1. ✅ Validar configuración: `grep "REPLACE_WITH_" .env.production`
2. ✅ Build de imagen Docker: `docker build -f Dockerfile.production -t agente-hotel-api:production .`
3. ✅ Deploy a staging: `docker-compose -f docker-compose.staging.yml up -d`
4. ✅ Smoke tests: `make health`
5. ✅ Deploy a producción: `docker-compose -f docker-compose.production.yml up -d`

---

## 🆘 ¿NECESITAS AYUDA?

### Para WhatsApp:
- Documentación oficial: https://developers.facebook.com/docs/whatsapp
- Support: https://business.facebook.com/support

### Para Gmail:
- Documentación: https://support.google.com/mail/answer/7126229
- App Passwords: https://support.google.com/accounts/answer/185833

### Para QloApps:
- Documentación: https://qloapps.com/qlo-reservation-system/
- Support: https://webkul.uvdesk.com/

---

**📌 ESTADO ACTUAL**: 
- ✅ Archivo `.env.production` creado
- ⏳ Pendiente: Configurar credenciales reales
- 🎯 Siguiente: Actualizar valores y validar

**¿Estás listo para continuar?** 🚀