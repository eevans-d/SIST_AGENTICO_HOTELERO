#!/bin/bash
# Backup y Restore procedures para PostgreSQL en Neon
# Uso:
#   ./db-backup-restore.sh backup     # Manual backup
#   ./db-backup-restore.sh restore <timestamp>  # Restore a punto específico

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date -Iseconds)]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Cargar DATABASE_URL
if [[ -z "${DATABASE_URL:-}" ]]; then
    error "DATABASE_URL no está configurada. Ejecuta: export DATABASE_URL='postgresql://...'"
fi

BACKUP_DIR="${BACKUP_DIR:-./.backups}"
mkdir -p "$BACKUP_DIR"

# Funciones

backup_manual() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/backup_manual_$timestamp.sql"
    
    log "Iniciando backup manual..."
    
    # Usar pg_dump a través de psql si es necesario
    # Nota: Requiere que psql esté instalado
    if ! command -v pg_dump &> /dev/null; then
        error "pg_dump no está instalado. Instala: apt-get install postgresql-client"
    fi
    
    PGPASSWORD="${DATABASE_URL##*:}" pg_dump -Fc "${DATABASE_URL%?sslmode=require}" > "$backup_file" 2>/dev/null || \
        error "Error en pg_dump. Verifica DATABASE_URL y conectividad"
    
    local size=$(du -h "$backup_file" | cut -f1)
    log "Backup completado: $backup_file ($size)"
    echo "$backup_file"
}

restore_from_branch() {
    local branch_name="$1"
    
    log "Preparando restauración desde branch: $branch_name"
    warn "OPERACIÓN CRÍTICA: Esta operación afectará la BD en producción"
    warn "¿Continuar? (escribe 'yes' para confirmar)"
    
    read -r confirmation
    if [[ "$confirmation" != "yes" ]]; then
        log "Cancelado por usuario"
        exit 0
    fi
    
    log "Procedimiento:"
    log "1. Ve a https://console.neon.tech/"
    log "2. Selecciona proyecto 'agente-hotel-prod'"
    log "3. Busca branch '$branch_name'"
    log "4. Click 'Promote to main' (o usa CLI)"
    log ""
    log "Alternativamente, via Neon CLI:"
    log "  neon branch promote $branch_name -p agente-hotel-prod"
    log ""
    log "IMPORTANTE: Luego de promote, redeploya la app en tu plataforma de hosting."
}

pitr_restore() {
    local target_timestamp="$1"
    
    log "Restauración Point-in-Time (PITR) a: $target_timestamp"
    warn "Neon mantiene últimas 7 días de PITR automáticamente"
    log ""
    log "Procedimiento:"
    log "1. Ve a https://console.neon.tech/ → Branches"
    log "2. Click 'Create branch' → 'Create from backup'"
    log "3. Selecciona timestamp: $target_timestamp"
    log "4. Nombre branch: 'recovery-$target_timestamp'"
    log "5. Copia nueva CONNECTION STRING (que incluye punto de restore)"
    log "6. Actualiza la variable de entorno DATABASE_URL en tu plataforma de hosting"
    log "7. Valida el endpoint de health"
    log "8. Si OK, promote: neon branch promote recovery-$target_timestamp"
}

# Main

case "${1:-help}" in
    backup)
        backup_manual
        ;;
    restore)
        if [[ -z "${2:-}" ]]; then
            error "Uso: $0 restore <branch_name_or_timestamp>"
        fi
        restore_from_branch "$2"
        ;;
    pitr)
        if [[ -z "${2:-}" ]]; then
            error "Uso: $0 pitr <timestamp> (ej: 2025-10-25T14:30:00Z)"
        fi
        pitr_restore "$2"
        ;;
    list)
        log "Backups locales:"
        ls -lh "$BACKUP_DIR" 2>/dev/null || warn "No hay backups locales"
        ;;
    *)
        cat <<EOF
PostgreSQL Backup & Restore Utility

Uso:
  $0 backup            # Crear backup manual (requiere pg_dump)
  $0 restore <branch>  # Restaurar desde Neon branch
  $0 pitr <timestamp>  # Restauración Point-in-Time
  $0 list              # Listar backups locales
  $0 help              # Esta ayuda

Ejemplos:
  $0 backup
  $0 restore recovery-2025-10-25T14-30-00Z
  $0 pitr 2025-10-25T14:30:00Z

Notas:
- DATABASE_URL debe estar exportada en el ambiente
- Neon mantiene automaticamente 7 días de PITR
- Los backups locales son Backup Formatado (-Fc)

Documentación completa: docs/operations/backup-restore.md
EOF
        ;;
esac
