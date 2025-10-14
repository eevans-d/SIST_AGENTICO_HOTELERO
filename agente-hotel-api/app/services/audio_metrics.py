# Audio Processing Metrics

from prometheus_client import Counter, Histogram, Gauge

# Contadores para operaciones de audio
audio_operations_total = Counter("audio_operations_total", "Total number of audio operations", ["operation", "status"])

# Histograma para latencia de operaciones de audio
audio_operation_duration_seconds = Histogram(
    "audio_operation_duration_seconds",
    "Duration of audio operations in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Contador para errores específicos de audio
audio_errors_total = Counter("audio_errors_total", "Total number of audio processing errors", ["error_type"])

# Gauge para archivos temporales activos
audio_temp_files_active = Gauge("audio_temp_files_active", "Number of active temporary audio files")

# Histograma para tamaño de archivos de audio
audio_file_size_bytes = Histogram(
    "audio_file_size_bytes",
    "Size of audio files in bytes",
    ["file_type"],
    buckets=[1024, 10240, 102400, 1048576, 10485760],  # 1KB to 10MB
)

# Métricas específicas para cache
audio_cache_operations_total = Counter(
    "audio_cache_operations_total", "Total number of audio cache operations", ["operation", "result"]
)

audio_cache_size_entries = Gauge("audio_cache_size_entries", "Number of entries in audio cache")

audio_cache_memory_bytes = Gauge("audio_cache_memory_bytes", "Memory used by audio cache in bytes")

# Métricas para limpieza automática de caché
audio_cache_cleanup_total = Counter(
    "audio_cache_cleanup_total", "Total number of automatic cache cleanup operations", ["status"]
)

audio_cache_cleanup_freed_bytes = Counter(
    "audio_cache_cleanup_freed_bytes", "Total bytes freed by cache cleanup operations"
)

audio_cache_cleanup_entries_removed = Counter(
    "audio_cache_cleanup_entries_removed", "Total number of entries removed by cache cleanup operations"
)

# Métricas para compresión de caché
audio_cache_compression_operations_total = Counter(
    "audio_cache_compression_operations_total", "Total number of audio cache compression operations", ["operation"]
)

audio_cache_compression_bytes_saved = Counter(
    "audio_cache_compression_bytes_saved", "Total bytes saved by audio cache compression"
)

audio_cache_compression_ratio = Histogram(
    "audio_cache_compression_ratio",
    "Compression ratio achieved in audio cache entries",
    buckets=[1.1, 1.5, 2.0, 3.0, 4.0, 5.0, 10.0],
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

    @staticmethod
    def record_cache_operation(operation: str, result: str):
        """Record audio cache operation"""
        audio_cache_operations_total.labels(operation=operation, result=result).inc()

    @staticmethod
    def update_cache_size(entries: int):
        """Update cache size in entries"""
        audio_cache_size_entries.set(entries)

    @staticmethod
    def update_cache_memory(bytes_used: int):
        """Update cache memory usage"""
        audio_cache_memory_bytes.set(bytes_used)

    @staticmethod
    def record_cache_cleanup(status: str):
        """Record cache cleanup operation"""
        audio_cache_cleanup_total.labels(status=status).inc()

    @staticmethod
    def record_operation_with_value(metric_name: str, value: float):
        """Record a metric with a specific value"""
        if metric_name == "audio_cache_cleanup_freed_mb":
            audio_cache_cleanup_freed_bytes.inc(value * 1024 * 1024)
        elif metric_name == "audio_cache_cleanup_entries_removed":
            audio_cache_cleanup_entries_removed.inc(value)
        elif metric_name == "audio_cache_compression_bytes_saved":
            audio_cache_compression_bytes_saved.inc(value)
        elif metric_name == "audio_cache_compression_ratio":
            audio_cache_compression_ratio.observe(value)

    @staticmethod
    def record_compression_operation(operation: str):
        """Record audio compression operation"""
        audio_cache_compression_operations_total.labels(operation=operation).inc()
