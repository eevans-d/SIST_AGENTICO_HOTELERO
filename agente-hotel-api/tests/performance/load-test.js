import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');
export let responseTime = new Trend('response_time');
export let requests = new Counter('requests_total');

// Test configuration
export let options = {
  stages: [
    // Ramp up
    { duration: '30s', target: 10 },   // Warm up
    { duration: '1m', target: 50 },    // Normal load
    { duration: '2m', target: 100 },   // Peak load
    { duration: '1m', target: 200 },   // Stress load
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must be below 2s
    http_req_failed: ['rate<0.05'],    // Error rate must be below 5%
    errors: ['rate<0.05'],             // Custom error rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test scenarios
const scenarios = {
  health_check: {
    url: '/health/live',
    weight: 20,
  },
  readiness_check: {
    url: '/health/ready', 
    weight: 10,
  },
  metrics_endpoint: {
    url: '/metrics',
    weight: 5,
  },
  webhook_get: {
    url: '/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test',
    weight: 15,
  },
  admin_dashboard: {
    url: '/admin/dashboard',
    weight: 10,
    headers: { 'Authorization': 'Bearer test-token' },
  },
};

export default function() {
  // Select random scenario based on weights
  const scenarioKeys = Object.keys(scenarios);
  const totalWeight = Object.values(scenarios).reduce((sum, s) => sum + s.weight, 0);
  const randomWeight = Math.random() * totalWeight;
  
  let cumulativeWeight = 0;
  let selectedScenario = null;
  
  for (const key of scenarioKeys) {
    cumulativeWeight += scenarios[key].weight;
    if (randomWeight <= cumulativeWeight) {
      selectedScenario = scenarios[key];
      break;
    }
  }
  
  // Execute request
  const startTime = Date.now();
  const response = http.get(
    `${BASE_URL}${selectedScenario.url}`,
    { headers: selectedScenario.headers || {} }
  );
  const endTime = Date.now();
  
  // Record metrics
  requests.add(1);
  responseTime.add(endTime - startTime);
  
  // Validate response
  const isSuccess = check(response, {
    'status is 200-299': (r) => r.status >= 200 && r.status < 300,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
    'response has content': (r) => r.body.length > 0,
  });
  
  if (!isSuccess) {
    errorRate.add(1);
  }
  
  // Add realistic user behavior
  sleep(Math.random() * 2 + 0.5); // 0.5-2.5 seconds between requests
}

// Setup function - runs once per VU at the beginning
export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  
  // Warm up the application
  const warmupResponse = http.get(`${BASE_URL}/health/live`);
  if (warmupResponse.status !== 200) {
    console.warn(`Warmup failed: ${warmupResponse.status}`);
  }
  
  return { baseUrl: BASE_URL };
}

// Teardown function - runs once after all VUs finish
export function teardown(data) {
  console.log('Load test completed');
}