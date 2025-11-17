# Archive - Documentación Histórica

**Propósito**: Este directorio contiene documentación obsoleta, versiones antiguas y archivos históricos del proyecto SIST_AGENTICO_HOTELERO.

**Última Actualización**: 2025-11-17  
**Política de Retención**: Mantener por 1 año, luego evaluar eliminación

---

## 📁 Estructura del Archive

### `/2025-11-pre-consolidation/`
**Fecha**: 2025-11-17  
**Razón**: Consolidación masiva de documentación para crear "fuente única de verdad"

#### `/duplicated-docs/`
Documentos que tenían contenido 80-100% idéntico a otros archivos activos.

**Archivos archivados**:
- `HANDOVER_PACKAGE.md` (3 KB)
  - **Razón**: Duplicado parcial de OPERATIONS_MANUAL.md
  - **Contenido**: Checklist go-live muy básico
  - **Reemplazado por**: `docs/operations/OPERATIONS_MANUAL.md`
  - **Fecha archivado**: 2025-11-17

#### `/obsolete-plans/`
Planes de ejecución y estrategias que ya fueron completadas o superadas.

**Archivos archivados**:
- _(Pendiente de migración)_

#### `/contradictory-reports/`
Reportes con métricas contradictorias que fueron consolidados en documentos actualizados.

**Archivos archivados**:
- _(Pendiente de migración)_

### `/docs-obsolete-nov5/`
**Fecha**: 2025-11-05  
**Razón**: Reorganización de documentación previa (snapshot histórico)

### `/docs-old/`
**Fecha**: Variable (2025-10 a 2025-11)  
**Razón**: Versiones antiguas de documentación antes de refactorings

### `/docs-old-nov3/`
**Fecha**: 2025-11-03  
**Razón**: Snapshot de documentación antes de cambios arquitectónicos

### `/plans-old/`
**Fecha**: 2025-10  
**Razón**: Planes de fases antiguas (PHASE_E5, etc.) ya completadas

---

## 🔍 Cómo Usar Este Archive

### Si necesitas información histórica:

1. **Buscar por fecha**: Usa la estructura de carpetas por fecha
2. **Buscar por contenido**: Usa grep recursivo
   ```bash
   cd archive
   grep -r "término de búsqueda" .
   ```
3. **Comparar versiones**: Usa diff entre archivo actual y archivado
   ```bash
   diff agente-hotel-api/docs/operations/OPERATIONS_MANUAL.md \
        archive/2025-11-pre-consolidation/duplicated-docs/HANDOVER_PACKAGE.md
   ```

### Si necesitas recuperar algo:

1. **Identificar archivo**: Navega a la carpeta correspondiente
2. **Copiar a ubicación activa**: 
   ```bash
   cp archive/path/to/file.md agente-hotel-api/docs/newlocation/
   ```
3. **Actualizar referencias**: Ejecutar script de validación de enlaces
   ```bash
   python scripts/validate_links.py
   ```

---

## 📊 Estadísticas del Archive

**Total de archivos archivados**: 1 (2025-11-17)  
**Espacio total**: ~3 KB (insignificante)  
**Archivos más antiguos**: 2025-10 (plans-old/)  
**Última actualización**: 2025-11-17

---

## ⚠️ Advertencias

1. **NO editar archivos en archive**: Son históricos, no activos
2. **NO commitear archivos nuevos aquí**: Usar ubicación activa y luego mover si se vuelve obsoleto
3. **NO eliminar sin aprobación**: Puede haber información de compliance/auditoría

---

## 🗓️ Política de Retención

### Retención por Categoría

| Categoría | Retención | Razón |
|-----------|-----------|-------|
| Duplicados | 6 meses | Recuperación rápida si consolidación falló |
| Planes completados | 1 año | Auditoría de decisiones pasadas |
| Reportes contradictorios | 6 meses | Trazabilidad de métricas |
| Snapshots de docs | 1 año | Referencia histórica |

### Proceso de Limpieza (Anual)

```bash
# Ejecutar cada noviembre
cd archive

# Eliminar duplicados >6 meses
find 2025-11-pre-consolidation/duplicated-docs/ -type f -mtime +180 -delete

# Eliminar planes >1 año
find */obsolete-plans/ -type f -mtime +365 -delete

# Reportar eliminaciones
git log --diff-filter=D --summary | grep "delete mode"
```

---

## 📝 Changelog del Archive

### 2025-11-17 - Consolidación Masiva Iniciada
- Creado `/2025-11-pre-consolidation/` con estructura organizada
- Archivado: `HANDOVER_PACKAGE.md` (duplicado de OPERATIONS_MANUAL)
- **Acción**: Consolidación de 180+ documentos en curso

### 2025-11-05 - Snapshot Pre-Refactoring
- Creado `/docs-obsolete-nov5/` con ~15 documentos
- **Razón**: Reorganización de estructura de /docs

### 2025-11-03 - Snapshot de Documentación
- Creado `/docs-old-nov3/` con ~20 documentos
- **Razón**: Cambios arquitectónicos mayores

### 2025-10 - Planes Antiguos
- Creado `/plans-old/` con planes de fases completadas
- **Razón**: PHASE_E5 y otros completados

---

## 🔗 Referencias Relacionadas

- **Documentación activa**: `agente-hotel-api/docs/`
- **Índice maestro**: `agente-hotel-api/docs/00-DOCUMENTATION-CENTRAL-INDEX.md`
- **Guía de contribución**: `.github/CONTRIBUTING.md`
- **Copilot instructions**: `.github/copilot-instructions.md`

---

## 📧 Contacto

Si tienes preguntas sobre archivos archivados o necesitas recuperar algo:
- **Backend Team**: backend@proyecto.com
- **Tech Lead**: techlead@proyecto.com
- **Issue Tracker**: GitHub Issues con tag `documentation-archive`

---

**Última revisión**: 2025-11-17  
**Mantenido por**: Backend AI Team  
**Versión**: 1.0.0
