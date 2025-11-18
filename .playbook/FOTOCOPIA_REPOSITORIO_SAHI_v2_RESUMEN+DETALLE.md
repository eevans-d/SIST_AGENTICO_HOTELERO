# FOTOCOPIA SAHI v2 — RESUMEN + DETALLE

**Proyecto**: SIST_AGENTICO_HOTELERO (Agente Hotelero IA)  
**Fecha**: 2025-11-18  
**Branch**: `feature/etapa2-qloapps-integration`  
**Commit de referencia**: `fa92c37882ef75c8c499bd328c757e355d5be478`

---

## 1. RESUMEN EJECUTIVO (PANORAMA RÁPIDO)

- **Qué es**: Sistema agéntico de recepción hotelera multicanal (WhatsApp, Gmail, etc.) con integración a PMS (QloApps), montado sobre FastAPI y orquestado vía Docker Compose con observabilidad completa (Prometheus, Grafana, Alertmanager, Jaeger).
- **Stack núcleo**: Python 3.12.3, FastAPI async, SQLAlchemy 2.x + asyncpg, Redis 7, Postgres 14, Prometheus, Grafana, Jaeger.  
- **Topología**: 7 servicios en `docker-compose.yml` (`agente-api`, `postgres`, `redis`, `prometheus`, `grafana`, `alertmanager`, `jaeger`) + perfil opcional `pms` para QloApps + MySQL.
- **Patrones obligatorios** (NON-NEGOTIABLE):
  - Orchestrator Pattern (router de intents con dict, no if/elif).
  - PMS Adapter Pattern (circuit breaker + cache + métricas).
  - Message Gateway Pattern (normalización WhatsApp/Gmail/SMS a `UnifiedMessage`).
  - Session Management Pattern (estado multi-turno + locks + TTL).
  - Feature Flags Pattern (Redis + `DEFAULT_FLAGS` con reglas anti import-cycle).
  - Observability 3 capas: logs estructurados + métricas Prometheus + trazas Jaeger.
- **Estado actual** (desde docs internas):
  - Deployment readiness: **8.9/10**.
  - Test coverage global: **31%** (28 tests pasando sobre 891 recogidos).
  - CVEs críticos: **0** (por ejemplo `python-jose` actualizado a 3.5.0).
- **Riesgos principales ahora mismo**:
  - Cobertura muy por debajo del objetivo (31% vs 70% objetivo general, 85% en servicios críticos).
  - `.env.supabase` listo para staging pero con secretos placeholder que impedirían producción segura.
  - Orquestador y PMS adapter son complejos (2k+ líneas) con deuda de tests.

**TL;DR para un nuevo desarrollador**: 
> "Piensa en esto como un agente de recepción hotelera enterprise: 
> un orquestador central llama a un PMS protegido por circuit breaker, se observa con métricas y trazas, y persiste sesiones multi-tenant. El sistema está bien diseñado a nivel arquitectura, pero necesita subir test coverage y cerrar cabos sueltos de configuración antes de producción real."

---

## 2. MAPA TÉCNICO COMPACTO

### 2.1. Servicios Docker (infraestructura runtime)

**Archivo clave**: `agente-hotel-api/docker-compose.yml`

- `agente-api`: FastAPI en puerto 8002, contiene toda la lógica de negocio y expone:
  - `/health/live` (liveness, siempre 200).
  - `/health/ready` (readiness, chequea Postgres, Redis y opcionalmente PMS).
  - `/metrics` (endpoint Prometheus).
  - Webhooks de WhatsApp/Gmail bajo `app/routers/webhooks.py`.
- `postgres`: base de datos principal para sesiones, tenants, locks (`SQLAlchemy + asyncpg`).
- `redis`: cache + rate limiting (`slowapi`) + feature flags + locks distribuidos.
- `prometheus`: scrape de `agente-api` y otros servicios cada ~8 segundos.
- `grafana`: dashboards preconfigurados para orquestador, PMS, salud general.
- `alertmanager`: rutas de alerta para circuit breaker, errores altos, etc.
- `jaeger`: trazas distribuidas conectadas a `agente-api` vía OpenTelemetry.

Uso práctico: para entender cómo se ejecuta todo junto, abre `docker-compose.yml` y mira primero el servicio `agente-api` y sus dependencias; luego revisa los `volumes` para persistencia y las `ports` para acceso local.

---

### 2.2. Núcleo de aplicación (`app/main.py` + middleware)

**Archivo clave**: `agente-hotel-api/app/main.py`

- Define la app FastAPI y el `lifespan` (startup/shutdown) para:
  - Inicializar conexiones a Postgres y Redis.
  - Registrar routers (webhooks, health, metrics, admin, etc.).
  - Configurar middlewares: CORS, seguridad, rate limiting, correlation_id, tracing.
- Integra `slowapi` para rate limiting con backend Redis.
- Usa configuración centralizada desde `app/core/settings.py`.

Uso práctico: cuando agregues endpoints nuevos, sigue el patrón de routers existentes y registra el router en `main.py`. Para problemas de arranque, el `lifespan` suele ser el primer lugar que hay que revisar.

---

### 2.3. Configuración (`app/core/settings.py`)

**Archivo clave**: `agente-hotel-api/app/core/settings.py`

- Settings con **Pydantic v2** y `SettingsConfigDict(env_file=".env", extra="ignore")`.
- Variables de entorno agrupadas por responsabilidad: entorno (ENVIRONMENT), logging, DB, Redis, PMS, TTS, etc.
- Construcción dinámica de URL de Postgres, soportando tanto URL única (`DATABASE_URL`/`POSTGRES_URL`) como parámetros sueltos (`POSTGRES_HOST`, `POSTGRES_DB`, ...).
- Campos `SecretStr` para credenciales sensibles: la app está diseñada para fallar al arranque si se dejan valores dummy en producción.
- Modo Supabase:
  - Flag `use_supabase` y ajustes de pool (`supabase_min_pool_size`, `supabase_max_overflow`) para minimizar costes en Supabase.

Uso práctico: cualquier cambio infra (por ejemplo, mover de Supabase a Postgres propio o cambiar el proveedor de Redis) pasa primero por aquí. No hardcodees nada: usa variables de entorno y amplía el modelo de settings si hace falta.

---

### 2.4. Orchestrator Pattern (`app/services/orchestrator.py`)

**Archivo clave**: `agente-hotel-api/app/services/orchestrator.py`

- Es el "cerebro" del sistema: recibe un `UnifiedMessage` y decide qué hacer.
- Router de intents basado en **dict**:
  - `_intent_handlers = {"check_availability": self._handle_availability, ...}`.
  - Cada handler es `async` y devuelve una respuesta normalizada (`{"response_type": "text|audio", "content": {...}}`).
- Lógica clave:
  - Llama a un motor NLP para obtener `intent` + `confidence`.
  - Si la confianza es baja, invoca fallback (mensajes de aclaración) y contabiliza `nlp_fallbacks_total`.
  - Si la operación requiere PMS, usa el adapter protegido por circuit breaker.
  - Puede escalar a humano (`_escalate_to_staff`) y registra métricas de escalación.
- Métricas y logs:
  - `intents_detected{intent,confidence}`.
  - `orchestrator_latency_seconds` para el tiempo total de procesamiento.
  - Logs estructurados con `structlog` que incluyen `correlation_id`.

Uso práctico: cualquier nueva funcionalidad de negocio (nuevo tipo de intención, nuevo flujo de conversación) se diseña como **nuevo intent + handler**. No modifiques la estructura del dict de intents; respeta el patrón para no romper trazas y métricas.

---

### 2.5. PMS Adapter Pattern (`app/services/pms_adapter.py`)

**Archivo clave**: `agente-hotel-api/app/services/pms_adapter.py`

- Envuelve llamadas al PMS (QloApps real o modo `mock`) y les añade:
  - Circuit breaker con estados `CLOSED → OPEN → HALF_OPEN → CLOSED`.
  - Retries con backoff (vía util de `app/core/retry.py`).
  - Cache Redis con TTL diferenciado por endpoint (`availability` vs `room_details`).
  - Métricas Prometheus: latencias, estado del breaker, hits/misses de cache.
- Modos de operación:
  - `PMS_TYPE=mock`: usa `MockPMSAdapter` con fixtures para desarrollo/test.
  - `PMS_TYPE=qloapps`: llamadas reales con auth via token.

Uso práctico: cuando necesites un nuevo endpoint del PMS, agrégalo aquí (con cache y métricas) y no directamente desde el orquestador. Si el sistema se comporta como "flaky" hacia el PMS, revisa primero el estado del circuit breaker en Prometheus/Grafana.

---

### 2.6. Message Gateway + Multi-Tenancy

**Archivos clave**:
- `agente-hotel-api/app/services/message_gateway.py`
- `agente-hotel-api/app/models/unified_message.py`
- `agente-hotel-api/app/services/dynamic_tenant_service.py`

- `message_gateway` recibe payloads específicos de canal (WhatsApp, Gmail, SMS) y los transforma en `UnifiedMessage` con:
  - `sender_id`, `channel`, `text`, `audio_data`, `timestamp`, `metadata`.
- Resolución de tenant:
  - Consulta Postgres para mapear identificadores de usuario a `Tenant`.
  - Usa cache en memoria (con TTL ~300s) para no saturar la BD.
  - Fallback chain: dynamic → static → `default` tenant.
- Métricas: `tenant_resolution_total{result=hit|default|miss_strict}` y otras de tenencia.

Uso práctico: si añades un nuevo canal (por ejemplo, un bot web propio), el punto de entrada correcto es aquí: nueva rama de normalización a `UnifiedMessage`, reutilizando el resto del pipeline intacto.

---

### 2.7. Session Management + Locks

**Archivos clave**:
- `agente-hotel-api/app/services/session_manager.py`
- `agente-hotel-api/app/services/lock_service.py`
- `agente-hotel-api/app/models/session.py`
- `agente-hotel-api/app/models/lock_audit.py`

- `session_manager` persiste estado de conversación:
  - Historial de intents (últimos N).
  - Contexto (fechas, disponibilidad consultada, preferencias de huésped).
  - TTL de sesión (por defecto 24h, configurable mediante settings).
- `lock_service` gestiona locks distribuidos en Redis:
  - Claves por combinación `tenant + usuario + recurso` (por ejemplo, reserva específica).
  - TTL para auto-liberar locks incluso si el proceso cae.
  - Auditoría a tabla `lock_audit` para trazabilidad.

Uso práctico: si tienes condiciones de carrera (dos canales intentando reservar al mismo tiempo), el lugar correcto para mitigarlas es con locks a través de `lock_service`, no inventando mecanismos ad-hoc en el orquestador.

---

### 2.8. Feature Flags (`feature_flag_service.py`)

**Archivo clave**: `agente-hotel-api/app/services/feature_flag_service.py`

- Implementa feature flags con backend Redis y fallback en memoria (`DEFAULT_FLAGS`).
- Reglas importantes:
  - Siempre `await ff.is_enabled(...)` en contextos async.
  - En módulos como `message_gateway` que podrían provocar ciclos de import, se usa directamente `DEFAULT_FLAGS`.
- Flags típicos:
  - `nlp.fallback.enhanced` (activar lógica mejorada de fallback NLP).
  - `tenancy.dynamic.enabled` (usar o no resolución dinámica de tenant).
  - `audio.processor.optimized` (activar versión optimizada de STT).

Uso práctico: para rollouts controlados (por ejemplo, nueva versión del NLP o nuevo flujo de reserva), agrega un flag aquí, úsalo en los servicios correspondientes y documenta su semántica.

---

### 2.9. Seguridad y Rate Limiting

**Archivos clave**:
- `agente-hotel-api/app/security/password_policy.py`
- `agente-hotel-api/app/security/jwt_handler.py`
- `agente-hotel-api/app/security/rate_limiter.py`
- `agente-hotel-api/app/core/middleware.py`

- Password policy enterprise (mínimo 12 caracteres, complejidad, historial, rotación) con tests unitarios completos.
- JWT con `python-jose` actualizado y validaciones robustas.
- Rate limiting con `slowapi` (por defecto ~120/min por webhook) usando Redis.
- Middleware de seguridad: headers estándar (HSTS, X-Frame-Options, X-Content-Type-Options, etc.) y límite de tamaño de request (por ejemplo 25MB para audio WhatsApp).

Uso práctico: antes de exponer un nuevo endpoint público, asegúrate de que pasa por el rate limiter y de que no salta las validaciones de auth.

---

### 2.10. Observabilidad (Prometheus, Grafana, Jaeger)

**Archivos clave**:
- `docker/prometheus/prometheus.yml`
- `docker/prometheus/alerts.yml` y `alerts-extra.yml`
- `docker/prometheus/recording_rules.tmpl.yml`
- `docker/grafana/**`

- Métricas clave en código:
  - Orchestrator: `intents_detected`, `nlp_fallbacks_total`, `orchestrator_latency_seconds`, `orchestrator_escalations_total`.
  - PMS: `pms_circuit_breaker_state`, `pms_api_latency_seconds`, `pms_circuit_breaker_calls_total`, `pms_cache_hits_total`, `pms_cache_misses_total`.
  - Sesiones: `sessions_active`, `session_creation_latency_seconds`.
  - Tenancy: `tenant_resolution_total`, `tenants_active_total`, `tenant_refresh_latency_seconds`.
- Alertas preconfiguradas para errores altos, circuit breaker en estado OPEN sostenido, etc.

Uso práctico: ante cualquier incidente, tu orden de ataque debería ser: logs → métricas → trazas.

---

## 3. .env.SUPABASE — ESTADO Y RIESGOS

**Archivo actual**: `agente-hotel-api/.env.supabase` (abierto en el editor)

### 3.1. Estado actual

- `POSTGRES_URL` apunta al pooler de Supabase, puerto 6543, con usuario y password reales.
- `REDIS_URL` apunta a un endpoint Upstash con TLS (`rediss://`).
- `PMS_TYPE=mock`, lo que permite operar sin credenciales reales de QloApps.
- `USE_SUPABASE=true` o equivalente en settings (según cómo esté conectado a `settings.py`), ajustando el tamaño del pool.

### 3.2. Problemas/pendientes antes de producción

- `SECRET_KEY`: mantiene un valor placeholder tipo `GENERA_CON_PYTHON_SECRETS_TOKEN_URLSAFE_32` que debe reemplazarse por un valor generado con `secrets.token_urlsafe(32)`.
- Credenciales de WhatsApp:
  - `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` siguen con comentarios de "OBTEN_DE_META_DEVELOPERS".
- Credenciales de Gmail:
  - `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD` siguen como placeholders (solo válidos para documentación o dev local sin envío real).

### 3.3. Recomendación operativa

- Para **staging controlado sin canales externos reales**, puedes mantener PMS en `mock` y no configurar WhatsApp/Gmail todavía.
- Para **producción o staging con canales reales**:
  1. Generar `SECRET_KEY` seguro.
  2. Configurar WhatsApp (Meta Developers) y Gmail (app password) y volcar los valores reales.
  3. Validar que nada de esto se comite al repo (usar `.env` en despliegue y no versionar).

---

## 4. CÓMO USAR ESTE SNAPSHOT

### 4.1. Si eres desarrollador nuevo

1. Lee esta v2 (RESUMEN + DETALLE) de arriba a abajo; te da el mapa mental.
2. Si necesitas más detalle, abre `FOTOCOPIA_REPOSITORIO_SAHI.md` que es la versión extendida.
3. Navega el código siguiendo este orden recomendado:
   - `app/main.py` → entender arranque y routers.
   - `app/services/orchestrator.py` → cómo fluye una conversación.
   - `app/services/pms_adapter.py` → cómo se habla con el PMS.
   - `app/services/session_manager.py` + `lock_service.py` → estado y concurrencia.
   - `app/core/settings.py` + `.env.supabase` → cómo se configura el entorno.

### 4.2. Si quieres subir cobertura de tests

1. Prioriza servicios críticos con objetivo 85%:
   - `orchestrator.py`, `pms_adapter.py`, `session_manager.py`, `lock_service.py`.
2. Usa los patrones de tests existentes en `tests/unit/test_orchestrator.py` y compañía.
3. Asegúrate de mockear PMS (usar `MockPMSAdapter`) y Redis cuando sea necesario.

### 4.3. Si preparas un despliegue a staging/producción

1. Revisa `.env.supabase` siguiendo la sección 3 de este documento.
2. Ejecuta pipeline de calidad:
   - `make install`
   - `make fmt`
   - `make lint`
   - `make test`
3. Ejecuta los checks previos de producción (cuando coverage sea razonable):
   - `make preflight`
   - `make canary-diff BASELINE=main CANARY=staging`
4. Monitoriza via Grafana/Prometheus tras el despliegue.

---

## 5. NOTAS FINALES

- Esta v2 está optimizada para ser **leída en 5–10 minutos** y darte una imagen clara del sistema sin entrar en todos los detalles de implementación.
- Para inspecciones profundas, referencias exactas de código o discusión arquitectónica avanzada, utiliza también `FOTOCOPIA_REPOSITORIO_SAHI.md`, que es la versión "extends" de esta.
- Toda la información aquí viene de archivos del repo (código y docs) y de tu `.env.supabase` actual; no se asume información externa.
