#!/bin/bash
# Backup/Restore Script for Agente Hotelero Postgres on Fly.io
# Usage:
#   ./backup-restore.sh backup  [file_prefix]  - Create backup
#   ./backup-restore.sh restore [backup_file]  - Restore from backup
#   ./backup-restore.sh list                   - List available backups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUPS_DIR="${SCRIPT_DIR}/../backups"
APP_NAME="agente-hotel-api"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUPS_DIR}/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure backups directory exists
mkdir -p "${BACKUPS_DIR}"

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "${LOG_FILE}"
}

# Function to get Postgres connection string from Fly
get_postgres_url() {
    # Try to get DATABASE_URL from Fly secrets
    local db_url
    
    # If we're running on Fly machines, get from app config
    if command -v flyctl &> /dev/null; then
        db_url=$(flyctl secrets list -a "${APP_NAME}" 2>/dev/null | grep DATABASE_URL | awk '{print $2}' || echo "")
    fi
    
    # Fallback to environment variable
    if [ -z "$db_url" ]; then
        db_url="${DATABASE_URL}"
    fi
    
    if [ -z "$db_url" ]; then
        log_error "DATABASE_URL not found. Set it in Fly secrets or environment."
        return 1
    fi
    
    echo "$db_url"
}

# Parse PostgreSQL URL to components
parse_db_url() {
    local url="$1"
    # Extract components from postgresql+asyncpg://user:password@host:port/db
    # postgres regex: ^postgresql\+asyncpg:\/\/([^:]+):(.+)@([^:]+):([^/]+)\/(.+)$
    
    if [[ $url =~ ^postgresql\+asyncpg://([^:]+):(.+)@([^:]+):([^/]+)/(.+)$ ]]; then
        PGUSER="${BASH_REMATCH[1]}"
        PGPASSWORD="${BASH_REMATCH[2]}"
        PGHOST="${BASH_REMATCH[3]}"
        PGPORT="${BASH_REMATCH[4]}"
        PGDATABASE="${BASH_REMATCH[5]}"
        return 0
    else
        log_error "Invalid PostgreSQL URL format: $url"
        return 1
    fi
}

# Backup function
backup() {
    local prefix="${1:-agente-hotel-api}"
    local backup_file="${BACKUPS_DIR}/${prefix}_${TIMESTAMP}.sql.gz"
    
    log "Starting backup of ${APP_NAME} database..."
    
    local db_url
    db_url=$(get_postgres_url) || exit 1
    
    if ! parse_db_url "$db_url"; then
        exit 1
    fi
    
    log "Database: $PGDATABASE @ $PGHOST:$PGPORT"
    
    # Create backup using pg_dump
    log "Dumping database to $backup_file..."
    export PGPASSWORD
    
    if pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        --no-password \
        --verbose \
        2>>"${LOG_FILE}" | gzip > "$backup_file"; then
        log_success "Backup created: $backup_file"
        ls -lh "$backup_file" | tee -a "${LOG_FILE}"
        unset PGPASSWORD
        return 0
    else
        log_error "Backup failed"
        unset PGPASSWORD
        return 1
    fi
}

# Restore function
restore() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "No backup file specified"
        echo "Usage: $0 restore <backup_file>"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Starting restore from $backup_file..."
    
    local db_url
    db_url=$(get_postgres_url) || exit 1
    
    if ! parse_db_url "$db_url"; then
        exit 1
    fi
    
    log "Target database: $PGDATABASE @ $PGHOST:$PGPORT"
    log "WARNING: This will DROP and recreate the database. Press Ctrl+C to cancel."
    sleep 5
    
    export PGPASSWORD
    
    # Drop existing database if it exists
    log "Dropping existing database (if exists)..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" --no-password \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PGDATABASE' AND pid <> pg_backend_pid();" \
        2>>"${LOG_FILE}" || true
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" --no-password \
        -c "DROP DATABASE IF EXISTS $PGDATABASE;" \
        2>>"${LOG_FILE}" || true
    
    # Create fresh database
    log "Creating fresh database..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" --no-password \
        -c "CREATE DATABASE $PGDATABASE;" \
        2>>"${LOG_FILE}" || {
        log_error "Failed to create database"
        unset PGPASSWORD
        return 1
    }
    
    # Restore from backup
    log "Restoring from backup..."
    if gunzip -c "$backup_file" | psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
        -d "$PGDATABASE" --no-password --verbose 2>>"${LOG_FILE}"; then
        log_success "Database restored from: $backup_file"
        unset PGPASSWORD
        return 0
    else
        log_error "Restore failed"
        unset PGPASSWORD
        return 1
    fi
}

# List backups
list_backups() {
    log "Available backups:"
    ls -lh "${BACKUPS_DIR}"/*.sql.gz 2>/dev/null || {
        log "No backups found in ${BACKUPS_DIR}"
        return 1
    }
}

# Cleanup old backups (keep only last 7 days)
cleanup_old_backups() {
    local days_to_keep="${1:-7}"
    log "Cleaning up backups older than $days_to_keep days..."
    
    find "${BACKUPS_DIR}" -name "*.sql.gz" -mtime +"$days_to_keep" -delete
    log_success "Cleanup completed"
}

# Main logic
case "${1:-}" in
    backup)
        backup "${2:-agente-hotel-api}" || exit 1
        cleanup_old_backups 7
        ;;
    restore)
        restore "$2" || exit 1
        ;;
    list)
        list_backups || exit 1
        ;;
    cleanup)
        cleanup_old_backups "${2:-7}" || exit 1
        ;;
    *)
        echo "Agente Hotelero Database Backup/Restore Utility"
        echo ""
        echo "Usage:"
        echo "  $0 backup  [prefix]        - Create backup (default prefix: agente-hotel-api)"
        echo "  $0 restore <backup_file>   - Restore database from backup"
        echo "  $0 list                    - List available backups"
        echo "  $0 cleanup [days]          - Remove backups older than N days (default: 7)"
        echo ""
        echo "Examples:"
        echo "  $0 backup"
        echo "  $0 restore backups/agente-hotel-api_20251025_120000.sql.gz"
        echo "  $0 cleanup 30"
        exit 1
        ;;
esac
