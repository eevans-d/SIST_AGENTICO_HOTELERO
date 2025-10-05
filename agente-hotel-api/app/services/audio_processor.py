# [PROMPT 2.6] app/services/audio_processor.py

import os
import tempfile
from pathlib import Path
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
# import whisper
from ..core.logging import logger


class WhisperSTT:
    def __init__(self):
        # self.model = whisper.load_model("base")
        pass

    async def transcribe(self, audio_file: Path) -> dict:
        # Mock response hasta tener Whisper configurado
        return {
            "text": "Hola, quisiera saber si tienen disponibilidad para el fin de semana.",
            "confidence": 0.9,
            "success": True,
        }


class ESpeakTTS:
    async def synthesize(self, text: str) -> Optional[bytes]:
        # Lógica para generar audio con eSpeak y convertir a OGG con FFmpeg
        return None


class AudioProcessor:
    def __init__(self):
        self.stt = WhisperSTT()
        self.tts = ESpeakTTS()
        self._temp_files_cleanup_timeout = 300  # 5 minutos

    @asynccontextmanager
    async def _temporary_file(self, suffix: str = ".tmp", cleanup_timeout: Optional[int] = None):
        """
        Context manager para manejo seguro de archivos temporales con cleanup automático.
        Previene memory leaks asegurando que archivos temporales se eliminen.
        """
        timeout = cleanup_timeout or self._temp_files_cleanup_timeout
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
        temp_file = Path(temp_path)
        
        try:
            # Cerrar file descriptor inmediatamente para evitar leaks
            os.close(temp_fd)
            yield temp_file
        finally:
            # Cleanup con timeout para evitar bloqueos
            try:
                async def _cleanup():
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            logger.debug(f"Cleaned up temporary file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
                
                await asyncio.wait_for(_cleanup(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout cleaning up temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Error in temp file cleanup: {e}")

    async def transcribe_whatsapp_audio(self, audio_url: str) -> dict:
        """
        Transcribe audio de WhatsApp con manejo seguro de archivos temporales.
        
        Previene memory leaks:
        1. Usa context manager para archivos temporales
        2. Cleanup automático incluso si hay excepciones
        3. Timeouts para operaciones de I/O
        """
        try:
            # Usar context manager para archivos temporales
            async with self._temporary_file(suffix=".ogg") as audio_temp:
                async with self._temporary_file(suffix=".wav") as wav_temp:
                    # 1. Descargar el audio (requiere implementación del downloader)
                    # await self._download_audio(audio_url, audio_temp)
                    
                    # 2. Convertir a WAV
                    # await self._convert_to_wav(audio_temp, wav_temp)
                    
                    # 3. Transcribir con Whisper
                    result = await self.stt.transcribe(wav_temp)
                    
                    # Los archivos se limpian automáticamente al salir del context manager
                    return result
                    
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": str(e)
            }

    async def generate_audio_response(self, text: str) -> Optional[bytes]:
        """
        Genera respuesta de audio con manejo seguro de archivos temporales.
        """
        try:
            async with self._temporary_file(suffix=".ogg") as output_temp:
                # Generar audio
                audio_data = await self.tts.synthesize(text)
                
                # Si TTS genera archivo, leerlo y retornar bytes
                if output_temp.exists():
                    with open(output_temp, "rb") as f:
                        audio_data = f.read()
                
                return audio_data
                
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None
