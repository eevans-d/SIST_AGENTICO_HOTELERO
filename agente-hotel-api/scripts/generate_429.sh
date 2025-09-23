#!/usr/bin/env bash
set -euo pipefail

# Genera tráfico concurrente al endpoint /webhooks/whatsapp para provocar 429

HOST=${HOST:-localhost}
PORT=${PORT:-8000}
REQUESTS=${REQUESTS:-60}
DELAY_MS=${DELAY_MS:-50}

URL="http://$HOST:$PORT/webhooks/whatsapp"

echo "Enviando $REQUESTS requests a $URL con delay ${DELAY_MS}ms"

for i in $(seq 1 "$REQUESTS"); do
  (
    # Cuerpo mínimo válido para el webhook; ajustar si hay validación estricta
    curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL" \
      -H 'Content-Type: application/json' \
      -d '{"entry": [{"changes": [{"value": {"messages": [{"from": "123", "id": "abc", "timestamp": "0", "type": "text", "text": {"body": "ping"}}]}}]}]}' \
      || true
    sleep $(awk "BEGIN {print $DELAY_MS/1000}")
  ) &
done

wait || true
echo "Listo. Revisa Prometheus/Alertas."
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
