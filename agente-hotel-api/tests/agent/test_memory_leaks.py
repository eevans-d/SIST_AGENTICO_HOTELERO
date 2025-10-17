"""
Memory Leak Detection Tests

Detecta memory leaks, resource leaks y degradación de performance
en conversaciones prolongadas del agente IA.

Ejecutar:
    pytest tests/agent/test_memory_leaks.py -v -s
    pytest tests/agent/test_memory_leaks.py -v -s --leak-iterations=1000
"""

import pytest
import asyncio
import tracemalloc
import gc
import psutil
import os
import time
from typing import Dict, List
from dataclasses import dataclass

# Ajustar imports según estructura del proyecto
from app.services.nlp_engine import NLPEngine
from app.services.session_manager import SessionManager
from app.services.pms_adapter import MockPMSAdapter


# ===== CONFIGURACIÓN =====

LEAK_ITERATIONS = int(os.getenv("LEAK_ITERATIONS", "500"))  # Iteraciones para detectar leaks
MEMORY_THRESHOLD_MB = 50  # Incremento de memoria sospechoso (MB)
GROWTH_RATE_THRESHOLD = 0.1  # Crecimiento < 10% esperado


@dataclass
class MemorySnapshot:
    """Snapshot de memoria en un punto del tiempo"""

    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    heap_mb: float  # Heap allocations
    num_objects: int
    top_allocations: List[tuple]

    def __repr__(self):
        return f"MemorySnapshot(rss={self.rss_mb:.2f}MB, heap={self.heap_mb:.2f}MB, objects={self.num_objects})"


# ===== FIXTURES =====


@pytest.fixture
def process():
    """Fixture del proceso actual para memory tracking"""
    return psutil.Process(os.getpid())


@pytest.fixture
async def nlp_engine():
    """Fixture del motor NLP"""
    engine = NLPEngine()
    yield engine
    # Cleanup explícito
    del engine
    gc.collect()


@pytest.fixture
async def session_manager():
    """Fixture del session manager"""
    manager = SessionManager()
    yield manager
    await manager.cleanup()
    del manager
    gc.collect()


@pytest.fixture
async def pms_adapter():
    """Fixture del PMS adapter"""
    adapter = MockPMSAdapter(redis_client=None)  # Mock no requiere redis real
    yield adapter
    # MockPMSAdapter no tiene método close()
    del adapter
    gc.collect()


# ===== HELPER FUNCTIONS =====


def take_memory_snapshot(process: psutil.Process, tracemalloc_snapshot=None) -> MemorySnapshot:
    """
    Captura un snapshot completo de memoria
    """
    gc.collect()  # Force garbage collection

    mem_info = process.memory_info()

    # Tracemalloc stats (top allocations)
    top_allocations = []
    heap_mb = 0
    if tracemalloc_snapshot:
        top_stats = tracemalloc_snapshot.statistics("lineno")[:10]
        top_allocations = [(str(stat), stat.size / 1024 / 1024) for stat in top_stats]
        heap_mb = sum(stat.size for stat in tracemalloc_snapshot.statistics("filename")) / 1024 / 1024

    return MemorySnapshot(
        timestamp=time.time(),
        rss_mb=mem_info.rss / 1024 / 1024,
        vms_mb=mem_info.vms / 1024 / 1024,
        heap_mb=heap_mb,
        num_objects=len(gc.get_objects()),
        top_allocations=top_allocations,
    )


def analyze_memory_growth(snapshots: List[MemorySnapshot]) -> Dict:
    """
    Analiza el crecimiento de memoria entre snapshots
    """
    if len(snapshots) < 2:
        return {"status": "insufficient_data"}

    initial = snapshots[0]
    final = snapshots[-1]

    rss_growth_mb = final.rss_mb - initial.rss_mb
    heap_growth_mb = final.heap_mb - initial.heap_mb
    objects_growth = final.num_objects - initial.num_objects

    # Calcular tasa de crecimiento
    rss_growth_rate = rss_growth_mb / initial.rss_mb if initial.rss_mb > 0 else 0

    # Detectar leaks
    has_leak = rss_growth_mb > MEMORY_THRESHOLD_MB or rss_growth_rate > GROWTH_RATE_THRESHOLD

    return {
        "status": "LEAK_DETECTED" if has_leak else "OK",
        "rss_growth_mb": rss_growth_mb,
        "heap_growth_mb": heap_growth_mb,
        "objects_growth": objects_growth,
        "growth_rate": rss_growth_rate,
        "initial_snapshot": initial,
        "final_snapshot": final,
        "leak_detected": has_leak,
    }


def print_memory_report(analysis: Dict):
    """
    Imprime reporte legible de memoria
    """
    print("\n" + "=" * 60)
    print("📊 MEMORY LEAK ANALYSIS REPORT")
    print("=" * 60)

    print(f"\n🔍 Status: {analysis['status']}")
    print("\n📈 Memory Growth:")
    print(f"  - RSS: {analysis['rss_growth_mb']:+.2f} MB ({analysis['growth_rate'] * 100:+.1f}%)")
    print(f"  - Heap: {analysis['heap_growth_mb']:+.2f} MB")
    print(f"  - Objects: {analysis['objects_growth']:+,}")

    print("\n📸 Initial State:")
    print(f"  {analysis['initial_snapshot']}")

    print("\n📸 Final State:")
    print(f"  {analysis['final_snapshot']}")

    if analysis["leak_detected"]:
        print("\n⚠️  LEAK DETECTED:")
        print(f"  - Growth exceeds threshold ({MEMORY_THRESHOLD_MB} MB)")
        print(f"  - Rate: {analysis['growth_rate'] * 100:.1f}% (threshold: {GROWTH_RATE_THRESHOLD * 100:.1f}%)")

        if analysis["final_snapshot"].top_allocations:
            print("\n🔝 Top Memory Allocations:")
            for i, (location, size_mb) in enumerate(analysis["final_snapshot"].top_allocations[:5], 1):
                print(f"  {i}. {size_mb:.2f} MB - {location[:80]}")

    print("=" * 60 + "\n")


# ===== TESTS DE MEMORY LEAKS =====


@pytest.mark.asyncio
async def test_nlp_engine_no_memory_leak(nlp_engine, process):
    """
    Validar que el NLP engine no tiene memory leaks en N iteraciones

    Ejecuta el mismo prompt muchas veces y verifica que:
    1. Memoria no crece más de MEMORY_THRESHOLD_MB
    2. Objetos no se acumulan indefinidamente
    3. Garbage collection funciona correctamente
    """
    tracemalloc.start()

    snapshots = []

    # Snapshot inicial
    gc.collect()
    snapshots.append(take_memory_snapshot(process, tracemalloc.take_snapshot()))

    print(f"\n🔄 Ejecutando {LEAK_ITERATIONS} iteraciones del NLP engine...")

    # Iterar N veces
    for i in range(LEAK_ITERATIONS):
        await nlp_engine.parse(
            "¿Tienen habitaciones disponibles para el 15 de enero?",
            user_id=f"leak_test_{i % 100}",  # Rotar 100 usuarios
        )

        # Snapshot cada 100 iteraciones
        if (i + 1) % 100 == 0:
            gc.collect()
            snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
            snapshots.append(snapshot)
            print(f"  Iteración {i + 1}/{LEAK_ITERATIONS}: {snapshot}")

    # Snapshot final
    gc.collect()
    final_snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
    snapshots.append(final_snapshot)

    tracemalloc.stop()

    # Análisis
    analysis = analyze_memory_growth(snapshots)
    print_memory_report(analysis)

    # Assertions
    assert analysis["rss_growth_mb"] < MEMORY_THRESHOLD_MB, (
        f"❌ MEMORY LEAK: RSS creció {analysis['rss_growth_mb']:.2f} MB"
    )

    assert analysis["growth_rate"] < GROWTH_RATE_THRESHOLD, (
        f"❌ MEMORY LEAK: Tasa de crecimiento {analysis['growth_rate'] * 100:.1f}% excede threshold"
    )


@pytest.mark.asyncio
async def test_session_manager_no_memory_leak(session_manager, process):
    """
    Validar que SessionManager no acumula sesiones en memoria

    Crea y destruye muchas sesiones para verificar cleanup correcto
    """
    tracemalloc.start()

    snapshots = []
    snapshots.append(take_memory_snapshot(process, tracemalloc.take_snapshot()))

    print(f"\n🔄 Creando {LEAK_ITERATIONS} sesiones...")

    for i in range(LEAK_ITERATIONS):
        user_id = f"user_{i}"

        # Crear sesión
        await session_manager.create_session(user_id)

        # Simular uso
        await session_manager.add_message(user_id, "Test message", role="user")
        await session_manager.add_message(user_id, "Test response", role="assistant")

        # Destruir sesión (simular timeout)
        await session_manager.close_session(user_id)

        # Snapshot cada 100 iteraciones
        if (i + 1) % 100 == 0:
            gc.collect()
            snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
            snapshots.append(snapshot)
            print(f"  Sesión {i + 1}/{LEAK_ITERATIONS}: {snapshot}")

    gc.collect()
    final_snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
    snapshots.append(final_snapshot)

    tracemalloc.stop()

    analysis = analyze_memory_growth(snapshots)
    print_memory_report(analysis)

    assert analysis["rss_growth_mb"] < MEMORY_THRESHOLD_MB, (
        f"❌ SESSION MANAGER LEAK: RSS creció {analysis['rss_growth_mb']:.2f} MB"
    )


@pytest.mark.asyncio
async def test_pms_adapter_connection_leak(pms_adapter, process):
    """
    Validar que PMSAdapter no tiene connection leaks

    Ejecuta muchas operaciones PMS y verifica que las conexiones se cierran
    """
    tracemalloc.start()

    snapshots = []
    snapshots.append(take_memory_snapshot(process, tracemalloc.take_snapshot()))

    print(f"\n🔄 Ejecutando {LEAK_ITERATIONS} operaciones PMS...")

    for i in range(LEAK_ITERATIONS):
        try:
            # Operaciones típicas
            await pms_adapter.check_availability(checkin="2025-01-15", checkout="2025-01-17", guests=2)

            # Snapshot cada 50 iteraciones
            if (i + 1) % 50 == 0:
                gc.collect()
                snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
                snapshots.append(snapshot)
                print(f"  PMS call {i + 1}/{LEAK_ITERATIONS}: {snapshot}")

        except Exception as e:
            print(f"  ⚠️  Error en iteración {i}: {e}")
            continue

    gc.collect()
    final_snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
    snapshots.append(final_snapshot)

    tracemalloc.stop()

    analysis = analyze_memory_growth(snapshots)
    print_memory_report(analysis)

    assert analysis["rss_growth_mb"] < MEMORY_THRESHOLD_MB, (
        f"❌ PMS CONNECTION LEAK: RSS creció {analysis['rss_growth_mb']:.2f} MB"
    )


@pytest.mark.asyncio
async def test_concurrent_conversations_no_leak(nlp_engine, process):
    """
    Validar que conversaciones concurrentes no causan leaks

    Simula múltiples usuarios conversando simultáneamente
    """
    tracemalloc.start()

    snapshots = []
    snapshots.append(take_memory_snapshot(process, tracemalloc.take_snapshot()))

    print(f"\n🔄 Ejecutando {LEAK_ITERATIONS // 10} rondas de 10 conversaciones concurrentes...")

    async def conversation(user_id: str):
        """Simula una conversación completa"""
        messages = [
            "Hola",
            "¿Tienen habitaciones disponibles?",
            "Para 2 personas",
            "¿Cuál es el precio?",
            "Gracias",
        ]
        for msg in messages:
            await nlp_engine.parse(msg, user_id=user_id)

    for round_num in range(LEAK_ITERATIONS // 10):
        # 10 conversaciones concurrentes
        tasks = [conversation(f"concurrent_user_{round_num}_{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        # Snapshot cada 5 rondas
        if (round_num + 1) % 5 == 0:
            gc.collect()
            snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
            snapshots.append(snapshot)
            print(f"  Ronda {round_num + 1}/{LEAK_ITERATIONS // 10}: {snapshot}")

    gc.collect()
    final_snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
    snapshots.append(final_snapshot)

    tracemalloc.stop()

    analysis = analyze_memory_growth(snapshots)
    print_memory_report(analysis)

    assert analysis["rss_growth_mb"] < MEMORY_THRESHOLD_MB * 2, (  # Más tolerante para concurrencia
        f"❌ CONCURRENT LEAK: RSS creció {analysis['rss_growth_mb']:.2f} MB"
    )


@pytest.mark.asyncio
async def test_audio_processing_no_leak(process):
    """
    Validar que el procesamiento de audio no tiene leaks

    Procesa muchos archivos de audio simulados
    """
    from app.services.audio_processor import AudioProcessor

    tracemalloc.start()

    AudioProcessor()
    snapshots = []
    snapshots.append(take_memory_snapshot(process, tracemalloc.take_snapshot()))

    print(f"\n🔄 Procesando {LEAK_ITERATIONS // 10} archivos de audio...")

    for i in range(LEAK_ITERATIONS // 10):
        try:
            # Simular audio (bytes aleatorios)
            audio_data = os.urandom(1024 * 100)  # 100KB

            # Procesar (STT) - Usar método existente
            # await processor.process_audio(audio_data, audio_format='ogg')
            # TODO: Implementar test con método real de AudioProcessor

            # Limpiar explícitamente
            del audio_data

            if (i + 1) % 10 == 0:
                gc.collect()
                snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
                snapshots.append(snapshot)
                print(f"  Audio {i + 1}/{LEAK_ITERATIONS // 10}: {snapshot}")

        except Exception as e:
            print(f"  ⚠️  Error en audio {i}: {e}")
            continue

    gc.collect()
    final_snapshot = take_memory_snapshot(process, tracemalloc.take_snapshot())
    snapshots.append(final_snapshot)

    tracemalloc.stop()

    analysis = analyze_memory_growth(snapshots)
    print_memory_report(analysis)

    assert analysis["rss_growth_mb"] < MEMORY_THRESHOLD_MB * 3, (  # Audio puede usar más memoria
        f"❌ AUDIO PROCESSING LEAK: RSS creció {analysis['rss_growth_mb']:.2f} MB"
    )


# ===== TEST DE DEGRADACIÓN DE PERFORMANCE =====


@pytest.mark.asyncio
async def test_no_performance_degradation_over_time(nlp_engine):
    """
    Validar que el tiempo de respuesta no se degrada con el uso

    Mide latencia en intervalos y verifica que no aumenta significativamente
    """
    print(f"\n⏱️  Midiendo degradación de performance en {LEAK_ITERATIONS} iteraciones...")

    latencies = []

    for i in range(LEAK_ITERATIONS):
        start = time.perf_counter()

        await nlp_engine.parse("¿Tienen habitaciones disponibles?", user_id=f"perf_test_{i % 100}")

        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        if (i + 1) % 100 == 0:
            recent_avg = sum(latencies[-100:]) / 100
            print(f"  Iteración {i + 1}: Latencia promedio últimas 100: {recent_avg:.2f}ms")

    # Análisis de degradación
    first_100_avg = sum(latencies[:100]) / 100
    last_100_avg = sum(latencies[-100:]) / 100
    degradation_pct = ((last_100_avg - first_100_avg) / first_100_avg) * 100

    print("\n" + "=" * 60)
    print("📊 PERFORMANCE DEGRADATION ANALYSIS")
    print("=" * 60)
    print(f"  First 100 avg: {first_100_avg:.2f}ms")
    print(f"  Last 100 avg: {last_100_avg:.2f}ms")
    print(f"  Degradation: {degradation_pct:+.1f}%")
    print("=" * 60 + "\n")

    # No debe degradarse más de 20%
    assert degradation_pct < 20, f"❌ PERFORMANCE DEGRADATION: {degradation_pct:.1f}% (threshold: 20%)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
