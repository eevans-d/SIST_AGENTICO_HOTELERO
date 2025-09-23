#!/bin/bash
# Script reproducible para la auditoría no invasiva de Agente Hotel API
set -euo pipefail

# Directorio de salida
OUTPUT_DIR="audit_results"
EVIDENCE_DIR="$OUTPUT_DIR/evidence"
METADATA_FILE="$OUTPUT_DIR/audit-metadata.json"

mkdir -p "$EVIDENCE_DIR"

echo "[+] Fase 0: Descubrimiento Rápido"
{
  echo "## Archivos de Configuración"
  find . -maxdepth 2 -name "pyproject.toml"
  find . -maxdepth 2 -name "*docker-compose*.yml"
  find . -maxdepth 2 -name "Dockerfile*"
  echo "\n## Scripts"
  find ./scripts -name "*.sh"
} > "$EVIDENCE_DIR/f0_discovery.txt"

echo "[+] Fase 1: Análisis Estático"
{
  echo "## Búsqueda de TODO/FIXME"
  grep -r -E "TODO|FIXME" ./app || echo "No TODOs/FIXMEs found."
} > "$EVIDENCE_DIR/f1_static_analysis.txt"

echo "[+] Fase 2: Dependencias (SCA)"
{
  echo "## Generando inventario de dependencias..."
  poetry show > "$EVIDENCE_DIR/f2_dependencies.txt"
  echo "\n## Ejecutando análisis de vulnerabilidades con pip-audit..."
  if ! command -v pip-audit &> /dev/null;
  then
      echo "pip-audit no encontrado, instalando..."
      pip install pip-audit
  fi
  pip-audit > "$EVIDENCE_DIR/f2_vulnerabilities.txt" || echo "pip-audit encontró vulnerabilidades. Ver reporte."
} 

echo "[+] Fase 3: Seguridad y Secretos"
{
  echo "## Búsqueda de patrones de secretos..."
  # Regex mejorada para buscar patrones comunes de claves y tokens
  grep -r -E "(api_key|secret|token|password)['\"\]*[:=]" --exclude-dir={'.git','.venv','__pycache__'} . > "$EVIDENCE_DIR/f3_secrets_scan.txt" || echo "No se encontraron patrones de secretos obvios."
} 

echo "[+] Fase 5: Tests (Intento de ejecución)"
{
  echo "## Intentando ejecutar la suite de tests..."
  if poetry run pytest -q --collect-only > "$EVIDENCE_DIR/f5_test_collection.txt" 2>&1; then
    echo "La recolección de tests fue exitosa."
    # Descomentar para ejecutar tests si el entorno es seguro y está configurado
    # poetry run pytest > "$EVIDENCE_DIR/f5_test_run.txt"
  else
    echo "Falló la recolección de tests. Revisa f5_test_collection.txt" 
  fi
} 

echo "[+] Generando metadata.json..."
# Este es un ejemplo. En un pipeline real, se usaría una herramienta como jq.
cat << EOF > "$METADATA_FILE"
{
  "project": {
    "repo": "local",
    "branch": "main",
    "root": "$(pwd)"
  },
  "analysis_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "findings_summary": "Ver audit-report.md para detalles",
  "artifacts_generated": [
    "$EVIDENCE_DIR/f0_discovery.txt",
    "$EVIDENCE_DIR/f1_static_analysis.txt",
    "$EVIDENCE_DIR/f2_dependencies.txt",
    "$EVIDENCE_DIR/f2_vulnerabilities.txt",
    "$EVIDENCE_DIR/f3_secrets_scan.txt",
    "$EVIDENCE_DIR/f5_test_collection.txt"
  ]
}
EOF

echo "[+] Auditoría completada. Resultados en el directorio: $OUTPUT_DIR"
