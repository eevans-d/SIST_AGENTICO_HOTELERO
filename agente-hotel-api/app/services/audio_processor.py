# [PROMPT 2.6] app/services/audio_processor.py

import os
import tempfile
from pathlib import Path
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
import time
# import whisper
from ..core.logging import logger
from ..exceptions.audio_exceptions import AudioDownloadError, AudioConversionError, AudioTranscriptionError, AudioSynthesisError
from .audio_metrics import AudioMetrics


class WhisperSTT:
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self._model_loaded = False
        
    async def _load_model(self):
        """Carga el modelo Whisper de forma lazy"""
        if self._model_loaded:
            return
            
        try:
            # Importar whisper solo cuando se necesite
            import whisper
            
            start_time = time.time()
            logger.info(f"Loading Whisper model: {self.model_name}")
            
            # Ejecutar en thread pool para no bloquear el event loop
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, whisper.load_model, self.model_name
            )
            
            load_time = time.time() - start_time
            logger.info(f"Whisper model loaded in {load_time:.2f}s")
            AudioMetrics.record_operation_duration("model_load", load_time)
            AudioMetrics.record_operation("model_load", "success")
            
            self._model_loaded = True
            
        except ImportError:
            logger.warning("Whisper not installed, using mock transcription")
            AudioMetrics.record_error("whisper_not_installed")
            self._model_loaded = "mock"
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            AudioMetrics.record_error("model_load_failed")
            raise AudioTranscriptionError(f"Failed to load Whisper model: {str(e)}")

    async def transcribe(self, audio_file: Path) -> dict:
        """Transcribe audio file using Whisper"""
        await self._load_model()
        
        start_time = time.time()
        
        # Si Whisper no está disponible, usar mock
        if self._model_loaded == "mock":
            logger.debug("Using mock transcription (Whisper not available)")
            return {
                "text": "Hola, quisiera saber si tienen disponibilidad para el fin de semana.",
                "confidence": 0.9,
                "success": True,
                "language": "es",
                "duration": 0.1
            }
        
        try:
            # Ejecutar transcripción en thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.model.transcribe, str(audio_file)
            )
            
            transcription_time = time.time() - start_time
            
            # Procesar resultado
            processed_result = {
                "text": result["text"].strip(),
                "confidence": self._calculate_confidence(result),
                "success": True,
                "language": result.get("language", "unknown"),
                "duration": transcription_time
            }
            
            logger.info(f"Transcription completed in {transcription_time:.2f}s: {processed_result['text'][:50]}...")
            AudioMetrics.record_operation_duration("transcription", transcription_time)
            AudioMetrics.record_operation("transcription", "success")
            
            return processed_result
            
        except Exception as e:
            transcription_time = time.time() - start_time
            logger.error(f"Error transcribing audio: {e}")
            AudioMetrics.record_operation("transcription", "error")
            AudioMetrics.record_error("transcription_failed")
            
            raise AudioTranscriptionError(f"Transcription failed: {str(e)}")
    
    def _calculate_confidence(self, whisper_result: dict) -> float:
        """Calculate confidence score from Whisper result"""
        # Whisper no proporciona confidence directamente
        # Estimamos basado en la información disponible
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.8  # Default confidence
        
        # Promedio de no-speech probability (invertido)
        total_confidence = 0.0
        total_duration = 0.0
        
        for segment in segments:
            duration = segment.get("end", 0) - segment.get("start", 0)
            no_speech_prob = segment.get("no_speech_prob", 0.2)
            confidence = 1.0 - no_speech_prob
            
            total_confidence += confidence * duration
            total_duration += duration
        
        if total_duration == 0:
            return 0.8
        
        avg_confidence = total_confidence / total_duration
        return min(max(avg_confidence, 0.0), 1.0)


class ESpeakTTS:
    def __init__(self, voice: str = "es", speed: int = 150, pitch: int = 50):
        self.voice = voice
        self.speed = speed  # words per minute
        self.pitch = pitch  # 0-99
        self._espeak_available = None
        
    async def _check_espeak_availability(self) -> bool:
        """Verifica si eSpeak está disponible"""
        if self._espeak_available is not None:
            return self._espeak_available
            
        try:
            process = await asyncio.create_subprocess_exec(
                "espeak", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("eSpeak is available")
                self._espeak_available = True
                AudioMetrics.record_operation("espeak_check", "success")
            else:
                logger.warning("eSpeak check failed")
                self._espeak_available = False
                AudioMetrics.record_operation("espeak_check", "failed")
                
        except FileNotFoundError:
            logger.warning("eSpeak not found in system")
            self._espeak_available = False
            AudioMetrics.record_error("espeak_not_found")
            
        return self._espeak_available

    async def synthesize(self, text: str, output_file: Optional[Path] = None) -> Optional[bytes]:
        """
        Genera audio usando eSpeak y lo convierte a OGG con FFmpeg
        
        :param text: Texto a sintetizar
        :param output_file: Archivo de salida opcional
        :return: Bytes del audio en formato OGG o None
        """
        if not await self._check_espeak_availability():
            logger.warning("eSpeak not available, returning None")
            AudioMetrics.record_error("espeak_unavailable")
            return None
            
        start_time = time.time()
        
        try:
            # Comando eSpeak para generar WAV
            espeak_cmd = [
                "espeak",
                "-v", self.voice,
                "-s", str(self.speed),
                "-p", str(self.pitch),
                "-w", "/dev/stdout",  # Output to stdout
                text
            ]
            
            # Comando FFmpeg para convertir WAV a OGG
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "wav",
                "-i", "pipe:0",  # Input from stdin
                "-c:a", "libvorbis",
                "-q:a", "4",  # Quality level
                "-f", "ogg",
                "pipe:1"  # Output to stdout
            ]
            
            # Crear procesos pipe
            espeak_process = await asyncio.create_subprocess_exec(
                *espeak_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            ffmpeg_process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdin=espeak_process.stdout,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Cerrar stdout de espeak para permitir EOF
            espeak_process.stdout.close()
            
            # Esperar a que ambos procesos terminen
            espeak_stdout, espeak_stderr = await espeak_process.communicate()
            ffmpeg_stdout, ffmpeg_stderr = await ffmpeg_process.communicate()
            
            synthesis_time = time.time() - start_time
            
            # Verificar errores
            if espeak_process.returncode != 0:
                error_msg = f"eSpeak failed: {espeak_stderr.decode()}"
                logger.error(error_msg)
                AudioMetrics.record_error("espeak_synthesis_failed")
                raise AudioSynthesisError(error_msg)
                
            if ffmpeg_process.returncode != 0:
                error_msg = f"FFmpeg conversion failed: {ffmpeg_stderr.decode()}"
                logger.error(error_msg)
                AudioMetrics.record_error("ffmpeg_tts_conversion_failed")
                raise AudioSynthesisError(error_msg)
            
            # Guardar archivo si se especifica
            if output_file:
                with open(output_file, "wb") as f:
                    f.write(ffmpeg_stdout)
                AudioMetrics.record_file_size("ogg_tts", len(ffmpeg_stdout))
            
            logger.info(f"TTS synthesis completed in {synthesis_time:.2f}s, size: {len(ffmpeg_stdout)} bytes")
            AudioMetrics.record_operation_duration("tts_synthesis", synthesis_time)
            AudioMetrics.record_operation("tts_synthesis", "success")
            
            return ffmpeg_stdout
            
        except FileNotFoundError as e:
            error_msg = f"Required tool not found: {str(e)}"
            logger.error(error_msg)
            AudioMetrics.record_error("tts_tool_missing")
            raise AudioSynthesisError(error_msg)
            
        except Exception as e:
            synthesis_time = time.time() - start_time
            error_msg = f"TTS synthesis failed: {str(e)}"
            logger.error(error_msg)
            AudioMetrics.record_operation("tts_synthesis", "error")
            AudioMetrics.record_error("tts_synthesis_failed")
            raise AudioSynthesisError(error_msg)

    async def synthesize_to_file(self, text: str, output_path: Path) -> bool:
        """
        Sintetiza texto y guarda directamente a archivo
        
        :param text: Texto a sintetizar
        :param output_path: Ruta donde guardar el archivo
        :return: True si fue exitoso, False si falló
        """
        try:
            audio_data = await self.synthesize(text, output_path)
            return audio_data is not None
        except Exception as e:
            logger.error(f"Error synthesizing to file {output_path}: {e}")
            return False


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

    async def _download_audio(self, audio_url: str, destination: Path):
        """
        Descarga un archivo de audio desde una URL y lo guarda en la ruta especificada.
        """
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        raise AudioDownloadError(f"Failed to download audio. HTTP Status: {response.status}")

                    with open(destination, "wb") as f:
                        while chunk := await response.content.read(1024):
                            f.write(chunk)

            logger.info(f"Audio downloaded successfully to {destination}")
        except Exception as e:
            logger.error(f"Error downloading audio from {audio_url}: {e}")
            raise AudioDownloadError(f"An error occurred while downloading audio.")

    async def _convert_to_wav(self, input_file: Path, output_file: Path):
        """
        Convierte un archivo de audio a formato WAV usando FFmpeg.
        """
        try:
            cmd = [
                "ffmpeg", "-i", str(input_file), "-ar", "16000", "-ac", "1",
                "-c:a", "pcm_s16le", "-y", str(output_file)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise AudioConversionError(f"FFmpeg conversion failed. Return code: {process.returncode}")

            logger.info(f"Audio converted successfully: {input_file} -> {output_file}")

        except FileNotFoundError:
            raise AudioConversionError("FFmpeg not found. Please install FFmpeg.")
        except Exception as e:
            logger.error(f"Error converting audio {input_file} to {output_file}: {e}")
            raise AudioConversionError(f"An error occurred during audio conversion.")

    async def transcribe_whatsapp_audio(self, audio_url: str) -> dict:
        """
        Transcribe audio de WhatsApp con manejo seguro de archivos temporales.
        """
        try:
            async with self._temporary_file(suffix=".ogg") as audio_temp:
                async with self._temporary_file(suffix=".wav") as wav_temp:
                    await self._download_audio(audio_url, audio_temp)
                    await self._convert_to_wav(audio_temp, wav_temp)
                    result = await self.stt.transcribe(wav_temp)
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
                audio_data = await self.tts.synthesize(text)
                
                if output_temp.exists():
                    with open(output_temp, "rb") as f:
                        audio_data = f.read()
                
                return audio_data
                
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None
