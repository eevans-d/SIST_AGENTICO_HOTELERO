#!/bin/sh
# Simple health pinger to keep readiness metrics fresh
# Env vars:
#   HEALTH_URL (default: http://agente-api:8000/health/ready)
#   INTERVAL (default: 30 seconds)

HEALTH_URL="${HEALTH_URL:-http://agente-api:8000/health/ready}"
INTERVAL="${INTERVAL:-30}"

echo "[health-pinger] Starting. URL=${HEALTH_URL} interval=${INTERVAL}s"
while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  # BusyBox wget is available in busybox:latest
  wget -q -O - "$HEALTH_URL" >/dev/null 2>&1 && STATUS="ok" || STATUS="fail"
  echo "[health-pinger] $TS ping -> $STATUS"
  sleep "$INTERVAL"
done
