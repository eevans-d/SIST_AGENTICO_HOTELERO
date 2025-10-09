# Implementación del Sistema de Caché de Audio

## Introducción

El sistema de caché de audio proporciona una solución para almacenar y reutilizar respuestas de audio generadas por el sistema text-to-speech (TTS). Esta implementación mejora el rendimiento del agente hotelero al evitar generar repetidamente las mismas respuestas de audio, reduciendo así la carga del sistema y mejorando los tiempos de respuesta.

## Componentes Principales

### 1. AudioCacheService

La clase `AudioCacheService` implementa la lógica principal para almacenar, recuperar y gestionar respuestas de audio en caché:

- **Almacenamiento**: Utiliza Redis como backend para almacenar tanto los datos binarios de audio como los metadatos relacionados.
- **TTL Configurable**: Permite definir tiempos de expiración diferentes según el tipo de contenido.
- **Limitación de Tamaño**: Evita almacenar en caché archivos de audio excesivamente grandes.
- **Limpieza automática**: Gestión inteligente del tamaño máximo de la caché basada en múltiples factores.
- **Métricas**: Registra estadísticas de uso y rendimiento.

### 2. Integración con AudioProcessor

El `AudioProcessor` se ha ampliado para utilizar automáticamente el sistema de caché:

- Intenta recuperar respuestas desde la caché antes de generar nuevo audio.
- Guarda en caché nuevas respuestas generadas.
- Proporciona métodos para administrar la caché.

### 3. API de Administración

Se han añadido endpoints en el router de administración para gestionar la caché:

- `GET /admin/audio-cache/stats`: Obtiene estadísticas detalladas de la caché, incluida información sobre configuración de limpieza automática.
- `DELETE /admin/audio-cache`: Limpia toda la caché.
- `DELETE /admin/audio-cache/entry`: Elimina una entrada específica de la caché.
- `POST /admin/audio-cache/cleanup`: Ejecuta manualmente el proceso de limpieza automática basada en tamaño.

## Tipos de Contenido y TTL

El sistema permite definir diferentes tiempos de expiración (TTL) según el tipo de contenido:

| Tipo de Contenido | TTL | Descripción |
|---|---|---|
| welcome_message | 7 días | Mensajes de bienvenida y saludos |
| common_responses | 3 días | Respuestas comunes y frecuentes |
| error_messages | 7 días | Mensajes de error |
| hotel_location | 7 días | Respuestas sobre la ubicación del hotel |
| reservation_instructions | 3 días | Instrucciones para reservar |
| room_options | 1 día | Información sobre tipos de habitaciones |
| availability_response | 12 horas | Respuestas sobre disponibilidad |

El TTL predeterminado para otros tipos de contenido es de 24 horas.

## Configuración

Las siguientes opciones están disponibles en la configuración del sistema:

```python
# Audio Cache Settings
audio_cache_enabled: bool = True  # Habilita/deshabilita la caché
audio_cache_ttl_seconds: int = 86400  # TTL predeterminado (24 horas)
audio_cache_max_size_mb: int = 100  # Tamaño máximo de caché en MB
```

## Limpieza Automática de Caché

El sistema implementa una limpieza automática inteligente para mantener el tamaño de la caché bajo control:

### Características Principales:

- **Activación basada en umbrales**: Se inicia automáticamente cuando el tamaño de la caché alcanza el 95% del límite configurado.
- **Reducción controlada**: Reduce el tamaño hasta el 80% del límite máximo.
- **Algoritmo multifactorial**: Selecciona entradas para eliminar basado en varios criterios.
- **Operación asíncrona**: Se ejecuta sin bloquear otras operaciones del sistema.

### Algoritmo de Selección

Las entradas se ordenan para eliminación según una puntuación compuesta por:

- **Antigüedad (70%)**: Entradas más antiguas tienen mayor prioridad para eliminación.
- **Frecuencia de uso (30%)**: Entradas menos utilizadas tienen mayor prioridad.
- **Tipo de contenido**: Factor de ajuste que protege respuestas comunes o de bienvenida.
- **Tamaño**: Se usa como factor de desempate (entradas más grandes se eliminan primero).

### Configuración Interna

```python
# En la clase AudioCacheService
_cleanup_threshold_percent = 95  # Limpiar al 95% del límite
_target_size_percent = 80  # Reducir hasta el 80% después de limpieza
```

### Ejecución Manual

Los administradores pueden invocar manualmente el proceso de limpieza a través del endpoint:

```
POST /admin/audio-cache/cleanup
```

### Métricas de Limpieza

El sistema registra métricas detalladas del proceso de limpieza:

- **audio_cache_cleanup_total**: Contador de operaciones de limpieza y su resultado.
- **audio_cache_cleanup_freed_bytes**: Bytes liberados por las operaciones de limpieza.
- **audio_cache_cleanup_entries_removed**: Número de entradas eliminadas.

## Métricas y Monitoreo

El sistema registra las siguientes métricas para monitoreo en Prometheus:

- **audio_cache_operations_total**: Contador de operaciones de caché (get/set) con etiquetas para resultados (hit/miss).
- **audio_cache_size_entries**: Gauge para el número de entradas en caché.
- **audio_cache_memory_bytes**: Gauge para la memoria total utilizada por la caché.
- **audio_cache_cleanup_total**: Contador de operaciones de limpieza automática por resultado.
- **audio_cache_cleanup_freed_bytes**: Contador acumulativo de bytes liberados por la limpieza.
- **audio_cache_cleanup_entries_removed**: Contador acumulativo de entradas eliminadas.

Estas métricas pueden visualizarse en un dashboard de Grafana para monitorear el comportamiento y rendimiento del sistema de caché.

## Flujo de Trabajo

1. **Petición de Generación de Audio**:
   - El sistema verifica si existe una versión en caché del audio solicitado.
   - Si existe (cache hit), retorna inmediatamente los datos de audio almacenados.
   - Si no existe (cache miss), genera el audio mediante TTS.

2. **Almacenamiento en Caché**:
   - Al generar nuevo audio, se almacena automáticamente en caché para uso futuro.
   - Se guardan tanto los datos binarios como metadatos (tamaño, tiempo de creación, etc.).

3. **Gestión de Caché**:
   - La caché se limpia automáticamente según los TTL configurados.
   - Se ejecuta limpieza automática basada en tamaño cuando se excede el umbral configurado.
   - Los administradores pueden ejecutar limpieza manual desde la API de administración.

## Beneficios

- **Mejora de Rendimiento**: Respuestas más rápidas para mensajes frecuentes.
- **Reducción de Carga**: Menos procesamiento de TTS, especialmente para respuestas comunes.
- **Consistencia**: Las respuestas de audio se mantienen consistentes para el mismo texto.
- **Optimización de Recursos**: Uso más eficiente de CPU y memoria.

## Limitaciones

- Requiere espacio adicional en Redis para almacenar los datos de audio.
- El primer uso de cada mensaje siempre será un cache miss.
- Las respuestas con contenido dinámico tienen menor probabilidad de cache hit.

## Compresión de Audio

El sistema implementa compresión para archivos de audio que superen un umbral de tamaño configurable, lo que optimiza el uso de memoria en Redis:

### Configuración

```python
# Audio Cache Compression Settings
audio_cache_compression_enabled: bool = True  # Activar/desactivar compresión
audio_cache_compression_threshold_kb: int = 100  # Comprimir archivos > 100KB
audio_cache_compression_level: int = 6  # Nivel de compresión (1-9)
```

### Funcionamiento

1. Al almacenar un archivo en caché, el sistema evalúa su tamaño.
2. Si excede el umbral y la compresión está habilitada, se comprime usando zlib.
3. Se almacena con un prefijo identificativo y metadata adicional.
4. Al recuperar, se descomprime automáticamente de forma transparente.
5. Se registran métricas detalladas sobre ratio de compresión y espacio ahorrado.

### Métricas

El sistema expone métricas específicas para la compresión:

- **audio_cache_compression_operations_total**: Operaciones de compresión/descompresión
- **audio_cache_compression_bytes_saved**: Bytes ahorrados mediante compresión
- **audio_cache_compression_ratio**: Ratio de compresión logrado (histograma)

### Estadísticas en Dashboard

El endpoint `/admin/audio-cache/stats` proporciona información detallada sobre la compresión:

```json
{
  "compression": {
    "enabled": true,
    "threshold_kb": 100,
    "compression_level": 6,
    "compressed_entries": 42,
    "compressed_size_mb": 5.2,
    "original_size_mb": 12.8,
    "space_saved_mb": 7.6,
    "compression_ratio": 2.46
  }
}
```

## Planes Futuros

- Políticas de caché más granulares por tenant
- Prefetching para respuestas comunes en segundo plano
- Dashboard de Grafana para visualización de métricas de caché