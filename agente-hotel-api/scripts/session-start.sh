#!/usr/bin/env bash
set -euo pipefail

echo "== Session Start =="
echo "Fecha: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Branch actual: $BRANCH"
echo "Últimos commits:"; git --no-pager log --oneline -5

STATUS_FILE="agente-hotel-api/docs/STATUS_SNAPSHOT.md"
if [ -f "$STATUS_FILE" ]; then
  echo "Resumen previo:"; grep '^## Top' -A5 "$STATUS_FILE" || true
fi

ISSUES_EXPORT="agente-hotel-api/PHASE5_ISSUES_EXPORT.md"
if [ -f "$ISSUES_EXPORT" ]; then
  echo "Top Issues (Phase5 export):"
  # Extraer primeras 5 filas de la tabla (ignorando encabezado)
  grep '^| ' "$ISSUES_EXPORT" | tail -n +3 | head -5 | cut -c1-160
fi

echo "DoD location: docs/DOD_CHECKLIST.md"
echo "Working Agreement: docs/playbook/WORKING_AGREEMENT.md"
echo "Playbook Gobernanza: docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md"
echo "Project config: .playbook/project_config.yml"
echo "== End Session Bootstrap =="
