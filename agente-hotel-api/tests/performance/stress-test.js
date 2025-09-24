import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics for stress testing
export let criticalErrors = new Rate('critical_errors');
export let recoveryTime = new Trend('recovery_time');

export let options = {
  stages: [
    { duration: '1m', target: 10 },    // Baseline
    { duration: '2m', target: 100 },   // Stress
    { duration: '2m', target: 300 },   // Breaking point
    { duration: '2m', target: 500 },   // Extreme stress
    { duration: '1m', target: 100 },   // Recovery test
    { duration: '1m', target: 0 },     // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(99)<5000'], // 99% under 5s (more lenient for stress)  
    http_req_failed: ['rate<0.1'],     // Allow up to 10% errors in stress test
    critical_errors: ['rate<0.02'],    // Critical errors must stay under 2%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function() {
  const endpoints = [
    '/health/live',
    '/health/ready', 
    '/metrics',
  ];
  
  const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
  const startTime = Date.now();
  
  const response = http.get(`${BASE_URL}${endpoint}`, {
    timeout: '10s', // Longer timeout for stress conditions
  });
  
  const endTime = Date.now();
  const responseTime = endTime - startTime;
  
  // Check for critical failures (5xx errors or timeouts)
  const isCriticalError = response.status >= 500 || response.status === 0;
  if (isCriticalError) {
    criticalErrors.add(1);
  }
  
  // Check response quality
  check(response, {
    'status is not 5xx': (r) => r.status < 500,
    'response time acceptable under stress': (r) => r.timings.duration < 10000,
    'no timeout occurred': (r) => r.status !== 0,
  });
  
  // Test recovery after errors
  if (response.status >= 400) {
    sleep(0.1); // Brief pause
    const recoveryStart = Date.now();
    const retryResponse = http.get(`${BASE_URL}/health/live`);
    if (retryResponse.status === 200) {
      recoveryTime.add(Date.now() - recoveryStart);
    }
  }
  
  // Variable sleep based on current load
  const currentVUs = __VU || 1;
  const sleepTime = Math.max(0.1, 1 - (currentVUs / 1000)); // Less sleep with more VUs
  sleep(sleepTime);
}

export function setup() {
  console.log(`Starting stress test against ${BASE_URL}`);
  console.log('Warning: This test will push the system to its limits');
  
  // Verify system is healthy before stress test
  const healthCheck = http.get(`${BASE_URL}/health/live`);
  if (healthCheck.status !== 200) {
    throw new Error(`System not healthy before stress test: ${healthCheck.status}`);
  }
}

export function teardown(data) {
  console.log('Stress test completed - allow system to recover');
  
  // Post-test health verification
  sleep(5); // Allow brief recovery
  const postHealthCheck = http.get(`${BASE_URL}/health/live`);
  if (postHealthCheck.status === 200) {
    console.log('✅ System recovered successfully after stress test');
  } else {
    console.log('⚠️ System may need manual intervention for recovery');
  }
}