# P015: Performance Testing Guide

**Status:** ✅ Complete  
**Version:** 1.0.0  
**Last Updated:** October 14, 2025  
**Author:** AI Agent  

---

## Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [Architecture](#architecture)
- [Test Scenarios](#test-scenarios)
- [SLO Definitions](#slo-definitions)
- [Installation & Setup](#installation--setup)
- [Usage Examples](#usage-examples)
- [Results Interpretation](#results-interpretation)
- [CI/CD Integration](#cicd-integration)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Appendix](#appendix)

---

## Overview

The Performance Testing Suite provides comprehensive load testing capabilities for the Agente Hotelero IA system using **k6** (Grafana's modern load testing tool) and custom Python validation scripts.

### Key Features

- ✅ **5 Test Scenarios**: Smoke, Load, Stress, Spike, Soak
- ✅ **SLO Validation**: Automated compliance checking against performance targets
- ✅ **Multi-Endpoint Coverage**: Health checks, WhatsApp webhooks, PMS operations, reservations
- ✅ **Custom Metrics**: Detailed latency, throughput, error tracking
- ✅ **HTML Reports**: Visual performance analysis
- ✅ **CI/CD Ready**: Exit codes for automated deployment gates

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Load Testing | k6 | Latest | Test execution and metrics collection |
| Validation | Python 3.10+ | 3.10+ | SLO validation and reporting |
| Reporting | k6-reporter | Latest | HTML report generation |
| Storage | JSON/Markdown | - | Results persistence |

---

## Objectives

### Primary Goals

1. **Validate SLO Compliance**: Ensure system meets performance requirements
2. **Identify Bottlenecks**: Find performance constraints before production
3. **Establish Baselines**: Document performance characteristics for comparison
4. **Prevent Regressions**: Catch performance degradation in CI/CD
5. **Capacity Planning**: Determine scalability limits

### Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| P95 Latency | < 3000ms | 95th percentile response time |
| P99 Latency | < 5000ms | 99th percentile response time |
| Error Rate | < 1% | Failed requests / Total requests |
| Throughput | > 10 RPS | Requests per second |
| Check Pass Rate | > 99% | Successful validations |
| Avg Latency | < 1500ms | Mean response time |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Performance Testing Suite                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
        ┌───────▼────────┐             ┌───────▼────────┐
        │  k6 Test Suite │             │   Validation   │
        │   (JavaScript) │             │     Script     │
        └───────┬────────┘             │    (Python)    │
                │                      └───────┬────────┘
                │ JSON Results                 │
                └──────────────┬───────────────┘
                               │
                ┌──────────────▼──────────────┐
                │   Reports & Artifacts       │
                │  (.performance/ directory)  │
                └─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼───┐     ┌────▼────┐    ┌────▼────┐
    │ JSON  │     │  HTML   │    │Markdown │
    │Results│     │ Report  │    │ Summary │
    └───────┘     └─────────┘    └─────────┘
```

### Data Flow

1. **k6 Execution**: Load tests run against API endpoints
2. **Metrics Collection**: Custom metrics tracked during execution
3. **JSON Export**: Results exported to `.performance/` directory
4. **Python Validation**: SLO compliance validated
5. **Report Generation**: HTML/Markdown reports created
6. **Exit Code**: Return appropriate status for CI/CD

---

## Test Scenarios

### 1. Smoke Test 🚬

**Purpose**: Minimal load validation - verify system works under light load

**Configuration**:
```javascript
{
    executor: 'constant-vus',
    vus: 1,
    duration: '1m',
    tags: { test_type: 'smoke' }
}
```

**Use Cases**:
- ✅ Quick sanity check after deployment
- ✅ Validate API is responding
- ✅ Check basic functionality
- ✅ Pre-flight check before larger tests

**Expected Results**:
- All health checks pass
- Error rate = 0%
- P95 latency < 500ms

**When to Run**:
- After every deployment
- Before running larger tests
- As part of smoke testing pipeline
- Daily health checks

---

### 2. Load Test 📊

**Purpose**: Normal operational load - validate SLOs under typical traffic

**Configuration**:
```javascript
{
    executor: 'ramping-vus',
    stages: [
        { duration: '2m', target: 5 },   // Warm up
        { duration: '5m', target: 10 },  // Normal load
        { duration: '5m', target: 10 },  // Sustain
        { duration: '2m', target: 0 }    // Cool down
    ],
    tags: { test_type: 'load' }
}
```

**Traffic Mix**:
- 60% WhatsApp messages
- 40% PMS operations
- 30% Reservation flows
- 10% Metrics queries

**Use Cases**:
- ✅ Validate SLO compliance
- ✅ Test typical user behavior
- ✅ Baseline performance measurement
- ✅ Pre-production validation

**Expected Results**:
- P95 latency < 3000ms
- Error rate < 1%
- Throughput > 10 RPS
- All SLOs met

**When to Run**:
- Before major releases
- Weekly performance validation
- After infrastructure changes
- Baseline establishment

---

### 3. Stress Test 💪

**Purpose**: Find breaking point - determine system limits

**Configuration**:
```javascript
{
    executor: 'ramping-vus',
    stages: [
        { duration: '2m', target: 10 },  // Warm up
        { duration: '5m', target: 20 },  // Approaching limit
        { duration: '5m', target: 30 },  // Above normal
        { duration: '5m', target: 40 },  // Stress level
        { duration: '5m', target: 50 },  // Breaking point
        { duration: '5m', target: 0 }    // Recovery
    ],
    tags: { test_type: 'stress' }
}
```

**Objectives**:
- Find maximum capacity
- Identify resource bottlenecks
- Test error handling under stress
- Validate graceful degradation

**Use Cases**:
- ✅ Capacity planning
- ✅ Infrastructure sizing
- ✅ Circuit breaker validation
- ✅ Auto-scaling threshold tuning

**Expected Results**:
- System remains stable up to 30 VUs
- Graceful degradation beyond capacity
- Circuit breakers activate appropriately
- Recovery after load removal

**When to Run**:
- Before capacity planning decisions
- After infrastructure upgrades
- Quarterly validation
- Before high-traffic events

---

### 4. Spike Test ⚡

**Purpose**: Sudden traffic burst - test resilience to rapid load increases

**Configuration**:
```javascript
{
    executor: 'ramping-vus',
    stages: [
        { duration: '10s', target: 5 },   // Baseline
        { duration: '10s', target: 100 }, // Sudden spike!
        { duration: '1m', target: 100 },  // Maintain
        { duration: '10s', target: 5 },   // Back to baseline
        { duration: '2m', target: 5 }     // Stabilize
    ],
    tags: { test_type: 'spike' }
}
```

**Scenarios**:
- Marketing campaign launch
- Viral social media post
- Event-driven traffic (hotel promotion)
- DDoS simulation

**Use Cases**:
- ✅ Test auto-scaling responsiveness
- ✅ Validate rate limiting
- ✅ Check queue handling
- ✅ Verify crash recovery

**Expected Results**:
- No service crashes
- Rate limiting activates
- Queue absorbs burst
- Quick recovery (<30s)

**When to Run**:
- Before marketing campaigns
- After rate limiting changes
- Monthly resilience testing
- Pre-event validation

---

### 5. Soak Test 🛁

**Purpose**: Extended duration - detect memory leaks and resource exhaustion

**Configuration**:
```javascript
{
    executor: 'constant-vus',
    vus: 5,
    duration: '30m',
    tags: { test_type: 'soak' }
}
```

**Monitoring Focus**:
- Memory usage over time
- Connection pool health
- Database connection leaks
- Cache effectiveness
- CPU utilization trends

**Use Cases**:
- ✅ Memory leak detection
- ✅ Connection pool validation
- ✅ Cache hit rate analysis
- ✅ Long-term stability

**Expected Results**:
- Stable memory usage
- No connection leaks
- Consistent performance
- No degradation over time

**When to Run**:
- After major code changes
- Before production deployment
- Monthly stability testing
- Post-incident validation

---

## SLO Definitions

### Service Level Objectives

| SLO Name | Target | Warning | Level | Description |
|----------|--------|---------|-------|-------------|
| **P95 Latency** | < 3000ms | < 2500ms | P0 | 95th percentile response time |
| **P99 Latency** | < 5000ms | < 4000ms | P1 | 99th percentile response time |
| **Error Rate** | < 1% | < 0.5% | P0 | Failed requests percentage |
| **Throughput** | > 10 RPS | > 15 RPS | P2 | Minimum requests per second |
| **Check Pass Rate** | > 99% | > 99.5% | P1 | Validation success rate |
| **Avg Latency** | < 1500ms | < 1000ms | P2 | Mean response time |

### SLO Status Levels

| Status | Description | Action Required |
|--------|-------------|-----------------|
| ✅ **PASS** | All thresholds met | None - continue monitoring |
| ⚠️ **WARNING** | Approaching threshold | Review performance trends |
| ❌ **FAIL** | SLO violated | Investigate and optimize |
| 🚨 **CRITICAL** | P0 SLO failed | Block deployment, urgent fix |

### Compliance Matrix

```
SLO Compliance = (Passed SLOs / Total SLOs) × 100%

100%     = ✅ Excellent (deploy approved)
90-99%   = ⚠️  Good (review warnings)
70-89%   = ❌ Fair (optimization needed)
< 70%    = 🚨 Critical (deployment blocked)
```

---

## Installation & Setup

### Prerequisites

```bash
# System Requirements
- Linux/macOS/Windows with WSL
- Docker + Docker Compose (optional)
- Node.js 16+ (for k6)
- Python 3.10+

# Hardware Recommendations
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 10+ GB free space
```

### Install k6

#### Option 1: Package Manager (Recommended)

```bash
# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Linux (Fedora/CentOS)
sudo dnf install https://dl.k6.io/rpm/repo.rpm
sudo dnf install k6
```

#### Option 2: Docker

```bash
docker pull grafana/k6:latest

# Run tests via Docker
docker run --rm -i grafana/k6:latest run - <tests/load/k6-performance-suite.js
```

### Install Python Dependencies

```bash
# Using Poetry (recommended)
cd agente-hotel-api
poetry install --with dev

# Using pip
pip install -r requirements-dev.txt
```

### Verify Installation

```bash
# Check k6 version
k6 version

# Expected output:
# k6 v0.48.0 (2023-11-29, go1.21.1, linux/amd64)

# Verify Python script
python3 tests/load/validate_performance.py --help
```

### Directory Setup

```bash
# Create performance artifacts directory
mkdir -p .performance

# Set permissions
chmod +x tests/load/validate_performance.py
```

---

## Usage Examples

### Quick Start

```bash
# 1. Start the application
make docker-up

# 2. Wait for services to be ready
make health

# 3. Run smoke test
make perf-smoke

# 4. Validate results
make perf-validate
```

### Scenario-Specific Examples

#### Smoke Test (1 minute)

```bash
# Via Makefile
make perf-smoke

# Manual execution
k6 run --env SCENARIO=smoke \
       --out json=.performance/results-smoke.json \
       tests/load/k6-performance-suite.js

# Validate
python3 tests/load/validate_performance.py \
        --results .performance/results-smoke.json \
        --format console
```

#### Load Test (14 minutes)

```bash
# Via Makefile
make perf-load

# Manual execution
k6 run --env SCENARIO=load \
       --env BASE_URL=http://localhost:8000 \
       --out json=.performance/results-load.json \
       tests/load/k6-performance-suite.js

# Generate HTML report
python3 tests/load/validate_performance.py \
        --results .performance/results-load.json \
        --format markdown \
        --output .performance/load-test-report.md
```

#### Stress Test (27 minutes)

```bash
# Via Makefile
make perf-stress

# Manual with custom parameters
k6 run --env SCENARIO=stress \
       --env BASE_URL=http://localhost:8000 \
       --vus 50 \
       --duration 30m \
       tests/load/k6-performance-suite.js
```

#### Spike Test (4 minutes)

```bash
# Via Makefile
make perf-spike

# Check if rate limiting activated
grep -i "rate limit" .performance/results-spike.json
```

#### Soak Test (30 minutes)

```bash
# Run in background
make perf-soak &

# Monitor in real-time
watch -n 5 'docker stats agente-api --no-stream'

# Check for memory leaks
python3 tests/load/validate_performance.py \
        --results .performance/results-soak.json \
        --format console | grep -A 10 "LATENCY METRICS"
```

### Advanced Usage

#### Custom Base URL

```bash
k6 run --env BASE_URL=https://staging.example.com \
       --env SCENARIO=load \
       tests/load/k6-performance-suite.js
```

#### Custom VU Count

```bash
# Override scenario VUs
k6 run --vus 20 --duration 10m \
       --env SCENARIO=load \
       tests/load/k6-performance-suite.js
```

#### Multiple Output Formats

```bash
k6 run --env SCENARIO=load \
       --out json=.performance/results.json \
       --out csv=.performance/results.csv \
       --summary-export=.performance/summary.json \
       tests/load/k6-performance-suite.js
```

#### CI/CD Mode (Minimal Output)

```bash
python3 tests/load/validate_performance.py --ci-mode

# Exit code indicates status:
# 0 = PASS
# 1 = WARNING/FAIL
# 2 = CRITICAL
```

---

## Results Interpretation

### k6 Console Output

```
     ✓ health_live: status is 200
     ✓ health_ready: status is 200
     ✓ whatsapp_webhook: status is 200

     checks.........................: 99.50% ✓ 995     ✗ 5
     errors.........................: 0.50%  ✓ 5       ✗ 0
     http_req_duration..............: avg=1250ms  min=100ms  med=1100ms  max=4500ms  p(90)=2500ms  p(95)=2800ms
     http_req_failed................: 0.50%  ✓ 5       ✗ 995
     http_reqs......................: 1000   16.67/s
     vus............................: 10     min=0     max=10
```

### Key Metrics Explained

| Metric | Meaning | Good Value | Bad Value |
|--------|---------|------------|-----------|
| **checks** | % of validation checks passed | > 99% | < 95% |
| **http_req_duration (p95)** | 95% of requests under this time | < 3000ms | > 5000ms |
| **http_req_failed** | % of failed HTTP requests | < 1% | > 5% |
| **http_reqs** | Total requests and rate (RPS) | > 10 RPS | < 5 RPS |
| **vus** | Virtual users (concurrent) | Steady | Erratic |

### Validation Report Structure

```
═══════════════════════════════════════════════════════════════
📊 PERFORMANCE VALIDATION REPORT
═══════════════════════════════════════════════════════════════
Test: results-load-2025-10-14
Scenario: LOAD
Timestamp: 2025-10-14T10:30:00
Duration: 840.5s
═══════════════════════════════════════════════════════════════

📈 LATENCY METRICS
────────────────────────────────────────────────────────────────
Min:          100.50 ms
Avg:         1250.30 ms  ← Average response time
Median:      1100.20 ms
P90:         2500.40 ms
P95:         2800.50 ms  ← 95% of requests under this
P99:         4200.60 ms  ← 99% of requests under this
Max:         4500.70 ms

🚀 THROUGHPUT METRICS
────────────────────────────────────────────────────────────────
Total Requests:           14000
Successful:               13930
Failed:                      70
Requests/sec:             16.67  ← Average RPS

❌ ERROR METRICS
────────────────────────────────────────────────────────────────
Total Errors:                70
Error Rate:                0.50%  ← Below 1% target ✅

✅ CHECK METRICS
────────────────────────────────────────────────────────────────
Total Checks:             42000
Passed:                   41790
Failed:                     210
Pass Rate:                99.50%  ← Above 99% target ✅

🎯 SLO VALIDATION RESULTS
═══════════════════════════════════════════════════════════════

✅ P95_LATENCY_MS
   Description: 95th percentile response time must be under 3 seconds
   Measured:    2800.50
   Target:      3000.00
   Status:      PASS (P0)
   Deviation:   -6.65%  ← 6.65% better than target

⚠️  THROUGHPUT_RPS
   Description: Minimum throughput of 10 requests per second
   Measured:    16.67
   Target:      10.00
   Warning:     15.00
   Status:      WARNING (P2)
   Deviation:   +66.70%  ← Above target, but below warning threshold

═══════════════════════════════════════════════════════════════
🏁 OVERALL STATUS
═══════════════════════════════════════════════════════════════
✅ PASS

💡 RECOMMENDATIONS
────────────────────────────────────────────────────────────────
  🔧 throughput_rps: Consider load balancing optimization
  🔧 Review connection pool configuration
```

### Status Indicators

| Symbol | Status | Action |
|--------|--------|--------|
| ✅ | PASS | SLO met, no action needed |
| ⚠️ | WARNING | Approaching threshold, monitor |
| ❌ | FAIL | SLO violated, optimization needed |
| 🚨 | CRITICAL | P0 failure, block deployment |

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Performance Testing

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance-test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Setup k6
        uses: grafana/setup-k6-action@v1
      
      - name: Start Services
        run: |
          docker-compose up -d
          sleep 30  # Wait for services
      
      - name: Run Smoke Test
        run: make perf-smoke
      
      - name: Run Load Test
        run: make perf-load
        continue-on-error: true
      
      - name: Validate Results
        id: validate
        run: |
          python3 tests/load/validate_performance.py --ci-mode
          echo "exit_code=$?" >> $GITHUB_OUTPUT
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: .performance/
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('.performance/summary.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 📊 Performance Test Results\n\n${report}`
            });
      
      - name: Fail if Critical
        if: steps.validate.outputs.exit_code == '2'
        run: exit 1
```

### GitLab CI Pipeline

```yaml
performance-test:
  stage: test
  image: grafana/k6:latest
  services:
    - docker:dind
  before_script:
    - docker-compose up -d
    - sleep 30
  script:
    - k6 run --env SCENARIO=load tests/load/k6-performance-suite.js
    - python3 tests/load/validate_performance.py --ci-mode
  artifacts:
    paths:
      - .performance/
    when: always
  only:
    - merge_requests
    - main
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'make docker-up'
                sh 'sleep 30'
            }
        }
        
        stage('Smoke Test') {
            steps {
                sh 'make perf-smoke'
            }
        }
        
        stage('Load Test') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    sh 'make perf-load'
                }
            }
        }
        
        stage('Validate') {
            steps {
                script {
                    def exitCode = sh(
                        script: 'python3 tests/load/validate_performance.py --ci-mode',
                        returnStatus: true
                    )
                    
                    if (exitCode == 2) {
                        error('Critical SLO violations detected')
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '.performance/**', allowEmptyArchive: true
            publishHTML([
                reportDir: '.performance',
                reportFiles: 'summary-*.html',
                reportName: 'Performance Report'
            ])
        }
    }
}
```

### Pre-Deployment Gate

```bash
#!/bin/bash
# scripts/pre-deploy-perf-check.sh

set -e

echo "🚀 Running pre-deployment performance validation..."

# Start services
docker-compose up -d
sleep 30

# Run load test
make perf-load

# Validate against SLOs
python3 tests/load/validate_performance.py --ci-mode

EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "🚨 CRITICAL: Performance validation failed!"
    echo "Deployment BLOCKED due to SLO violations"
    exit 1
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠️  WARNING: Some SLOs not met, but deployment allowed"
    exit 0
else
    echo "✅ PASS: All performance SLOs met"
    exit 0
fi
```

---

## Performance Optimization

### Common Bottlenecks

#### 1. Database Queries

**Symptoms**:
- High P95 latency (> 5000ms)
- Increasing response times under load
- Database CPU at 100%

**Solutions**:
```python
# Add indexes
CREATE INDEX idx_sessions_phone ON sessions(guest_phone);
CREATE INDEX idx_reservations_dates ON reservations(check_in, check_out);

# Use connection pooling
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 40

# Implement query optimization
# Bad: N+1 queries
for reservation in reservations:
    guest = db.query(Guest).filter_by(id=reservation.guest_id).first()

# Good: Eager loading
reservations = db.query(Reservation).options(
    joinedload(Reservation.guest)
).all()
```

#### 2. External API Calls

**Symptoms**:
- Timeouts under load
- Circuit breaker activation
- High error rates

**Solutions**:
```python
# Implement caching
@cached(ttl=300)
async def get_availability(check_in, check_out):
    return await pms_client.check_availability(check_in, check_out)

# Use connection pooling
async with aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=100)
) as session:
    # Reuse connections

# Set appropriate timeouts
timeout = aiohttp.ClientTimeout(total=5, connect=2)
```

#### 3. Memory Leaks

**Symptoms**:
- Increasing memory usage in soak tests
- OOM kills after extended runtime
- Performance degradation over time

**Solutions**:
```python
# Close database sessions
try:
    session = SessionLocal()
    # ... operations
finally:
    session.close()

# Use context managers
async with AsyncSessionFactory() as session:
    # Automatically closed

# Clear caches periodically
if cache_size > MAX_CACHE_SIZE:
    cache.clear_old_entries()
```

#### 4. CPU Bottlenecks

**Symptoms**:
- CPU at 100% during tests
- Low throughput despite low latency
- Thread pool exhaustion

**Solutions**:
```python
# Increase worker processes
gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Use async operations
async def process_messages(messages):
    tasks = [process_message(msg) for msg in messages]
    return await asyncio.gather(*tasks)

# Implement background tasks
background_tasks.add_task(send_email, email)
```

### Optimization Checklist

- [ ] Database indexes created
- [ ] Connection pooling configured
- [ ] Caching implemented (Redis)
- [ ] Async operations used
- [ ] Circuit breakers active
- [ ] Rate limiting configured
- [ ] Worker count optimized
- [ ] Memory leaks fixed
- [ ] Static assets cached
- [ ] Compression enabled (gzip)

---

## Troubleshooting

### Common Issues

#### Issue 1: k6 Not Found

```bash
# Error
bash: k6: command not found

# Solution
# Install k6 (see Installation section)
brew install k6  # macOS
sudo apt install k6  # Linux
```

#### Issue 2: Connection Refused

```bash
# Error
WARN[0001] Request Failed error="Get \"http://localhost:8000/health/live\": dial tcp [::1]:8000: connect: connection refused"

# Solution
# Ensure services are running
make docker-up
make health

# Check BASE_URL
k6 run --env BASE_URL=http://host.docker.internal:8000 tests/load/k6-performance-suite.js
```

#### Issue 3: High Error Rates

```bash
# Error
http_req_failed: 25% (errors > 1% threshold)

# Debug
# Check logs
docker logs agente-api -f

# Verify rate limiting
curl -v http://localhost:8000/health/ready

# Review PMS adapter status
curl http://localhost:8000/metrics | grep pms_circuit_breaker_state
```

#### Issue 4: Validation Script Fails

```bash
# Error
FileNotFoundError: .performance/results-smoke.json

# Solution
# Ensure k6 exports JSON
k6 run --out json=.performance/results-smoke.json tests/load/k6-performance-suite.js

# Check file permissions
ls -la .performance/
chmod 644 .performance/*.json
```

#### Issue 5: OOM During Soak Test

```bash
# Error
docker: OOMKilled

# Solution
# Increase Docker memory
docker-compose.yml:
  agente-api:
    deploy:
      resources:
        limits:
          memory: 2G

# Monitor memory usage
docker stats agente-api --no-stream

# Run shorter soak test
k6 run --env SCENARIO=soak --duration 10m tests/load/k6-performance-suite.js
```

### Debug Mode

```bash
# Enable k6 verbose output
k6 run --verbose tests/load/k6-performance-suite.js

# Enable Python debug logging
python3 tests/load/validate_performance.py --debug --results .performance/results.json

# Check application logs
docker logs agente-api -f | grep ERROR

# Monitor metrics in real-time
watch -n 1 'curl -s http://localhost:8000/metrics | grep http_requests_total'
```

---

## Best Practices

### Test Design

1. **Start Small**: Always run smoke test before larger scenarios
2. **Ramp Gradually**: Use ramp-up periods to avoid sudden load
3. **Think Time**: Include realistic delays between requests
4. **Data Variety**: Use diverse test data (different phones, dates)
5. **Endpoint Mix**: Test realistic traffic distribution

### Execution

1. **Isolate Environment**: Run tests on dedicated infrastructure
2. **Consistent Baseline**: Use same hardware/network for comparisons
3. **Monitor Resources**: Watch CPU/memory/disk during tests
4. **Document Context**: Record system state, versions, config
5. **Repeat Tests**: Run multiple times to confirm results

### Analysis

1. **Compare Trends**: Track metrics over time, not just absolute values
2. **Investigate Outliers**: Don't ignore P99/max values
3. **Correlate Errors**: Match errors with specific test phases
4. **Review All SLOs**: Don't focus only on latency
5. **Act on Findings**: Prioritize optimization based on impact

### Automation

1. **CI/CD Integration**: Block deployments on critical failures
2. **Scheduled Tests**: Run daily/weekly baseline tests
3. **Alert on Regressions**: Notify team of performance degradation
4. **Artifact Retention**: Keep historical results for comparison
5. **Self-Service**: Enable developers to run tests locally

---

## Appendix

### A. Makefile Targets Reference

```makefile
# Performance Testing Targets
make perf-smoke        # Quick validation (1 min)
make perf-load         # Normal load test (14 min)
make perf-stress       # Stress test (27 min)
make perf-spike        # Spike test (4 min)
make perf-soak         # Extended test (30 min)
make perf-validate     # Validate last results
make perf-baseline     # Establish baseline
make perf-clean        # Clean results directory
```

### B. Exit Codes Reference

| Exit Code | Status | Meaning | Action |
|-----------|--------|---------|--------|
| 0 | SUCCESS | All SLOs passed | Deploy approved |
| 1 | WARNING | Some SLOs failed (non-critical) | Review recommended |
| 2 | CRITICAL | Critical SLO failures | Deployment BLOCKED |

### C. File Structure

```
agente-hotel-api/
├── tests/
│   └── load/
│       ├── k6-performance-suite.js      # k6 test scenarios
│       └── validate_performance.py      # SLO validation script
├── .performance/                         # Results directory
│   ├── results-smoke-*.json             # k6 JSON output
│   ├── summary-smoke-*.html             # HTML reports
│   ├── load-test-report.md              # Markdown reports
│   └── baseline.json                    # Baseline metrics
├── docs/
│   └── P015-PERFORMANCE-TESTING-GUIDE.md  # This file
└── Makefile                             # Test execution targets
```

### D. Glossary

| Term | Definition |
|------|------------|
| **VU** | Virtual User - simulated concurrent user |
| **RPS** | Requests Per Second - throughput measure |
| **P95** | 95th Percentile - 95% of requests under this value |
| **P99** | 99th Percentile - 99% of requests under this value |
| **SLO** | Service Level Objective - performance target |
| **SLI** | Service Level Indicator - measured metric |
| **Latency** | Time from request to response |
| **Throughput** | Number of operations per time unit |
| **Check** | Validation assertion in test |
| **Scenario** | Load testing pattern (smoke, load, etc.) |

### E. Additional Resources

- [k6 Documentation](https://k6.io/docs/)
- [Grafana k6 Cloud](https://grafana.com/products/cloud/k6/)
- [Performance Testing Best Practices](https://k6.io/docs/testing-guides/)
- [SLO Definition Guide](https://sre.google/sre-book/service-level-objectives/)
- [Makefile Reference](../Makefile)

### F. Support

For issues or questions:
- **GitHub Issues**: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/issues
- **Documentation**: `/docs`
- **Logs**: `docker logs agente-api`
- **Metrics**: `http://localhost:8000/metrics`

---

**Document Version:** 1.0.0  
**Last Updated:** October 14, 2025  
**Status:** ✅ Complete  
**Next Review:** January 2026
