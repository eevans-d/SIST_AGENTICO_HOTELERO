#!/usr/bin/env python3
import os
import asyncio
import tempfile
from pathlib import Path

from app.services.audio_processor import AudioProcessor
from app.core.logging import setup_logging

# Configurar logging para el test
setup_logging()

async def test_whatsapp_audio_integration():
    """Prueba la integración entre WhatsApp y procesamiento de audio."""
    print("Iniciando prueba de integración WhatsApp-Audio...")
    
    # Inicializar componentes
    # whatsapp_client = WhatsAppMetaClient()  # No usado en esta prueba
    audio_processor = AudioProcessor()
    
    # 1. Generar un mensaje de audio de prueba
    sample_text = "Este es un mensaje de prueba para WhatsApp desde el Agente Hotelero"
    print(f"1. Generando audio a partir del texto: '{sample_text}'")
    audio_data = await audio_processor.generate_audio_response(sample_text)
    
    if not audio_data:
        print("❌ Error: No se pudo generar el audio")
        return
    
    print(f"✅ Audio generado correctamente ({len(audio_data)} bytes)")
    
    # 2. Guardar en un archivo temporal para simulación
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(audio_data)
    
    try:
        print(f"2. Audio guardado en archivo temporal: {temp_path}")
        
        # 3. Simular proceso completo usando archivos locales
        print("3. Simulando procesamiento de mensaje de audio...")
        
        # Simulamos el procesamiento del audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = Path(wav_file.name)
            
        await audio_processor._convert_to_wav(temp_path, wav_path)
        print(f"✅ Audio convertido a WAV: {wav_path}")
        
        # Transcribir con Whisper
        result = await audio_processor.stt.transcribe(wav_path)
        
        print("✅ Transcripción exitosa!")
        print(f"   Texto: '{result['text']}'")
        print(f"   Confianza: {result['confidence']:.2f}")
        print(f"   Duración: {result['duration']:.2f}s")
        
        # 4. Simular envío de mensaje a un número de prueba (reemplazar con número real para pruebas reales)
        test_number = "5491100000000"  # Número de prueba ficticio
        print(f"4. Simularíamos envío de audio a {test_number} (prueba deshabilitada en modo test)")
        
        """
        # Este código se activaría para pruebas reales
        if os.getenv("ENABLE_REAL_WHATSAPP_TESTS") == "true":
            response = await whatsapp_client.send_audio_message(
                to=test_number,
                audio_data=audio_data
            )
            print(f"   Respuesta API WhatsApp: {response}")
        """
            
    finally:
        # Limpiar archivos temporales
        for path in [temp_path, wav_path]:
            if path.exists():
                os.unlink(path)
                print(f"🧹 Archivo temporal eliminado: {path}")

if __name__ == "__main__":
    asyncio.run(test_whatsapp_audio_integration())