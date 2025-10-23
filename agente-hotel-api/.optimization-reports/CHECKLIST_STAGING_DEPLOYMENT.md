# ✅ CHECKLIST: Staging Deployment Preparation

**Documento**: Preparación completa del entorno de Staging  
**Fecha Creación**: 2025-10-22  
**Estado**: Ready for Execution  
**Tiempo Estimado Total**: 1.5-2 horas  
**Prerequisitos**: PR aprobado, merge a `main` completado

---

## 🎯 Objetivo

Preparar **todos los recursos necesarios** para el despliegue en Staging del sistema con los 4 bloqueantes de seguridad implementados. Este checklist garantiza que el entorno Staging:

1. ✅ Tenga configuración reproducible (Infrastructure as Code)
2. ✅ Contenga datos de prueba representativos
3. ✅ Incluya monitoreo completo (Prometheus, Grafana, AlertManager)
4. ✅ Permita performance benchmarking automático

---

## 📋 PRE-FLIGHT CHECKLIST (5 min)

Verificar antes de iniciar:

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Branch main actualizado
git checkout main && git pull origin main

# 2. Docker disponible
docker --version && docker compose version

# 3. Puertos libres (8002, 5432, 6379, 9090, 3000, 9093, 16686)
netstat -tuln | grep -E '8002|5432|6379|9090|3000|9093|16686'

# 4. Espacio en disco (mínimo 5GB)
df -h /var/lib/docker

# 5. Archivos base existen
ls -lh docker-compose.yml Dockerfile.production pyproject.toml
```

**TODOS DEBEN PASAR** antes de continuar.

---

## 🔧 PARTE 1: Docker Compose Staging (30 min)

### 1.1 Crear `docker-compose.staging.yml`

**Archivo**: `docker-compose.staging.yml` (ubicación: raíz del proyecto)

```yaml
version: '3.9'

services:
  # ==================== APLICACIÓN PRINCIPAL ====================
  agente-api:
    build:
      context: .
      dockerfile: Dockerfile.production
    container_name: agente-api-staging
    environment:
      # Variables críticas (usar .env.staging)
      ENVIRONMENT: staging
      DEBUG: "false"
      PMS_TYPE: qloapps
      CHECK_PMS_IN_READINESS: "true"
      TENANCY_DYNAMIC_ENABLED: "true"
      
      # Database
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-agente_staging}
      POSTGRES_USER: ${POSTGRES_USER:-agente_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      
      # Redis
      REDIS_HOST: redis
      REDIS_PORT: 6379
      
      # Secrets (MUST override in .env.staging)
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      WHATSAPP_TOKEN: ${WHATSAPP_TOKEN}
      WHATSAPP_VERIFY_TOKEN: ${WHATSAPP_VERIFY_TOKEN}
      
      # PMS Integration
      PMS_BASE_URL: ${PMS_BASE_URL}
      PMS_API_KEY: ${PMS_API_KEY}
      
      # Monitoring
      PROMETHEUS_MULTIPROC_DIR: /tmp/prometheus
    ports:
      - "8002:8002"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./logs:/app/logs
    networks:
      - agente-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  # ==================== POSTGRESQL ====================
  postgres:
    image: postgres:14-alpine
    container_name: postgres-staging
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-agente_staging}
      POSTGRES_USER: ${POSTGRES_USER:-agente_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    volumes:
      - postgres-data-staging:/var/lib/postgresql/data
      - ./scripts/init-staging-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    networks:
      - agente-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agente_user} -d ${POSTGRES_DB:-agente_staging}"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ==================== REDIS ====================
  redis:
    image: redis:7-alpine
    container_name: redis-staging
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis-data-staging:/data
    networks:
      - agente-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ==================== PROMETHEUS ====================
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus-staging
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=7d'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./docker/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus-data-staging:/prometheus
    networks:
      - agente-network
    restart: unless-stopped

  # ==================== GRAFANA ====================
  grafana:
    image: grafana/grafana:latest
    container_name: grafana-staging
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_INSTALL_PLUGINS: "grafana-piechart-panel,grafana-clock-panel"
    ports:
      - "3000:3000"
    volumes:
      - ./docker/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./docker/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana-data-staging:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - agente-network
    restart: unless-stopped

  # ==================== ALERTMANAGER ====================
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager-staging
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    volumes:
      - ./docker/alertmanager/config.yml:/etc/alertmanager/config.yml:ro
      - alertmanager-data-staging:/alertmanager
    networks:
      - agente-network
    restart: unless-stopped

  # ==================== JAEGER (TRACING) ====================
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: jaeger-staging
    environment:
      COLLECTOR_ZIPKIN_HOST_PORT: ":9411"
      SPAN_STORAGE_TYPE: memory
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"  # UI
      - "14268:14268"
      - "14250:14250"
      - "9411:9411"
    networks:
      - agente-network
    restart: unless-stopped

networks:
  agente-network:
    driver: bridge

volumes:
  postgres-data-staging:
  redis-data-staging:
  prometheus-data-staging:
  grafana-data-staging:
  alertmanager-data-staging:
```

**Validación**:
```bash
docker compose -f docker-compose.staging.yml config
# Debe pasar sin errores
```

---

### 1.2 Crear `.env.staging` Template

**Archivo**: `.env.staging.example` (template para producción)

```bash
# ========================================
# STAGING ENVIRONMENT CONFIGURATION
# ========================================
# CRITICAL: Replace ALL values before deploying!

# -------------------- ENVIRONMENT --------------------
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# -------------------- DATABASE --------------------
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=agente_staging
POSTGRES_USER=agente_user
POSTGRES_PASSWORD=CHANGE_ME_CRYPTO_SECURE_32_CHARS

# -------------------- REDIS --------------------
REDIS_HOST=redis
REDIS_PORT=6379

# -------------------- SECURITY SECRETS --------------------
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=CHANGE_ME_CRYPTO_SECURE_32_CHARS
JWT_SECRET_KEY=CHANGE_ME_CRYPTO_SECURE_32_CHARS

# -------------------- WHATSAPP META API --------------------
WHATSAPP_TOKEN=CHANGE_ME_META_BUSINESS_TOKEN
WHATSAPP_VERIFY_TOKEN=CHANGE_ME_WEBHOOK_VERIFY_TOKEN
WHATSAPP_PHONE_NUMBER_ID=CHANGE_ME_PHONE_ID

# -------------------- PMS INTEGRATION --------------------
PMS_TYPE=qloapps
PMS_BASE_URL=https://staging-pms.example.com/api
PMS_API_KEY=CHANGE_ME_PMS_TOKEN
CHECK_PMS_IN_READINESS=true

# -------------------- MULTI-TENANCY --------------------
TENANCY_DYNAMIC_ENABLED=true
DEFAULT_TENANT_ID=tenant_staging_001

# -------------------- MONITORING --------------------
GRAFANA_PASSWORD=CHANGE_ME_GRAFANA_ADMIN_PASSWORD

# -------------------- RATE LIMITING --------------------
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120

# -------------------- FEATURES FLAGS --------------------
# Enable/disable features (comma-separated)
FEATURE_FLAGS=nlp.fallback.enhanced:true,tenancy.dynamic.enabled:true,audio.processor.optimized:true,pms.circuit_breaker.enabled:true
```

**Generador de Secretos**:
```bash
# Crear .env.staging con secretos seguros
cat << 'SCRIPT' > scripts/generate-staging-secrets.sh
#!/bin/bash
set -e

echo "# Auto-generated staging secrets - $(date)"
echo ""

echo "# Database"
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo ""

echo "# Security"
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo ""

echo "# WhatsApp (MUST manually set from Meta Business Dashboard)"
echo "WHATSAPP_TOKEN=CHANGE_ME_META_BUSINESS_TOKEN"
echo "WHATSAPP_VERIFY_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')"
echo ""

echo "# Grafana"
echo "GRAFANA_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')"
SCRIPT

chmod +x scripts/generate-staging-secrets.sh
./scripts/generate-staging-secrets.sh > .env.staging
```

---

## 📊 PARTE 2: Seed Data Creation (20 min)

### 2.1 Crear `init-staging-db.sql`

**Archivo**: `scripts/init-staging-db.sql`

```sql
-- ========================================
-- STAGING DATABASE INITIALIZATION
-- ========================================
-- Purpose: Create test data for 4 bloqueantes validation
-- Date: 2025-10-22

-- -------------------- TENANTS (Para BLOQUEANTE 1) --------------------
INSERT INTO tenants (id, name, is_active, created_at, updated_at) VALUES
('tenant_hotel_madrid', 'Hotel Madrid Central', true, NOW(), NOW()),
('tenant_hotel_bcn', 'Hotel Barcelona Beach', true, NOW(), NOW()),
('tenant_hotel_sevilla', 'Hotel Sevilla Plaza', true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- -------------------- TENANT USER IDENTIFIERS (Para BLOQUEANTE 1) --------------------
-- Mapeo: phone_number → tenant_id
INSERT INTO tenant_user_identifiers (tenant_id, identifier_type, identifier_value, channel, created_at, updated_at) VALUES
-- Tenant Madrid
('tenant_hotel_madrid', 'phone', '+34600111222', 'whatsapp', NOW(), NOW()),
('tenant_hotel_madrid', 'email', 'guest1@madrid.com', 'gmail', NOW(), NOW()),
('tenant_hotel_madrid', 'phone', '+34600111333', 'whatsapp', NOW(), NOW()),

-- Tenant Barcelona
('tenant_hotel_bcn', 'phone', '+34600222333', 'whatsapp', NOW(), NOW()),
('tenant_hotel_bcn', 'email', 'guest1@barcelona.com', 'gmail', NOW(), NOW()),

-- Tenant Sevilla
('tenant_hotel_sevilla', 'phone', '+34600333444', 'whatsapp', NOW(), NOW()),
('tenant_hotel_sevilla', 'email', 'guest1@sevilla.com', 'gmail', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- -------------------- SESSIONS (Para validación de estado) --------------------
-- Crear sesiones de prueba con diferentes estados
INSERT INTO sessions (session_id, tenant_id, user_id, channel, state, created_at, updated_at, expires_at) VALUES
('session_madrid_001', 'tenant_hotel_madrid', '+34600111222', 'whatsapp', '{"intent_history": ["check_availability"], "context": {"check_in": "2025-11-01", "check_out": "2025-11-03"}}', NOW(), NOW(), NOW() + INTERVAL '24 hours'),
('session_bcn_001', 'tenant_hotel_bcn', '+34600222333', 'whatsapp', '{"intent_history": ["greeting", "check_availability"], "context": {"guests": 2}}', NOW(), NOW(), NOW() + INTERVAL '24 hours')
ON CONFLICT DO NOTHING;

-- -------------------- LOCK AUDIT (Para troubleshooting) --------------------
-- No insertar, se crean dinámicamente, pero dejar tabla lista
-- (Ya existe por SQLAlchemy migration)

-- -------------------- FEATURE FLAGS (Redis init via script) --------------------
-- Se manejan en redis-init.sh

-- -------------------- COMMIT & REPORT --------------------
SELECT 'Staging data seeded successfully!' AS status;
SELECT COUNT(*) AS tenants_count FROM tenants;
SELECT COUNT(*) AS identifiers_count FROM tenant_user_identifiers;
SELECT COUNT(*) AS sessions_count FROM sessions;
```

**Validación**:
```bash
# Ejecutar manualmente para verificar SQL
docker exec -i postgres-staging psql -U agente_user -d agente_staging < scripts/init-staging-db.sql
```

---

### 2.2 Crear `redis-init.sh` (Feature Flags)

**Archivo**: `scripts/redis-init.sh`

```bash
#!/bin/bash
# ========================================
# REDIS INITIALIZATION: Feature Flags
# ========================================
set -e

REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

echo "🔄 Initializing Redis feature flags for staging..."

# Esperar a que Redis esté listo
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q PONG; do
  echo "⏳ Waiting for Redis..."
  sleep 2
done

echo "✅ Redis ready. Setting feature flags..."

# Feature Flags (formato: "feature:flag_name" → "true|false")
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" <<EOF
SET feature:nlp.fallback.enhanced "true"
SET feature:tenancy.dynamic.enabled "true"
SET feature:audio.processor.optimized "true"
SET feature:pms.circuit_breaker.enabled "true"
SET feature:metadata.validation.strict "true"
SET feature:channel.spoofing.detection "true"
EOF

echo "✅ Feature flags initialized:"
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" KEYS "feature:*"

echo "🎉 Redis initialization complete!"
```

**Ejecución**:
```bash
chmod +x scripts/redis-init.sh
docker exec -i redis-staging bash -c "$(cat scripts/redis-init.sh)"
```

---

### 2.3 Crear Test Payloads (WhatsApp & Gmail)

**Archivo**: `tests/fixtures/staging_payloads.json`

```json
{
  "description": "Test payloads for staging smoke tests",
  "payloads": {
    "whatsapp_tenant_madrid": {
      "channel": "whatsapp",
      "tenant_id": "tenant_hotel_madrid",
      "payload": {
        "entry": [
          {
            "changes": [
              {
                "value": {
                  "messages": [
                    {
                      "from": "34600111222",
                      "text": {"body": "Hola, quiero reservar una habitación para el 1 de noviembre"},
                      "timestamp": "1698844800",
                      "type": "text"
                    }
                  ]
                }
              }
            ]
          }
        ]
      },
      "expected_intent": "check_availability",
      "security_checks": ["tenant_isolation", "metadata_filter", "channel_spoofing"]
    },
    "whatsapp_malicious_metadata": {
      "channel": "whatsapp",
      "tenant_id": "tenant_hotel_madrid",
      "payload": {
        "entry": [
          {
            "changes": [
              {
                "value": {
                  "messages": [
                    {
                      "from": "34600111222",
                      "text": {"body": "Test metadata injection"},
                      "timestamp": "1698844800",
                      "type": "text",
                      "metadata": {
                        "malicious_key": "should_be_filtered",
                        "x_tenant_override": "tenant_hotel_bcn",
                        "safe_key": "should_pass"
                      }
                    }
                  ]
                }
              }
            ]
          }
        ]
      },
      "expected_filtered_keys": ["malicious_key", "x_tenant_override"],
      "expected_preserved_keys": ["safe_key"],
      "security_checks": ["metadata_filter"]
    },
    "gmail_tenant_bcn": {
      "channel": "gmail",
      "tenant_id": "tenant_hotel_bcn",
      "payload": {
        "from": "guest1@barcelona.com",
        "subject": "Consulta disponibilidad habitación",
        "body": "Buenos días, quisiera saber si tienen disponibilidad para 2 personas del 5 al 7 de noviembre.",
        "timestamp": "2025-10-22T10:30:00Z"
      },
      "expected_intent": "check_availability",
      "security_checks": ["tenant_isolation", "channel_spoofing"]
    }
  }
}
```

---

## 📈 PARTE 3: Monitoring Configuration (30 min)

### 3.1 Actualizar `prometheus.yml` con Alerting Rules

**Archivo**: `docker/prometheus/alerts.yml`

```yaml
# ========================================
# PROMETHEUS ALERTING RULES - STAGING
# ========================================
groups:
  - name: security_blockers
    interval: 30s
    rules:
      # -------------------- BLOQUEANTE 1: Tenant Isolation --------------------
      - alert: TenantIsolationViolation
        expr: rate(tenant_isolation_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
          component: security
          bloqueante: "1"
        annotations:
          summary: "Tenant isolation violation detected"
          description: "{{ $value }} tenant isolation errors/sec in last 5 min. Investigate immediately."
          runbook: "Check logs with: docker logs agente-api-staging | grep TenantIsolationError"

      # -------------------- BLOQUEANTE 2: Metadata Filtering --------------------
      - alert: MetadataInjectionAttempt
        expr: rate(metadata_filtered_keys_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
          component: security
          bloqueante: "2"
        annotations:
          summary: "High rate of metadata filtering"
          description: "{{ $value }} filtered keys/sec - possible injection attack."
          runbook: "Check filtered keys with: redis-cli -h redis-staging KEYS 'metrics:metadata_filtered:*'"

      # -------------------- BLOQUEANTE 3: Channel Spoofing --------------------
      - alert: ChannelSpoofingDetected
        expr: rate(channel_spoofing_detected_total[5m]) > 0.01
        for: 1m
        labels:
          severity: critical
          component: security
          bloqueante: "3"
        annotations:
          summary: "Channel spoofing attack detected"
          description: "{{ $value }} spoofing attempts/sec. Block IP immediately."
          runbook: "Get attacker IP: docker logs agente-api-staging | grep ChannelSpoofingError | tail -n 20"

      # -------------------- BLOQUEANTE 4: Stale Cache --------------------
      - alert: StaleCacheHighUsage
        expr: rate(pms_stale_cache_hits_total[5m]) / rate(pms_api_calls_total[5m]) > 0.5
        for: 10m
        labels:
          severity: warning
          component: availability
          bloqueante: "4"
        annotations:
          summary: "High stale cache usage (>50%)"
          description: "PMS degraded - {{ $value | humanizePercentage }} requests using stale data."
          runbook: "Check PMS health: curl http://localhost:8002/health/ready | jq .pms"

      # -------------------- CIRCUIT BREAKER --------------------
      - alert: CircuitBreakerOpen
        expr: pms_circuit_breaker_state == 1
        for: 5m
        labels:
          severity: critical
          component: availability
        annotations:
          summary: "PMS circuit breaker OPEN"
          description: "Circuit breaker tripped - all PMS requests failing."
          runbook: "Check PMS logs: docker logs agente-api-staging | grep 'circuit_breaker'"

  - name: performance
    interval: 30s
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
          component: performance
        annotations:
          summary: "P95 latency > 2s"
          description: "{{ $value }}s latency - investigate slow endpoints."

      - alert: ErrorRateHigh
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 3m
        labels:
          severity: critical
          component: reliability
        annotations:
          summary: "Error rate > 5%"
          description: "{{ $value | humanizePercentage }} of requests failing."
```

**Integración en `prometheus.yml`**:
```yaml
# Agregar al final de docker/prometheus/prometheus.yml
rule_files:
  - /etc/prometheus/alerts.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

---

### 3.2 Configurar AlertManager

**Archivo**: `docker/alertmanager/config.yml` (actualizar)

```yaml
# ========================================
# ALERTMANAGER CONFIGURATION - STAGING
# ========================================
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'component', 'bloqueante']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h
  receiver: 'default'
  routes:
    # CRITICAL alerts → Slack + Email
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: false
    
    # Security bloqueantes → Security team
    - match_re:
        component: security
        bloqueante: "[1-4]"
      receiver: 'security-team'
      continue: true
    
    # Performance/Availability → DevOps
    - match:
        component: performance|availability
      receiver: 'devops-team'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'  # Generic webhook
        send_resolved: true

  - name: 'critical-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#agente-hotel-alerts'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: |
          *Alert:* {{ .GroupLabels.alertname }}
          *Severity:* {{ .CommonLabels.severity }}
          *Component:* {{ .CommonLabels.component }}
          {{ if .CommonLabels.bloqueante }}*Bloqueante:* #{{ .CommonLabels.bloqueante }}{{ end }}
          *Description:* {{ range .Alerts }}{{ .Annotations.description }}{{ end }}
          *Runbook:* {{ range .Alerts }}{{ .Annotations.runbook }}{{ end }}
    email_configs:
      - to: 'oncall@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'CHANGE_ME_SMTP_PASSWORD'
        headers:
          Subject: '🚨 CRITICAL ALERT: {{ .GroupLabels.alertname }}'

  - name: 'security-team'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#security-alerts'
        title: '🔒 Security: {{ .GroupLabels.alertname }}'
        text: |
          *Bloqueante #{{ .CommonLabels.bloqueante }}* triggered
          {{ range .Alerts }}{{ .Annotations.description }}{{ end }}

  - name: 'devops-team'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#devops-alerts'
        title: '⚙️ DevOps: {{ .GroupLabels.alertname }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'component']
```

---

### 3.3 Crear Grafana Dashboard JSON

**Archivo**: `docker/grafana/dashboards/security-blockers-dashboard.json`

```json
{
  "dashboard": {
    "title": "Security Blockers - Staging",
    "uid": "security-blockers-staging",
    "timezone": "browser",
    "schemaVersion": 30,
    "version": 1,
    "panels": [
      {
        "id": 1,
        "title": "BLOQUEANTE 1: Tenant Isolation Errors",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tenant_isolation_errors_total[5m])",
            "legendFormat": "Errors/sec"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "alert": {
          "conditions": [
            {
              "evaluator": {"params": [0.1], "type": "gt"},
              "operator": {"type": "and"},
              "query": {"params": ["A", "5m", "now"]},
              "reducer": {"type": "avg"}
            }
          ]
        }
      },
      {
        "id": 2,
        "title": "BLOQUEANTE 2: Metadata Filtered Keys",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(metadata_filtered_keys_total[5m]))",
            "legendFormat": "Filtered Keys/sec"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 6, "h": 8}
      },
      {
        "id": 3,
        "title": "BLOQUEANTE 3: Channel Spoofing Attempts",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(channel_spoofing_detected_total[5m])",
            "legendFormat": "Spoofing Attempts/sec"
          }
        ],
        "gridPos": {"x": 18, "y": 0, "w": 6, "h": 8}
      },
      {
        "id": 4,
        "title": "BLOQUEANTE 4: Stale Cache Usage (%)",
        "type": "gauge",
        "targets": [
          {
            "expr": "100 * (rate(pms_stale_cache_hits_total[5m]) / rate(pms_api_calls_total[5m]))",
            "legendFormat": "Stale %"
          }
        ],
        "gridPos": {"x": 0, "y": 8, "w": 8, "h": 8},
        "fieldConfig": {
          "defaults": {
            "max": 100,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 30},
                {"color": "red", "value": 50}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Circuit Breaker State",
        "type": "stat",
        "targets": [
          {
            "expr": "pms_circuit_breaker_state",
            "legendFormat": "State (0=closed, 1=open, 2=half-open)"
          }
        ],
        "gridPos": {"x": 8, "y": 8, "w": 8, "h": 8}
      },
      {
        "id": 6,
        "title": "Overall Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ],
        "gridPos": {"x": 16, "y": 8, "w": 8, "h": 8}
      }
    ]
  }
}
```

**Auto-provisioning Grafana**:
```yaml
# docker/grafana/provisioning/dashboards/default.yaml
apiVersion: 1
providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

---

## ⚡ PARTE 4: Performance Benchmarking (20 min)

### 4.1 Crear `benchmark-staging.sh`

**Archivo**: `scripts/benchmark-staging.sh`

```bash
#!/bin/bash
# ========================================
# STAGING PERFORMANCE BENCHMARK
# ========================================
set -e

BASE_URL=${BASE_URL:-http://localhost:8002}
DURATION=${DURATION:-60}  # seconds
CONCURRENCY=${CONCURRENCY:-10}

echo "🚀 Starting performance benchmark for Staging..."
echo "   Base URL: $BASE_URL"
echo "   Duration: ${DURATION}s"
echo "   Concurrency: ${CONCURRENCY}"
echo ""

# -------------------- PREREQUISITE CHECK --------------------
if ! command -v wrk &> /dev/null; then
  echo "❌ ERROR: 'wrk' not installed. Install with:"
  echo "   sudo apt-get install wrk (Ubuntu/Debian)"
  echo "   brew install wrk (macOS)"
  exit 1
fi

# -------------------- HEALTH CHECK --------------------
echo "1️⃣  Health Check Benchmark..."
wrk -t4 -c${CONCURRENCY} -d${DURATION}s "$BASE_URL/health/live" \
  --latency \
  > /tmp/benchmark-health.txt 2>&1
cat /tmp/benchmark-health.txt

# -------------------- WEBHOOK ENDPOINT --------------------
echo ""
echo "2️⃣  WhatsApp Webhook Benchmark (simulated payload)..."
cat > /tmp/webhook-payload.lua << 'EOF'
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = '{"entry":[{"changes":[{"value":{"messages":[{"from":"34600111222","text":{"body":"Test message"},"timestamp":"1698844800","type":"text"}]}}]}]}'
EOF

wrk -t4 -c${CONCURRENCY} -d${DURATION}s -s /tmp/webhook-payload.lua \
  "$BASE_URL/api/webhooks/whatsapp" \
  --latency \
  > /tmp/benchmark-webhook.txt 2>&1
cat /tmp/benchmark-webhook.txt

# -------------------- METRICS ENDPOINT --------------------
echo ""
echo "3️⃣  Metrics Endpoint Benchmark..."
wrk -t4 -c${CONCURRENCY} -d${DURATION}s "$BASE_URL/metrics" \
  --latency \
  > /tmp/benchmark-metrics.txt 2>&1
cat /tmp/benchmark-metrics.txt

# -------------------- SUMMARY --------------------
echo ""
echo "📊 BENCHMARK SUMMARY"
echo "===================="

# Extract key metrics (assuming wrk output format)
health_rps=$(grep "Requests/sec:" /tmp/benchmark-health.txt | awk '{print $2}')
webhook_rps=$(grep "Requests/sec:" /tmp/benchmark-webhook.txt | awk '{print $2}')
metrics_rps=$(grep "Requests/sec:" /tmp/benchmark-metrics.txt | awk '{print $2}')

health_p99=$(grep "99%" /tmp/benchmark-health.txt | awk '{print $2}')
webhook_p99=$(grep "99%" /tmp/benchmark-webhook.txt | awk '{print $2}')

echo "Health Endpoint:   ${health_rps} req/s, P99: ${health_p99}"
echo "Webhook Endpoint:  ${webhook_rps} req/s, P99: ${webhook_p99}"
echo "Metrics Endpoint:  ${metrics_rps} req/s"
echo ""

# Validate against SLOs
slo_rps=100
slo_p99_ms=500

if (( $(echo "$webhook_rps < $slo_rps" | bc -l) )); then
  echo "⚠️  WARNING: Webhook RPS ($webhook_rps) below SLO ($slo_rps)"
else
  echo "✅ Webhook RPS meets SLO"
fi

# Convert P99 to ms (assuming format like "500.00ms")
webhook_p99_val=$(echo "$webhook_p99" | sed 's/ms//')
if (( $(echo "$webhook_p99_val > $slo_p99_ms" | bc -l) )); then
  echo "⚠️  WARNING: Webhook P99 ($webhook_p99) above SLO (${slo_p99_ms}ms)"
else
  echo "✅ Webhook P99 meets SLO"
fi

echo ""
echo "🎉 Benchmark complete! Results saved in /tmp/benchmark-*.txt"
```

**Ejecución**:
```bash
chmod +x scripts/benchmark-staging.sh
./scripts/benchmark-staging.sh
```

---

### 4.2 Definir Baseline Metrics

**Archivo**: `.optimization-reports/BASELINE_METRICS.md`

```markdown
# Baseline Performance Metrics - Staging

**Fecha**: 2025-10-22  
**Entorno**: Staging (Docker Compose, 7 servicios)  
**Hardware**: (Especificar después del primer benchmark)

## 🎯 Service Level Objectives (SLOs)

| Métrica | Target | Acceptable | Critical |
|---------|--------|------------|----------|
| **Webhook P99 Latency** | < 200ms | < 500ms | > 1000ms |
| **Health Check P99** | < 50ms | < 100ms | > 200ms |
| **Webhook Throughput** | > 100 req/s | > 50 req/s | < 20 req/s |
| **Error Rate** | < 0.1% | < 1% | > 5% |
| **Availability** | > 99.9% | > 99% | < 95% |

## 📈 Expected Metrics (Post-Bloqueantes)

### Latency Breakdown (per bloqueante)

| Bloqueante | Expected Latency | Measured Latency | Status |
|------------|------------------|------------------|--------|
| **BLOQUEANTE 1** (Tenant Isolation) | < 2ms | TBD | ⏳ |
| **BLOQUEANTE 2** (Metadata Filter) | < 1ms | TBD | ⏳ |
| **BLOQUEANTE 3** (Channel Spoofing) | < 1ms | TBD | ⏳ |
| **BLOQUEANTE 4** (Stale Cache) | < 50ms* | TBD | ⏳ |
| **Total Added Latency** | < 5ms | TBD | ⏳ |

*\*BLOQUEANTE 4 latency depends on PMS circuit breaker state (worst case: 50ms timeout)*

### Throughput

| Endpoint | Expected RPS | Measured RPS | Status |
|----------|--------------|--------------|--------|
| `/health/live` | > 1000 | TBD | ⏳ |
| `/api/webhooks/whatsapp` | > 100 | TBD | ⏳ |
| `/metrics` | > 500 | TBD | ⏳ |

## ✅ Benchmark Execution Checklist

- [ ] Run `scripts/benchmark-staging.sh` after first deployment
- [ ] Populate "Measured Latency" and "Measured RPS" columns
- [ ] Validate all metrics meet "Acceptable" SLO
- [ ] Document any deviations > 10% from expected
- [ ] Re-benchmark after 24h of staging usage

## 📊 Historical Benchmarks

| Date | Version | Webhook P99 | Throughput | Notes |
|------|---------|-------------|------------|-------|
| 2025-10-22 | v1.0.0-security | TBD | TBD | Initial staging deployment |
```

---

## ✅ FINAL CHECKLIST (5 min)

Verificar que todo está preparado:

```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Archivos de configuración existen
ls -lh docker-compose.staging.yml \
       .env.staging.example \
       scripts/init-staging-db.sql \
       scripts/redis-init.sh \
       scripts/generate-staging-secrets.sh \
       scripts/benchmark-staging.sh \
       docker/prometheus/alerts.yml \
       docker/alertmanager/config.yml \
       docker/grafana/dashboards/security-blockers-dashboard.json \
       tests/fixtures/staging_payloads.json \
       .optimization-reports/BASELINE_METRICS.md

# 2. Scripts son ejecutables
chmod +x scripts/*.sh

# 3. Validar Docker Compose
docker compose -f docker-compose.staging.yml config > /dev/null
echo "✅ Docker Compose válido"

# 4. Validar SQL syntax (dry-run)
docker run --rm -v "$(pwd)/scripts:/scripts" postgres:14-alpine \
  psql --echo-errors --single-transaction --set ON_ERROR_STOP=1 \
       --file=/scripts/init-staging-db.sql \
       --dry-run 2>&1 | grep -q "ERROR" && echo "❌ SQL errors" || echo "✅ SQL válido"
```

---

## 🚀 EJECUCIÓN RÁPIDA (Cuando PR esté aprobado)

```bash
# PASO 1: Generar secretos (1 min)
./scripts/generate-staging-secrets.sh > .env.staging
# MANUAL: Editar .env.staging y completar WHATSAPP_TOKEN, PMS_API_KEY

# PASO 2: Levantar servicios (3-5 min)
docker compose -f docker-compose.staging.yml up -d --build

# PASO 3: Verificar health checks (1 min)
sleep 30  # Esperar inicio
curl http://localhost:8002/health/ready | jq .

# PASO 4: Inicializar datos (30 seg)
docker exec -i postgres-staging psql -U agente_user -d agente_staging < scripts/init-staging-db.sql
./scripts/redis-init.sh

# PASO 5: Ejecutar smoke tests (5 min)
# (Usar payloads de tests/fixtures/staging_payloads.json)
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/staging_payloads.json

# PASO 6: Verificar Grafana dashboards (2 min)
open http://localhost:3000  # Login: admin / (ver .env.staging GRAFANA_PASSWORD)

# PASO 7: Ejecutar benchmark (5 min)
./scripts/benchmark-staging.sh
```

**TOTAL: 15-20 minutos** desde zero hasta staging funcionando con monitoreo completo.

---

## 📝 DOCUMENTOS RELACIONADOS

1. **VALIDACION_COMPLETA_CODIGO.md** - Audit con score 9.66/10
2. **GUIA_MERGE_DEPLOYMENT.md** - Workflow merge + deploy (3-5h)
3. **GUIA_TROUBLESHOOTING.md** - Debug procedures & FAQ
4. **BASELINE_METRICS.md** - SLOs y expected performance (este documento)

---

## 🎯 MÉTRICAS DE ÉXITO

**Criterios para considerar Staging exitoso:**

✅ **Funcionalidad**:
- [ ] 10/10 tests E2E pasan
- [ ] Health checks responden 200 OK
- [ ] Todos los servicios (7) running

✅ **Seguridad**:
- [ ] 0 errores TenantIsolationError en logs
- [ ] 0 intentos spoofing sin detectar
- [ ] Metadata filtering activo (logs confirman)

✅ **Performance**:
- [ ] Webhook P99 < 500ms (SLO acceptable)
- [ ] Throughput > 50 req/s (SLO acceptable)
- [ ] Error rate < 1%

✅ **Monitoreo**:
- [ ] Prometheus scraping (9090/targets = UP)
- [ ] Grafana dashboards visibles (3000)
- [ ] AlertManager configurado (9093)
- [ ] Jaeger traces funcionando (16686)

✅ **Resiliencia**:
- [ ] Circuit breaker abre/cierra correctamente (simular fallo PMS)
- [ ] Stale cache activa cuando PMS falla
- [ ] Rollback funciona (restaurar a versión anterior)

---

**FIN DEL CHECKLIST** 🎉

**Next Steps**:
1. ✅ Crear PR en GitHub (mañana según user)
2. ⏳ Esperar aprobación reviewers
3. ⏳ Ejecutar este checklist post-merge
4. ⏳ Monitor staging 24-48h
5. ⏳ Deploy a producción

---

**Fecha**: 2025-10-22  
**Versión**: 1.0  
**Mantenido por**: Backend AI Team
