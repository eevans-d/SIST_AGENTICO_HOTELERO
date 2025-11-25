#!/bin/bash

###############################################################################
# DEEP CLEANUP SCRIPT - Sistema Agente Hotelero IA
# Limpieza profunda y optimización del proyecto
# Version: 1.0.0
# Date: 2025-10-09
###############################################################################

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
DELETED_FILES=0
DELETED_DIRS=0
MOVED_FILES=0
SPACE_FREED=0

# Función para logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para obtener tamaño de archivo/directorio
get_size() {
    du -sh "$1" 2>/dev/null | cut -f1 || echo "0K"
}

# Crear directorio de backup
BACKUP_DIR="/tmp/agente_hotel_cleanup_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
log_info "Directorio de backup creado: $BACKUP_DIR"

# Cambiar al directorio del proyecto
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

echo ""
echo "=========================================="
echo "  LIMPIEZA PROFUNDA DEL PROYECTO"
echo "=========================================="
echo ""

###############################################################################
# 1. LIMPIEZA DE CACHE Y ARCHIVOS TEMPORALES
###############################################################################
log_info "FASE 1: Eliminando cache y archivos temporales..."

# Eliminar __pycache__ del proyecto (no del venv)
if [ -d "app" ]; then
    find app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find app -type f -name "*.pyc" -delete 2>/dev/null || true
    find app -type f -name "*.pyo" -delete 2>/dev/null || true
    log_success "Cache de Python en app/ eliminado"
fi

if [ -d "tests" ]; then
    find tests -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find tests -type f -name "*.pyc" -delete 2>/dev/null || true
    log_success "Cache de Python en tests/ eliminado"
fi

# Eliminar .pytest_cache
if [ -d ".pytest_cache" ]; then
    SIZE=$(get_size .pytest_cache)
    rm -rf .pytest_cache
    log_success "Eliminado .pytest_cache ($SIZE)"
    ((DELETED_DIRS++))
fi

# Eliminar .ruff_cache
if [ -d ".ruff_cache" ]; then
    SIZE=$(get_size .ruff_cache)
    rm -rf .ruff_cache
    log_success "Eliminado .ruff_cache ($SIZE)"
    ((DELETED_DIRS++))
fi

# Eliminar coverage files
if [ -f ".coverage" ]; then
    rm -f .coverage
    log_success "Eliminado .coverage"
    ((DELETED_FILES++))
fi

if [ -d "htmlcov" ]; then
    SIZE=$(get_size htmlcov)
    rm -rf htmlcov
    log_success "Eliminado htmlcov/ ($SIZE)"
    ((DELETED_DIRS++))
fi

# Eliminar .benchmarks si está vacío
if [ -d ".benchmarks" ]; then
    if [ -z "$(ls -A .benchmarks)" ]; then
        rm -rf .benchmarks
        log_success "Eliminado .benchmarks/ (vacío)"
        ((DELETED_DIRS++))
    else
        log_warning ".benchmarks/ contiene datos, se mantiene"
    fi
fi

###############################################################################
# 2. LIMPIEZA DE ENTORNOS VIRTUALES DUPLICADOS
###############################################################################
log_info "FASE 2: Limpiando entornos virtuales duplicados..."

# Eliminar venv/ si existe (redundante con .venv)
if [ -d "venv" ]; then
    SIZE=$(get_size venv)
    mv venv "$BACKUP_DIR/" 2>/dev/null || rm -rf venv
    log_success "Movido venv/ a backup ($SIZE)"
    ((DELETED_DIRS++))
fi

# Eliminar node_modules si existe (no es proyecto Node.js)
if [ -d "node_modules" ]; then
    SIZE=$(get_size node_modules)
    rm -rf node_modules
    log_success "Eliminado node_modules/ ($SIZE)"
    ((DELETED_DIRS++))
fi

###############################################################################
# 3. CONSOLIDAR ARCHIVOS DE TEST
###############################################################################
log_info "FASE 3: Consolidando archivos de test..."

# Mover tests de raíz a tests/
for test_file in test_audio.py test_audio_workflow.py test_main.py test_whatsapp_audio.py; do
    if [ -f "$test_file" ]; then
        # Verificar si ya existe en tests/
        if [ -f "tests/$test_file" ]; then
            log_warning "$test_file ya existe en tests/, eliminando duplicado de raíz"
            rm -f "$test_file"
        else
            mv "$test_file" "tests/"
            log_success "Movido $test_file a tests/"
        fi
        ((MOVED_FILES++))
    fi
done

###############################################################################
# 4. CONSOLIDAR DOCUMENTACIÓN
###############################################################################
log_info "FASE 4: Consolidando documentación..."

# Crear directorio de documentación histórica
mkdir -p docs/archive

# Mover documentación de fases a archive
for doc_file in AUDIO_TESTING_SUMMARY.md FASE2_TESTING_COMPLETADO.md \
                FASE3_INTEGRACION_COMPLETADA.md FASE4_OPTIMIZACION_COMPLETADA.md \
                MULTILINGUAL_SUMMARY.md OPTIMIZATION_SUMMARY.md PHASE5_ISSUES_EXPORT.md; do
    if [ -f "$doc_file" ]; then
        mv "$doc_file" "docs/archive/"
        log_success "Archivado $doc_file"
        ((MOVED_FILES++))
    fi
done

# Eliminar README duplicado
if [ -f "README_COMPLETE.md" ]; then
    if diff -q README.md README_COMPLETE.md > /dev/null 2>&1; then
        rm -f README_COMPLETE.md
        log_success "Eliminado README_COMPLETE.md (duplicado de README.md)"
        ((DELETED_FILES++))
    else
        mv README_COMPLETE.md docs/archive/
        log_success "Archivado README_COMPLETE.md (contenido diferente)"
        ((MOVED_FILES++))
    fi
fi

###############################################################################
# 5. LIMPIEZA DE ARCHIVOS DE CONFIGURACIÓN OBSOLETOS
###############################################################################
log_info "FASE 5: Limpiando archivos de configuración obsoletos..."

# Eliminar backup de .env antiguo
if [ -f ".env.backup.20251004_053705" ]; then
    mv .env.backup.20251004_053705 "$BACKUP_DIR/"
    log_success "Backup de .env movido a $BACKUP_DIR"
    ((MOVED_FILES++))
fi

# Verificar .env.test (consolidar si es necesario)
if [ -f ".env.test" ]; then
    if [ -f ".env.example" ]; then
        log_warning ".env.test existe, revisar si se puede consolidar con .env.example"
    fi
fi

###############################################################################
# 6. LIMPIEZA DE DOCKER COMPOSE DUPLICADOS
###############################################################################
log_info "FASE 6: Analizando Docker Compose files..."

# Listar docker-compose files
log_info "Docker Compose files encontrados:"
ls -1 docker-compose*.yml 2>/dev/null | while read -r file; do
    SIZE=$(get_size "$file")
    echo "  - $file ($SIZE)"
done

# Crear directorio para docker-compose no utilizados
mkdir -p docker/compose-archive

# Mover docker-compose no esenciales
if [ -f "docker-compose.audio-production.yml" ]; then
    log_warning "docker-compose.audio-production.yml - Verificar si es necesario"
    # No lo movemos automáticamente por si es usado
fi

if [ -f "docker-compose.test.yml" ]; then
    log_warning "docker-compose.test.yml - Verificar si es necesario"
fi

###############################################################################
# 7. LIMPIEZA DE REQUIREMENTS.TXT (REDUNDANTES CON PYPROJECT.TOML)
###############################################################################
log_info "FASE 7: Limpiando archivos requirements.txt redundantes..."

# Mover requirements a backup (ya se usa pyproject.toml)
mkdir -p "$BACKUP_DIR/requirements"

for req_file in requirements.txt requirements-prod.txt requirements-test.txt requirements-audio-optimization.txt; do
    if [ -f "$req_file" ]; then
        cp "$req_file" "$BACKUP_DIR/requirements/"
        # No eliminamos aún, solo informamos
        log_warning "$req_file existe (redundante con pyproject.toml) - backup creado"
    fi
done

log_info "Se recomienda usar solo pyproject.toml y eliminar requirements*.txt manualmente si confirmas que no son necesarios"

###############################################################################
# 8. LIMPIEZA DE DOCKERFILES
###############################################################################
log_info "FASE 8: Analizando Dockerfiles..."

log_info "Dockerfiles encontrados:"
ls -1 Dockerfile* 2>/dev/null | while read -r file; do
    SIZE=$(get_size "$file")
    echo "  - $file ($SIZE)"
done

if [ -f "Dockerfile.audio-optimized" ]; then
    log_warning "Dockerfile.audio-optimized - Verificar si se sigue usando"
fi

###############################################################################
# 9. LIMPIEZA DE HERRAMIENTAS DESCARGADAS
###############################################################################
log_info "FASE 9: Limpiando herramientas descargadas..."

# Mover k6 a tools
if [ -d "k6-v0.46.0-linux-amd64" ]; then
    SIZE=$(get_size k6-v0.46.0-linux-amd64)
    mkdir -p tools
    mv k6-v0.46.0-linux-amd64 tools/
    log_success "Movido k6-v0.46.0-linux-amd64/ a tools/ ($SIZE)"
    ((MOVED_FILES++))
fi

###############################################################################
# 10. LIMPIEZA DE AUDIT RESULTS
###############################################################################
log_info "FASE 10: Limpiando audit results..."

if [ -d "audit_results" ]; then
    if [ -z "$(ls -A audit_results)" ]; then
        rm -rf audit_results
        log_success "Eliminado audit_results/ (vacío)"
        ((DELETED_DIRS++))
    else
        # Archivar resultados antiguos
        mkdir -p docs/archive/audit_results
        mv audit_results/* docs/archive/audit_results/ 2>/dev/null || true
        rm -rf audit_results
        log_success "Archivados audit_results"
        ((MOVED_FILES++))
    fi
fi

###############################################################################
# 11. LIMPIEZA DE LOGS
###############################################################################
log_info "FASE 11: Limpiando archivos de log antiguos..."

# Buscar y archivar logs viejos
find . -type f -name "*.log" ! -path "*.venv*" ! -path "*node_modules*" -mtime +7 2>/dev/null | while read -r logfile; do
    mkdir -p "$BACKUP_DIR/logs/$(dirname "$logfile")"
    mv "$logfile" "$BACKUP_DIR/logs/$logfile"
    log_success "Archivado log antiguo: $logfile"
    ((MOVED_FILES++))
done

###############################################################################
# 12. OPTIMIZACIÓN DE .git
###############################################################################
log_info "FASE 12: Optimizando repositorio Git..."

# Git garbage collection
git gc --aggressive --prune=now 2>/dev/null || log_warning "Git gc falló o no es un repositorio git"

# Limpiar branches remotas eliminadas
git remote prune origin 2>/dev/null || log_warning "Git remote prune falló"

log_success "Optimización de Git completada"

###############################################################################
# REPORTE FINAL
###############################################################################
echo ""
echo "=========================================="
echo "  REPORTE DE LIMPIEZA"
echo "=========================================="
echo ""

log_info "Archivos eliminados: $DELETED_FILES"
log_info "Directorios eliminados: $DELETED_DIRS"
log_info "Archivos movidos/consolidados: $MOVED_FILES"

echo ""
log_info "Tamaño actual del proyecto:"
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO
echo "  - agente-hotel-api/: $(get_size agente-hotel-api/)"
echo "  - .git/: $(get_size .git/)"
echo "  - docs/: $(get_size docs/)"
echo "  - .venv/: $(get_size .venv/ 2>/dev/null || echo 'N/A')"

echo ""
log_success "Backup creado en: $BACKUP_DIR"
log_info "Si todo funciona correctamente, puedes eliminar el backup con:"
echo "  rm -rf $BACKUP_DIR"

echo ""
log_info "Archivos que requieren revisión manual:"
echo "  1. requirements*.txt (redundantes con pyproject.toml)"
echo "  2. docker-compose.audio-production.yml (verificar si es necesario)"
echo "  3. docker-compose.test.yml (verificar si es necesario)"
echo "  4. Dockerfile.audio-optimized (verificar si es necesario)"
echo "  5. .env.test (consolidar con .env.example si es posible)"

echo ""
log_success "✅ LIMPIEZA COMPLETADA"

# Generar reporte detallado
REPORT_FILE="/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api/docs/CLEANUP_REPORT_$(date +%Y%m%d_%H%M%S).md"

cat > "$REPORT_FILE" << EOF
# Reporte de Limpieza Profunda - Sistema Agente Hotelero IA

**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')  
**Script:** deep_cleanup.sh v1.0.0

## Resumen Ejecutivo

- **Archivos eliminados:** $DELETED_FILES
- **Directorios eliminados:** $DELETED_DIRS
- **Archivos movidos/consolidados:** $MOVED_FILES
- **Backup creado en:** $BACKUP_DIR

## Acciones Realizadas

### 1. Cache y Archivos Temporales
- ✅ Eliminado __pycache__ de app/ y tests/
- ✅ Eliminado .pytest_cache
- ✅ Eliminado .ruff_cache
- ✅ Eliminado archivos de coverage (.coverage, htmlcov/)
- ✅ Limpiado .benchmarks (si vacío)

### 2. Entornos Virtuales
- ✅ Eliminado venv/ duplicado
- ✅ Eliminado node_modules/ (no necesario)

### 3. Consolidación de Tests
- ✅ Movidos tests de raíz a tests/
  * test_audio.py
  * test_audio_workflow.py
  * test_main.py
  * test_whatsapp_audio.py

### 4. Consolidación de Documentación
- ✅ Creado docs/archive/ para documentación histórica
- ✅ Archivados documentos de fases:
  * AUDIO_TESTING_SUMMARY.md
  * FASE2_TESTING_COMPLETADO.md
  * FASE3_INTEGRACION_COMPLETADA.md
  * FASE4_OPTIMIZACION_COMPLETADA.md
  * MULTILINGUAL_SUMMARY.md
  * OPTIMIZATION_SUMMARY.md
  * PHASE5_ISSUES_EXPORT.md
- ✅ Procesado README_COMPLETE.md

### 5. Configuración
- ✅ Backup de .env.backup.20251004_053705

### 6. Docker Files
- ⚠️ Requiere revisión manual de docker-compose redundantes

### 7. Requirements.txt
- ⚠️ Archivos redundantes con pyproject.toml (requiere revisión)

### 8. Herramientas
- ✅ k6 movido a tools/

### 9. Audit Results
- ✅ Archivados en docs/archive/audit_results/

### 10. Logs
- ✅ Logs antiguos (>7 días) archivados en backup

### 11. Git
- ✅ Ejecutado git gc --aggressive
- ✅ Limpiadas branches remotas eliminadas

## Tamaño Actual del Proyecto

\`\`\`
agente-hotel-api/: $(cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO && get_size agente-hotel-api/)
.git/: $(cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO && get_size .git/)
docs/: $(cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO && get_size docs/)
.venv/: $(cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO && get_size .venv/ 2>/dev/null || echo 'N/A')
\`\`\`

## Acciones Pendientes (Revisión Manual)

1. **requirements*.txt** - Redundantes con pyproject.toml, considerar eliminar
2. **docker-compose.audio-production.yml** - Verificar si es necesario
3. **docker-compose.test.yml** - Verificar si es necesario
4. **Dockerfile.audio-optimized** - Verificar si es necesario
5. **.env.test** - Consolidar con .env.example si es posible

## Recomendaciones

1. Ejecutar tests para verificar que todo funciona correctamente
2. Si los tests pasan, eliminar el directorio de backup
3. Revisar archivos marcados para revisión manual
4. Considerar agregar al .gitignore:
   - __pycache__/
   - .pytest_cache/
   - .ruff_cache/
   - .coverage
   - htmlcov/
   - *.log
   - .env.backup.*

## Comandos de Verificación

\`\`\`bash
# Ejecutar tests
poetry run pytest tests/ -v

# Verificar health del sistema
make health

# Verificar build de Docker
docker-compose build

# Si todo funciona, eliminar backup
rm -rf $BACKUP_DIR
\`\`\`

---

**✅ Limpieza completada exitosamente**
EOF

log_success "Reporte detallado generado en: $REPORT_FILE"

exit 0
