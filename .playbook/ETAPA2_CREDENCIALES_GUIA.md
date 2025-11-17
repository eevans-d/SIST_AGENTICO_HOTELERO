# Guía de Obtención de Credenciales - ETAPA 2

**Fecha**: 2025-11-17  
**Estado Actual**: 3/12 credenciales configuradas (25%)  
**Objetivo**: Configurar todas las credenciales para integración real

---

## Estado de Credenciales

### ✓ Configuradas (3/12)
- `WHATSAPP_ACCESS_TOKEN` ✓
- `WHATSAPP_PHONE_NUMBER_ID` ✓
- `WHATSAPP_VERIFY_TOKEN` ✓

### ✗ Faltantes (9/12)

#### QloApps PMS (4 credenciales)
- `QLOAPPS_BASE_URL`
- `QLOAPPS_API_KEY`
- `QLOAPPS_USERNAME`
- `QLOAPPS_PASSWORD`

#### WhatsApp (1 credencial)
- `WHATSAPP_BUSINESS_ACCOUNT_ID`

#### Gmail OAuth2 (4 credenciales)
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_SENDER_EMAIL`

---

## 1. QloApps PMS - Configuración

### ⚠️ IMPORTANTE: No hay imagen Docker oficial de QloApps

**Estado actual**: La imagen `webkul/qloapps:latest` no existe en Docker Hub.

**Opciones disponibles**:

### Opción A: Instalación Manual de QloApps (Recomendado para Producción)

**Requisitos**:
- Servidor con Apache/Nginx
- MySQL 5.7+
- PHP 7.4+

**Pasos**:

```bash
# 1. Descargar QloApps desde sitio oficial
wget https://qloapps.com/download/latest.zip
unzip latest.zip -d /var/www/qloapps

# 2. Configurar base de datos MySQL
mysql -u root -p
CREATE DATABASE qloapps;
CREATE USER 'qloapps'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON qloapps.* TO 'qloapps'@'localhost';
FLUSH PRIVILEGES;

# 3. Acceder a instalador web
# URL: http://localhost/qloapps
# Seguir wizard de instalación

# 4. Generar API Key desde panel de administración
# Admin Panel > Advanced Parameters > Webservice
# Enable webservice: Yes
# Add new key > Generate
```

**Credenciales generadas**:
```bash
QLOAPPS_BASE_URL=http://localhost/qloapps
QLOAPPS_API_KEY=<key_generada_en_panel>
QLOAPPS_USERNAME=admin@qloapps.com
QLOAPPS_PASSWORD=<tu_password_admin>
```

### Opción B: Usar Mock PMS Adapter (Desarrollo/Testing)

**Para continuar con ETAPA 2 sin QloApps real**:

Mantén `PMS_TYPE=mock` en `.env` y el sistema usará datos simulados.

**Ventajas**:
- No requiere instalación compleja
- Datos consistentes para testing
- Respuestas rápidas sin latencia de red

**Limitaciones**:
- No conecta con sistema real
- Datos de prueba únicamente
- No persiste reservas reales

**Configuración**:
```bash
# En .env
PMS_TYPE=mock
CHECK_PMS_IN_READINESS=false
```

### Opción B: QloApps Cloud/Hosting Externo (Producción)

Si tienes una instancia de QloApps ya en producción o usas QloApps SaaS:

```bash
QLOAPPS_BASE_URL=https://tu-hotel.qloapps.com
QLOAPPS_API_KEY=<solicitar_a_administrador>
QLOAPPS_USERNAME=<usuario_api>
QLOAPPS_PASSWORD=<password_api>
```

**Validar conexión**:
```bash
curl -X GET "https://tu-hotel.qloapps.com/api" \
  -H "Authorization: Basic $(echo -n 'QLOAPPS_API_KEY:' | base64)"
```

### Opción C: Continuar con Mock PMS (Desarrollo - Sin Bloqueo)

**RECOMENDADO PARA ETAPA 2 INICIAL**: Continúa usando MockPMSAdapter mientras se gestiona instalación real de QloApps.

```bash
# En .env - Mantener configuración actual
PMS_TYPE=mock
CHECK_PMS_IN_READINESS=false

# Esto permite:
# - Continuar con integración WhatsApp
# - Continuar con integración Gmail
# - Ejecutar tests de flujo completo
# - Validar orchestrator y NLP
```

**Cuando QloApps real esté disponible**:
```bash
# Cambiar a modo real
PMS_TYPE=qloapps
CHECK_PMS_IN_READINESS=true

# Agregar credenciales reales
QLOAPPS_BASE_URL=https://...
QLOAPPS_API_KEY=...
```

---

## 2. WhatsApp Meta Cloud API - Configuración

### Ya tienes 3/4 credenciales ✓

Solo falta: `WHATSAPP_BUSINESS_ACCOUNT_ID`

**Cómo obtenerlo**:

1. **Acceder a Meta Business Suite**
   - URL: https://business.facebook.com/
   - Iniciar sesión con cuenta de Facebook Business

2. **Navegar a WhatsApp Settings**
   - Business Settings > Accounts > WhatsApp Accounts
   - Seleccionar tu WhatsApp Business Account

3. **Copiar Business Account ID**
   - En la URL verás: `https://business.facebook.com/wa/manage/home/?waba_id=XXXXXXXXX`
   - El número `XXXXXXXXX` es tu `WHATSAPP_BUSINESS_ACCOUNT_ID`

4. **Alternativamente, usar Graph API Explorer**
   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/debug_token" \
     -d "input_token=YOUR_ACCESS_TOKEN" \
     -d "access_token=YOUR_ACCESS_TOKEN"
   ```

**Actualizar en .env**:
```bash
WHATSAPP_BUSINESS_ACCOUNT_ID=<tu_waba_id>
```

---

## 3. Gmail OAuth2 - Configuración Completa

### Paso 1: Crear Proyecto en Google Cloud Console

1. **Acceder a Google Cloud Console**
   - URL: https://console.cloud.google.com/
   - Crear proyecto nuevo: "Agente-Hotelero-IA"

2. **Habilitar Gmail API**
   ```
   APIs & Services > Enable APIs and Services
   Buscar: "Gmail API"
   Click: Enable
   ```

3. **Crear Credenciales OAuth2**
   ```
   APIs & Services > Credentials > Create Credentials > OAuth client ID
   Application type: Web application
   Name: "Agente Hotelero Email Service"
   
   Authorized redirect URIs:
   - http://localhost:8002/auth/gmail/callback
   - https://tu-dominio.com/auth/gmail/callback (producción)
   ```

4. **Copiar credenciales generadas**:
   ```bash
   GMAIL_CLIENT_ID=<Client_ID_generado>.apps.googleusercontent.com
   GMAIL_CLIENT_SECRET=<Client_Secret_generado>
   ```

### Paso 2: Obtener Refresh Token

**Script de autenticación** (ya incluido en el proyecto):

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Ejecutar script de OAuth2 flow
python scripts/gmail_oauth_setup.py \
  --client-id $GMAIL_CLIENT_ID \
  --client-secret $GMAIL_CLIENT_SECRET
```

**Proceso**:
1. Script abre navegador automáticamente
2. Iniciar sesión con cuenta de Gmail del hotel
3. Autorizar permisos (envío de emails)
4. Script captura código y genera refresh_token
5. Refresh token se guarda automáticamente

**Alternativamente, manual**:

```bash
# 1. Generar URL de autorización
AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth?\
client_id=$GMAIL_CLIENT_ID&\
redirect_uri=http://localhost:8002/auth/gmail/callback&\
response_type=code&\
scope=https://www.googleapis.com/auth/gmail.send&\
access_type=offline&\
prompt=consent"

echo $AUTH_URL

# 2. Abrir en navegador, autorizar, copiar código de la URL de retorno

# 3. Intercambiar código por refresh_token
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=<CODIGO_COPIADO>" \
  -d "client_id=$GMAIL_CLIENT_ID" \
  -d "client_secret=$GMAIL_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost:8002/auth/gmail/callback" \
  -d "grant_type=authorization_code"

# Response incluye refresh_token - copiarlo
```

### Paso 3: Configurar Email Remitente

```bash
# Email desde el cual se enviarán las notificaciones
GMAIL_SENDER_EMAIL=reservas@tu-hotel.com

# O usar email personal si es para testing
GMAIL_SENDER_EMAIL=tu-email@gmail.com
```

**Credenciales finales Gmail**:
```bash
GMAIL_CLIENT_ID=<client_id>.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=<client_secret>
GMAIL_REFRESH_TOKEN=<refresh_token_obtenido>
GMAIL_SENDER_EMAIL=reservas@tu-hotel.com
```

---

## 4. Aplicar Configuración Completa

### Actualizar `.env`

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Editar .env con todas las credenciales
nano .env  # o vim, code, etc.
```

**Sección a actualizar**:

```bash
# ============================================================================
# ETAPA 2 - INTEGRACIÓN REAL
# ============================================================================

# Cambiar de mock a qloapps
PMS_TYPE=qloapps
CHECK_PMS_IN_READINESS=true

# === QloApps PMS ===
QLOAPPS_BASE_URL=http://qloapps:8080
QLOAPPS_API_KEY=<tu_api_key>
QLOAPPS_USERNAME=admin@qloapps.com
QLOAPPS_PASSWORD=<tu_password>

# === WhatsApp Meta Cloud API ===
WHATSAPP_ACCESS_TOKEN=<tu_access_token>
WHATSAPP_PHONE_NUMBER_ID=<tu_phone_id>
WHATSAPP_BUSINESS_ACCOUNT_ID=<tu_waba_id>
WHATSAPP_VERIFY_TOKEN=<tu_verify_token>

# === Gmail OAuth2 ===
GMAIL_CLIENT_ID=<tu_client_id>.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=<tu_client_secret>
GMAIL_REFRESH_TOKEN=<tu_refresh_token>
GMAIL_SENDER_EMAIL=reservas@tu-hotel.com
```

### Validar Configuración

```bash
# Ejecutar script de validación
python scripts/validate_credentials.py

# Debe mostrar: 12/12 credenciales válidas ✓
```

---

## 5. Restart de Servicios con Nueva Configuración

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Detener todos los servicios
docker compose down

# Rebuild con nueva configuración (si hay cambios en código)
docker compose build agente-api

# Levantar con PMS profile (incluye qloapps + mysql)
docker compose --profile pms up -d

# Verificar que todos los servicios estén UP
docker compose ps

# Health check
curl http://localhost:8002/health/ready | jq .
```

**Output esperado**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-17T...",
  "services": {
    "database": {"status": "up", "latency_ms": 5},
    "redis": {"status": "up", "latency_ms": 2},
    "pms": {"status": "up", "type": "qloapps", "latency_ms": 120}
  }
}
```

---

## 6. Tests de Integración - ETAPA 2

### Test 1: QloApps PMS

```bash
# Test de conexión PMS
pytest tests/integration/test_pms_qloapps.py -v

# Test de disponibilidad de habitaciones
pytest tests/integration/test_pms_qloapps.py::test_check_availability -v
```

### Test 2: WhatsApp

```bash
# Test de envío de mensaje (usa número de prueba)
pytest tests/integration/test_whatsapp_integration.py::test_send_message -v

# Test de webhook verification
curl -X GET "http://localhost:8002/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=REPLACE_WITH_SECURE_TOKEN&hub.challenge=test123"
```

### Test 3: Gmail

```bash
# Test de envío de email
pytest tests/integration/test_gmail_integration.py::test_send_confirmation_email -v
```

### Test 4: Flujo E2E

```bash
# Test de reserva completa (WhatsApp → PMS → Gmail)
pytest tests/e2e/test_reservation_flow_real.py -v
```

---

## 7. Troubleshooting

### QloApps no responde

```bash
# Verificar logs
docker compose logs qloapps

# Verificar MySQL está UP
docker compose exec mysql mysql -u root -p -e "SHOW DATABASES;"

# Restart QloApps
docker compose restart qloapps
```

### WhatsApp webhook no recibe mensajes

1. Verificar token en Meta Business Suite
2. Verificar webhook URL es HTTPS (ngrok para local)
3. Revisar logs: `docker compose logs agente-api | grep whatsapp`

### Gmail OAuth2 error

```bash
# Regenerar refresh_token
python scripts/gmail_oauth_setup.py --force-reauth

# Verificar scopes en Google Cloud Console
# Debe incluir: https://www.googleapis.com/auth/gmail.send
```

---

## Checklist de Completación ETAPA 2

- [ ] QloApps instalado y accesible
- [ ] API Key de QloApps generada
- [ ] WhatsApp Business Account ID obtenido
- [ ] Gmail OAuth2 configurado completamente
- [ ] Todas las credenciales en `.env`
- [ ] Validación: `python scripts/validate_credentials.py` → 12/12 ✓
- [ ] Stack Docker con `--profile pms` levantado
- [ ] Health check: `/health/ready` → `pms: up` ✓
- [ ] Tests de integración QloApps pasando
- [ ] Tests de integración WhatsApp pasando
- [ ] Tests de integración Gmail pasando
- [ ] Test E2E de reserva completa pasando

---

## Scripts de Ayuda

```bash
# Validar credenciales
make validate-credentials  # alias: python scripts/validate_credentials.py

# Setup Gmail OAuth2
make setup-gmail          # alias: python scripts/gmail_oauth_setup.py

# Test conectividad QloApps
make test-pms-connection  # curl + pytest

# Generar secrets seguros
make generate-secrets     # python secrets CLI

# Full integration tests
make test-integration-real
```

---

**Última actualización**: 2025-11-17  
**Mantenido por**: Backend AI Team  
**Próxima revisión**: Post-ETAPA 2 deployment
