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
AUTO_CREATE_LABELS=${AUTO_CREATE_LABELS:-1}

# Parseo de argumentos estilo KEY=VALUE para comodidad (ej: bash script DRY_RUN=1 LABELS_EXTRA="priority")
for arg in "$@"; do
  case $arg in
    DRY_RUN=*) DRY_RUN="${arg#*=}" ;;
    LABELS_EXTRA=*) LABELS_EXTRA="${arg#*=}" ;;
    REPO_SLUG=*) REPO_SLUG="${arg#*=}" ;;
    AUTO_CREATE_LABELS=*) AUTO_CREATE_LABELS="${arg#*=}" ;;
  esac
done

REQUIRED_LABELS=(
  phase5 enhancement performance reliability multi-tenant nlp observability admin ci grafana tracing feature-flags documentation
)

function ensure_labels() {
  if [[ "$AUTO_CREATE_LABELS" -ne 1 ]]; then
    echo "(Skip) Creación automática de labels desactivada"; return 0; fi
  echo "Verificando labels requeridos..."
  local existing
  if ! existing=$(gh label list --repo "$REPO_SLUG" --limit 200 2>/dev/null | awk '{print $1}'); then
    echo "⚠ No se pudieron listar labels (¿autenticación gh?)"; return 1
  fi
  for lbl in "${REQUIRED_LABELS[@]}"; do
    if echo "$existing" | grep -qx "$lbl"; then
      continue
    fi
    local color=""; local desc="Label auto creado (fase5)";
    case "$lbl" in
      phase5) color=5319e7 ;;
      performance) color=1d76db ;;
      reliability) color=fbca04 ;;
      multi-tenant) color=0e8a16 ;;
      nlp) color=c2e0c6 ;;
      observability) color=0052cc ;;
      admin) color=bfdadc ;;
      ci) color=ededed ;;
      grafana) color=ffc1cc ;;
      tracing) color=5319e7 ;;
      feature-flags) color=2b3137 ;;
      documentation) color=0075ca ;;
      enhancement) color=a2eeef ;;
      *) color=ededed ;;
    esac
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "DRY_RUN: gh label create $lbl --color $color --description '$desc'"
    else
      if gh label create "$lbl" --repo "$REPO_SLUG" --color "$color" --description "$desc" >/dev/null 2>&1; then
        echo "✔ Label creado: $lbl"
      else
        echo "⚠ Fallo creando label: $lbl"
      fi
    fi
  done
}

function create_issue() {
  local title="$1"; shift
  local body="$1"; shift
  local labels="$1"; shift
  # Construir lista de flags --label
  IFS=',' read -ra LARR <<<"$labels"
  local cmd=(gh issue create --repo "$REPO_SLUG" --title "$title" --body "$body")
  for l in "${LARR[@]}"; do
    [[ -z "$l" ]] && continue
    # trim whitespace
    l_clean=$(echo "$l" | xargs)
    [[ -z "$l_clean" ]] && continue
    cmd+=(--label "$l_clean")
  done
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY_RUN: ${cmd[*]}"
  else
    echo "Creando: $title"
    if "${cmd[@]}" >/dev/null 2>&1; then
      echo "✔ Issue creado"
    else
      echo "⚠ Fallo creando issue: $title"
    fi
  fi
}

echo "== Creación de issues Fase 5 (Repo: $REPO_SLUG) =="
ensure_labels || echo "Continuando aunque hubo errores al asegurar labels"

# Detectar estado de autenticación gh
if ! gh auth status >/dev/null 2>&1; then
  echo "⚠ gh no autenticado: modo OFFLINE (export a Markdown)."
  OFFLINE=1
else
  OFFLINE=0
fi
EXPORT_MD_FILE=${EXPORT_MD_FILE:-"PHASE5_ISSUES_EXPORT.md"}
if [[ $OFFLINE -eq 1 ]]; then
  echo "Generando export Markdown: $EXPORT_MD_FILE"
  {
    echo "# Phase 5 Issues (Export Offline)"
    echo "Generado: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "| Title | Labels | Body |"
    echo "|-------|--------|------|"
  } > "$EXPORT_MD_FILE"
  # Redefinir create_issue para modo offline
  function create_issue() {
    local title="$1"; shift
    local body="$1"; shift
    local labels="$1"; shift
    safe_body=$(echo "$body" | tr '|' ' ' | sed 's/$/<br>/')
    echo "| $title | $labels | $safe_body |" >> "$EXPORT_MD_FILE"
    echo "OFFLINE: agregado '$title'"
  }
else
  # Re-definir create_issue normal (manteniendo versión previa) solo si no offline
  function create_issue() {
    local title="$1"; shift
    local body="$1"; shift
    local labels="$1"; shift
    IFS=',' read -ra LARR <<<"$labels"
    local cmd=(gh issue create --repo "$REPO_SLUG" --title "$title" --body "$body")
    for l in "${LARR[@]}"; do
      [[ -z "$l" ]] && continue
      l_clean=$(echo "$l" | xargs)
      [[ -z "$l_clean" ]] && continue
      cmd+=(--label "$l_clean")
    done
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "DRY_RUN: ${cmd[*]}"
    else
      echo "Creando: $title"
      if "${cmd[@]}" >/dev/null 2>&1; then
        echo "✔ Issue creado"
      else
        echo "⚠ Fallo creando issue: $title"
      fi
    fi
  }
fi

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
if [[ $OFFLINE -eq 1 ]]; then
  echo "Archivo export generado: $EXPORT_MD_FILE"
fi
