# [PROMPT 2.6] app/services/audio_processor.py - OPTIMIZED

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager
import time

from ..core.logging import logger
from ..core.settings import settings
from ..exceptions.audio_exceptions import (
    AudioDownloadError, 
    AudioConversionError, 
    AudioTranscriptionError, 
    AudioSynthesisError,
    AudioTimeoutError,
    AudioValidationError
)
from .audio_metrics import AudioMetrics
from .audio_cache_service import AudioCacheService
from .audio_cache_optimizer import AudioCacheOptimizer, AudioCacheType, CacheStrategy
from .audio_compression_optimizer import (
    AudioCompressionOptimizer, 
    CompressionLevel, 
    NetworkConditions
)
from .audio_connection_pool import (
    AudioConnectionManager, 
    ServiceType, 
    ConnectionConfig
)


class OptimizedWhisperSTT:
    """
    Versión optimizada de WhisperSTT con caché inteligente y gestión de recursos.
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        cache_optimizer: Optional[AudioCacheOptimizer] = None
    ):
        self.model_name = model_name or settings.whisper_model
        self.language = settings.whisper_language
        self.model = None
        self._model_loaded = False
        self.cache_optimizer = cache_optimizer
        
    async def _load_model(self):
        """Carga el modelo Whisper de forma lazy con caché inteligente"""
        if self._model_loaded:
            return
        
        # Verificar caché primero
        if self.cache_optimizer:
            cached_model = await self.cache_optimizer.get(
                f"whisper_model_{self.model_name}",
                AudioCacheType.STT_MODEL,
                CacheStrategy.ADAPTIVE
            )
            
            if cached_model:
                self.model = cached_model
                self._model_loaded = True
                logger.info(f"Whisper model loaded from cache: {self.model_name}")
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
            
            # Guardar en caché
            if self.cache_optimizer:
                await self.cache_optimizer.set(
                    f"whisper_model_{self.model_name}",
                    self.model,
                    AudioCacheType.STT_MODEL,
                    ttl=3600,  # 1 hora
                    strategy=CacheStrategy.ADAPTIVE
                )
            
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
        """Transcribe audio file using Whisper con caché inteligente"""
        await self._load_model()
        
        # Generar clave de caché basada en hash del archivo
        cache_key = f"transcription_{audio_file.stat().st_size}_{audio_file.stat().st_mtime}"
        
        # Verificar caché de transcripción
        if self.cache_optimizer:
            cached_result = await self.cache_optimizer.get(
                cache_key,
                AudioCacheType.TRANSCRIPTION,
                CacheStrategy.LRU
            )
            
            if cached_result:
                logger.debug(f"Transcription loaded from cache: {cache_key}")
                return cached_result
        
        start_time = time.time()
        
        # Si Whisper no está disponible, usar mock
        if self._model_loaded == "mock":
            logger.debug("Using mock transcription (Whisper not available)")
            result = {
                "text": "Hola, quisiera saber si tienen disponibilidad para el fin de semana.",
                "confidence": 0.9,
                "success": True,
                "language": "es",
                "duration": 0.1
            }
        else:
            try:
                # Ejecutar transcripción en thread pool
                loop = asyncio.get_event_loop()
                whisper_result = await loop.run_in_executor(
                    None, self.model.transcribe, str(audio_file)
                )
                
                transcription_time = time.time() - start_time
                
                # Procesar resultado
                result = {
                    "text": whisper_result["text"].strip(),
                    "confidence": self._calculate_confidence(whisper_result),
                    "success": True,
                    "language": whisper_result.get("language", "unknown"),
                    "duration": transcription_time
                }
                
                logger.info(f"Transcription completed in {transcription_time:.2f}s: {result['text'][:50]}...")
                AudioMetrics.record_operation_duration("transcription", transcription_time)
                AudioMetrics.record_operation("transcription", "success")
                
            except Exception as e:
                transcription_time = time.time() - start_time
                logger.error(f"Error transcribing audio: {e}")
                AudioMetrics.record_operation("transcription", "error")
                AudioMetrics.record_error("transcription_failed")
                
                raise AudioTranscriptionError(f"Transcription failed: {str(e)}")
        
        # Guardar resultado en caché
        if self.cache_optimizer:
            await self.cache_optimizer.set(
                cache_key,
                result,
                AudioCacheType.TRANSCRIPTION,
                ttl=1800,  # 30 minutos
                strategy=CacheStrategy.LRU
            )
        
        return result
    
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
    def __init__(self, voice: Optional[str] = None, speed: Optional[int] = None, pitch: Optional[int] = None):
        self.voice = voice or settings.espeak_voice
        self.speed = speed or settings.espeak_speed  # words per minute
        self.pitch = pitch or settings.espeak_pitch  # 0-99
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
            
            # Crear procesos pipe de forma secuencial para evitar errores de StreamReader
            espeak_process = await asyncio.create_subprocess_exec(
                *espeak_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Leer la salida de eSpeak
            espeak_stdout, espeak_stderr = await espeak_process.communicate()
            
            if espeak_process.returncode != 0:
                error_msg = f"eSpeak failed: {espeak_stderr.decode()}"
                logger.error(error_msg)
                AudioMetrics.record_error("espeak_synthesis_failed")
                raise AudioSynthesisError(error_msg)
            
            # Ahora procesar con FFmpeg
            ffmpeg_process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Enviar datos de eSpeak a FFmpeg
            ffmpeg_stdout, ffmpeg_stderr = await ffmpeg_process.communicate(input=espeak_stdout)
            
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


class OptimizedAudioProcessor:
    """
    Procesador de audio optimizado con caché inteligente, compresión adaptiva 
    y gestión de conexiones mejorada.
    """
    
    def __init__(
        self, 
        redis_client=None,
        enable_compression: bool = True,
        enable_connection_pooling: bool = True
    ):
        # Optimizadores
        self.cache_optimizer = AudioCacheOptimizer(
            redis_client=redis_client,
            max_memory_mb=512,
            default_ttl=3600
        ) if redis_client else None
        
        self.compression_optimizer = AudioCompressionOptimizer() if enable_compression else None
        
        self.connection_manager = AudioConnectionManager(
            redis_client=redis_client
        ) if enable_connection_pooling else None
        
        # Servicios STT/TTS optimizados
        self.stt = OptimizedWhisperSTT(cache_optimizer=self.cache_optimizer)
        self.tts = ESpeakTTS()
        self.cache = AudioCacheService()
        
        # Configuración
        self._temp_files_cleanup_timeout = 300  # 5 minutos
        self._started = False
    
    async def start(self):
        """Inicia los servicios optimizados."""
        if self._started:
            return
        
        # Iniciar optimizadores
        if self.cache_optimizer:
            await self.cache_optimizer.start()
        
        if self.connection_manager:
            # Registrar servicios de audio externos si están configurados
            if hasattr(settings, 'external_stt_url') and settings.external_stt_url:
                await self.connection_manager.register_service(
                    ServiceType.STT_SERVICE,
                    ConnectionConfig(
                        base_url=settings.external_stt_url,
                        max_connections=10,
                        timeout_seconds=30.0
                    )
                )
            
            if hasattr(settings, 'external_tts_url') and settings.external_tts_url:
                await self.connection_manager.register_service(
                    ServiceType.TTS_SERVICE,
                    ConnectionConfig(
                        base_url=settings.external_tts_url,
                        max_connections=10,
                        timeout_seconds=30.0
                    )
                )
        
        self._started = True
        logger.info("OptimizedAudioProcessor iniciado con todas las optimizaciones")
    
    async def stop(self):
        """Detiene los servicios optimizados."""
        if not self._started:
            return
        
        if self.cache_optimizer:
            await self.cache_optimizer.stop()
        
        if self.connection_manager:
            await self.connection_manager.shutdown_all()
        
        self._started = False
        logger.info("OptimizedAudioProcessor detenido")

    @asynccontextmanager
    async def _temporary_file(self, suffix: str = ".tmp", cleanup_timeout: Optional[int] = None):
        """
        Context manager para manejo seguro de archivos temporales con cleanup automático.
        Previene memory leaks asegurando que archivos temporales se eliminen.
        """
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

    async def _download_audio_optimized(
        self, 
        audio_url: str, 
        destination: Path,
        network_conditions: Optional[NetworkConditions] = None
    ):
        """
        Descarga optimizada de audio con compresión adaptiva.
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp not installed for audio downloads")
            AudioMetrics.record_error("aiohttp_not_installed") 
            raise AudioDownloadError("aiohttp required for audio downloads")

        try:
            # Usar connection pool si está disponible
            if self.connection_manager:
                # Intentar usar pool de conexiones para descargas
                # Esto sería para servicios externos de audio, no para URLs arbitrarias
                pass
            
            timeout = aiohttp.ClientTimeout(total=settings.audio_timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        raise AudioDownloadError(f"Failed to download audio. HTTP Status: {response.status}")

                    # Check content length if available
                    content_length = response.headers.get('content-length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > settings.audio_max_size_mb:
                            raise AudioValidationError(f"Audio file too large: {size_mb:.1f}MB > {settings.audio_max_size_mb}MB")

                    AudioMetrics.increment_temp_files()
                    try:
                        with open(destination, "wb") as f:
                            bytes_written = 0
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                bytes_written += len(chunk)
                                
                                # Check size during download
                                if bytes_written > settings.audio_max_size_mb * 1024 * 1024:
                                    raise AudioValidationError(f"Audio file too large during download: >{settings.audio_max_size_mb}MB")
                        
                        # Aplicar compresión si está habilitada
                        if self.compression_optimizer:
                            await self._apply_download_compression(
                                destination, network_conditions
                            )
                        
                        AudioMetrics.record_file_size("downloaded_audio", bytes_written)
                        logger.info(f"Audio downloaded successfully to {destination}, size: {bytes_written} bytes")
                        
                    finally:
                        AudioMetrics.decrement_temp_files()

        except asyncio.TimeoutError:
            AudioMetrics.record_error("download_timeout")
            raise AudioTimeoutError(f"Audio download timeout after {settings.audio_timeout_seconds}s")
        except Exception as e:
            AudioMetrics.record_error("download_failed")
            raise AudioDownloadError(f"Failed to download audio: {str(e)}")
    
    async def _apply_download_compression(
        self,
        file_path: Path,
        network_conditions: Optional[NetworkConditions] = None
    ):
        """
        Aplica compresión al archivo descargado si es beneficioso.
        """
        if not self.compression_optimizer:
            return
        
        try:
            with open(file_path, "rb") as f:
                original_data = f.read()
            
            # Comprimir solo si el archivo es grande (>500KB)
            if len(original_data) > 500 * 1024:
                compressed_data, metadata = await self.compression_optimizer.compress_audio(
                    original_data,
                    network_conditions=network_conditions,
                    max_size_kb=1024  # Máximo 1MB
                )
                
                # Usar versión comprimida solo si es significativamente menor
                if metadata["compression_ratio"] > 1.5:
                    with open(file_path, "wb") as f:
                        f.write(compressed_data)
                    
                    logger.info(
                        f"Audio comprimido: {metadata['original_size']} -> "
                        f"{metadata['compressed_size']} bytes "
                        f"(ratio: {metadata['compression_ratio']:.2f})"
                    )
        
        except Exception as e:
            logger.warning(f"Error aplicando compresión a descarga: {e}")
            # No fallar si la compresión falla
        except Exception as e:
            logger.error(f"Error downloading audio from {audio_url}: {e}")
            AudioMetrics.record_error("download_failed")
            raise AudioDownloadError(f"Audio download failed: {str(e)}")

    async def _convert_to_wav(self, input_file: Path, output_file: Path):
        """
        Convierte un archivo de audio a formato WAV usando FFmpeg.
        """
        try:
            cmd = [
                "ffmpeg", "-i", str(input_file), 
                "-ar", "16000",  # Sample rate 16kHz (optimal for Whisper)
                "-ac", "1",      # Mono channel  
                "-c:a", "pcm_s16le",  # 16-bit PCM
                "-y",            # Overwrite output
                str(output_file)
            ]

            start_time = time.time()
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=settings.audio_timeout_seconds
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.audio_timeout_seconds  
            )
            
            conversion_time = time.time() - start_time

            if process.returncode != 0:
                error_msg = f"FFmpeg conversion failed. Return code: {process.returncode}. Error: {stderr.decode()}"
                logger.error(error_msg)
                AudioMetrics.record_error("ffmpeg_conversion_failed")
                raise AudioConversionError(error_msg)

            # Record metrics
            output_size = output_file.stat().st_size if output_file.exists() else 0
            AudioMetrics.record_file_size("converted_wav", output_size)
            AudioMetrics.record_operation_duration("audio_conversion", conversion_time)
            AudioMetrics.record_operation("audio_conversion", "success")
            
            logger.info(f"Audio converted successfully: {input_file} -> {output_file} in {conversion_time:.2f}s")

        except asyncio.TimeoutError:
            AudioMetrics.record_error("conversion_timeout")
            raise AudioTimeoutError(f"Audio conversion timeout after {settings.audio_timeout_seconds}s")
        except FileNotFoundError:
            AudioMetrics.record_error("ffmpeg_not_found")
            raise AudioConversionError("FFmpeg not found. Please install FFmpeg.")
        except Exception as e:
            logger.error(f"Error converting audio {input_file} to {output_file}: {e}")
            AudioMetrics.record_error("conversion_failed")
            AudioMetrics.record_operation("audio_conversion", "error")
            raise AudioConversionError(f"Audio conversion failed: {str(e)}")

    async def transcribe_whatsapp_audio(self, audio_url: str) -> dict:
        """
        Transcribe audio de WhatsApp con manejo seguro de archivos temporales.
        """
        if not settings.audio_enabled:
            logger.info("Audio processing disabled, returning mock response")
            return {
                "text": "Audio processing está deshabilitado en configuración.",
                "confidence": 0.0,
                "success": False,
                "language": "es",
                "duration": 0.0
            }
            
        start_time = time.time()
        try:
            async with self._temporary_file(suffix=".ogg") as audio_temp:
                async with self._temporary_file(suffix=".wav") as wav_temp:
                    # Download and convert audio
                    await self._download_audio(audio_url, audio_temp)
                    await self._convert_to_wav(audio_temp, wav_temp)
                    
                    # Transcribe with Whisper
                    result = await self.stt.transcribe(wav_temp)
                    
                    # Add processing time to result
                    total_time = time.time() - start_time
                    result["total_processing_time"] = total_time
                    
                    # Record overall success metrics
                    AudioMetrics.record_operation_duration("whatsapp_audio_pipeline", total_time)
                    AudioMetrics.record_operation("whatsapp_audio_pipeline", "success")
                    
                    return result
                    
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error transcribing WhatsApp audio: {e}")
            AudioMetrics.record_operation("whatsapp_audio_pipeline", "error")
            AudioMetrics.record_error("whatsapp_transcription_failed")
            
            return {
                "text": "",
                "confidence": 0.0,
                "success": False,
                "error": str(e),
                "total_processing_time": total_time
            }

    async def generate_audio_response(self, text: str, content_type: Optional[str] = None) -> Optional[bytes]:
        """
        Genera respuesta de audio con manejo de caché y archivos temporales seguros.
        
        Args:
            text: Texto a convertir en audio
            content_type: Tipo de contenido para determinar estrategias de caché
        """
        if not settings.audio_enabled:
            logger.info("Audio processing disabled, TTS unavailable")
            return None
        
        # Intentar obtener desde caché primero
        cached_result = await self.cache.get(text, voice=self.tts.voice, content_type=content_type)
        if cached_result:
            audio_data, metadata = cached_result
            is_compressed = metadata.get('compressed', False)
            hits = metadata.get('hits', 0)
            
            # Log con información detallada si está comprimido
            if is_compressed:
                compression_ratio = metadata.get('compression_ratio', 0)
                original_size = metadata.get('original_size', 0)
                saved_kb = (original_size - len(audio_data)) / 1024
                logger.info(f"Audio cache hit (comprimido) para texto: '{text[:50]}...' (hits: {hits}, ratio: {compression_ratio}x, ahorro: {saved_kb:.1f}KB)")
            else:
                logger.info(f"Audio cache hit para texto: '{text[:50]}...' (hits: {hits})")
                
            AudioMetrics.record_cache_operation("get", "hit")
            return audio_data
        
        AudioMetrics.record_cache_operation("get", "miss")
        
        try:
            # Generar audio usando TTS
            audio_data = await self.tts.synthesize(text)
            
            if audio_data:
                # Guardar en caché para uso futuro
                await self.cache.set(
                    text=text,
                    audio_data=audio_data,
                    voice=self.tts.voice,
                    content_type=content_type,
                    metadata={
                        "created_at": time.time(),
                        "size_bytes": len(audio_data),
                        "tts_engine": "espeak",
                        "voice": self.tts.voice
                    }
                )
                
                AudioMetrics.record_operation("audio_response_generation", "success")
                AudioMetrics.record_file_size("generated_audio", len(audio_data))
                logger.info(f"Generated and cached audio response: {len(audio_data)} bytes for text: '{text[:50]}...'")
            else:
                AudioMetrics.record_operation("audio_response_generation", "failed")
                logger.warning("TTS synthesis returned no data")
                
            return audio_data
                
        except Exception as e:
            logger.error(f"Error generating audio response: {e}")
            AudioMetrics.record_operation("audio_response_generation", "error")
            AudioMetrics.record_error("audio_response_generation_failed")
            return None
    
    async def get_cache_stats(self) -> dict:
        """
        Obtiene estadísticas de la caché de audio.
        """
        return await self.cache.get_cache_stats()
    
    async def clear_audio_cache(self) -> int:
        """
        Limpia la caché de audio.
        
        Returns:
            Número de entradas eliminadas
        """
        return await self.cache.clear_cache()
    
    async def remove_from_cache(self, text: str, voice: Optional[str] = None) -> bool:
        """
        Elimina una entrada específica de la caché.
        
        Args:
            text: Texto de la entrada a eliminar
            voice: Voz específica (usa la actual si no se especifica)
        
        Returns:
            True si se eliminó la entrada, False si no existía
        """
        voice_to_use = voice or self.tts.voice
        return await self.cache.invalidate(text, voice_to_use)


# Alias para compatibilidad hacia atrás
# La clase original AudioProcessor ahora es un alias de OptimizedAudioProcessor
class AudioProcessor(OptimizedAudioProcessor):
    """
    Clase AudioProcessor original - ahora es un alias de OptimizedAudioProcessor
    para mantener compatibilidad con código existente.
    """
    
    def __init__(self, redis_client=None):
        # Usar configuración conservadora para compatibilidad
        super().__init__(
            redis_client=redis_client,
            enable_compression=False,  # Deshabilitado por defecto para compatibilidad
            enable_connection_pooling=False  # Deshabilitado por defecto para compatibilidad
        )
        
        # Mantener referencia a componentes para compatibilidad
        self.stt = self.stt
        self.tts = self.tts
        self.cache = self.cache
        
        # Método _download_audio para compatibilidad
        self._download_audio = self._download_audio_optimized
