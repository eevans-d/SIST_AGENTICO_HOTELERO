#!/usr/bin/env bash
# [PROMPT GA-01] Script de Restauración
set -e

BACKUP_PATH=$1

if [ -z "$BACKUP_PATH" ]; then
    echo "Uso: $0 <ruta_al_backup>"
    exit 1
fi

echo "Restaurando desde ${BACKUP_PATH}..."

# Lógica de restauración aquí

echo "Restauración completada."
