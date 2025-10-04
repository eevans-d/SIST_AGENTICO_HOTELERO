# 🎯 PLAN DE EJECUCIÓN INMEDIATA - Validación y Optimización Completa

**Fecha:** 4 de octubre de 2025  
**Objetivo:** Validar ambiente de desarrollo + Implementar herramientas avanzadas + Optimizar infraestructura crítica  
**Duración Total Estimada:** 90-120 minutos  
**Estado Inicial:** Sprint 1, 2, 3 completados (60%) - Commit 6f5f03d

---

## 📋 ESTRUCTURA DEL PLAN

### **FASE A: VALIDACIÓN Y TESTING DEL NUEVO ENTORNO** 🧪
**Duración:** 30-40 minutos  
**Objetivo:** Garantizar que todas las mejoras implementadas funcionan correctamente

### **FASE B: HERRAMIENTAS AVANZADAS (SPRINT 4)** 🛠️
**Duración:** 30-40 minutos  
**Objetivo:** Automatizar calidad de código y procesos CI/CD

### **FASE C: OPTIMIZACIÓN CRÍTICA DE INFRAESTRUCTURA** 🚀
**Duración:** 30-40 minutos  
**Objetivo:** Resolver deudas técnicas identificadas y optimizar componentes clave

---

## ═══════════════════════════════════════════════════════════════
## FASE A: VALIDACIÓN Y TESTING DEL NUEVO ENTORNO 🧪
## ═══════════════════════════════════════════════════════════════

### A.1. Pre-Validación del Sistema (5 min)

#### A.1.1. Verificar Estado Actual
```bash
# Comando 1: Estado Git
git status
git log --oneline -5

# Comando 2: Estado Docker
docker ps -a
docker images | grep agente

# Comando 3: Estado de Servicios
make health
```

**Criterios de Éxito:**
- ✅ Working tree limpio
- ✅ Último commit: 6f5f03d
- ✅ Sin contenedores fallidos
- ✅ Health checks pasando

**Acciones si falla:** Resolver conflictos antes de continuar

---

#### A.1.2. Verificar Dependencias Instaladas
```bash
# Comando: Listar paquetes nuevos
poetry show | grep -E "(pytest-cov|pytest-benchmark|pytest-watch)"
```

**Criterios de Éxito:**
- ✅ pytest-cov ~5.0.0
- ✅ pytest-benchmark ~4.0.0
- ✅ pytest-watch ~4.2.0

**Archivo a verificar:** `poetry.lock` debe contener los 8 paquetes nuevos

---

### A.2. Ejecutar Script de Setup Automatizado (10 min)

#### A.2.1. Preparar Ambiente de Prueba
```bash
# Comando 1: Backup de .env actual
cp agente-hotel-api/.env agente-hotel-api/.env.backup.$(date +%Y%m%d_%H%M%S)

# Comando 2: Ejecutar dev-setup.sh
cd agente-hotel-api
chmod +x dev-setup.sh
./dev-setup.sh
```

**Criterios de Éxito:**
- ✅ Script ejecuta sin errores
- ✅ Todos los prerequisitos detectados correctamente
- ✅ Archivo .env creado/actualizado
- ✅ Git hooks instalados en .git/hooks/
- ✅ Dependencias Poetry verificadas
- ✅ Validación final exitosa

**Validaciones Esperadas:**
1. ✅ Python 3.11+ detectado
2. ✅ Docker + Docker Compose disponibles
3. ✅ Poetry instalado
4. ✅ Git configurado
5. ✅ Secrets generados automáticamente
6. ✅ Estructura de directorios validada

**Acciones si falla:**
- Revisar logs del script
- Verificar permisos de ejecución
- Consultar DEBUGGING.md sección "Script de Setup"

---

#### A.2.2. Validar Archivos Generados
```bash
# Comando: Verificar archivos críticos
ls -la agente-hotel-api/.env
ls -la agente-hotel-api/.git/hooks/pre-commit
ls -la agente-hotel-api/.git/hooks/pre-push
cat agente-hotel-api/.env | grep -E "(SECRET_KEY|JWT_SECRET|ENCRYPTION_KEY)"
```

**Criterios de Éxito:**
- ✅ .env existe y contiene secrets generados (no dummies)
- ✅ Hooks Git instalados y ejecutables
- ✅ Secrets tienen longitud adecuada (≥32 caracteres)

---

### A.3. Probar Comandos Nuevos del Makefile (10 min)

#### A.3.1. Comandos de Desarrollo
```bash
cd agente-hotel-api

# Test 1: Levantar ambiente dev
make dev-up

# Esperar 30 segundos para que servicios inicien
sleep 30

# Test 2: Verificar status
make dev-status

# Test 3: Ver logs
make dev-logs | head -50

# Test 4: Shell interactivo
make dev-shell
# Dentro del shell:
# - python --version
# - pip list | grep pytest
# - exit
```

**Criterios de Éxito:**
- ✅ `dev-up` levanta 8 servicios correctamente
- ✅ `dev-status` muestra todos los servicios "Up" y "healthy"
- ✅ Logs no muestran errores críticos
- ✅ Shell interactivo accesible

**Servicios Esperados:**
1. postgres (healthy)
2. redis (healthy)
3. agente-api (healthy)
4. prometheus (healthy)
5. grafana (healthy)
6. adminer (healthy)
7. redis-commander (healthy)
8. mailhog (healthy)

**Acciones si falla:**
- Verificar puertos disponibles (5432, 6379, 8000, 9090, 3000, 8080, 8081, 8025)
- Revisar logs: `docker compose -f docker-compose.dev.yml logs [servicio]`
- Consultar DEBUGGING.md sección "Docker Troubleshooting"

---

#### A.3.2. Comandos de Testing
```bash
# Test 1: Cobertura de pruebas
make test-cov

# Test 2: Tests unitarios solamente
make test-unit

# Test 3: Quick check (linting + tests rápidos)
make quick-check

# Test 4: Benchmark (si hay tiempo)
make benchmark
```

**Criterios de Éxito:**
- ✅ `test-cov` genera reporte HTML en `htmlcov/`
- ✅ Cobertura ≥ 70% (actual: probablemente ~65-75%)
- ✅ `test-unit` ejecuta ≥20 tests (actual: 46 tests)
- ✅ `quick-check` completa en <60 segundos
- ✅ `benchmark` genera estadísticas de performance

**Métricas Esperadas:**
- Total tests: 46
- Tests unitarios: ~20-25
- Tests integración: ~15-20
- Tests e2e: ~5-10
- Tiempo ejecución: <30 segundos

**Archivos Generados:**
- `htmlcov/index.html` - Reporte de cobertura
- `.coverage` - Base de datos de cobertura
- `.benchmarks/` - Resultados de benchmarks

---

### A.4. Validar Herramientas de Desarrollo (5 min)

#### A.4.1. Acceder a Herramientas Web
```bash
# Abrir en navegador (o verificar con curl):
curl -I http://localhost:8080  # Adminer (PostgreSQL GUI)
curl -I http://localhost:8081  # Redis Commander
curl -I http://localhost:8025  # MailHog
curl -I http://localhost:9090  # Prometheus
curl -I http://localhost:3000  # Grafana
```

**Criterios de Éxito:**
- ✅ Todas las URLs responden 200 OK
- ✅ Adminer conecta a PostgreSQL con credenciales de .env
- ✅ Redis Commander muestra datos de Redis
- ✅ MailHog captura emails de prueba
- ✅ Prometheus muestra métricas del agente
- ✅ Grafana tiene dashboards pre-configurados

**Credenciales de Acceso:**
- Adminer: Sistema=PostgreSQL, Servidor=postgres, Usuario/DB/Password desde .env
- Redis Commander: Sin autenticación en dev
- MailHog: Sin autenticación
- Prometheus: Sin autenticación
- Grafana: admin/admin (cambiar en primer login)

---

#### A.4.2. Probar Hot-Reload
```bash
# Test: Modificar archivo y verificar reload automático
echo "# Test hot-reload $(date)" >> agente-hotel-api/app/main.py

# Verificar logs para confirmar reload
docker compose -f docker-compose.dev.yml logs agente-api | tail -20

# Revertir cambio
git checkout agente-hotel-api/app/main.py
```

**Criterios de Éxito:**
- ✅ Cambio detectado en <2 segundos
- ✅ Servicio se recarga automáticamente
- ✅ Logs muestran mensaje de reload
- ✅ Sin necesidad de rebuild

**Mensaje Esperado en Logs:**
```
INFO: Detected file change, reloading...
INFO: Application startup complete.
```

---

### A.5. Documentación y Reporte de Validación (5 min)

#### A.5.1. Generar Reporte de Cobertura
```bash
# Abrir reporte HTML en navegador
xdg-open agente-hotel-api/htmlcov/index.html
# O en macOS: open htmlcov/index.html
# O simplemente navegar a file:///path/to/htmlcov/index.html
```

**Análisis Esperado:**
- Identificar archivos con cobertura <70%
- Priorizar servicios críticos (orchestrator, pms_adapter, message_gateway)
- Listar funciones sin cobertura

---

#### A.5.2. Crear Documento de Validación
**Archivo:** `VALIDATION_REPORT_FASE_A.md`

**Contenido:**
```markdown
# Reporte de Validación - Fase A

**Fecha:** 4 de octubre de 2025  
**Ejecutado por:** AI Agent  
**Duración:** [tiempo real]

## Resumen Ejecutivo
- ✅/❌ Script dev-setup.sh ejecutado exitosamente
- ✅/❌ 8 servicios Docker levantados y healthy
- ✅/❌ 16 comandos Makefile funcionales
- ✅/❌ Hot-reload operativo (<2s)
- ✅/❌ Cobertura de tests: XX%
- ✅/❌ Herramientas web accesibles

## Detalles por Componente
[Lista detallada con checks y tiempos]

## Issues Identificados
[Problemas encontrados y resolución]

## Recomendaciones
[Mejoras sugeridas para siguientes fases]
```

---

## ═══════════════════════════════════════════════════════════════
## FASE B: HERRAMIENTAS AVANZADAS (SPRINT 4) 🛠️
## ═══════════════════════════════════════════════════════════════

### B.1. Pre-commit Hooks Avanzados (15 min)

#### B.1.1. Configurar Pre-commit Framework
**Archivo:** `agente-hotel-api/.pre-commit-config.yaml`

**Contenido:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-json
      - id: check-merge-conflict
      - id: check-case-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports, --no-strict-optional]

  - repo: local
    hooks:
      - id: pytest-quick
        name: pytest-quick
        entry: poetry run pytest tests/unit -x -v
        language: system
        pass_filenames: false
        always_run: true
```

**Instalación:**
```bash
cd agente-hotel-api
poetry add --group dev pre-commit
poetry run pre-commit install
poetry run pre-commit install --hook-type pre-push
```

**Criterios de Éxito:**
- ✅ Archivo .pre-commit-config.yaml creado
- ✅ pre-commit instalado en Poetry
- ✅ Hooks instalados en .git/hooks/
- ✅ Test manual: `poetry run pre-commit run --all-files` pasa

---

#### B.1.2. Configurar Bandit para Seguridad
**Agregar a:** `agente-hotel-api/pyproject.toml`

**Contenido:**
```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv"]
tests = ["B201", "B301", "B302", "B303", "B304", "B305", "B306", "B307", "B308", "B309", "B310", "B311", "B312", "B313", "B314", "B315", "B316", "B317", "B318", "B319", "B320", "B321", "B323", "B324", "B325", "B401", "B402", "B403", "B404", "B405", "B406", "B407", "B408", "B409", "B410", "B411", "B412", "B413", "B501", "B502", "B503", "B504", "B505", "B506", "B507", "B601", "B602", "B603", "B604", "B605", "B606", "B607", "B608", "B609", "B610", "B611", "B701", "B702", "B703"]
skips = ["B101", "B601"]  # assert_used, subprocess
```

---

#### B.1.3. Configurar MyPy para Type Checking
**Agregar a:** `agente-hotel-api/pyproject.toml`

**Contenido:**
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Gradualmente aumentar
ignore_missing_imports = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true
```

---

#### B.1.4. Actualizar Makefile con Comandos Pre-commit
**Agregar a:** `agente-hotel-api/Makefile`

```makefile
# ============================================
# PRE-COMMIT HOOKS
# ============================================

.PHONY: pre-commit-install
pre-commit-install: ## Instalar pre-commit hooks
	@echo "📦 Instalando pre-commit..."
	poetry add --group dev pre-commit
	poetry run pre-commit install
	poetry run pre-commit install --hook-type pre-push
	@echo "✅ Pre-commit hooks instalados"

.PHONY: pre-commit-run
pre-commit-run: ## Ejecutar pre-commit en todos los archivos
	@echo "🔍 Ejecutando pre-commit..."
	poetry run pre-commit run --all-files

.PHONY: pre-commit-update
pre-commit-update: ## Actualizar versiones de pre-commit hooks
	@echo "🔄 Actualizando pre-commit hooks..."
	poetry run pre-commit autoupdate

.PHONY: security-scan
security-scan: ## Escaneo de seguridad con bandit
	@echo "🔒 Escaneando código con Bandit..."
	poetry run bandit -r app/ -c pyproject.toml

.PHONY: type-check
type-check: ## Type checking con mypy
	@echo "🔍 Verificando tipos con MyPy..."
	poetry run mypy app/ --config-file pyproject.toml
```

**Test:**
```bash
make pre-commit-install
make pre-commit-run
make security-scan
make type-check
```

---

### B.2. Pipeline CI Local (10 min)

#### B.2.1. Crear Script de CI Local
**Archivo:** `agente-hotel-api/scripts/ci-local.sh`

**Contenido:**
```bash
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  🚀 CI LOCAL PIPELINE - Agente Hotel API     ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

START_TIME=$(date +%s)

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para reportar pasos
step() {
    echo -e "${BLUE}▶ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# PASO 1: Linting
step "Paso 1/7: Linting con Ruff..."
if poetry run ruff check app/ tests/ --fix; then
    success "Linting pasado"
else
    error "Linting falló"
fi

# PASO 2: Formateo
step "Paso 2/7: Verificando formato con Ruff..."
if poetry run ruff format --check app/ tests/; then
    success "Formato correcto"
else
    error "Formato incorrecto - ejecuta 'make fmt'"
fi

# PASO 3: Type Checking
step "Paso 3/7: Type checking con MyPy..."
if poetry run mypy app/ --config-file pyproject.toml --no-error-summary 2>/dev/null || true; then
    success "Type checking completado"
else
    echo -e "${YELLOW}⚠ Type checking con warnings (no bloqueante)${NC}"
fi

# PASO 4: Security Scan
step "Paso 4/7: Escaneo de seguridad con Bandit..."
if poetry run bandit -r app/ -c pyproject.toml -lll -q; then
    success "Escaneo de seguridad pasado"
else
    error "Vulnerabilidades de seguridad detectadas"
fi

# PASO 5: Tests Unitarios
step "Paso 5/7: Ejecutando tests unitarios..."
if poetry run pytest tests/unit -v --tb=short; then
    success "Tests unitarios pasados"
else
    error "Tests unitarios fallaron"
fi

# PASO 6: Tests de Integración
step "Paso 6/7: Ejecutando tests de integración..."
if poetry run pytest tests/integration -v --tb=short; then
    success "Tests de integración pasados"
else
    error "Tests de integración fallaron"
fi

# PASO 7: Coverage Check
step "Paso 7/7: Verificando cobertura de tests..."
if poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=70 -q; then
    success "Cobertura ≥70%"
else
    echo -e "${YELLOW}⚠ Cobertura <70% (no bloqueante en local)${NC}"
fi

# Reporte Final
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  ✅ CI LOCAL PIPELINE COMPLETADO              ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Duración: ${DURATION}s${NC}"
echo ""
echo "🚀 Todo listo para push!"
```

**Instalación:**
```bash
chmod +x agente-hotel-api/scripts/ci-local.sh
```

**Agregar a Makefile:**
```makefile
.PHONY: ci-local
ci-local: ## Ejecutar pipeline CI completo localmente
	@./scripts/ci-local.sh
```

**Test:**
```bash
make ci-local
```

---

#### B.2.2. Integrar CI Local con Pre-push Hook
**Archivo:** `agente-hotel-api/.git/hooks/pre-push` (actualizar)

**Contenido:**
```bash
#!/bin/bash

echo "🚀 Ejecutando CI local antes de push..."
cd "$(git rev-parse --show-toplevel)/agente-hotel-api"

if ./scripts/ci-local.sh; then
    echo "✅ CI local pasado - procediendo con push"
    exit 0
else
    echo "❌ CI local falló - push bloqueado"
    echo "Ejecuta 'make ci-local' para ver detalles"
    exit 1
fi
```

---

### B.3. Automatización de Benchmarks (5 min)

#### B.3.1. Crear Suite de Benchmarks
**Archivo:** `agente-hotel-api/tests/benchmarks/test_performance.py`

**Contenido:**
```python
"""Performance benchmarks for critical paths."""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.benchmark(group="api")
def test_health_endpoint_performance(benchmark):
    """Benchmark health endpoint response time."""
    async def health_check():
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/live")
            assert response.status_code == 200
    
    benchmark(health_check)


@pytest.mark.benchmark(group="orchestrator")
async def test_message_processing_performance(benchmark):
    """Benchmark message orchestration pipeline."""
    from app.services.orchestrator import MessageOrchestrator
    from app.models.unified_message import UnifiedMessage
    
    orchestrator = MessageOrchestrator()
    
    test_message = UnifiedMessage(
        channel="test",
        sender_id="test_user",
        content="Hola, quiero hacer una reserva",
        timestamp=1234567890,
        tenant_id="default"
    )
    
    async def process():
        return await orchestrator.process_message(test_message)
    
    result = benchmark(process)
    assert result is not None


@pytest.mark.benchmark(group="pms")
async def test_pms_adapter_cache_performance(benchmark):
    """Benchmark PMS adapter with cache hits."""
    from app.services.pms_adapter import PMSAdapter
    
    adapter = PMSAdapter()
    
    async def check_availability():
        return await adapter.check_availability(
            hotel_id=1,
            check_in="2025-12-01",
            check_out="2025-12-05"
        )
    
    result = benchmark(check_availability)
    assert result is not None
```

---

#### B.3.2. Configurar Baseline de Performance
**Archivo:** `agente-hotel-api/.benchmarks/baseline.json`

Este archivo se genera automáticamente, pero podemos establecer thresholds:

**Agregar a:** `agente-hotel-api/pytest.ini`

```ini
[pytest]
# ... configuración existente ...

# Benchmark configuration
benchmark_max_time = 0.5  # 500ms max por test
benchmark_min_rounds = 5
benchmark_calibration_precision = 10
benchmark_warmup = true
```

---

#### B.3.3. Automatizar Comparación de Benchmarks
**Archivo:** `agente-hotel-api/scripts/benchmark-compare.sh`

**Contenido:**
```bash
#!/bin/bash
# Compara benchmarks actuales con baseline

set -e

echo "🔍 Comparando benchmarks con baseline..."

# Ejecutar benchmarks y guardar resultados
poetry run pytest tests/benchmarks/ \
    --benchmark-only \
    --benchmark-json=.benchmarks/current.json

# Si existe baseline, comparar
if [ -f .benchmarks/baseline.json ]; then
    echo "📊 Comparando con baseline..."
    poetry run pytest-benchmark compare \
        .benchmarks/baseline.json \
        .benchmarks/current.json \
        --csv=.benchmarks/comparison.csv
    
    echo "✅ Comparación guardada en .benchmarks/comparison.csv"
else
    echo "⚠️  No existe baseline - guardando como referencia"
    cp .benchmarks/current.json .benchmarks/baseline.json
fi
```

**Agregar a Makefile:**
```makefile
.PHONY: benchmark-baseline
benchmark-baseline: ## Establecer baseline de performance
	@echo "📊 Estableciendo baseline de performance..."
	poetry run pytest tests/benchmarks/ --benchmark-only --benchmark-json=.benchmarks/baseline.json
	@echo "✅ Baseline guardado"

.PHONY: benchmark-compare
benchmark-compare: ## Comparar performance con baseline
	@./scripts/benchmark-compare.sh
```

---

## ═══════════════════════════════════════════════════════════════
## FASE C: OPTIMIZACIÓN CRÍTICA DE INFRAESTRUCTURA 🚀
## ═══════════════════════════════════════════════════════════════

### C.1. Análisis de Deuda Técnica (10 min)

#### C.1.1. Auditoría de Código
**Ejecutar:**
```bash
cd agente-hotel-api

# 1. Buscar TODOs y FIXMEs
echo "🔍 Buscando TODOs y FIXMEs..."
grep -rn "TODO\|FIXME\|XXX\|HACK" app/ --color=always | tee .playbook/todos.txt

# 2. Buscar code smells
echo "🔍 Buscando código duplicado..."
poetry run pylint app/ --disable=all --enable=duplicate-code || true

# 3. Complejidad ciclomática
echo "🔍 Analizando complejidad..."
poetry run radon cc app/ -a -nb | tee .playbook/complexity.txt

# 4. Mantenibilidad
echo "🔍 Analizando mantenibilidad..."
poetry run radon mi app/ -nb | tee .playbook/maintainability.txt
```

**Instalar herramientas si es necesario:**
```bash
poetry add --group dev pylint radon
```

---

#### C.1.2. Crear Reporte de Deuda Técnica
**Archivo:** `agente-hotel-api/.playbook/TECH_DEBT_REPORT.md`

**Contenido generado automáticamente basado en análisis:**
```markdown
# Reporte de Deuda Técnica

**Fecha:** 4 de octubre de 2025  
**Generado por:** Auditoría automatizada

## Resumen Ejecutivo
- Total TODOs/FIXMEs: [número]
- Archivos con complejidad alta: [lista]
- Índice de mantenibilidad promedio: [score]

## Prioridad Alta 🔴
[Issues críticos que afectan funcionamiento]

## Prioridad Media 🟡
[Issues que afectan mantenibilidad]

## Prioridad Baja 🟢
[Mejoras cosméticas]

## Recomendaciones
[Acciones prioritarias]
```

---

### C.2. Optimización de Servicios Críticos (15 min)

#### C.2.1. Optimizar PMS Adapter
**Análisis:** Identificar puntos de mejora en `app/services/pms_adapter.py`

**Mejoras a implementar:**

1. **Cache Warming:** Pre-calentar cache al inicio
```python
# Agregar a PMSAdapter.__init__ o método start()
async def warm_cache(self):
    """Pre-warm cache with frequently accessed data."""
    logger.info("Warming PMS cache...")
    try:
        # Cache hotel list
        await self.get_hotels()
        # Cache room types for default hotel
        await self.get_room_types(hotel_id=1)
        logger.info("PMS cache warmed successfully")
    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")
```

2. **Batch Operations:** Agrupar llamadas API
```python
async def check_availability_batch(
    self,
    requests: List[AvailabilityRequest]
) -> List[AvailabilityResponse]:
    """Check availability for multiple requests in batch."""
    # Implementación con asyncio.gather para paralelizar
    tasks = [
        self.check_availability(
            hotel_id=req.hotel_id,
            check_in=req.check_in,
            check_out=req.check_out
        )
        for req in requests
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

3. **Metrics Enhancement:** Agregar métricas detalladas
```python
# Agregar histogram para latencia por endpoint
pms_endpoint_latency = Histogram(
    'pms_endpoint_latency_seconds',
    'PMS API endpoint latency',
    ['endpoint', 'method', 'cache_status']
)

# Usar en cada llamada
with pms_endpoint_latency.labels(
    endpoint='/availability',
    method='GET',
    cache_status='hit' if from_cache else 'miss'
).time():
    result = await self._make_request(...)
```

---

#### C.2.2. Optimizar Orchestrator
**Archivo:** `app/services/orchestrator.py`

**Mejoras:**

1. **Pipeline Paralelo:** Paralelizar operaciones independientes
```python
async def process_message(self, message: UnifiedMessage) -> Response:
    """Process message with parallel operations where possible."""
    
    # Operaciones paralelas
    intent_task = asyncio.create_task(self.nlp.detect_intent(message.content))
    session_task = asyncio.create_task(self.session_manager.get_session(message.sender_id))
    
    intent, session = await asyncio.gather(intent_task, session_task)
    
    # Continuar con lógica secuencial...
```

2. **Circuit Breaker para NLP:** Proteger llamadas a NLP
```python
from app.core.circuit_breaker import CircuitBreaker

class MessageOrchestrator:
    def __init__(self):
        self.nlp_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=NLPError
        )
    
    async def _safe_nlp_call(self, text: str):
        """NLP call with circuit breaker."""
        async with self.nlp_circuit:
            return await self.nlp.detect_intent(text)
```

3. **Request Deduplication:** Evitar procesar mensajes duplicados
```python
from aiocache import Cache

class MessageOrchestrator:
    def __init__(self):
        self.dedup_cache = Cache(Cache.REDIS)
    
    async def is_duplicate(self, message: UnifiedMessage) -> bool:
        """Check if message was recently processed."""
        key = f"msg:{message.sender_id}:{hash(message.content)}"
        if await self.dedup_cache.exists(key):
            return True
        await self.dedup_cache.set(key, 1, ttl=60)  # 60s window
        return False
```

---

#### C.2.3. Optimizar Session Manager
**Archivo:** `app/services/session_manager.py`

**Mejoras:**

1. **Session Pooling:** Reusar conexiones DB
```python
from sqlalchemy.pool import QueuePool

# En database.py, configurar pool
engine = create_async_engine(
    settings.postgres_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validar conexiones
    pool_recycle=3600,   # Reciclar cada hora
)
```

2. **Lazy Loading:** Cargar datos de sesión bajo demanda
```python
class Session:
    _conversation_history: Optional[List[Message]] = None
    
    async def get_conversation_history(self):
        """Lazy load conversation history."""
        if self._conversation_history is None:
            self._conversation_history = await self._load_history()
        return self._conversation_history
```

3. **Session Cleanup:** Limpiar sesiones expiradas automáticamente
```python
async def cleanup_expired_sessions(self):
    """Remove expired sessions from DB and cache."""
    cutoff = datetime.now() - timedelta(hours=24)
    
    # Cleanup DB
    await self.db.execute(
        delete(SessionModel).where(SessionModel.updated_at < cutoff)
    )
    
    # Cleanup Redis
    cursor = 0
    while True:
        cursor, keys = await self.redis.scan(
            cursor,
            match="session:*",
            count=100
        )
        for key in keys:
            ttl = await self.redis.ttl(key)
            if ttl < 0:  # Sin TTL o expirado
                await self.redis.delete(key)
        if cursor == 0:
            break
```

---

### C.3. Configuración de Monitoring Avanzado (5 min)

#### C.3.1. Agregar Custom Metrics
**Archivo:** `app/services/metrics_service.py`

**Agregar métricas de negocio:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
reservations_total = Counter(
    'hotel_reservations_total',
    'Total reservations created',
    ['status', 'channel', 'room_type']
)

reservation_value = Histogram(
    'hotel_reservation_value_euros',
    'Reservation value in euros',
    buckets=[50, 100, 200, 500, 1000, 2000, 5000]
)

active_conversations = Gauge(
    'hotel_active_conversations',
    'Number of active guest conversations'
)

guest_satisfaction = Histogram(
    'hotel_guest_satisfaction_score',
    'Guest satisfaction score (1-5)',
    buckets=[1, 2, 3, 4, 5]
)

# Usage example
reservations_total.labels(
    status='confirmed',
    channel='whatsapp',
    room_type='deluxe'
).inc()

reservation_value.observe(450.00)
```

---

#### C.3.2. Configurar Alertas de Negocio
**Archivo:** `docker/alertmanager/config.yml`

**Agregar reglas de alertas:**
```yaml
# Agregar a sección route.routes
- match:
    severity: business
  receiver: business-alerts
  group_by: ['alertname', 'channel']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

# Agregar nuevo receiver
receivers:
  - name: business-alerts
    webhook_configs:
      - url: 'http://agente-api:8000/webhooks/alerts/business'
        send_resolved: true
```

**Archivo:** `docker/prometheus/prometheus.yml`

**Agregar reglas de alertas de negocio:**
```yaml
groups:
  - name: business_alerts
    interval: 30s
    rules:
      - alert: HighReservationFailureRate
        expr: |
          (
            sum(rate(hotel_reservations_total{status="failed"}[5m]))
            /
            sum(rate(hotel_reservations_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: business
          team: operations
        annotations:
          summary: "Alta tasa de fallo en reservas ({{ $value | humanizePercentage }})"
          description: "Más del 10% de reservas están fallando en los últimos 5 minutos"

      - alert: LowGuestSatisfaction
        expr: |
          avg(hotel_guest_satisfaction_score) < 3.0
        for: 1h
        labels:
          severity: business
          team: customer_success
        annotations:
          summary: "Satisfacción de huéspedes baja ({{ $value }})"
          description: "La satisfacción promedio está por debajo de 3.0"

      - alert: PMSIntegrationDown
        expr: |
          pms_circuit_breaker_state == 1
        for: 2m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "Integración PMS caída"
          description: "Circuit breaker del PMS está OPEN - sistema degradado"
```

---

#### C.3.3. Crear Dashboard de Negocio en Grafana
**Archivo:** `docker/grafana/dashboards/business_metrics.json`

**Contenido:** (Extracto de dashboard JSON)
```json
{
  "dashboard": {
    "title": "Hotel Business Metrics",
    "panels": [
      {
        "title": "Reservations by Channel",
        "targets": [
          {
            "expr": "sum(rate(hotel_reservations_total[5m])) by (channel)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Average Reservation Value",
        "targets": [
          {
            "expr": "histogram_quantile(0.5, sum(rate(hotel_reservation_value_euros_bucket[5m])) by (le))"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Active Conversations",
        "targets": [
          {
            "expr": "hotel_active_conversations"
          }
        ],
        "type": "gauge"
      },
      {
        "title": "Guest Satisfaction Trend",
        "targets": [
          {
            "expr": "avg(hotel_guest_satisfaction_score)"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

---

## ═══════════════════════════════════════════════════════════════
## RESUMEN Y VALIDACIÓN FINAL
## ═══════════════════════════════════════════════════════════════

### Checklist Final de Validación

#### Fase A: ✅ Validación Completa
- [ ] dev-setup.sh ejecutado exitosamente
- [ ] 8 servicios Docker healthy
- [ ] 16 comandos Makefile funcionan
- [ ] Hot-reload operativo (<2s)
- [ ] Cobertura ≥70%
- [ ] Herramientas web accesibles
- [ ] VALIDATION_REPORT_FASE_A.md creado

#### Fase B: ✅ Herramientas Avanzadas
- [ ] .pre-commit-config.yaml configurado
- [ ] Pre-commit hooks instalados
- [ ] CI local pipeline funcional
- [ ] Benchmarks ejecutándose
- [ ] Baseline de performance establecido
- [ ] 6 comandos nuevos en Makefile funcionan

#### Fase C: ✅ Optimización Infraestructura
- [ ] Reporte de deuda técnica generado
- [ ] PMS Adapter optimizado (cache warming, batch, metrics)
- [ ] Orchestrator optimizado (parallel, circuit breaker, deduplication)
- [ ] Session Manager optimizado (pooling, lazy loading, cleanup)
- [ ] Métricas de negocio implementadas
- [ ] Alertas de negocio configuradas
- [ ] Dashboard Grafana actualizado

---

## 📊 MÉTRICAS DE ÉXITO

### Mejoras Esperadas

#### Performance
- ✅ Tiempo de setup: 30min → 5min (83% reducción)
- ✅ Hot-reload: <2s (vs rebuild 60s+)
- ✅ Tests coverage: +10-15% absoluto
- ✅ CI local: <60s ejecución completa
- ✅ PMS latency: -20-30% con optimizaciones

#### Developer Experience
- ✅ +16 comandos Makefile útiles
- ✅ +8 herramientas de desarrollo integradas
- ✅ +6 hooks automatizados
- ✅ Documentación completa (DEBUGGING.md, VALIDATION_REPORT)

#### Code Quality
- ✅ Linting automático en commits
- ✅ Security scan en CI
- ✅ Type checking integrado
- ✅ Benchmark tracking continuo

#### Observability
- ✅ +4 métricas de negocio
- ✅ +3 alertas críticas
- ✅ Dashboard business completo

---

## 🎯 COMANDOS DE EJECUCIÓN

### Para Ejecutar Plan Completo
```bash
# Fase A: Validación
cd agente-hotel-api
./dev-setup.sh
make dev-up
make dev-status
make test-cov
make quick-check

# Fase B: Herramientas Avanzadas
make pre-commit-install
make pre-commit-run
make ci-local
make benchmark-baseline

# Fase C: Optimización
# (Cambios en código - aplicar manualmente)
make fmt
make lint
make test
make dev-restart

# Validación Final
make full-check
```

---

## 📝 ENTREGABLES

1. **VALIDATION_REPORT_FASE_A.md** - Reporte de validación ambiente dev
2. **.pre-commit-config.yaml** - Configuración hooks pre-commit
3. **scripts/ci-local.sh** - Pipeline CI local
4. **scripts/benchmark-compare.sh** - Comparación benchmarks
5. **tests/benchmarks/test_performance.py** - Suite benchmarks
6. **.playbook/TECH_DEBT_REPORT.md** - Reporte deuda técnica
7. **app/services/*_optimized.py** - Servicios optimizados
8. **docker/grafana/dashboards/business_metrics.json** - Dashboard negocio
9. **docker/prometheus/prometheus.yml** - Alertas actualizadas
10. **Makefile** - +6 comandos nuevos

---

## 🚀 TIEMPO ESTIMADO TOTAL

- **Fase A:** 30-40 minutos
- **Fase B:** 30-40 minutos  
- **Fase C:** 30-40 minutos  
- **TOTAL:** 90-120 minutos (1.5-2 horas)

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Must Have (Obligatorios)
1. ✅ Todos los tests pasan (46/46)
2. ✅ Cobertura ≥70%
3. ✅ CI local exitoso
4. ✅ Sin vulnerabilidades HIGH/CRITICAL
5. ✅ Docker compose dev funcional
6. ✅ Hot-reload operativo

### Should Have (Deseables)
1. ✅ Pre-commit hooks instalados
2. ✅ Benchmarks establecidos
3. ✅ Métricas de negocio implementadas
4. ✅ Documentación actualizada

### Nice to Have (Opcionales)
1. ⚪ Type coverage >80%
2. ⚪ Deuda técnica <10 issues HIGH
3. ⚪ Dashboard business completo

---

**FIN DEL PLAN - LISTO PARA EJECUCIÓN** ✅
