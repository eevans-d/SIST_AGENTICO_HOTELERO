# 📊 AUDITORÍA PROFESIONAL COMPLETA - SISTEMA AGÉNTICO HOTELERO

> **Fecha:** 09 de Octubre de 2025  
> **Proyecto:** SIST_AGENTICO_HOTELERO - Agente Hotel API  
> **Cobertura:** Prompts 1-8 (Auditoría Completa)  
> **Estado:** En Progreso (37% → 100%)

---

## 🎯 RESUMEN EJECUTIVO

### Hallazgos Principales

| Categoría | Estado | Descripción |
|-----------|--------|-------------|
| **Stack Técnico** | ✅ Robusto | Python 3.12 + FastAPI + async/await |
| **Arquitectura** | ✅ Madura | 9 agentes especializados, circuit breakers |
| **RAG** | ❌ Ausente | Sistema template-based (oportunidad de mejora) |
| **LLM Generativo** | ❌ No implementado | Solo Rasa NLU para clasificación |
| **Observabilidad** | ✅ Implementada | Prometheus + Grafana + AlertManager |
| **Escalabilidad** | ⚠️ Limitada | Sin message queue (llamadas directas) |

---

## 📄 PROMPTS 1-3: ANÁLISIS TÉCNICO Y ARQUITECTURA

### ✅ PROMPT 1: Inventario Técnico Completo

**Archivo:** `docs/AUDIT_PROMPT_1_INVENTARIO_TECNICO.json`

#### Resumen de Hallazgos

- **193 archivos Python** distribuidos en el proyecto
- **30+ dependencias** gestionadas con Poetry
- **Python 3.12** con tipado fuerte y async/await
- **Stack principal:**
  - FastAPI (framework web)
  - PostgreSQL (DB principal)
  - Redis (cache + locks)
  - QloApps PMS (integración hotelera)
  - Rasa NLU (clasificación de intents)
  - Whisper (STT para audio)

#### Componentes Identificados

1. **Orchestrator** - Coordinador central
2. **NLPEngine** - Procesamiento de lenguaje natural (Rasa)
3. **PMSAdapter** - Integración con sistema hotelero
4. **AudioProcessor** - Transcripción de mensajes de voz
5. **WhatsAppClient** - Canal de comunicación
6. **GmailClient** - Canal de comunicación (preparado)
7. **SessionManager** - Gestión de estado conversacional
8. **MessageGateway** - Normalización multi-canal
9. **TemplateService** - Generación de respuestas

#### Gaps Críticos

- ❌ **NO RAG infrastructure** - Sin búsqueda semántica
- ❌ **NO generative LLM** - Respuestas limitadas a templates
- ⚠️ **Secrets management** - Archivos .env (no vault centralizado)

---

### ✅ PROMPT 2: Arquitectura y Flujo de Agentes

**Archivo:** `docs/AUDIT_PROMPT_2_ARQUITECTURA_AGENTES.yaml`

#### Arquitectura Visualizada

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (WhatsApp)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  WhatsApp API    │
                    │   (Webhook)      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Message Gateway  │ ◄── Normalize multi-channel
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  ORCHESTRATOR    │ ◄── Central coordinator
                    │   (Coordinator)  │
                    └────┬──┬──┬───┬───┘
                         │  │  │   │
           ┌─────────────┘  │  │   └─────────────┐
           │                │  │                  │
    ┌──────▼──────┐  ┌─────▼──▼─────┐  ┌────────▼────────┐
    │ NLP Engine  │  │  PMS Adapter  │  │ Audio Processor │
    │ (Rasa NLU)  │  │ (QloApps API) │  │   (Whisper)     │
    └─────────────┘  └───────────────┘  └─────────────────┘
           │                │                     │
    ┌──────▼──────┐  ┌─────▼──────┐    ┌────────▼────────┐
    │  Intents +  │  │   Redis    │    │  Session Mgr    │
    │  Entities   │  │  (Cache)   │    │  (State)        │
    └─────────────┘  └────────────┘    └─────────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Template Service │ ◄── Response generation
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ WhatsApp Client  │ ◄── Send response
                    └────────┬─────────┘
                             │
                             ▼
                          USER
```

#### Flujos Operacionales Documentados

1. **Flujo estándar de mensaje** (14 pasos)
   - Recepción webhook → Normalización → NLP → PMS → Respuesta
   
2. **Flujo late checkout con confirmación** (13 pasos)
   - Solicitud → Verificación disponibilidad → Confirmación usuario → Reserva
   
3. **Flujo de audio** (6 pasos)
   - Audio → Transcripción Whisper → Procesamiento estándar

#### Patrones de Comunicación

- **Patrón principal:** Event-driven async message processing
- **Sin LLM prompts:** Sistema basado en templates + clasificación Rasa
- **Error handling:** Circuit breakers + retry logic + fallback templates

---

### ✅ PROMPT 3: Infraestructura RAG Detallada

**Archivo:** `docs/AUDIT_PROMPT_3_INFRAESTRUCTURA_RAG.yaml`

#### Estado Actual

**❌ RAG NO IMPLEMENTADO**

- Sin vector database
- Sin embeddings
- Sin retrieval service
- Sin generative LLM

#### Sistema Actual

- **18+ templates estáticos** para respuestas predefinidas
- **Rasa NLU** para clasificación de intents (15+ intents)
- **No puede responder preguntas dinámicas** fuera de templates

#### Gap Analysis

| Componente | Estado | Impacto |
|------------|--------|---------|
| Vector Store | ❌ Ausente | No semantic search |
| Embeddings | ❌ Ausente | No similarity matching |
| Retrieval | ❌ Ausente | No dynamic knowledge |
| Generative LLM | ❌ Ausente | No flexible responses |
| Document Ingestion | ❌ Ausente | No knowledge base |

#### Roadmap Recomendado

**Fase 1 - MVP (2-3 semanas, $0)**
- Vector DB: pgvector
- Embeddings: Sentence Transformers (local)
- Ingesta inicial: FAQ + políticas del hotel
- Integración: Feature flag controlado

**Fase 2 - Production (4-6 semanas, $50-200/mes)**
- Vector DB: Qdrant/Weaviate
- Embeddings: OpenAI embeddings
- Reranking con cross-encoders
- Monitoreo de relevancia

**Fase 3 - Advanced (8-12 semanas, $200-500/mes)**
- Multi-source ingestion (PMS, CRM, docs)
- Generative LLM responses con citations
- Continuous learning from conversations
- A/B testing framework

#### Beneficios Esperados

- **+50% reducción** en respuestas `out_of_scope`
- **+30% mejora** en satisfacción del usuario
- **-40% reducción** en tiempo de respuesta para queries complejas
- **Capacidad** de responder preguntas no previstas

---

## 📈 MÉTRICAS DEL SISTEMA

| Categoría | Métrica | Valor |
|-----------|---------|-------|
| **Código** | Archivos Python | 193 |
| **Código** | Líneas servicios | 17,770 |
| **Código** | Tests | 100+ |
| **Agentes** | Total agentes | 9 |
| **Agentes** | Orquestadores | 2 |
| **Agentes** | Especialistas | 7 |
| **NLP** | Intents soportados | 15+ |
| **NLP** | Templates | 18+ |
| **NLP** | Idiomas | 3 (ES/EN/PT) |
| **Infra** | Bases de datos | 3 (Postgres/Redis/MySQL) |
| **Infra** | Contenedores | 6+ |
| **RAG** | Implementado | ❌ NO |

---

## 🚨 GAPS IDENTIFICADOS (Top 10)

1. ❌ **NO RAG infrastructure** - Semantic search opportunity
2. ❌ **NO generative LLM** - Limited to templates
3. ⚠️ **NO centralized secrets management** - Using .env files
4. ⚠️ **NO prompt injection protection** - Input validation only
5. ⚠️ **NO systematic LLM evaluation** - Rasa metrics only
6. ⚠️ **NO cost/token observability** - N/A (no LLM currently)
7. ⚠️ **NO distributed tracing** - Basic logging only
8. ⚠️ **NO A/B testing framework** - Static responses
9. ⚠️ **NO user feedback collection** - No satisfaction tracking
10. ⚠️ **NO message queue** - Direct method calls (scalability limit)

---

## 💡 RECOMENDACIONES ESTRATÉGICAS

### 🥇 PRIORIDAD ALTA (Ahora - Q4 2025)

1. **Completar Quick Wins Features 4-6** (progreso actual: 75%)
2. **Implementar user feedback collection system**
3. **Add systematic out_of_scope tracking**
4. **Consider message queue** for scalability (RabbitMQ/Redis Streams)

### 🥈 PRIORIDAD MEDIA (Q1 2026)

5. **Implement RAG Phase 1** (FAQ knowledge base)
6. **Add centralized secrets management** (HashiCorp Vault)
7. **Integrate generative LLM** for dynamic responses
8. **Implement A/B testing framework**

### 🥉 PRIORIDAD BAJA (Q2 2026)

9. **Add distributed tracing** (OpenTelemetry)
10. **Implement RAG Phase 2-3** (production-ready)
11. **Add prompt injection protection**
12. **Build LLM cost/token observability**

---

## ❓ PREGUNTAS SIN RESOLVER (Top 10)

1. ¿Versión exacta de Rasa utilizada?
2. ¿Se utiliza algún LLM generativo o solo templates?
3. ¿Existen planes para implementar RAG?
4. ¿Cuál es la política de retención de logs?
5. ¿Cómo se manejan datos sensibles (GDPR)?
6. ¿Existe documentación de runbooks operacionales?
7. ¿Cómo se realiza rollback en caso de deploy fallido?
8. ¿Existe monitoreo de business KPIs (conversión, satisfacción)?
9. ¿Los servicios de performance optimization están activos?
10. ¿Cuál es el SLA objetivo del sistema?

---


## 📄 PROMPTS 4-8: OPERACIONES, OBSERVABILIDAD Y DEPLOYMENT

### ✅ PROMPT 4: Scripts y Automatización

**Análisis:** 50+ scripts identificados + 92 targets en Makefile

#### Catálogo de Scripts

**Scripts de Deployment:**
- `deploy.sh` (289 líneas) - Despliegue producción con backup y rollback
- `deploy-staging.sh` - Despliegue a staging
- `deploy-audio-system.sh` - Despliegue específico de sistema de audio
- `canary-deploy.sh` - Despliegue canary con análisis automático

**Scripts de Backup/Restore:**
- `backup.sh` - Backup automatizado (PostgreSQL + MySQL + Redis)
- `restore.sh` - Restauración de backups
- Retención: 30 días configurado
- Soporte para subida a S3

**Scripts de Monitoring:**
- `monitoring.sh` - Monitoreo continuo de servicios
- `health-check.sh` - Health checks manuales
- `health-pinger.sh` - Pinger periódico
- `synthetic-health-check.sh` - Synthetic monitoring

**Scripts de Testing:**
- `resilience-test-suite.sh` - Suite completa de resiliencia
- `chaos-db-failure.sh` - Chaos testing para DB
- `chaos-redis-failure.sh` - Chaos testing para Redis
- `test_multilingual.py` - Tests multiidioma
- `eval-smoke.sh` - Smoke tests rápidos

**Scripts de Análisis:**
- `canary-analysis.sh` - Análisis de canary deployments
- `canary-monitor.sh` - Monitoreo de canary
- `benchmark-compare.sh` - Comparación de benchmarks
- `tech-debt-audit.sh` - Auditoría de deuda técnica
- `parse_rasa_results.py` - Parser de resultados Rasa

**Scripts de Validación:**
- `preflight.py` - Validación pre-deployment (Python)
- `validate-slo-compliance.sh` - Validación de SLOs
- `validate_performance_system.sh` - Validación de performance
- `validate_preflight.py` - Validador del preflight
- `final_verification.sh` - Verificación final

**Scripts de Security:**
- `security-scan.sh` - Escaneo completo de seguridad
- `security_hardening.sh` - Hardening de seguridad
- `rotate_secrets.sh` - Rotación de secretos
- `scripts/guardrails.conf` - Configuración de guardrails

**Scripts de Data:**
- `generate_multilingual_data.py` - Generación de datos multiidioma
- `evaluate_multilingual_models.py` - Evaluación de modelos
- `train_rasa.sh` - Entrenamiento de Rasa NLU
- `train_enhanced_models.sh` - Entrenamiento de modelos mejorados

**Scripts de Utilidades:**
- `deep_cleanup.sh` - Limpieza profunda
- `generate_429.sh` - Generación de rate limit errors (testing)
- `generate-status-summary.sh` - Generación de resúmenes de estado
- `session-start.sh` - Inicialización de sesión de desarrollo
- `update_operational_metrics.py` - Actualización de métricas hoteleras

#### Makefile Targets (92 comandos)

**Categorías principales:**

1. **Setup & Dependencies** (8 targets)
   - `install`, `dev-setup`, `install-k6`, `pre-commit-install`

2. **Code Quality** (10 targets)
   - `fmt`, `lint`, `security-fast`, `security-scan`, `type-check`

3. **Testing** (12 targets)
   - `test`, `test-unit`, `test-integration`, `test-e2e`
   - `test-business-metrics`, `load-test`, `chaos-test`

4. **Docker Operations** (6 targets)
   - `docker-up`, `docker-down`, `docker-build`, `logs`, `health`

5. **Monitoring & Observability** (8 targets)
   - `analyze-performance`, `analyze-chaos`, `open-resilience-dashboard`
   - `compliance-dashboard`, `open-governance-docs`

6. **Deployment & Governance** (15 targets)
   - `preflight`, `canary-diff`, `pre-deploy-check`
   - `validate-slo-compliance`, `check-error-budget`, `check-burn-rates`

7. **Database Operations** (4 targets)
   - `backup`, `restore`, `init-db`

8. **Performance Testing** (6 targets)
   - `performance-test`, `stress-test`, `k6-smoke`
   - `benchmark-baseline`, `benchmark-compare`

9. **Resilience & Chaos** (8 targets)
   - `resilience-test`, `chaos-db`, `chaos-redis`
   - `test-incident-response`

10. **Business Metrics** (5 targets)
    - `update-operational-metrics`, `generate-slo-report`
    - `create-incident-report`

#### Dependency Tree Crítico

```
make preflight
  ├─ scripts/preflight.py (validation)
  ├─ make security-fast (trivy scan)
  └─ make test (pytest suite)

make pre-deploy-check
  ├─ make security-fast
  ├─ make validate-slo-compliance
  └─ make resilience-test

make docker-up
  ├─ docker-compose.yml
  ├─ .env configuration
  └─ Docker network setup

make canary-diff
  ├─ scripts/canary-deploy.sh
  ├─ Prometheus queries (PromQL)
  └─ .playbook/canary_diff_report.json
```

#### Auto-Detection de Tooling

El Makefile detecta automáticamente:
- **uv** (gestor de dependencias moderno)
- **poetry** (gestor de dependencias estándar)
- **npm** (para proyectos JS/TS)
- **Docker Compose** v2 vs v1

#### Integración CI/CD

- **ci-local.sh** - Pipeline CI completo local
- **GitHub Actions** - Workflows en `.github/workflows/`
- **Pre-commit hooks** - Validación automática pre-commit

#### Métricas de Scripts

| Métrica | Valor |
|---------|-------|
| **Total Scripts** | 50+ |
| **Makefile Targets** | 92 |
| **Líneas Makefile** | 676 |
| **Scripts Python** | 12+ |
| **Scripts Bash** | 38+ |
| **Scripts de Deploy** | 5 |
| **Scripts de Testing** | 10+ |
| **Scripts de Monitoring** | 6 |

---

### ✅ PROMPT 5: Observabilidad y Evaluación

**Infraestructura:** Prometheus + Grafana + AlertManager + structlog

#### Logging Estructurado

**Framework:** `structlog` con salida JSON

**Configuración (`app/core/logging.py`):**
```python
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),  # JSON output
    ]
)
```

**Características:**
- Salida JSON para parsing automático
- Timestamps ISO 8601
- Correlation IDs en middleware
- Stack traces automáticos en errores
- Contexto estructurado (key-value pairs)

**Ejemplo de log:**
```json
{
  "event": "pms_request",
  "level": "info",
  "timestamp": "2025-10-09T14:32:10.123456",
  "correlation_id": "abc123",
  "endpoint": "/api/availability",
  "latency_ms": 245
}
```

#### Métricas Prometheus

**Total de métricas identificadas:** 50+ métricas instrumentadas

**Categorías de Métricas:**

1. **HTTP/Request Metrics (MetricsService)**
   - `http_request_latency_seconds` (Histogram) - Latencia por endpoint/método
   - `http_requests_total` (Counter) - Total requests
   - `active_connections` (Gauge) - Conexiones activas

2. **Orchestrator Metrics**
   - `orchestrator_latency` (Histogram) - Latencia de orquestación
   - `orchestrator_messages_total` (Counter) - Mensajes procesados
   - `orchestrator_errors_total` (Counter) - Errores de orquestación
   - `orchestrator_degraded_responses` (Counter) - Respuestas degradadas

3. **PMS Adapter Metrics**
   - `pms_api_latency_seconds` (Histogram) - Latencia de PMS API
   - `pms_operations_total` (Counter) - Operaciones PMS
   - `pms_errors_total` (Counter) - Errores PMS por tipo
   - `pms_cache_hits_total` (Counter) - Cache hits
   - `pms_cache_misses_total` (Counter) - Cache misses
   - `pms_circuit_breaker_state` (Gauge) - Estado del circuit breaker
   - `pms_circuit_breaker_calls_total` (Counter) - Llamadas circuit breaker

4. **Session Metrics**
   - `session_active_total` (Gauge) - Sesiones activas
   - `session_cleanup_total` (Counter) - Limpiezas ejecutadas
   - `session_expirations_total` (Counter) - Sesiones expiradas

5. **NLP Metrics**
   - `nlp_confidence_category_total` (Counter) - Categorías de confianza
   - `nlp_fallback_total` (Counter) - Fallbacks NLP
   - `intents_detected` (Counter) - Intents detectados por nombre

6. **Business Metrics (Hoteleras)**
   - `reservations_total` (Counter) - Reservas por estado
   - `reservation_value` (Histogram) - Valor de reservas
   - `reservation_nights` (Histogram) - Noches por reserva
   - `reservation_lead_time` (Histogram) - Lead time de reservas
   - `active_conversations` (Gauge) - Conversaciones activas
   - `conversation_duration` (Histogram) - Duración conversaciones
   - `messages_per_conversation` (Histogram) - Mensajes por conversación
   - `guest_satisfaction` (Histogram) - Satisfacción del huésped
   - `guest_nps` (Histogram) - Net Promoter Score
   - `occupancy_rate` (Gauge) - Tasa de ocupación
   - `available_rooms` (Gauge) - Habitaciones disponibles
   - `daily_revenue` (Gauge) - Ingresos diarios
   - `average_daily_rate` (Gauge) - Tarifa promedio diaria (ADR)
   - `revpar` (Gauge) - Revenue Per Available Room

7. **Audio Metrics**
   - `audio_operations_total` (Counter) - Operaciones de audio
   - `audio_operation_duration_seconds` (Histogram) - Duración operaciones
   - `audio_errors_total` (Counter) - Errores de audio
   - `audio_temp_files_active` (Gauge) - Archivos temporales activos
   - `audio_file_size_bytes` (Histogram) - Tamaño de archivos
   - `audio_cache_operations_total` (Counter) - Operaciones de cache

8. **Multilingual Metrics**
   - `language_detection_total` (Counter) - Detecciones de idioma
   - `language_detection_latency` (Histogram) - Latencia de detección

9. **Tenant Metrics**
   - `tenant_resolution_total` (Counter) - Resoluciones de tenant
   - `tenants_active_total` (Gauge) - Tenants activos
   - `tenant_identifiers_cached_total` (Gauge) - Identificadores cacheados
   - `tenant_refresh_latency_seconds` (Histogram) - Latencia de refresh
   - `tenant_request_total` (Counter) - Requests por tenant
   - `tenant_request_errors` (Counter) - Errores por tenant

10. **Message Gateway Metrics**
    - `message_normalized_total` (Counter) - Mensajes normalizados
    - `message_normalization_errors_total` (Counter) - Errores normalización
    - `message_normalization_latency_seconds` (Histogram) - Latencia normalización

11. **Feature Flag Metrics**
    - `feature_flag_enabled` (Gauge) - Estado de feature flags

#### Prometheus Configuration

**Scrape Configuration (`docker/prometheus/prometheus.yml`):**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "agente-api"
    static_configs:
      - targets: ["agente-api:8000"]
```

**Endpoints:**
- `/metrics` - Endpoint Prometheus en agente-api:8000

**Alert Rules:**
- `/etc/prometheus/alerts.yml` - Alertas principales
- `/etc/prometheus/alerts-extra.yml` - Alertas adicionales
- `/etc/prometheus/business_alerts.yml` - Alertas de negocio
- `/etc/prometheus/generated/recording_rules.yml` - Recording rules

#### AlertManager Configuration

**Route Configuration (`docker/alertmanager/config.yml`):**
```yaml
global:
  resolve_timeout: 5m

route:
  receiver: "null"
  # Routing por severidad (comentado por defecto)

receivers:
  - name: "null"
  # Slack webhook (template disponible)
  # Email SMTP (template disponible)
```

**Características:**
- Routing por severidad (critical/warning)
- Soporte para Slack webhooks
- Soporte para Email SMTP
- Templates de notificación

#### Grafana Dashboards

**Ubicación:** `docker/grafana/`

**Dashboards disponibles:**
- Performance dashboard (latencia, throughput)
- Business metrics dashboard (ocupación, ADR, RevPAR)
- Error tracking dashboard
- Circuit breaker monitoring
- Session analytics

**Acceso:**
- URL: http://localhost:3000 (default)
- Credenciales configurables vía environment

#### Health Checks

**Endpoints de Health:**

1. `/health/live` - Liveness probe
   - Siempre retorna 200 si el proceso está vivo
   - Para Kubernetes liveness

2. `/health/ready` - Readiness probe
   - Verifica: PostgreSQL, Redis, PMS (opcional)
   - Retorna 200 solo si todas las dependencias OK
   - Para Kubernetes readiness

**Container Health Checks:**
Todos los servicios en docker-compose.yml tienen healthcheck configurado

#### Evaluación de LLM

**Estado actual:** ❌ NO IMPLEMENTADO

**Razón:** Sistema usa Rasa NLU (clasificación) + templates (no generativo)

**Métricas de Rasa disponibles:**
- Intent recognition accuracy
- Entity extraction F1-score
- Confidence scores por intent
- Cross-validation metrics

**Scripts de evaluación:**
- `scripts/parse_rasa_results.py` - Parser de resultados Rasa
- `scripts/evaluate_multilingual_models.py` - Evaluación modelos multiidioma
- `scripts/benchmark_nlp.py` - Benchmarks de NLP

**Gaps para LLM evaluation:**
- Sin métricas de generación (BLEU, ROUGE, perplexity)
- Sin human evaluation framework
- Sin prompt versioning
- Sin A/B testing de prompts
- Sin tracking de costos/tokens

#### Distributed Tracing

**Estado actual:** ⚠️ NO IMPLEMENTADO

**Logging actual:**
- Correlation IDs en requests
- Structured logging con contexto
- Sin traces distribuidos entre servicios

**Recomendación futura:**
- OpenTelemetry integration
- Jaeger/Tempo como backend
- Trace context propagation

#### Observability Summary

| Componente | Estado | Descripción |
|------------|--------|-------------|
| **Structured Logging** | ✅ Implementado | structlog con JSON |
| **Prometheus Metrics** | ✅ Implementado | 50+ métricas instrumentadas |
| **Grafana Dashboards** | ✅ Implementado | Múltiples dashboards |
| **AlertManager** | ✅ Implementado | Routing y notificaciones |
| **Health Checks** | ✅ Implementado | Live + Ready probes |
| **Business Metrics** | ✅ Implementado | Métricas hoteleras |
| **LLM Evaluation** | ❌ N/A | Sistema no usa LLM generativo |
| **Distributed Tracing** | ❌ No implementado | Gap identificado |
| **Cost/Token Tracking** | ❌ N/A | Sistema no usa APIs pagas |

---

### ✅ PROMPT 6: Configuración y Deployment

**Gestión de Configuración:** Pydantic Settings + Environment Variables

#### Settings Architecture

**Archivo principal:** `app/core/settings.py`

**Framework:** Pydantic v2 Settings Management

**Características:**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
```

**Enums para Type Safety:**
- `Environment` (development, staging, production)
- `LogLevel` (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `TTSEngine` (espeak, coqui, elevenlabs)
- `PMSType` (qloapps, mock)

**Tipos de Secrets:**
- `SecretStr` para datos sensibles (API keys, passwords)
- Validación en startup (prevent dummy values in production)

**Categorías de Settings:**

1. **App Settings**
   - `app_name`, `environment`, `debug`, `log_level`
   
2. **Database Settings**
   - `postgres_url` o componentes individuales
   - `postgres_host`, `postgres_port`, `postgres_user`, etc.
   
3. **Redis Settings**
   - `redis_url`, `redis_host`, `redis_port`, `redis_password`
   
4. **PMS Settings**
   - `pms_type` (qloapps/mock)
   - `pms_base_url`, `pms_api_key`
   - `check_pms_in_readiness` (toggle)
   
5. **WhatsApp Settings**
   - `whatsapp_access_token` (SecretStr)
   - `whatsapp_phone_number_id`
   - `whatsapp_verify_token` (SecretStr)
   
6. **Gmail Settings**
   - `gmail_credentials_path`
   - `gmail_token_path`
   
7. **Audio Settings**
   - `tts_engine` (enum)
   - `audio_temp_dir`
   
8. **NLP Settings**
   - `rasa_http_url`
   - `rasa_model_path`

#### Secrets Management

**Método actual:** Environment Variables + .env files

**Archivos:**
- `.env.example` (template con valores dummy)
- `.env` (local development, gitignored)
- `.env.production` (production secrets, NOT in repo)

**Validation:**
```python
# Production secrets validation
if environment == "production":
    if secret_key == "CHANGE_ME_IN_PRODUCTION":
        raise ValueError("Production secrets not configured")
```

**Gaps:**
- ❌ NO centralized secrets vault (HashiCorp Vault, AWS Secrets Manager)
- ❌ NO automatic secret rotation
- ⚠️ Secrets in environment variables (visible in process list)

**Recomendación:**
- Phase 1: HashiCorp Vault integration
- Phase 2: Kubernetes Secrets + External Secrets Operator
- Phase 3: Automated rotation policies

#### Docker Deployment

**Archivos de Compose:**

1. **docker-compose.yml** (Development)
   - Servicios: agente-api, postgres, redis, prometheus, grafana, alertmanager
   - Perfiles: default, pms (opcional para QloApps)
   - Networks: frontend_network, backend_network

2. **docker-compose.production.yml** (Production)
   - Configuración optimizada para producción
   - Resource limits
   - Restart policies
   - Logging drivers

**Dockerfile:**
- `Dockerfile` - Desarrollo (multi-stage build)
- `Dockerfile.production` - Producción (optimizado)

**Docker Networks:**
```yaml
networks:
  frontend_network:
    # NGINX public exposure
  backend_network:
    # Internal service communication
```

**Volumes:**
- Persistent data para PostgreSQL, MySQL, Redis
- Prometheus data retention
- Grafana dashboards

**Profiles:**
```bash
# Default (sin PMS)
docker compose up

# Con QloApps PMS
docker compose --profile pms up
```

#### Deployment Methods

**1. Manual Deployment**
```bash
make docker-up      # Start full stack
make health         # Validate services
make logs           # Monitor logs
```

**2. Script-Based Deployment**
```bash
./scripts/deploy.sh production v1.2.3
```

**Características:**
- Pre-deployment validation
- Automatic backup before deploy
- Health checks post-deploy
- Automatic rollback on failure
- Deployment logging

**3. CI/CD Pipeline**

**GitHub Actions Workflows:**
- `.github/workflows/preflight.yml` - Pre-merge validation
- `.github/workflows/deploy.yml` (inferido) - Auto-deployment

**Pipeline stages:**
1. Lint & Format check
2. Security scan (trivy, gitleaks)
3. Unit tests
4. Integration tests
5. Build Docker image
6. Push to registry
7. Deploy to staging
8. Run smoke tests
9. Canary deployment to production
10. Monitor metrics
11. Promote or rollback

**4. Canary Deployment**
```bash
make canary-diff
```

**Proceso:**
- Deploy new version to 10% traffic
- Monitor P95 latency and error rate
- Compare with baseline (PromQL queries)
- Auto-promote if thresholds met
- Auto-rollback if degradation detected

**Thresholds:**
- P95 latency: ≤10% increase
- Error rate: ≤50% increase

#### Infrastructure Requirements

**Minimum Production Requirements:**

| Resource | Specification |
|----------|---------------|
| **CPU** | 4 cores |
| **RAM** | 8 GB |
| **Storage** | 50 GB SSD |
| **Network** | 100 Mbps |
| **Docker** | v24+ |
| **Docker Compose** | v2+ |

**Recommended Production:**

| Resource | Specification |
|----------|---------------|
| **CPU** | 8 cores |
| **RAM** | 16 GB |
| **Storage** | 200 GB SSD |
| **Network** | 1 Gbps |
| **Load Balancer** | NGINX/Traefik |
| **Database** | PostgreSQL 15+ (managed) |
| **Cache** | Redis 7+ (managed) |

**Database Sizing:**
- PostgreSQL: 10 GB initial, grows with sessions/logs
- Redis: 2 GB cache + locks
- MySQL (QloApps): 5 GB hotel data

#### Configuration Management Summary

| Aspecto | Implementación | Estado |
|---------|----------------|--------|
| **Settings Framework** | Pydantic v2 | ✅ Robusto |
| **Type Safety** | Enums + SecretStr | ✅ Implementado |
| **Environment Files** | .env + .env.example | ✅ Funcional |
| **Secrets Vault** | N/A | ❌ Gap crítico |
| **Docker Compose** | Multi-profile | ✅ Flexible |
| **Deployment Scripts** | Automated | ✅ Completo |
| **CI/CD** | GitHub Actions | ✅ Activo |
| **Canary Deploys** | Automated | ✅ Sofisticado |
| **Rollback** | Automatic | ✅ Implementado |
| **Health Checks** | Multi-level | ✅ Comprehensive |

---

