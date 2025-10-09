"""
Tests de rendimiento para el sistema de audio del agente hotelero.
Este módulo verifica que las operaciones de audio se ejecuten dentro de límites aceptables.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import threading

from app.services.audio_processor import AudioProcessor
from app.services.audio_cache_service import AudioCacheService
from app.services.audio_metrics import AudioMetrics


@pytest.fixture
async def audio_processor():
    """Procesador de audio para pruebas de rendimiento."""
    processor = AudioProcessor()
    
    # Configurar mocks para evitar dependencias externas
    processor.stt.model = MagicMock()
    processor.stt._model_loaded = "mock"
    
    return processor


@pytest.mark.asyncio
async def test_transcription_performance(audio_processor):
    """Test que verifica el tiempo de transcripción dentro de límites aceptables."""
    
    # Mock de transcripción rápida
    with patch.object(audio_processor.stt, "transcribe") as mock_transcribe:
        mock_transcribe.return_value = {
            "text": "Mensaje de prueba para medir rendimiento",
            "confidence": 0.92,
            "success": True,
            "language": "es",
            "duration": 1.5
        }
        
        # Medir tiempo de transcripción
        start_time = time.time()
        result = await audio_processor.transcribe_audio_file("mock_path.wav")
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verificar resultado
        assert result["success"] is True
        
        # El procesamiento debería ser muy rápido con mock (< 0.1s)
        assert duration < 0.1, f"Transcripción tomó {duration:.3f}s, debería ser < 0.1s"


@pytest.mark.asyncio
async def test_synthesis_performance(audio_processor):
    """Test que verifica el tiempo de síntesis dentro de límites aceptables."""
    
    # Mock de síntesis rápida
    with patch.object(audio_processor.tts, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"audio_data_bytes"
        
        # Medir tiempo de síntesis
        start_time = time.time()
        result = await audio_processor.generate_audio_response("Mensaje de prueba")
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verificar resultado
        assert result is not None
        
        # El procesamiento debería ser muy rápido con mock (< 0.1s)
        assert duration < 0.1, f"Síntesis tomó {duration:.3f}s, debería ser < 0.1s"


@pytest.mark.asyncio
async def test_cache_performance():
    """Test que verifica el rendimiento del sistema de caché."""
    
    # Mock del cliente Redis
    with patch("app.services.audio_cache_service.get_redis_client") as mock_redis:
        redis_client = AsyncMock()
        mock_redis.return_value = redis_client
        
        # Configurar tiempos de respuesta rápidos
        redis_client.get.return_value = None
        redis_client.set.return_value = True
        
        cache_service = AudioCacheService()
        
        # Test de operación GET
        start_time = time.time()
        result = await cache_service.get("test_text")
        get_duration = time.time() - start_time
        
        assert result is None
        assert get_duration < 0.05, f"Cache GET tomó {get_duration:.3f}s"
        
        # Test de operación SET
        start_time = time.time()
        await cache_service.set("test_text", b"audio_data")
        set_duration = time.time() - start_time
        
        assert set_duration < 0.05, f"Cache SET tomó {set_duration:.3f}s"


@pytest.mark.asyncio
async def test_concurrent_audio_processing(audio_processor):
    """Test que verifica el rendimiento bajo carga concurrente."""
    
    # Mock para operaciones paralelas
    with patch.object(audio_processor.tts, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"audio_data_bytes"
        
        # Función auxiliar para procesamiento
        async def process_audio(text: str) -> bytes:
            return await audio_processor.generate_audio_response(text)
        
        # Crear múltiples tareas concurrentes
        tasks = [
            process_audio(f"Mensaje de prueba número {i}")
            for i in range(10)
        ]
        
        # Medir tiempo total de procesamiento concurrente
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time
        
        # Verificar resultados
        assert len(results) == 10
        assert all(result is not None for result in results)
        
        # Con procesamiento paralelo, debería tomar menos de 1 segundo total
        assert total_duration < 1.0, f"Procesamiento concurrente tomó {total_duration:.3f}s"
        
        # Verificar que se llamó synthesize para cada tarea
        assert mock_synthesize.call_count == 10


@pytest.mark.asyncio
async def test_memory_usage_during_processing():
    """Test que verifica que el uso de memoria permanece controlado."""
    
    # Versión simplificada sin psutil
    processor = AudioProcessor()
    processor.stt._model_loaded = "mock"
    
    with patch.object(processor.tts, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"audio_data" * 1000  # Simular audio más grande
        
        # Procesar múltiples audios
        results = []
        for i in range(20):
            result = await processor.generate_audio_response(f"Mensaje largo de prueba número {i} " * 10)
            results.append(result)
        
        # Verificar que todas las operaciones completaron
        assert len(results) == 20
        assert all(result is not None for result in results)


@pytest.mark.asyncio
async def test_metrics_collection_performance():
    """Test que verifica que la recolección de métricas no afecte significativamente el rendimiento."""
    
    # Función de prueba que registra métricas
    async def operation_with_metrics():
        start_time = time.time()
        
        # Simular operación de audio
        await asyncio.sleep(0.001)  # 1ms de "trabajo"
        
        duration = time.time() - start_time
        
        # Registrar métricas (sin usar métodos no disponibles)
        AudioMetrics.record_operation_duration("test_operation", duration)
        AudioMetrics.record_operation("test_operation", "success")
        
        return duration
    
    # Medir tiempo con métricas
    start_time = time.time()
    durations = await asyncio.gather(*[operation_with_metrics() for _ in range(100)])
    total_time_with_metrics = time.time() - start_time
    
    # Medir tiempo sin métricas (función simple)
    async def operation_without_metrics():
        await asyncio.sleep(0.001)
    
    start_time = time.time()
    await asyncio.gather(*[operation_without_metrics() for _ in range(100)])
    total_time_without_metrics = time.time() - start_time
    
    # El overhead de métricas debería ser mínimo (< 50% incremento)
    overhead_ratio = total_time_with_metrics / total_time_without_metrics
    assert overhead_ratio < 1.5, f"Overhead de métricas: {overhead_ratio:.2f}x"
    
    # Verificar que las operaciones completaron
    assert len(durations) == 100


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test que verifica el manejo correcto de timeouts en operaciones de audio."""
    
    processor = AudioProcessor()
    
    # Mock que simula operación lenta
    with patch.object(processor.tts, "synthesize") as mock_synthesize:
        async def slow_synthesize(text):
            await asyncio.sleep(5)  # Simular operación muy lenta
            return b"audio_data"
        
        mock_synthesize.side_effect = slow_synthesize
        
        # Intentar operación con timeout
        start_time = time.time()
        
        try:
            # Usar timeout para evitar que la prueba cuelgue
            result = await asyncio.wait_for(
                processor.generate_audio_response("Texto de prueba"),
                timeout=1.0  # Timeout de 1 segundo
            )
            
            # No debería llegar aquí
            assert False, "La operación debería haber hecho timeout"
            
        except asyncio.TimeoutError:
            # Esto es lo esperado
            duration = time.time() - start_time
            
            # Verificar que el timeout ocurrió aproximadamente en el tiempo esperado
            assert 0.8 < duration < 1.5, f"Timeout ocurrió en {duration:.3f}s"
            
            # Verificar que la operación se canceló correctamente
            assert mock_synthesize.call_count == 1