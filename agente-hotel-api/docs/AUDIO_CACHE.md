# Implementación del Sistema de Caché de Audio

## Introducción

El sistema de caché de audio proporciona una solución para almacenar y reutilizar respuestas de audio generadas por el sistema text-to-speech (TTS). Esta implementación mejora el rendimiento del agente hotelero al evitar generar repetidamente las mismas respuestas de audio, reduciendo así la carga del sistema y mejorando los tiempos de respuesta.

## Componentes Principales

### 1. AudioCacheService

La clase `AudioCacheService` implementa la lógica principal para almacenar, recuperar y gestionar respuestas de audio en caché:

- **Almacenamiento**: Utiliza Redis como backend para almacenar tanto los datos binarios de audio como los metadatos relacionados.
- **TTL Configurable**: Permite definir tiempos de expiración diferentes según el tipo de contenido.
- **Limitación de Tamaño**: Evita almacenar en caché archivos de audio excesivamente grandes.
- **Métricas**: Registra estadísticas de uso y rendimiento.

### 2. Integración con AudioProcessor

El `AudioProcessor` se ha ampliado para utilizar automáticamente el sistema de caché:

- Intenta recuperar respuestas desde la caché antes de generar nuevo audio.
- Guarda en caché nuevas respuestas generadas.
- Proporciona métodos para administrar la caché.

### 3. API de Administración

Se han añadido endpoints en el router de administración para gestionar la caché:

- `/admin/audio-cache/stats`: Obtiene estadísticas de la caché.
- `/admin/audio-cache`: Limpia toda la caché.
- `/admin/audio-cache/entry`: Elimina una entrada específica de la caché.

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
```

## Métricas y Monitoreo

El sistema registra las siguientes métricas para monitoreo:

- **audio_cache_operations_total**: Contador de operaciones de caché (get/set) con etiquetas para resultados (hit/miss).
- **audio_cache_size_entries**: Gauge para el número de entradas en caché.
- **audio_cache_memory_bytes**: Gauge para la memoria total utilizada por la caché.

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
   - Los administradores pueden limpiar manualmente la caché según sea necesario.

## Beneficios

- **Mejora de Rendimiento**: Respuestas más rápidas para mensajes frecuentes.
- **Reducción de Carga**: Menos procesamiento de TTS, especialmente para respuestas comunes.
- **Consistencia**: Las respuestas de audio se mantienen consistentes para el mismo texto.
- **Optimización de Recursos**: Uso más eficiente de CPU y memoria.

## Limitaciones

- Requiere espacio adicional en Redis para almacenar los datos de audio.
- El primer uso de cada mensaje siempre será un cache miss.
- Las respuestas con contenido dinámico tienen menor probabilidad de cache hit.