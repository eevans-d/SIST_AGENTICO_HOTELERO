#!/usr/bin/env python3
import os
import asyncio
import tempfile
from pathlib import Path

from app.services.audio_processor import WhisperSTT, ESpeakTTS
from app.core.settings import Settings

# Para realizar pruebas independientes
async def main():
    settings = Settings()
    print("Configuración de audio:")
    print(f"- Audio enabled: {settings.audio_enabled}")
    print(f"- TTS engine: {settings.tts_engine}")
    print(f"- Whisper model: {settings.whisper_model}")
    print(f"- Espeak voice: {settings.espeak_voice}")
    print()
    
    # Prueba del TTS
    print("Probando eSpeak TTS...")
    tts = ESpeakTTS()
    test_text = "Hola, soy el agente hotelero. ¿En qué puedo ayudarte?"
    
    # Crear archivo temporal para la prueba
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    
    try:
        # Comprobar disponibilidad de eSpeak
        espeak_available = await tts._check_espeak_availability()
        print(f"eSpeak disponible: {espeak_available}")
        
        # Sintetizar voz a archivo
        result = await tts.synthesize_to_file(test_text, temp_path)
        print(f"Síntesis a archivo exitosa: {result}")
        if result:
            print(f"Archivo generado: {temp_path} ({temp_path.stat().st_size} bytes)")
        
        # Prueba STT
        print("\nProbando Whisper STT...")
        stt = WhisperSTT()
        
        # Cargar el modelo
        try:
            await stt._load_model()
            print(f"Modelo cargado: {stt._model_loaded}")
        except Exception as e:
            print(f"Error al cargar el modelo: {e}")
            
    finally:
        # Eliminar archivo temporal
        if temp_path.exists():
            os.unlink(temp_path)
            print(f"Archivo temporal eliminado: {temp_path}")

if __name__ == "__main__":
    asyncio.run(main())