#!/usr/bin/env bash
set -euo pipefail

OUT="agente-hotel-api/docs/STATUS_SNAPSHOT.md"
echo "# Status Snapshot" > "$OUT"
echo "Generado: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT"
echo >> "$OUT"

echo "## Últimos Commits" >> "$OUT"
git --no-pager log --oneline -10 >> "$OUT"

echo >> "$OUT"
echo "## Top Issues (Phase 5 Export)" >> "$OUT"
if [ -f agente-hotel-api/PHASE5_ISSUES_EXPORT.md ]; then
  grep '^| ' agente-hotel-api/PHASE5_ISSUES_EXPORT.md | head -12 >> "$OUT" || true
else
  echo "(No PHASE5_ISSUES_EXPORT.md disponible)" >> "$OUT"
fi

echo >> "$OUT"
echo "## Artefactos Clave" >> "$OUT"
echo "- DoD: docs/DOD_CHECKLIST.md" >> "$OUT"
echo "- Working Agreement: docs/playbook/WORKING_AGREEMENT.md" >> "$OUT"
echo "- Playbook Gobernanza: docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md" >> "$OUT"
echo "- Project Config: .playbook/project_config.yml" >> "$OUT"
echo "- Decision Records: docs/DEC-*" >> "$OUT"

echo >> "$OUT"
echo "## Próximas Prioridades Sugeridas" >> "$OUT"
echo "1. Canary diff métrico (baseline vs canary)" >> "$OUT"
echo "2. Mapping dinámico tenants" >> "$OUT"
echo "3. Métrica fallback ratio + panel NLP" >> "$OUT"
echo "4. Endpoint admin feature flags" >> "$OUT"
echo "5. Thresholds adaptativos (error budget)" >> "$OUT"

echo "Snapshot escrito en $OUT"
