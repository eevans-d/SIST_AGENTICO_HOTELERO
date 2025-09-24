#!/bin/sh
set -eu

TEMPLATE="/etc/prometheus/recording_rules.tmpl.yml"
OUTDIR="/etc/prometheus/generated"
OUTFILE="$OUTDIR/recording_rules.yml"

mkdir -p "$OUTDIR"

SLO_TARGET=${SLO_TARGET:-99.0}
SLO_TRAFFIC_FLOOR=${SLO_TRAFFIC_FLOOR:-0.5}
# Error budget fraction = 1 - (SLO_TARGET/100)
if [ -n "${ERROR_BUDGET_FRACTION:-}" ]; then
  BUDGET_FRACTION="$ERROR_BUDGET_FRACTION"
else
  if command -v awk >/dev/null 2>&1; then
    BUDGET_FRACTION=$(awk -v slo="$SLO_TARGET" 'BEGIN { printf("%.6f", (100.0 - slo)/100.0) }')
  else
    # Fallback a 1% si no hay awk
    BUDGET_FRACTION="0.010000"
  fi
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "Template $TEMPLATE no encontrado" >&2
  exit 1
fi

# Sustituir placeholders BUDGET_FRACTION y SLO_TARGET_VALUE en la plantilla
sed "s/BUDGET_FRACTION/${BUDGET_FRACTION}/g; s/SLO_TARGET_VALUE/${SLO_TARGET}/g; s/TRAFFIC_FLOOR_VALUE/${SLO_TRAFFIC_FLOOR}/g" "$TEMPLATE" > "$OUTFILE"

echo "Usando SLO_TARGET=${SLO_TARGET} (traffic floor=${SLO_TRAFFIC_FLOOR} rps) => ERROR_BUDGET_FRACTION=${BUDGET_FRACTION}" >&2
echo "Recording rules generadas en $OUTFILE:" >&2
sed -n '1,160p' "$OUTFILE" >&2

# Ejecutar Prometheus con los mismos argumentos
exec /bin/prometheus "$@"
