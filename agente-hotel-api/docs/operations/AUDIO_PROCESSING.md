# Guía de Audio Processing

## Introducción

El sistema de procesamiento de audio del Agente Hotelero permite la interacción con los usuarios mediante mensajes de voz. Esta guía describe cómo funciona el sistema, cómo configurarlo y cómo solucionar problemas comunes.

## Componentes Principales

### 1. Speech-to-Text (STT)

El sistema utiliza **Whisper** para la transcripción de voz a texto:

- **Modelos disponibles**: `tiny`, `base`, `small`, `medium`, `large`
- **Idioma predeterminado**: Español (`es`)
- **Configuración**: Ajustable en `.env` mediante `WHISPER_MODEL` y `WHISPER_LANGUAGE`

### 2. Text-to-Speech (TTS)

El sistema utiliza **eSpeak** para la síntesis de voz:

- **Voces disponibles**: Múltiples idiomas, predeterminado `es` (español)
- **Parámetros ajustables**: Velocidad (words per minute) y tono (pitch)
- **Configuración**: Ajustable en `.env` mediante `ESPEAK_VOICE`, `ESPEAK_SPEED` y `ESPEAK_PITCH`

### 3. Conversión de Audio

Utiliza **FFmpeg** para la conversión entre formatos:

- **Formatos soportados**: Conversión de cualquier formato a WAV (16kHz, mono) para STT
- **Salida TTS**: Formato OGG (Vorbis) para compatibilidad con WhatsApp

## Configuración

### Requisitos del Sistema

1. **FFmpeg**: Necesario para conversión de formatos
2. **eSpeak**: Necesario para síntesis de voz
3. **Python 3.12+**: Con paquetes: `openai-whisper`, `aiohttp`, `aiofiles`

### Variables de Entorno

```
# Habilitar/deshabilitar procesamiento de audio
AUDIO_ENABLED=true

# Configuración Whisper
WHISPER_MODEL=base  # Opciones: tiny, base, small, medium, large
WHISPER_LANGUAGE=es

# Configuración eSpeak
ESPEAK_VOICE=es
ESPEAK_SPEED=150
ESPEAK_PITCH=50

# Límites de procesamiento
AUDIO_MAX_SIZE_MB=25
AUDIO_TIMEOUT_SECONDS=30
```

## Monitoreo

El sistema incluye métricas Prometheus para supervisar el procesamiento de audio:

1. **Contadores**:
   - `audio_operations_total`: Operaciones por tipo y estado
   - `audio_errors_total`: Errores por tipo

2. **Histogramas**:
   - `audio_operation_duration_seconds`: Duración de operaciones
   - `audio_file_size_bytes`: Tamaño de archivos por tipo

3. **Gauges**:
   - `audio_temp_files_active`: Archivos temporales activos

## Pruebas

### Prueba Rápida

```bash
# Prueba básica de STT/TTS
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api
python test_audio.py

# Prueba de flujo completo
python test_audio_workflow.py
```

### Tests Automatizados

```bash
# Tests unitarios
pytest tests/unit/test_audio_processor.py -v

# Tests de integración
pytest tests/integration/test_audio_processor_integration.py -v -m integration
```

## Solución de Problemas

### 1. Transcripción de baja calidad

- **Causa posible**: Modelo Whisper insuficiente
- **Solución**: Actualizar a un modelo más grande en `.env`: `WHISPER_MODEL=medium`

### 2. Errores de FFmpeg

- **Causa posible**: FFmpeg no instalado o versión incompatible
- **Solución**: `sudo apt install -y ffmpeg`
- **Verificación**: `ffmpeg -version`

### 3. Errores de eSpeak

- **Causa posible**: eSpeak no instalado
- **Solución**: `sudo apt install -y espeak espeak-data libespeak-dev`
- **Verificación**: `espeak --version`

### 4. Consumo excesivo de memoria

- **Causa posible**: Modelo Whisper demasiado grande
- **Solución**: Usar un modelo más pequeño o aumentar memoria disponible
- **Monitoreo**: Verificar `audio_temp_files_active` para detectar fugas de archivos temporales

## Recomendaciones de Producción

1. **Modelo Whisper óptimo**: 
   - Para balancear precisión y rendimiento, usar `small` o `medium`
   - Para recursos limitados, usar `base`

2. **Configuración eSpeak recomendada**:
   - Velocidad: 130-150 words per minute
   - Tono (pitch): 40-60 (50 es natural)

3. **Límites de tamaño**:
   - WhatsApp limita mensajes de voz a 16MB
   - Ajustar `AUDIO_MAX_SIZE_MB` acorde a necesidades (default: 25MB)

4. **Timeouts**:
   - Ajustar `AUDIO_TIMEOUT_SECONDS` según capacidad del servidor
   - Valor recomendado: 30-60 segundos