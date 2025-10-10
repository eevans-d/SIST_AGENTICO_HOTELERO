# Mejoras en el Procesamiento de Audio

## Visión General

Como parte de la implementación de las capacidades avanzadas de procesamiento de audio (Fase E.4 y E.4.1), se han desarrollado funcionalidades que permiten al agente hotelero responder con mensajes de audio a consultas realizadas por voz. Esto mejora significativamente la experiencia del usuario al proporcionar una interacción más natural y accesible.

## Respuestas Combinadas de Audio y Ubicación

Como parte de la fase inicial (E.4), se añadió la funcionalidad para manejar respuestas combinadas de audio y ubicación. Esta mejora permite al agente responder con mensajes de voz y datos de ubicación geográfica cuando un usuario envía un mensaje de voz solicitando la ubicación del hotel.

### Componentes Actualizados

1. **Orchestrator (`app/services/orchestrator.py`)**
   - Se agregó un nuevo tipo de respuesta `audio_with_location` para manejar respuestas combinadas
   - Se actualizó el intent `hotel_location` para generar respuestas de audio junto con datos de ubicación cuando se reciben mensajes de voz
   - Se mejoró el método `handle_unified_message` para procesar este nuevo tipo de respuesta

2. **WebHooks Router (`app/routers/webhooks.py`)**
   - Se implementó el manejo de respuestas de tipo `audio_with_location`
   - Se configuró el envío secuencial de mensajes de audio seguidos de mensajes de ubicación
   - Se agregó manejo adecuado del texto descriptivo

3. **Template Service (`app/services/template_service.py`)**
   - Se agregó el método `get_audio_with_location` para generar plantillas combinadas
   - Se estructuraron respuestas que incluyen texto, datos binarios de audio y datos de ubicación geográfica

### Flujo de Trabajo

Cuando un usuario envía un mensaje de audio preguntando por la ubicación del hotel:

1. El mensaje se normaliza a un objeto `UnifiedMessage` con `tipo="audio"`
2. El orquestador lo procesa y detecta la intención `hotel_location`
3. Al detectar que el mensaje original es de audio, genera una respuesta de tipo `audio_with_location`
4. El router de webhooks envía primero un mensaje de audio, opcionalmente un mensaje de texto, y finalmente los datos de ubicación

### Pruebas

Se han añadido pruebas unitarias para verificar:

- El manejo correcto de la intención `hotel_location` tanto para mensajes de texto como de audio
- El procesamiento correcto de respuestas combinadas en el router de webhooks
- La correcta integración entre todos los componentes

### Ejemplos de Uso

```python
# Respuesta del orquestador para un mensaje de audio
{
    "response_type": "audio_with_location",
    "content": {
        "text": "Nuestro hotel está ubicado en Av. Principal 123, Centro, Ciudad.",
        "audio_data": b"...", # datos binarios del audio
        "location": {
            "latitude": 19.4326,
            "longitude": -99.1332,
            "name": "Hotel Test",
            "address": "Av. Principal 123"
        }
    },
    "original_message": mensaje_original
}
```

## Ampliación de Respuestas de Audio para Múltiples Intents (Fase E.4.1)

Como parte de la fase E.4.1, se ha extendido el soporte de respuestas de audio a múltiples intents adicionales, ampliando significativamente la capacidad del agente para proporcionar respuestas de voz en diversos contextos.

### Nuevos Intents Soportados

#### 1. `make_reservation`

Cuando un usuario envía un mensaje de voz solicitando hacer una reserva, el agente responde también con audio, proporcionando una experiencia coherente.

```python
# En orchestrator.py - intent make_reservation
if message.tipo == "audio":
    audio_data = await self.audio_processor.generate_audio_response(response_text)
    return {
        "response_type": "audio",
        "content": {
            "text": response_text,
            "audio_data": audio_data
        },
        "session_data": updated_session
    }
```

#### 2. `show_room_options`

Este intent ahora utiliza un nuevo patrón de respuesta que incluye audio con un mensaje de seguimiento (follow-up) interactivo:

```python
# En orchestrator.py - intent show_room_options
if message.tipo == "audio":
    audio_data = await self.audio_processor.generate_audio_response(intro_text)
    return {
        "response_type": "audio",
        "content": {
            "text": intro_text,
            "audio_data": audio_data,
            "follow_up": {
                "type": "interactive_list",
                "content": interactive_content
            }
        }
    }
```

Este patrón permite enviar primero un mensaje de audio explicativo y luego un mensaje interactivo con opciones, superando la limitación de WhatsApp que no permite combinar audio y elementos interactivos en un solo mensaje.

#### 3. Respuesta de fallback por defecto

Se ha mejorado la respuesta de fallback para mantener la coherencia en la interacción por voz:

```python
# En orchestrator.py - método fallback
if message.tipo == "audio":
    audio_data = await self.audio_processor.generate_audio_response(fallback_text)
    return {
        "response_type": "audio",
        "content": {
            "text": fallback_text,
            "audio_data": audio_data
        }
    }
```

### Mejoras en el Manejo de Webhooks

El router de webhooks se ha actualizado para soportar:

1. **Mensajes de audio simple**: Envío de respuestas de audio con texto opcional
2. **Mensajes de seguimiento (follow-up)**: Procesamiento de mensajes secundarios después de un mensaje de audio
3. **Secuenciación de mensajes**: Envío ordenado de múltiples tipos de mensaje

```python
# En webhooks.py - manejo de audio con follow-up
if response_type == "audio":
    # Procesar mensaje de audio
    await whatsapp_client.send_audio_message(...)
    
    # Si hay follow-up, procesarlo
    if follow_up := content.get("follow_up"):
        follow_up_type = follow_up.get("type")
        follow_up_content = follow_up.get("content")
        
        if follow_up_type == "interactive_list":
            await whatsapp_client.send_interactive_list_message(...)
```

### Nuevas Pruebas

Se han agregado pruebas para verificar:

- `test_audio_response_types.py`: Valida los diferentes tipos de respuesta de audio
- `test_audio_follow_up_webhook.py`: Verifica el manejo de mensajes de audio con seguimiento

### Patrones y Mejores Prácticas

1. **Detección contextual**: Responder con audio solo cuando el mensaje original es de voz
2. **Manejo de errores robusto**: Degradación elegante si la generación de audio falla
3. **Mensajes de seguimiento**: Patrón para combinar audio con otros tipos de mensajes
4. **Consistencia**: Mantener una experiencia coherente en toda la conversación

### Intents Adicionales con Soporte de Audio (Expansión Continua)

Como parte del desarrollo continuo, se han agregado más intents con soporte completo de audio:

#### 4. `guest_services`

- **Tipo de Respuesta**: `audio` o `text`
- **Comportamiento**: Proporciona información sobre servicios para huéspedes (WiFi, desayuno, limpieza, etc.)
- **Patrón**: Responde con audio cuando recibe mensaje de voz, texto para mensajes escritos

#### 5. `hotel_amenities`

- **Tipo de Respuesta**: `audio` o `text`
- **Comportamiento**: Información sobre amenidades del hotel (piscina, gimnasio, restaurante, etc.)
- **Patrón**: Responde con audio cuando recibe mensaje de voz, texto para mensajes escritos

#### 6. `check_in_info`

- **Tipo de Respuesta**: `audio` o `text`
- **Comportamiento**: Información sobre el proceso de check-in (horarios, documentos necesarios)
- **Patrón**: Responde con audio cuando recibe mensaje de voz, texto para mensajes escritos

#### 7. `check_out_info`

- **Tipo de Respuesta**: `audio` o `text`
- **Comportamiento**: Información sobre el proceso de check-out (horarios, extensiones)
- **Patrón**: Responde con audio cuando recibe mensaje de voz, texto para mensajes escritos

#### 8. `cancellation_policy`

- **Tipo de Respuesta**: `audio` o `text`
- **Comportamiento**: Información sobre política de cancelación del hotel
- **Patrón**: Responde con audio cuando recibe mensaje de voz, texto para mensajes escritos

### Plantillas de Respuesta

Todos estos nuevos intents utilizan plantillas de texto bien estructuradas:

```python
TEXT_TEMPLATES = {
    "guest_services": "Nuestros servicios para huéspedes incluyen: WiFi gratuito, desayuno continental de 7:00 a 10:00, servicio de limpieza diario, recepción 24 horas, y servicio de lavandería. ¿Necesitas información específica sobre algún servicio?",
    "hotel_amenities": "Nuestras amenidades incluyen: piscina al aire libre, gimnasio con equipos modernos, restaurante con comida internacional, bar, centro de negocios, estacionamiento gratuito, y spa con tratamientos relajantes. ¿Te interesa conocer más detalles de alguna?",
    "check_in_info": "El check-in es a partir de las 15:00 horas. Necesitarás tu documento de identidad y la confirmación de reserva. Si llegas antes, podemos guardar tu equipaje sin costo adicional. ¿Tienes alguna consulta específica?",
    "check_out_info": "El check-out es hasta las 12:00 horas. Puedes solicitar extensión hasta las 14:00 por un cargo adicional del 50% de la tarifa diaria. También ofrecemos servicio de guardado de equipaje si tu vuelo es más tarde.",
    "cancellation_policy": "Nuestra política de cancelación permite cancelación gratuita hasta 24 horas antes del check-in. Cancelaciones posteriores tienen un cargo del 50% de la primera noche. Para reservas no reembolsables, no se permiten cancelaciones."
}
```

## Consideraciones Futuras

- Añadir soporte para otras respuestas combinadas como "audio_with_image" o "audio_with_buttons"
- Implementar opciones de configuración para controlar si siempre se envía texto junto con audio
- Optimizar el manejo de errores específicos para audio y ubicación
- Explorar servicios TTS en la nube para mejorar la calidad de voz
- Personalizar voces según contexto o preferencias de usuario
- Implementar caché para respuestas de audio frecuentes
- Expandir soporte de audio a todos los intents restantes