# ETAPA 2 - Estrategia Pragmática de Ejecución

**Fecha**: 2025-11-17  
**Decisión**: Continuar ETAPA 2 con Mock PMS + Integraciones Reales  
**Razón**: No existe imagen Docker oficial de QloApps

---

## Problema Identificado

```bash
docker compose --profile pms up -d qloapps
# Error: pull access denied for webkul/qloapps, repository does not exist
```

**Root Cause**: La imagen `webkul/qloapps:latest` no existe en Docker Hub.

**Opciones evaluadas**:
1. ❌ Instalación manual de QloApps (requiere servidor dedicado, 2-4 horas)
2. ❌ Esperar a que el usuario instale QloApps (bloquea todo ETAPA 2)
3. ✅ **Continuar con Mock PMS + Integraciones Reales** (desbloquea 80% de ETAPA 2)

---

## Estrategia Adoptada

### Fase 2A: Integraciones de Comunicación (AHORA)

**Objetivo**: Completar integraciones de WhatsApp y Gmail con servicios reales.

**Componentes a integrar**:
- ✅ WhatsApp Meta Cloud API (3/4 credenciales ya configuradas)
- ✅ Gmail OAuth2 (script automatizado listo)
- ✅ Orchestrator con flujo completo
- ✅ NLP Engine en modo producción

**PMS**: Mantener `PMS_TYPE=mock` temporalmente

**Beneficios**:
- Desbloquea desarrollo inmediato
- Valida flujo completo de mensajería
- Tests E2E funcionando
- No depende de instalación compleja de QloApps

### Fase 2B: PMS Real (POSTERIOR)

**Cuándo**: Una vez que usuario tenga QloApps instalado o acceso a instancia cloud.

**Qué hacer**:
1. Obtener credenciales de QloApps real
2. Cambiar `.env`: `PMS_TYPE=mock` → `PMS_TYPE=qloapps`
3. Agregar credenciales reales
4. Re-ejecutar tests de integración PMS

**Tiempo estimado**: 30 minutos (si credenciales están listas)

---

## Plan de Ejecución Inmediato

### 1. Completar Credencial de WhatsApp Faltante

**Falta**: `WHATSAPP_BUSINESS_ACCOUNT_ID`

**Pasos**:
```bash
# Opción A: Desde Meta Business Suite
# 1. Ir a https://business.facebook.com/
# 2. Business Settings > WhatsApp Accounts
# 3. Copiar Business Account ID de la URL

# Opción B: Desde Graph API
curl -X GET "https://graph.facebook.com/v18.0/debug_token" \
  -d "input_token=$WHATSAPP_ACCESS_TOKEN" \
  -d "access_token=$WHATSAPP_ACCESS_TOKEN"
```

**Actualizar `.env`**:
```bash
WHATSAPP_BUSINESS_ACCOUNT_ID=<tu_waba_id>
```

### 2. Configurar Gmail OAuth2 Completo

**Script disponible**: `scripts/gmail_oauth_setup.py`

**Pasos**:

#### A. Crear Proyecto en Google Cloud Console

1. Ir a https://console.cloud.google.com/
2. Crear proyecto: "Agente-Hotelero-IA"
3. Habilitar Gmail API
4. Crear credenciales OAuth2 (tipo: Web application)
5. Copiar Client ID y Client Secret

#### B. Ejecutar Script de Setup

```bash
cd agente-hotel-api

python scripts/gmail_oauth_setup.py \
  --client-id <CLIENT_ID>.apps.googleusercontent.com \
  --client-secret <CLIENT_SECRET> \
  --sender-email reservas@tu-hotel.com
```

**Proceso automático**:
- Abre navegador para autorización
- Captura OAuth2 callback
- Genera refresh_token
- Guarda credenciales en `.env`

### 3. Validar Configuración Completa

```bash
# Ejecutar validación
python scripts/validate_credentials.py

# Output esperado:
# WhatsApp: 4/4 ✓
# Gmail: 4/4 ✓
# QloApps: 0/4 (mock mode)
```

### 4. Restart de Servicios con Nueva Configuración

```bash
# Detener stack actual
docker compose down

# Levantar con nueva configuración (SIN profile pms)
docker compose up -d

# Verificar health
curl http://localhost:8002/health/ready | jq .
```

### 5. Tests de Integración Real

```bash
# Test WhatsApp
pytest tests/integration/test_whatsapp_integration.py -v

# Test Gmail
pytest tests/integration/test_gmail_integration.py -v

# Test Orchestrator con Mock PMS
pytest tests/integration/test_orchestrator_integration.py -v

# Test E2E completo (WhatsApp → Orchestrator → Mock PMS → Gmail)
pytest tests/e2e/test_reservation_flow.py -v --mock-pms
```

---

## Métricas de Éxito - Fase 2A

- [ ] WhatsApp: 4/4 credenciales configuradas
- [ ] Gmail: 4/4 credenciales configuradas
- [ ] Tests de integración WhatsApp: 100% pasando
- [ ] Tests de integración Gmail: 100% pasando
- [ ] Test E2E con Mock PMS: Pasando
- [ ] Webhook de WhatsApp recibiendo mensajes reales
- [ ] Emails de confirmación enviándose correctamente

**Criterio de completación**: 6/6 checks ✓

---

## Documentación de Decisión

**ADR (Architecture Decision Record)**

**Decisión**: Usar Mock PMS Adapter en ETAPA 2A, posponer QloApps real a ETAPA 2B.

**Contexto**: 
- Imagen Docker de QloApps no disponible
- Instalación manual requiere 2-4 horas
- 80% de ETAPA 2 es independiente del PMS

**Consecuencias**:
- ✅ Desbloquea desarrollo inmediato
- ✅ Valida integraciones críticas (WhatsApp, Gmail)
- ✅ Permite testing E2E completo
- ⚠️ Reservas no persisten en PMS real (modo simulación)
- ⚠️ Requiere fase 2B posterior para producción completa

**Reversibilidad**: Alta (cambio de configuración en `.env`)

---

## Checklist de Migración a PMS Real (Fase 2B)

Cuando QloApps esté disponible:

- [ ] Obtener URL de instancia QloApps
- [ ] Generar API Key en panel admin
- [ ] Actualizar `.env`: `PMS_TYPE=qloapps`
- [ ] Agregar credenciales: `QLOAPPS_BASE_URL`, `QLOAPPS_API_KEY`, etc.
- [ ] Ejecutar: `docker compose restart agente-api`
- [ ] Validar: `curl http://localhost:8002/health/ready` → `pms: {"status": "up", "type": "qloapps"}`
- [ ] Ejecutar tests: `pytest tests/integration/test_pms_qloapps.py -v`
- [ ] Test E2E real: `pytest tests/e2e/test_reservation_flow.py -v`

**Tiempo estimado**: 30-45 minutos

---

## Próximos Pasos Inmediatos

**AHORA** (Fase 2A):

1. Obtener `WHATSAPP_BUSINESS_ACCOUNT_ID` (5 min)
2. Configurar Gmail OAuth2 (15 min)
3. Validar credenciales (2 min)
4. Restart servicios (1 min)
5. Ejecutar tests de integración (10 min)

**DESPUÉS** (Fase 2B - cuando QloApps esté listo):

1. Obtener credenciales QloApps
2. Actualizar `.env`
3. Restart y validar
4. Tests PMS real

---

**Última actualización**: 2025-11-17  
**Estado**: Estrategia aprobada, ejecutando Fase 2A  
**Bloqueante actual**: Configuración de credenciales (no técnico)
