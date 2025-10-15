"""
Service Chaos Scenarios

Scenarios for testing service-level failures:
- Random service failures
- Circuit breaker trips
- Resource exhaustion
- Memory leaks
- CPU spikes
"""

from typing import List

from app.core.chaos import (
    BlastRadius,
    ChaosExperiment,
    FaultConfig,
    FaultType,
)


def create_random_service_failure_scenario(
    target_service: str = "orchestrator",
    probability: float = 0.15,
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create random service failure scenario.
    
    Simulates random RuntimeError failures in service operations.
    
    Args:
        target_service: Service to inject failures into
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_random_fail_{target_service}",
        name="Random Service Failure",
        description=f"Inject random RuntimeErrors into {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=probability,
            exception_class="RuntimeError",
            exception_message="Service temporarily unavailable (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="System handles errors gracefully and retries work",
        rollback_strategy="immediate",
    )


def create_circuit_breaker_trip_scenario(
    target_service: str = "pms_adapter",
    probability: float = 0.5,  # High probability to trigger circuit breaker
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create circuit breaker trip scenario.
    
    Simulates conditions that cause circuit breaker to open.
    
    Args:
        target_service: Service to inject circuit breaker failures into
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_circuit_break_{target_service}",
        name="Circuit Breaker Trip",
        description=f"Trigger circuit breaker opening in {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.CIRCUIT_BREAK,
            probability=probability,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Circuit breaker opens, system uses fallback logic",
        rollback_strategy="gradual",
    )


def create_service_rate_limit_scenario(
    target_service: str = "whatsapp_client",
    rate_limit_requests: int = 10,
    rate_limit_window_seconds: int = 60,
    duration_seconds: int = 240,
) -> ChaosExperiment:
    """
    Create service rate limiting scenario.
    
    Simulates aggressive rate limiting.
    
    Args:
        target_service: Service to inject rate limiting into
        rate_limit_requests: Max requests allowed
        rate_limit_window_seconds: Time window in seconds
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_rate_limit_{target_service}_{rate_limit_requests}req_{rate_limit_window_seconds}s",
        name=f"Service Rate Limiting - {rate_limit_requests} req/{rate_limit_window_seconds}s",
        description=f"Enforce strict rate limit on {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.RATE_LIMIT,
            probability=1.0,  # Always check rate limit
            rate_limit_requests=rate_limit_requests,
            rate_limit_window_seconds=rate_limit_window_seconds,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Rate limiting is enforced, requests queue or retry",
        rollback_strategy="immediate",
    )


def create_cascading_failure_scenario(
    target_service: str = "orchestrator",
    duration_seconds: int = 150,
) -> ChaosExperiment:
    """
    Create cascading failure scenario.
    
    Simulates failures that could cascade through the system.
    
    Args:
        target_service: Initial service to fail
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_cascade_fail_{target_service}",
        name="Cascading Failure",
        description=f"Simulate cascading failures starting from {target_service}",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=0.3,
            exception_class="RuntimeError",
            exception_message="Upstream service failure (chaos-induced cascade)",
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Circuit breakers prevent cascading failures",
        rollback_strategy="immediate",
    )


def create_slow_service_response_scenario(
    target_service: str = "nlp_engine",
    latency_ms: int = 5000,
    probability: float = 0.4,
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create slow service response scenario.
    
    Simulates a service that becomes very slow.
    
    Args:
        target_service: Service to slow down
        latency_ms: Response latency in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_slow_response_{target_service}_{latency_ms}ms",
        name=f"Slow Service Response - {latency_ms}ms",
        description=f"Make {target_service} respond very slowly ({latency_ms}ms)",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=1000,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Timeouts prevent request queue buildup",
        rollback_strategy="immediate",
    )


def create_service_unavailable_scenario(
    target_service: str = "session_manager",
    duration_seconds: int = 90,
) -> ChaosExperiment:
    """
    Create service unavailable scenario.
    
    Simulates complete service unavailability.
    
    Args:
        target_service: Service to make unavailable
        duration_seconds: How long to run experiment
        
    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"svc_unavailable_{target_service}",
        name="Service Unavailable",
        description=f"Make {target_service} completely unavailable",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=1.0,  # Always fail
            exception_class="ConnectionError",
            exception_message=f"{target_service} is unavailable (chaos-induced)",
            blast_radius=BlastRadius.ENTIRE_SYSTEM,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="System operates with degraded functionality",
        rollback_strategy="immediate",
    )


# Predefined service chaos scenarios
service_scenarios: List[ChaosExperiment] = [
    create_random_service_failure_scenario(),
    create_circuit_breaker_trip_scenario(),
    create_service_rate_limit_scenario(),
    create_cascading_failure_scenario(),
    create_slow_service_response_scenario(),
    create_service_unavailable_scenario(),
]


__all__ = [
    "create_random_service_failure_scenario",
    "create_circuit_breaker_trip_scenario",
    "create_service_rate_limit_scenario",
    "create_cascading_failure_scenario",
    "create_slow_service_response_scenario",
    "create_service_unavailable_scenario",
    "service_scenarios",
]
