"""
Mejoras de monitoreo y métricas para el sistema de audio del agente hotelero.
Este módulo agrega métricas específicas para el sistema de audio integrado.
"""

from prometheus_client import Counter, Histogram, Gauge
import time

# Métricas específicas del sistema de audio
audio_messages_processed = Counter(
    "audio_messages_processed_total", "Total audio messages processed by the agent", ["channel", "intent", "status"]
)

audio_processing_duration = Histogram(
    "audio_processing_duration_seconds",
    "Time spent processing audio messages end-to-end",
    ["processing_stage", "intent"],
)

audio_quality_metrics = Gauge(
    "audio_quality_score", "Audio quality metrics (confidence, clarity, etc.)", ["metric_type", "language"]
)

tts_cache_metrics = Counter(
    "tts_cache_operations_total", "TTS cache operations", ["operation", "result", "content_type"]
)

stt_accuracy_metrics = Histogram("stt_accuracy_score", "STT accuracy scores", ["language", "audio_quality"])


class AudioIntegrationMetrics:
    """Clase para gestionar métricas del sistema de audio integrado."""

    @staticmethod
    def record_audio_message_processed(channel: str, intent: str, status: str):
        """Registra un mensaje de audio procesado."""
        audio_messages_processed.labels(channel=channel, intent=intent, status=status).inc()

    @staticmethod
    def record_processing_duration(stage: str, intent: str, duration: float):
        """Registra la duración de una etapa del procesamiento de audio."""
        audio_processing_duration.labels(processing_stage=stage, intent=intent).observe(duration)

    @staticmethod
    def record_audio_quality(metric_type: str, language: str, score: float):
        """Registra métricas de calidad de audio."""
        audio_quality_metrics.labels(metric_type=metric_type, language=language).set(score)

    @staticmethod
    def record_cache_operation(operation: str, result: str, content_type: str):
        """Registra operaciones del cache TTS."""
        tts_cache_metrics.labels(operation=operation, result=result, content_type=content_type).inc()

    @staticmethod
    def record_stt_accuracy(language: str, audio_quality: str, accuracy: float):
        """Registra métricas de precisión STT."""
        stt_accuracy_metrics.labels(language=language, audio_quality=audio_quality).observe(accuracy)


class AudioProcessingTracker:
    """Context manager para trackear el procesamiento completo de audio."""

    def __init__(self, intent: str, channel: str):
        self.intent = intent
        self.channel = channel
        self.start_time: float = 0.0
        self.stages = {}

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        total_duration = time.time() - self.start_time
        status = "error" if exc_type else "success"

        # Registrar métricas finales
        AudioIntegrationMetrics.record_audio_message_processed(self.channel, self.intent, status)
        AudioIntegrationMetrics.record_processing_duration("total_processing", self.intent, total_duration)

    def stage(self, stage_name: str):
        """Context manager para trackear una etapa específica."""
        return AudioStageTracker(self, stage_name)


class AudioStageTracker:
    """Context manager para trackear etapas individuales del procesamiento."""

    def __init__(self, parent_tracker: AudioProcessingTracker, stage_name: str):
        self.parent = parent_tracker
        self.stage_name = stage_name
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.parent.stages[self.stage_name] = duration

        AudioIntegrationMetrics.record_processing_duration(self.stage_name, self.parent.intent, duration)


# Función de utilidad para instrumentar el orquestador
async def track_audio_processing(func, intent: str, channel: str, *args, **kwargs):
    """Wrapper para trackear automáticamente el procesamiento de audio."""
    with AudioProcessingTracker(intent, channel):
        return await func(*args, **kwargs)
