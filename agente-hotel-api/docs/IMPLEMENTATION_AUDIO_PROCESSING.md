# Implementación de Audio Processing

## Resumen del Componente

Se ha implementado el procesamiento de audio en el Agente Hotelero, permitiendo:

1. **Transcripción de audio a texto (STT)** utilizando Whisper
2. **Síntesis de texto a voz (TTS)** utilizando eSpeak
3. **Conversión de formatos de audio** utilizando FFmpeg

## Dependencias Instaladas

- **Sistema**:
  - FFmpeg: Para conversión de formatos de audio
  - eSpeak: Para síntesis de voz
  - Bibliotecas: `libespeak-dev`, `build-essential`

- **Python**:
  - `openai-whisper`: Modelo para STT
  - `aiohttp`: Para descargas asíncronas
  - `aiofiles`: Para manejo asíncrono de archivos

## Archivos Implementados/Modificados

1. **Servicios**:
   - `app/services/audio_processor.py`: Implementación principal con clases para STT, TTS y procesamiento
   - `app/services/audio_metrics.py`: Métricas Prometheus para monitoreo

2. **Excepciones**:
   - `app/exceptions/audio_exceptions.py`: Jerarquía de excepciones para manejo de errores

3. **Utilidades**:
   - `app/utils/audio_converter.py`: Funciones auxiliares para conversión de audio

4. **Tests**:
   - `tests/unit/test_audio_processor.py`: Tests unitarios
   - `tests/integration/test_audio_processor_integration.py`: Tests de integración

5. **Documentación**:
   - `docs/AUDIO_PROCESSING.md`: Guía completa del procesamiento de audio

## Configuración

Las variables de configuración se establecen en `app/core/settings.py`:

```python
# Audio Processing Settings
audio_enabled: bool = True
tts_engine: TTSEngine = TTSEngine.ESPEAK
    
# Whisper STT Configuration
whisper_model: str = "base"  # tiny, base, small, medium, large
whisper_language: str = "es"  # Spanish by default
    
# eSpeak TTS Configuration 
espeak_voice: str = "es"
espeak_speed: int = 150  # words per minute
espeak_pitch: int = 50   # 0-99
    
# Audio Processing Limits
audio_max_size_mb: int = 25  # WhatsApp limit
audio_timeout_seconds: int = 30
```

## Scripts de Prueba

1. **`test_audio.py`**: Prueba básica de componentes TTS y STT
2. **`test_audio_workflow.py`**: Prueba del flujo completo de procesamiento

## Observabilidad

Se han añadido métricas Prometheus para monitorear:

1. Operaciones de audio (contadores)
2. Duración de procesamiento (histogramas)
3. Errores específicos (contadores)
4. Archivos temporales activos (gauge)
5. Tamaño de archivos (histogramas)

## Próximos Pasos

1. Optimizar modelos para producción (ajustes de rendimiento)
2. Implementar almacenamiento en caché para transcripciones frecuentes
3. Añadir soporte para más voces y lenguajes
4. Implementar pruebas de carga para determinar límites del sistema

Para más detalles, consultar la documentación completa en `docs/AUDIO_PROCESSING.md`.