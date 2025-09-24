# [PROMPT GA-01] Documentación de Infraestructura

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

Implementación:

- Decorador dinámico `app/core/ratelimit.py` que usa `request.app.state.limiter`.
- En `debug=True` el limit se omite para no requerir Redis en desarrollo/pruebas.
- En producción, `app/main.py` configura `app.state.limiter` con Redis (`settings.redis_url`).

Pruebas:

- `tests/test_rate_limit.py` valida 429 al exceder GET `/webhooks/whatsapp` con `storage_uri="memory://"`.

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

Cambiar SLO:
1. Editar `.env` y setear `SLO_TARGET=99.2` (ejemplo).
2. Reiniciar solo Prometheus: `docker compose restart prometheus` (el entrypoint regenerará reglas).
3. Verificar: `make prometheus-rules-status | grep orchestrator_burn_rate_fast` muestra reglas regeneradas.

Pisos de tráfico SLO:
- Las alertas de degradación y burn rate añaden `orchestrator_message_rate_all > 0.5` para evitar ruido en bajo volumen. Ajustar si el tráfico normal es menor.

Métrica auxiliar añadida:
- `orchestrator_message_rate_all`: suma global de `rate(orchestrator_messages_total[5m])`, usada en alertas SLO.

Métricas SLO / Error Budget adicionales:
- `orchestrator_slo_target`
- `orchestrator_error_budget_fraction`
- `orchestrator_error_budget_used_ratio_30m`
- `orchestrator_error_budget_remaining_ratio_30m`
- `orchestrator_error_budget_hours_to_exhaust_fast`
- `orchestrator_error_budget_hours_to_exhaust_slow`

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

## Métricas de Readiness

La ruta `/health/ready` ahora actualiza métricas Prometheus para facilitar observabilidad:

- `dependency_up{name}` (Gauge): 1 si la dependencia está OK (database, redis, pms), 0 si falla.
- `readiness_up` (Gauge): 1 si todas las dependencias están OK, 0 si alguna falla.
- `readiness_last_check_timestamp` (Gauge): timestamp epoch del último check.

Alerta relacionada:

- `DependencyDown` (warning): `readiness_up < 1` durante más de 2m. Revisar `/health/ready` y los `dependency_up` para diagnóstico rápido.
