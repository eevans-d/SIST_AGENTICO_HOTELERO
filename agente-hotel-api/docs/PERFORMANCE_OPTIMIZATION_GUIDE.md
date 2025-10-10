# Performance Optimization System - Operations Guide

## 📊 Sistema de Optimización de Performance

Sistema empresarial completo de optimización automática, monitoreo de recursos y escalado inteligente para el Agente Hotelero IA System.

---

## 🎯 Componentes del Sistema

### 1. **Performance Optimizer**
Optimización integral del sistema con análisis automático y ejecución de mejoras.

**Características:**
- Análisis automático de CPU, memoria, base de datos, cache y API
- Optimizaciones automáticas basadas en thresholds configurables
- Historial completo de optimizaciones con tracking de impacto
- Métricas Prometheus integradas

**Configuración:**
```python
thresholds = {
    'cpu_usage': 75.0,           # % máximo de CPU
    'memory_usage': 80.0,         # % máximo de memoria
    'db_connections': 100,        # Conexiones máximas de BD
    'cache_hit_rate': 0.7,        # Tasa mínima de hit de cache
    'api_response_time': 1000     # Tiempo máximo de respuesta (ms)
}
```

**Endpoints:**
- `GET /api/v1/performance/optimization/report` - Reporte completo
- `POST /api/v1/performance/optimization/execute` - Ejecutar optimización manual
- `GET /api/v1/performance/status` - Estado general del sistema

---

### 2. **Database Performance Tuner**
Optimización avanzada de PostgreSQL con análisis de consultas y recomendaciones de índices.

**Características:**
- Análisis de consultas lentas usando `pg_stat_statements`
- Recomendaciones inteligentes de índices
- Optimización automática de configuración de PostgreSQL
- VACUUM ANALYZE programado
- Detección de índices no utilizados

**Operaciones Principales:**
```bash
# Obtener análisis de consultas lentas
curl http://localhost:8000/api/v1/performance/database/report

# Ejecutar optimización de base de datos
curl -X POST http://localhost:8000/api/v1/performance/database/optimize \
  -d '{"create_indexes": true, "vacuum_analyze": true}'
```

**Consultas Monitoreadas:**
- Consultas con tiempo > 100ms
- Consultas con > 1000 filas examinadas
- Consultas sin índices apropiados

---

### 3. **Cache Optimizer**
Optimización inteligente de Redis con análisis de patrones y estrategias adaptativas.

**Características:**
- Análisis de patrones de uso de cache
- Identificación de hot/cold keys
- Estrategias TTL adaptativas
- Compresión automática de valores grandes (> 1MB)
- Precarga inteligente de datos frecuentes

**Estrategias de Optimización:**
```python
# Hot keys (acceso frecuente)
- TTL extendido: 3600s → 7200s
- Precarga automática
- Prioridad alta en memoria

# Cold keys (acceso infrecuente)
- TTL reducido: 3600s → 1800s
- Candidatos para eliminación
- Prioridad baja en memoria
```

**Endpoints:**
- `GET /api/v1/performance/cache/report` - Análisis de cache
- `POST /api/v1/performance/cache/optimize` - Ejecutar optimización

---

### 4. **Resource Monitor**
Monitoreo en tiempo real de recursos del sistema con alertas proactivas.

**Características:**
- Monitoreo continuo de CPU, memoria, disco, red
- Alertas inteligentes con múltiples niveles de severidad
- Predicciones de tendencias usando regresión lineal
- Historial de métricas (24 horas)

**Niveles de Alerta:**
```
LOW      - Informativa, sin acción requerida
MEDIUM   - Atención necesaria, monitorear
HIGH     - Acción requerida pronto
CRITICAL - Acción inmediata requerida
```

**Thresholds por Defecto:**
```python
CPU:
  Warning: 70%
  Critical: 85%

Memory:
  Warning: 80%
  Critical: 90%

Disk:
  Warning: 80%
  Critical: 90%
```

**Endpoints:**
- `GET /api/v1/performance/metrics` - Métricas actuales
- `GET /api/v1/performance/alerts` - Alertas activas
- `POST /api/v1/performance/alerts/{id}/resolve` - Resolver alerta

---

### 5. **Auto Scaler**
Sistema de escalado automático inteligente basado en métricas y predicciones.

**Características:**
- Evaluación continua de necesidades de escalado
- Reglas configurables por servicio
- Escalado programado para horas pico/valle
- Cooldown configurable entre operaciones

**Servicios Configurados:**
```yaml
agente-api:
  min_instances: 2
  max_instances: 10
  target_cpu: 70%
  scale_up_cooldown: 5min
  scale_down_cooldown: 10min

orchestrator:
  min_instances: 1
  max_instances: 5
  target_cpu: 60%

nlp-engine:
  min_instances: 1
  max_instances: 4
  target_cpu: 80%
```

**Triggers de Escalado:**
- `CPU_HIGH` - Uso alto de CPU
- `MEMORY_HIGH` - Uso alto de memoria
- `LOAD_HIGH` - Load average alto
- `RESPONSE_TIME_HIGH` - Tiempos de respuesta altos
- `PREDICTION_BASED` - Basado en predicciones
- `SCHEDULE_BASED` - Programado por horario

**Endpoints:**
- `GET /api/v1/performance/scaling/status` - Estado de escalado
- `POST /api/v1/performance/scaling/evaluate` - Evaluar decisiones
- `POST /api/v1/performance/scaling/execute` - Ejecutar escalado
- `PUT /api/v1/performance/scaling/rule/{service}/{rule}` - Actualizar regla

---

### 6. **Performance Scheduler**
Programador inteligente de tareas de optimización con expresiones CRON.

**Tareas Programadas por Defecto:**

| Tarea | Frecuencia | Horario | Duración Máx |
|-------|------------|---------|--------------|
| Optimización de Performance | Cada 4 horas | 24/7 | 30 min |
| Mantenimiento de BD | Diario | 3:00 AM | 1 hora |
| Optimización de Cache | Cada 2 horas | 24/7 | 15 min |
| Evaluación de Escalado | Cada 30 min | 8AM-10PM | 5 min |
| Limpieza de Sistema | Diario | 2:00 AM | 20 min |
| Monitoreo de Recursos | Cada 10 min | 24/7 | 3 min |
| Health Check Integral | Cada hora | 24/7 | 10 min |

**Configuración de Horarios:**
```python
# Expresiones CRON
"0 */4 * * *"      # Cada 4 horas
"0 3 * * *"        # Diario a las 3 AM
"*/30 8-22 * * *"  # Cada 30 min de 8 AM a 10 PM
```

---

## 🚀 Uso Operacional

### Inicio del Sistema

```bash
# Iniciar con Docker Compose
docker-compose up -d

# Los servicios de optimización se inician automáticamente
# Logs de inicialización:
# ✅ Servicios de optimización de performance inicializados
# ✅ Performance Optimizer iniciado
# ✅ Resource Monitor iniciado
# ✅ Auto Scaler iniciado
# ✅ Performance Scheduler iniciado
```

### Monitoreo en Tiempo Real

```bash
# Estado general del sistema
curl http://localhost:8000/api/v1/performance/status | jq

# Métricas actuales
curl http://localhost:8000/api/v1/performance/metrics | jq

# Alertas activas
curl http://localhost:8000/api/v1/performance/alerts | jq
```

### Operaciones Manuales

```bash
# Ejecutar optimización manual
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute \
  -H "Content-Type: application/json" \
  -d '{"force": true, "optimization_types": ["cpu", "memory", "cache"]}'

# Optimizar base de datos
curl -X POST http://localhost:8000/api/v1/performance/database/optimize \
  -d '{"create_indexes": true, "vacuum_analyze": true}'

# Optimizar cache
curl -X POST http://localhost:8000/api/v1/performance/cache/optimize \
  -d '{"optimize_ttl": true, "preload_data": true}'

# Evaluar decisiones de escalado
curl -X POST http://localhost:8000/api/v1/performance/scaling/evaluate | jq

# Ejecutar escalado
curl -X POST http://localhost:8000/api/v1/performance/scaling/execute
```

### Obtener Recomendaciones

```bash
# Recomendaciones consolidadas
curl http://localhost:8000/api/v1/performance/recommendations | jq

# Reporte de optimización
curl http://localhost:8000/api/v1/performance/optimization/report | jq

# Reporte de base de datos
curl http://localhost:8000/api/v1/performance/database/report | jq

# Reporte de cache
curl http://localhost:8000/api/v1/performance/cache/report | jq
```

---

## 📈 Métricas de Prometheus

### Métricas de Performance Optimizer

```promql
# Duración de optimizaciones
performance_optimization_duration_seconds

# Operaciones de optimización por tipo
performance_operations_total{operation_type, status}

# Métricas del sistema
system_metrics{metric_type, component}
```

### Métricas de Resource Monitor

```promql
# Uso de recursos
system_resource_usage{resource_type, component}

# Alertas generadas
resource_alerts_total{alert_type, severity}

# Predicciones de recursos
resource_predictions{resource_type, timeframe}
```

### Métricas de Auto Scaler

```promql
# Operaciones de escalado
scaling_operations_total{operation, resource_type, status}

# Instancias activas
active_instances{service_name}

# Eficiencia de escalado
scaling_efficiency{metric_type}
```

### Métricas de Database Tuner

```promql
# Duración de tuning
database_tuning_duration_seconds{operation}

# Consultas lentas
database_slow_queries_total

# Índices creados
database_indexes_created_total
```

### Métricas de Cache Optimizer

```promql
# Optimizaciones de cache
cache_optimization_duration_seconds{operation}

# Hot/cold keys
cache_keys_total{key_type}

# Eficiencia de cache
cache_optimization_efficiency
```

---

## 🔧 Configuración Avanzada

### Ajustar Thresholds

```python
# En performance_optimizer.py
self.thresholds = {
    'cpu_usage': 80.0,        # Aumentar threshold de CPU
    'memory_usage': 85.0,     # Aumentar threshold de memoria
    'cache_hit_rate': 0.75    # Mejorar tasa mínima de cache
}
```

### Configurar Escalado

```python
# En auto_scaler.py
ServiceConfig(
    name='agente-api',
    tier=ServiceTier.CRITICAL,
    min_instances=3,          # Aumentar mínimo
    max_instances=15,         # Aumentar máximo
    target_cpu_percent=65.0,  # Más conservador
    scale_up_cooldown=240,    # Cooldown más corto
    scale_down_cooldown=720   # Cooldown más largo
)
```

### Programar Tareas Personalizadas

```python
# En performance_scheduler.py
ScheduledTask(
    id="custom_optimization",
    name="Optimización Personalizada",
    task_type=TaskType.PERFORMANCE_OPTIMIZATION,
    priority=TaskPriority.HIGH,
    cron_expression="0 */6 * * *",  # Cada 6 horas
    function_name="run_performance_optimization",
    parameters={"force": False, "optimization_types": ["database", "cache"]},
    enabled=True,
    max_duration_seconds=1800,
    retry_count=2,
    retry_delay_seconds=300,
    created_at=datetime.now()
)
```

---

## 🎯 Best Practices

### 1. **Monitoreo Continuo**
- Revisar dashboards de Grafana regularmente
- Configurar alertas en AlertManager
- Revisar logs de optimización semanalmente

### 2. **Optimización Proactiva**
- Ejecutar optimizaciones manuales antes de eventos de alta carga
- Revisar recomendaciones diariamente
- Aplicar índices recomendados en horarios de bajo tráfico

### 3. **Escalado Inteligente**
- Configurar escalado programado para horarios conocidos
- Ajustar thresholds basados en patrones observados
- Mantener margen de seguridad en instancias mínimas

### 4. **Mantenimiento Regular**
- VACUUM ANALYZE semanal en producción
- Limpieza de cache mensual
- Revisión de reglas de escalado mensual

### 5. **Testing de Performance**
- Ejecutar benchmarks antes de cambios mayores
- Validar optimizaciones en staging primero
- Monitorear impacto de optimizaciones

---

## 🚨 Troubleshooting

### Problema: Alta Latencia en API

**Diagnóstico:**
```bash
# Ver métricas de API
curl http://localhost:8000/api/v1/performance/metrics | jq '.current_metrics.api'

# Ver consultas lentas
curl http://localhost:8000/api/v1/performance/database/report | jq '.slow_queries'
```

**Solución:**
1. Ejecutar optimización de base de datos
2. Verificar cache hit rate
3. Considerar escalado horizontal

### Problema: Alto Uso de Memoria

**Diagnóstico:**
```bash
# Ver uso de memoria
curl http://localhost:8000/api/v1/performance/metrics | jq '.current_metrics.memory'

# Ver estado de cache
curl http://localhost:8000/api/v1/performance/cache/report | jq
```

**Solución:**
1. Ejecutar limpieza de cache
2. Implementar compresión
3. Reducir TTL de keys frías

### Problema: CPU Alto Sostenido

**Diagnóstico:**
```bash
# Ver tendencias de CPU
curl http://localhost:8000/api/v1/performance/metrics?include_predictions=true | jq

# Ver procesos
curl http://localhost:8000/api/v1/performance/status | jq
```

**Solución:**
1. Ejecutar auto-optimización
2. Escalar horizontalmente
3. Revisar consultas N+1 en código

---

## 📚 Referencias

- [Prometheus Metrics](../docs/metrics.md)
- [Grafana Dashboards](../docker/grafana/dashboards/)
- [Alert Rules](../docker/alertmanager/config.yml)
- [API Documentation](http://localhost:8000/docs)

---

## 🔄 Changelog

### v1.0.0 (2025-01-XX)
- ✅ Sistema completo de optimización implementado
- ✅ 7 servicios de optimización integrados
- ✅ API REST completa con 15+ endpoints
- ✅ Scheduler con 7 tareas programadas
- ✅ Métricas Prometheus completas
- ✅ Documentación operacional completa
