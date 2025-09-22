#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
REQUESTS="${REQUESTS:-80}"
DELAY_MS="${DELAY_MS:-50}"

URL="http://${HOST}:${PORT}/webhooks/whatsapp"

echo "Hitting ${URL} ${REQUESTS} times to provoke 429s (limit 60/min)..."
count_429=0
for i in $(seq 1 "${REQUESTS}"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${URL}") || code="curl_err"
  if [[ "$code" == "429" ]]; then
    ((count_429++)) || true
  fi
  printf "%s " "$code"
  # Small delay to avoid overwhelming terminal; still fast enough to cross 60/min
  sleep "0.$DELAY_MS"
done
echo
echo "Total 429: ${count_429}/${REQUESTS}"

echo "Tip: Alert 'HighWebhook429Rate' may take up to ~5m window to fire (based on rule)."
