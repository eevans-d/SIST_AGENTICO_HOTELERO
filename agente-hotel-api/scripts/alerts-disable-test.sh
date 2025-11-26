#!/usr/bin/env bash
set -euo pipefail

# Desactiva la alerta sintética AlwaysFiring en docker/prometheus/alerts-extra.yml
# restaurando backup si existe, o escribiendo un archivo vacío "groups: []".

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ROOT_DIR=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)
ALERTS_FILE="$ROOT_DIR/docker/prometheus/alerts-extra.yml"
BACKUP_FILE="$ALERTS_FILE.bak"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

echo "⚙️ Desactivando alerta sintética en $ALERTS_FILE"

if [[ -f "$BACKUP_FILE" ]]; then
  cp "$BACKUP_FILE" "$ALERTS_FILE"
  echo "🔁 Restaurado desde backup: $BACKUP_FILE"
else
  echo "groups: []" > "$ALERTS_FILE"
  echo "🧹 Archivo reseteado a configuración vacía (groups: [])."
fi

echo "✅ Reiniciando Prometheus para recargar reglas..."
docker compose -f "$COMPOSE_FILE" restart prometheus >/dev/null

echo "✅ Listo. La alerta sintética dejará de dispararse en ~1m."
