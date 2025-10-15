"""
Network Chaos Scenarios

Scenarios for testing network-related failures:
- Latency injection
- Packet loss simulation
- Connection timeouts
- DNS failures
- Network partitions
"""

from typing import List

from app.core.chaos import (
    BlastRadius,
    ChaosExperiment,
    FaultConfig,
    FaultType,
)


def create_network_latency_scenario(
    target_service: str = "pms_adapter",
    latency_ms: int = 2000,
    jitter_ms: int = 500,
    probability: float = 0.3,
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create network latency injection scenario.
    
    Simulates slow network conditions by adding artificial latency.
    
    Args:
        target_service: Service to inject latency into
        latency_ms: Base latency in milliseconds
        jitter_ms: Random jitter to add (+/-)
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"net_latency_{target_service}_{latency_ms}ms",
        name=f"Network Latency - {latency_ms}ms",
        description=f"Inject {latency_ms}ms (+/-{jitter_ms}ms) latency into {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=jitter_ms,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis=f"P95 latency remains below {latency_ms * 2}ms",
        rollback_strategy="immediate",
    )


def create_network_timeout_scenario(
    target_service: str = "pms_adapter",
    timeout_ms: int = 10000,
    probability: float = 0.1,
    duration_seconds: int = 60,
) -> ChaosExperiment:
    """
    Create network timeout scenario.
    
    Simulates requests that timeout due to network issues.
    
    Args:
        target_service: Service to inject timeouts into
        timeout_ms: Timeout duration in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"net_timeout_{target_service}_{timeout_ms}ms",
        name=f"Network Timeout - {timeout_ms}ms",
        description=f"Inject {timeout_ms}ms timeouts into {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.TIMEOUT,
            probability=probability,
            timeout_ms=timeout_ms,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Error rate remains below 5%",
        rollback_strategy="immediate",
    )


def create_connection_failure_scenario(
    target_service: str = "pms_adapter",
    probability: float = 0.2,
    duration_seconds: int = 90,
) -> ChaosExperiment:
    """
    Create connection failure scenario.
    
    Simulates failed network connections.
    
    Args:
        target_service: Service to inject failures into
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"net_conn_fail_{target_service}",
        name="Connection Failure",
        description=f"Simulate connection failures to {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=probability,
            exception_class="ConnectionError",
            exception_message="Connection refused (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Circuit breaker opens and system degrades gracefully",
        rollback_strategy="immediate",
    )


def create_high_latency_spike_scenario(
    target_service: str = "whatsapp_client",
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create high latency spike scenario.
    
    Simulates sudden network degradation with very high latency.
    
    Args:
        target_service: Service to inject latency spikes into
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"net_latency_spike_{target_service}",
        name="High Latency Spike",
        description=f"Inject severe latency spikes (5-10s) into {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=0.15,
            latency_ms=7000,  # 7 seconds
            latency_jitter_ms=3000,  # +/- 3 seconds
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Requests timeout gracefully and retry logic works",
        rollback_strategy="immediate",
    )


def create_intermittent_connectivity_scenario(
    target_service: str = "pms_adapter",
    duration_seconds: int = 300,
) -> ChaosExperiment:
    """
    Create intermittent connectivity scenario.
    
    Simulates unstable network with random failures.
    
    Args:
        target_service: Service to inject intermittent failures into
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"net_intermittent_{target_service}",
        name="Intermittent Connectivity",
        description=f"Simulate unstable network to {target_service} with random failures",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=0.25,  # 25% failure rate
            exception_class="ConnectionError",
            exception_message="Network unreachable (chaos-induced intermittent failure)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Retry logic handles transient failures without user impact",
        rollback_strategy="gradual",
    )


# Predefined network chaos scenarios
network_scenarios: List[ChaosExperiment] = [
    create_network_latency_scenario(),
    create_network_timeout_scenario(),
    create_connection_failure_scenario(),
    create_high_latency_spike_scenario(),
    create_intermittent_connectivity_scenario(),
]


__all__ = [
    "create_network_latency_scenario",
    "create_network_timeout_scenario",
    "create_connection_failure_scenario",
    "create_high_latency_spike_scenario",
    "create_intermittent_connectivity_scenario",
    "network_scenarios",
]
