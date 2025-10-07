# API Sistema Agente Hotelero IA

Componente principal del sistema Agente Hotelero IA. Esta API FastAPI maneja la orquestación de IA y comunicaciones con huéspedes a través de múltiples canales, integrándose con QloApps PMS para la gestión de reservas.

## 📋 Índice

1. [Arquitectura del API](#arquitectura-del-api)
2. [Requisitos](#requisitos)
3. [Instalación](#instalación)
4. [Configuración](#configuración)
5. [Uso](#uso)
6. [Despliegue](#despliegue)
7. [Pruebas](#pruebas)
8. [Monitoreo](#monitoreo)
9. [Documentación Adicional](#documentación-adicional)

## 🏗️ Arquitectura del API

### Componentes Principales

- **FastAPI**: Framework asincrónico para API REST
- **PostgreSQL**: Base de datos para sesiones, bloqueos y mapeo de inquilinos
- **Redis**: Caché, limitación de velocidad y gestión de bloqueos
- **QloApps PMS**: Sistema de gestión de propiedades hoteleras
- **Stack de Monitoreo**: Prometheus, Grafana, AlertManager

### Patrones de Diseño Clave

- **Patrón Orquestador** (`app/services/orchestrator.py`): Coordina el flujo mensaje→NLP→PMS→respuesta
- **Circuit Breaker** (`app/core/circuit_breaker.py`): Protege contra fallos en cascada con servicios externos
- **Mensajes Unificados** (`app/models/unified_message.py`): Normaliza comunicaciones multi-canal
- **Feature Flags** (`app/services/feature_flag_service.py`): Control dinámico de funcionalidades

### Estructura del Proyecto

```
agente-hotel-api/
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── core/                # Configuración, middleware, utilidades
│   ├── exceptions/          # Excepciones personalizadas
│   ├── models/              # Modelos Pydantic y SQLAlchemy
│   ├── routers/             # Endpoints de API
│   ├── services/            # Lógica de negocio
│   └── utils/               # Utilidades generales
├── docker/                  # Configuraciones de servicios
├── docs/                    # Documentación
├── scripts/                 # Scripts de mantenimiento y despliegue
├── tests/                   # Pruebas automatizadas
├── Dockerfile               # Configuración de Docker
├── docker-compose.yml       # Orquestación de servicios
└── pyproject.toml          # Dependencias y configuración
```

## 📋 Requisitos

### Software

- Docker y Docker Compose
- Python 3.10+
- Git
- Make

### Dependencias externas

- Cuenta de WhatsApp Business API
- Cuenta de Gmail (opcional)
- QloApps PMS (opcional, se puede usar mock para desarrollo)

## 🚀 Instalación

### Desarrollo Local

```bash
# Clonar repositorio (si aún no lo has hecho)
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api

# Configuración inicial
make dev-setup

# Instalar dependencias
make install

# Iniciar servicios con PMS mock
make docker-up
```

### Desarrollo con QloApps Real

```bash
# Iniciar con QloApps real (requiere credenciales)
make docker-up --profile pms

# Verificar conexión con QloApps
curl http://localhost:8000/health/ready
```

### Verificar Instalación

```bash
# Verificar servicios en ejecución
docker-compose ps

# Verificar estado de salud
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Verificar métricas
curl http://localhost:8000/metrics
```

## ⚙️ Configuración

### Archivos de Configuración

- **Desarrollo**: `.env` (creado desde `.env.example`)
- **Staging**: `.env.staging` (creado desde `.env.staging.example`)
- **Producción**: `.env.production` (configurado en despliegue)

### Variables de Entorno Principales

```
# Configuración API
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=info

# Base de Datos
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=agente
POSTGRES_PASSWORD=******
POSTGRES_DB=agente

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# QloApps PMS
PMS_TYPE=qloapps  # o 'mock' para desarrollo
PMS_API_BASE_URL=http://qloapps:8080/api/v1
PMS_API_KEY=******

# WhatsApp
WHATSAPP_ACCESS_TOKEN=******
WHATSAPP_PHONE_NUMBER_ID=******

# SLO
SLO_TARGET=99.0
```

### Feature Flags

Los feature flags permiten habilitar/deshabilitar funcionalidades dinámicamente:

```bash
# Listar feature flags actuales
curl http://localhost:8000/admin/feature-flags

# Activar flag específico
curl -X POST http://localhost:8000/admin/feature-flags \
  -H "Content-Type: application/json" \
  -d '{"name": "nlp.fallback.enhanced", "enabled": true}'
```

### Cache Configuration

```bash
# Ver configuración de caché actual
curl http://localhost:8000/admin/cache

# Ajustar TTL para un patrón específico
curl -X POST http://localhost:8000/admin/cache/ttl \
  -H "Content-Type: application/json" \
  -d '{"pattern": "availability:*", "ttl": 3600}'
```

## 🖥️ Uso

### Gestión de Servicios

```bash
# Iniciar todos los servicios
make docker-up

# Detener todos los servicios
make docker-down

# Ver logs
make logs

# Verificar estado de servicios
make health
```

### APIs Principales

#### API de Webhooks

- **WhatsApp**: `POST /webhooks/whatsapp`
  - Recibe mensajes entrantes de WhatsApp
  - Verifica firma de solicitudes
  - Normaliza a `UnifiedMessage`
  
- **Gmail**: `POST /webhooks/gmail`
  - Procesa correos entrantes
  - Extrae contenido relevante
  - Normaliza a `UnifiedMessage`

#### API de Administración

- **Feature Flags**: 
  - `GET /admin/feature-flags` - Listar flags
  - `POST /admin/feature-flags` - Actualizar flag

- **Cache**: 
  - `GET /admin/cache` - Ver estadísticas de caché
  - `POST /admin/cache/invalidate` - Invalidar caché
  - `POST /admin/cache/ttl` - Ajustar TTL

- **Tenants**:
  - `GET /admin/tenants` - Listar inquilinos
  - `POST /admin/tenants/refresh` - Forzar actualización de caché

#### API de Salud y Monitoreo

- **Liveness**: `GET /health/live`
- **Readiness**: `GET /health/ready`
- **Métricas**: `GET /metrics`

### Flujos Principales

#### Procesamiento de Mensajes WhatsApp

1. WhatsApp envía mensaje a webhook `/webhooks/whatsapp`
2. `message_gateway.py` normaliza a `UnifiedMessage`
3. `orchestrator.py` coordina procesamiento:
   - Audio → `AudioProcessor` para transcripción
   - Texto → `NLPEngine` para reconocimiento de intención
   - Intención → `pms_adapter.py` para operaciones PMS
   - Respuesta → `TemplateService` para formateo
   - Envío → `whatsapp_client.py` para responder

#### Consulta de Disponibilidad

1. Usuario pregunta por disponibilidad
2. `NLPEngine` extrae fechas y preferencias
3. `pms_adapter.py` consulta al PMS con circuit breaker
4. Resultados se almacenan en caché Redis
5. Respuesta formateada para WhatsApp/Gmail

#### Creación de Reserva

1. Usuario confirma intención de reservar
2. Sistema solicita información faltante
3. `SessionManager` mantiene estado de conversación
4. `LockService` previene conflictos concurrentes
5. `pms_adapter.py` crea reserva en PMS
6. Se envía confirmación al usuario

## 🚀 Despliegue

### Despliegue a Staging

```bash
# Preparación
cp .env.staging.example .env.staging
nano .env.staging  # Editar con valores reales

# Despliegue automatizado
bash scripts/deploy-staging.sh

# Verificación post-despliegue
bash scripts/health-check.sh staging
```

### Despliegue a Producción

```bash
# Preparación
cp .env.staging .env.production
nano .env.production  # Ajustar valores para producción

# Backup previo
make backup ENVIRONMENT=production

# Despliegue canary (10% tráfico)
bash scripts/deploy-production.sh --canary

# Monitoreo canary
bash scripts/canary-monitor.sh

# Despliegue completo (si canary es exitoso)
bash scripts/deploy-production.sh --complete
```

### Rollback

```bash
# Rollback a versión anterior
bash scripts/rollback.sh production

# Restaurar datos si es necesario
make restore ENVIRONMENT=production BACKUP_DATE=20251005_153045
```

## 🧪 Pruebas

### Ejecución de Pruebas

```bash
# Todas las pruebas
make test

# Pruebas específicas
make test-unit
make test-integration
make test-e2e

# Pruebas de rendimiento
cd tests/performance && locust -f load_test.py
```

### Análisis de Cobertura

```bash
make coverage

# Abrir reporte HTML
open htmlcov/index.html
```

### Validación de Seguridad

```bash
# Análisis de seguridad rápido
make security-fast

# Análisis completo
make security
```

## 📊 Monitoreo

### Dashboards

- **Grafana**: http://localhost:3000
  - Usuario: admin
  - Contraseña: ver `.env` (GRAFANA_ADMIN_PASSWORD)

Dashboards principales:
- **Agente - Overview**: Vista general del sistema
- **SLO Health**: Métricas de nivel de servicio
- **PMS Integration**: Métricas de integración con QloApps
- **WhatsApp Metrics**: Estadísticas de mensajería

### Métricas Clave

| Métrica | Descripción | Umbral Warning | Umbral Critical |
|---------|-------------|----------------|-----------------|
| `pms_circuit_breaker_state` | Estado del circuit breaker | >0 por 1m | >0 por 5m |
| `http_request_duration_seconds` | Latencia de solicitudes API | P95 > 500ms | P95 > 1s |
| `orchestrator_error_ratio` | Tasa de errores del orquestador | >0.01 por 5m | >0.05 por 5m |
| `pms_cache_hit_ratio` | Tasa de aciertos de caché | <0.7 | <0.5 |
| `orchestrator_slo_budget_remaining` | Presupuesto de error SLO restante | <50% | <25% |

### Alertas

Las alertas están configuradas en AlertManager y se notifican a través de:
- Slack: #agente-hotel-alerts
- Email: alertas@agente-hotel.com
- PagerDuty: Solo para alertas críticas

## 📚 Documentación Adicional

- **[Guía de Despliegue](docs/DEPLOYMENT_GUIDE.md)**: Instrucciones detalladas para despliegue
- **[Manual de Operaciones](docs/OPERATIONS_MANUAL.md)**: Guía para operación y mantenimiento
- **[Plan de Pruebas](docs/TEST_VALIDATION_PLAN.md)**: Estrategia de pruebas y validación
- **[Arquitectura de Infraestructura](README-Infra.md)**: Detalles de la infraestructura
- **[Runbooks](docs/RUNBOOKS/)**: Procedimientos para resolución de problemas comunes
- **[FAQ](docs/FAQ.md)**: Preguntas frecuentes