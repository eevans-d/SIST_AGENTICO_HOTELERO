#!/usr/bin/env bash
set -euo pipefail

# Script: create-phase5-issues.sh
# Requisitos: GitHub CLI (gh) autenticado con scope repo.
# Uso:
#   bash scripts/create-phase5-issues.sh
# Variables opcionales:
#   DRY_RUN=1   => solo imprime comandos
#   LABELS_EXTRA="team-core" => etiquetas adicionales

REPO_SLUG=${REPO_SLUG:-"eevans-d/SIST_AGENTICO_HOTELERO"}
LABELS_BASE="phase5,enhancement"
LABELS_EXTRA=${LABELS_EXTRA:-""}
DRY_RUN=${DRY_RUN:-0}

function create_issue() {
  local title="$1"; shift
  local body="$1"; shift
  local labels="$1"; shift
  local cmd=(gh issue create --repo "$REPO_SLUG" --title "$title" --body "$body" --label "$labels")
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY_RUN: ${cmd[*]}"
  else
    echo "Creando: $title"
    "${cmd[@]}" >/dev/null && echo "✔" || echo "⚠ Fallo creando issue: $title"
  fi
}

echo "== Creación de issues Fase 5 (Repo: $REPO_SLUG) =="

create_issue \
  "chore(canary): tráfico sintético y comparación baseline vs canary" \
  "Generar tráfico controlado (k6) antes y durante canary; comparar p95 y error rate.\nCriterios:\n- Baseline previo\n- Reporte delta JSON\n- Falla si p95_canary > p95_base *1.10 o error_rate_canary > error_rate_base *1.5 (mínimos absolutos)." \
  "$LABELS_BASE,performance,reliability,$LABELS_EXTRA"

create_issue \
  "feat(tenant): mapping dinámico persistente" \
  "Reemplazar mapa en memoria por tabla 'tenants'. Cache Redis 60s. Match por patrón. Tests de aislamiento." \
  "$LABELS_BASE,multi-tenant,$LABELS_EXTRA"

create_issue \
  "reliability(gating): thresholds adaptativos (error budget)" \
  "Ajustar umbral P95 smoke según error budget restante (Prometheus). <80% => 420ms, <60% => 400ms." \
  "$LABELS_BASE,reliability,performance,$LABELS_EXTRA"

create_issue \
  "feat(nlp): métrica fallback low confidence" \
  "Exponer counter/fallback y recording rule ratio 5m. Panel en dashboard." \
  "$LABELS_BASE,nlp,observability,$LABELS_EXTRA"

create_issue \
  "feat(admin): endpoint listado feature flags" \
  "GET /admin/feature-flags => [{'flag','value','source'}]. Protegido por auth. Tests." \
  "$LABELS_BASE,admin,$LABELS_EXTRA"

create_issue \
  "perf(smoke): publicar artifact y summary en CI" \
  "Subir smoke-summary.json como artifact + job summary p95/error_rate. Tabla histórica futura." \
  "$LABELS_BASE,performance,ci,$LABELS_EXTRA"

create_issue \
  "observability(canary): panel comparativo baseline vs canary" \
  "Dashboard con series p95, error rate y delta porcentual. Añadir alertas suaves si delta>10%." \
  "$LABELS_BASE,observability,grafana,$LABELS_EXTRA"

create_issue \
  "feat(tracing): esqueleto OpenTelemetry" \
  "Añadir dependencias OTel, tracer básico (fastapi middleware), export a stdout. Sampling 1%." \
  "$LABELS_BASE,observability,tracing,$LABELS_EXTRA"

create_issue \
  "feat(flags): invalidación push cache local" \
  "Canal Redis pub/sub 'feature_flags_events' para invalidar cache local en FeatureFlagService." \
  "$LABELS_BASE,feature-flags,$LABELS_EXTRA"

create_issue \
  "docs(tenant): guía multi-tenant avanzada" \
  "Documentar segmentación, aislamiento futuro (DB/schema), patrones de escalado y riesgos." \
  "$LABELS_BASE,documentation,multi-tenant,$LABELS_EXTRA"

echo "== Fin =="
