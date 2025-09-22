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

Ajustes:
  - Editar umbrales/ventanas en `alerts.yml` según tráfico real.
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

## Dashboards Grafana

- Carpeta: "Agente Hotel" (provisionada automáticamente).
- Dashboards:
  - `Alertas - Overview` (`docker/grafana/dashboards/alerts-overview.json`):
    - KPIs de alertas activas (total, críticas, warning).
    - Distribución por severidad.
    - Detalle de alertas firing y tiempo reciente en estado firing por regla.
