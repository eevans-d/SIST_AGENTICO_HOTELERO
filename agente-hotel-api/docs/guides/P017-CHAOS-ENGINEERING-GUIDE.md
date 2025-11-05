# P017 - Chaos Engineering Guide

**Project:** Agente Hotelero IA  
**Phase:** FASE 4 - Performance & Resilience  
**Version:** 1.0.0  
**Date:** October 15, 2025

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Principles of Chaos Engineering](#2-principles-of-chaos-engineering)
3. [Architecture Overview](#3-architecture-overview)
4. [Chaos Framework Components](#4-chaos-framework-components)
5. [Chaos Scenarios](#5-chaos-scenarios)
6. [Running Chaos Experiments](#6-running-chaos-experiments)
7. [Safety Guidelines](#7-safety-guidelines)
8. [Interpreting Results](#8-interpreting-results)
9. [Best Practices](#9-best-practices)
10. [Troubleshooting](#10-troubleshooting)
11. [Integration with CI/CD](#11-integration-with-cicd)
12. [References](#12-references)

---

## 1. Introduction

### What is Chaos Engineering?

Chaos Engineering is the discipline of experimenting on a system to build confidence in the system's capability to withstand turbulent conditions in production.

### Why Chaos Engineering?

- **Proactive Resilience**: Discover weaknesses before they cause outages
- **Confidence Building**: Verify that resilience mechanisms work as designed
- **Continuous Validation**: Ensure system remains resilient as it evolves
- **Reduced MTTR**: Teams practice incident response in controlled scenarios

### Project Context

The Agente Hotelero IA system integrates with external services (QloApps PMS, WhatsApp API, Gmail API) and maintains session state across distributed components. Chaos engineering validates:

- Circuit breakers prevent cascading failures
- Retry logic handles transient failures
- Cache fallbacks provide degraded service
- System recovers within acceptable MTTR

---

## 2. Principles of Chaos Engineering

### Core Principles

1. **Build a Hypothesis around Steady State Behavior**
   - Define what "normal" looks like (e.g., "P95 latency < 3s")
   - Measure baseline metrics before chaos injection

2. **Vary Real-world Events**
   - Network failures, service crashes, resource exhaustion
   - Model actual production failure modes

3. **Run Experiments in Production** (or production-like environments)
   - Staging environments may hide issues
   - Use blast radius controls to limit impact

4. **Automate Experiments to Run Continuously**
   - Integrate into CI/CD pipeline
   - Chaos Monkey for random, continuous testing

5. **Minimize Blast Radius**
   - Start small (single request)
   - Gradually increase scope
   - Always have rollback mechanism

### Netflix Chaos Monkey Inspiration

Our implementation follows Netflix's Chaos Monkey pattern:
- Random fault injection during business hours
- Configurable probability (default: 5%)
- Safe rollback on critical failures
- Comprehensive logging and metrics

---

## 3. Architecture Overview

### Chaos Engineering Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    Chaos Orchestrator                        │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ Chaos Scheduler│  │  Chaos Monkey  │  │ Safety Manager │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└────────────────┬─────────────────────────────────────────────┘
                 │
       ┌─────────┴─────────┐
       │  Chaos Manager    │
       │  - Experiments    │
       │  - Fault Configs  │
       │  - Metrics        │
       └─────────┬─────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐
│Network │  │Service │  │Database│
│Chaos   │  │Chaos   │  │Chaos   │
└────────┘  └────────┘  └────────┘
┌───▼────┐  ┌───▼────┐
│PMS     │  │Resource│
│Chaos   │  │Chaos   │
└────────┘  └────────┘
```

### Components

- **ChaosManager**: Manages experiments, fault injection, metrics
- **ChaosOrchestrator**: Coordinates experiment execution with safety checks
- **ChaosScheduler**: Schedules recurring chaos experiments
- **ChaosMonkey**: Random, continuous fault injection
- **Chaos Scenarios**: Predefined failure scenarios (30+ scenarios)

### Integration Points

- **FastAPI Middleware**: Intercepts requests for fault injection
- **Prometheus**: Collects chaos experiment metrics
- **Grafana**: Visualizes system behavior during chaos
- **AlertManager**: Triggers alerts on critical failures

---

## 4. Chaos Framework Components

### ChaosManager (`app/core/chaos.py`)

Central manager for chaos experiments:

```python
from app.core.chaos import get_chaos_manager, ChaosExperiment, FaultConfig, FaultType

manager = get_chaos_manager()

# Create experiment
experiment = ChaosExperiment(
    id="my_experiment",
    name="PMS Latency Test",
    description="Inject 2s latency into PMS calls",
    fault_config=FaultConfig(
        fault_type=FaultType.LATENCY,
        probability=0.3,
        latency_ms=2000,
    ),
    target_service="pms_adapter",
    duration_seconds=60,
    steady_state_hypothesis="P95 latency remains below 5s",
)

# Register and start
manager.register_experiment(experiment)
manager.start_experiment(experiment.id)

# ... wait for duration ...

# Stop (automatic rollback)
manager.stop_experiment(experiment.id)
```

### Fault Types

| Fault Type | Description | Use Case |
|-----------|-------------|----------|
| `LATENCY` | Add artificial delay | Slow network, overloaded service |
| `EXCEPTION` | Raise exception | Service crash, API error |
| `TIMEOUT` | Timeout after delay | Hung requests |
| `CIRCUIT_BREAK` | Simulate circuit breaker open | Cascading failure prevention |
| `RATE_LIMIT` | Enforce rate limiting | API throttling |
| `RESOURCE_EXHAUSTION` | Resource unavailable | Memory/CPU limits |

### Blast Radius

| Level | Scope | Risk | Use Case |
|-------|-------|------|----------|
| `SINGLE_REQUEST` | One request | Low | Initial testing |
| `SINGLE_SERVICE` | One service instance | Medium | Service resilience |
| `SERVICE_CLUSTER` | All instances | High | Cluster behavior |
| `ENTIRE_SYSTEM` | Whole system | Critical | DR testing |

**Always start with SINGLE_REQUEST and gradually increase!**

### Chaos Decorators

Inject chaos into functions:

```python
from app.core.chaos import chaos_middleware

@chaos_middleware(service_name="pms_adapter")
async def make_pms_call(booking_id: str):
    # Chaos may be injected here based on active experiments
    response = await pms_client.get_booking(booking_id)
    return response
```

### Context Managers

Safe, scoped chaos injection:

```python
from app.core.chaos import chaos_experiment_context

async with chaos_experiment_context(experiment):
    # Run workload during experiment
    await run_load_test()
    # Automatic rollback when context exits
```

---

## 5. Chaos Scenarios

### 5.1 Network Chaos (`tests/chaos/scenarios/network_chaos.py`)

**Scenarios:**
1. **Network Latency** (2s + jitter)
   - Tests: Timeout handling, request queueing
   - Hypothesis: P95 latency < 2x baseline

2. **Network Timeout** (10s timeout)
   - Tests: Timeout configuration, retry logic
   - Hypothesis: Error rate < 5%

3. **Connection Failure** (ConnectionError)
   - Tests: Circuit breaker, fallback logic
   - Hypothesis: Circuit breaker opens gracefully

4. **High Latency Spike** (7s ± 3s)
   - Tests: Extreme latency handling
   - Hypothesis: Requests timeout and retry

5. **Intermittent Connectivity** (25% failure rate)
   - Tests: Retry with exponential backoff
   - Hypothesis: Transient failures masked

**Running:**
```bash
make chaos-network
```

### 5.2 Service Chaos (`tests/chaos/scenarios/service_chaos.py`)

**Scenarios:**
1. **Random Service Failure** (15% RuntimeError)
   - Tests: Error handling, retries
   - Hypothesis: System handles errors gracefully

2. **Circuit Breaker Trip** (50% failure to trigger CB)
   - Tests: Circuit breaker opens and provides fallback
   - Hypothesis: CB opens, uses fallback logic

3. **Service Rate Limiting** (10 req/60s)
   - Tests: Rate limit handling, queueing
   - Hypothesis: Requests queue or retry

4. **Cascading Failure** (30% failure, cluster-wide)
   - Tests: Circuit breakers prevent cascade
   - Hypothesis: Failures isolated, no cascade

5. **Slow Service Response** (5s delay, 40% probability)
   - Tests: Timeout configuration
   - Hypothesis: Timeouts prevent queue buildup

6. **Service Unavailable** (100% failure, system-wide)
   - Tests: Degraded mode operation
   - Hypothesis: System operates with reduced functionality

**Running:**
```bash
make chaos-service
```

### 5.3 Database Chaos (`tests/chaos/scenarios/database_chaos.py`)

**Scenarios:**
1. **Connection Failure** (10% ConnectionError)
   - Tests: Connection pool retry logic
   - Hypothesis: Pool retries and eventually succeeds

2. **Slow Query** (3s + jitter)
   - Tests: Query timeouts
   - Hypothesis: Timeouts prevent request blocking

3. **Query Timeout** (15s timeout)
   - Tests: Timeout handling, error recovery
   - Hypothesis: Application handles timeouts gracefully

4. **Connection Pool Exhaustion** (30% pool exhaustion)
   - Tests: Pool management
   - Hypothesis: Pool prevents complete exhaustion

5. **Transaction Deadlock** (5% deadlock)
   - Tests: Deadlock detection and retry
   - Hypothesis: Retry logic handles deadlocks

**Running:**
```bash
make chaos-database
```

### 5.4 PMS Chaos (`tests/chaos/scenarios/pms_chaos.py`)

**Scenarios:**
1. **API Failure** (20% 500 errors)
   - Tests: Circuit breaker, cache fallback
   - Hypothesis: CB opens, uses cached data

2. **Slow Response** (8s + 2s jitter)
   - Tests: PMS timeout configuration
   - Hypothesis: Timeouts prevent queue buildup

3. **Rate Limiting** (5 req/60s)
   - Tests: Rate limit handling, request queueing
   - Hypothesis: Queueing and retry logic works

4. **API Timeout** (20s timeout, 15% probability)
   - Tests: Timeout handling, retry attempts
   - Hypothesis: Retries attempt recovery

5. **Complete Unavailability** (100% failure)
   - Tests: Degraded mode with cache
   - Hypothesis: Cached data provides limited functionality

6. **Intermittent Failures** (25% failure rate)
   - Tests: Retry logic for transient failures
   - Hypothesis: Retries mask transient failures

**Running:**
```bash
make chaos-pms
```

### 5.5 Resource Chaos (`tests/chaos/scenarios/resource_chaos.py`)

**Scenarios:**
1. **Memory Pressure** (20% memory allocation failure)
   - Tests: GC behavior, OOM handling
   - Hypothesis: GC handles pressure, no OOM kill

2. **CPU Throttling** (1.5s processing delay)
   - Tests: Performance under CPU limits
   - Hypothesis: Throughput maintained with degraded performance

3. **Disk I/O Slowdown** (2.5s I/O delay)
   - Tests: Async I/O behavior
   - Hypothesis: Async I/O prevents blocking

4. **Resource Exhaustion** (40% resource limit exceeded)
   - Tests: Resource limits, recovery
   - Hypothesis: Limits prevent cascade, service recovers

5. **Memory Leak** (15% gradual leak)
   - Tests: Memory monitoring, alerting
   - Hypothesis: Monitoring detects leak, alerts triggered

**Running:**
```bash
make chaos-resource
```

---

## 6. Running Chaos Experiments

### Quick Start

**1. Dry Run (No Actual Injection):**
```bash
make chaos-dry-run
```

**2. Run Single Category:**
```bash
# Network chaos
make chaos-network

# Service chaos
make chaos-service

# Database chaos
make chaos-database

# PMS chaos
make chaos-pms
```

**3. Run All Scenarios:**
```bash
make chaos-all
```

**4. Resilience Test Suite:**
```bash
make chaos-resilience
```

**5. Generate Report:**
```bash
make chaos-report
```

### Advanced Usage

**Custom Experiment:**

```python
from app.core.chaos import ChaosExperiment, FaultConfig, FaultType, BlastRadius
from tests.chaos.orchestrator import ChaosOrchestrator

# Define experiment
experiment = ChaosExperiment(
    id="custom_latency_test",
    name="Custom Latency Test",
    description="Test 500ms latency on WhatsApp client",
    fault_config=FaultConfig(
        fault_type=FaultType.LATENCY,
        probability=0.5,
        latency_ms=500,
        latency_jitter_ms=100,
        blast_radius=BlastRadius.SINGLE_REQUEST,
    ),
    target_service="whatsapp_client",
    duration_seconds=120,
    steady_state_hypothesis="Message delivery rate > 95%",
)

# Run experiment
orchestrator = ChaosOrchestrator()
await orchestrator.run_experiment(experiment)
```

**Run Scenario Suite:**

```python
from tests.chaos.orchestrator import ChaosOrchestrator
from tests.chaos.scenarios import network_scenarios, pms_scenarios

# Select scenarios
scenarios = [
    network_scenarios[0],  # Network latency
    pms_scenarios[0],      # PMS failure
]

# Run with 30s delay between scenarios
orchestrator = ChaosOrchestrator()
results = await orchestrator.run_scenario_suite(
    scenarios,
    delay_between_seconds=30
)

# Analyze results
for exp_id, metrics in results.items():
    print(f"{exp_id}: Availability={metrics.availability:.2%}")
```

### Chaos Monkey (Automated Random Injection)

**⚠️ USE WITH EXTREME CAUTION - ONLY IN NON-PROD ENVIRONMENTS**

```bash
# Starts chaos monkey with 5% probability every 5 minutes
make chaos-monkey
```

**Programmatic:**

```python
from tests.chaos.orchestrator import ChaosMonkey

monkey = ChaosMonkey(
    enabled=True,
    probability=0.05,  # 5% chance per check
    check_interval_seconds=300,  # Check every 5 minutes
    business_hours_only=True,  # Only during 9 AM - 5 PM weekdays
)

monkey.start()
# ... let it run ...
monkey.stop()
```

### Chaos Scheduler (Recurring Experiments)

```python
from tests.chaos.orchestrator import ChaosScheduler
from tests.chaos.scenarios import network_scenarios

scheduler = ChaosScheduler()

# Run network latency test every 2 hours
scheduler.add_schedule(
    experiment=network_scenarios[0],
    interval_seconds=7200,  # 2 hours
)

scheduler.start()
# ... runs continuously ...
scheduler.stop()
```

---

## 7. Safety Guidelines

### Pre-Experiment Checklist

- [ ] Review experiment hypothesis and expected behavior
- [ ] Start with small blast radius (`SINGLE_REQUEST`)
- [ ] Verify rollback mechanism is configured
- [ ] Check monitoring dashboards are accessible
- [ ] Notify team of chaos experiment schedule
- [ ] Have incident response plan ready
- [ ] Verify safety limits are configured (max error rate, min availability)

### During Experiment

- [ ] Monitor Grafana dashboards continuously
- [ ] Watch for unexpected behavior beyond hypothesis
- [ ] Check AlertManager for critical alerts
- [ ] Verify blast radius remains contained
- [ ] Be ready to abort if safety thresholds breached

### Post-Experiment

- [ ] Verify automatic rollback completed
- [ ] Check system returned to steady state
- [ ] Review metrics and logs
- [ ] Document unexpected findings
- [ ] Update incident response procedures if needed

### Safety Limits

Experiments automatically abort if:
- **Error rate > 50%**
- **Availability < 50%**
- **Another experiment already running** (prevents concurrent chaos)
- **Duration > 30 minutes** (prevents runaway experiments)

### Blast Radius Escalation

1. **Phase 1**: `SINGLE_REQUEST`, low probability (10%)
2. **Phase 2**: `SINGLE_REQUEST`, medium probability (30%)
3. **Phase 3**: `SERVICE_CLUSTER`, low probability (10%)
4. **Phase 4**: `SERVICE_CLUSTER`, medium probability (30%)
5. **Phase 5**: `ENTIRE_SYSTEM` (only after phases 1-4 successful)

### Emergency Stop

```python
# Get chaos manager
from app.core.chaos import get_chaos_manager

manager = get_chaos_manager()

# Stop specific experiment
manager.stop_experiment("experiment_id")

# Or stop all active experiments
for exp in manager.get_active_experiments():
    manager.stop_experiment(exp.id)
```

### Rollback Verification

After stopping experiment:
1. Check `experiment.state == ChaosState.COMPLETED`
2. Verify fault config removed from manager
3. Confirm metrics show error rate returning to baseline
4. Check logs for rollback confirmation

---

## 8. Interpreting Results

### Key Metrics

**Availability:**
- **Target**: > 99.9% (3 nines)
- **Degraded**: 95-99.9%
- **Failure**: < 95%

**Error Rate:**
- **Normal**: < 1%
- **Elevated**: 1-5%
- **Critical**: > 5%

**MTTR (Mean Time To Recovery):**
- **Excellent**: < 30s
- **Good**: 30s - 2m
- **Needs Improvement**: > 2m

**Circuit Breaker Trips:**
- **Expected**: > 0 when failures injected
- **Concern**: 0 (circuit breaker not triggering)

### Example Analysis

```
Experiment: PMS API Failure (20% error rate injected)
Duration: 60s
Results:
  - Total Requests: 1000
  - Affected Requests: 200 (20%)
  - Successful: 850 (85%)
  - Failed: 150 (15%)
  - Error Rate: 15%
  - Availability: 85%
  - Circuit Breaker Trips: 3
  - MTTR: 45s

Analysis:
✅ Circuit breaker opened after failures (3 trips)
✅ Error rate (15%) lower than injection rate (20%) - retries working
✅ MTTR within acceptable range (45s < 2m)
⚠️  Availability dropped to 85% (below 95% target)
📝 Action: Investigate why 5% more requests failed beyond injected faults
📝 Action: Consider increasing cache TTL for better fallback
```

### Grafana Dashboards

**During Chaos Experiment:**
1. **System Overview**: Watch P95 latency, error rate, requests/sec
2. **SLO Compliance**: Verify SLO violations are expected and temporary
3. **Performance Metrics**: Check PMS latency, DB query times
4. **Business Metrics**: Ensure guest operations aren't permanently affected

### Log Analysis

Look for:
- `chaos_experiment_started`: Experiment began
- `chaos_fault_injected`: Faults being applied
- `chaos_safety_error_rate_high`: Safety abort triggered
- `chaos_experiment_completed`: Experiment finished
- `chaos_experiment_context_exited`: Rollback completed

---

## 9. Best Practices

### DO

✅ **Start Small**: Begin with single-request, low-probability experiments  
✅ **Automate**: Integrate into CI/CD for continuous validation  
✅ **Document**: Record hypotheses, results, and learnings  
✅ **Monitor**: Watch dashboards during experiments  
✅ **Iterate**: Gradually increase blast radius and complexity  
✅ **Learn**: Use failures to improve resilience mechanisms  
✅ **Communicate**: Notify team before running experiments

### DON'T

❌ **Skip Dry Runs**: Always test in dry-run mode first  
❌ **Run Concurrent**: Multiple experiments interfere with each other  
❌ **Ignore Safety Limits**: They exist for a reason  
❌ **Test in Production** (initially): Validate in staging first  
❌ **Forget Rollback**: Always verify rollback works  
❌ **Rush**: Take time to analyze results before next experiment

### Experiment Design

**Good Hypothesis:**
> "When PMS API returns 500 errors for 20% of requests, the circuit breaker will open after 5 consecutive failures, and the system will serve cached availability data with P95 latency < 3s."

**Bad Hypothesis:**
> "The system will handle PMS failures."

**Good Hypothesis:**
- Specific failure mode (500 errors, 20% rate)
- Expected behavior (circuit breaker opens after 5 failures)
- Measurable outcome (P95 latency < 3s, cached data served)

---

## 10. Troubleshooting

### Experiment Won't Start

**Problem**: `Pre-flight checks failed`

**Solutions:**
- Check if another experiment is running: `manager.get_active_experiments()`
- Verify duration < 30 minutes
- Reduce blast radius if `ENTIRE_SYSTEM`

### Experiment Aborted Early

**Problem**: `Runtime safety checks failed`

**Solutions:**
- Check metrics: Error rate might have exceeded 50%
- Verify availability didn't drop below 50%
- Review logs for `chaos_safety_*` messages
- Reduce fault injection probability

### No Faults Being Injected

**Problem**: Requests succeeding at 100%

**Solutions:**
- Verify `chaos_middleware` decorator applied to target functions
- Check `target_service` name matches service in code
- Ensure `fault_config.enabled = True`
- Increase `probability` if very low
- Check logs for `chaos_fault_injected` messages

### Rollback Not Working

**Problem**: Faults persist after experiment

**Solutions:**
- Manually stop: `manager.stop_experiment(exp_id)`
- Check experiment state: `experiment.state`
- Verify fault config removed from manager
- Restart application if needed

### Metrics Not Collected

**Problem**: `ChaosMetrics` shows all zeros

**Solutions:**
- Ensure Prometheus is scraping `/metrics` endpoint
- Verify experiment duration long enough to collect data
- Check `_collect_metrics()` implementation
- Increase experiment duration

### Circuit Breaker Not Tripping

**Problem**: High error rate but no CB trips

**Solutions:**
- Verify circuit breaker configured on target service
- Check CB threshold settings (number of failures, time window)
- Increase fault injection probability
- Use `FaultType.CIRCUIT_BREAK` to explicitly trigger

---

## 11. Integration with CI/CD

### GitHub Actions Workflow

```yaml
name: Chaos Engineering Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:  # Manual trigger

jobs:
  chaos-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --all-extras
      
      - name: Start services
        run: docker compose up -d
      
      - name: Run chaos scenarios
        run: make chaos-all
      
      - name: Generate report
        run: make chaos-report
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: chaos-report
          path: .playbook/chaos_reports/latest.txt
```

### Pre-Deployment Validation

```bash
# In CI/CD pipeline before production deployment
make chaos-resilience

# If tests pass, proceed with deployment
# If tests fail, block deployment
```

### Continuous Chaos (GameDay)

Schedule regular "GameDays" where chaos experiments run in production-like environments:

```bash
# Weekly chaos gameday
0 10 * * 5 make chaos-all >> /var/log/chaos-gameday.log 2>&1
```

---

## 12. References

### External Resources

- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Netflix Chaos Monkey](https://netflix.github.io/chaosmonkey/)
- [Google SRE Book - Chapter 32: Chaos Engineering](https://sre.google/sre-book/production-environment/)
- [AWS Fault Injection Simulator](https://aws.amazon.com/fis/)

### Related Documentation

- `docs/P015-PERFORMANCE-TESTING-GUIDE.md`: Performance testing framework
- `docs/P016-OBSERVABILITY-GUIDE.md`: Monitoring and observability
- `docs/OPERATIONS_MANUAL.md`: Operational procedures
- `docs/HANDOVER_PACKAGE.md`: System architecture

### Project Files

- `app/core/chaos.py`: Chaos engineering framework
- `tests/chaos/orchestrator.py`: Experiment orchestration
- `tests/chaos/scenarios/`: Predefined chaos scenarios
- `tests/chaos/test_advanced_resilience.py`: Resilience test suite
- `Makefile`: Chaos engineering targets

---

## Appendix: Quick Reference

### Common Commands

```bash
# Dry run
make chaos-dry-run

# Run specific category
make chaos-network
make chaos-service
make chaos-database
make chaos-pms

# Run all scenarios
make chaos-all

# Generate report
make chaos-report

# Resilience tests
make chaos-resilience
```

### Fault Types Summary

| Type | Effect | Config |
|------|--------|--------|
| LATENCY | Delay | `latency_ms`, `latency_jitter_ms` |
| EXCEPTION | Raise error | `exception_class`, `exception_message` |
| TIMEOUT | Long delay + error | `timeout_ms` |
| CIRCUIT_BREAK | Connection error | None |
| RATE_LIMIT | Reject excess requests | `rate_limit_requests`, `rate_limit_window_seconds` |
| RESOURCE_EXHAUSTION | Resource error | `exception_message` |

### Blast Radius Levels

1. `SINGLE_REQUEST`: One request (safest)
2. `SINGLE_SERVICE`: One instance
3. `SERVICE_CLUSTER`: All instances
4. `ENTIRE_SYSTEM`: Whole system (most risky)

---

**Document Version:** 1.0.0  
**Last Updated:** October 15, 2025  
**Maintained By:** DevOps Team  
**Review Cycle:** Quarterly

For questions or issues, refer to `OPERATIONS_MANUAL.md` or contact the DevOps team.
