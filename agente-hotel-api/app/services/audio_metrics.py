# Audio Processing Metrics

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict

# Contadores para operaciones de audio
audio_operations_total = Counter(
    'audio_operations_total',
    'Total number of audio operations',
    ['operation', 'status']
)

# Histograma para latencia de operaciones de audio
audio_operation_duration_seconds = Histogram(
    'audio_operation_duration_seconds',
    'Duration of audio operations in seconds',
    ['operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Contador para errores específicos de audio
audio_errors_total = Counter(
    'audio_errors_total',
    'Total number of audio processing errors',
    ['error_type']
)

# Gauge para archivos temporales activos
audio_temp_files_active = Gauge(
    'audio_temp_files_active',
    'Number of active temporary audio files'
)

# Histograma para tamaño de archivos de audio
audio_file_size_bytes = Histogram(
    'audio_file_size_bytes',
    'Size of audio files in bytes',
    ['file_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
)


class AudioMetrics:
    """
    Wrapper class for audio processing metrics
    """
    
    @staticmethod
    def record_operation(operation: str, status: str):
        """Record an audio operation"""
        audio_operations_total.labels(operation=operation, status=status).inc()
    
    @staticmethod
    def record_operation_duration(operation: str, duration: float):
        """Record the duration of an audio operation"""
        audio_operation_duration_seconds.labels(operation=operation).observe(duration)
    
    @staticmethod
    def record_error(error_type: str):
        """Record an audio processing error"""
        audio_errors_total.labels(error_type=error_type).inc()
    
    @staticmethod
    def increment_temp_files():
        """Increment active temporary files counter"""
        audio_temp_files_active.inc()
    
    @staticmethod
    def decrement_temp_files():
        """Decrement active temporary files counter"""
        audio_temp_files_active.dec()
    
    @staticmethod
    def record_file_size(file_type: str, size: int):
        """Record audio file size"""
        audio_file_size_bytes.labels(file_type=file_type).observe(size)