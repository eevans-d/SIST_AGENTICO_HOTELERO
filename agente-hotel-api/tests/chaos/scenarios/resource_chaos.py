"""
Resource Chaos Scenarios

Scenarios for testing resource-related failures:
- Memory pressure
- CPU throttling
- Disk I/O slowdowns
- Resource exhaustion
"""

from typing import List

from app.core.chaos import (
    BlastRadius,
    ChaosExperiment,
    FaultConfig,
    FaultType,
)


def create_memory_pressure_scenario(
    target_service: str = "orchestrator",
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create memory pressure scenario.
    
    Simulates high memory usage.
    
    Args:
        target_service: Service to inject memory pressure into
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"res_memory_pressure_{target_service}",
        name="Memory Pressure",
        description=f"Simulate memory pressure in {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.RESOURCE_EXHAUSTION,
            probability=0.2,
            exception_class="RuntimeError",
            exception_message="Memory allocation failed (chaos-induced pressure)",
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Garbage collection handles pressure, OOM killer doesn't trigger",
        rollback_strategy="immediate",
    )


def create_cpu_throttling_scenario(
    target_service: str = "nlp_engine",
    latency_ms: int = 1500,  # Simulates CPU throttling by adding processing delay
    probability: float = 0.35,
    duration_seconds: int = 240,
) -> ChaosExperiment:
    """
    Create CPU throttling scenario.
    
    Simulates CPU resource limitation by slowing operations.
    
    Args:
        target_service: Service to throttle
        latency_ms: Processing delay in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"res_cpu_throttle_{target_service}_{latency_ms}ms",
        name=f"CPU Throttling - {latency_ms}ms",
        description=f"Simulate CPU throttling in {target_service} ({latency_ms}ms delay)",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=300,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="System maintains throughput with degraded performance",
        rollback_strategy="gradual",
    )


def create_disk_io_slowdown_scenario(
    target_service: str = "database",
    latency_ms: int = 2500,
    probability: float = 0.25,
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create disk I/O slowdown scenario.
    
    Simulates slow disk operations.
    
    Args:
        target_service: Service to slow down
        latency_ms: I/O operation latency in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"res_disk_io_slow_{target_service}_{latency_ms}ms",
        name=f"Disk I/O Slowdown - {latency_ms}ms",
        description=f"Simulate slow disk I/O in {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=500,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Async I/O prevents request blocking",
        rollback_strategy="immediate",
    )


def create_resource_exhaustion_scenario(
    target_service: str = "whatsapp_client",
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create resource exhaustion scenario.
    
    Simulates complete resource exhaustion (memory, CPU, connections).
    
    Args:
        target_service: Service to exhaust resources in
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"res_exhaustion_{target_service}",
        name="Resource Exhaustion",
        description=f"Simulate resource exhaustion in {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.RESOURCE_EXHAUSTION,
            probability=0.4,
            exception_class="RuntimeError",
            exception_message="Resource limit exceeded (chaos-induced exhaustion)",
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Resource limits prevent cascade, service recovers",
        rollback_strategy="immediate",
    )


def create_memory_leak_scenario(
    target_service: str = "session_manager",
    duration_seconds: int = 300,
) -> ChaosExperiment:
    """
    Create memory leak scenario.
    
    Simulates gradual memory leak.
    
    Args:
        target_service: Service with memory leak
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"res_memory_leak_{target_service}",
        name="Memory Leak Simulation",
        description=f"Simulate gradual memory leak in {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.RESOURCE_EXHAUSTION,
            probability=0.15,
            exception_class="RuntimeError",
            exception_message="Memory leak detected (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_SERVICE,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Memory monitoring detects leak, alerts triggered",
        rollback_strategy="gradual",
    )


# Predefined resource chaos scenarios
resource_scenarios: List[ChaosExperiment] = [
    create_memory_pressure_scenario(),
    create_cpu_throttling_scenario(),
    create_disk_io_slowdown_scenario(),
    create_resource_exhaustion_scenario(),
    create_memory_leak_scenario(),
]


__all__ = [
    "create_memory_pressure_scenario",
    "create_cpu_throttling_scenario",
    "create_disk_io_slowdown_scenario",
    "create_resource_exhaustion_scenario",
    "create_memory_leak_scenario",
    "resource_scenarios",
]
