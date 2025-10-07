# Integración de WhatsApp con Procesamiento de Audio

## Descripción General

Este componente permite la integración bidireccional entre WhatsApp y el sistema de procesamiento de audio del Agente Hotelero. Facilita:

1. Recepción y transcripción de mensajes de voz de WhatsApp 
2. Envío de respuestas de audio generadas mediante síntesis de voz

## Flujos de Trabajo

### Recepción y Transcripción de Mensajes de Voz

```
Usuario (WhatsApp) -> Mensaje de Voz -> Webhook -> WhatsAppClient -> 
  -> download_media() -> AudioProcessor -> Whisper STT -> Texto Transcrito -> Orquestador
```

1. El usuario envía un mensaje de voz por WhatsApp
2. El webhook del agente recibe la notificación con el `media_id` del audio
3. `WhatsAppClient.download_media()` descarga el archivo de audio
4. `WhatsAppClient.process_audio_message()` coordina el procesamiento
5. `AudioProcessor` convierte el archivo y lo transcribe con Whisper
6. El texto transcrito se envía al orquestador para procesamiento normal

### Envío de Respuestas de Audio

```
Orquestador -> Texto Respuesta -> AudioProcessor -> eSpeak TTS -> 
  -> Audio OGG -> WhatsAppClient.send_audio_message() -> Usuario (WhatsApp)
```

1. El orquestador decide enviar una respuesta de audio
2. `AudioProcessor.generate_audio_response()` crea el audio con eSpeak
3. `WhatsAppClient.send_audio_message()` sube el audio a WhatsApp API
4. El mensaje de audio se envía al usuario

### Respuestas Combinadas (Audio + Ubicación)

```
Orquestador -> (Texto + Coordenadas) -> [AudioProcessor + TemplateService] -> 
  -> Respuesta Combinada -> WebhookRouter -> [Audio -> Texto -> Ubicación] -> Usuario (WhatsApp)
```

1. El orquestador detecta una intención que requiere respuesta combinada (ej: `hotel_location`)
2. Determina que el mensaje de entrada era de voz y debe responder con audio
3. Genera audio con `AudioProcessor.generate_audio_response()`
4. Obtiene datos de ubicación con `TemplateService.get_location()`
5. Construye respuesta combinada con `TemplateService.get_audio_with_location()`
6. El router de webhooks envía secuencialmente:
   - Primero el mensaje de audio
   - Después un mensaje de texto (opcional)
   - Finalmente la ubicación con mapa

## Componentes Clave

### WhatsAppClient

Nuevos métodos añadidos:

1. **`send_audio_message(to, audio_data, filename)`**
   - Sube archivos de audio OGG a la API de WhatsApp (proceso en dos pasos)
   - Envía el mensaje de audio al destinatario usando el ID obtenido
   - Registra métricas y logs de éxito/error

2. **`process_audio_message(media_id)`**
   - Descarga un archivo de audio por su ID
   - Coordina la conversión y transcripción
   - Devuelve resultado con texto, confianza y metadatos

### AudioProcessor

Componentes utilizados:

1. **`WhisperSTT`**
   - Transcribe mensajes de voz a texto
   - Proporciona información de confianza y duración

2. **`ESpeakTTS`**
   - Genera respuestas de voz a partir de texto
   - Optimizado para voces en español

### TemplateService

Nuevo método añadido:

1. **`get_audio_with_location(location_template, text, audio_data, **kwargs)`**
   - Combina datos de audio y ubicación en una sola estructura
   - Facilita respuestas enriquecidas para intents que involucran ubicaciones
   - Permite al router de webhooks enviar correctamente ambos tipos de contenido

### Orchestrator

Mejoras realizadas:

1. **Detección de tipo de mensaje**
   - Identifica mensajes de audio para decidir respuestas apropiadas
   - Mantiene contexto del tipo de mensaje durante el procesamiento

2. **Nuevo tipo de respuesta `audio_with_location`**
   - Para responder a preguntas de ubicación que llegan como audio
   - Genera respuestas más ricas y naturales combinando múltiples tipos de mensajes

## Consideraciones Técnicas

1. **Formato de Audio**
   - WhatsApp utiliza OGG con codec Opus para mensajes de voz
   - Conversión a WAV requerida para Whisper
   - Respuestas generadas en OGG con codec Vorbis

2. **Flujo de Archivos**
   - Archivos temporales utilizados para la conversión
   - Limpieza automática para evitar memory leaks

3. **Métricas Prometheus**
   - `whatsapp_messages_sent_total{type="audio", status="*"}`
   - `whatsapp_media_downloads_total{status="*"}`
   - `audio_operation_duration_seconds{operation="*"}`

## Ejemplos de Uso

### Procesar mensaje de voz recibido

```python
# En el webhook
async def handle_whatsapp_audio_message(media_id: str, from_number: str):
    client = WhatsAppMetaClient()
    
    # Procesar el audio
    transcription = await client.process_audio_message(media_id)
    
    if transcription["success"]:
        # Usar el texto transcrito
        text = transcription["text"]
        # Enviar a sistema NLP...
    else:
        # Manejar error
        error_message = transcription.get("error", "Error desconocido")
        # Notificar al usuario...
```

### Enviar respuesta de audio

```python
async def send_audio_response(to: str, text: str):
    audio_processor = AudioProcessor()
    client = WhatsAppMetaClient()
    
    # Generar audio
    audio_data = await audio_processor.generate_audio_response(text)
    
    if audio_data:
        # Enviar mensaje de audio
        await client.send_audio_message(
            to=to,
            audio_data=audio_data,
            filename="respuesta.ogg"
        )
        return True
    
    return False
```

### Enviar respuesta combinada de audio y ubicación

```python
async def handle_location_query_with_audio(to: str, text: str, location_data: dict):
    """
    Manejador para consultas de ubicación que llegan como mensajes de voz.
    Envía una respuesta combinada con audio, texto y mapa de ubicación.
    """
    orchestrator = Orchestrator(
        pms_adapter=get_pms_adapter(),
        session_manager=SessionManager(get_redis()),
        lock_service=LockService(get_redis())
    )
    
    # Simular procesamiento de intent para hotel_location
    result = await orchestrator.handle_intent(
        {
            "intent": {"name": "hotel_location", "confidence": 0.95},
            "language": "es"
        },
        {}, # Sesión vacía
        UnifiedMessage(
            message_id="123",
            canal="whatsapp",
            user_id=to,
            timestamp_iso="2023-01-01T00:00:00Z",
            tipo="audio",  # Importante: especificar tipo audio
            texto="¿Dónde está ubicado el hotel?"
        )
    )
    
    # Procesar el resultado (tipo audio_with_location)
    if result.get("response_type") == "audio_with_location":
        content = result.get("content", {})
        client = WhatsAppMetaClient()
        
        # Enviar audio
        if content.get("audio_data"):
            await client.send_audio_message(
                to=to,
                audio_data=content["audio_data"]
            )
        
        # Enviar texto
        if text := content.get("text"):
            await client.send_message(
                to=to, 
                text=text
            )
        
        # Enviar ubicación
        location = content.get("location", {})
        if location:
            await client.send_location_message(
                to=to,
                latitude=location.get("latitude", 0),
                longitude=location.get("longitude", 0),
                name=location.get("name"),
                address=location.get("address")
            )
        
        await client.close()
        return True
        
    return False
```

## Pruebas

Para ejecutar las pruebas de esta integración:

```bash
# Prueba del flujo completo
python test_whatsapp_audio.py

# Tests unitarios
pytest tests/unit/test_whatsapp_audio.py -v

# Pruebas de integración para mensajes combinados
pytest tests/unit/test_audio_location_webhook.py -v
pytest tests/unit/test_location_handler.py -v
```

## Actualizaciones Recientes (7 de octubre, 2025)

### Nuevas Características

1. **Respuestas combinadas audio + ubicación**
   - Implementadas para intent `hotel_location`
   - Capacidad de responder con audio cuando el mensaje original era de voz
   - Estructura de datos unificada para este tipo de respuestas

2. **Mejoras en Router de Webhooks**
   - Manejo secuencial para respuestas combinadas
   - Envío ordenado: audio → texto → ubicación
   - Tratamiento apropiado de respuestas parciales

3. **TemplateService Mejorado**
   - Nuevo método `get_audio_with_location` para respuestas combinadas
   - Mantiene separación de responsabilidades en la generación de contenido

### Problemas Resueltos

1. **Compatibilidad de Formatos**
   - Asegurada compatibilidad entre formato de audio generado y API de WhatsApp
   - Manejo adecuado de mensajes sin audio o con audio corrupto

2. **Flujo de Respuestas Ricas**
   - Ordenamiento correcto de mensajes múltiples
   - Garantía de entrega consistente incluso con fallas parciales

3. **Métricas y Logging**
   - Adición de métricas para nuevos flujos de procesamiento
   - Logs detallados para diagnóstico de problemas en producción

## Próximos Pasos

1. **Expansión de Intents**
   - Añadir soporte para audio en más tipos de intents (check_availability, make_reservation)
   - Implementar decisiones inteligentes sobre cuándo usar audio vs. texto

2. **Mejoras de Calidad**
   - Explorar modelos TTS más naturales (Coqui TTS, Azure, AWS Polly)
   - Optimizar tiempos de procesamiento y tamaños de archivo

3. **Personalización**
   - Permitir selección de voz basada en preferencias del usuario
   - Ajustar velocidad y tono según el contexto del mensaje