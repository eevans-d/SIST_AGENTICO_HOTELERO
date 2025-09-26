import http from 'k6/http';
import { Trend, Rate } from 'k6/metrics';
import { check, sleep } from 'k6';

export const latencyP95 = new Trend('smoke_latency_p95');
export const errorRate = new Rate('smoke_error_rate');

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-arrival-rate',
      rate: __ENV.K6_RPS ? parseInt(__ENV.K6_RPS) : 40,
      timeUnit: '1s',
      duration: __ENV.K6_DURATION || '60s',
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    smoke_error_rate: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/health/live`);
  const ok = check(res, { 'status is 200': (r) => r.status === 200 });
  if (!ok) {
    errorRate.add(1);
  }
  sleep(0.2);
}
