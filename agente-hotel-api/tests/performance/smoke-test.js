import http from 'k6/http';
import { Trend, Rate } from 'k6/metrics';
import { check, sleep } from 'k6';

// Métricas custom (k6 ya exporta http_req_duration que usaremos para P95)
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

export function handleSummary(data) {
  // Extraer P95 de duración request global
  const p95 = data.metrics.http_req_duration ? data.metrics.http_req_duration.p(95) : 0;
  const errRate = data.metrics.smoke_error_rate ? data.metrics.smoke_error_rate.rate : 0;
  const summary = { p95_ms: p95, error_rate: errRate, thresholds: { p95_target_ms: 450, error_rate_max: 0.01 } };
  return {
    'reports/performance/smoke-summary.json': JSON.stringify(summary, null, 2),
    stdout: `\nSmoke Summary => p95_ms=${p95.toFixed(2)} error_rate=${errRate}\n`,
  };
}
