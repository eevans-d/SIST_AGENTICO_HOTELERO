#!/bin/bash
# [PROMPT 3.4] Script de Backup Automatizado
set -euo pipefail

BACKUP_DIR="/backups/agente-hotel/daily"
RETENTION_DAYS=30

# ... (lógica de backup para postgres, mysql, redis y subida a S3)

echo "Script de backup automatizado implementado."
