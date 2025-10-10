# 🚀 Performance Optimization System

Sistema empresarial completo de optimización automática de performance para el **Agente Hotelero IA System**.

---

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Arquitectura](#arquitectura)
- [Componentes](#componentes)
- [Instalación](#instalación)
- [Uso Rápido](#uso-rápido)
- [API Endpoints](#api-endpoints)
- [Configuración](#configuración)
- [Monitoreo](#monitoreo)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

El **Performance Optimization System** es una suite completa de servicios diseñados para:

✅ **Monitorear** recursos del sistema en tiempo real  
✅ **Optimizar** automáticamente performance de CPU, memoria, base de datos y cache  
✅ **Escalar** servicios dinámicamente basado en demanda  
✅ **Predecir** problemas de performance antes de que ocurran  
✅ **Programar** tareas de mantenimiento en horarios óptimos  
✅ **Alertar** proactivamente sobre problemas de recursos  

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                     (main.py)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Performance API Router                          │
│            (routers/performance.py)                          │
│  • 15+ REST endpoints para gestión de optimización          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Performance │  │  Database   │  │    Cache    │
    │  Optimizer  │  │    Tuner    │  │  Optimizer  │
    └─────────────┘  └─────────────┘  └─────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ↓
                    ┌─────────────────┐
                    │ Resource Monitor│
                    │ • CPU, Memory   │
                    │ • Disk, Network │
                    │ • Predictions   │
                    └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Auto Scaler │  │ Performance │  │ Prometheus  │
    │             │  │  Scheduler  │  │   Metrics   │
    └─────────────┘  └─────────────┘  └─────────────┘
```

---

## 🔧 Componentes

### 1. **Performance Optimizer** (`performance_optimizer.py`)
Optimización integral del sistema con análisis automático.

**Características Clave:**
- ✅ Análisis de CPU, memoria, DB, cache y API
- ✅ Optimizaciones automáticas basadas en thresholds
- ✅ Historial de optimizaciones con tracking de impacto
- ✅ Métricas Prometheus integradas

### 2. **Database Tuner** (`database_tuner.py`)
Optimización avanzada de PostgreSQL.

**Características Clave:**
- ✅ Análisis de consultas lentas (pg_stat_statements)
- ✅ Recomendaciones inteligentes de índices
- ✅ Optimización de configuración automática
- ✅ VACUUM ANALYZE programado

### 3. **Cache Optimizer** (`cache_optimizer.py`)
Optimización inteligente de Redis.

**Características Clave:**
- ✅ Análisis de patrones de uso
- ✅ Hot/cold key identification
- ✅ Estrategias TTL adaptativas
- ✅ Compresión automática de valores grandes
- ✅ Precarga inteligente de datos frecuentes

### 4. **Resource Monitor** (`resource_monitor.py`)
Monitoreo en tiempo real con alertas proactivas.

**Características Clave:**
- ✅ Monitoreo continuo de sistema
- ✅ Alertas con múltiples niveles de severidad
- ✅ Predicciones de tendencias
- ✅ Historial de 24 horas

### 5. **Auto Scaler** (`auto_scaler.py`)
Escalado automático inteligente.

**Características Clave:**
- ✅ Evaluación continua de escalado
- ✅ Reglas configurables por servicio
- ✅ Escalado programado (horas pico/valle)
- ✅ Sistema de confianza para decisiones

### 6. **Performance Scheduler** (`performance_scheduler.py`)
Programador inteligente de tareas.

**Características Clave:**
- ✅ 7 tareas predefinidas de mantenimiento
- ✅ Expresiones CRON para programación
- ✅ Ejecución concurrente controlada
- ✅ Retry automático con backoff

---

## 📦 Instalación

### Requisitos

```bash
# Python 3.12+
python --version

# PostgreSQL 14+
psql --version

# Redis 7+
redis-cli --version
```

### Instalar Dependencias

```bash
# Con Poetry (recomendado)
cd agente-hotel-api
poetry install

# O con pip
pip install -r requirements.txt
```

### Dependencias Adicionales

```toml
# pyproject.toml
psutil = "^5.9.8"      # Métricas de sistema
croniter = "^2.0.1"    # Programación de tareas
```

---

## 🚀 Uso Rápido

### Iniciar Sistema Completo

```bash
# Con Docker Compose
docker-compose up -d

# Los servicios de optimización se inician automáticamente
# Verificar en logs:
docker-compose logs -f agente-api | grep "optimización"
```

### Verificar Estado

```bash
# Estado general
curl http://localhost:8000/api/v1/performance/status | jq

# Métricas actuales
curl http://localhost:8000/api/v1/performance/metrics | jq

# Alertas activas
curl http://localhost:8000/api/v1/performance/alerts | jq
```

### Ejecutar Optimización Manual

```bash
# Optimización completa
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Optimización específica (solo CPU y memoria)
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute \
  -d '{"force": true, "optimization_types": ["cpu", "memory"]}'
```

### Ver Recomendaciones

```bash
# Recomendaciones consolidadas
curl http://localhost:8000/api/v1/performance/recommendations | jq

# Ejemplo de respuesta:
{
  "system_optimization": [...],
  "database_optimization": {
    "indexes": ["CREATE INDEX idx_reservations_date ON reservations(check_in_date)"],
    "configuration": ["shared_buffers = 256MB"]
  },
  "cache_optimization": ["Implementar compresión para keys > 1MB"],
  "priority_actions": [
    {
      "category": "database",
      "action": "Crear índice: idx_reservations_date",
      "impact": "high",
      "effort": "low"
    }
  ]
}
```

---

## 🌐 API Endpoints

### Performance General

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/status` | Estado general del sistema |
| GET | `/api/v1/performance/metrics` | Métricas actuales |
| GET | `/api/v1/performance/recommendations` | Recomendaciones consolidadas |

### Optimización

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/optimization/report` | Reporte de optimizaciones |
| POST | `/api/v1/performance/optimization/execute` | Ejecutar optimización |

### Base de Datos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/database/report` | Análisis de performance de DB |
| POST | `/api/v1/performance/database/optimize` | Optimizar base de datos |

### Cache

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/cache/report` | Análisis de cache |
| POST | `/api/v1/performance/cache/optimize` | Optimizar cache |

### Escalado

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/scaling/status` | Estado de escalado |
| POST | `/api/v1/performance/scaling/evaluate` | Evaluar decisiones |
| POST | `/api/v1/performance/scaling/execute` | Ejecutar escalado |
| PUT | `/api/v1/performance/scaling/rule/{service}/{rule}` | Actualizar regla |

### Alertas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/alerts` | Obtener alertas |
| POST | `/api/v1/performance/alerts/{id}/resolve` | Resolver alerta |

### Benchmarking

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/performance/benchmark` | Ejecutar benchmark |

---

## ⚙️ Configuración

### Thresholds de Optimización

```python
# En performance_optimizer.py
thresholds = {
    'cpu_usage': 75.0,           # % máximo de CPU
    'memory_usage': 80.0,         # % máximo de memoria
    'db_connections': 100,        # Conexiones máximas de BD
    'cache_hit_rate': 0.7,        # Tasa mínima de hit de cache
    'api_response_time': 1000     # Tiempo máximo de respuesta (ms)
}
```

### Configuración de Escalado

```python
# En auto_scaler.py
ServiceConfig(
    name='agente-api',
    tier=ServiceTier.CRITICAL,
    min_instances=2,
    max_instances=10,
    target_cpu_percent=70.0,
    target_memory_percent=80.0,
    scale_up_cooldown=300,    # 5 minutos
    scale_down_cooldown=600   # 10 minutos
)
```

### Tareas Programadas

```python
# En performance_scheduler.py
ScheduledTask(
    id="perf_optimization_regular",
    name="Optimización Regular",
    cron_expression="0 */4 * * *",  # Cada 4 horas
    function_name="run_performance_optimization",
    enabled=True,
    max_duration_seconds=1800  # 30 minutos
)
```

### Variables de Entorno

```bash
# .env
PERFORMANCE_MONITORING_ENABLED=true
PERFORMANCE_AUTO_OPTIMIZE=true
PERFORMANCE_SCHEDULER_ENABLED=true
AUTO_SCALING_ENABLED=true

# Thresholds
PERFORMANCE_CPU_THRESHOLD=75
PERFORMANCE_MEMORY_THRESHOLD=80
PERFORMANCE_DISK_THRESHOLD=85
```

---

## 📊 Monitoreo

### Métricas de Prometheus

```promql
# CPU Usage
system_resource_usage{resource_type="cpu"}

# Memory Usage
system_resource_usage{resource_type="memory"}

# Optimization Duration
performance_optimization_duration_seconds

# Scaling Operations
scaling_operations_total{operation, status}

# Cache Efficiency
cache_optimization_efficiency
```

### Dashboards de Grafana

El sistema incluye dashboards pre-configurados:

1. **Performance Overview** - Vista general del sistema
2. **Resource Monitoring** - Monitoreo detallado de recursos
3. **Optimization History** - Historial de optimizaciones
4. **Scaling Decisions** - Decisiones de escalado
5. **Database Performance** - Performance de PostgreSQL
6. **Cache Performance** - Performance de Redis

### Alertas

Configuradas en AlertManager:

- 🔴 **Critical** - CPU > 90%, Memory > 95%
- 🟠 **Warning** - CPU > 80%, Memory > 85%
- 🟡 **Info** - Optimización ejecutada, escalado realizado

---

## 🔍 Troubleshooting

### Problema: Servicios de optimización no inician

**Síntomas:**
```
⚠️  Error inicializando servicios de optimización
```

**Solución:**
```bash
# Verificar dependencias
poetry install

# Verificar Redis
redis-cli ping

# Verificar PostgreSQL
psql -U postgres -c "SELECT 1"

# Ver logs detallados
docker-compose logs -f agente-api
```

### Problema: Optimizaciones no se ejecutan

**Síntomas:**
- No hay entradas en historial de optimizaciones
- Métricas no mejoran

**Solución:**
```bash
# Verificar scheduler
curl http://localhost:8000/api/v1/performance/status | jq '.optimization_actions_today'

# Ejecutar manualmente
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute \
  -d '{"force": true}'

# Revisar thresholds
curl http://localhost:8000/api/v1/performance/metrics | jq '.thresholds'
```

### Problema: Alertas excesivas

**Síntomas:**
- Demasiadas alertas de recursos
- Alertas repetitivas

**Solución:**
```bash
# Ajustar thresholds en resource_monitor.py
thresholds = {
    ResourceType.CPU: {
        'warning': 80.0,   # Aumentar de 70
        'critical': 90.0   # Aumentar de 85
    }
}

# Ajustar cooldown
config = {
    'alert_cooldown': 600  # Aumentar de 300 (10 minutos)
}
```

### Problema: Escalado automático no funciona

**Síntomas:**
- No se ejecutan decisiones de escalado
- Servicios no escalan

**Solución:**
```bash
# Verificar configuración
curl http://localhost:8000/api/v1/performance/scaling/status | jq

# Evaluar decisiones manualmente
curl -X POST http://localhost:8000/api/v1/performance/scaling/evaluate | jq

# Verificar reglas de escalado
curl http://localhost:8000/api/v1/performance/scaling/status | jq '.service_configs'
```

---

## 📚 Documentación Adicional

- [Guía de Operaciones](./PERFORMANCE_OPTIMIZATION_GUIDE.md)
- [API Documentation](http://localhost:8000/docs)
- [Prometheus Metrics](./metrics.md)
- [Grafana Dashboards](../docker/grafana/dashboards/)

---

## 🎯 Próximas Mejoras

- [ ] Machine Learning para predicciones avanzadas
- [ ] Integración con Kubernetes HPA
- [ ] Optimización predictiva basada en ML
- [ ] Dashboard web dedicado
- [ ] Alertas via Slack/Email
- [ ] Optimización multi-región

---

## 📝 Licencia

Este sistema es parte del **Agente Hotelero IA System**.

---

## 👥 Contribuir

Para contribuir al sistema de optimización:

1. Fork el repositorio
2. Crear branch de feature (`git checkout -b feature/optimization-improvement`)
3. Commit cambios (`git commit -am 'Add: nueva optimización'`)
4. Push al branch (`git push origin feature/optimization-improvement`)
5. Crear Pull Request

---

## 📞 Soporte

Para soporte técnico:
- **Issues**: [GitHub Issues](https://github.com/tu-repo/issues)
- **Documentación**: [Docs](./docs/)
- **Email**: support@example.com

---

**🚀 Sistema de Optimización de Performance v1.0.0**  
*Optimización automática empresarial para Agente Hotelero IA System*
