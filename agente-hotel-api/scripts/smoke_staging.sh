#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost:8002"}

echo "[SMOKE] Health live..."
curl -sf "${BASE_URL}/health/live" >/dev/null && echo "OK" || { echo "FAIL"; exit 1; }

echo "[SMOKE] Health ready..."
curl -sf "${BASE_URL}/health/ready" >/dev/null && echo "OK" || { echo "FAIL"; exit 1; }

echo "[SMOKE] Metrics endpoint..."
curl -sf "${BASE_URL}/metrics" | grep -E "jwt_sessions_active|db_connections_active|password_rotations_total" >/dev/null && echo "OK" || { echo "FAIL"; exit 1; }

echo "[SMOKE] Done."
