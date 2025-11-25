#!/usr/bin/env bash
set -euo pipefail

# Security scan aggregator: dependencies (pip/poetry), filesystem (IaC), docker image (if built)
# Requires: trivy (https://aquasecurity.github.io/trivy), optional: pip-audit

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/audit_results"
mkdir -p "$REPORT_DIR"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'

info(){ echo -e "${YELLOW}[INFO]${NC} $*"; }
ok(){ echo -e "${GREEN}[OK]${NC} $*"; }
err(){ echo -e "${RED}[ERR]${NC} $*"; }

if ! command -v trivy >/dev/null 2>&1; then
  err "trivy no instalado. Instalar: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
  exit 1
fi

# 1. Dependency scan (Python)
info "Escaneando dependencias Python (poetry lock / requirements)"
TRIVY_DEPS_REPORT="$REPORT_DIR/trivy-deps-$TIMESTAMP.json"
trivy fs --security-checks vuln --dependency-tree --format json --output "$TRIVY_DEPS_REPORT" "$PROJECT_ROOT" || true
ok "Reporte dependencias: $TRIVY_DEPS_REPORT"

# 2. Config / IaC / Secrets (light)
info "Escaneo de secretos y configuración ligera"
TRIVY_CONFIG_REPORT="$REPORT_DIR/trivy-config-$TIMESTAMP.json"
trivy fs --security-checks config,secret --format json --output "$TRIVY_CONFIG_REPORT" "$PROJECT_ROOT" || true
ok "Reporte config/secrets: $TRIVY_CONFIG_REPORT"

# 3. Docker image scan (if image exists locally)
IMAGE_TAG=${IMAGE_TAG:-agente-hotel-api:latest}
if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  info "Escaneando imagen Docker $IMAGE_TAG"
  TRIVY_IMAGE_REPORT="$REPORT_DIR/trivy-image-$TIMESTAMP.json"
  trivy image --format json --output "$TRIVY_IMAGE_REPORT" "$IMAGE_TAG" || true
  ok "Reporte imagen: $TRIVY_IMAGE_REPORT"
else
  info "Imagen $IMAGE_TAG no encontrada localmente; omitiendo escaneo de imagen (build primero si lo deseas)."
fi

# 4. pip-audit (opcional)
if command -v pip-audit >/dev/null 2>&1; then
  info "Ejecutando pip-audit"
  PIP_AUDIT_REPORT="$REPORT_DIR/pip-audit-$TIMESTAMP.json"
  pip-audit -f json -o "$PIP_AUDIT_REPORT" || true
  ok "Reporte pip-audit: $PIP_AUDIT_REPORT"
else
  info "pip-audit no instalado (pip install pip-audit) — omitido"
fi

info "Resumen rápido (trivy high/critical):"
trivy fs --severity HIGH,CRITICAL --quiet "$PROJECT_ROOT" | head -n 20 || true

ok "Escaneo de seguridad completado. Revisar JSON en $REPORT_DIR"
