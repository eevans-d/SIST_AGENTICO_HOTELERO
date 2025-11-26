#!/usr/bin/env bash
set -euo pipefail

# Activa una alerta sintética AlwaysFiring en docker/prometheus/alerts-extra.yml
# y reinicia Prometheus para recargar reglas de forma segura.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ROOT_DIR=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)
ALERTS_FILE="$ROOT_DIR/docker/prometheus/alerts-extra.yml"
BACKUP_FILE="$ALERTS_FILE.bak"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

echo "⚙️ Activando alerta sintética (AlwaysFiring) en $ALERTS_FILE"

# Backup previo si no existe aún
if [[ -f "$ALERTS_FILE" && ! -f "$BACKUP_FILE" ]]; then
  cp "$ALERTS_FILE" "$BACKUP_FILE"
  echo "🗄️  Backup creado: $BACKUP_FILE"
fi

cat > "$ALERTS_FILE" <<'YAML'
groups:
  - name: agente-test
    interval: 15s
    rules:
      - alert: AlwaysFiring
        expr: vector(1)
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Alerta de prueba (AlwaysFiring)"
          description: "Alerta sintética para validar receivers y ruteo."
YAML

echo "✅ Archivo actualizado. Reiniciando Prometheus para recargar reglas..."

docker compose -f "$COMPOSE_FILE" restart prometheus >/dev/null

echo "✅ Listo. Verifica en Grafana/Alertmanager que la alerta esté FIREING tras ~1m."
