#!/usr/bin/env python3
import os
import asyncio
import tempfile
from pathlib import Path
import sys

from app.services.audio_processor import AudioProcessor
from app.core.settings import Settings
from app.core.logging import setup_logging

# Configurar logging para el test
setup_logging()

async def test_full_workflow():
    """Prueba el flujo completo de procesamiento de audio con un archivo de muestra."""
    print("Iniciando prueba de flujo completo de audio...")
    
    # Crear texto de ejemplo y convertirlo a audio
    sample_text = "Hola, bienvenido al Hotel Maravilla. ¿En qué podemos ayudarte hoy?"
    processor = AudioProcessor()
    
    print(f"1. Generando audio a partir del texto: '{sample_text}'")
    audio_data = await processor.generate_audio_response(sample_text)
    
    if not audio_data:
        print("❌ Error: No se pudo generar el audio")
        return
    
    print(f"✅ Audio generado correctamente ({len(audio_data)} bytes)")
    
    # Guardar en un archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(audio_data)
    
    try:
        print(f"2. Audio guardado en archivo temporal: {temp_path}")
        
        # Simular URL para la transcripción (usando file:// para pruebas locales)
        file_url = f"file://{temp_path}"
        
        # En un caso real usaríamos transcribe_whatsapp_audio con una URL de WhatsApp
        # Para pruebas locales, modificamos para usar el archivo directamente
        print(f"3. Transcribiendo audio...")
        
        # Creamos archivo WAV temporal para la transcripción
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = Path(wav_file.name)
            
        await processor._convert_to_wav(temp_path, wav_path)
        print(f"✅ Audio convertido a WAV: {wav_path}")
        
        # Transcribir con Whisper
        try:
            result = await processor.stt.transcribe(wav_path)
            print(f"✅ Transcripción exitosa!")
            print(f"   Texto: '{result['text']}'")
            print(f"   Confianza: {result['confidence']:.2f}")
            print(f"   Duración: {result['duration']:.2f}s")
        except Exception as e:
            print(f"❌ Error en transcripción: {e}")
    
    finally:
        # Limpiar archivos temporales
        for path in [temp_path, wav_path]:
            if path.exists():
                os.unlink(path)
                print(f"🧹 Archivo temporal eliminado: {path}")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())