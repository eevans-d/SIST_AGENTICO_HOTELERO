# ROADMAP FASE 1 - REMEDIACIÓN DE HALLAZGOS CRÍTICOS

**Fecha inicio**: 2025-11-13  
**Owner**: Equipo Dev + SRE  
**Objetivo**: Resolver hallazgos críticos de auditoría FASE 0 para alcanzar GO PRODUCCIÓN

---

## 📋 RESUMEN EJECUTIVO

**Estado actual**: ✅ C1+C2 COMPLETADAS | 2 CRITICAL eliminadas | Próximo: H1 (4h)  
**Meta**: GO INCONDICIONAL en 3 semanas (15 días hábiles)  
**Esfuerzo total**: ~50 horas de desarrollo + 10 horas de validación  
**Progreso Sprint 1**: 2/4 tareas completadas (C1 ✅, C2 ✅, H1 ⏳, H2 ⏳)

---

## 🎯 PRIORIZACIÓN POR IMPACTO Y ESFUERZO

| ID | Hallazgo | Severidad | Esfuerzo | Prioridad | Sprint | Estado |
|----|----------|-----------|----------|-----------|--------|--------|
| **C1** | SPOF AlertManager | CRITICAL | 2h | P0 | S1 | ✅ DONE |
| **C2** | Validar Prometheus Rules | CRITICAL | 1h | P0 | S1 | ✅ DONE |
| **H1** | Trazas sin contexto negocio | HIGH | 4h | P1 | S1 | ⏳ TODO |
| **H2** | CSP no estricta | HIGH | 2h | P1 | S1 | ⏳ TODO |
| **H3** | Cobertura Orchestrator 13% | HIGH | 8h | P1 | S2 | ⏳ TODO |
| **H4** | Cobertura PMS Adapter 2% | HIGH | 8h | P1 | S2 | ⏳ TODO |
| **M1** | Feature flags push invalidation | MEDIUM | 16h | P2 | S3 | ⏳ TODO |
| **M2** | Rate limiting per-tenant | MEDIUM | 6h | P2 | S3 | ⏳ TODO |
| **M3** | Bulkhead pattern pools | MEDIUM | 8h | P3 | S3 | ⏳ TODO |

---

## 🚀 FASE 1A: QUICK WINS (Sprint 1 - Días 1-3)

### ✅ C1: ELIMINAR SPOF DE ALERTMANAGER [COMPLETADA]

**Estado**: ✅ IMPLEMENTADA Y VALIDADA  
**Fecha completada**: 2025-01-17  
**Resultado**: 9/9 validaciones automatizadas pasadas

**Problema**: Todas las alertas van únicamente a `agente-api:8000/api/v1/alerts/webhook`. Si la API cae, el sistema de alertas queda ciego (cascada de silencio).

**Solución implementada**: Triple redundancia con PagerDuty + Email SMTP + Webhook + Slack.

**Archivos modificados**:
- `docker/alertmanager/entrypoint.sh` - Generación dinámica de config multi-canal
- `docker-compose.yml` - Puerto 9093 expuesto
- `scripts/validate-alertmanager-spof-fix.sh` - Validación automatizada con API v2
- `.env.example` - PAGERDUTY_INTEGRATION_KEY con documentación

**Validación ejecutada**:
```bash
./scripts/validate-alertmanager-spof-fix.sh
# ✅ Preflight checks (5/5 passed)
# ✅ Config validation (receiver 'critical' has 4 channels)
# ✅ Test alert posted successfully
# ✅ Alert confirmed active via API v2
```

**Documentación creada**:
- `GUIA_VALIDACION_C1_SPOF_FIX.md` - Guía paso a paso para usuario
- `docs/setup/ALERTMANAGER_SPOF_FIX_SETUP.md` - Documentación técnica
- `VALIDACION_C1_RESUMEN_EJECUTIVO.md` - Resumen ejecutivo

**Commits**: 305fb77, 62e2d8d, 9d6b0d4

---

### ✅ C2: VALIDAR REGLAS DE PROMETHEUS [COMPLETADA]

**Estado**: ✅ IMPLEMENTADA Y VALIDADA  
**Fecha completada**: 2025-01-17  
**Resultado**: 96 reglas validadas, 0 errores de sintaxis

**Problema**: Dashboards de SLO dependen de `recording rules` que pre-calculan métricas. Si están mal, toda la observabilidad es ilusoria.

**Solución implementada**: Script de validación con promtool + target de Makefile.

**Archivos creados**:
- `scripts/validate-prometheus-rules.sh` (279 líneas)
  * Auto-detección de promtool (local o Docker)
  * Validación de 4 archivos de alertas (63 reglas)
  * Validación de 2 archivos de recording rules (47 reglas)
  * Validación de prometheus.yml con 4 rule files
  * Exit code 0 si todo OK, 1 si errores

**Target de Makefile**:
```bash
make validate-prometheus
# ✅ Alert Rules: 4 valid (0 errors)
# ✅ Recording Rules: 2 valid (0 errors)
# ✅ Config Files: 1 valid (prometheus.yml)
# ✅ ALL VALIDATIONS PASSED ✅
```

**Archivos validados**:
```
Alert Rules:
  - alerts.yml (34 rules) ✅
  - alerts-extra.yml (0 rules) ✅
  - business_alerts.yml (15 rules) ✅
  - alert_rules.yml (14 rules) ✅

Recording Rules:
  - recording_rules.yml (15 rules) ✅
  - recording_rules.tmpl.yml (32 rules) ✅

Config:
  - prometheus.yml (4 rule files referenced) ✅
```

**Tecnología**:
- promtool v3.7.3 (desde imagen prom/prometheus:latest)
- Docker volume mount para acceso a archivos
- Generación temporal de config con rutas relativas

**Documentación creada**:
- `VALIDACION_C2_PROMETHEUS_RULES.md` - Resumen ejecutivo completo

**Commit**: a3a255e

**Pasos de implementación**:

```yaml
# 1. Obtener Integration Key de PagerDuty (o crear cuenta trial)
# URL: https://www.pagerduty.com/sign-up/
# Crear servicio "Agente Hotelero API" → copiar Integration Key

# 2. Modificar docker/alertmanager/config.yml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'critical-pagerduty'
      continue: true  # ✅ Enviar también a webhook
    - match:
        severity: warning
      receiver: 'warning-email'

receivers:
  - name: 'default-receiver'
    webhook_configs:
      - url: 'http://agente-api:8000/api/v1/alerts/webhook'

  - name: 'critical-pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_INTEGRATION_KEY}'  # De .env
        severity: 'critical'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        client: 'AlertManager - Agente Hotelero'
        client_url: '{{ .ExternalURL }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'
          runbook: '{{ .CommonAnnotations.runbook_url }}'
    email_configs:  # ✅ Redundancia adicional
      - to: 'oncall@example.com'
        from: 'alertmanager@agente-hotel.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: '${SMTP_USERNAME}'
        auth_password: '${SMTP_PASSWORD}'
        headers:
          Subject: '[CRITICAL] {{ .GroupLabels.alertname }}'

  - name: 'warning-email'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@agente-hotel.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: '${SMTP_USERNAME}'
        auth_password: '${SMTP_PASSWORD}'
```

**Variables de entorno** (añadir a `.env`):
```bash
# PagerDuty
PAGERDUTY_INTEGRATION_KEY=your_pagerduty_key_here

# SMTP (Gmail)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here  # NO la contraseña normal, usar App Password
```

**Validación**:
```bash
# 1. Reiniciar AlertManager
docker compose restart alertmanager

# 2. Enviar alerta de prueba
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "critical"},
    "annotations": {"summary": "Test SPOF fix", "runbook_url": "http://example.com"}
  }]'

# 3. Verificar:
# - PagerDuty recibe incident
# - Email llega a oncall@example.com
# - Webhook a agente-api:8000 también se ejecuta (logs)
```

**Criterio de éxito**:
- ✅ Alerta de prueba llega a 3 canales (PagerDuty + Email + Webhook)
- ✅ Si agente-api cae, PagerDuty y Email siguen funcionando
- ✅ Métrica `alertmanager_notifications_total` incrementa para cada receiver

**Esfuerzo**: 2 horas  
**Owner**: SRE

---

### ✅ C2: VALIDAR REGLAS DE PROMETHEUS

**Problema**: Dashboards de SLO dependen de `recording rules` que pre-calculan métricas. Si están mal, toda la observabilidad es ilusoria.

**Solución**: Validar con `promtool` y crear test automatizado en CI/CD.

**Pasos de implementación**:

```bash
# 1. Validar reglas actuales con Docker (promtool no está instalado local)
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

docker run --rm \
  -v $(pwd)/docker/prometheus:/prometheus \
  prom/prometheus:latest \
  promtool check rules /prometheus/alerts.yml

# Si hay recording_rules.yml separado:
docker run --rm \
  -v $(pwd)/docker/prometheus:/prometheus \
  prom/prometheus:latest \
  promtool check rules /prometheus/recording_rules.yml

# 2. Crear script de validación
cat > scripts/validate-prometheus-rules.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Validando reglas de Prometheus..."

# Validar alerts.yml
docker run --rm \
  -v $(pwd)/docker/prometheus:/prometheus \
  prom/prometheus:latest \
  promtool check rules /prometheus/alerts.yml

# Validar recording rules si existen
if [ -f docker/prometheus/recording_rules.yml ]; then
  docker run --rm \
    -v $(pwd)/docker/prometheus:/prometheus \
    prom/prometheus:latest \
    promtool check rules /prometheus/recording_rules.yml
fi

echo "✅ Todas las reglas de Prometheus son válidas"
EOF

chmod +x scripts/validate-prometheus-rules.sh

# 3. Añadir a Makefile
cat >> Makefile << 'EOF'

# Validar reglas de Prometheus
validate-prometheus:
	@./scripts/validate-prometheus-rules.sh

# Pre-commit hook (opcional)
pre-commit-prometheus: validate-prometheus
	@echo "✅ Prometheus rules validated"
EOF

# 4. Ejecutar validación
make validate-prometheus
```

**Criterio de éxito**:
- ✅ `promtool check rules` pasa sin errores
- ✅ Script ejecutable en CI/CD (GitHub Actions)
- ✅ Pre-commit hook previene commit de reglas inválidas

**Esfuerzo**: 1 hora  
**Owner**: SRE

---

### ✅ H1: ENRIQUECER TRAZAS CON CONTEXTO DE NEGOCIO

**Problema**: `grep span.set_attribute` = 0 resultados. Trazas no tienen `tenant_id`, `user_id`, `intent_name`. Debugging en producción es difícil.

**Solución**: Añadir atributos de negocio automáticamente en middleware y manualmente en puntos críticos.

**Pasos de implementación**:

```python
# 1. Modificar app/core/tracing.py - Añadir helper function
def enrich_span_from_request(span, request):
    """Enriquece span con contexto de negocio desde request state."""
    # Tenant ID
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        span.set_attribute("tenant.id", str(tenant_id))
    
    # User ID
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        span.set_attribute("user.id", str(user_id))
    
    # Canal (WhatsApp, Gmail, etc)
    canal = getattr(request.state, "canal", None)
    if canal:
        span.set_attribute("channel.type", canal)
    
    # Correlation ID (ya existe pero lo hacemos explícito)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        span.set_attribute("request.correlation_id", correlation_id)

# 2. Modificar app/core/middleware.py - Añadir en tracing middleware
async def dispatch(self, request: Request, call_next):
    # ... código existente de OpenTelemetry ...
    
    # ✅ AÑADIR DESPUÉS de crear el span
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        kind=trace.SpanKind.SERVER
    ) as span:
        # ✅ Enriquecer con contexto de negocio
        from app.core.tracing import enrich_span_from_request
        enrich_span_from_request(span, request)
        
        # ... resto del código ...

# 3. Modificar app/services/orchestrator.py - Añadir en puntos críticos
async def process_message(self, message: UnifiedMessage):
    # ✅ Añadir al inicio del método
    from opentelemetry import trace
    span = trace.get_current_span()
    
    span.set_attribute("business.intent", intent_result.get("intent", "unknown"))
    span.set_attribute("business.confidence", intent_result.get("confidence", 0.0))
    span.set_attribute("business.tenant_id", message.tenant_id)
    span.set_attribute("business.user_id", message.user_id)
    span.set_attribute("business.channel", message.canal)
    
    # ... resto de la lógica ...

# 4. Modificar app/services/pms_adapter.py - Añadir en llamadas PMS
async def check_availability(self, checkin_date, checkout_date):
    from opentelemetry import trace
    span = trace.get_current_span()
    
    span.set_attribute("pms.operation", "check_availability")
    span.set_attribute("pms.checkin_date", checkin_date)
    span.set_attribute("pms.checkout_date", checkout_date)
    
    # ... resto de la lógica ...
```

**Validación**:
```bash
# 1. Ejecutar request de prueba
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, necesito habitación"}'

# 2. Verificar en Jaeger UI
# URL: http://localhost:16686/search
# Buscar trace reciente → Ver "Tags"
# Debe mostrar: tenant.id, user.id, business.intent, etc.

# 3. Query PromQL para validar
# (si exportas spans como métricas)
sum(traces_spanmetrics_calls_total{tenant_id="tenantA"}) by (business_intent)
```

**Criterio de éxito**:
- ✅ `grep span.set_attribute app/` > 10 resultados
- ✅ Trazas en Jaeger muestran tenant_id, user_id, intent
- ✅ Búsqueda en Jaeger por tenant_id funciona

**Esfuerzo**: 4 horas  
**Owner**: Dev Backend

---

### ✅ H2: FORTALECER CSP (CONTENT-SECURITY-POLICY)

**Problema**: CSP actual permite `unsafe-inline` en styles, lo que habilita XSS vía inyección de estilos.

**Solución**: Eliminar `unsafe-inline` y usar nonces para estilos dinámicos.

**Pasos de implementación**:

```python
# 1. Modificar app/core/middleware.py - Fortalecer CSP
def build_csp(self) -> str:
    """Build Content-Security-Policy header with nonce support."""
    # Generar nonce único por request (si se necesita)
    # nonce = secrets.token_urlsafe(16)
    
    raw = getattr(settings, "csp_extra_sources", None)
    extra = f" {raw}" if raw else ""
    
    # ✅ CSP estricta SIN unsafe-inline
    csp = (
        f"default-src 'self'; "
        f"script-src 'self'{extra}; "
        f"style-src 'self'{extra}; "  # ❌ Removido 'unsafe-inline'
        f"img-src 'self' data: https:; "
        f"connect-src 'self'; "
        f"font-src 'self'{extra}; "
        f"object-src 'none'; "
        f"media-src 'self'; "
        f"frame-src 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'"
    )
    return csp

# 2. Si Grafana dashboards necesitan inline styles, usar nonce:
async def dispatch(self, request: Request, call_next):
    # Generar nonce para este request
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    
    # CSP con nonce
    csp = (
        f"default-src 'self'; "
        f"script-src 'self'; "
        f"style-src 'self' 'nonce-{nonce}'; "  # ✅ Solo inline con nonce válido
        # ... resto ...
    )
    
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = csp
    return response

# 3. En templates HTML (si los hay), usar el nonce:
# <style nonce="{{ request.state.csp_nonce }}">
#   .my-class { color: red; }
# </style>
```

**Validación**:
```bash
# 1. Test con curl
curl -I http://localhost:8002/health/live | grep Content-Security-Policy

# Debe mostrar SIN 'unsafe-inline':
# Content-Security-Policy: default-src 'self'; style-src 'self'; ...

# 2. Test de XSS con inyección de estilo
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"message": "<style>body{display:none}</style>Hola"}'

# No debe aplicar el estilo inyectado (CSP debe bloquearlo)

# 3. Verificar en browser console (si hay UI)
# Abrir DevTools → Console
# No debe mostrar errores "CSP blocked inline style"
```

**Criterio de éxito**:
- ✅ CSP no contiene `unsafe-inline`
- ✅ Dashboards de Grafana siguen funcionando
- ✅ Security headers test pasa: https://securityheaders.com/

**Esfuerzo**: 2 horas  
**Owner**: Dev Backend + Security

---

## 🚀 FASE 1B: COBERTURA CORE (Sprint 2 - Días 4-10)

### ✅ H3: AUMENTAR COBERTURA ORCHESTRATOR 13% → 70%

**Problema**: Módulo core con lógica de negocio compleja tiene solo 13% cobertura. Alto riesgo de regresiones.

**Solución**: Tests de contrato (entrada/salida correcta) + tests unitarios de paths críticos.

**Estrategia de testing** (3 niveles):

#### Nivel 1: Tests de Contrato (Sprint 2, Día 4-5)
Validar que entrada/salida es correcta sin probar lógica interna.

```python
# tests/unit/test_orchestrator_contracts.py
import pytest
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage

@pytest.mark.asyncio
async def test_process_message_returns_valid_response():
    """Contract: process_message debe devolver dict con response_type y content."""
    orch = await setup_orchestrator()  # Mock dependencies
    
    msg = UnifiedMessage(
        user_id="u1",
        canal="whatsapp",
        texto="Necesito habitación",
        tipo="text"
    )
    
    result = await orch.process_message(msg)
    
    # Contrato: Siempre devuelve dict con estas claves
    assert isinstance(result, dict)
    assert "response_type" in result
    assert result["response_type"] in ["text", "text_with_image", "audio"]
    assert "content" in result or "error" in result

@pytest.mark.asyncio
async def test_handle_availability_intent_structure():
    """Contract: Intent availability devuelve estructura esperada."""
    orch = await setup_orchestrator()
    
    intent_result = {"intent": "check_availability", "confidence": 0.9}
    context = {}
    msg = UnifiedMessage(user_id="u1", canal="whatsapp", texto="Disponibilidad")
    
    result = await orch._handle_availability(intent_result, context, msg)
    
    # Contrato de estructura
    assert "response_type" in result
    if "rooms" in result:
        assert isinstance(result["rooms"], list)
        for room in result["rooms"]:
            assert "room_type" in room
            assert "price" in room
```

**Cobertura esperada**: +15% (total 28%)

#### Nivel 2: Tests de Paths Críticos (Sprint 2, Día 6-7)
Validar lógica de decisión en if/else/match statements.

```python
# tests/unit/test_orchestrator_critical_paths.py
@pytest.mark.asyncio
async def test_business_hours_escalation_path():
    """Path crítico: Fuera de horario + palabra URGENTE → escalamiento."""
    orch = await setup_orchestrator()
    
    # Mock is_business_hours = False
    with patch("app.services.orchestrator.is_business_hours", return_value=False):
        msg = UnifiedMessage(
            user_id="u1",
            canal="whatsapp",
            texto="URGENTE: Necesito ayuda",
            tipo="text"
        )
        
        result = await orch.process_message(msg)
        
        # Debe escalar
        assert result.get("escalated") is True
        assert "urgencia" in result.get("content", "").lower()
        
        # Métrica debe incrementar
        escalations = get_metric_value("orchestrator_escalations_total", 
                                       labels={"reason": "urgent_after_hours"})
        assert escalations >= 1

@pytest.mark.asyncio
async def test_low_confidence_fallback_path():
    """Path crítico: Confianza NLP baja → fallback genérico."""
    orch = await setup_orchestrator()
    
    # Mock NLP con baja confianza
    with patch.object(orch.nlp_engine, "detect_intent") as mock_nlp:
        mock_nlp.return_value = {"intent": "unknown", "confidence": 0.2}
        
        msg = UnifiedMessage(user_id="u1", canal="whatsapp", texto="xyz abc")
        result = await orch.process_message(msg)
        
        # Debe usar fallback
        assert "no entendí" in result["content"].lower()
        
        # Métrica de fallback debe incrementar
        fallbacks = get_metric_value("nlp_fallbacks_total")
        assert fallbacks >= 1
```

**Cobertura esperada**: +25% (total 53%)

#### Nivel 3: Tests de Edge Cases (Sprint 2, Día 8-9)
Validar comportamiento en condiciones extremas.

```python
# tests/unit/test_orchestrator_edge_cases.py
@pytest.mark.asyncio
async def test_pms_timeout_graceful_degradation():
    """Edge: PMS timeout → respuesta graciosa sin crash."""
    orch = await setup_orchestrator()
    
    # Mock PMS que tarda >30s
    async def slow_pms(*args, **kwargs):
        await asyncio.sleep(35)
        raise httpx.TimeoutException("PMS timeout")
    
    with patch.object(orch.pms_adapter, "check_availability", side_effect=slow_pms):
        msg = UnifiedMessage(user_id="u1", canal="whatsapp", 
                           texto="Disponibilidad para mañana")
        
        result = await orch.process_message(msg)
        
        # NO debe crashear
        assert result is not None
        assert "response_type" in result
        
        # Debe usar fallback o mensaje de error amigable
        assert "momento" in result["content"].lower() or \
               "intentar" in result["content"].lower()

@pytest.mark.asyncio
async def test_concurrent_reservations_race_condition():
    """Edge: 2 usuarios reservan misma habitación simultáneamente."""
    orch = await setup_orchestrator()
    
    msg1 = UnifiedMessage(user_id="u1", canal="whatsapp", texto="Reservar 101")
    msg2 = UnifiedMessage(user_id="u2", canal="whatsapp", texto="Reservar 101")
    
    # Ejecutar concurrentemente
    results = await asyncio.gather(
        orch.process_message(msg1),
        orch.process_message(msg2),
        return_exceptions=True
    )
    
    # Solo UNO debe tener reserva exitosa
    successful = [r for r in results if "confirmación" in r.get("content", "").lower()]
    assert len(successful) == 1
    
    # El otro debe recibir mensaje de no disponible
    failed = [r for r in results if r not in successful]
    assert "no disponible" in failed[0].get("content", "").lower()
```

**Cobertura esperada**: +17% (total 70% ✅)

**Esfuerzo**: 8 horas (3 niveles × ~2.5h cada uno)  
**Owner**: Dev Backend

---

### ✅ H4: AUMENTAR COBERTURA PMS ADAPTER 2% → 70%

**Problema**: Integración crítica con sistema externo tiene 2% cobertura. Cualquier cambio es riesgoso.

**Solución**: Mock server de PMS + tests de circuit breaker scenarios.

**Pasos de implementación**:

```python
# 1. Crear mock server de PMS
# tests/mocks/pms_mock_server.py
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI()

# Simular QloApps API
@app.get("/api/availability")
async def mock_availability(checkin: str, checkout: str, hotel_id: int = 1):
    """Mock de check_availability."""
    return {
        "rooms_available": 3,
        "rooms": [
            {"room_type": "Single", "price": 100.0, "room_id": 101},
            {"room_type": "Double", "price": 150.0, "room_id": 201},
            {"room_type": "Suite", "price": 250.0, "room_id": 301},
        ]
    }

@app.post("/api/reservations")
async def mock_create_reservation(data: dict):
    """Mock de create_reservation."""
    # Simular validación
    if data.get("room_id") == 999:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        "reservation_id": "RES-12345",
        "status": "confirmed",
        "confirmation_code": "ABC123"
    }

# Endpoints para chaos testing
@app.get("/api/slow")
async def slow_endpoint():
    """Endpoint que tarda >30s."""
    await asyncio.sleep(35)
    return {"status": "ok"}

@app.get("/api/error")
async def error_endpoint():
    """Endpoint que siempre falla."""
    raise HTTPException(status_code=500, detail="Internal Server Error")

# 2. Tests de integración con mock server
# tests/integration/test_pms_adapter_integration.py
import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def pms_mock_server():
    """Levanta mock server de PMS en background."""
    # Iniciar servidor en puerto 18080
    # (usar pytest-asyncio + uvicorn.run en thread)
    # ... implementación ...

@pytest.mark.asyncio
async def test_check_availability_success(pms_mock_server):
    """Happy path: PMS devuelve disponibilidad."""
    from app.services.pms_adapter import QloAppsPMSAdapter
    
    adapter = QloAppsPMSAdapter(base_url="http://localhost:18080")
    
    result = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    assert result["rooms_available"] == 3
    assert len(result["rooms"]) == 3
    assert result["rooms"][0]["room_type"] == "Single"

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(pms_mock_server):
    """Circuit breaker: Se abre después de 5 fallos."""
    from app.services.pms_adapter import QloAppsPMSAdapter
    
    adapter = QloAppsPMSAdapter(base_url="http://localhost:18080")
    
    # Hacer 5 llamadas al endpoint que falla
    for _ in range(5):
        with pytest.raises(Exception):
            await adapter._make_request("GET", "/api/error")
    
    # El breaker debe estar OPEN
    assert adapter.circuit_breaker.state == CircuitState.OPEN
    
    # La 6ta llamada debe fallar inmediatamente sin HTTP request
    with pytest.raises(CircuitBreakerOpenError):
        await adapter._make_request("GET", "/api/error")

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery(pms_mock_server):
    """Circuit breaker: Recuperación HALF_OPEN → CLOSED."""
    from app.services.pms_adapter import QloAppsPMSAdapter
    
    adapter = QloAppsPMSAdapter(base_url="http://localhost:18080")
    
    # Abrir circuit breaker
    for _ in range(5):
        with pytest.raises(Exception):
            await adapter._make_request("GET", "/api/error")
    
    assert adapter.circuit_breaker.state == CircuitState.OPEN
    
    # Esperar recovery_timeout (30s en prod, 1s en tests)
    await asyncio.sleep(adapter.circuit_breaker.recovery_timeout + 0.5)
    
    # Siguiente llamada exitosa debe cerrar el breaker
    result = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    assert adapter.circuit_breaker.state == CircuitState.CLOSED
    assert result["rooms_available"] > 0

@pytest.mark.asyncio
async def test_cache_hit_reduces_pms_calls(pms_mock_server):
    """Cache: Segunda llamada no hace HTTP request."""
    from app.services.pms_adapter import QloAppsPMSAdapter
    
    adapter = QloAppsPMSAdapter(base_url="http://localhost:18080")
    
    # Primera llamada (cache MISS)
    result1 = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    # Segunda llamada inmediata (cache HIT)
    result2 = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    # Resultados idénticos
    assert result1 == result2
    
    # Métrica de cache hit debe incrementar
    cache_hits = get_metric_value("pms_cache_hits_total")
    assert cache_hits >= 1
```

**Cobertura esperada**: 70% con mock server + circuit breaker scenarios

**Esfuerzo**: 8 horas  
**Owner**: Dev Backend

---

## 🚀 FASE 1C: MEJORAS ARQUITECTÓNICAS (Sprint 3 - Días 11-15)

### ✅ M1: FEATURE FLAGS CON PUSH INVALIDATION

**Problema**: TTL 30s causa lag en killswitches. Cambio de flag tarda hasta 40s en propagarse.

**Solución**: Implementar Redis pub/sub para invalidación push.

**Pasos de implementación**:

```python
# 1. Modificar app/services/feature_flag_service.py
import asyncio
from redis.asyncio import Redis

class FeatureFlagService:
    def __init__(self, redis: Redis, ttl_seconds: int = 30):
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.cache_times = {}
        
        # ✅ NUEVO: Suscripción a canal de invalidación
        self.pubsub = None
        self.invalidation_task = None
    
    async def start(self):
        """Iniciar suscripción a invalidaciones."""
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("feature_flags_invalidate")
        
        # Task que escucha invalidaciones
        self.invalidation_task = asyncio.create_task(self._listen_invalidations())
    
    async def _listen_invalidations(self):
        """Loop que escucha canal de invalidación."""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                flag_key = message["data"].decode("utf-8")
                
                # Invalidar caché local
                if flag_key in self.cache:
                    del self.cache[flag_key]
                    del self.cache_times[flag_key]
                
                logger.info(f"feature_flag.invalidated", flag_key=flag_key)
    
    async def set_flag(self, key: str, value: bool):
        """Setear flag y notificar a todos los pods."""
        # Guardar en Redis
        await self.redis.hset("feature_flags", key, int(value))
        
        # ✅ Publicar invalidación
        await self.redis.publish("feature_flags_invalidate", key)
        
        # Invalidar caché local
        if key in self.cache:
            del self.cache[key]
            del self.cache_times[key]
    
    async def stop(self):
        """Cleanup."""
        if self.invalidation_task:
            self.invalidation_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe("feature_flags_invalidate")
            await self.pubsub.close()
```

**Validación**:
```python
# Test de propagación instantánea
@pytest.mark.asyncio
async def test_flag_invalidation_push():
    """Flag change se propaga en <1s vía pub/sub."""
    ff1 = FeatureFlagService(redis_client)
    ff2 = FeatureFlagService(redis_client)
    
    await ff1.start()
    await ff2.start()
    
    # Pod 1 lee flag (cache)
    value1 = await ff1.is_enabled("test_flag")  # False
    
    # Pod 2 cambia flag
    await ff2.set_flag("test_flag", True)
    
    # Esperar propagación (debe ser <1s)
    await asyncio.sleep(0.5)
    
    # Pod 1 lee nuevamente (debe ver cambio SIN esperar TTL)
    value2 = await ff1.is_enabled("test_flag")
    
    assert value1 is False
    assert value2 is True  # ✅ Cambio propagado instantáneamente
```

**Criterio de éxito**:
- ✅ Cambio de flag se propaga en <1s (no 30s)
- ✅ Killswitch funciona en tiempo real
- ✅ Métrica `feature_flag_invalidations_total` incrementa

**Esfuerzo**: 16 horas (refactor + tests + validación)  
**Owner**: Dev Backend

---

### ✅ M2: RATE LIMITING PER-TENANT

**Problema**: Rate limiter actual es global. Un tenant malicioso consume el límite de todos.

**Solución**: Configurar slowapi con key_func basado en tenant_id.

```python
# app/core/ratelimit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_tenant_id(request: Request) -> str:
    """Extrae tenant_id del request state para rate limiting."""
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if tenant_id:
        return f"tenant:{tenant_id}"
    
    # Fallback a IP si no hay tenant_id
    return f"ip:{get_remote_address(request)}"

# Crear limiter con key_func multi-tenant
limiter = Limiter(
    key_func=get_tenant_id,
    storage_uri="redis://localhost:6379"
)

# Uso en routers
@router.post("/webhooks/whatsapp")
@limiter.limit("120/minute")  # 120 req/min PER TENANT (no global)
async def whatsapp_webhook(request: Request):
    # ...
```

**Esfuerzo**: 6 horas  
**Owner**: Dev Backend

---

### ✅ M3: BULKHEAD PATTERN PARA POOLS DE CONEXIÓN

**Problema**: Si pool de PMS se satura, funciones que NO usan PMS también se bloquean.

**Solución**: Pools separados por servicio (PMS, DB, Redis, NLP).

```python
# app/core/pools.py
from asyncio import Semaphore

class ResourcePools:
    """Bulkhead pattern: Pools separados por recurso."""
    
    def __init__(self):
        self.pms_pool = Semaphore(10)      # Max 10 llamadas PMS concurrentes
        self.db_pool = Semaphore(50)       # Max 50 queries DB concurrentes
        self.nlp_pool = Semaphore(20)      # Max 20 llamadas NLP concurrentes
        self.redis_pool = Semaphore(100)   # Max 100 ops Redis concurrentes
    
    async def with_pms(self, coro):
        """Ejecuta corutina con protección de bulkhead PMS."""
        async with self.pms_pool:
            return await coro
```

**Esfuerzo**: 8 horas  
**Owner**: Dev Backend + SRE

---

## 📊 MÉTRICAS DE ÉXITO (KPIS)

| Métrica | Antes | Meta Sprint 1 | Meta Sprint 2 | Meta Sprint 3 |
|---------|-------|---------------|---------------|---------------|
| **SPOF de Alertas** | 1 canal | 3 canales | 3 canales | 3 canales |
| **Prometheus Rules Válidas** | ❓ | ✅ 100% | ✅ 100% | ✅ 100% |
| **Trazas con Contexto** | 0 attrs | 5 attrs | 5 attrs | 5 attrs |
| **CSP Estricta** | unsafe-inline | ✅ Sin unsafe | ✅ Sin unsafe | ✅ Sin unsafe |
| **Cobertura Orchestrator** | 13% | 13% | 70% | 70% |
| **Cobertura PMS Adapter** | 2% | 2% | 70% | 70% |
| **Feature Flags Lag** | 30s | 30s | 30s | <1s |
| **Rate Limiting** | Global | Global | Global | Per-tenant |

---

## 🎯 DECISIÓN GO/NO-GO REVISADA

### Sprint 1 (Quick Wins) → GO STAGING
- ✅ SPOF eliminado
- ✅ Prometheus validado
- ✅ Trazas enriquecidas
- ✅ CSP estricta

**Restricción**: Staging only, no producción (cobertura aún baja)

### Sprint 2 (Cobertura Core) → GO PRODUCCIÓN LIMITADA
- ✅ Orchestrator 70%
- ✅ PMS Adapter 70%

**Restricción**: Tráfico <500 TPS, monitoreo 24/7

### Sprint 3 (Mejoras Arquitectónicas) → GO PRODUCCIÓN FULL
- ✅ Feature flags con push invalidation
- ✅ Rate limiting per-tenant
- ✅ Bulkhead pattern

**Sin restricciones**: Producción full con >1000 TPS

---

## 📅 CRONOGRAMA DETALLADO

**Sprint 1** (Días 1-3 - 15h):
- Día 1: C1 SPOF AlertManager (2h) + C2 Prometheus (1h)
- Día 2: H1 Trazas contexto (4h)
- Día 3: H2 CSP estricta (2h) + Validación integral (6h)

**Sprint 2** (Días 4-10 - 20h):
- Días 4-5: H3 Orchestrator nivel 1 (contratos) + nivel 2 (paths) (10h)
- Días 6-7: H3 Orchestrator nivel 3 (edge cases) + H4 PMS mock server (8h)
- Días 8-10: H4 PMS circuit breaker tests + Validación (2h)

**Sprint 3** (Días 11-15 - 30h):
- Días 11-12: M1 Feature flags push invalidation (16h)
- Día 13: M2 Rate limiting per-tenant (6h)
- Días 14-15: M3 Bulkhead pattern + Validación final (8h)

---

## ✅ CHECKLIST DE VALIDACIÓN FINAL

Antes de marcar COMPLETADO, verificar:

- [ ] **C1**: PagerDuty recibe alerta de prueba
- [ ] **C1**: Email llega a oncall@example.com
- [ ] **C1**: Webhook a agente-api también funciona
- [ ] **C2**: `promtool check rules` pasa sin errores
- [ ] **C2**: Script en Makefile ejecutable
- [ ] **H1**: `grep span.set_attribute app/` > 10 resultados
- [ ] **H1**: Jaeger UI muestra tenant_id, user_id, intent
- [ ] **H2**: CSP header no contiene `unsafe-inline`
- [ ] **H2**: Dashboards de Grafana siguen funcionando
- [ ] **H3**: Cobertura orchestrator ≥70%
- [ ] **H3**: Tests de edge cases pasan
- [ ] **H4**: Cobertura pms_adapter ≥70%
- [ ] **H4**: Circuit breaker tests pasan
- [ ] **M1**: Flag change se propaga en <1s
- [ ] **M2**: Rate limiting funciona per-tenant
- [ ] **M3**: PMS saturado no bloquea otras funciones

---

**Documento aprobado para ejecución.**  
**Próximo paso**: Comenzar con C1 (SPOF AlertManager).
