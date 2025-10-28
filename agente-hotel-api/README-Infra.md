# [PROMPT GA-01] Documentación de Infraestructura

## Guía de Alineación (Resumen)

Para iniciar una sesión de trabajo consistente y evitar desviaciones:

1. Ejecutar `bash agente-hotel-api/scripts/session-start.sh` (imprime estado rápido).
2. Revisar `docs/STATUS_SNAPSHOT.md` (generar previo con `bash agente-hotel-api/scripts/generate-status-summary.sh`).
3. Confirmar reglas en `docs/playbook/WORKING_AGREEMENT.md`.
4. Validar que el item a trabajar cumple Definition of Ready (`CONTRIBUTING.md`).
5. Al abrir PR: adjuntar secciones aplicables de `docs/DOD_CHECKLIST.md`.

Artefactos clave de alineación:
- `CONTRIBUTING.md`
- `docs/DOD_CHECKLIST.md`
- `docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md`
- `docs/playbook/WORKING_AGREEMENT.md`
- `.playbook/project_config.yml`
- Preflight CI: `.github/workflows/preflight.yml` (genera `.playbook/preflight_report.json` y bloquea si NO_GO / blocking issues)

### Preflight local
Ejecutar:
```
make preflight READINESS_SCORE=7.5 MVP_SCORE=7.0 SECURITY_GATE=PASS CHANGE_COMPLEXITY=medium
```
Genera `.playbook/preflight_report.json` y aplica reglas de modo (A/B/C).

### Canary Diff (Baseline vs Canary)
Script: `scripts/canary-deploy.sh`
Genera reporte: `.playbook/canary_diff_report.json`
Parámetros principales (env overrides):
- `P95_INCREASE_LIMIT` (default 1.10)
- `ERR_INCREASE_LIMIT` (default 1.50)
- `ERR_ABS_MIN` (default 0.005)
- `BASELINE_RANGE` / `CANARY_RANGE` (ventanas PromQL)

Uso rápido:
```
make canary-diff
# o manual
bash scripts/canary-deploy.sh staging $(git rev-parse --short HEAD)
```
Estado PASS/FAIL se refleja en `status` y razones en `fail_reasons`.

### Tenancy Dinámico
- Modelos: `Tenant`, `TenantUserIdentifier` (bootstrap automático, migraciones futuras con Alembic recomendado).
- Servicio: `dynamic_tenant_service` (caché + refresh periódico). Flag `tenancy.dynamic.enabled`.
- Métricas:
  - `tenant_resolution_total{result=hit|default|miss_strict|provided}`
  - `tenants_active_total`, `tenant_identifiers_cached_total`
  - `tenant_refresh_latency_seconds`
- Endpoints Admin:
  - `GET /admin/tenants`
  - `POST /admin/tenants` (body: tenant_id,name)
  - `POST /admin/tenants/{tenant_id}/identifiers` (body: identifier)
  - `DELETE /admin/tenants/{tenant_id}/identifiers/{identifier}`
  - `PATCH /admin/tenants/{tenant_id}` (body: status=active|inactive)
  - `POST /admin/tenants/refresh`

### Mensajes Interactivos (WhatsApp)
- Flag de función: `features.interactive_messages`
  - Default: `false` en entornos de prueba (permite aserciones deterministas en texto plano).
  - Recomendado: `true` en staging/producción para habilitar botones/listas interactivas.
- Activación vía Redis (hash `feature_flags`):
  - `HSET feature_flags features.interactive_messages 1`
- Comportamiento:
  - La respuesta puede ser `interactive_buttons` o `interactive_buttons_with_image` si hay imagen disponible.
  - El webhook de WhatsApp (en modo test) devuelve eco de `response_type` y `content` para validación.
  - Métricas: se registran en Prometheus junto con el resto del flujo del orquestador.

### Gestión y observabilidad de Feature Flags
- Lectura (admin, auth requerida): `GET /admin/feature-flags` → `{ "flags": { ... } }`
- Métrica: `feature_flag_enabled{flag}` sirve como gauge (1/0) y se actualiza al leer/usar flags.


## Stack Tecnológico

- **Orquestación:** Docker Compose
- **Reverse Proxy:** NGINX
- **Servicios:**
  - `agente-api`: Aplicación FastAPI.
  - `qloapps`: PMS.
  - `postgres`: Base de datos para el agente.
  - `mysql`: Base de datos para QloApps.
  - `redis`: Cache y locks.
  - `prometheus`, `grafana`, `alertmanager`: Stack de monitorización.

## Redes

- `frontend_network`: Expuesta al exterior, para NGINX.
- `backend_network`: Red interna para la comunicación entre servicios.

## Comandos

- `make docker-up`: Inicia el stack.
- `make docker-down`: Detiene el stack.
- `make health`: Verifica la salud de los servicios.
- `make backup`: Crea un backup de las bases de datos.

## Métricas y Observabilidad

La API expone métricas Prometheus en `/metrics` (router `metrics.py`). Métricas relevantes:

- HTTP (definidas/globales):
  - `http_requests_total{method,endpoint,status_code}`
  - `request_duration_seconds{method,endpoint}` (Histogram)
  - `active_connections` (Gauge)

- PMS Adapter (`app/services/pms_adapter.py`):
  - `pms_api_latency_seconds{endpoint,method}` (Histogram)
  - `pms_operations_total{operation,status}`
  - `pms_errors_total{operation,error_type}`
  - `pms_cache_hits_total`, `pms_cache_misses_total`
  - `pms_cache_hit_ratio` (recording rule 5m)
  - `pms_circuit_breaker_state` (0=closed, 1=open, 2=half-open)

- Reintentos (`app/core/retry.py`):
  - `retry_attempts_total{operation,exception}`

Ejemplos PromQL:

```promql
# Tasa de errores HTTP 5xx por endpoint (5m)
sum by (endpoint) (rate(http_requests_total{status_code=~"5.."}[5m]))

# Latencia p95 de PMS availability (5m)
histogram_quantile(0.95, sum by (le) (rate(pms_api_latency_seconds_bucket{endpoint="/api/availability"}[5m])))

# Conteo de reintentos por operación (10m)
sum by (operation) (rate(retry_attempts_total[10m]))

# Estado del circuit breaker (último valor)
max_over_time(pms_circuit_breaker_state[1m])
```

## Política de Rate Limiting

Se aplica limitación por ruta usando SlowAPI:

- `/webhooks/whatsapp`:
  - GET verificación: `60/minute`
  - POST eventos: `120/minute`
- `/admin/dashboard`: `30/minute`
- `/admin/tenants/refresh`: `30/minute`
- `/admin/tenants`: `60/minute`

Implementación:

- Decorador dinámico `app/core/ratelimit.py` que usa `request.app.state.limiter`.
- En `debug=True` el limit se omite para no requerir Redis en desarrollo/pruebas.
- En producción, `app/main.py` configura `app.state.limiter` con Redis (`settings.redis_url`).
- Response HTTP 429 cuando se excede el límite (incluye headers `Retry-After`).

Pruebas:

- `tests/integration/test_rate_limit_and_signatures.py` valida firmas, content-type y límites en múltiples endpoints.

## Validación de Firmas (Webhook Security)

### WhatsApp Webhook Signature

El endpoint `/webhooks/whatsapp` valida firmas HMAC-SHA256:

**Header requerido**: `X-Hub-Signature-256`

**Formato**: `sha256=<hexdigest>`

**Ejemplo de validación (Python)**:
```python
import hmac
import hashlib

# Payload bytes recibido
body = request.body

# Secret desde settings (configurado en .env como WHATSAPP_APP_SECRET)
app_secret = settings.whatsapp_app_secret.get_secret_value()

# Generar firma esperada
expected_sig = hmac.new(
    app_secret.encode(), 
    body, 
    hashlib.sha256
).hexdigest()

# Comparar con firma enviada (sin prefijo "sha256=")
received_sig = request.headers.get("X-Hub-Signature-256", "").replace("sha256=", "")

# Validación segura contra timing attacks
if not hmac.compare_digest(received_sig, expected_sig):
    return 401 Unauthorized
```

**Flujo de validación**:
1. Extraer header `X-Hub-Signature-256`.
2. Remover prefijo `sha256=` para obtener valor hex.
3. Calcular HMAC-SHA256 del body con app secret.
4. Comparar usando `hmac.compare_digest()` (protege contra timing attacks).
5. Si no coincide, retornar 401 antes de procesar.

**Validaciones adicionales** (después de signature):
- Content-Type: Debe ser `application/json` (415 si no).
- Tamaño de payload: Máximo 1 MB (413 si excede).
- JSON válido: Parseable como JSON (400 si inválido).

**Cadena de validación** (orden es crítico por seguridad):
```
[1] Firma HMAC-SHA256 (401) 
    ↓
[2] Content-Type (415)
    ↓
[3] Tamaño payload (413)
    ↓
[4] JSON parsing (400)
    ↓
[5] Rate limit (429)
    ↓
[6] Procesamiento de negocio
```

**Cómo testear localmente**:
```bash
#!/bin/bash
ENDPOINT="http://localhost:8002/webhooks/whatsapp"
SECRET="your-whatsapp-app-secret"
PAYLOAD='{"object":"whatsapp_business_account","entry":[]}'

# Generar firma
SIG="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hex | cut -d' ' -f2)"

# Enviar con firma válida
curl -X POST "$ENDPOINT" \
  -H "X-Hub-Signature-256: $SIG" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# Enviar con firma inválida (esperar 401)
curl -X POST "$ENDPOINT" \
  -H "X-Hub-Signature-256: sha256=0000000000000000000000000000000000000000000000000000000000000000" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

### Endpoints Protegidos

**Admin endpoints** (`/admin/*`):
- Requieren autenticación vía `Authorization: Bearer <token>` (JWT).
- No usan validación de firma (tokens son los mecanismos de seguridad).
- Rate limiting aplicado después de auth.

**Public webhooks** (`/webhooks/whatsapp`):
- Validación de firma (no requieren Bearer token).
- Rate limiting aplicado después de validación.

## Variables de Entorno Clave

- App y entorno:
  - `ENVIRONMENT` (development | production)
  - `DEBUG` (true/false)
  - `SECRET_KEY`

- Base de datos:
  - `POSTGRES_URL` (p.ej. `postgresql+asyncpg://user:pass@postgres:5432/db`)

- Redis (cache/locks/rate limit):
  - `REDIS_URL` (p.ej. `redis://:password@redis:6379/0`)

- WhatsApp:
  - `WHATSAPP_ACCESS_TOKEN`
  - `WHATSAPP_PHONE_NUMBER_ID`
  - `WHATSAPP_VERIFY_TOKEN`
  - `WHATSAPP_APP_SECRET` (usado para verificar firma `X-Hub-Signature-256`)

- Gmail:
  - `GMAIL_USERNAME`
  - `GMAIL_APP_PASSWORD`

Notas:
- En producción, los secretos son validados y la app no inicia si mantienen valores dummy.
- El rate limiter usa `app.state.limiter` con `storage_uri` derivado de `REDIS_URL`. En debug/tests se puede usar `memory://`.

- Alertmanager:
  - Lee variables desde `.env` (docker-compose `env_file`) para expandir placeholders en `config.yml`.
  - Variables soportadas (si usás receivers de ejemplo):
    - `SLACK_WEBHOOK_URL`, `ALERT_EMAIL_TO`, `ALERT_EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.

## Alertas (Prometheus/Alertmanager)

- Reglas definidas en `docker/prometheus/alerts.yml` y cargadas por `prometheus.yml`.
- Enrutadas a Alertmanager (ver `docker/alertmanager/config.yml`).
- Alertas incluidas:
  - `HighHttp5xxRate` (tasa de 5xx > 0.1 rps por endpoint, 5m)
  - `HighWebhook429Rate` (tasa de 429 en `/webhooks/whatsapp` > 0.2 rps, 5m)
  - `HighPmsLatencyP95` (p95 PMS > 1s, 10m)
  - `CircuitBreakerOpen` (CB > 0 por 2m)
  - `DependencyDown` (readiness_up < 1 con checks recientes, 2m, warning)
  - `OrchestratorHighErrorRateWarning` (error rate por intent > 5% con piso de tráfico > 0.2 rps, 10m)
  - `OrchestratorHighErrorRateCritical` (error rate por intent > 20% con piso de tráfico > 0.5 rps, 5m)
  - `OrchestratorHighLatencyP95` (p95 del orquestador > 2s por 10m)
  - `OrchestratorSLODegradationWarning` (success rate global < 99% por 30m con tráfico global > 0.5 rps)
  - `OrchestratorSLODegradationCritical` (success rate global < 97% por 10m con tráfico global > 0.5 rps)
  - `OrchestratorSLOBurnRateWarning` (burn rate fast>2 & slow>1 con tráfico global > 0.5 rps)
  - `OrchestratorSLOBurnRateCritical` (burn rate fast2>14.4 & slow2>6 con tráfico global > 0.5 rps)
  - `OrchestratorSLOBudgetExhaustForecastWarning` (proyección agotamiento <12h)
  - `OrchestratorSLOBudgetExhaustForecastCritical` (proyección agotamiento <6h)
  - `PmsCacheHitRatioLowWarning` (ratio <70% con actividad >0.2 ops/s por 15m)
  - `PmsCacheHitRatioLowCritical` (ratio <50% con actividad >0.2 ops/s por 10m)

Ajustes:
  - Editar umbrales/ventanas en `alerts.yml` según tráfico real.
  - Ajustar los pisos de tráfico (`orchestrator_message_rate_all > 0.5`) si la volumetría real es menor o mayor.
  - Añadir `receivers` en Alertmanager para email/Slack/PagerDuty.

Receivers de ejemplo:
- En `docker/alertmanager/config.yml` hay ejemplos comentados para Slack (webhook) y Email (SMTP). Para habilitarlos:
  1) Define variables en `.env` (p.ej. `SLACK_WEBHOOK_URL`, `ALERT_EMAIL_TO`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, etc.).
  2) Descomenta el bloque deseado y ajusta `route.routes` para rutar por `severity`.
  3) Reinicia solo Alertmanager o todo el stack.

Autoconfiguración por variables de entorno:
- El servicio `alertmanager` usa un entrypoint que genera `/etc/alertmanager/generated.yml` en runtime según `.env`:
  - Si `SLACK_WEBHOOK_URL` está definido, crea receiver `slack` y ruta `severity=critical` → `slack`.
  - Si `ALERT_EMAIL_TO` y `SMTP_*` están definidos, crea receiver `email` y ruta `severity=warning` → `email`.
  - Siempre deja `receiver: "null"` como default, así no falla si faltan variables.
- Ver config efectiva en logs de Alertmanager (el entrypoint imprime el YAML generado) o dentro del contenedor.
  - Inspección rápida: `docker compose logs alertmanager | sed -n '/^# generated by entrypoint.sh/,$p'`
  - Dentro del contenedor: `docker exec -it agente_alertmanager sh -c 'cat /etc/alertmanager/generated.yml'`

Pruebas de alertas (opcional):
- 429 en Webhook (dispara `HighWebhook429Rate`):
  - Ejecuta: `make test-alert-429`
  - Nota: la alerta usa ventana de 5m; espera a que la tasa sostenga el umbral.
- Alerta sintética crítica (rápida y reversible):
  - Usa archivo adicional `docker/prometheus/alerts-extra.yml` (se carga automáticamente por Prometheus).
  - Activar: `make alerts-enable-test` (crea regla AlwaysFiring y reinicia Prometheus/Alertmanager).
  - Verificar: `make alertmanager-alerts` (lista alertas activas) y/o revisa tu receiver (Slack/Email).
  - Desactivar: `make alerts-disable-test` (vacía alerts-extra.yml y reinicia servicios).

Inspección rápida:
- Reglas cargadas en Prometheus: `make prometheus-rules-status`
- Config generado de Alertmanager: `make alertmanager-config`

## Parametrización de SLO

El objetivo SLO (por defecto 99%) se controla con la variable de entorno `SLO_TARGET` (por ejemplo `SLO_TARGET=99.5`). En el entrypoint `prom-entrypoint.sh` se calcula el error budget fraction (`BUDGET_FRACTION = 1 - SLO_TARGET/100`) y se sustituye en la plantilla `recording_rules.tmpl.yml` generando `generated/recording_rules.yml`.

Variables relevantes:
 - `SLO_TARGET`: Porcentaje de éxito deseado (float). Default: 99.0
 - `ERROR_BUDGET_FRACTION`: (Opcional) Override manual del error budget (si se define, ignora `SLO_TARGET`).
 - `SLO_TRAFFIC_FLOOR`: Piso de tráfico global (rps) para evaluar alertas SLO/predicción. Default: 0.5

Cambiar SLO:
1. Editar `.env` y setear `SLO_TARGET=99.2` (ejemplo).
2. Reiniciar solo Prometheus: `docker compose restart prometheus` (el entrypoint regenerará reglas).
3. Verificar: `make prometheus-rules-status | grep orchestrator_burn_rate_fast` muestra reglas regeneradas.

Pisos de tráfico SLO:
- Las alertas usan `orchestrator_message_rate_all > orchestrator_slo_traffic_floor` (derivado de `SLO_TRAFFIC_FLOOR`) para evitar ruido en bajo volumen.

Métrica auxiliar añadida:
- `orchestrator_message_rate_all`: suma global de `rate(orchestrator_messages_total[5m])`, usada en alertas SLO.

Métricas SLO / Error Budget adicionales:
- `orchestrator_slo_target`
- `orchestrator_error_budget_fraction`
- `orchestrator_error_budget_used_ratio_30m`
- `orchestrator_error_budget_remaining_ratio_30m`
- `orchestrator_error_budget_hours_to_exhaust_fast`
- `orchestrator_error_budget_hours_to_exhaust_slow`

## Métricas de Cache PMS

Recording rule:

```promql
pms_cache_hit_ratio = sum(rate(pms_cache_hits_total[5m])) / clamp_min(sum(rate(pms_cache_hits_total[5m])) + sum(rate(pms_cache_misses_total[5m])), 0.000001)
```

Interpretación:
- Objetivo saludable típico: >0.8 (ajustar según patrón de acceso real).
- Alerta warning dispara <0.7 (15m) y critical <0.5 (10m) siempre que exista actividad de cache >0.2 ops/s (para evitar ruido en horas de baja demanda).
- Paneles añadidos en dashboard "Agente - Overview":
  - Stat: "PMS Cache Hit Ratio" (panel id 21)
  - Serie: "PMS Cache Ops (hits vs misses)" (panel id 22)

Acciones ante degradación (ver runbook `PmsCacheHitRatio` a añadir en manual de operaciones):
1. Revisar TTL excesivamente corto o invalidaciones masivas (`_invalidate_cache_pattern`).
2. Verificar crecimiento de misses correlacionado con despliegue reciente.
3. Analizar si hay cardinalidad alta de keys (ej. inclusión de parámetros poco relevantes en cache_key).
4. Realizar warm-up manual para endpoints críticos si la latencia PMS sube simultáneamente.

## Métricas Predictivas Circuit Breaker PMS

Métricas instrumentadas para anticipar la apertura del breaker y reducir tiempo en estado OPEN:

Primitivas:
- `pms_circuit_breaker_calls_total{state,result}`: Conteo de llamadas (state previo a la ejecución; result=success|failure).
- `pms_circuit_breaker_failure_streak`: Racha de fallos consecutivos actual.
- `pms_circuit_breaker_state`: 0=closed,1=open,2=half-open.

Recording rules derivadas:
```promql
# Ratios multi-ventana
pms_cb_failure_ratio_1m = sum(rate(pms_circuit_breaker_calls_total{result="failure"}[1m])) / clamp_min(sum(rate(pms_circuit_breaker_calls_total[1m])), 0.000001)
pms_cb_failure_ratio_5m = sum(rate(pms_circuit_breaker_calls_total{result="failure"}[5m])) / clamp_min(sum(rate(pms_circuit_breaker_calls_total[5m])), 0.000001)
pms_cb_failure_ratio_15m = sum(rate(pms_circuit_breaker_calls_total{result="failure"}[15m])) / clamp_min(sum(rate(pms_circuit_breaker_calls_total[15m])), 0.000001)

# Fracción de la racha vs threshold (threshold actual =5)
pms_cb_failure_streak_fraction = pms_circuit_breaker_failure_streak / 5

# Velocidad de crecimiento de la racha (failures/seg)
pms_cb_failure_streak_rate = rate(pms_circuit_breaker_failure_streak[5m])

# Estimación de minutos hasta apertura si la racha continúa creciendo al ritmo actual
pms_cb_minutes_to_open_estimate = clamp_min((5 - pms_circuit_breaker_failure_streak) / clamp_min(pms_cb_failure_streak_rate, 0.000001) / 60, 0)

# Señal booleana suavizada de riesgo inminente
pms_cb_risk_imminent_raw = (pms_cb_failure_streak_fraction >= 0.6) * (pms_cb_failure_ratio_1m > 0.5)
pms_cb_risk_imminent = avg_over_time(pms_cb_risk_imminent_raw[3m])
```

Alertas predictivas:
- `PmsCircuitBreakerImminentOpenWarning`: Riesgo inminente (racha >=60%, ratios cortos elevados) por 3m.
- `PmsCircuitBreakerImminentOpenCritical`: Racha >=80% y ratios altos (1m/5m) por 2m.

Interpretación / Operativa:
1. Ver panel de latencia `PMS API latency p95` y correlacionar con incremento de fallos.
2. Revisar tipo de errores (panel `PMS Errors by type`). Si predominan timeouts, considerar aumentar ligeramente `read` timeout temporalmente.
3. Validar conectividad y salud upstream (PMS) antes de modificar parámetros locales.
4. Si `minutes_to_open_estimate` cae <1 y el servicio upstream está degradado, aplicar mitigación: reducir fan-out de llamadas (limitar intents que consultan disponibilidad) y activar respuestas degradadas.
5. Post mortem: ajustar `failure_threshold` si se detectan falsos positivos repetidos, o tunear timeouts para reducir fallos transitorios.

Buenas prácticas:
- Evitar usar únicamente la racha: los failure ratios multi-ventana dan contexto de persistencia vs ráfagas cortas.
- Usar la señal suavizada `pms_cb_risk_imminent` para paneles (reduce flapping visual) pero mantener condiciones más estrictas en las alertas.

## Dashboards Grafana

- Carpeta: "Agente Hotel" (provisionada automáticamente).
- Dashboards:
  - `Alertas - Overview` (`docker/grafana/dashboards/alerts-overview.json`):
    - KPIs de alertas activas (total, críticas, warning).
    - Distribución por severidad.
    - Detalle de alertas firing y tiempo reciente en estado firing por regla.
  - `Agente - Overview` (`docker/grafana/dashboards/agente-overview.json`):
    - Latencias de PMS (p95), requests HTTP y otras métricas generales.
    - Paneles del Orchestrator: p95 por intent, tasa/porcentaje de errores por intent, volumen de mensajes y estado del Circuit Breaker.
    - Paneles SLO: SLO target, error budget fraction, success rate global, burn rates multi-ventana, budget usado/restante y horas hasta agotarlo.
  - `Webhooks - Rate Limit` (`docker/grafana/dashboards/webhooks-rate-limit.json`):
    - Enfoque en métricas de `/webhooks/whatsapp` y códigos 429.
  - `Readiness & Dependencies` (`docker/grafana/dashboards/readiness-overview.json`):
    - Gauge por dependencia (`dependency_up{name}`)
    - Estado global (`readiness_up`)
    - Serie temporal de readiness
  - `SLO Health` (`docker/grafana/dashboards/slo-health.json`):
    - SLO target, success rate, budget usado/restante.
    - Burn rates multi ventana.
    - Horas hasta agotar presupuesto.
    - Top intents por error% y p95, tasa global.

## Métricas de Readiness

La ruta `/health/ready` ahora actualiza métricas Prometheus para facilitar observabilidad:

- `dependency_up{name}` (Gauge): 1 si la dependencia está OK (database, redis, pms), 0 si falla.
- `readiness_up` (Gauge): 1 si todas las dependencias están OK, 0 si alguna falla.
- `readiness_last_check_timestamp` (Gauge): timestamp epoch del último check.

Alerta relacionada:

- `DependencyDown` (warning): `readiness_up < 1` durante más de 2m. Revisar `/health/ready` y los `dependency_up` para diagnóstico rápido.

## Security Scanning

El proyecto incluye herramientas de escaneo de seguridad integradas:

### Trivy Scanning
- **Fast scan**: `make security-fast` - Solo vulnerabilidades HIGH/CRITICAL + secrets
- **Full scan**: `make security-scan` - Ejecuta `scripts/security-scan.sh` con reporte completo
- **CI Integration**: El pipeline CI ejecuta `security-fast` automáticamente
- **Docker image scan**: `make docker-vulnerability-scan` - Escanea imagen construida

## Docker Hardening

### Security Features
- **Non-root user**: Imagen ejecuta como `appuser:1000` (no root)
- **Minimal attack surface**: Solo dependencias runtime necesarias
- **Security updates**: Actualizaciones de seguridad en build time
- **Health checks**: Health check personalizado cada 15s
- **Build optimization**: Multi-stage build + .dockerignore

### Build Targets
```bash
make docker-build-hardened    # Build con hardening + test health check
make docker-vulnerability-scan # Escaneo de vulnerabilidades imagen
```

### Production Image
Usa `requirements-prod.txt` que excluye dependencias de desarrollo para reducir superficie de ataque.

## Synthetic Monitoring

### Health Check Sintético
Script `scripts/synthetic-health-check.sh` para monitoreo externo:

```bash
# Local test
make synthetic-health-check

# Production monitoring (vía cron)
HEALTH_CHECK_URL=https://api.hotel.com \
SLACK_WEBHOOK=https://hooks.slack.com/... \
./scripts/synthetic-health-check.sh
```

**Environment Variables:**
- `HEALTH_CHECK_URL`: Base URL a verificar
- `TIMEOUT`: Timeout por request (default: 10s)  
- `MAX_RETRIES`: Reintentos máximos (default: 3)
- `SLACK_WEBHOOK`: Webhook para alertas (opcional)

**Endpoints verificados:**
- `/health/live` (crítico)
- `/health/ready` (importante)
- `/metrics` (opcional)

## Dependency Management

### Dependabot
Configurado en `.github/dependabot.yml` para actualización automática:
- **Python deps**: Lunes 09:00 (pip ecosystem)
- **Docker images**: Martes 10:00
- **GitHub Actions**: Miércoles 11:00

Límites: 3 PRs Python, 2 PRs Docker/Actions por semana.

**Guardrails configurados**: Solo security updates y patches automáticos, major versions requieren review manual.

## Guardrails & Circuit Breakers

### Configuración Central
Archivo `scripts/guardrails.conf` contiene todos los límites de seguridad:

```bash
# Validar configuración
make validate-guardrails

# Probar circuit breakers  
make test-circuit-breakers
```

### Límites Implementados

**Workflows:**
- CI timeout: 15 minutos máximo
- Deploy timeout: 25 minutos máximo  
- Nightly scan timeout: 30 minutos máximo
- Step timeout por defecto: 5 minutos

**Health Checks:**
- Max retries absoluto: 10 (sin importar configuración)
- Timeout máximo: 60 segundos
- Rate limiting: 1 segundo mínimo entre requests
- Alert cooldown: 5 minutos entre alertas del mismo tipo

**Dependabot:**
- Python: máximo 3 PRs simultáneos
- Docker: máximo 2 PRs simultáneos  
- Actions: máximo 2 PRs simultáneos
- Solo security + patch updates automáticos

**Docker & Security:**
- Build timeout: 10 minutos

## Performance Smoke Gating (Fase 5)

Se añadió un pipeline de "smoke performance" que ejecuta una prueba corta (k6 ~60s) en cada push/PR a `main`.

Componentes:
- Script de prueba: `tests/performance/smoke-test.js` (constant-arrival-rate, 40–50 RPS)
- Summary JSON: `reports/performance/smoke-summary.json` generado vía `handleSummary` de k6.
- Script de evaluación: `scripts/eval-smoke.sh` (valida P95 <= 450ms y error rate <= 1%).
- Workflow CI: `.github/workflows/perf-smoke.yml` (falla si se exceden umbrales).

Uso local:
```bash
make k6-smoke                 # Ejecuta test + eval (no bloqueante local)
cat reports/performance/smoke-summary.json
P95_LIMIT_MS=400 bash scripts/eval-smoke.sh   # Ajustar umbral manual
```

Racional:
1. Detectar regresiones de latencia rápido antes de ejecutar suites largas.
2. Reducir riesgo de merges que erosionen SLO sin darse cuenta.
3. Servir de base para canary comparativo (baseline vs canary).

Próximas extensiones sugeridas:
- Parseo de error rate HTTP real (métrica Prometheus) tras carga.
- Publicación del summary como artifact CI.
- Ajuste dinámico de umbrales según error budget restante.
- Vulnerability scan timeout: 5 minutos
- Trivy output limitado para evitar logs gigantes

### Circuit Breakers
- **Health check alerts**: Lockfile-based con cooldown de 5 minutos
- **Retry logic**: Exponential backoff automático
- **Resource limits**: Timeouts absolutos en todos los procesos
- **Rate limiting**: Delay mínimo entre operaciones críticas

### Emergency Breakers
- Disk usage >85%: detener workflows
- Memory usage >90%: kill procesos  
- CPU usage >95%: throttling automático

## Normalización de Mensajes (WhatsApp)
Métricas:
- message_normalized_total{canal,tenant_id}
- message_normalization_errors_total{canal,error_type}
- message_normalization_latency_seconds_bucket

Errores controlados:
- missing_entry
- missing_changes
- missing_messages
- unexpected (errores no previstos)

Flag:
- tenancy.dynamic.enabled (activa mapeo dinámico de tenants).

Test:
pytest -q tests/unit/test_message_gateway_normalization.py

## Grafana Dashboards

### Acceso

**URL:** http://localhost:3000  
**Credenciales por defecto:**
- Usuario: `admin`
- Password: `admin` (cambiar en primer login)

**Datasource:** Prometheus (`http://prometheus:9090`)

### Dashboards Disponibles

#### 1. Database & PMS Performance (`database-performance.json`)

**Propósito:** Monitoreo completo de la salud de la base de datos PostgreSQL, connection pool y operaciones PMS.

**Ubicación:** `docker/grafana/dashboards/database-performance.json`

**Paneles Principales:**

1. **Connection Pool Utilization** (Gauge)
   - Métrica: `db_pool_utilization_percent`
   - Umbrales:
     - Verde: <75%
     - Amarillo: 75-90%
     - Rojo: >90%
   - **Acción si rojo:** Aumentar `POSTGRES_POOL_SIZE` o `POSTGRES_MAX_OVERFLOW`

2. **Database Connections by State** (Time Series)
   - Métricas:
     - `db_pool_active_connections` (verde) - Ejecutando queries
     - `db_pool_idle_connections` (azul) - Disponibles en pool
     - `db_pool_idle_in_transaction` (rojo) - Transaction leak indicator
   - **Alerta:** Si `idle_in_transaction` > 3, revisar commit/rollback en código

3. **Long Running Queries (>30s)** (Stat)
   - Métrica: `db_pool_long_running_queries`
   - Umbrales:
     - Verde: 0
     - Amarillo: 1-2
     - Rojo: ≥3
   - **Acción si rojo:** Ejecutar `python scripts/monitor_connections.py` para ver queries

4. **PMS API Latency (P50/P95/P99)** (Time Series)
   - Métricas:
     - P50: `histogram_quantile(0.50, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le, endpoint))`
     - P95: `histogram_quantile(0.95, ...)`
     - P99: `histogram_quantile(0.99, ...)`
   - **Threshold crítico:** P95 > 2s (dispara alerta `HighPmsLatencyP95`)
   - **Acción:** Revisar cache hit ratio, circuit breaker state

5. **PMS Circuit Breaker State** (Stat)
   - Métrica: `pms_circuit_breaker_state`
   - Valores:
     - 0 = CLOSED (verde) - Normal
     - 1 = OPEN (rojo) - PMS no disponible
     - 2 = HALF-OPEN (amarillo) - Recuperándose
   - **Alerta:** Dispara `CircuitBreakerOpen` si state=1 por >2 minutos

6. **PMS Operations Rate (Success vs Error)** (Time Series)
   - Métricas:
     - Success: `rate(pms_operations_total{status="success"}[5m])`
     - Error: `rate(pms_operations_total{status="error"}[5m])`
   - **Visualización:** Stacked area (verde=success, rojo=error)
   - **Análisis:** Picos de error correlacionados con circuit breaker open

7. **PMS Cache Hit Ratio** (Gauge)
   - Métrica: `(rate(pms_cache_hits_total[5m]) / (rate(pms_cache_hits_total[5m]) + rate(pms_cache_misses_total[5m]))) * 100`
   - Umbrales:
     - Rojo: <50%
     - Amarillo: 50-70%
     - Verde: >70%
   - **Acción si bajo:** Revisar TTL config, ejecutar `python scripts/analyze_redis_cache.py`

8. **Circuit Breaker Call Distribution** (Time Series)
   - Métricas por estado:
     - Closed - Success
     - Closed - Failure
     - Open - Rejected
     - Half-Open - Test
   - **Análisis:** Observar transiciones CLOSED→OPEN para identificar patrones

9. **Pool Overflow Usage** (Stat)
   - Métrica: `db_pool_overflow`
   - Umbrales:
     - Verde: 0
     - Amarillo: 1-10
     - Rojo: >20
   - **Interpretación:** Conexiones más allá del pool base (indica necesidad de incrementar `POSTGRES_POOL_SIZE`)

10. **API Error Rate (5xx responses)** (Time Series)
    - Métrica: `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
    - **Threshold crítico:** >5% (0.05)
    - **Correlación:** Errores 5xx suelen correlacionar con pool exhaustion o circuit breaker open

**Configuración del Dashboard:**

- **Refresh:** 10 segundos (ajustable en tiempo real)
- **Time Range:** Última hora (default)
- **Tags:** `database`, `performance`, `pms`, `monitoring`
- **Auto-refresh:** Activado para monitoreo en vivo

**Uso Recomendado:**

1. **Monitoreo diario:** Revisar P95 latency y pool utilization
2. **Incidentes:** Abrir dashboard al recibir alerta de Prometheus/AlertManager
3. **Capacity planning:** Analizar tendencias semanales de overflow y utilization
4. **Debugging:** Correlacionar long queries con spikes de latencia API

#### 2. Otros Dashboards Existentes

- **agente-overview.json** - Métricas generales de la API
- **alerts-overview.json** - Estado de todas las alertas
- **audio-cache-dashboard.json** - Cache de archivos de audio
- **audio-system-dashboard.json** - Sistema de procesamiento de audio
- **business_metrics.json** - Métricas de negocio
- **readiness-overview.json** - Health checks de dependencias
- **resilience-dashboard.json** - Circuit breakers y retries
- **slo-health.json** - SLO y error budget tracking
- **webhooks-rate-limit.json** - Rate limiting de webhooks

### Provisioning Automático

**Configuración:** `docker/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: default
    orgId: 1
    folder: "Agente Hotel"
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

**Proceso:**
1. Dashboards en formato JSON se colocan en `docker/grafana/dashboards/`
2. Al iniciar Grafana, automáticamente se cargan en la carpeta "Agente Hotel"
3. Los dashboards son editables desde la UI (cambios no persisten en archivos)
4. Para cambios permanentes, editar los archivos JSON y reiniciar Grafana

### Scripts de Monitoreo Relacionados

**1. Connection Pool Monitor:**
```bash
# Análisis único
python scripts/monitor_connections.py

# Monitoreo continuo (10s interval)
python scripts/monitor_connections.py --watch

# Con threshold de alerta
python scripts/monitor_connections.py --threshold 80

# Export Prometheus metrics
python scripts/monitor_connections.py --prometheus
```

**Output:** `.playbook/connection_pool_report.json`, `.playbook/connection_pool_metrics.prom`

**2. Redis Cache Analyzer:**
```bash
# Análisis completo
python scripts/analyze_redis_cache.py

# Con credenciales custom
python scripts/analyze_redis_cache.py --host redis-prod --password secret
```

**Output:** `.playbook/redis_analysis.json`

**3. Database Index Validator:**
```bash
# Validar índices
./scripts/validate_indexes.sh

# Con database custom
./scripts/validate_indexes.sh --host db-prod --database agente_hotel_prod
```

**Output:** `.playbook/index_analysis.json`

### Troubleshooting Grafana

**Dashboard no aparece:**
1. Verificar JSON válido: `cat docker/grafana/dashboards/database-performance.json | jq .`
2. Revisar logs: `docker compose logs grafana | grep -i error`
3. Reiniciar servicio: `docker compose restart grafana`

**Métricas no muestran datos:**
1. Verificar Prometheus: http://localhost:9090/targets (todos UP)
2. Verificar datasource en Grafana: Settings → Data Sources → Prometheus
3. Test query en Prometheus: `db_pool_utilization_percent` debe devolver valores
4. Revisar si los scripts de monitoreo han exportado métricas: `ls -l .playbook/*.prom`

**Permisos de datasource:**
1. Si Grafana no puede conectar a Prometheus, verificar red Docker: `docker network inspect agente-hotel-api_backend_network`
2. Prometheus debe estar en la misma red backend
3. URL del datasource debe ser `http://prometheus:9090` (nombre del servicio Docker)

### Integración con AlertManager

Los paneles en los dashboards están configurados para mostrar thresholds visuales que coinciden con las reglas de alerta de Prometheus:

| Dashboard Panel | Alert Rule | Threshold |
|-----------------|------------|-----------|
| Pool Utilization | N/A (manual) | >90% rojo |
| Long Queries | N/A (manual) | ≥3 rojo |
| PMS Latency P95 | `HighPmsLatencyP95` | >1s por 10min |
| Circuit Breaker | `CircuitBreakerOpen` | state=1 por 2min |
| Error Rate | `HighHttp5xxRate` | >10% por 5min |
| Cache Hit Ratio | `PmsCacheHitRatioLowCritical` | <50% por 10min |

**Ver alertas activas:** http://localhost:9093 (AlertManager UI)

### Best Practices

1. **No editar dashboards en UI:** Los cambios no persisten. Editar JSON y reiniciar Grafana.
2. **Usar variables de templating:** Para filtrar por tenant, endpoint, etc (futuro)
3. **Exportar dashboards editados:** Settings → JSON Model → Copy → Pegar en archivo
4. **Configurar retención de datos:** Prometheus default 15d, ajustar según necesidad
5. **Crear snapshots para debugging:** Share → Snapshot para compartir con equipo
