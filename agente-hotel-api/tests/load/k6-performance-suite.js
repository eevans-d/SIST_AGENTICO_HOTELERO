/**
 * ═══════════════════════════════════════════════════════════════════════════
 * k6 Performance Testing Suite - Agente Hotelero IA System
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * Comprehensive load testing suite for validating system performance under
 * various load conditions and ensuring SLO compliance.
 * 
 * Test Scenarios:
 * ---------------
 * 1. smoke_test: Minimal load validation (1 VU, 1 min)
 * 2. load_test: Normal operational load (10 VUs, 10 min)
 * 3. stress_test: Breaking point analysis (ramp to 50 VUs)
 * 4. spike_test: Traffic burst resilience (sudden 0→100→0 VUs)
 * 5. soak_test: Memory leak detection (5 VUs, 30 min)
 * 
 * SLO Targets:
 * ------------
 * - P95 Latency: < 3000ms
 * - Error Rate: < 1%
 * - Throughput: > 10 RPS
 * - Check Pass Rate: > 99%
 * 
 * Usage:
 * ------
 * # Run specific scenario
 * k6 run --env SCENARIO=smoke tests/load/k6-performance-suite.js
 * k6 run --env SCENARIO=load tests/load/k6-performance-suite.js
 * 
 * # Export results for validation
 * k6 run --out json=.performance/results-smoke.json tests/load/k6-performance-suite.js
 * 
 * # Run with custom BASE_URL
 * k6 run --env BASE_URL=http://localhost:8000 tests/load/k6-performance-suite.js
 * 
 * @version 1.0.0
 * @since P015
 * @author AI Agent
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";

// ═══════════════════════════════════════════════════════════════════════════
// CUSTOM METRICS
// ═══════════════════════════════════════════════════════════════════════════

const errorRate = new Rate('errors');
const successRate = new Rate('success');
const healthCheckDuration = new Trend('health_check_duration', true);
const reservationDuration = new Trend('reservation_duration', true);
const pmsOperationDuration = new Trend('pms_operation_duration', true);
const whatsappMessageDuration = new Trend('whatsapp_message_duration', true);

const totalRequests = new Counter('total_requests');
const failedRequests = new Counter('failed_requests');
const successfulRequests = new Counter('successful_requests');

const activeVUs = new Gauge('active_vus');

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'smoke';

// Test data pools
const GUEST_PHONES = [
    '+34600000001',
    '+34600000002',
    '+34600000003',
    '+34600000004',
    '+34600000005',
    '+34600000006',
    '+34600000007',
    '+34600000008',
    '+34600000009',
    '+34600000010'
];

const RESERVATION_REQUESTS = [
    'Hola, quisiera reservar una habitación para 2 personas del 20 al 25 de diciembre',
    'Buenos días, necesito una habitación doble para el próximo fin de semana',
    'Quiero hacer una reserva para 3 noches a partir del 15 de este mes',
    'Hola, tengo una pregunta sobre disponibilidad de habitaciones en enero',
    'Necesito cancelar mi reserva #12345',
    'Quisiera cambiar las fechas de mi reserva',
    'Qué servicios incluye la habitación?',
    'Tienen disponibilidad para 4 personas del 1 al 5 de febrero?'
];

// ═══════════════════════════════════════════════════════════════════════════
// SCENARIO CONFIGURATIONS
// ═══════════════════════════════════════════════════════════════════════════

const scenarios = {
    // Smoke Test: Minimal load - verify system works under light load
    smoke: {
        executor: 'constant-vus',
        vus: 1,
        duration: '1m',
        gracefulStop: '10s',
        tags: { test_type: 'smoke' }
    },

    // Load Test: Normal operational load - validate SLOs
    load: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '2m', target: 5 },   // Ramp up to 5 VUs
            { duration: '5m', target: 10 },  // Ramp up to 10 VUs (normal load)
            { duration: '5m', target: 10 },  // Stay at 10 VUs
            { duration: '2m', target: 0 }    // Ramp down
        ],
        gracefulRampDown: '30s',
        tags: { test_type: 'load' }
    },

    // Stress Test: Find breaking point
    stress: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '2m', target: 10 },  // Warm up
            { duration: '5m', target: 20 },  // Approaching normal load
            { duration: '5m', target: 30 },  // Above normal load
            { duration: '5m', target: 40 },  // Stress level
            { duration: '5m', target: 50 },  // Breaking point
            { duration: '5m', target: 0 }    // Recovery
        ],
        gracefulRampDown: '1m',
        tags: { test_type: 'stress' }
    },

    // Spike Test: Sudden traffic burst
    spike: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '10s', target: 5 },   // Baseline
            { duration: '10s', target: 100 }, // Sudden spike
            { duration: '1m', target: 100 },  // Maintain spike
            { duration: '10s', target: 5 },   // Return to baseline
            { duration: '2m', target: 5 },    // Stabilize
            { duration: '10s', target: 0 }    // Ramp down
        ],
        gracefulRampDown: '30s',
        tags: { test_type: 'spike' }
    },

    // Soak Test: Extended duration - detect memory leaks
    soak: {
        executor: 'constant-vus',
        vus: 5,
        duration: '30m',
        gracefulStop: '1m',
        tags: { test_type: 'soak' }
    }
};

// Select active scenario
export const options = {
    scenarios: {
        [SCENARIO]: scenarios[SCENARIO]
    },

    // SLO Thresholds
    thresholds: {
        // P95 latency must be under 3 seconds
        'http_req_duration': ['p(95)<3000'],
        
        // Error rate must be below 1%
        'http_req_failed': ['rate<0.01'],
        
        // 99% of checks must pass
        'checks': ['rate>0.99'],
        
        // Custom metrics thresholds
        'errors': ['rate<0.01'],
        'success': ['rate>0.99'],
        
        // Endpoint-specific thresholds
        'health_check_duration': ['p(95)<500'],
        'reservation_duration': ['p(95)<5000'],
        'pms_operation_duration': ['p(95)<4000'],
        'whatsapp_message_duration': ['p(95)<3000']
    },

    // Output configuration
    summaryTrendStats: ['min', 'avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
    
    // Tags for filtering
    tags: {
        environment: 'test',
        service: 'agente-hotel-api'
    }
};

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Get random element from array
 */
function getRandomElement(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Generate random check-in/check-out dates
 */
function getRandomDates() {
    const today = new Date();
    const checkIn = new Date(today);
    checkIn.setDate(today.getDate() + Math.floor(Math.random() * 30) + 1);
    
    const checkOut = new Date(checkIn);
    checkOut.setDate(checkIn.getDate() + Math.floor(Math.random() * 7) + 1);
    
    return {
        check_in: checkIn.toISOString().split('T')[0],
        check_out: checkOut.toISOString().split('T')[0]
    };
}

/**
 * Common check patterns
 */
function checkResponse(response, name, expectedStatus = 200) {
    const checks = {
        [`${name}: status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
        [`${name}: response time < 5s`]: (r) => r.timings.duration < 5000,
        [`${name}: has body`]: (r) => r.body && r.body.length > 0
    };
    
    const result = check(response, checks);
    
    // Update metrics
    totalRequests.add(1);
    if (result) {
        successRate.add(1);
        errorRate.add(0);
        successfulRequests.add(1);
    } else {
        successRate.add(0);
        errorRate.add(1);
        failedRequests.add(1);
    }
    
    return result;
}

// ═══════════════════════════════════════════════════════════════════════════
// TEST FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Test 1: Health Check Endpoints
 */
function testHealthChecks() {
    group('Health Checks', () => {
        // Liveness check
        const liveResponse = http.get(`${BASE_URL}/health/live`, {
            tags: { name: 'health_live' }
        });
        healthCheckDuration.add(liveResponse.timings.duration);
        checkResponse(liveResponse, 'health_live');

        // Readiness check
        const readyResponse = http.get(`${BASE_URL}/health/ready`, {
            tags: { name: 'health_ready' }
        });
        healthCheckDuration.add(readyResponse.timings.duration);
        checkResponse(readyResponse, 'health_ready');
    });
}

/**
 * Test 2: WhatsApp Webhook
 */
function testWhatsAppWebhook() {
    group('WhatsApp Webhook', () => {
        const phone = getRandomElement(GUEST_PHONES);
        const message = getRandomElement(RESERVATION_REQUESTS);
        
        const payload = JSON.stringify({
            object: 'whatsapp_business_account',
            entry: [{
                id: 'test-account-id',
                changes: [{
                    value: {
                        messaging_product: 'whatsapp',
                        metadata: {
                            display_phone_number: '34600000000',
                            phone_number_id: 'test-phone-id'
                        },
                        messages: [{
                            from: phone,
                            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                            timestamp: Math.floor(Date.now() / 1000).toString(),
                            type: 'text',
                            text: {
                                body: message
                            }
                        }]
                    },
                    field: 'messages'
                }]
            }]
        });

        const response = http.post(
            `${BASE_URL}/api/v1/webhooks/whatsapp`,
            payload,
            {
                headers: { 'Content-Type': 'application/json' },
                tags: { name: 'whatsapp_webhook' }
            }
        );

        whatsappMessageDuration.add(response.timings.duration);
        checkResponse(response, 'whatsapp_webhook', 200);
    });
}

/**
 * Test 3: PMS Operations (via Mock or Real)
 */
function testPMSOperations() {
    group('PMS Operations', () => {
        const dates = getRandomDates();
        
        // Check availability
        const availResponse = http.get(
            `${BASE_URL}/api/v1/pms/availability?check_in=${dates.check_in}&check_out=${dates.check_out}`,
            {
                tags: { name: 'pms_availability' }
            }
        );
        pmsOperationDuration.add(availResponse.timings.duration);
        checkResponse(availResponse, 'pms_availability');

        // Get room types
        const roomsResponse = http.get(
            `${BASE_URL}/api/v1/pms/room-types`,
            {
                tags: { name: 'pms_room_types' }
            }
        );
        pmsOperationDuration.add(roomsResponse.timings.duration);
        checkResponse(roomsResponse, 'pms_room_types');
    });
}

/**
 * Test 4: Reservation Flow
 */
function testReservationFlow() {
    group('Reservation Flow', () => {
        const dates = getRandomDates();
        const phone = getRandomElement(GUEST_PHONES);
        
        // Create reservation
        const reservationPayload = JSON.stringify({
            guest_phone: phone,
            check_in: dates.check_in,
            check_out: dates.check_out,
            room_type: 'standard',
            guests: 2,
            special_requests: 'Vista al mar si es posible'
        });

        const createResponse = http.post(
            `${BASE_URL}/api/v1/reservations`,
            reservationPayload,
            {
                headers: { 'Content-Type': 'application/json' },
                tags: { name: 'create_reservation' }
            }
        );
        reservationDuration.add(createResponse.timings.duration);
        
        if (checkResponse(createResponse, 'create_reservation', 201)) {
            const reservationData = JSON.parse(createResponse.body);
            const reservationId = reservationData.id || reservationData.reservation_id;
            
            if (reservationId) {
                // Get reservation details
                const getResponse = http.get(
                    `${BASE_URL}/api/v1/reservations/${reservationId}`,
                    {
                        tags: { name: 'get_reservation' }
                    }
                );
                reservationDuration.add(getResponse.timings.duration);
                checkResponse(getResponse, 'get_reservation');
            }
        }
    });
}

/**
 * Test 5: Metrics Endpoint
 */
function testMetricsEndpoint() {
    group('Metrics', () => {
        const response = http.get(`${BASE_URL}/metrics`, {
            tags: { name: 'prometheus_metrics' }
        });
        
        check(response, {
            'metrics: status is 200': (r) => r.status === 200,
            'metrics: has content': (r) => r.body.length > 0,
            'metrics: is text format': (r) => r.headers['Content-Type'].includes('text/plain')
        });
    });
}

/**
 * Test 6: Admin Endpoints (if available)
 */
function testAdminEndpoints() {
    group('Admin Endpoints', () => {
        // List tenants
        const tenantsResponse = http.get(
            `${BASE_URL}/api/v1/admin/tenants`,
            {
                tags: { name: 'admin_tenants' }
            }
        );
        checkResponse(tenantsResponse, 'admin_tenants');

        // Feature flags status
        const flagsResponse = http.get(
            `${BASE_URL}/api/v1/admin/feature-flags`,
            {
                tags: { name: 'admin_feature_flags' }
            }
        );
        checkResponse(flagsResponse, 'admin_feature_flags');
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN TEST EXECUTION
// ═══════════════════════════════════════════════════════════════════════════

export default function() {
    // Update active VUs metric
    activeVUs.add(__VU);

    // Execute test mix based on scenario
    switch(SCENARIO) {
        case 'smoke':
            // Smoke test: Just health checks and basic operations
            testHealthChecks();
            sleep(1);
            break;

        case 'load':
            // Load test: Full flow with realistic mix
            testHealthChecks();
            sleep(0.5);
            
            if (Math.random() < 0.6) {
                testWhatsAppWebhook();
            }
            
            if (Math.random() < 0.4) {
                testPMSOperations();
            }
            
            if (Math.random() < 0.3) {
                testReservationFlow();
            }
            
            if (Math.random() < 0.1) {
                testMetricsEndpoint();
            }
            
            sleep(Math.random() * 2 + 1); // 1-3s think time
            break;

        case 'stress':
            // Stress test: More aggressive, less sleep
            testHealthChecks();
            testWhatsAppWebhook();
            
            if (Math.random() < 0.5) {
                testPMSOperations();
            }
            
            if (Math.random() < 0.4) {
                testReservationFlow();
            }
            
            sleep(Math.random() * 0.5); // 0-0.5s think time
            break;

        case 'spike':
            // Spike test: Rapid fire requests
            testHealthChecks();
            testWhatsAppWebhook();
            testPMSOperations();
            // No sleep - max throughput
            break;

        case 'soak':
            // Soak test: Realistic user behavior over long period
            testHealthChecks();
            sleep(1);
            
            testWhatsAppWebhook();
            sleep(2);
            
            if (Math.random() < 0.3) {
                testPMSOperations();
                sleep(1);
            }
            
            if (Math.random() < 0.2) {
                testReservationFlow();
                sleep(2);
            }
            
            if (Math.random() < 0.05) {
                testAdminEndpoints();
            }
            
            sleep(Math.random() * 5 + 3); // 3-8s think time
            break;

        default:
            console.error(`Unknown scenario: ${SCENARIO}`);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SETUP AND TEARDOWN
// ═══════════════════════════════════════════════════════════════════════════

export function setup() {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('🚀 k6 Performance Testing Suite - Agente Hotelero IA');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`Scenario: ${SCENARIO.toUpperCase()}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Test Started: ${new Date().toISOString()}`);
    console.log('═══════════════════════════════════════════════════════════════');
    
    // Verify API is reachable
    const healthCheck = http.get(`${BASE_URL}/health/live`);
    if (healthCheck.status !== 200) {
        throw new Error(`API not reachable at ${BASE_URL}. Status: ${healthCheck.status}`);
    }
    
    console.log('✅ API health check passed');
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    return {
        startTime: new Date().toISOString(),
        scenario: SCENARIO
    };
}

export function teardown(data) {
    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('🏁 Test Execution Complete');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`Started: ${data.startTime}`);
    console.log(`Ended: ${new Date().toISOString()}`);
    console.log(`Scenario: ${data.scenario.toUpperCase()}`);
    console.log('═══════════════════════════════════════════════════════════════');
}

// ═══════════════════════════════════════════════════════════════════════════
// CUSTOM SUMMARY REPORT
// ═══════════════════════════════════════════════════════════════════════════

export function handleSummary(data) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outputDir = '.performance';
    
    // Calculate custom metrics
    const totalReqs = data.metrics.http_reqs ? data.metrics.http_reqs.values.count : 0;
    const failedReqs = data.metrics.http_req_failed ? data.metrics.http_req_failed.values.passes : 0;
    const errorRatePct = totalReqs > 0 ? (failedReqs / totalReqs * 100).toFixed(2) : 0;
    
    const p95Latency = data.metrics.http_req_duration ? 
        data.metrics.http_req_duration.values['p(95)'].toFixed(2) : 'N/A';
    
    const checksPassRate = data.metrics.checks ? 
        (data.metrics.checks.values.passes / data.metrics.checks.values.count * 100).toFixed(2) : 'N/A';

    // SLO Validation
    const sloStatus = {
        p95_latency: parseFloat(p95Latency) < 3000,
        error_rate: parseFloat(errorRatePct) < 1.0,
        checks_pass: parseFloat(checksPassRate) > 99.0
    };

    const allSLOsPassed = Object.values(sloStatus).every(v => v === true);

    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('📊 SLO VALIDATION RESULTS');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`P95 Latency: ${p95Latency}ms ${sloStatus.p95_latency ? '✅' : '❌'} (target: <3000ms)`);
    console.log(`Error Rate: ${errorRatePct}% ${sloStatus.error_rate ? '✅' : '❌'} (target: <1%)`);
    console.log(`Checks Pass: ${checksPassRate}% ${sloStatus.checks_pass ? '✅' : '❌'} (target: >99%)`);
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`OVERALL: ${allSLOsPassed ? '✅ PASS' : '❌ FAIL'}`);
    console.log('═══════════════════════════════════════════════════════════════\n');

    return {
        [`${outputDir}/results-${SCENARIO}-${timestamp}.json`]: JSON.stringify(data, null, 2),
        [`${outputDir}/summary-${SCENARIO}-${timestamp}.html`]: htmlReport(data),
        stdout: textSummary(data, { indent: ' ', enableColors: true })
    };
}
