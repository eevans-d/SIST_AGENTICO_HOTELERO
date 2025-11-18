# 🚀 ETAPA 2 - Plan de Ejecución: Integración QloApps + WhatsApp/Gmail

**Fecha de Inicio:** 2025-11-17  
**Branch:** `feature/dlq-h2-green` → `feature/etapa2-qloapps-integration`  
**Prerequisitos:** ETAPA 1 ✅ COMPLETADA

---

## 📋 Objetivos ETAPA 2

### Objetivo Principal
Integrar el sistema con QloApps PMS real y canales de comunicación productivos (WhatsApp, Gmail) para crear un ambiente de staging realista.

### Entregables Clave
1. **PMS Real Integrado**: QloAppsClient operativo con auth + circuit breaker
2. **WhatsApp Productivo**: Meta Cloud API configurada con webhooks
3. **Gmail Productivo**: OAuth2 configurado para notificaciones
4. **Tests E2E**: Flujo completo de reserva end-to-end
5. **Cobertura Extendida**: 40% → 70%+
6. **Load Testing**: 500 RPS validados
7. **Security Audit**: OWASP validación completada

---

## 🎯 Fases de Ejecución

### FASE 1: Preparación de Configuración (30 min)

#### 1.1 Crear Branch ETAPA 2
```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO
git checkout -b feature/etapa2-qloapps-integration
```

#### 1.2 Preparar `.env.production`
**Archivos Base:**
- Copiar `.env.supabase` → `.env.production`
- Actualizar variables clave:

```bash
# PMS Configuration (CAMBIO CRÍTICO)
PMS_TYPE=qloapps                        # CAMBIAR de mock → qloapps
PMS_BASE_URL=<QLOAPPS_URL>             # URL producción/staging QloApps
PMS_API_KEY=<SECRET>                    # API Key QloApps
PMS_AUTH_TOKEN=<SECRET>                 # Bearer token QloApps
CHECK_PMS_IN_READINESS=true             # CAMBIAR de false → true

# WhatsApp Configuration
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=<SECRET>       # Meta Cloud API Phone ID
WHATSAPP_BUSINESS_ACCOUNT_ID=<SECRET>   # Meta Business Account ID
WHATSAPP_ACCESS_TOKEN=<SECRET>          # Meta Access Token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=<SECRET>  # Token verificación webhook

# Gmail Configuration
GMAIL_CLIENT_ID=<SECRET>                # OAuth2 Client ID
GMAIL_CLIENT_SECRET=<SECRET>            # OAuth2 Client Secret
GMAIL_REFRESH_TOKEN=<SECRET>            # OAuth2 Refresh Token
GMAIL_FROM_EMAIL=reservas@hotel.com     # Email remitente

# Database (Supabase Production)
USE_SUPABASE=true                       # CAMBIAR de false → true
POSTGRES_URL=postgresql+asyncpg://postgres.xxx:5432/postgres
POSTGRES_HOST=xxx.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres.xxx
POSTGRES_PASSWORD=<SECRET>

# Redis (Upstash Production)
REDIS_URL=redis://:xxx@xxx.upstash.io:6379
REDIS_HOST=xxx.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=<SECRET>

# Security (PRODUCCIÓN)
DEBUG=false                             # CAMBIAR de true → false
ENVIRONMENT=production                  # CAMBIAR de development → production
CORS_ALLOWED_ORIGINS=https://hotel.com,https://api.hotel.com
COOP_ENABLED=true                       # Habilitar para producción
COEP_ENABLED=true
```

#### 1.3 Validar Credenciales
- **QloApps**: Hacer llamada curl de prueba con API key
- **WhatsApp**: Validar webhook con Meta
- **Gmail**: Verificar OAuth2 tokens válidos
- **Supabase**: Probar conexión a Postgres
- **Upstash**: Probar conexión a Redis

**Checklist:**
- [ ] `.env.production` creado con todas las secrets
- [ ] QloApps API key validada
- [ ] WhatsApp webhook verificado
- [ ] Gmail OAuth2 tokens válidos
- [ ] Supabase conexión exitosa
- [ ] Upstash Redis conectado

---

### FASE 2: Integración QloApps (1-2 horas)

#### 2.1 Activar QloAppsClient

**Archivo:** `app/services/pms_adapter.py`

**Validaciones:**
1. Revisar `QloAppsClient.__init__()` - auth headers correctos
2. Probar `check_availability()` con fechas reales
3. Validar `get_room_details()` con room_id real
4. Confirmar `create_reservation()` con datos mock

**Tests de Validación:**
```bash
# Test unitario con mock de httpx
pytest tests/unit/test_pms_adapter.py -v -k "qloapps"

# Test de integración con QloApps real (requiere .env.production)
pytest tests/integration/test_pms_integration.py -v --env=production
```

#### 2.2 Circuit Breaker Tuning

**Objetivo:** Ajustar thresholds para PMS real (SLA real vs mock)

**Configuración Actual:**
```python
self.circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # 5 failures → OPEN
    recovery_timeout=30,      # 30s recovery
    expected_exception=httpx.HTTPError
)
```

**Ajustar según SLA QloApps:**
- Si SLA > 99.5%: mantener `failure_threshold=5`
- Si SLA 95-99%: aumentar a `failure_threshold=10`
- `recovery_timeout`: ajustar según tiempo de recovery QloApps (30-60s)

#### 2.3 Cache Strategy para PMS

**Endpoints Críticos:**
- `availability`: TTL 5 min (frecuencia media)
- `room_details`: TTL 60 min (cambios infrecuentes)
- `guest_profile`: TTL 30 min
- `reservation_status`: TTL 2 min (alta frecuencia cambios)

**Código:**
```python
# En pms_adapter.py
cache_ttls = {
    "availability": 300,      # 5 min
    "room_details": 3600,     # 60 min
    "guest_profile": 1800,    # 30 min
    "reservation_status": 120 # 2 min
}
```

**Checklist:**
- [ ] QloAppsClient autenticación exitosa
- [ ] `check_availability()` retorna datos reales
- [ ] Circuit breaker protege contra outages
- [ ] Cache reduce latencia en llamadas repetidas
- [ ] Métricas Prometheus capturando latency/errors

---

### FASE 3: WhatsApp Integration (1-2 horas)

#### 3.1 Configurar Webhook en Meta

**Pasos:**
1. Acceder a Meta Developer Console
2. Configurar Webhook URL: `https://api.hotel.com/api/webhooks/whatsapp`
3. Configurar Verify Token: valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
4. Suscribirse a eventos: `messages`, `message_status`

**Validación Webhook:**
```bash
# Simular llamada de verificación de Meta
curl -X GET "http://localhost:8002/api/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=<TOKEN>"
# Debe retornar: test123
```

#### 3.2 Test de Envío de Mensaje

**Código de Prueba:**
```python
# tests/integration/test_whatsapp_live.py
import pytest
from app.services.whatsapp_client import WhatsAppClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_text_message_live():
    client = WhatsAppClient()
    result = await client.send_text_message(
        to="+1234567890",  # Número de prueba
        text="Test desde ETAPA 2 - Sistema Agente Hotel"
    )
    assert result["success"] is True
```

**Ejecutar:**
```bash
pytest tests/integration/test_whatsapp_live.py -v --env=production
```

#### 3.3 Test de Recepción de Mensaje

**Simular Webhook WhatsApp:**
```bash
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "123",
      "changes": [{
        "value": {
          "messages": [{
            "from": "1234567890",
            "id": "wamid.xxx",
            "timestamp": "1699999999",
            "text": {"body": "Hola, necesito una reserva"},
            "type": "text"
          }]
        }
      }]
    }]
  }'
```

**Validar:**
- Logs muestran mensaje procesado
- Orchestrator detecta intent `greeting`
- Respuesta enviada de vuelta (verificar en WhatsApp test number)

**Checklist:**
- [ ] Webhook configurado en Meta Developer Console
- [ ] Verificación de webhook exitosa
- [ ] Envío de mensaje test exitoso
- [ ] Recepción de webhook procesada correctamente
- [ ] Respuesta automática funciona

---

### FASE 4: Gmail Integration (1 hora)

#### 4.1 Configurar OAuth2

**Archivo:** `app/services/gmail_client.py`

**Validar Tokens:**
```python
# Script de validación: scripts/validate_gmail_oauth.py
import asyncio
from app.services.gmail_client import GmailClient

async def main():
    client = GmailClient()
    result = await client.send_reservation_confirmation(
        to="test@hotel.com",
        guest_name="Juan Pérez",
        reservation_id="RES-001",
        check_in="2025-12-01",
        check_out="2025-12-05",
        room_type="Suite Deluxe"
    )
    print(f"Email enviado: {result}")

asyncio.run(main())
```

**Ejecutar:**
```bash
poetry run python scripts/validate_gmail_oauth.py
```

#### 4.2 Templates de Email

**Archivo:** `templates/email_reservation_confirmation.html`

**Validar:**
- Template renderiza correctamente con datos reales
- Imágenes embedded o links funcionan
- Footer con datos de contacto del hotel

**Checklist:**
- [ ] OAuth2 tokens configurados y validados
- [ ] Envío de email de prueba exitoso
- [ ] Templates renderizando correctamente
- [ ] Rate limiting configurado (no exceder Gmail limits)

---

### FASE 5: Tests E2E Completos (2-3 horas)

#### 5.1 Flujo Completo de Reserva

**Archivo:** `tests/e2e/test_reservation_flow.py`

**Escenario:**
1. Guest envía mensaje por WhatsApp: "Quiero reservar una habitación"
2. Bot detecta intent `check_availability`
3. Bot consulta disponibilidad en QloApps (PMS real)
4. Bot responde con opciones disponibles
5. Guest selecciona habitación y fechas
6. Bot crea reserva en QloApps
7. Bot envía confirmación por WhatsApp
8. Bot envía email de confirmación vía Gmail

**Ejecutar:**
```bash
pytest tests/e2e/test_reservation_flow.py -v --env=production --slow
```

#### 5.2 Validar Métricas E2E

**Prometheus Queries:**
```promql
# Latencia end-to-end
histogram_quantile(0.95, rate(orchestrator_latency_seconds_bucket[5m]))

# Tasa de éxito de reservas
rate(reservations_created_total[5m]) / rate(reservation_attempts_total[5m])

# Circuit breaker trips durante E2E
rate(pms_circuit_breaker_calls_total{state="open"}[5m])
```

**Grafana Dashboard:**
- Abrir dashboard "E2E Reservation Flow"
- Verificar latencia P95 < 3s
- Success rate > 95%
- Circuit breaker trips = 0

**Checklist:**
- [ ] E2E test pasando con PMS real + WhatsApp + Gmail
- [ ] Latencia P95 < 3 segundos
- [ ] Success rate > 95%
- [ ] Circuit breaker no trips durante test
- [ ] Logs estructurados capturan todo el flujo

---

### FASE 6: Cobertura y Calidad (2-4 horas)

#### 6.1 Aumentar Cobertura 40% → 70%

**Prioridad Alta** (target 85%+):
- `app/services/orchestrator.py`
- `app/services/pms_adapter.py`
- `app/services/session_manager.py`
- `app/services/lock_service.py`
- `app/services/whatsapp_client.py`
- `app/services/gmail_client.py`

**Estrategia:**
```bash
# Generar reporte actual
make coverage-report

# Ejecutar tests con --cov-report=html
pytest --cov=app --cov-report=html --cov-report=term-missing

# Revisar htmlcov/index.html para identificar gaps
open htmlcov/index.html
```

**Escribir Tests Faltantes:**
- Error cases (timeouts, 500 errors, auth failures)
- Edge cases (fechas inválidas, habitaciones no disponibles)
- Concurrency (locks, race conditions)

#### 6.2 Lint & Format

```bash
make fmt        # Ruff format + Prettier
make lint       # Ruff check + gitleaks
```

**Checklist:**
- [ ] Cobertura global 70%+
- [ ] Cobertura servicios core 85%+
- [ ] 0 errores de linting
- [ ] 0 secrets detectados por gitleaks

---

### FASE 7: Load Testing (1-2 horas)

#### 7.1 Configurar Locust

**Archivo:** `tests/load/locustfile.py`

```python
from locust import HttpUser, task, between

class HotelAgentUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def check_availability(self):
        self.client.post("/api/webhooks/whatsapp", json={
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "test",
                            "text": {"body": "Disponibilidad para mañana"},
                            "type": "text"
                        }]
                    }
                }]
            }]
        })
    
    @task(1)
    def health_check(self):
        self.client.get("/health/ready")
```

#### 7.2 Ejecutar Load Test

**Objetivo:** 500 RPS con P95 < 500ms, error rate < 1%

```bash
# Iniciar Locust
poetry run locust -f tests/load/locustfile.py --host=http://localhost:8002

# Acceder a UI
open http://localhost:8089

# Configurar:
# - Number of users: 500
# - Spawn rate: 50/s
# - Run time: 5 minutos
```

**Validar:**
- P95 latency < 500ms
- Error rate < 1%
- Circuit breaker no trips masivos
- Redis/Postgres no saturan

**Checklist:**
- [ ] 500 RPS sostenidos por 5 min
- [ ] P95 latency < 500ms
- [ ] Error rate < 1%
- [ ] No degradación de servicios

---

### FASE 8: Security Audit (1-2 horas)

#### 8.1 OWASP ZAP Scan

```bash
# Levantar app
make docker-up

# Ejecutar ZAP scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable zap-baseline.py \
  -t http://host.docker.internal:8002 \
  -r zap_report.html
```

**Revisar:**
- SQL Injection: ❌ No debe haber vulnerabilidades
- XSS: ❌ Todos los inputs sanitizados
- CSRF: ✅ Protecciones habilitadas
- Auth bypass: ❌ No debe ser posible

#### 8.2 Security Headers Validation

```bash
# Test security headers
pytest tests/test_security_headers.py -v

# Verificar headers con curl
curl -I http://localhost:8002/health/live
```

**Esperado:**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: ...
```

**Checklist:**
- [ ] OWASP ZAP scan sin vulnerabilidades HIGH/CRITICAL
- [ ] Security headers presentes en todas las respuestas
- [ ] Secrets no expuestos en logs/responses
- [ ] Rate limiting protege contra brute force

---

### FASE 9: Deployment Preparation (1 hora)

#### 9.1 Docker Compose Production

**Archivo:** `docker-compose.production.yml`

**Validar:**
- Usa `.env.production`
- Health checks configurados correctamente
- Restart policies: `restart: unless-stopped`
- Resource limits definidos (CPU, memoria)

#### 9.2 Staging Deploy Dry-Run

```bash
# Script de deployment staging
./scripts/deploy-staging.sh --env production --build --dry-run

# Verificar plan de deployment
cat .playbook/deploy_plan.json
```

**Checklist:**
- [ ] `docker-compose.production.yml` validado
- [ ] Secrets en `.env.production` no commiteados
- [ ] Deploy script dry-run exitoso
- [ ] Rollback plan documentado

---

## 📊 Criterios de Éxito ETAPA 2

| Criterio | Target | Actual | Status |
|----------|--------|--------|--------|
| **PMS Integration** | QloApps auth + CRUD | - | ⏳ |
| **WhatsApp Live** | Envío/Recepción OK | - | ⏳ |
| **Gmail Live** | Confirmaciones enviadas | - | ⏳ |
| **E2E Tests** | Flujo completo pasa | - | ⏳ |
| **Cobertura Global** | 70%+ | 31% | ⏳ |
| **Load Testing** | 500 RPS, P95<500ms | - | ⏳ |
| **Security Audit** | 0 CRITICAL/HIGH | - | ⏳ |
| **Deployment Ready** | Staging deploy OK | - | ⏳ |

---

## 🚨 Bloqueantes Potenciales

### Bloqueante 1: QloApps API Credentials
**Riesgo:** Sin API key válida, no se puede integrar PMS real  
**Mitigación:** Solicitar credenciales al equipo de QloApps ASAP  
**Fallback:** Mantener modo mock si no hay credenciales

### Bloqueante 2: WhatsApp Business Verification
**Riesgo:** Meta requiere verificación de negocio (puede tardar días)  
**Mitigación:** Iniciar proceso de verificación en paralelo  
**Fallback:** Usar test numbers mientras se verifica

### Bloqueante 3: Gmail OAuth2 Refresh Token Expirado
**Riesgo:** Tokens OAuth2 expiran si no se usan  
**Mitigación:** Regenerar tokens con Google Cloud Console  
**Fallback:** Usar SMTP simple en lugar de Gmail API

### Bloqueante 4: Supabase Rate Limits
**Riesgo:** Free tier de Supabase tiene rate limits bajos  
**Mitigación:** Upgrade a plan Pro si se alcanza límite  
**Fallback:** Usar Postgres local para staging

---

## 📅 Timeline Estimado

| Fase | Duración | Inicio | Fin |
|------|----------|--------|-----|
| FASE 1: Configuración | 30 min | Ahora | +30min |
| FASE 2: QloApps | 1-2h | +30min | +2.5h |
| FASE 3: WhatsApp | 1-2h | +2.5h | +4.5h |
| FASE 4: Gmail | 1h | +4.5h | +5.5h |
| FASE 5: E2E Tests | 2-3h | +5.5h | +8.5h |
| FASE 6: Cobertura | 2-4h | +8.5h | +12.5h |
| FASE 7: Load Testing | 1-2h | +12.5h | +14.5h |
| FASE 8: Security | 1-2h | +14.5h | +16.5h |
| FASE 9: Deploy Prep | 1h | +16.5h | +17.5h |

**Total Estimado:** 11-18 horas (2-3 días de trabajo)

---

## 🎯 Próximo Paso Inmediato

**ACCIÓN:** Crear branch `feature/etapa2-qloapps-integration` y preparar `.env.production`

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO
git checkout -b feature/etapa2-qloapps-integration
cp agente-hotel-api/.env.supabase agente-hotel-api/.env.production
# EDITAR .env.production con secrets reales
```

---

**Preparado por:** GitHub Copilot Agent (Claude Sonnet 4.5)  
**Última Actualización:** 2025-11-17  
**Documento Vivo:** Actualizar conforme se completen fases
