# 📋 FLY.IO CONFIGURATION - Guía Detallada de fly.toml

**Explicación línea por línea de fly.toml y su configuración**

---

## ESTRUCTURA GENERAL

```toml
[app]                    # Metadatos de la app
[build]                  # Configuración de build Docker
[env]                    # Variables de entorno no-secretas
[[services]]             # Servicios (HTTP, TCP)
[[services.ports]]       # Puertos expuestos
[services.http_checks]   # Health checks HTTP
[services.tcp_checks]    # Health checks TCP
[metrics]                # Métricas Prometheus
[deploy]                 # Estrategia de deployment
```

---

## SECCIÓN [app]

```toml
app = "agente-hotel"
```
- **Propósito**: Nombre único de la app en Fly.io
- **Rango**: 1-30 caracteres
- **Reglas**: Minúsculas, hífenes permitidos, sin espacios
- **Ejemplos**: `agente-hotel`, `api-prod`, `scheduler-service`
- **NO cambiar**: Una vez deployada, no modificar
- **Uso**: Aparece en URLs: `https://agente-hotel.fly.dev`

```toml
primary_region = "mia"
```
- **Propósito**: Región geográfica donde corre la app por defecto
- **Opciones comunes**:
  - `mia` - Miami (North America, US East)
  - `sfo` - San Francisco (US West)
  - `cdg` - Paris (Europe)
  - `sin` - Singapore (Asia)
  - `syd` - Sydney (Australia)
- **Ver todas**: `flyctl regions list`
- **Cambiar región**: `flyctl regions update --primary SFO`
- **Nota**: Pings desde Miami ~10-20ms a servidor en Argentina (relativo)

```toml
console_command = "/bin/bash"
```
- **Propósito**: Shell por defecto para `flyctl ssh console`
- **Opciones**:
  - `/bin/bash` - Bash shell (recomendado)
  - `/bin/sh` - Sh shell (minimal)
  - `/usr/bin/python` - Python REPL
- **Uso**: `flyctl ssh console` te conecta con este shell
- **Default**: `/bin/bash` si existe, sino `/bin/sh`

```toml
kill_signal = "SIGTERM"
```
- **Propósito**: Señal para graceful shutdown
- **Opciones**:
  - `SIGTERM` (15) - Soft kill, app tiene tiempo para cleanup
  - `SIGKILL` (9) - Hard kill, sin aviso (evitar)
- **Timeout**: 30 segundos para shutdown, luego SIGKILL automático
- **En app**: Capturar SIGTERM y cerrar conexiones BD, Redis, etc.

```python
# En app/main.py para capturar SIGTERM
import signal

async def shutdown():
    logger.info("Shutting down...")
    # Cerrar conexiones
    await db.close()
    await redis.close()

signal.signal(signal.SIGTERM, shutdown)
```

---

## SECCIÓN [build]

```toml
[build]
dockerfile = "Dockerfile.production"
```
- **Propósito**: Especifica qué Dockerfile usar
- **Opciones**:
  - `Dockerfile` - Dockerfile por defecto
  - `Dockerfile.production` - Optimizado para prod
  - `docker/Dockerfile.custom` - Path custom
- **Ubicación**: Relativo a `build_context`
- **Recomendación**: Usar `Dockerfile.production` con multi-stage build

```toml
build_context = "."
```
- **Propósito**: Directorio raíz para el build
- **Valor por defecto**: `.` (raíz del repo)
- **Uso**: Copia archivos desde aquí
- **Ejemplo**:
  ```
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  ```

```toml
build_target = "production"
```
- **Propósito**: Target específico en multi-stage Dockerfile
- **Uso común**:
  ```dockerfile
  FROM python:3.12 AS base
  RUN pip install poetry
  
  FROM base AS development
  # Dev dependencies
  
  FROM base AS production
  # Minimal, solo runtime
  ```
- **En fly.toml**: `build_target = "production"` ← Usa el stage "production"
- **Ventaja**: Imagen más pequeña (~100 MB vs 500 MB)

```toml
args = ["ENVIRONMENT=production"]
```
- **Propósito**: Argumentos para `docker build --build-arg`
- **Acceso en Dockerfile**:
  ```dockerfile
  ARG ENVIRONMENT
  ENV ENVIRONMENT=${ENVIRONMENT}
  ```
- **Uso**: Compilar optimizaciones según ambiente
- **Múltiples**:
  ```toml
  args = [
    "ENVIRONMENT=production",
    "BUILD_DATE=2025-10-18"
  ]
  ```

---

## SECCIÓN [env]

```toml
[env]
```
- **Propósito**: Variables de entorno NO-SECRETAS
- **Notas**:
  - Variables públicas (visibles en logs)
  - Secrets en `flyctl secrets set` (no en archivo)
  - Sobrescribibles por secrets en tiempo de ejecución

```toml
ENVIRONMENT = "production"
```
- **Propósito**: Contexto de ejecución
- **Valores**: `development`, `staging`, `production`
- **Uso en app**:
  ```python
  from app.core.settings import settings
  if settings.environment == "production":
      enable_security_checks()
  ```
- **Logging**: Cambia nivel según valor

```toml
DEBUG = "false"
```
- **Propósito**: Modo debug de app
- **Valores**: `true`, `false`
- **En production**: Siempre `false`
- **Efectos**:
  - Rate limiting deshabilitado (si DEBUG=true)
  - Logs más verbosos
  - Excepciones exponen más detalles

```toml
LOG_LEVEL = "INFO"
```
- **Propósito**: Nivel de logging
- **Valores**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Recomendado por ambiente**:
  - Dev: `DEBUG`
  - Staging: `INFO`
  - Prod: `WARNING` (menos ruido)

```toml
WORKER_COUNT = "4"
```
- **Propósito**: Workers de Gunicorn/Uvicorn
- **Fórmula**: `(CPU cores * 2) + 1`
- **En Fly.io**: Default es 1, aumentar si necesario
- **Cálculo**: Ver `flyctl info` para CPU cores

```toml
JWT_ALGORITHM = "HS256"
```
- **Propósito**: Algoritmo de JWT
- **Valores**: `HS256` (HMAC), `RS256` (RSA), etc.
- **HS256**: Más rápido, requiere shared secret
- **RS256**: Más seguro, requiere key par (publica/privada)

```toml
RATE_LIMIT_ENABLED = "true"
```
- **Propósito**: Habilitar rate limiting
- **Valores**: `true`, `false`
- **En prod**: Siempre `true`

```toml
RATE_LIMIT_PER_MINUTE = "120"
```
- **Propósito**: Requests por minuto permitido
- **Default**: 120 por IP
- **Ajuste según**: Carga esperada

```toml
REDIS_CACHE_TTL_SECONDS = "300"
```
- **Propósito**: TTL por defecto de caché
- **Valor**: 300 segundos = 5 minutos
- **Ajustar según**: Tipo de dato (availability: 5min, rooms: 60min)

```toml
PMS_TYPE = "mock"
```
- **Propósito**: Tipo de adaptador PMS
- **Valores**:
  - `mock` - Retorna datos fake (desarrollo)
  - `qloapps` - QloApps real (prod)
- **Cambiar en prod**: `PMS_TYPE=qloapps`
- **Requiere**: PMS_API_KEY en secrets

```toml
PMS_CIRCUIT_BREAKER_THRESHOLD = "5"
```
- **Propósito**: Fallos antes de abrir circuit breaker
- **Valor**: Número de fallos permitidos
- **Recomendado**: 3-5 fallos en ventana de 30s

```toml
CHECK_PMS_IN_READINESS = "false"
```
- **Propósito**: Incluir PMS en `/health/ready`
- **Valores**: `true` (prod), `false` (dev)
- **Efecto**:
  - Si `true`: App no ready si PMS no available
  - Si `false`: App ready aunque PMS esté down

```toml
TENANCY_DYNAMIC_ENABLED = "true"
```
- **Propósito**: Usar tenant resolution dinámica
- **Valores**: `true` (prod), `false` (testing)
- **Efecto**: Resolve tenant de BD en lugar de hardcoded

```toml
SESSION_TTL_HOURS = "24"
```
- **Propósito**: Duración de conversación en horas
- **Valor**: 24 = 1 día
- **Nota**: Sessions se limpian de BD después de este tiempo

```toml
AUDIO_PROCESSOR_ENGINE = "openai"
```
- **Propósito**: Motor de STT (speech-to-text)
- **Opciones**: `openai` (recomendado), `google`, `local`
- **En prod**: `openai` requiere API key en secrets

---

## SECCIÓN [[services]]

```toml
[[services]]
internal_port = 8000
protocol = "tcp"
```
- **Propósito**: Define servicios (puertos) expuestos
- **internal_port**: Puerto donde escucha app dentro de contenedor
- **protocol**: `tcp` o `udp` (TCP para HTTP)
- **En app**: FastAPI debe escuchar en este puerto
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

```toml
[services.concurrency]
type = "connections"
hard_limit = 100
soft_limit = 80
```
- **Propósito**: Limitar conexiones concurrentes
- **hard_limit**: Máximo absoluto (100 conexiones)
- **soft_limit**: Nivel de advertencia (80)
- **Efecto**: Fly.io rechaza nuevas conexiones si > hard_limit
- **Ajuste**: Aumentar si es necesario

---

## SECCIÓN [[services.ports]]

```toml
[[services.ports]]
port = 80
handlers = ["http"]
force_https = true
```
- **Propósito**: Exponer puerto 80 (HTTP)
- **handlers**: Tipos de tráfico (`http`, `tls`, `pb`)
- **force_https**: Redirige HTTP → HTTPS automáticamente
- **Certificado**: Fly.io genera automáticamente (Let's Encrypt)
- **URL**: `http://agente-hotel.fly.dev` → `https://agente-hotel.fly.dev`

```toml
[[services.ports]]
port = 443
handlers = ["tls", "http"]
h2 = true
```
- **Propósito**: Exponer puerto 443 (HTTPS/TLS)
- **handlers**: `tls` (TLS encryption), `http` (HTTP sobre TLS)
- **h2**: HTTP/2 habilitado (protocolo más rápido)
- **Certificado**: Automático con Let's Encrypt
- **URL**: `https://agente-hotel.fly.dev`

---

## SECCIÓN [services.http_checks]

```toml
[services.http_checks]
interval = 30000
timeout = 5000
grace_period = 30000
```

- **interval** (ms): Cada cuánto se verifica
  - 30000 ms = cada 30 segundos
  - Aumentar si app tarda en responder
  
- **timeout** (ms): Máximo para que health check responda
  - 5000 ms = 5 segundos
  - Si app tarda > 5s, se cuenta como fallo
  
- **grace_period** (ms): Tiempo antes de verificar tras startup
  - 30000 ms = 30 segundos
  - Esperar 30s antes de empezar health checks (app necesita tiempo)
  - ⚠️ Si app tarda > 30s: aumentar a 60000 ms

```toml
[[services.http_checks.checks]]
protocol = "http"
method = "GET"
path = "/health/live"
require_response_code = 200
```

- **protocol**: `http` o `https`
- **method**: `GET`, `POST`, `HEAD`
- **path**: Endpoint de health check
- **require_response_code**: Código HTTP esperado
- **Nota**: En producción, `/health/live` debe responder en < 5s
  ```python
  # En app/routers/health.py
  @router.get("/health/live")
  async def live():
      return {"status": "alive"}
  ```

---

## SECCIÓN [services.tcp_checks]

```toml
[services.tcp_checks.checks]
interval = 15000
timeout = 5000
grace_period = 30000
```

- **interval**: Cada 15 segundos intenta conexión TCP
- **timeout**: 5 segundos para conectar
- **grace_period**: 30 segundos antes de empezar checks
- **Nota**: TCP checks son más básicos que HTTP
  - Solo verifica que puerto está abierto
  - No verifica respuesta de app

---

## SECCIÓN [metrics]

```toml
[metrics]
port = 9090
path = "/metrics"
```

- **port**: Puerto interno para Prometheus
- **path**: Endpoint de métricas
- **Acceso**:
  ```bash
  flyctl ssh console
  curl localhost:9090/metrics
  exit
  ```
- **Nota**: Fly.io scrapes este endpoint automáticamente
  - Métricas disponibles en Grafana
  - Datos históricos para alertas

---

## SECCIÓN [deploy]

```toml
[deploy]
strategy = "rolling"
max_concurrency = 1
min_machines_running = 1
```

- **strategy**: `rolling` (reemplaza máquinas una por una)
  - Alternativas: `immediate` (reemplaza todas), `bluegreen` (antiguo)
  - **rolling**: Mantiene servicio online durante deploy
  
- **max_concurrency**: Máquinas para reemplazar simultáneamente
  - 1 = reemplaza de a 1
  - 2 = reemplaza de a 2 (más rápido pero más riesgo)
  
- **min_machines_running**: Mínimas máquinas activas
  - 1 = siempre al menos 1 máquina corriendo
  - Útil para evitar downtime

---

## SECCIONES OPCIONALES

### Experimental Features

```toml
[experimental]
auto_rollback = true
```
- **auto_rollback**: Rollback automático si health checks fallan
- **Útil**: Evita deployments malos que se quedan atascados

### Statics (Archivos estáticos)

```toml
[[statics]]
guest_path = "/public"
url_prefix = "/static"
```
- **guest_path**: Directorio en contenedor
- **url_prefix**: URL pública
- **Uso**: Servir CSS, JS, imágenes sin ir a la app

---

## CONFIGURACIÓN RECOMENDADA PARA AGENTE HOTEL

```toml
app = "agente-hotel"
primary_region = "mia"
console_command = "/bin/bash"
kill_signal = "SIGTERM"

[build]
dockerfile = "Dockerfile.production"
build_context = "."
build_target = "production"

[env]
ENVIRONMENT = "production"
DEBUG = "false"
LOG_LEVEL = "WARNING"
WORKER_COUNT = "4"
JWT_ALGORITHM = "HS256"
RATE_LIMIT_ENABLED = "true"
RATE_LIMIT_PER_MINUTE = "120"
REDIS_CACHE_TTL_SECONDS = "300"
PMS_TYPE = "qloapps"
PMS_CIRCUIT_BREAKER_THRESHOLD = "5"
CHECK_PMS_IN_READINESS = "true"
TENANCY_DYNAMIC_ENABLED = "true"
SESSION_TTL_HOURS = "24"
AUDIO_PROCESSOR_ENGINE = "openai"

[[services]]
internal_port = 8000
protocol = "tcp"

[services.concurrency]
type = "connections"
hard_limit = 100
soft_limit = 80

[[services.ports]]
port = 80
handlers = ["http"]
force_https = true

[[services.ports]]
port = 443
handlers = ["tls", "http"]
h2 = true

[services.http_checks]
interval = 30000
timeout = 5000
grace_period = 30000

[[services.http_checks.checks]]
protocol = "http"
method = "GET"
path = "/health/live"
require_response_code = 200

[services.tcp_checks.checks]
interval = 15000
timeout = 5000
grace_period = 30000

[metrics]
port = 9090
path = "/metrics"

[deploy]
strategy = "rolling"
max_concurrency = 1
min_machines_running = 1
```

---

## CAMBIOS COMUNES

### Cambiar región
```toml
# De
primary_region = "mia"

# A
primary_region = "sfo"
```
Luego:
```bash
flyctl deploy
```

### Aumentar recursos por más concurrencia
```toml
# De
[services.concurrency]
hard_limit = 100
soft_limit = 80

# A
[services.concurrency]
hard_limit = 200
soft_limit = 150
```

### Cambiar a desarrollo
```toml
# De
ENVIRONMENT = "production"
DEBUG = "false"
LOG_LEVEL = "WARNING"

# A
ENVIRONMENT = "development"
DEBUG = "true"
LOG_LEVEL = "DEBUG"
```

### Aumentar grace period (para app lenta)
```toml
# De
grace_period = 30000

# A
grace_period = 60000
```

---

## VALIDACIÓN

Verificar que fly.toml es válido:

```bash
# Validar sintaxis TOML
flyctl config validate

# O
flyctl deploy --dry-run
```

---

## DEBUGGING

Ver configuración actual:

```bash
# En Fly.io
flyctl config show

# O
flyctl info --json
```

---

**Última actualización**: 2025-10-18

**Guarda esta guía para referencia al ajustar configuración!**
