#!/usr/bin/env bash
set -euo pipefail

SUMMARY_FILE="reports/performance/smoke-summary.json"
P95_LIMIT_MS=${P95_LIMIT_MS:-450}
ERR_LIMIT=${ERR_LIMIT:-0.01}

if [ ! -f "$SUMMARY_FILE" ]; then
  echo "❌ Summary no encontrado: $SUMMARY_FILE"; exit 1
fi

P95=$(jq -r '.p95_ms' "$SUMMARY_FILE")
ERR=$(jq -r '.error_rate' "$SUMMARY_FILE")

echo "➡ P95: ${P95} ms (límite ${P95_LIMIT_MS} ms)"
echo "➡ Error Rate: ${ERR} (límite ${ERR_LIMIT})"

FAIL=0
awk -v a="$P95" -v b="$P95_LIMIT_MS" 'BEGIN{ if (a > b) exit 1 }' || { echo "⚠ P95 excede límite"; FAIL=1; }
awk -v a="$ERR" -v b="$ERR_LIMIT" 'BEGIN{ if (a > b) exit 1 }' || { echo "⚠ Error rate excede límite"; FAIL=1; }

if [ $FAIL -ne 0 ]; then
  echo "❌ Smoke test gating falló"; exit 2
fi
echo "✅ Smoke test dentro de límites"
