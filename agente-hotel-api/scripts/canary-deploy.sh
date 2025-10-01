#!/usr/bin/env bash
set -euo pipefail

###############################################
# Canary Deploy Script (fase 5 - versión inicial funcional)
# Requisitos:
#  - Docker compose local simulando entornos (usa mismo stack con bandera CANARY=1)
#  - Prometheus accesible en localhost:9090
# Uso:
#  bash scripts/canary-deploy.sh staging <commit>
# Flags:
#  --dry-run (no despliega, solo imprime pasos)
###############################################

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
	DRY_RUN=true
	shift || true
fi

ENV="${1:-staging}"
VERSION="${2:-local}" # commit hash sugerido

# Parámetros (override via env):
PROM_URL="${PROM_URL:-http://localhost:9090}"    # URL Prometheus
BASELINE_RANGE="${BASELINE_RANGE:-2m}"           # Ventana baseline antes de canary
CANARY_RANGE="${CANARY_RANGE:-2m}"               # Ventana canary tras warmup
WARMUP_SECONDS="${WARMUP_SECONDS:-30}"           # Calentamiento tras readiness
P95_INCREASE_LIMIT="${P95_INCREASE_LIMIT:-1.10}" # Multiplicador máximo permitido
ERR_INCREASE_LIMIT="${ERR_INCREASE_LIMIT:-1.50}" # Multiplicador máximo permitido
ERR_ABS_MIN="${ERR_ABS_MIN:-0.005}"              # Error rate absoluto mínimo gatillo
OUT_JSON="${OUT_JSON:-.playbook/canary_diff_report.json}"

mkdir -p .playbook

echo "[canary] Inicio | env=$ENV version=$VERSION dry_run=$DRY_RUN"

function step() { echo -e "\n➡ $1"; }

if $DRY_RUN; then
	echo "[canary] DRY RUN: no se realizarán cambios reales"
fi

step "Construir imagen (si aplica)"
if ! $DRY_RUN; then
	docker build -t agente-hotel-api:$VERSION . >/dev/null
fi

step "Desplegar instancia canary (1 réplica)"
if ! $DRY_RUN; then
	CANARY_PORT=8010
	docker run -d --rm --name agente-hotel-api-canary -p $CANARY_PORT:8000 -e CANARY=1 agente-hotel-api:$VERSION >/dev/null
	trap 'docker stop agente-hotel-api-canary >/dev/null 2>&1 || true' EXIT
fi

step "Esperar readiness"
if ! $DRY_RUN; then
	ATTEMPTS=0
	until curl -sSf http://localhost:8010/health/ready >/dev/null 2>&1; do
		ATTEMPTS=$((ATTEMPTS+1))
		if [ $ATTEMPTS -gt 15 ]; then
			echo "❌ Canary no ready tras 15 intentos"; exit 1
		fi
		sleep 2
	done
	echo "✅ Ready"
fi

step "Recolectar métricas baseline (P95 y error_rate)"
P95_QUERY_BASELINE="histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[${BASELINE_RANGE}])) by (le))"
ERR_QUERY_BASELINE="(sum(rate(http_requests_total{status_code=~\"5..\"}[${BASELINE_RANGE}])) / sum(rate(http_requests_total[${BASELINE_RANGE}])))"

query_prom() {
	local q="$1"; local url="${PROM_URL}/api/v1/query?query=${q}"
	curl -s --fail "$url" | jq -r '.data.result[0].value[1] // 0' 2>/dev/null || echo 0
}

if ! $DRY_RUN; then
	BASELINE_P95=$(query_prom "$P95_QUERY_BASELINE")
	BASELINE_ERR_RATE=$(query_prom "$ERR_QUERY_BASELINE")
else
	BASELINE_P95=0.250
	BASELINE_ERR_RATE=0.002
fi
echo "Baseline P95=${BASELINE_P95}s | ErrorRate=${BASELINE_ERR_RATE}"

step "Warmup canary ${WARMUP_SECONDS}s y recopilación canary window (${CANARY_RANGE})"
if ! $DRY_RUN; then
	sleep "$WARMUP_SECONDS"
	# Nota: Idealmente aquí gatillaríamos tráfico sintético (TODO: integrar k6 smoke con --vus bajo)
	sleep $(echo "$CANARY_RANGE" | sed 's/m/*60/;s/s//;s/[^0-9*]//g' | bc -l 2>/dev/null || echo 30)
fi

step "Recolectar métricas canary"
P95_QUERY_CANARY="histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[${CANARY_RANGE}])) by (le))"
ERR_QUERY_CANARY="(sum(rate(http_requests_total{status_code=~\"5..\"}[${CANARY_RANGE}])) / sum(rate(http_requests_total[${CANARY_RANGE}])))"
if ! $DRY_RUN; then
	CANARY_P95=$(query_prom "$P95_QUERY_CANARY")
	CANARY_ERR_RATE=$(query_prom "$ERR_QUERY_CANARY")
else
	CANARY_P95=0.265
	CANARY_ERR_RATE=0.0025
fi
echo "Canary P95=${CANARY_P95}s | ErrorRate=${CANARY_ERR_RATE}"

step "Evaluar diffs (p95 x${P95_INCREASE_LIMIT} / err x${ERR_INCREASE_LIMIT} abs_min=${ERR_ABS_MIN})"

fail_reasons=()

P95_LIMIT=$(echo "$BASELINE_P95 * $P95_INCREASE_LIMIT" | bc -l)
if (( $(echo "$CANARY_P95 > $P95_LIMIT" | bc -l) )); then
	fail_reasons+=("p95_delta_exceeded")
fi

ERR_LIMIT_MULTI=$(echo "$BASELINE_ERR_RATE * $ERR_INCREASE_LIMIT" | bc -l)
ERR_LIMIT=$(echo "$ERR_LIMIT_MULTI > $ERR_ABS_MIN" | bc -l)
if (( ERR_LIMIT == 1 )); then
	ERR_THRESH=$ERR_LIMIT_MULTI
else
	ERR_THRESH=$ERR_ABS_MIN
fi
if (( $(echo "$CANARY_ERR_RATE > $ERR_THRESH" | bc -l) )); then
	fail_reasons+=("error_rate_delta_exceeded")
fi

STATUS="PASS"
if ((${#fail_reasons[@]} > 0)); then
	STATUS="FAIL"
fi

step "Generar reporte JSON (${OUT_JSON})"
cat >"$OUT_JSON" <<EOF
{
  "env": "${ENV}",
  "version": "${VERSION}",
  "baseline": {
    "p95": ${BASELINE_P95},
    "error_rate": ${BASELINE_ERR_RATE}
  },
  "canary": {
    "p95": ${CANARY_P95},
    "error_rate": ${CANARY_ERR_RATE}
  },
  "limits": {
    "p95_multiplier": ${P95_INCREASE_LIMIT},
    "error_rate_multiplier": ${ERR_INCREASE_LIMIT},
    "error_rate_abs_min": ${ERR_ABS_MIN}
  },
  "status": "${STATUS}",
  "fail_reasons": ["${fail_reasons[*]}"]
}
EOF
echo "Reporte en $OUT_JSON"

if [[ "$STATUS" == "PASS" ]]; then
	echo "✅ Criterios OK (canary PASS)."
else
	echo "❌ Canary FAIL: ${fail_reasons[*]}"; exit 2
fi

echo "[canary] Finalizado"

