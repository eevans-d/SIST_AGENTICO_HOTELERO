"""
Chaos Orchestrator

Coordinates chaos experiments and provides safe execution with:
- Experiment scheduling
- Chaos Monkey implementation
- Safe rollback mechanisms
- Incident reporting
- Automated chaos testing
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from app.core.chaos import (
    ChaosExperiment,
    ChaosManager,
    ChaosMetrics,
    get_chaos_manager,
)
from app.core.logging import get_logger
from tests.chaos.scenarios import (
    database_scenarios,
    network_scenarios,
    pms_scenarios,
    resource_scenarios,
    service_scenarios,
)

logger = get_logger(__name__)


class ChaosMonkey:
    """
    Implements Netflix Chaos Monkey pattern.

    Randomly terminates services/injects faults during business hours
    to ensure systems are resilient to unexpected failures.
    """

    def __init__(
        self,
        enabled: bool = False,
        probability: float = 0.05,  # 5% chance per check
        check_interval_seconds: int = 300,  # Check every 5 minutes
        business_hours_only: bool = True,
    ):
        self.enabled = enabled
        self.probability = probability
        self.check_interval_seconds = check_interval_seconds
        self.business_hours_only = business_hours_only
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start Chaos Monkey."""
        if self._running:
            logger.warning("chaos_monkey_already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "chaos_monkey_started",
            probability=self.probability,
            interval=self.check_interval_seconds,
        )

    def stop(self) -> None:
        """Stop Chaos Monkey."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("chaos_monkey_stopped")

    async def _run_loop(self) -> None:
        """Main chaos monkey loop."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_seconds)

                if self.business_hours_only and not self._is_business_hours():
                    logger.debug("chaos_monkey_skip_non_business_hours")
                    continue

                if random.random() < self.probability:
                    await self._inject_chaos()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("chaos_monkey_error", error=str(e))

    def _is_business_hours(self) -> bool:
        """Check if current time is during business hours (9 AM - 5 PM, weekdays)."""
        now = datetime.now()
        # Monday = 0, Sunday = 6
        if now.weekday() >= 5:  # Weekend
            return False
        if now.hour < 9 or now.hour >= 17:  # Outside 9 AM - 5 PM
            return False
        return True

    async def _inject_chaos(self) -> None:
        """Inject random chaos experiment."""
        all_scenarios = network_scenarios + service_scenarios + database_scenarios + pms_scenarios + resource_scenarios

        if not all_scenarios:
            return

        # Pick random scenario
        scenario = random.choice(all_scenarios)

        # Reduce duration for chaos monkey (30-60s instead of full duration)
        scenario.duration_seconds = random.randint(30, 60)

        logger.info(
            "chaos_monkey_injecting",
            experiment_id=scenario.id,
            name=scenario.name,
            duration=scenario.duration_seconds,
        )

        orchestrator = ChaosOrchestrator()
        try:
            await orchestrator.run_experiment(scenario)
        except Exception as e:
            logger.error(
                "chaos_monkey_experiment_failed",
                experiment_id=scenario.id,
                error=str(e),
            )


class ChaosScheduler:
    """
    Schedules chaos experiments.

    Allows defining experiment schedules for automated resilience testing.
    """

    def __init__(self):
        self._schedules: Dict[str, Dict] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_schedule(
        self,
        experiment: ChaosExperiment,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
    ) -> None:
        """
        Add experiment to schedule.

        Args:
            experiment: Chaos experiment to schedule
            cron_expression: Cron expression (not implemented)
            interval_seconds: Run every N seconds
        """
        if not interval_seconds:
            raise ValueError("interval_seconds is required")

        self._schedules[experiment.id] = {
            "experiment": experiment,
            "interval_seconds": interval_seconds,
            "last_run": None,
        }

        logger.info(
            "chaos_schedule_added",
            experiment_id=experiment.id,
            interval_seconds=interval_seconds,
        )

    def remove_schedule(self, experiment_id: str) -> None:
        """Remove experiment from schedule."""
        if experiment_id in self._schedules:
            del self._schedules[experiment_id]
            logger.info("chaos_schedule_removed", experiment_id=experiment_id)

    def start(self) -> None:
        """Start scheduler."""
        if self._running:
            logger.warning("chaos_scheduler_already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("chaos_scheduler_started", schedules=len(self._schedules))

    def stop(self) -> None:
        """Stop scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("chaos_scheduler_stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.utcnow()

                for exp_id, schedule in list(self._schedules.items()):
                    last_run = schedule["last_run"]
                    interval = schedule["interval_seconds"]

                    should_run = last_run is None or (now - last_run).total_seconds() >= interval

                    if should_run:
                        experiment = schedule["experiment"]
                        logger.info("chaos_schedule_running", experiment_id=exp_id)

                        orchestrator = ChaosOrchestrator()
                        try:
                            await orchestrator.run_experiment(experiment)
                            schedule["last_run"] = now
                        except Exception as e:
                            logger.error(
                                "chaos_schedule_experiment_failed",
                                experiment_id=exp_id,
                                error=str(e),
                            )

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("chaos_scheduler_error", error=str(e))


class ChaosOrchestrator:
    """
    Main orchestrator for chaos experiments.

    Provides safe experiment execution with:
    - Pre-flight checks
    - Progress monitoring
    - Automatic rollback
    - Metrics collection
    - Incident reporting
    """

    def __init__(self, manager: Optional[ChaosManager] = None):
        self.manager = manager or get_chaos_manager()
        self._active_experiments: Set[str] = set()

    async def run_experiment(
        self,
        experiment: ChaosExperiment,
        dry_run: bool = False,
    ) -> ChaosMetrics:
        """
        Run a chaos experiment safely.

        Args:
            experiment: Experiment to run
            dry_run: If True, simulate without actual injection

        Returns:
            Final metrics from experiment

        Raises:
            RuntimeError: If experiment fails safety checks
        """
        # Pre-flight checks
        if not self._preflight_checks(experiment):
            raise RuntimeError(f"Pre-flight checks failed for {experiment.id}")

        if dry_run:
            logger.info(
                "chaos_experiment_dry_run",
                experiment_id=experiment.id,
                name=experiment.name,
            )
            return self._simulate_experiment(experiment)

        # Register and start
        self.manager.register_experiment(experiment)

        if not self.manager.start_experiment(experiment.id):
            raise RuntimeError(f"Failed to start experiment {experiment.id}")

        self._active_experiments.add(experiment.id)

        try:
            # Run for specified duration
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(seconds=experiment.duration_seconds)

            logger.info(
                "chaos_experiment_running",
                experiment_id=experiment.id,
                duration_seconds=experiment.duration_seconds,
            )

            # Monitor during execution
            while datetime.utcnow() < end_time:
                await asyncio.sleep(10)  # Check every 10 seconds

                # Collect metrics
                metrics = await self._collect_metrics(experiment)
                self.manager.record_metrics(experiment.id, metrics)

                # Safety checks during execution
                if not self._runtime_safety_checks(metrics):
                    logger.warning(
                        "chaos_experiment_safety_abort",
                        experiment_id=experiment.id,
                        reason="Runtime safety checks failed",
                    )
                    break

            # Final metrics
            final_metrics = await self._collect_metrics(experiment)

            logger.info(
                "chaos_experiment_completed",
                experiment_id=experiment.id,
                total_requests=final_metrics.total_requests,
                affected_requests=final_metrics.affected_requests,
                error_rate=final_metrics.error_rate,
            )

            return final_metrics

        except Exception as e:
            logger.error(
                "chaos_experiment_error",
                experiment_id=experiment.id,
                error=str(e),
            )
            raise

        finally:
            # Always stop experiment (triggers rollback)
            self.manager.stop_experiment(experiment.id, success=True)
            self._active_experiments.discard(experiment.id)

    def _preflight_checks(self, experiment: ChaosExperiment) -> bool:
        """
        Perform pre-flight safety checks.

        Args:
            experiment: Experiment to check

        Returns:
            True if checks pass
        """
        # Check 1: No other experiments running (safety)
        if len(self.manager.get_active_experiments()) > 0:
            logger.warning(
                "chaos_preflight_fail_concurrent",
                active_experiments=len(self.manager.get_active_experiments()),
            )
            return False

        # Check 2: Blast radius is reasonable
        from app.core.chaos import BlastRadius

        if experiment.fault_config.blast_radius == BlastRadius.ENTIRE_SYSTEM:
            logger.warning(
                "chaos_preflight_warning_system_wide",
                experiment_id=experiment.id,
            )
            # Allow but log warning

        # Check 3: Duration is reasonable (max 30 minutes)
        if experiment.duration_seconds > 1800:
            logger.warning(
                "chaos_preflight_fail_duration",
                duration=experiment.duration_seconds,
            )
            return False

        return True

    def _runtime_safety_checks(self, metrics: ChaosMetrics) -> bool:
        """
        Perform runtime safety checks during experiment.

        Args:
            metrics: Current metrics

        Returns:
            True if experiment should continue
        """
        # Check 1: Error rate not too high (max 50%)
        if metrics.error_rate > 0.5:
            logger.warning(
                "chaos_safety_error_rate_high",
                error_rate=metrics.error_rate,
            )
            return False

        # Check 2: Availability not too low (min 50%)
        if metrics.availability < 0.5:
            logger.warning(
                "chaos_safety_availability_low",
                availability=metrics.availability,
            )
            return False

        return True

    async def _collect_metrics(self, experiment: ChaosExperiment) -> ChaosMetrics:
        """
        Collect current metrics for experiment.

        Args:
            experiment: Experiment to collect metrics for

        Returns:
            Current metrics
        """
        # In real implementation, would query Prometheus/metrics service
        # For now, return mock metrics
        exp = self.manager._experiments.get(experiment.id)

        if exp:
            total = max(exp.total_requests, 1)
            return ChaosMetrics(
                experiment_id=experiment.id,
                timestamp=datetime.utcnow(),
                total_requests=exp.total_requests,
                affected_requests=exp.affected_requests,
                failed_requests=exp.errors_induced,
                error_rate=exp.errors_induced / total if total > 0 else 0.0,
                availability=1.0 - (exp.errors_induced / total) if total > 0 else 1.0,
            )

        return ChaosMetrics(
            experiment_id=experiment.id,
            timestamp=datetime.utcnow(),
        )

    def _simulate_experiment(self, experiment: ChaosExperiment) -> ChaosMetrics:
        """Simulate experiment for dry run."""
        logger.info(
            "chaos_simulation",
            experiment_id=experiment.id,
            fault_type=experiment.fault_config.fault_type,
            probability=experiment.fault_config.probability,
        )

        return ChaosMetrics(
            experiment_id=experiment.id,
            timestamp=datetime.utcnow(),
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            affected_requests=100,
            error_rate=0.05,
            availability=0.95,
        )

    async def run_scenario_suite(
        self,
        scenarios: List[ChaosExperiment],
        delay_between_seconds: int = 60,
    ) -> Dict[str, ChaosMetrics]:
        """
        Run a suite of chaos scenarios sequentially.

        Args:
            scenarios: List of experiments to run
            delay_between_seconds: Delay between experiments

        Returns:
            Dict mapping experiment ID to final metrics
        """
        results = {}

        for i, scenario in enumerate(scenarios):
            logger.info(
                "chaos_suite_running",
                scenario=f"{i + 1}/{len(scenarios)}",
                experiment_id=scenario.id,
            )

            try:
                metrics = await self.run_experiment(scenario)
                results[scenario.id] = metrics

                # Delay between experiments
                if i < len(scenarios) - 1:
                    logger.info(
                        "chaos_suite_delay",
                        seconds=delay_between_seconds,
                    )
                    await asyncio.sleep(delay_between_seconds)

            except Exception as e:
                logger.error(
                    "chaos_suite_experiment_failed",
                    experiment_id=scenario.id,
                    error=str(e),
                )
                # Continue with remaining scenarios

        logger.info(
            "chaos_suite_completed",
            total_scenarios=len(scenarios),
            successful=len(results),
            failed=len(scenarios) - len(results),
        )

        return results


__all__ = [
    "ChaosMonkey",
    "ChaosScheduler",
    "ChaosOrchestrator",
]
