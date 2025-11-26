#!/bin/bash
# Script de Auditoría de Deuda Técnica
# Analiza TODOs, FIXMEs, complejidad y mantenibilidad del código

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     🔍 AUDITORÍA DE DEUDA TÉCNICA - Agente Hotel API         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

REPORT_DIR=".playbook"
mkdir -p "$REPORT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TODOS_FILE="$REPORT_DIR/todos_$TIMESTAMP.txt"
COMPLEXITY_FILE="$REPORT_DIR/complexity_$TIMESTAMP.txt"
REPORT_FILE="$REPORT_DIR/TECH_DEBT_REPORT.md"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}▶ Paso 1/4: Buscando TODOs, FIXMEs y HACKs...${NC}"
echo ""

# Buscar TODOs y FIXMEs
grep -rn "TODO\|FIXME\|XXX\|HACK" app/ --color=never 2>/dev/null | tee "$TODOS_FILE" || echo "No se encontraron TODOs/FIXMEs"
TODO_COUNT=$(wc -l < "$TODOS_FILE" 2>/dev/null || echo "0")
echo -e "${GREEN}✓ Encontrados: $TODO_COUNT items${NC}"
echo ""

echo -e "${BLUE}▶ Paso 2/4: Analizando complejidad ciclomática...${NC}"
echo ""

# Analizar complejidad con radon (si está disponible)
if command -v radon &> /dev/null; then
    radon cc app/ -a -nb | tee "$COMPLEXITY_FILE"
    echo -e "${GREEN}✓ Análisis de complejidad completado${NC}"
else
    echo -e "${YELLOW}⚠ radon no instalado - saltando análisis de complejidad${NC}"
    echo "Instalar con: pip install radon"
fi
echo ""

echo -e "${BLUE}▶ Paso 3/4: Analizando mantenibilidad...${NC}"
echo ""

# Analizar índice de mantenibilidad
if command -v radon &> /dev/null; then
    MAINTAINABILITY=$(radon mi app/ -nb 2>/dev/null || echo "No disponible")
    echo "$MAINTAINABILITY"
    echo -e "${GREEN}✓ Análisis de mantenibilidad completado${NC}"
else
    echo -e "${YELLOW}⚠ radon no instalado - saltando análisis de mantenibilidad${NC}"
fi
echo ""

echo -e "${BLUE}▶ Paso 4/4: Generando reporte consolidado...${NC}"
echo ""

# Generar reporte markdown
cat > "$REPORT_FILE" << EOF
# 📊 Reporte de Deuda Técnica

**Fecha de generación:** $(date '+%d de %B de %Y, %H:%M')  
**Ejecutado por:** tech-debt-audit.sh  
**Versión:** 1.0

---

## 🎯 Resumen Ejecutivo

| Métrica | Valor | Estado |
|---------|-------|--------|
| TODOs/FIXMEs encontrados | $TODO_COUNT | $([ $TODO_COUNT -gt 10 ] && echo "🔴 Alto" || ([ $TODO_COUNT -gt 5 ] && echo "🟡 Medio" || echo "🟢 Bajo")) |
| Archivos analizados | $(find app/ -name "*.py" | wc -l) | ✅ |
| Timestamp | $TIMESTAMP | ✅ |

---

## 📝 TODOs y FIXMEs Encontrados

$(if [ $TODO_COUNT -gt 0 ]; then
    echo "### Lista completa"
    echo ""
    echo "\`\`\`"
    cat "$TODOS_FILE"
    echo "\`\`\`"
    echo ""
    echo "**Total:** $TODO_COUNT items pendientes"
else
    echo "✅ No se encontraron TODOs o FIXMEs en el código."
fi)

---

## 🔢 Análisis de Complejidad Ciclomática

$(if [ -f "$COMPLEXITY_FILE" ]; then
    echo "### Archivos con mayor complejidad"
    echo ""
    echo "\`\`\`"
    head -30 "$COMPLEXITY_FILE"
    echo "\`\`\`"
    echo ""
    echo "Ver archivo completo: \`$COMPLEXITY_FILE\`"
else
    echo "⚠️ Análisis de complejidad no disponible."
    echo ""
    echo "**Instalar radon para habilitar:**"
    echo "\`\`\`bash"
    echo "pip install radon"
    echo "\`\`\`"
fi)

---

## 🎨 Índice de Mantenibilidad

$(if command -v radon &> /dev/null; then
    echo "### Clasificación por Mantenibilidad"
    echo ""
    radon mi app/ -nb -s 2>/dev/null || echo "No disponible"
else
    echo "⚠️ Análisis de mantenibilidad no disponible."
    echo ""
    echo "Requiere: \`pip install radon\`"
fi)

---

## 🎯 Recomendaciones Prioritarias

### Prioridad Alta 🔴

$(if [ $TODO_COUNT -gt 10 ]; then
    echo "1. **Resolver TODOs críticos** - Se encontraron $TODO_COUNT items pendientes"
    echo "   - Revisar y priorizar TODOs/FIXMEs"
    echo "   - Crear issues para items importantes"
    echo "   - Eliminar comentarios obsoletos"
else
    echo "✅ Nivel de TODOs bajo - mantener bajo control"
fi)

2. **Refactorizar funciones complejas**
   - Buscar funciones con complejidad ciclomática > 10
   - Dividir en funciones más pequeñas
   - Mejorar testeabilidad

3. **Mejorar cobertura de tests**
   - Actual: 73%
   - Objetivo: 80%+
   - Enfocarse en módulos críticos

### Prioridad Media 🟡

1. **Documentación de código**
   - Agregar docstrings faltantes
   - Documentar casos edge
   - Actualizar comentarios obsoletos

2. **Type hints**
   - Agregar type hints a funciones públicas
   - Habilitar mypy strict mode gradualmente

### Prioridad Baja 🟢

1. **Optimizaciones de performance**
   - Identificar cuellos de botella
   - Optimizar queries N+1
   - Cachear resultados frecuentes

---

## 📈 Tendencias y Métricas

### Evolución de Deuda Técnica

| Fecha | TODOs | Complejidad Promedio | Mantenibilidad |
|-------|-------|---------------------|----------------|
| $(date '+%Y-%m-%d') | $TODO_COUNT | N/A | N/A |

**Nota:** Ejecutar este script periódicamente para tracking de tendencias.

---

## 🔧 Herramientas Recomendadas

### Instaladas
- ✅ pytest (testing)
- ✅ pytest-cov (cobertura)
- ✅ ruff (linting)

### Por instalar
- ⏳ radon (análisis de complejidad)
- ⏳ pylint (análisis estático avanzado)
- ⏳ vulture (detección de código muerto)

**Comando de instalación:**
\`\`\`bash
poetry add --group dev radon pylint vulture
\`\`\`

---

## 📊 Archivos del Análisis

- TODOs/FIXMEs: \`$TODOS_FILE\`
- Complejidad: \`$COMPLEXITY_FILE\`
- Este reporte: \`$REPORT_FILE\`

---

## 🚀 Próximos Pasos

1. Revisar este reporte con el equipo
2. Priorizar items críticos
3. Crear plan de acción
4. Ejecutar auditoría mensualmente
5. Tracking de métricas en el tiempo

---

**Generado automáticamente por:** \`scripts/tech-debt-audit.sh\`  
**Para re-ejecutar:** \`./scripts/tech-debt-audit.sh\`
EOF

echo -e "${GREEN}✓ Reporte generado: $REPORT_FILE${NC}"
echo ""

# Mostrar resumen
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    📊 RESUMEN DEL ANÁLISIS                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "  TODOs/FIXMEs encontrados:  $TODO_COUNT"
echo "  Archivos Python:           $(find app/ -name "*.py" | wc -l)"
echo "  Reporte generado:          $REPORT_FILE"
echo ""
echo "  Ver reporte completo:"
echo "  $ cat $REPORT_FILE"
echo ""
echo -e "${GREEN}✅ Auditoría completada exitosamente${NC}"
