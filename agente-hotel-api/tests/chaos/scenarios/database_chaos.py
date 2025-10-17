"""
Database Chaos Scenarios

Scenarios for testing database-related failures:
- Connection failures
- Slow queries
- Query timeouts
- Deadlocks
- Connection pool exhaustion
"""

from typing import List

from app.core.chaos import (
    BlastRadius,
    ChaosExperiment,
    FaultConfig,
    FaultType,
)


def create_db_connection_failure_scenario(
    target_service: str = "database",
    probability: float = 0.1,
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create database connection failure scenario.

    Simulates failed database connections.

    Args:
        target_service: Database service identifier
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"db_conn_fail_{target_service}",
        name="Database Connection Failure",
        description="Simulate database connection failures",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=probability,
            exception_class="ConnectionError",
            exception_message="Could not connect to database (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Connection pool retries and eventually succeeds",
        rollback_strategy="immediate",
    )


def create_slow_query_scenario(
    target_service: str = "database",
    latency_ms: int = 3000,
    probability: float = 0.25,
    duration_seconds: int = 180,
) -> ChaosExperiment:
    """
    Create slow database query scenario.

    Simulates database queries that take longer than expected.

    Args:
        target_service: Database service identifier
        latency_ms: Query execution latency in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"db_slow_query_{latency_ms}ms",
        name=f"Slow Database Query - {latency_ms}ms",
        description=f"Inject {latency_ms}ms delays into database queries",
        fault_config=FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=probability,
            latency_ms=latency_ms,
            latency_jitter_ms=500,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Query timeouts prevent request blocking",
        rollback_strategy="immediate",
    )


def create_query_timeout_scenario(
    target_service: str = "database",
    timeout_ms: int = 15000,
    probability: float = 0.15,
    duration_seconds: int = 90,
) -> ChaosExperiment:
    """
    Create database query timeout scenario.

    Simulates queries that timeout.

    Args:
        target_service: Database service identifier
        timeout_ms: Timeout duration in milliseconds
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"db_query_timeout_{timeout_ms}ms",
        name=f"Database Query Timeout - {timeout_ms}ms",
        description="Simulate database query timeouts",
        fault_config=FaultConfig(
            fault_type=FaultType.TIMEOUT,
            probability=probability,
            timeout_ms=timeout_ms,
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Application handles timeouts gracefully",
        rollback_strategy="immediate",
    )


def create_connection_pool_exhaustion_scenario(
    target_service: str = "database",
    duration_seconds: int = 150,
) -> ChaosExperiment:
    """
    Create connection pool exhaustion scenario.

    Simulates all database connections being in use.

    Args:
        target_service: Database service identifier
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"db_pool_exhaustion_{target_service}",
        name="Connection Pool Exhaustion",
        description="Simulate database connection pool exhaustion",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=0.3,
            exception_class="RuntimeError",
            exception_message="Connection pool exhausted (chaos-induced)",
            blast_radius=BlastRadius.SERVICE_CLUSTER,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Connection pool management prevents complete exhaustion",
        rollback_strategy="gradual",
    )


def create_transaction_deadlock_scenario(
    target_service: str = "database",
    probability: float = 0.05,
    duration_seconds: int = 120,
) -> ChaosExperiment:
    """
    Create transaction deadlock scenario.

    Simulates database deadlocks.

    Args:
        target_service: Database service identifier
        probability: Probability of injection (0.0-1.0)
        duration_seconds: How long to run experiment

    Returns:
        ChaosExperiment configuration
    """
    return ChaosExperiment(
        id=f"db_deadlock_{target_service}",
        name="Transaction Deadlock",
        description="Simulate database transaction deadlocks",
        fault_config=FaultConfig(
            fault_type=FaultType.EXCEPTION,
            probability=probability,
            exception_class="RuntimeError",
            exception_message="Deadlock detected (chaos-induced)",
            blast_radius=BlastRadius.SINGLE_REQUEST,
        ),
        target_service=target_service,
        duration_seconds=duration_seconds,
        steady_state_hypothesis="Deadlock detection and retry logic handles failures",
        rollback_strategy="immediate",
    )


# Predefined database chaos scenarios
database_scenarios: List[ChaosExperiment] = [
    create_db_connection_failure_scenario(),
    create_slow_query_scenario(),
    create_query_timeout_scenario(),
    create_connection_pool_exhaustion_scenario(),
    create_transaction_deadlock_scenario(),
]


__all__ = [
    "create_db_connection_failure_scenario",
    "create_slow_query_scenario",
    "create_query_timeout_scenario",
    "create_connection_pool_exhaustion_scenario",
    "create_transaction_deadlock_scenario",
    "database_scenarios",
]
