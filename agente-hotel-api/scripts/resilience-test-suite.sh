#!/bin/bash

# Performance & Chaos Test Report Generator
# This script runs both performance and chaos tests, collecting comprehensive metrics

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/resilience"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Ensure report directory exists
mkdir -p "$REPORT_DIR"

# Load guardrails configuration
source "$SCRIPT_DIR/guardrails.conf"

echo "🧪 Starting Comprehensive Resilience Testing Suite"
echo "📊 Report will be saved to: $REPORT_DIR"
echo "⏰ Started at: $(date)"

# Function to run performance tests
run_performance_tests() {
    echo ""
    echo "🚀 === PERFORMANCE TESTING PHASE ==="
    
    local start_time=$(date +%s)
    
    # Load Test
    echo "📈 Running Load Test..."
    timeout "${MAX_PERFORMANCE_TEST_DURATION}" k6 run \
        --out json="$REPORT_DIR/load-test-${TIMESTAMP}.json" \
        --summary-export="$REPORT_DIR/load-test-summary-${TIMESTAMP}.json" \
        "$PROJECT_ROOT/tests/performance/load-test.js" || {
        echo "⚠️  Load test timed out or failed"
        return 1
    }
    
    # Wait for system recovery
    echo "⏳ Waiting ${RECOVERY_WAIT_SECONDS}s for system recovery..."
    sleep "$RECOVERY_WAIT_SECONDS"
    
    # Stress Test
    echo "💥 Running Stress Test..."
    timeout "${MAX_PERFORMANCE_TEST_DURATION}" k6 run \
        --out json="$REPORT_DIR/stress-test-${TIMESTAMP}.json" \
        --summary-export="$REPORT_DIR/stress-test-summary-${TIMESTAMP}.json" \
        "$PROJECT_ROOT/tests/performance/stress-test.js" || {
        echo "⚠️  Stress test timed out or failed"
        return 1
    }
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo "✅ Performance tests completed in ${duration}s"
    
    # Generate performance summary
    cat > "$REPORT_DIR/performance-summary-${TIMESTAMP}.md" << EOF
# Performance Test Summary

**Timestamp**: $(date)
**Duration**: ${duration} seconds

## Load Test Results
- Raw data: \`load-test-${TIMESTAMP}.json\`
- Summary: \`load-test-summary-${TIMESTAMP}.json\`

## Stress Test Results
- Raw data: \`stress-test-${TIMESTAMP}.json\`
- Summary: \`stress-test-summary-${TIMESTAMP}.json\`

## Key Metrics Collected
- Request rates and response times
- Error rates and types
- Resource utilization
- Breaking point analysis
- Recovery characteristics

## Analysis
Run \`make analyze-performance REPORT=${TIMESTAMP}\` for detailed analysis.
EOF
}

# Function to run chaos engineering tests
run_chaos_tests() {
    echo ""
    echo "🌪️  === CHAOS ENGINEERING PHASE ==="
    
    local start_time=$(date +%s)
    
    # Database Chaos Test
    echo "🗄️  Running Database Chaos Test..."
    if ! timeout "${MAX_CHAOS_TEST_DURATION}" "$SCRIPT_DIR/chaos-db-failure.sh" > "$REPORT_DIR/chaos-db-${TIMESTAMP}.log" 2>&1; then
        echo "⚠️  Database chaos test timed out or failed"
        return 1
    fi
    
    # Wait for system recovery
    echo "⏳ Waiting ${RECOVERY_WAIT_SECONDS}s for system recovery..."
    sleep "$RECOVERY_WAIT_SECONDS"
    
    # Redis Chaos Test
    echo "🔄 Running Redis Chaos Test..."
    if ! timeout "${MAX_CHAOS_TEST_DURATION}" "$SCRIPT_DIR/chaos-redis-failure.sh" > "$REPORT_DIR/chaos-redis-${TIMESTAMP}.log" 2>&1; then
        echo "⚠️  Redis chaos test timed out or failed"
        return 1
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo "✅ Chaos tests completed in ${duration}s"
    
    # Generate chaos summary
    cat > "$REPORT_DIR/chaos-summary-${TIMESTAMP}.md" << EOF
# Chaos Engineering Test Summary

**Timestamp**: $(date)
**Duration**: ${duration} seconds

## Database Chaos Test
- Log file: \`chaos-db-${TIMESTAMP}.log\`
- Simulated PostgreSQL failure and recovery
- Monitored system behavior during outage

## Redis Chaos Test
- Log file: \`chaos-redis-${TIMESTAMP}.log\`
- Simulated Redis cache failures
- Tested multiple failure scenarios (stop, network, memory)

## Resilience Validation
- Circuit breaker behavior
- Graceful degradation
- Recovery characteristics

## Analysis
Run \`make analyze-chaos REPORT=${TIMESTAMP}\` for detailed analysis.
EOF
}

# Function to collect system metrics during tests
collect_metrics() {
    echo ""
    echo "📊 === COLLECTING SYSTEM METRICS ==="
    
    # Prometheus query for key metrics
    local prometheus_url="http://localhost:9090"
    local queries=(
        "orchestrator_success_rate_all"
        "pms_circuit_breaker_state"
        "pms_cache_hit_ratio"
        "orchestrator_burn_rate_fast"
        "orchestrator_burn_rate_slow"
        "pms_cb_failure_ratio_5m"
    )
    
    for query in "${queries[@]}"; do
        echo "📈 Collecting metric: $query"
        if curl -s "${prometheus_url}/api/v1/query?query=${query}" > "$REPORT_DIR/metric-${query}-${TIMESTAMP}.json"; then
            echo "✅ Collected: $query"
        else
            echo "⚠️  Failed to collect: $query"
        fi
    done
}

# Function to generate final report
generate_final_report() {
    echo ""
    echo "📋 === GENERATING FINAL REPORT ==="
    
    cat > "$REPORT_DIR/resilience-report-${TIMESTAMP}.md" << EOF
# Comprehensive Resilience Test Report

**Generated**: $(date)
**Test Suite**: Performance Testing + Chaos Engineering
**Report ID**: ${TIMESTAMP}

## Executive Summary

This report contains results from comprehensive resilience testing including:
- Load and stress performance testing
- Database and cache failure simulation
- Circuit breaker and graceful degradation validation
- System recovery characteristics analysis

## Test Components

### Performance Testing
- **Load Test**: Realistic user behavior simulation
- **Stress Test**: Breaking point and recovery analysis
- **Files**: \`*load-test-${TIMESTAMP}*\`, \`*stress-test-${TIMESTAMP}*\`

### Chaos Engineering
- **Database Chaos**: PostgreSQL failure simulation
- **Cache Chaos**: Redis failure scenarios
- **Files**: \`*chaos-db-${TIMESTAMP}*\`, \`*chaos-redis-${TIMESTAMP}*\`

### System Metrics
- **Circuit Breaker States**: Real-time monitoring
- **SLO Burn Rates**: Error budget consumption
- **Cache Performance**: Hit ratios and degradation
- **Files**: \`*metric-*-${TIMESTAMP}*\`

## Analysis Commands

\`\`\`bash
# Analyze performance results
make analyze-performance REPORT=${TIMESTAMP}

# Analyze chaos results
make analyze-chaos REPORT=${TIMESTAMP}

# Generate trends report
make trends-report REPORT=${TIMESTAMP}

# View in Grafana dashboard
make open-resilience-dashboard
\`\`\`

## Recommendations

1. **Performance**: Review breaking points and scaling thresholds
2. **Resilience**: Validate circuit breaker timing and recovery
3. **Monitoring**: Ensure SLO burn rate alerts are properly configured
4. **Operations**: Update runbooks based on failure scenarios

## Next Steps

- Schedule regular resilience testing (weekly/monthly)
- Integrate results into SLO reporting
- Update incident response procedures
- Consider additional chaos scenarios

---
*Generated by Agente Hotelero IA Resilience Testing Suite*
EOF

    echo "📄 Final report generated: resilience-report-${TIMESTAMP}.md"
}

# Main execution
main() {
    local exit_code=0
    
    # Validate prerequisites
    if ! command -v k6 &> /dev/null; then
        echo "❌ k6 not found. Please install k6 load testing tool."
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        echo "❌ Docker not available. Please ensure Docker is running."
        exit 1
    fi
    
    # Run test phases
    if ! run_performance_tests; then
        echo "❌ Performance testing failed"
        exit_code=1
    fi
    
    if ! run_chaos_tests; then
        echo "❌ Chaos testing failed"
        exit_code=1
    fi
    
    # Collect metrics regardless of test results
    collect_metrics
    
    # Generate final report
    generate_final_report
    
    echo ""
    echo "🎯 === RESILIENCE TESTING COMPLETE ==="
    echo "📊 Report ID: ${TIMESTAMP}"
    echo "📁 Location: $REPORT_DIR"
    echo "⏰ Finished at: $(date)"
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ All tests completed successfully"
    else
        echo "⚠️  Some tests failed - check individual logs"
    fi
    
    return $exit_code
}

# Execute main function
main "$@"