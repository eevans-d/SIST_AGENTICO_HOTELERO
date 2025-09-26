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

step "Recolectar métricas baseline (latencia P95 simulada)"
P95_QUERY='histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[5m])) by (le))'
if ! $DRY_RUN; then
	BASELINE_P95=$(curl -s "http://localhost:9090/api/v1/query?query=${P95_QUERY}" | jq -r '.data.result[0].value[1] // 0')
else
	BASELINE_P95=0.25
fi
echo "Baseline P95=${BASELINE_P95}s"

step "Validar error rate (placeholder)"
if ! $DRY_RUN; then
	ERROR_RATE=0
else
	ERROR_RATE=0
fi
echo "ErrorRate=${ERROR_RATE}"

step "Evaluar criterios promoción"
PROMOTE=true
if (( $(echo "$BASELINE_P95 > 1.2" | bc -l) )); then
	echo "⚠ Latencia P95 alta: $BASELINE_P95"; PROMOTE=false
fi
if (( $(echo "$ERROR_RATE > 0.02" | bc -l) )); then
	echo "⚠ Error rate alto: $ERROR_RATE"; PROMOTE=false
fi

if $PROMOTE; then
	echo "✅ Criterios OK. (Promoción real pendiente de implementación pipeline)"
else
	echo "❌ Criterios no cumplen. Abortando canary."
	exit 2
fi

echo "[canary] Finalizado"

