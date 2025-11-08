#!/usr/bin/env bash
set -euo pipefail

# Renders docker/alertmanager/config.yml from config.tmpl.yml using envsubst

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TEMPLATE="$ROOT_DIR/docker/alertmanager/config.tmpl.yml"
OUTPUT="$ROOT_DIR/docker/alertmanager/config.yml"

if ! command -v envsubst >/dev/null 2>&1; then
  echo "Error: envsubst not found. Install gettext-base (Linux) or use 'brew install gettext' (macOS)." >&2
  exit 1
fi

echo "Rendering Alertmanager config from template..."
envsubst < "$TEMPLATE" > "$OUTPUT"
echo "✅ Wrote: $OUTPUT"
