# Plan de Pruebas y Validación - Sistema Agente Hotelero IA

## Objetivo

Este documento define el proceso completo de pruebas y validación para el Sistema Agente Hotelero IA, asegurando la calidad, confiabilidad y rendimiento del sistema en todos los ambientes de despliegue.

## Índice

1. [Estrategia de Pruebas](#1-estrategia-de-pruebas)
2. [Tipos de Pruebas](#2-tipos-de-pruebas)
3. [Ambientes de Prueba](#3-ambientes-de-prueba)
4. [Automatización de Pruebas](#4-automatización-de-pruebas)
5. [Validación de Despliegue](#5-validación-de-despliegue)
6. [Pruebas de Canary](#6-pruebas-de-canary)
7. [Plan de Mejora Continua](#7-plan-de-mejora-continua)
8. [Herramientas](#8-herramientas)
9. [Glosario](#9-glosario)

## 1. Estrategia de Pruebas

### 1.1. Enfoque de Pruebas

El Sistema Agente Hotelero IA sigue una estrategia de pruebas piramidal con cuatro niveles:

1. **Pruebas Unitarias**: Verifican componentes individuales aislados
2. **Pruebas de Integración**: Validan la interacción entre componentes
3. **Pruebas de Sistema**: Evalúan el funcionamiento completo del sistema
4. **Pruebas de Aceptación**: Validan escenarios de negocio end-to-end

### 1.2. Principios Clave

- **Shift Left**: Detección temprana de problemas en el ciclo de desarrollo
- **Automatización**: Priorización de pruebas automatizadas sobre manuales
- **Cobertura Crítica**: Enfoque en flujos críticos de negocio
- **Monitoreo Continuo**: Las pruebas no terminan con el despliegue

### 1.3. Criterios de Éxito

- **Cobertura de Código**: >80% en módulos críticos
- **Tasa de Detección de Defectos**: >90% antes de producción
- **Tiempo Medio de Recuperación**: <30 minutos para incidentes críticos
- **Precisión de NLP**: >85% para intenciones primarias

## 2. Tipos de Pruebas

### 2.1. Pruebas Unitarias

**Objetivo**: Verificar el correcto funcionamiento de componentes individuales.

**Herramientas**: pytest, unittest

**Ubicación**: `/tests/unit/`

**Ejecución**:
```bash
# Ejecutar todas las pruebas unitarias
make test-unit

# Ejecutar pruebas específicas
python -m pytest tests/unit/test_pms_adapter.py -v
```

**Cobertura Mínima**: 80%

**Ejemplos de Pruebas Unitarias**:
- Circuit Breaker (estado y transiciones)
- Adaptador PMS (caché, reintentos)
- Procesador de Audio (conversión, formatos)
- Servicio de Bloqueo (adquisición, liberación)

### 2.2. Pruebas de Integración

**Objetivo**: Verificar la interacción correcta entre componentes del sistema.

**Herramientas**: pytest, pytest-asyncio

**Ubicación**: `/tests/integration/`

**Ejecución**:
```bash
# Ejecutar todas las pruebas de integración
make test-integration

# Ejecutar pruebas específicas
python -m pytest tests/integration/test_pms_integration.py -v
```

**Ejemplos de Pruebas de Integración**:
- Orquestador con Motor NLP
- Gateway de Mensajes con WhatsApp/Gmail
- Adaptador PMS con Mock Server
- Servicio de Plantillas con Orquestador

### 2.3. Pruebas de Sistema

**Objetivo**: Evaluar el sistema completo funcionando en conjunto.

**Herramientas**: pytest, pytest-docker-compose

**Ubicación**: `/tests/system/`

**Ejecución**:
```bash
# Ejecutar todas las pruebas de sistema
make test-system

# Ejecutar pruebas específicas
python -m pytest tests/system/test_high_load.py -v
```

**Ejemplos de Pruebas de Sistema**:
- Procesamiento completo de mensajes de WhatsApp
- Flujo completo de reservas
- Gestión de errores y reintentos
- Degradación controlada ante fallos

### 2.4. Pruebas de Contrato

**Objetivo**: Verificar que los servicios cumplen con sus contratos de API.

**Herramientas**: pact, OpenAPI validator

**Ubicación**: `/tests/contracts/`

**Ejecución**:
```bash
# Ejecutar todas las pruebas de contrato
make test-contracts

# Validar contra especificación OpenAPI
python -m pytest tests/contracts/test_api_spec.py -v
```

**Ejemplos de Pruebas de Contrato**:
- Contratos PMS-Agente
- Contratos WhatsApp-Gateway de Mensajes
- Validación de esquemas JSON de respuesta

### 2.5. Pruebas End-to-End (E2E)

**Objetivo**: Validar flujos completos de usuario desde el inicio hasta el fin.

**Herramientas**: pytest, playwright

**Ubicación**: `/tests/e2e/`

**Ejecución**:
```bash
# Ejecutar todas las pruebas E2E
make test-e2e

# Ejecutar flujo de reservación específico
python -m pytest tests/e2e/test_reservation_flow.py -v
```

**Ejemplos de Pruebas E2E**:
- Consulta de disponibilidad vía WhatsApp
- Reserva completa con pago
- Flujo de cancelación de reserva
- Gestión de modificación de reserva

### 2.6. Pruebas de Rendimiento

**Objetivo**: Evaluar el rendimiento y escalabilidad del sistema bajo carga.

**Herramientas**: locust, k6

**Ubicación**: `/tests/performance/`

**Ejecución**:
```bash
# Ejecutar pruebas de carga
make test-load

# Ejecutar pruebas de estrés
make test-stress

# Ejecutar pruebas específicas
cd tests/performance && locust -f locustfile.py
```

**Ejemplos de Pruebas de Rendimiento**:
- Prueba de carga para webhooks de WhatsApp
- Prueba de estrés para consultas de disponibilidad
- Prueba de spike para picos de tráfico
- Evaluación de límites de tasa (rate limiting)

### 2.7. Pruebas de Resiliencia

**Objetivo**: Verificar la capacidad del sistema para recuperarse de fallos.

**Herramientas**: chaos-monkey, toxiproxy

**Ubicación**: `/tests/resilience/`

**Ejecución**:
```bash
# Ejecutar pruebas de resiliencia
make test-resilience

# Ejecutar escenario específico
python -m pytest tests/resilience/test_pms_failure.py -v
```

**Ejemplos de Pruebas de Resiliencia**:
- Latencia alta en PMS
- Caída de Redis
- Reinicios de servicios
- Pérdida de conexión a WhatsApp API

## 3. Ambientes de Prueba

### 3.1. Ambiente de Desarrollo Local

**Propósito**: Desarrollo y pruebas iniciales.

**Configuración**:
- Docker Compose local
- Mock PMS para desarrollo rápido
- Datos sintéticos

**Uso**:
```bash
# Iniciar ambiente de desarrollo
make docker-up
```

### 3.2. Ambiente de Integración Continua (CI)

**Propósito**: Ejecución automática de pruebas en cada commit.

**Configuración**:
- GitHub Actions o Jenkins
- Contenedores efímeros
- Mock PMS

**Ubicación**: `.github/workflows/ci.yml`

### 3.3. Ambiente de Staging

**Propósito**: Pruebas pre-producción con configuración similar a producción.

**Configuración**:
- Infraestructura similar a producción
- Conexión real a QloApps staging
- Datos de prueba curados

**Uso**:
```bash
# Desplegar a staging
make deploy ENVIRONMENT=staging
```

### 3.4. Ambiente de Producción

**Propósito**: Servicio de producción con tráfico real.

**Configuración**:
- Infraestructura optimizada
- Conexión real a QloApps producción
- Datos reales

**Uso**:
```bash
# Desplegar a producción (con canary)
make deploy ENVIRONMENT=production CANARY=true
```

## 4. Automatización de Pruebas

### 4.1. Integración Continua (CI)

**Flujo**:
1. Commit/PR a repositorio
2. Ejecución automática de pruebas unitarias y de integración
3. Análisis estático de código y seguridad
4. Generación de reporte de cobertura
5. Notificación de resultados

**Configuración**: `.github/workflows/ci.yml`

### 4.2. Pipeline de Pruebas

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Análisis   │ ─> │   Pruebas   │ ─> │   Pruebas   │ ─> │   Pruebas   │
│  Estático   │    │  Unitarias  │    │ Integración │    │   Sistema   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐        v
│  Despliegue │ <- │   Pruebas   │ <- │   Pruebas   │ <- ┌─────────────┐
│ Producción  │    │   Canary    │    │  Staging    │    │   Pruebas   │
└─────────────┘    └─────────────┘    └─────────────┘    │     E2E     │
                                                         └─────────────┘
```

### 4.3. Programación de Pruebas Automáticas

| Tipo de Prueba    | Frecuencia              | Gatillo                     |
|-------------------|-------------------------|----------------------------|
| Unitarias         | Cada commit             | Push a cualquier rama      |
| Integración       | Cada commit             | Push a cualquier rama      |
| Sistema           | Diario                  | Cron + Pull Request a main |
| Contratos         | Diario                  | Cron + Pull Request a main |
| E2E               | Pull Request            | Pull Request a main        |
| Rendimiento       | Semanal                 | Cron + Cambios en perf     |
| Resiliencia       | Semanal                 | Cron                       |

## 5. Validación de Despliegue

### 5.1. Pre-Despliegue

Verificaciones antes del despliegue:

```bash
# Verificar que todas las pruebas pasan
make test

# Verificar seguridad
make security-fast

# Validar dependencias
make dependency-check

# Validación pre-vuelo
make preflight ENVIRONMENT=production
```

### 5.2. Post-Despliegue

Verificaciones después del despliegue:

```bash
# Verificar estado de salud
curl https://api.agente-hotel.com/health/ready

# Verificar versión desplegada
curl https://api.agente-hotel.com/version

# Ejecutar pruebas de humo
make test-smoke ENVIRONMENT=production

# Verificar métricas iniciales
make verify-metrics ENVIRONMENT=production
```

### 5.3. Lista de Verificación Post-Despliegue

1. **Verificar endpoints de salud**:
   ```bash
   curl https://api.agente-hotel.com/health/live
   curl https://api.agente-hotel.com/health/ready
   ```

2. **Validar funcionalidades críticas**:
   ```bash
   # Enviar mensaje de prueba
   curl -X POST https://api.agente-hotel.com/admin/test-message \
     -H "Content-Type: application/json" \
     -d '{"message": "Hola, quiero reservar"}'
   
   # Verificar disponibilidad
   curl -X POST https://api.agente-hotel.com/admin/test-availability \
     -H "Content-Type: application/json" \
     -d '{"check_in": "2025-01-15", "check_out": "2025-01-17"}'
   ```

3. **Monitorear logs y métricas**:
   ```bash
   # Verificar logs
   docker-compose -f docker-compose.production.yml logs --tail=50 agente-api
   
   # Verificar métricas clave
   curl http://localhost:9090/api/v1/query?query=up
   curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state
   ```

4. **Validar alertas**:
   ```bash
   # Comprobar que Alertmanager está operativo
   curl http://localhost:9093/-/healthy
   
   # Verificar que no hay alertas activas
   curl http://localhost:9093/api/v1/alerts
   ```

## 6. Pruebas de Canary

### 6.1. Estrategia de Despliegue Canary

El sistema utiliza despliegue canary para minimizar el impacto de nuevas versiones:

1. **Despliegue inicial**: 10% del tráfico a la nueva versión
2. **Periodo de observación**: 30 minutos
3. **Incrementos graduales**: 25%, 50%, 100%
4. **Rollback automático**: Si se detectan errores o degradación

### 6.2. Métricas de Evaluación Canary

| Métrica | Umbral Advertencia | Umbral Crítico | Acción |
|---------|-------------------|---------------|--------|
| Error Rate | >1% delta | >2% delta | Rollback |
| Latencia P95 | >10% incremento | >25% incremento | Rollback |
| Circuit Breaker Abierto | >0 por 1m | >0 por 5m | Rollback |
| SLO Burn Rate | >2x normal | >5x normal | Rollback |

### 6.3. Script de Monitoreo Canary

```bash
# Ejecutar monitoreo de canary
bash scripts/canary-monitor.sh

# Personalizar umbrales
LATENCY_THRESHOLD=1.2 ERROR_RATE_THRESHOLD=0.03 bash scripts/canary-monitor.sh
```

## 7. Plan de Mejora Continua

### 7.1. Retroalimentación de Pruebas

El sistema recopila métricas para mejorar continuamente:

- **Tiempo de ejecución de pruebas**: Optimizar pruebas lentas
- **Cobertura de código**: Identificar áreas sin cobertura
- **Tasa de detección de defectos**: Evaluar efectividad
- **Falsos positivos/negativos**: Refinar casos de prueba

### 7.2. Ciclo de Mejora

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Recopilar  │ ──> │  Analizar   │ ──> │   Planear   │
│  Métricas   │     │  Resultados │     │   Mejoras   │
└─────────────┘     └─────────────┘     └─────────────┘
      ^                                        │
      │                                        │
      │                                        v
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Evaluar   │ <── │ Implementar │ <── │ Priorizar   │
│  Resultados │     │   Mejoras   │     │   Cambios   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 7.3. KPIs de Calidad

| KPI | Objetivo | Medición |
|-----|----------|----------|
| Tasa de Defectos | <0.5 defectos/1000 LOC | Defectos / KLOC |
| Tiempo Medio de Detección | <8 horas | Tiempo entre introducción y detección |
| Tiempo Medio de Resolución | <24 horas | Tiempo entre detección y resolución |
| Test Pass Rate | >98% | Pruebas exitosas / Total pruebas |

## 8. Herramientas

### 8.1. Pruebas y Calidad

- **pytest**: Framework de pruebas unitarias y de integración
- **pytest-asyncio**: Soporte para pruebas asíncronas
- **pytest-cov**: Medición de cobertura de código
- **pytest-docker-compose**: Pruebas con Docker Compose
- **locust**: Pruebas de carga y rendimiento
- **toxiproxy**: Simulación de fallos de red para pruebas de resiliencia

### 8.2. Monitoreo y Evaluación

- **Prometheus**: Recopilación de métricas
- **Grafana**: Visualización de métricas
- **AlertManager**: Gestión de alertas
- **OpenTelemetry**: Trazas distribuidas

### 8.3. Automatización

- **GitHub Actions**: CI/CD
- **Docker**: Contenedorización
- **Make**: Automatización de tareas
- **Bash**: Scripts de despliegue y monitoreo

## 9. Glosario

- **SLO (Service Level Objective)**: Objetivo de nivel de servicio, meta de rendimiento
- **Circuit Breaker**: Patrón para prevenir fallos en cascada
- **Canary Release**: Despliegue gradual a un subconjunto de usuarios
- **Rate Limiting**: Limitación de velocidad para proteger APIs
- **Mock**: Simulación de componente externo para pruebas
- **E2E**: End-to-End, pruebas que cubren flujos completos
- **Burn Rate**: Velocidad de consumo del presupuesto de error SLO