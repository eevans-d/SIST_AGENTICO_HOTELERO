"""
Sistema de compresión adaptiva de audio para optimización de bandwidth y storage.
Ajusta dinámicamente la calidad de audio basado en condiciones de red y uso.
"""

import asyncio
import io
import time
from enum import Enum
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
import logging

import pydub
from pydub import AudioSegment
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

class CompressionLevel(Enum):
    """Niveles de compresión de audio."""
    ULTRA_LOW = "ultra_low"      # 8kHz, 32kbps - Para conexiones muy lentas
    LOW = "low"                  # 16kHz, 64kbps - Para conexiones lentas
    MEDIUM = "medium"            # 22kHz, 128kbps - Calidad balanceada
    HIGH = "high"                # 44kHz, 192kbps - Alta calidad
    LOSSLESS = "lossless"        # Sin compresión - Máxima calidad

class AudioFormat(Enum):
    """Formatos de audio soportados."""
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"
    WAV = "wav"
    M4A = "m4a"

@dataclass
class CompressionSettings:
    """Configuración de compresión de audio."""
    sample_rate: int
    bitrate: int
    format: AudioFormat
    channels: int = 1  # Mono por defecto para llamadas
    normalize: bool = True
    noise_reduction: bool = True

@dataclass
class NetworkConditions:
    """Condiciones de red para compresión adaptiva."""
    bandwidth_kbps: Optional[float] = None
    latency_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    connection_type: Optional[str] = None  # "wifi", "cellular", "ethernet"

class AudioCompressionOptimizer:
    """
    Optimizador de compresión de audio con adaptación automática
    basada en condiciones de red y requisitos de calidad.
    """
    
    COMPRESSION_PROFILES = {
        CompressionLevel.ULTRA_LOW: CompressionSettings(
            sample_rate=8000,
            bitrate=32,
            format=AudioFormat.OPUS,
            channels=1,
            normalize=True,
            noise_reduction=True
        ),
        CompressionLevel.LOW: CompressionSettings(
            sample_rate=16000,
            bitrate=64,
            format=AudioFormat.OPUS,
            channels=1,
            normalize=True,
            noise_reduction=True
        ),
        CompressionLevel.MEDIUM: CompressionSettings(
            sample_rate=22050,
            bitrate=128,
            format=AudioFormat.MP3,
            channels=1,
            normalize=True,
            noise_reduction=False
        ),
        CompressionLevel.HIGH: CompressionSettings(
            sample_rate=44100,
            bitrate=192,
            format=AudioFormat.MP3,
            channels=2,
            normalize=False,
            noise_reduction=False
        ),
        CompressionLevel.LOSSLESS: CompressionSettings(
            sample_rate=44100,
            bitrate=0,  # Sin límite de bitrate
            format=AudioFormat.WAV,
            channels=2,
            normalize=False,
            noise_reduction=False
        )
    }
    
    def __init__(self):
        # Métricas de Prometheus
        self.compression_operations = Counter(
            "audio_compression_operations_total",
            "Operaciones de compresión de audio",
            ["level", "format", "result"]
        )
        self.compression_latency = Histogram(
            "audio_compression_seconds",
            "Latencia de compresión de audio",
            ["level", "format"]
        )
        self.compression_ratio = Histogram(
            "audio_compression_ratio",
            "Ratio de compresión alcanzado",
            ["level", "format"]
        )
        self.audio_quality_score = Gauge(
            "audio_quality_score",
            "Score de calidad de audio (0-1)",
            ["level", "format"]
        )
        
        # Cache de configuraciones optimizadas
        self._adaptive_cache: Dict[str, Tuple[CompressionLevel, float]] = {}
    
    async def compress_audio(
        self,
        audio_data: bytes,
        target_level: Optional[CompressionLevel] = None,
        network_conditions: Optional[NetworkConditions] = None,
        max_size_kb: Optional[int] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Comprime audio con nivel automático o especificado.
        
        Args:
            audio_data: Datos de audio a comprimir
            target_level: Nivel de compresión específico (opcional)
            network_conditions: Condiciones de red para adaptación automática
            max_size_kb: Tamaño máximo del archivo resultante en KB
            
        Returns:
            Tuple con datos comprimidos y metadatos de compresión
        """
        # TEMPORAL FIX: Deshabilitar procesamiento hasta agregar pydub
        logger.warning("AudioCompressionOptimizer temporalmente deshabilitado - retornando audio sin procesar")
        return audio_data, {
            "original_size": len(audio_data),
            "compressed_size": len(audio_data),
            "compression_ratio": 1.0,
            "quality_score": 1.0,
            "level": "passthrough",
            "format": "original",
            "processing_time": 0.0,
            "disabled": True
        }
        
        # Código original comentado hasta agregar pydub a requirements
        """
        start_time = time.time()
        
        try:
            # Cargar audio original
            original_audio = Any.from_file(io.BytesIO(audio_data))
            original_size = len(audio_data)
            
            # Determinar nivel de compresión
            if target_level is None:
                target_level = await self._determine_optimal_compression_level(
                    original_audio, network_conditions, max_size_kb
                )
            
            settings = self.COMPRESSION_PROFILES[target_level]
            
            # Aplicar optimizaciones de audio
            optimized_audio = await self._optimize_audio(original_audio, settings)
            
            # Comprimir según configuración
            compressed_data = await self._apply_compression(optimized_audio, settings)
            compressed_size = len(compressed_data)
            
            # Calcular métricas
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            quality_score = await self._calculate_quality_score(
                original_audio, optimized_audio, settings
            )
            
            # Actualizar métricas
            self.compression_operations.labels(
                level=target_level.value,
                format=settings.format.value,
                result="success"
            ).inc()
            
            self.compression_ratio.labels(
                level=target_level.value,
                format=settings.format.value
            ).observe(compression_ratio)
            
            self.audio_quality_score.labels(
                level=target_level.value,
                format=settings.format.value
            ).set(quality_score)
            
            metadata = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "quality_score": quality_score,
                "level": target_level.value,
                "format": settings.format.value,
                "sample_rate": settings.sample_rate,
                "bitrate": settings.bitrate,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
            logger.info(
                f"Audio comprimido: {original_size} -> {compressed_size} bytes "
                f"(ratio: {compression_ratio:.2f}, calidad: {quality_score:.2f})"
            )
            
            return compressed_data, metadata
            
        except Exception as e:
            self.compression_operations.labels(
                level=target_level.value if target_level else "unknown",
                format="unknown",
                result="error"
            ).inc()
            
            logger.error(f"Error en compresión de audio: {e}")
            raise
        
        finally:
            if target_level:
                self.compression_latency.labels(
                    level=target_level.value,
                    format=self.COMPRESSION_PROFILES[target_level].format.value
                ).observe(time.time() - start_time)
        """
    
    async def _determine_optimal_compression_level(
        self,
        audio: Any,
        network_conditions: Optional[NetworkConditions] = None,
        max_size_kb: Optional[int] = None
    ) -> CompressionLevel:
        """
        Determina el nivel óptimo de compresión basado en múltiples factores.
        """
        # Cache key para condiciones similares
        cache_key = self._generate_cache_key(audio, network_conditions, max_size_kb)
        
        if cache_key in self._adaptive_cache:
            cached_level, cached_time = self._adaptive_cache[cache_key]
            # Usar caché si es reciente (últimos 5 minutos)
            if time.time() - cached_time < 300:
                return cached_level
        
        # Factores base
        audio_duration = len(audio) / 1000.0  # segundos
        audio_size_estimate = len(audio.raw_data)
        
        # Análisis de condiciones de red
        if network_conditions:
            level = await self._analyze_network_conditions(
                network_conditions, audio_duration
            )
        else:
            level = CompressionLevel.MEDIUM  # Default
        
        # Ajustar por restricción de tamaño
        if max_size_kb:
            level = await self._adjust_for_size_constraint(
                audio, level, max_size_kb
            )
        
        # Guardar en caché
        self._adaptive_cache[cache_key] = (level, time.time())
        
        return level
    
    async def _analyze_network_conditions(
        self,
        conditions: NetworkConditions,
        audio_duration: float
    ) -> CompressionLevel:
        """
        Analiza condiciones de red para determinar compresión óptima.
        """
        # Bandwidth disponible
        if conditions.bandwidth_kbps:
            if conditions.bandwidth_kbps < 50:
                return CompressionLevel.ULTRA_LOW
            elif conditions.bandwidth_kbps < 128:
                return CompressionLevel.LOW
            elif conditions.bandwidth_kbps < 512:
                return CompressionLevel.MEDIUM
            else:
                return CompressionLevel.HIGH
        
        # Tipo de conexión
        if conditions.connection_type:
            if conditions.connection_type == "cellular":
                return CompressionLevel.LOW
            elif conditions.connection_type == "wifi":
                return CompressionLevel.MEDIUM
            elif conditions.connection_type == "ethernet":
                return CompressionLevel.HIGH
        
        # Latencia
        if conditions.latency_ms:
            if conditions.latency_ms > 200:
                return CompressionLevel.LOW  # Priorizar velocidad
            elif conditions.latency_ms < 50:
                return CompressionLevel.HIGH  # Puede permitirse calidad
        
        # Pérdida de paquetes
        if conditions.packet_loss_percent:
            if conditions.packet_loss_percent > 5:
                return CompressionLevel.LOW  # Reducir datos
        
        return CompressionLevel.MEDIUM
    
    async def _adjust_for_size_constraint(
        self,
        audio: Any,
        current_level: CompressionLevel,
        max_size_kb: int
    ) -> CompressionLevel:
        """
        Ajusta nivel de compresión para cumplir restricción de tamaño.
        """
        levels_by_compression = [
            CompressionLevel.LOSSLESS,
            CompressionLevel.HIGH,
            CompressionLevel.MEDIUM,
            CompressionLevel.LOW,
            CompressionLevel.ULTRA_LOW
        ]
        
        current_index = levels_by_compression.index(current_level)
        
        # Estimar tamaño con nivel actual
        estimated_size = await self._estimate_compressed_size(audio, current_level)
        
        # Si cumple con la restricción, usar nivel actual
        if estimated_size <= max_size_kb * 1024:
            return current_level
        
        # Buscar nivel que cumpla la restricción
        for i in range(current_index + 1, len(levels_by_compression)):
            level = levels_by_compression[i]
            estimated_size = await self._estimate_compressed_size(audio, level)
            
            if estimated_size <= max_size_kb * 1024:
                return level
        
        # Si ningún nivel cumple, usar el más comprimido
        return CompressionLevel.ULTRA_LOW
    
    async def _estimate_compressed_size(
        self,
        audio: Any,
        level: CompressionLevel
    ) -> int:
        """
        Estima el tamaño comprimido sin procesar completamente.
        """
        settings = self.COMPRESSION_PROFILES[level]
        duration_seconds = len(audio) / 1000.0
        
        if settings.bitrate > 0:
            # Cálculo basado en bitrate
            estimated_bits = settings.bitrate * 1000 * duration_seconds
            return int(estimated_bits / 8)
        else:
            # Para lossless, usar factor de compresión conservador
            return int(len(audio.raw_data) * 0.6)
    
    async def _optimize_audio(
        self,
        audio: Any,
        settings: CompressionSettings
    ) -> Any:
        """
        Aplica optimizaciones de audio antes de la compresión.
        """
        optimized = audio
        
        # Ajustar canales
        if settings.channels == 1 and optimized.channels > 1:
            optimized = optimized.set_channels(1)
        
        # Ajustar sample rate
        if optimized.frame_rate != settings.sample_rate:
            optimized = optimized.set_frame_rate(settings.sample_rate)
        
        # Normalización
        if settings.normalize:
            optimized = await self._normalize_audio(optimized)
        
        # Reducción de ruido básica
        if settings.noise_reduction:
            optimized = await self._reduce_noise(optimized)
        
        return optimized
    
    async def _normalize_audio(self, audio: Any) -> Any:
        """
        Normaliza el volumen del audio.
        """
        # Normalizar a -3dB para evitar clipping
        target_dBFS = -3.0
        change_in_dBFS = target_dBFS - audio.dBFS
        return audio.apply_gain(change_in_dBFS)
    
    async def _reduce_noise(self, audio: Any) -> Any:
        """
        Aplica reducción básica de ruido.
        """
        # Filtro de paso alto simple para eliminar ruido de baja frecuencia
        # Esto es una implementación básica, se puede mejorar con bibliotecas especializadas
        return audio.high_pass_filter(80)
    
    async def _apply_compression(
        self,
        audio: Any,
        settings: CompressionSettings
    ) -> bytes:
        """
        Aplica la compresión final al audio.
        """
        output_buffer = io.BytesIO()
        
        format_params = {
            "format": settings.format.value,
            "bitrate": f"{settings.bitrate}k" if settings.bitrate > 0 else None
        }
        
        # Filtrar parámetros None
        format_params = {k: v for k, v in format_params.items() if v is not None}
        
        audio.export(output_buffer, **format_params)
        return output_buffer.getvalue()
    
    async def _calculate_quality_score(
        self,
        original: Any,
        compressed: Any,
        settings: CompressionSettings
    ) -> float:
        """
        Calcula un score de calidad estimado (0-1).
        """
        # Factores que afectan la calidad
        sample_rate_factor = min(settings.sample_rate / 44100, 1.0)
        bitrate_factor = min(settings.bitrate / 320, 1.0) if settings.bitrate > 0 else 1.0
        channel_factor = settings.channels / 2.0
        
        # Score combinado
        quality_score = (
            sample_rate_factor * 0.4 +
            bitrate_factor * 0.4 +
            channel_factor * 0.2
        )
        
        return min(quality_score, 1.0)
    
    def _generate_cache_key(
        self,
        audio: Any,
        network_conditions: Optional[NetworkConditions],
        max_size_kb: Optional[int]
    ) -> str:
        """
        Genera clave de caché para condiciones similares.
        """
        audio_signature = f"{len(audio)}_{audio.frame_rate}_{audio.channels}"
        
        network_signature = "none"
        if network_conditions:
            network_signature = f"{network_conditions.bandwidth_kbps}_{network_conditions.connection_type}"
        
        size_signature = str(max_size_kb) if max_size_kb else "none"
        
        return f"{audio_signature}_{network_signature}_{size_signature}"
    
    async def get_compression_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de compresión.
        """
        return {
            "cache_size": len(self._adaptive_cache),
            "supported_formats": [fmt.value for fmt in AudioFormat],
            "compression_levels": [level.value for level in CompressionLevel],
            "profiles": {
                level.value: {
                    "sample_rate": settings.sample_rate,
                    "bitrate": settings.bitrate,
                    "format": settings.format.value,
                    "channels": settings.channels
                }
                for level, settings in self.COMPRESSION_PROFILES.items()
            }
        }