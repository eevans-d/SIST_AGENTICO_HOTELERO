# Solución de Problemas de Inicio (Startup Troubleshooting)

Este documento detalla los problemas comunes encontrados durante el inicio de la aplicación y sus soluciones aplicadas.

## 1. Error de Base de Datos: `DuplicatePreparedStatementError`

**Síntoma:**
```
asyncpg.exceptions.DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_1__" already exists
```

**Causa:**
La aplicación está conectada a una base de datos Supabase que utiliza `pgbouncer` en modo de pool de transacciones. `asyncpg` intenta por defecto usar *prepared statements*, lo cual no es compatible con este modo de pooling.

**Solución:**
Se deshabilitaron los *prepared statements* en `app/core/database.py`:
```python
connect_args = {
    "statement_cache_size": 0,
    # "prepare_threshold": None  # Nota: prepare_threshold puede causar errores de argumento inesperado en algunas versiones
}
```

## 2. Error de Métricas: `Duplicated timeseries`

**Síntoma:**
```
ValueError: Duplicated timeseries in CollectorRegistry: {'hotel_reservations_total', ...}
```

**Causa:**
El cliente de Prometheus (`prometheus_client`) utiliza un registro global (`REGISTRY`). Si los módulos que definen métricas son re-importados (por ejemplo, durante un *hot reload* de uvicorn o si hay importaciones circulares/múltiples), se intenta registrar la misma métrica dos veces, causando un error.

**Solución:**
Se implementó un patrón de "obtener o crear" para las métricas en `app/services/business_metrics.py` y `app/monitoring/business_metrics.py`.

```python
def _get_or_create_counter(name, documentation, labelnames=None):
    try:
        return Counter(name, documentation, labelnames)
    except ValueError:
        return REGISTRY._names_to_collectors[name]
```

## 3. Error de Inyección de Dependencias: `NoneType object has no attribute`

**Síntoma:**
```
AttributeError: 'NoneType' object has no attribute 'setex'
```
Ocurriendo en `PerformanceMonitoringService`.

**Causa:**
El servicio de monitoreo de rendimiento se estaba inicializando con dependencias `None` (Redis, MetricsService) en su función de fábrica `get_performance_service`.

**Solución:**
Se actualizó `app/monitoring/performance_service.py` para inyectar correctamente las dependencias asíncronas:

```python
async def get_performance_service() -> PerformanceMonitoringService:
    # ...
    redis = await get_redis()
    # ...
    _performance_service = PerformanceMonitoringService(
        redis_client=redis,
        metrics_service=global_metrics_service
    )
```

## 4. Error de Inicialización de Orchestrator: `Orchestrator not initialized`

**Síntoma:**
El `DLQService` fallaba al intentar reintentar mensajes porque la instancia del `Orchestrator` no estaba disponible o era `None`.

**Causa:**
Dependencia circular y orden de inicialización. El `Orchestrator` es un componente complejo que depende de otros servicios. El `DLQService` intentaba acceder a una variable global `_orchestrator_instance` que podía no estar inicializada.

**Solución:**
1. Se creó una función factoría `get_orchestrator()` en `app/services/orchestrator.py` que maneja la inicialización *lazy* y el patrón Singleton.
2. Se actualizó `app/services/dlq_service.py` para usar `await get_orchestrator()` en lugar de acceder directamente a la variable privada.

---
**Fecha de última actualización:** 23 de Noviembre, 2025
