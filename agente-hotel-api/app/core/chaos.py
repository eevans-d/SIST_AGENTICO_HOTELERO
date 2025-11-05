"""
Chaos Engineering Framework

This module provides tools for controlled fault injection and chaos experiments
to validate system resilience and identify failure modes.

Features:
- Fault injection decorators
- Failure scenario generators
- Blast radius controls
- Recovery time tracking
- Safe experiment execution with automatic rollback

Based on Netflix Chaos Monkey principles and Principles of Chaos Engineering.
"""

import asyncio
import functools
import random
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

from pydantic import BaseModel, Field

from app.core.logging import logger

T = TypeVar("T")


class FaultType(str, Enum):
    """Types of faults that can be injected."""

    LATENCY = "latency"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    CIRCUIT_BREAK = "circuit_break"
    RATE_LIMIT = "rate_limit"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DATA_CORRUPTION = "data_corruption"


class ChaosState(str, Enum):
    """State of chaos experiment."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class BlastRadius(str, Enum):
    """Scope of chaos experiment impact."""

    SINGLE_REQUEST = "single_request"  # Affects one request
    SINGLE_SERVICE = "single_service"  # Affects one service instance
    SERVICE_CLUSTER = "service_cluster"  # Affects all instances
    ENTIRE_SYSTEM = "entire_system"  # Affects entire system


class FaultConfig(BaseModel):
    """Configuration for fault injection."""

    fault_type: FaultType
    probability: float = Field(ge=0.0, le=1.0, default=0.1)  # 10% by default
    enabled: bool = True
    blast_radius: BlastRadius = BlastRadius.SINGLE_REQUEST

    # Latency-specific (optional)
    latency_ms: Optional[int] = None
    latency_jitter_ms: Optional[int] = None

    # Exception-specific (optional)
    exception_class: Optional[str] = None
    exception_message: Optional[str] = "Chaos-induced exception"

    # Timeout-specific (optional)
    timeout_ms: Optional[int] = None

    # Rate limit-specific (optional)
    rate_limit_requests: Optional[int] = None
    rate_limit_window_seconds: Optional[int] = None


class ChaosExperiment(BaseModel):
    """Chaos experiment definition."""

    id: str
    name: str
    description: str
    fault_config: FaultConfig
    target_service: str
    target_endpoint: Optional[str] = None
    duration_seconds: int = Field(ge=1, default=60)
    steady_state_hypothesis: str
    rollback_strategy: str = "immediate"

    # Experiment state
    state: ChaosState = ChaosState.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Metrics
    total_requests: int = 0
    affected_requests: int = 0
    errors_induced: int = 0
    recovery_time_seconds: Optional[float] = None


class ChaosMetrics(BaseModel):
    """Metrics collected during chaos experiment."""

    experiment_id: str
    timestamp: datetime

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    affected_requests: int = 0

    # Latency metrics
    p50_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None

    # Recovery metrics
    time_to_detect_seconds: Optional[float] = None
    time_to_resolve_seconds: Optional[float] = None
    mttr_seconds: Optional[float] = None  # Mean Time To Recovery

    # System health
    error_rate: float = 0.0
    availability: float = 1.0
    circuit_breaker_trips: int = 0


class ChaosManager:
    """
    Manages chaos experiments and fault injection.

    Ensures safe execution with blast radius controls and automatic rollback.
    """

    def __init__(self):
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._active_experiments: Set[str] = set()
        self._fault_configs: Dict[str, FaultConfig] = {}
        self._metrics: Dict[str, List[ChaosMetrics]] = {}
        self._safety_enabled: bool = True
        self._max_concurrent_experiments: int = 1  # Safety: one at a time
        self._request_counters: Dict[str, int] = {}
        self._rate_limit_windows: Dict[str, List[float]] = {}

    def register_experiment(self, experiment: ChaosExperiment) -> None:
        """Register a chaos experiment."""
        self._experiments[experiment.id] = experiment
        self._metrics[experiment.id] = []
        logger.info(
            "chaos_experiment_registered",
            experiment_id=experiment.id,
            name=experiment.name,
            fault_type=experiment.fault_config.fault_type,
        )

    def start_experiment(self, experiment_id: str) -> bool:
        """
        Start a chaos experiment.

        Returns:
            True if experiment started successfully, False otherwise.
        """
        if experiment_id not in self._experiments:
            logger.error("chaos_experiment_not_found", experiment_id=experiment_id)
            return False

        # Safety check: limit concurrent experiments
        if len(self._active_experiments) >= self._max_concurrent_experiments:
            logger.warning(
                "chaos_max_concurrent_experiments_reached",
                active_count=len(self._active_experiments),
            )
            return False

        experiment = self._experiments[experiment_id]
        experiment.state = ChaosState.RUNNING
        experiment.start_time = datetime.now(timezone.utc)
        self._active_experiments.add(experiment_id)

        # Enable fault injection
        self._fault_configs[experiment.target_service] = experiment.fault_config

        logger.info(
            "chaos_experiment_started",
            experiment_id=experiment_id,
            name=experiment.name,
            target_service=experiment.target_service,
            duration_seconds=experiment.duration_seconds,
        )

        return True

    def stop_experiment(self, experiment_id: str, success: bool = True) -> None:
        """Stop a chaos experiment and perform rollback."""
        if experiment_id not in self._experiments:
            return

        experiment = self._experiments[experiment_id]
        experiment.state = ChaosState.COMPLETED if success else ChaosState.FAILED
        experiment.end_time = datetime.now(timezone.utc)
        self._active_experiments.discard(experiment_id)

        # Disable fault injection (rollback)
        if experiment.target_service in self._fault_configs:
            del self._fault_configs[experiment.target_service]

        logger.info(
            "chaos_experiment_stopped",
            experiment_id=experiment_id,
            state=experiment.state,
            duration_actual=str(experiment.end_time - experiment.start_time) if experiment.start_time else None,
        )

    def should_inject_fault(self, service: str, endpoint: Optional[str] = None) -> bool:
        """
        Determine if a fault should be injected for this request.

        Args:
            service: Target service name
            endpoint: Optional endpoint path

        Returns:
            True if fault should be injected based on probability.
        """
        if service not in self._fault_configs:
            return False

        config = self._fault_configs[service]
        if not config.enabled:
            return False

        # Blast radius check
        if config.blast_radius == BlastRadius.SINGLE_REQUEST:
            # Use probability for single request targeting
            return random.random() < config.probability
        elif config.blast_radius == BlastRadius.SINGLE_SERVICE:
            # Affect all requests to this service instance
            return True
        elif config.blast_radius == BlastRadius.SERVICE_CLUSTER:
            # Affect based on probability across cluster
            return random.random() < config.probability
        else:  # ENTIRE_SYSTEM
            # Always affect when system-wide
            return True

    async def inject_fault(self, service: str, endpoint: Optional[str] = None) -> None:
        """
        Inject configured fault.

        Args:
            service: Target service name
            endpoint: Optional endpoint path

        Raises:
            Exception: If fault injection requires raising an exception.
        """
        if service not in self._fault_configs:
            return

        config = self._fault_configs[service]

        # Update metrics
        for exp_id in self._active_experiments:
            exp = self._experiments[exp_id]
            if exp.target_service == service:
                exp.affected_requests += 1

        # Inject fault based on type
        if config.fault_type == FaultType.LATENCY:
            await self._inject_latency(config)

        elif config.fault_type == FaultType.EXCEPTION:
            self._inject_exception(config)

        elif config.fault_type == FaultType.TIMEOUT:
            await self._inject_timeout(config)

        elif config.fault_type == FaultType.CIRCUIT_BREAK:
            self._inject_circuit_break(config)

        elif config.fault_type == FaultType.RATE_LIMIT:
            self._inject_rate_limit(service, config)

        else:
            logger.warning("chaos_unsupported_fault_type", fault_type=config.fault_type)

    async def _inject_latency(self, config: FaultConfig) -> None:
        """Inject artificial latency."""
        latency_ms = config.latency_ms or 1000  # Default 1s
        jitter_ms = config.latency_jitter_ms or 0

        if jitter_ms > 0:
            latency_ms += random.randint(-jitter_ms, jitter_ms)

        delay_seconds = max(0, latency_ms) / 1000.0

        logger.debug("chaos_injecting_latency", latency_ms=latency_ms)
        await asyncio.sleep(delay_seconds)

    def _inject_exception(self, config: FaultConfig) -> None:
        """Inject an exception."""
        exception_message = config.exception_message or "Chaos-induced exception"

        # Map string exception class to actual exception
        exception_map = {
            "ValueError": ValueError,
            "RuntimeError": RuntimeError,
            "TimeoutError": TimeoutError,
            "ConnectionError": ConnectionError,
            "Exception": Exception,
        }

        exc_class = exception_map.get(config.exception_class or "RuntimeError", RuntimeError)

        logger.debug(
            "chaos_injecting_exception",
            exception_class=exc_class.__name__,
            message=exception_message,
        )

        raise exc_class(exception_message)

    async def _inject_timeout(self, config: FaultConfig) -> None:
        """Inject a timeout by sleeping longer than expected."""
        timeout_ms = config.timeout_ms or 30000  # Default 30s
        delay_seconds = timeout_ms / 1000.0

        logger.debug("chaos_injecting_timeout", timeout_ms=timeout_ms)
        await asyncio.sleep(delay_seconds)
        raise TimeoutError("Chaos-induced timeout")

    def _inject_circuit_break(self, config: FaultConfig) -> None:
        """Simulate circuit breaker opening."""
        logger.debug("chaos_injecting_circuit_break")
        raise ConnectionError("Circuit breaker is OPEN (chaos-induced)")

    def _inject_rate_limit(self, service: str, config: FaultConfig) -> None:
        """Simulate rate limiting."""
        rate_limit = config.rate_limit_requests or 10
        window_seconds = config.rate_limit_window_seconds or 60

        now = time.time()
        key = f"{service}:rate_limit"

        # Initialize or clean old entries
        if key not in self._rate_limit_windows:
            self._rate_limit_windows[key] = []

        # Remove entries outside window
        self._rate_limit_windows[key] = [ts for ts in self._rate_limit_windows[key] if now - ts < window_seconds]

        # Check if rate limit exceeded
        if len(self._rate_limit_windows[key]) >= rate_limit:
            logger.debug(
                "chaos_injecting_rate_limit",
                requests_in_window=len(self._rate_limit_windows[key]),
                limit=rate_limit,
            )
            raise RuntimeError(f"Rate limit exceeded: {rate_limit} requests per {window_seconds}s (chaos-induced)")

        # Record this request
        self._rate_limit_windows[key].append(now)

    def record_metrics(self, experiment_id: str, metrics: ChaosMetrics) -> None:
        """Record metrics for an experiment."""
        if experiment_id in self._metrics:
            self._metrics[experiment_id].append(metrics)

    def get_experiment_metrics(self, experiment_id: str) -> List[ChaosMetrics]:
        """Get all metrics for an experiment."""
        return self._metrics.get(experiment_id, [])

    def get_active_experiments(self) -> List[ChaosExperiment]:
        """Get all currently active experiments."""
        return [self._experiments[exp_id] for exp_id in self._active_experiments if exp_id in self._experiments]

    def is_chaos_active(self, service: str) -> bool:
        """Check if chaos is currently active for a service."""
        return service in self._fault_configs


# Global chaos manager instance
_chaos_manager: Optional[ChaosManager] = None


def get_chaos_manager() -> ChaosManager:
    """Get or create the global chaos manager."""
    global _chaos_manager
    if _chaos_manager is None:
        _chaos_manager = ChaosManager()
    return _chaos_manager


def chaos_middleware(service_name: str):
    """
    Decorator for chaos injection in async functions.

    Usage:
        @chaos_middleware(service_name="pms_adapter")
        async def make_pms_call():
            # Your code here
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            manager = get_chaos_manager()

            # Check if fault should be injected
            if manager.should_inject_fault(service_name):
                try:
                    await manager.inject_fault(service_name)
                except Exception as e:
                    logger.warning(
                        "chaos_fault_injected",
                        service=service_name,
                        fault_type=str(type(e).__name__),
                        message=str(e),
                    )
                    raise

            # Execute original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


@asynccontextmanager
async def chaos_experiment_context(experiment: ChaosExperiment):
    """
    Context manager for running chaos experiments safely.

    Usage:
        async with chaos_experiment_context(experiment):
            # Run your workload
            await run_load_test()
    """
    manager = get_chaos_manager()
    manager.register_experiment(experiment)

    try:
        # Start experiment
        if not manager.start_experiment(experiment.id):
            raise RuntimeError(f"Failed to start experiment {experiment.id}")

        logger.info(
            "chaos_experiment_context_entered",
            experiment_id=experiment.id,
            name=experiment.name,
        )

        yield manager

    except Exception as e:
        logger.error(
            "chaos_experiment_failed",
            experiment_id=experiment.id,
            error=str(e),
        )
        manager.stop_experiment(experiment.id, success=False)
        raise

    finally:
        # Always stop experiment (rollback)
        manager.stop_experiment(experiment.id, success=True)
        logger.info(
            "chaos_experiment_context_exited",
            experiment_id=experiment.id,
        )


@contextmanager
def safe_chaos_injection(
    fault_type: FaultType,
    probability: float = 0.1,
    **kwargs,
):
    """
    Context manager for safe, scoped chaos injection.

    Usage:
        with safe_chaos_injection(FaultType.LATENCY, latency_ms=500):
            # Code that may experience injected latency
            response = make_api_call()
    """
    manager = get_chaos_manager()
    temp_service = f"temp_chaos_{id(kwargs)}"

    # Create temporary fault config
    config = FaultConfig(
        fault_type=fault_type,
        probability=probability,
        **kwargs,
    )

    # Temporarily register
    manager._fault_configs[temp_service] = config

    try:
        yield manager
    finally:
        # Clean up
        if temp_service in manager._fault_configs:
            del manager._fault_configs[temp_service]
