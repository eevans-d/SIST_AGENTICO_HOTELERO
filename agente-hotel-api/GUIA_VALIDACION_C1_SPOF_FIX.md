# 🚨 GUÍA DE VALIDACIÓN: Fix SPOF AlertManager (C1)

**📅 Fecha**: 13 de Noviembre, 2025  
**⏱️ Tiempo estimado**: 30-45 minutos  
**🎯 Objetivo**: Validar que AlertManager tiene 3 canales redundantes (PagerDuty + Email + Webhook)  
**🔴 Criticidad**: P0 - BLOQUEA PRODUCCIÓN

---

## 📋 ÍNDICE

1. [¿Qué estamos arreglando?](#qué-estamos-arreglando)
2. [Pre-requisitos](#pre-requisitos)
3. [PASO 1: Configurar PagerDuty](#paso-1-configurar-pagerduty-15-minutos)
4. [PASO 2: Configurar Gmail SMTP](#paso-2-configurar-gmail-smtp-10-minutos)
5. [PASO 3: Actualizar archivo .env](#paso-3-actualizar-archivo-env-5-minutos)
6. [PASO 4: Reiniciar AlertManager](#paso-4-reiniciar-alertmanager-2-minutos)
7. [PASO 5: Ejecutar validación automática](#paso-5-ejecutar-validación-automática-5-minutos)
8. [PASO 6: Validación manual en 3 canales](#paso-6-validación-manual-en-3-canales)
9. [Troubleshooting](#troubleshooting)
10. [Limpieza y próximos pasos](#limpieza-y-próximos-pasos)

---

## ¿Qué estamos arreglando?

### El Problema (ANTES)
```
AlertManager → Webhook ÚNICO → agente-api:8000
                    ❌ Si agente-api falla → SILENCIO TOTAL
```

Todas las alertas críticas (base de datos caída, servicio inaccesible, errores 500) van **solo** a un webhook interno. Si la API falla, **nadie se entera**.

### La Solución (DESPUÉS)
```
                    ┌─→ PagerDuty (incident management) ✅
AlertManager ───────┼─→ Email SMTP (oncall inbox)       ✅
                    └─→ Webhook (agente-api:8000)        ✅
```

Ahora AlertManager envía a **3 canales independientes**. Si uno falla, los otros 2 siguen funcionando.

### ¿Por qué es CRÍTICO?
- Sin alertas → No sabemos que el sistema está caído
- Sin alertas → Clientes reportan errores antes que nosotros (mala experiencia)
- Sin alertas → Violamos SLAs de tiempo de respuesta

---

## Pre-requisitos

Antes de empezar, verifica que tienes:

```bash
# 1. Navegador web (para PagerDuty y Gmail)
# 2. Terminal abierta en el directorio del proyecto
cd ~/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 3. Docker Compose funcionando
docker compose ps
# Debes ver: postgres, redis, prometheus, grafana, alertmanager corriendo

# 4. Editor de texto (para .env)
# Usa: nano, vim, o VSCode
```

---

## PASO 1: Configurar PagerDuty (15 minutos)

### 1.1 Crear cuenta gratuita

1. **Abrir navegador** → https://www.pagerduty.com/
2. Click en **"Start Free Trial"** (14 días gratis, no requiere tarjeta)
3. Completa registro:
   - **Email**: `tu-email@gmail.com` (usa uno que revises frecuentemente)
   - **Company Name**: `Agente Hotelero` (o el nombre de tu empresa)
   - **Phone**: Tu número móvil (para SMS de alertas críticas)

4. Confirma email (revisa bandeja de entrada)

### 1.2 Crear servicio de alertas

Una vez dentro de PagerDuty:

1. Click en **"Services"** (menú lateral izquierdo)
2. Click en **"+ New Service"**
3. Configuración del servicio:
   ```
   Name:                 Agente Hotelero API - Production
   Description:          Sistema de recepcionista IA con alertas críticas
   Escalation Policy:    Default (tú serás notificado)
   Alert Grouping:       Intelligent (agrupa alertas similares)
   ```
4. Click **"Next"** (NO cambies el resto de opciones)

### 1.3 Agregar integración Events API v2

1. En la página del servicio recién creado, busca sección **"Integrations"**
2. Click **"+ Add Integration"**
3. Selecciona **"Events API v2"** (⚠️ NO v1, debe ser v2)
4. Click **"Add"**

### 1.4 Copiar Integration Key

Verás una pantalla con:
```
Integration Key: R012A3B4C5D6E7F8G9H0I1J2K3L4M5N6
```

**🔴 IMPORTANTE**: 
- Copia este valor COMPLETO (empieza con `R` y tiene 32 caracteres)
- **NO lo compartas públicamente** (es como una contraseña)
- Guárdalo en un lugar temporal (lo usaremos en PASO 3)

---

## PASO 2: Configurar Gmail SMTP (10 minutos)

### 2.1 Habilitar autenticación de 2 factores (2FA)

1. **Abrir navegador** → https://myaccount.google.com/security
2. Busca sección **"Signing in to Google"**
3. Click en **"2-Step Verification"**
4. Si dice **"Off"**:
   - Click **"Get Started"**
   - Sigue el asistente (te pedirá tu contraseña y un código SMS)
   - Confirma activación
5. Si dice **"On"** → ✅ Ya estás listo, pasa al siguiente paso

### 2.2 Generar App Password (contraseña de aplicación)

1. **Abrir navegador** → https://myaccount.google.com/apppasswords
   
   ⚠️ **Si no ves esta página**:
   - Verifica que 2FA esté habilitado (paso anterior)
   - Espera 5 minutos y recarga la página
   - Cierra sesión y vuelve a entrar

2. Configuración del App Password:
   ```
   Select app:     Mail
   Select device:  Other (Custom name)
   Name:           Agente Hotelero AlertManager
   ```

3. Click **"Generate"**

4. Verás una pantalla con 16 caracteres:
   ```
   abcd efgh ijkl mnop
   ```

5. **🔴 IMPORTANTE**:
   - Copia SOLO los 16 caracteres **SIN ESPACIOS**: `abcdefghijklmnop`
   - Este es tu `SMTP_PASSWORD` (NO es tu contraseña de Gmail normal)
   - Guárdalo en lugar temporal (lo usaremos en PASO 3)
   - Después de cerrar esta ventana, **NO podrás volver a verlo**

### 2.3 Decidir email de destino

Piensa en **quién debe recibir las alertas**:
- **Opción 1 (desarrollo/testing)**: Tu mismo email → `tu-email@gmail.com`
- **Opción 2 (producción)**: Email del equipo oncall → `oncall@tuempresa.com`

Guarda esta dirección, la usaremos en PASO 3.

---

## PASO 3: Actualizar archivo .env (5 minutos)

### 3.1 Crear archivo .env desde plantilla

```bash
# En tu terminal, dentro de agente-hotel-api/
cd ~/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Crear .env desde .env.example (si no existe ya)
cp .env.example .env

# Verificar que se creó
ls -la .env
# Debes ver: -rw-r--r-- 1 tu-usuario tu-grupo ... .env
```

### 3.2 Abrir .env en editor

**Opción A - Nano (más fácil)**:
```bash
nano .env
```

**Opción B - VSCode**:
```bash
code .env
```

**Opción C - Vim**:
```bash
vim .env
```

### 3.3 Localizar sección de alertas

Presiona `Ctrl+W` (en nano) o `/Alerting` (en vim) para buscar:
```bash
# ==============================================================================
# Alerting Configuration (FASE 1 - SPOF Fix)
# ==============================================================================
```

### 3.4 Actualizar valores con tus credenciales

Reemplaza **SOLO estos 5 valores** con los datos que copiaste antes:

```bash
# ✅ Pega tu Integration Key de PagerDuty (PASO 1.4)
PAGERDUTY_INTEGRATION_KEY=R012A3B4C5D6E7F8G9H0I1J2K3L4M5N6

# ✅ Configura emails de destino (PASO 2.3)
ALERT_EMAIL_TO=tu-email@gmail.com           # Quien recibe las alertas
ALERT_EMAIL_FROM=agente-alerts@gmail.com    # Remitente (puede ser ficticio)

# ✅ Configura SMTP (PASO 2.2)
SMTP_HOST=smtp.gmail.com                    # NO cambiar
SMTP_PORT=587                               # NO cambiar
SMTP_USERNAME=tu-email@gmail.com            # Tu email de Gmail COMPLETO
SMTP_PASSWORD=abcdefghijklmnop              # App Password de 16 chars (SIN ESPACIOS)
```

### 3.5 Ejemplo COMPLETO de configuración

```bash
# ==============================================================================
# Alerting Configuration (FASE 1 - SPOF Fix)
# ==============================================================================
PAGERDUTY_INTEGRATION_KEY=R012A3B4C5D6E7F8G9H0I1J2K3L4M5N6

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#agente-hotel-alerts

ALERT_EMAIL_TO=juan.perez@empresa.com
ALERT_EMAIL_FROM=agente-alerts@gmail.com

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=mi-cuenta@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

### 3.6 Guardar y cerrar

- **Nano**: `Ctrl+O` (guardar), `Enter`, `Ctrl+X` (salir)
- **Vim**: `Esc`, `:wq`, `Enter`
- **VSCode**: `Ctrl+S` (guardar), cerrar pestaña

### 3.7 Verificar que se guardó correctamente

```bash
# Verificar que las variables NO tienen REPLACE_WITH
grep "REPLACE_WITH" .env

# ✅ Resultado esperado: Sin output (línea vacía)
# ❌ Si ves líneas con REPLACE_WITH → repite paso 3.4
```

---

## PASO 4: Reiniciar AlertManager (2 minutos)

### 4.1 Reiniciar servicio con nueva configuración

```bash
# Reiniciar SOLO AlertManager (no afecta otros servicios)
docker compose restart alertmanager

# Esperar 5 segundos
sleep 5
```

### 4.2 Verificar que arrancó correctamente

```bash
# Ver logs de inicio
docker compose logs alertmanager | tail -n 20
```

**✅ Resultado esperado** (busca estas líneas):
```
level=info msg="Listening on :9093" address=:9093
level=info msg="Loading configuration file" file=/etc/alertmanager/config.yml
level=info msg="Completed loading of configuration file" file=/etc/alertmanager/config.yml
```

**❌ Si ves errores** como:
```
level=error msg="Error loading config" err="..."
```
→ Ve a [Troubleshooting - Error en config.yml](#error-en-configyml)

### 4.3 Verificar que está escuchando

```bash
# Probar endpoint de salud
curl -sf http://localhost:9093/-/healthy

# ✅ Resultado esperado: (sin output, código 200)
# ❌ Si falla: curl: (7) Failed to connect
```

---

## PASO 5: Ejecutar validación automática (5 minutos)

### 5.1 Dar permisos de ejecución al script (si no lo hiciste antes)

```bash
chmod +x scripts/validate-alertmanager-spof-fix.sh
```

### 5.2 Ejecutar script de validación

```bash
./scripts/validate-alertmanager-spof-fix.sh
```

### 5.3 Interpretar salida del script

**✅ RESULTADO ESPERADO** (todo verde):
```
ℹ Preflight checks...
✓ AlertManager is healthy
✓ Prometheus is healthy
✓ .env file exists
✓ PAGERDUTY_INTEGRATION_KEY configured
✓ SMTP_PASSWORD configured
ℹ Checking AlertManager configuration...
✓ SPOF fix confirmed: critical-alerts has 3 channels (PagerDuty + Email + Webhook)
ℹ Sending test alert to AlertManager...
✓ Test alert sent successfully
ℹ Waiting 5 seconds for alert processing...
✓ Test alert is active in AlertManager

========================================================================
MANUAL VALIDATION REQUIRED
========================================================================

The test alert 'TestSPOFFix' was sent to AlertManager.

✅ Check the following channels for the alert:

1. 🟢 PagerDuty Incident:
   - Login to https://www.pagerduty.com/
   - Check Incidents tab for 'SPOF Fix Validation Test Alert'
   - Expected: New incident with severity 'critical'

2. 📧 Email Alert:
   - Check inbox for ALERT_EMAIL_TO
   - Subject: 'TestSPOFFix'
   - Expected: Email from AlertManager with alert details

3. 🔗 Webhook Notification:
   - Check agente-api logs: docker logs agente-api | grep TestSPOFFix
   - Expected: POST to /webhooks/alerts with alert payload

========================================================================
If ALL 3 channels received the alert → SPOF fix is SUCCESSFUL ✅
If ONLY webhook received alert → SPOF fix FAILED ❌
========================================================================
```

**❌ Si ves errores**, ve a la sección [Troubleshooting](#troubleshooting).

---

## PASO 6: Validación manual en 3 canales

Ahora debes verificar **MANUALMENTE** que la alerta llegó a los 3 canales:

---

### Canal 1: PagerDuty 🟢

#### 6.1.1 Abrir PagerDuty
```bash
# En tu navegador
https://www.pagerduty.com/
```

#### 6.1.2 Login con tu cuenta

#### 6.1.3 Ir a "Incidents"
- Click en **"Incidents"** (menú superior)
- Deberías ver un nuevo incidente:

```
🔴 SPOF Fix Validation Test Alert
Service: Agente Hotelero API - Production
Status: Triggered
Time: hace unos segundos
```

#### 6.1.4 Click en el incidente
Verás detalles:
```
Severity: critical
Description: This is a test alert to verify redundant notification 
             channels (PagerDuty + Email + Webhook).
```

#### 6.1.5 Resolver el incidente (limpieza)
- Click en **"Resolve"**
- Reason: `Test completed successfully`
- Click **"Resolve Incident"**

**✅ RESULTADO**: Incidente visible en PagerDuty → **Canal 1 FUNCIONA**

---

### Canal 2: Email 📧

#### 6.2.1 Abrir tu cliente de email
- Gmail web: https://mail.google.com/
- Outlook: https://outlook.live.com/
- Cliente desktop (Thunderbird, Apple Mail, etc.)

#### 6.2.2 Revisar bandeja de entrada
Busca email con:
```
De:      AlertManager <agente-alerts@gmail.com>
Para:    tu-email@gmail.com (el que configuraste)
Asunto:  🚨 CRITICAL: TestSPOFFix
```

#### 6.2.3 Abrir el email
Contenido esperado:
```
[FIRING:1] TestSPOFFix

- alertname = TestSPOFFix
- severity = critical
- service = agente-api
- test_id = testspoffix_XXXXXXXXXX

Annotations:
- summary = SPOF Fix Validation Test Alert
- description = This is a test alert to verify redundant 
                notification channels...
```

**⚠️ Si NO ves el email**:
1. Revisa carpeta de **Spam** / **Correo no deseado**
2. Busca por remitente: `agente-alerts@gmail.com`
3. Espera 2-3 minutos más (puede haber delay)
4. Si sigue sin llegar → ve a [Troubleshooting - Email no recibido](#email-no-recibido)

**✅ RESULTADO**: Email recibido → **Canal 2 FUNCIONA**

---

### Canal 3: Webhook 🔗

#### 6.3.1 Verificar logs de agente-api
```bash
# En tu terminal
docker logs agente-api | grep TestSPOFFix
```

**✅ Resultado esperado**:
```
INFO:     127.0.0.1:XXXX - "POST /webhooks/alerts HTTP/1.1" 200 OK
... alertname="TestSPOFFix" severity="critical" ...
```

**❌ Si NO ves nada**:
```bash
# Verificar que agente-api está corriendo
docker compose ps agente-api

# Ver últimos 50 logs
docker compose logs --tail=50 agente-api

# Verificar endpoint de webhook existe
curl -X POST http://localhost:8002/webhooks/alerts \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
# Esperado: 200 OK o 400 Bad Request (pero NO 404)
```

**✅ RESULTADO**: Webhook recibido en logs → **Canal 3 FUNCIONA**

---

### VALIDACIÓN FINAL

Completa este checklist:

```
[ ] ✅ Canal 1 (PagerDuty): Incidente visible y resuelto
[ ] ✅ Canal 2 (Email):     Email recibido en bandeja
[ ] ✅ Canal 3 (Webhook):   Logs muestran POST a /webhooks/alerts

RESULTADO:
[ ] 3/3 canales funcionan → ✅ SPOF FIX EXITOSO - CONTINUAR
[ ] 2/3 canales funcionan → ⚠️  REVISAR TROUBLESHOOTING
[ ] 0-1 canales funcionan → ❌ ERROR CRÍTICO - NO CONTINUAR
```

---

## Troubleshooting

### Error en config.yml

**Síntoma**:
```bash
docker compose logs alertmanager | grep error
# level=error msg="Error loading config" err="yaml: unmarshal error..."
```

**Solución**:
```bash
# 1. Validar sintaxis YAML
docker run --rm -v $(pwd)/docker/alertmanager:/config \
  prom/alertmanager:latest \
  amtool check-config /config/config.yml

# 2. Si hay errores → verificar indentación
cat docker/alertmanager/config.yml | grep -A 20 "receivers:"

# 3. Comparar con versión original
git diff docker/alertmanager/config.yml

# 4. Si todo falla → restaurar original y re-aplicar fix
git checkout docker/alertmanager/config.yml
# (y volver a aplicar los cambios manualmente)
```

---

### PAGERDUTY_INTEGRATION_KEY inválida

**Síntoma**:
```bash
# Script dice:
✗ PAGERDUTY_INTEGRATION_KEY not configured in .env
```

**Solución**:
```bash
# 1. Verificar que existe en .env
grep PAGERDUTY_INTEGRATION_KEY .env
# Debe mostrar: PAGERDUTY_INTEGRATION_KEY=R012...

# 2. Verificar formato (32 caracteres, empieza con R)
grep PAGERDUTY_INTEGRATION_KEY .env | wc -c
# Debe ser aprox 65 caracteres (32 key + 33 nombre var)

# 3. Verificar que NO tiene comillas ni espacios
# ❌ MALO: PAGERDUTY_INTEGRATION_KEY="R012..."
# ❌ MALO: PAGERDUTY_INTEGRATION_KEY= R012...
# ✅ BUENO: PAGERDUTY_INTEGRATION_KEY=R012...

# 4. Re-generar key en PagerDuty si es necesario
# Services → Agente Hotelero API → Integrations → Events API v2
# Click en "..." → View Integration Key → Copiar
```

---

### Email no recibido

**Síntoma**: Paso 6.2 no muestra email en bandeja.

**Solución 1 - Verificar credenciales SMTP**:
```bash
# Ver si hay errores de auth en AlertManager
docker compose logs alertmanager | grep -i smtp
# Buscar: "535 5.7.8 Username and Password not accepted"

# Si ves error 535 → App Password incorrecto
# Re-generar: https://myaccount.google.com/apppasswords
```

**Solución 2 - Test manual de SMTP**:
```bash
# Enviar email de prueba con tus credenciales
docker run --rm -it \
  alpine/mail:latest \
  -S smtp=smtp://smtp.gmail.com:587 \
  -S smtp-use-starttls \
  -S smtp-auth=login \
  -S smtp-auth-user=tu-email@gmail.com \
  -S smtp-auth-password=abcdefghijklmnop \
  -s "Test SMTP Agente Hotelero" \
  -r agente-alerts@gmail.com \
  tu-email@gmail.com <<< "Test body"

# ✅ Si ves: "Mail sent successfully"
#    → Credenciales OK, problema en AlertManager config

# ❌ Si ves: "Authentication failed"
#    → App Password incorrecto, regenerar en Gmail
```

**Solución 3 - Verificar variable SMTP_USERNAME**:
```bash
# Debe ser email COMPLETO (no solo username)
grep SMTP_USERNAME .env
# ✅ CORRECTO: SMTP_USERNAME=juan.perez@gmail.com
# ❌ INCORRECTO: SMTP_USERNAME=juan.perez
```

---

### Webhook no aparece en logs

**Síntoma**: Paso 6.3 no muestra logs de POST.

**Solución**:
```bash
# 1. Verificar que agente-api está corriendo
docker compose ps agente-api
# State debe ser "Up"

# 2. Verificar que AlertManager puede alcanzar agente-api
docker compose exec alertmanager wget -qO- http://agente-api:8000/health/live
# Esperado: {"status":"healthy"}

# 3. Verificar regla de routing en AlertManager
curl -sf http://localhost:9093/api/v1/status | jq '.data.config.original' | grep -A 5 "webhook_configs"
# Debe mostrar: url: 'http://agente-api:8000/webhooks/alerts'

# 4. Ver TODOS los logs de agente-api (sin filtro)
docker compose logs --tail=100 agente-api
# Buscar manualmente "POST" o "webhook"
```

---

## Limpieza y próximos pasos

### Limpiar alerta de prueba

Si el incidente de PagerDuty sigue activo:
```bash
# Opción 1: Desde PagerDuty web
# Incidents → TestSPOFFix → Resolve

# Opción 2: Esperar 5 minutos (auto-expira)
```

### Commit de cambios

```bash
cd ~/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Verificar qué cambió
git status
# Debes ver:
#   modified:   docker/alertmanager/config.yml
#   modified:   .env.example
#   new file:   scripts/validate-alertmanager-spof-fix.sh
#   new file:   docs/setup/ALERTMANAGER_SPOF_FIX_SETUP.md

# NO commitear .env (tiene secretos)
git diff .env
# Si ves cambios → agregarlo a .gitignore

# Commit SOLO archivos seguros
git add docker/alertmanager/config.yml
git add .env.example
git add scripts/validate-alertmanager-spof-fix.sh
git add docs/setup/ALERTMANAGER_SPOF_FIX_SETUP.md

git commit -m "fix(alerting): C1 - Add redundant notification channels to AlertManager

- Add PagerDuty integration for critical alerts
- Add Email (SMTP) backup notification channel
- Keep webhook to agente-api as tertiary channel
- Create validation script: validate-alertmanager-spof-fix.sh
- Update .env.example with alerting credentials documentation

Fixes SPOF where all alerts went to single webhook.
Now requires 3 simultaneous failures for complete alerting outage.

Validated: PagerDuty + Email + Webhook all receiving test alerts.
"

# Push a repositorio
git push origin main
```

### Marcar tarea como completa

```bash
# Actualizar roadmap
echo "✅ C1: SPOF AlertManager Fix - COMPLETADO" >> docs/ROADMAP_FASE_1_REMEDIATION.md
echo "  - Fecha: $(date +%Y-%m-%d)" >> docs/ROADMAP_FASE_1_REMEDIATION.md
echo "  - Validado: 3/3 canales funcionando (PagerDuty + Email + Webhook)" >> docs/ROADMAP_FASE_1_REMEDIATION.md
```

### Próxima tarea: C2 (Prometheus Rules Validation)

```bash
# La siguiente tarea crítica es validar reglas de Prometheus
# Tiempo estimado: 1 hora
# Comando de inicio:
make validate-prometheus  # (cuando esté implementado)
```

---

## ✅ CRITERIOS DE ÉXITO

Has completado exitosamente C1 si:

1. **✅ PagerDuty**: 
   - Incidente "TestSPOFFix" creado
   - Severidad "critical"
   - Incidente resuelto manualmente

2. **✅ Email**:
   - Email recibido en `ALERT_EMAIL_TO`
   - Asunto contiene "TestSPOFFix"
   - Remitente es `ALERT_EMAIL_FROM`

3. **✅ Webhook**:
   - Logs de `agente-api` muestran POST a `/webhooks/alerts`
   - Status code 200 OK
   - Payload contiene `alertname="TestSPOFFix"`

4. **✅ Configuración**:
   - `.env` tiene credenciales válidas (sin REPLACE_WITH)
   - `docker/alertmanager/config.yml` tiene 3 receivers
   - Script `validate-alertmanager-spof-fix.sh` ejecuta sin errores

5. **✅ Documentación**:
   - Commit creado con descripción clara
   - Push exitoso a repositorio
   - Task marcada como completa en roadmap

---

## 📞 Soporte

Si después de seguir esta guía y troubleshooting sigues con problemas:

1. **Revisa logs completos**:
   ```bash
   docker compose logs > full-logs.txt
   ```

2. **Verifica estado de servicios**:
   ```bash
   docker compose ps
   curl http://localhost:9093/-/healthy  # AlertManager
   curl http://localhost:9090/-/healthy  # Prometheus
   curl http://localhost:8002/health/ready  # agente-api
   ```

3. **Comparte contexto**:
   - Output completo del script de validación
   - Logs de AlertManager (últimas 50 líneas)
   - Contenido de `.env` (⚠️ OCULTA secretos antes de compartir)

---

**🎉 ¡Felicitaciones si llegaste hasta acá con todo en verde!**

Ahora tienes un sistema de alertas **resiliente** que sobrevive fallas del servicio principal.

**Próximo paso**: C2 - Validación de reglas de Prometheus (1 hora de esfuerzo)
