#!/usr/bin/env bash
set -euo pipefail

###############################################
# Canary Deploy Script (Esqueleto Fase 5)
# Objetivo: realizar despliegue progresivo validando métricas.
# Estado: placeholder inicial.
###############################################

ENV="${1:-staging}"
VERSION="${2:-local}" # commit hash sugerido

echo "[canary] Iniciando canary para env=$ENV version=$VERSION (placeholder)"
echo "[canary] Pasos previstos:"
echo " 1. Construir imagen si no existe"
echo " 2. Desplegar subconjunto (1 réplica)"
echo " 3. Validar /health/ready"
echo " 4. Consultar métricas (latencia P95, error rate)"
echo " 5. Promover a producción completa"
echo "(Implementación completa pendiente)"

exit 0
