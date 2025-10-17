"""
PMS Chaos Scenarios

Scenarios for testing PMS integration failures:
- API failures
- Delayed responses
- Rate limiting
- Invalid responses
- Service unavailability
"""

from typing import List

from app.core.chaos import (
    BlastRadius,
    ChaosExperiment,
    FaultConfig,
    FaultType,
)


def create_pms_api_failure_scenario(
    probability: float = 0.2,
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create PMS API failure scenario.

    Simulates PMS API returning errors.

    Args:
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id="pms_api_fail",
        name="PMS API Failure",
        description="Simulate PMS API returning 500 errors",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=probability,
            exception_class="RuntimeError",
            exception_message="PMS API returned 500 Internal Server Error (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Circuit breaker opens, fallback to cached data",
        rollback_strategy="immediate",
    )


def create_pms_slow_response_scenario(
    latency_ms: int = 8000,
    probability: float = 0.3,
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create PMS slow response scenario.

    Simulates PMS API responding very slowly.

    Args:
        latency_ms: Response latency in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"pms_slow_response_{latency_ms}ms",
        name=f"PMS Slow Response - {latency_ms}ms",
        description=f"Inject {latency_ms}ms delays into PMS API responses",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=2000,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Request timeouts prevent queue buildup",
        rollback_strategy="immediate",
    )


def create_pms_rate_limit_scenario(
    rate_limit_requests: int = 5,
    rate_limit_window_seconds: int = 60,
    duration_seconds: int = 240,
) -> ChaosExperiment:
    """
    Create PMS rate limiting scenario.

    Simulates PMS API aggressively rate limiting requests.

    Args:
        rate_limit_requests: Max requests allowed
        rate_limit_window_seconds: Time window in seconds
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"pms_rate_limit_{rate_limit_requests}req_{rate_limit_window_seconds}s",
        name=f"PMS Rate Limiting - {rate_limit_requests} req/{rate_limit_window_seconds}s",
        description=f"Enforce strict rate limit on PMS API: {rate_limit_requests} req/{rate_limit_window_seconds}s",
        fault_config=FaultConfig(
            fault_type=FaultType.RATE_LIMIT,
            probability=1.0,  # Always check rate limit
            rate_limit_requests=rate_limit_requests,
            rate_limit_window_seconds=rate_limit_window_seconds,
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Request queueing and retry logic handles rate limits",
        rollback_strategy="gradual",
    )


def create_pms_timeout_scenario(
    timeout_ms: int = 20000,
    probability: float = 0.15,
    duration_seconds: int = 90,
) -> ChaosExperiment:
    """
    Create PMS timeout scenario.

    Simulates PMS API requests timing out.

    Args:
        timeout_ms: Timeout duration in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"pms_timeout_{timeout_ms}ms",
        name=f"PMS API Timeout - {timeout_ms}ms",
        description="Simulate PMS API request timeouts",
        fault_config=FaultConfig(
            fault_type=FaultType.TIMEOUT,
            probability=probability,
            timeout_ms=timeout_ms,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Timeouts are handled, retry logic attempts recovery",
        rollback_strategy="immediate",
    )


def create_pms_unavailable_scenario(
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create PMS unavailable scenario.

    Simulates complete PMS unavailability.

    Args:
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id="pms_unavailable",
        name="PMS Unavailable",
        description="Simulate complete PMS unavailability",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=1.0,  # Always fail
            exception_class="ConnectionError",
            exception_message="PMS service is unavailable (chaos-induced)",
            blast_radius=BlastRadius.ENTIRE_SYSTEM,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="System operates with cached data and degraded functionality",
        rollback_strategy="immediate",
    )


def create_pms_intermittent_failure_scenario(
    duration_seconds: int = 300,
) -> ChaosExperiment:
    """
    Create PMS intermittent failure scenario.

    Simulates random, intermittent PMS failures.

    Args:
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id="pms_intermittent_fail",
        name="PMS Intermittent Failures",
        description="Simulate random, intermittent PMS API failures",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=0.25,  # 25% failure rate
            exception_class="RuntimeError",
            exception_message="PMS API intermittent error (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service="pms_adapter",
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Retry logic handles transient failures gracefully",
        rollback_strategy="gradual",
    )


# Predefined PMS chaos scenarios
pms_scenarios: List[ChaosExperiment] = [
    create_pms_api_failure_scenario(),
    create_pms_slow_response_scenario(),
    create_pms_rate_limit_scenario(),
    create_pms_timeout_scenario(),
    create_pms_unavailable_scenario(),
    create_pms_intermittent_failure_scenario(),
]


__all__ = [
    "create_pms_api_failure_scenario",
    "create_pms_slow_response_scenario",
    "create_pms_rate_limit_scenario",
    "create_pms_timeout_scenario",
    "create_pms_unavailable_scenario",
    "create_pms_intermittent_failure_scenario",
    "pms_scenarios",
]
