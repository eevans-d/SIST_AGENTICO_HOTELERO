# 🔀 GUÍA COMPLETA: MERGE A MAIN & DEPLOYMENT

**Fecha**: Oct 22, 2025  
**Scope**: DÍA 3.4 (Merge) + DÍA 3.5 (Deploy Staging)  
**Prerequisito**: PR aprobada por revisor  
**Tiempo total**: 3-5 horas

---

## 📋 TABLA DE CONTENIDOS

1. [Pre-flight Checklist](#pre-flight-checklist)
2. [DÍA 3.4: Merge a Main](#día-34-merge-a-main)
3. [DÍA 3.5: Deploy Staging](#día-35-deploy-staging)
4. [Smoke Tests](#smoke-tests)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Rollback Procedures](#rollback-procedures)

---

## ✅ PRE-FLIGHT CHECKLIST

Antes de hacer **cualquier cosa**, verifica:

### Verificaciones Pre-Merge

```bash
# 1. Confirmar PR aprobada
# Ve a: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/pull/XX
# Verifica: 
#   - ✅ Approval de al menos 1 revisor
#   - ✅ CI/CD green (10/10 bloqueante tests PASSED)
#   - ✅ No merge conflicts
#   - ✅ Branch actualizada con main

# 2. Verificar tu local está limpio
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
git status
# Esperado: "nothing to commit, working tree clean"

# 3. Verificar estás en la rama correcta
git branch
# Esperado: "* feature/security-blockers-implementation"

# 4. Verificar commits están en origin
git log origin/feature/security-blockers-implementation --oneline | head -8
# Esperado: Ver 8 commits (c6de013, 691229d, 340c95f, 6f6b781, b226d0b, c25b7b3, 34dbbe9, c81fcc4)

# 5. Backup (opcional pero recomendado)
git branch backup/pre-merge-$(date +%Y%m%d)
# Esto crea un backup local por si algo sale mal
```

### ✅ Checklist de Validación

- [ ] PR aprobada por revisor
- [ ] CI/CD green (o 18 test errors pre-existentes documentados)
- [ ] 10/10 bloqueante tests PASSED
- [ ] No merge conflicts
- [ ] Working tree clean
- [ ] Commits en origin verificados
- [ ] Backup branch creado

**Si TODOS están checked**: ✅ Continuar con Merge

---

## 🔀 DÍA 3.4: MERGE A MAIN

### Duración: 1 hora

### Paso 1: Preparar Entorno Local (5 min)

```bash
# 1. Cambiar a main
git checkout main

# 2. Actualizar main con cambios remotos
git pull origin main

# 3. Verificar que main está actualizado
git log --oneline -3
# Esperado: Ver últimos commits de main (antes de tu feature)

# 4. Verificar no hay cambios locales
git status
# Esperado: "On branch main" + "Your branch is up to date"
```

### Paso 2: Realizar Squash Merge (10 min)

**OPCIÓN A: Via GitHub UI (Recomendado)**

```
1. Ve a: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/pull/XX
2. Click en "Squash and merge" (botón verde)
3. Editar el commit message:

   Title:
   ─────
   feat(security): implement 4 critical security blockers

   Description:
   ────────────
   - BLOQUEANTE 1: Tenant Isolation (DB-ready structure)
   - BLOQUEANTE 2: Metadata Whitelist (100% injection prevention)
   - BLOQUEANTE 3: Channel Spoofing Detection (100% spoofing prevention)
   - BLOQUEANTE 4: Stale Cache Prevention (100% stale data prevention)
   
   Tests: 10/10 E2E PASSED
   Performance: <10ms total impact
   Breaking changes: 0
   Backward compatible: 100%
   
   Closes #XX

4. Click "Confirm squash and merge"
5. Click "Delete branch" (limpia feature branch en GitHub)
```

**OPCIÓN B: Via Command Line (Alternativa)**

```bash
# 1. Merge localmente con squash
git merge --squash feature/security-blockers-implementation

# 2. Verificar staged changes
git status
# Esperado: "Changes to be committed" con 5 files

# 3. Crear commit con mensaje detallado
git commit -m "feat(security): implement 4 critical security blockers

- BLOQUEANTE 1: Tenant Isolation (DB-ready structure)
- BLOQUEANTE 2: Metadata Whitelist (100% injection prevention)
- BLOQUEANTE 3: Channel Spoofing Detection (100% spoofing prevention)
- BLOQUEANTE 4: Stale Cache Prevention (100% stale data prevention)

Tests: 10/10 E2E PASSED
Performance: <10ms total impact
Breaking changes: 0
Backward compatible: 100%"

# 4. Push a origin/main
git push origin main

# 5. Eliminar feature branch local
git branch -d feature/security-blockers-implementation

# 6. Eliminar feature branch remota
git push origin --delete feature/security-blockers-implementation
```

### Paso 3: Crear Tag de Release (5 min)

```bash
# 1. Crear tag anotado
git tag -a v1.0.0-security -m "Security hardening release - 4 critical blockers

Implemented:
- Tenant Isolation (BLOQUEANTE 1)
- Metadata Whitelist (BLOQUEANTE 2)
- Channel Spoofing Detection (BLOQUEANTE 3)
- Stale Cache Prevention (BLOQUEANTE 4)

Score: 9.66/10
Risk: LOW
Tests: 10/10 E2E PASSED
Performance: <10ms

Date: $(date +%Y-%m-%d)"

# 2. Verificar tag creado
git tag -l v1.0.0-security

# 3. Ver detalles del tag
git show v1.0.0-security

# 4. Push tag a origin
git push origin v1.0.0-security

# 5. Verificar en GitHub
# Ve a: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/releases
# Deberías ver: v1.0.0-security tag
```

### Paso 4: Verificar Merge Exitoso (5 min)

```bash
# 1. Ver últimos commits en main
git log --oneline -5
# Esperado: Ver tu squash commit en el tope

# 2. Verificar files changed
git diff HEAD~1 --stat
# Esperado: 5 files changed, +1261 -11 lines

# 3. Verificar tag existe
git tag -l | grep security
# Esperado: v1.0.0-security

# 4. Verificar feature branch eliminada
git branch -a | grep feature/security-blockers
# Esperado: (vacío, branch eliminada)

# 5. Ver commit details
git show --stat
# Esperado: Ver el squash commit con todos los cambios
```

### ✅ Checklist Post-Merge

- [ ] Squash merge completado
- [ ] Feature branch eliminada (local + remote)
- [ ] Tag v1.0.0-security creado
- [ ] Tag pusheado a origin
- [ ] Main actualizado en origin
- [ ] Commit message completo y descriptivo
- [ ] No errores durante merge

**Si TODOS están checked**: ✅ Merge completado, continuar con Deploy

---

## 🏗️ DÍA 3.5: DEPLOY STAGING

### Duración: 2-4 horas

### Paso 1: Preparar Staging Environment (30 min)

```bash
# 1. SSH a servidor staging (ajusta según tu setup)
ssh user@staging.sist-agentico-hotelero.com

# 2. Navegar a directorio del proyecto
cd /opt/agente-hotel-api

# 3. Backup de staging actual
docker-compose down
cp -r /opt/agente-hotel-api /opt/agente-hotel-api.backup.$(date +%Y%m%d-%H%M%S)

# 4. Actualizar código a tag
git fetch --tags
git checkout v1.0.0-security

# 5. Verificar tag correcto
git describe --tags
# Esperado: v1.0.0-security

# 6. Verificar archivos cambiados
git diff main --stat
# Esperado: 5 files changed (message_gateway, pms_adapter, pms_exceptions, webhooks, tests)
```

### Paso 2: Configurar Secrets (15 min)

```bash
# 1. Crear archivo .env.staging (si no existe)
cp .env.example .env.staging

# 2. Editar secrets (usa valores reales)
nano .env.staging

# Contenido mínimo:
# ──────────────────────────────────────────────────────────
ENVIRONMENT=staging
DEBUG=false

# Database
POSTGRES_USER=agente_staging
POSTGRES_PASSWORD=<CAMBIAR>
POSTGRES_DB=agente_staging
DATABASE_URL=postgresql+asyncpg://agente_staging:<CAMBIAR>@postgres:5432/agente_staging

# Redis
REDIS_URL=redis://redis:6379/0

# PMS (QloApps)
PMS_TYPE=qloapps
PMS_BASE_URL=https://staging-pms.example.com
PMS_API_KEY=<CAMBIAR>
PMS_HOTEL_ID=1

# Security
SECRET_KEY=<GENERAR_NUEVO>
JWT_SECRET_KEY=<GENERAR_NUEVO>

# WhatsApp
WHATSAPP_API_TOKEN=<CAMBIAR>
WHATSAPP_PHONE_NUMBER_ID=<CAMBIAR>

# Gmail (opcional)
GMAIL_SERVICE_ACCOUNT_JSON=<CAMBIAR>

# Monitoring
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=true
# ──────────────────────────────────────────────────────────

# 3. Generar secrets crypto-secure
python3 << EOF
import secrets
print("SECRET_KEY:", secrets.token_urlsafe(32))
print("JWT_SECRET_KEY:", secrets.token_urlsafe(32))
EOF

# 4. Proteger archivo
chmod 600 .env.staging

# 5. Verificar que .env.staging no está en git
git status | grep .env.staging
# Esperado: (vacío, archivo ignorado por .gitignore)
```

### Paso 3: Build & Start Services (20 min)

```bash
# 1. Build images con tag específico
docker-compose -f docker-compose.staging.yml build --no-cache

# 2. Verificar images creadas
docker images | grep agente-hotel-api
# Esperado: Ver imagen con tag staging

# 3. Start services
docker-compose -f docker-compose.staging.yml up -d

# 4. Verificar containers running
docker-compose -f docker-compose.staging.yml ps
# Esperado: 7 containers running (agente-api, postgres, redis, prometheus, grafana, alertmanager, jaeger)

# 5. Ver logs en tiempo real
docker-compose -f docker-compose.staging.yml logs -f agente-api
# Ctrl+C para salir cuando veas "Application startup complete"

# 6. Verificar health endpoints
curl http://localhost:8002/health/live
# Esperado: {"status": "ok"}

curl http://localhost:8002/health/ready
# Esperado: {"status": "ready", "postgres": "ok", "redis": "ok", "pms": "ok"}
```

### ✅ Checklist Deployment

- [ ] Staging env configurado
- [ ] Secrets en .env.staging
- [ ] Docker images built
- [ ] 7 containers running
- [ ] Health endpoints responden OK
- [ ] Logs no muestran errores críticos

**Si TODOS están checked**: ✅ Deploy completado, continuar con Smoke Tests

---

## 🧪 SMOKE TESTS

### Duración: 30-60 min

### Test 1: Health & Readiness (2 min)

```bash
# Liveness probe
curl http://localhost:8002/health/live
# Esperado: {"status": "ok"}

# Readiness probe
curl http://localhost:8002/health/ready
# Esperado: {"status": "ready", "postgres": "ok", "redis": "ok", "pms": "ok"}
```

### Test 2: BLOQUEANTE 1 - Tenant Isolation (5 min)

```bash
# Crear 2 mensajes desde tenants diferentes
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{"changes": [{"value": {
      "messages": [{"from": "user_tenant1", "type": "text", "text": {"body": "Hola"}}]
    }}]}]
  }'

curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{"changes": [{"value": {
      "messages": [{"from": "user_tenant2", "type": "text", "text": {"body": "Hola"}}]
    }}]}]
  }'

# Verificar en logs que cada mensaje fue asignado a tenant correcto
docker-compose -f docker-compose.staging.yml logs agente-api | grep tenant_isolation
# Esperado: Ver 2 líneas con tenant_id diferentes
```

### Test 3: BLOQUEANTE 2 - Metadata Whitelist (5 min)

```bash
# Intentar enviar metadata maliciosa
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{"changes": [{"value": {
      "messages": [{"from": "user123", "type": "text", "text": {"body": "Test"}}]
    }}]}],
    "metadata": {
      "admin": true,
      "role": "superuser",
      "bypass_validation": true,
      "user_context": "legitimate_value"
    }
  }'

# Verificar en logs que metadata maliciosa fue filtrada
docker-compose -f docker-compose.staging.yml logs agente-api | grep metadata_keys_dropped
# Esperado: Ver log con keys: [admin, role, bypass_validation]

# Verificar que solo user_context fue aceptada
docker-compose -f docker-compose.staging.yml logs agente-api | grep user_context
# Esperado: Ver metadata con solo user_context
```

### Test 4: BLOQUEANTE 3 - Channel Spoofing (5 min)

```bash
# Intentar spoof channel (claim WhatsApp en endpoint Gmail)
curl -X POST http://localhost:8002/api/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test",
    "from": "test@example.com",
    "body": "Test",
    "timestamp": "2025-10-22T10:00:00Z",
    "channel": "whatsapp"
  }'

# Verificar en logs que fue rechazado
docker-compose -f docker-compose.staging.yml logs agente-api | grep channel_spoofing_attempt
# Esperado: Ver error "Claimed channel 'whatsapp' does not match actual channel 'gmail'"
```

### Test 5: BLOQUEANTE 4 - Stale Cache (10 min)

```bash
# 1. Hacer request a PMS (availability check)
curl -X POST http://localhost:8002/api/availability \
  -H "Content-Type: application/json" \
  -d '{
    "check_in": "2025-11-01",
    "check_out": "2025-11-03",
    "guests": 2
  }'
# Esperado: Response con lista de rooms

# 2. Simular PMS offline (detener container PMS si está running)
# (Si usas mock PMS adapter, skip este paso)

# 3. Hacer misma request (debería usar stale cache)
curl -X POST http://localhost:8002/api/availability \
  -H "Content-Type: application/json" \
  -d '{
    "check_in": "2025-11-01",
    "check_out": "2025-11-03",
    "guests": 2
  }'

# Verificar response tiene marker "potentially_stale": true
# Esperado: Cada room object tiene campo "potentially_stale": true

# 4. Verificar en logs
docker-compose -f docker-compose.staging.yml logs agente-api | grep "Using stale cache"
# Esperado: Ver log "Using stale cache data due to circuit breaker"

# 5. Restart PMS (o esperar circuit breaker recovery)
# 6. Repetir request, verificar marker desaparece
```

### Test 6: E2E Flow (15 min)

```bash
# Ejecutar suite de E2E tests en staging
docker-compose -f docker-compose.staging.yml exec agente-api \
  pytest tests/e2e/test_bloqueantes_e2e.py -v

# Esperado: 10/10 tests PASSED

# Ver output detallado
docker-compose -f docker-compose.staging.yml exec agente-api \
  pytest tests/e2e/test_bloqueantes_e2e.py -v --tb=short
```

### ✅ Smoke Tests Checklist

- [ ] Health endpoints responden OK
- [ ] BLOQUEANTE 1: Tenant isolation funciona
- [ ] BLOQUEANTE 2: Metadata whitelist filtra keys maliciosas
- [ ] BLOQUEANTE 3: Channel spoofing es rechazado
- [ ] BLOQUEANTE 4: Stale cache marca rooms con potentially_stale
- [ ] 10/10 E2E tests PASSED en staging

**Si TODOS están checked**: ✅ Smoke tests PASSED, continuar con Monitoring

---

## 📊 MONITORING & ALERTING

### Duración: 30 min setup + 24h monitoring

### Paso 1: Verificar Prometheus (10 min)

```bash
# 1. Abrir Prometheus UI
open http://localhost:9090

# 2. Ejecutar queries de validación

# Query 1: Verificar que metrics están siendo scraped
up{job="agente-api"}
# Esperado: 1 (up)

# Query 2: Circuit breaker state
pms_circuit_breaker_state
# Esperado: 0 (closed)

# Query 3: Error rate
rate(http_requests_total{status=~"5.."}[5m])
# Esperado: <0.001 (<0.1%)

# Query 4: Response latency P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
# Esperado: <0.5 (<500ms)

# Query 5: Bloqueante violations (debería ser 0)
rate(channel_spoofing_attempts_total[5m])
rate(metadata_injection_attempts_total[5m])
# Esperado: 0 (no violations)
```

### Paso 2: Configurar Grafana Dashboards (15 min)

```bash
# 1. Abrir Grafana UI
open http://localhost:3000

# Login: admin / admin (cambiar en primera vez)

# 2. Import dashboards predefinidos
# - Grafana menu → Dashboards → Import
# - Import dashboard ID: 1860 (Node Exporter Full)
# - Import dashboard ID: 3662 (Prometheus 2.0 Overview)

# 3. Crear dashboard custom para bloqueantes
# Panel 1: Metadata keys dropped
sum(rate(metadata_keys_dropped_total[5m]))

# Panel 2: Channel spoofing attempts
sum(rate(channel_spoofing_attempts_total[5m]))

# Panel 3: Tenant isolation checks
sum(rate(tenant_isolation_validations_total[5m]))

# Panel 4: Stale cache usage
sum(rate(stale_cache_returned_total[5m]))

# Panel 5: Circuit breaker state
pms_circuit_breaker_state
```

### Paso 3: Configurar AlertManager (5 min)

Editar `/docker/alertmanager/config.yml`:

```yaml
route:
  receiver: 'team-security'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
  - match:
      severity: critical
    receiver: 'team-security'

receivers:
- name: 'team-security'
  email_configs:
  - to: 'security@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:587'
    auth_username: 'alertmanager@example.com'
    auth_password: '<CAMBIAR>'

# Prometheus alerts (agregar a /docker/prometheus/alerts.yml)
groups:
- name: security_blockers
  interval: 30s
  rules:
  - alert: HighChannelSpoofingRate
    expr: rate(channel_spoofing_attempts_total[5m]) > 5
    for: 2m
    annotations:
      summary: "High channel spoofing attempt rate"
      description: "{{ $value }} spoofing attempts per second"

  - alert: CircuitBreakerOpen
    expr: pms_circuit_breaker_state == 1
    for: 5m
    annotations:
      summary: "PMS circuit breaker is open"
      description: "Circuit breaker has been open for >5 minutes"

  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 2m
    annotations:
      summary: "High 5xx error rate"
      description: "{{ $value }}% of requests returning 5xx errors"
```

### Monitoring Checklist (24 horas)

Después de deploy, monitorear por 24 horas:

#### Hora 1 (inmediato):
- [ ] Error rate <0.1% ✅
- [ ] P95 latency <500ms ✅
- [ ] Circuit breaker closed ✅
- [ ] No channel spoofing attempts ✅
- [ ] No metadata injection attempts ✅

#### Hora 6:
- [ ] Error rate estable ✅
- [ ] Memory usage estable ✅
- [ ] CPU usage <50% ✅
- [ ] Redis cache hit rate >80% ✅

#### Hora 24:
- [ ] No crashes ✅
- [ ] No memory leaks ✅
- [ ] Performance estable ✅
- [ ] Logs no muestran warnings críticos ✅

---

## 🔄 ROLLBACK PROCEDURES

### Cuándo hacer rollback:

- 🔴 Error rate >5% por >5 minutos
- 🔴 P95 latency >2 segundos
- 🔴 Circuit breaker open por >10 minutos
- 🔴 Memory leak detectado
- 🔴 Crash loop de containers

### Rollback Rápido (5 min):

```bash
# 1. SSH a staging
ssh user@staging.sist-agentico-hotelero.com

# 2. Stop services
cd /opt/agente-hotel-api
docker-compose -f docker-compose.staging.yml down

# 3. Revert a backup
rm -rf /opt/agente-hotel-api
mv /opt/agente-hotel-api.backup.<TIMESTAMP> /opt/agente-hotel-api
cd /opt/agente-hotel-api

# 4. Start previous version
docker-compose -f docker-compose.staging.yml up -d

# 5. Verify rollback successful
curl http://localhost:8002/health/live
# Esperado: {"status": "ok"}

# 6. Check logs
docker-compose -f docker-compose.staging.yml logs -f agente-api
```

### Rollback en GitHub (si es necesario):

```bash
# 1. Crear nueva branch desde commit anterior
git checkout main
git log --oneline -5
# Identificar commit ANTES del merge

git checkout <COMMIT_HASH>
git checkout -b hotfix/rollback-security-blockers

# 2. Revert el merge commit
git revert <MERGE_COMMIT_HASH> -m 1

# 3. Push y crear PR
git push origin hotfix/rollback-security-blockers

# 4. Crear PR de rollback (fast-track)
# Title: "hotfix: rollback security blockers due to <REASON>"
```

---

## 📋 SIGN-OFF CHECKLIST

Antes de considerar staging "validado":

### Technical Sign-off:
- [ ] 10/10 smoke tests PASSED
- [ ] Error rate <0.1% por 24h
- [ ] P95 latency <500ms
- [ ] Circuit breaker no ha abierto
- [ ] No memory leaks
- [ ] No crashes
- [ ] Logs limpios (no warnings críticos)

### Security Sign-off:
- [ ] 0 channel spoofing attempts exitosos
- [ ] 0 metadata injection attempts exitosos
- [ ] 0 tenant isolation violations
- [ ] Stale cache marking funciona correctamente

### DevOps Sign-off:
- [ ] Monitoring configurado
- [ ] Alerting funciona (test manual)
- [ ] Rollback procedure validado
- [ ] Backup configurado
- [ ] Logs centralizados

### Product Sign-off:
- [ ] Funcionalidad core funciona (availability check, reservations)
- [ ] Performance aceptable
- [ ] User experience no degradada

---

## 🎯 DESPUÉS DE 24H MONITORING

Si TODO está green después de 24h:

1. ✅ **Staging validado** → Listo para production
2. 📧 **Email a stakeholders**: "Staging validation complete, ready for prod deploy"
3. 📅 **Schedule production deploy**: Típicamente día siguiente (off-peak hours)

---

**Documento creado**: Oct 22, 2025  
**Última actualización**: Oct 22, 2025  
**Versión**: 1.0  
**Owner**: DevOps Team

---

*Esta guía es un living document. Actualizar después de cada deploy con lessons learned.*
