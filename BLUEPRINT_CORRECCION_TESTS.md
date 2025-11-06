# 🎯 BLUEPRINT: Corrección de Tests de Seguridad

**Fecha inicio**: Noviembre 6, 2025  
**Objetivo**: Lograr 104/104 tests de seguridad passing  
**Tiempo estimado**: 2-3 horas  
**Estado actual**: 12/104 passing (11.5%)  
**Estado objetivo**: 104/104 passing (100%)

---

## 📊 DIAGNÓSTICO INICIAL

### Problema Principal
```
❌ 92 tests failing con error: 404 Not Found
✅ Esperado: 401 Unauthorized (sin token JWT)
🔍 Causa: Routers performance y nlp NO montados en test environment
```

### Tests Afectados
```
tests/auth/test_performance_auth.py    → 70 tests (16 failing por 404)
tests/auth/test_nlp_admin_auth.py      → 22 tests (6 failing por 404)
tests/security/test_metrics_ip_filter.py → 12 tests (12 passing ✅)
```

---

## 📋 CHECKLIST DETALLADO

### FASE 1: ANÁLISIS Y PREPARACIÓN (15 min)

#### 1.1 Verificar estructura actual
- [ ] **Tarea**: Listar archivos en `tests/mocks/`
  ```bash
  ls -la agente-hotel-api/tests/mocks/
  ```
  - **Resultado esperado**: Ver si existe directorio y qué mocks ya existen
  - **Siguiente acción**: Crear directorio si no existe

- [ ] **Tarea**: Revisar `conftest.py` actual
  ```bash
  cat agente-hotel-api/tests/conftest.py | head -100
  ```
  - **Resultado esperado**: Ver fixtures actuales y estructura
  - **Siguiente acción**: Planificar modificaciones

#### 1.2 Identificar dependencias de routers
- [ ] **Tarea**: Revisar imports en `app/routers/performance.py`
  ```bash
  grep -n "app.state\." agente-hotel-api/app/routers/performance.py | head -20
  ```
  - **Resultado esperado**: Lista de servicios usados (performance_optimizer, database_tuner, cache_tuner, etc.)
  - **Siguiente acción**: Documentar servicios a mockear

- [ ] **Tarea**: Revisar imports en `app/routers/nlp.py`
  ```bash
  grep -n "app.state\." agente-hotel-api/app/routers/nlp.py | head -20
  ```
  - **Resultado esperado**: Lista de servicios usados (nlp_service, session_manager, etc.)
  - **Siguiente acción**: Documentar servicios a mockear

---

### FASE 2: CREAR MOCKS DE SERVICIOS (1 hora)

#### 2.1 Crear directorio de mocks
- [ ] **Tarea**: Crear estructura `tests/mocks/`
  ```bash
  mkdir -p agente-hotel-api/tests/mocks
  touch agente-hotel-api/tests/mocks/__init__.py
  ```
  - **Resultado esperado**: Directorio creado
  - **Verificación**: `ls -la agente-hotel-api/tests/mocks/`

#### 2.2 Crear MockPerformanceOptimizer
- [ ] **Tarea**: Crear `tests/mocks/mock_performance_optimizer.py`
  - **Contenido**: Clase con métodos async que retornan datos dummy
  - **Métodos necesarios**:
    - `get_status()` → `{"status": "ok", "metrics": {...}}`
    - `get_metrics()` → `{"cpu": 50, "memory": 60, ...}`
    - `get_optimization_report()` → `{"recommendations": [...]}`
    - `execute_optimization()` → `{"status": "executed"}`
  - **Resultado esperado**: Archivo creado con ~100 líneas
  - **Verificación**: `python -c "from tests.mocks.mock_performance_optimizer import MockPerformanceOptimizer; print('OK')"`

#### 2.3 Crear MockDatabaseTuner
- [ ] **Tarea**: Crear `tests/mocks/mock_database_tuner.py`
  - **Contenido**: Clase con métodos async
  - **Métodos necesarios**:
    - `get_report()` → `{"status": "healthy", "queries": [...]}`
    - `optimize()` → `{"optimizations_applied": 0}`
  - **Resultado esperado**: Archivo creado con ~50 líneas
  - **Verificación**: Import exitoso

#### 2.4 Crear MockCacheTuner
- [ ] **Tarea**: Crear `tests/mocks/mock_cache_tuner.py`
  - **Contenido**: Clase con métodos async
  - **Métodos necesarios**:
    - `get_report()` → `{"hit_rate": 0.85, "keys": 1000}`
    - `optimize()` → `{"invalidated_keys": 0}`
  - **Resultado esperado**: Archivo creado con ~50 líneas
  - **Verificación**: Import exitoso

#### 2.5 Crear MockScalingService
- [ ] **Tarea**: Crear `tests/mocks/mock_scaling_service.py`
  - **Contenido**: Clase con métodos async
  - **Métodos necesarios**:
    - `get_status()` → `{"services": {...}}`
    - `evaluate()` → `{"recommendations": [...]}`
    - `execute()` → `{"status": "executed"}`
    - `update_rule()` → `{"updated": True}`
  - **Resultado esperado**: Archivo creado con ~80 líneas
  - **Verificación**: Import exitoso

#### 2.6 Crear MockAlertingService
- [ ] **Tarea**: Crear `tests/mocks/mock_alerting_service.py`
  - **Contenido**: Clase con métodos async
  - **Métodos necesarios**:
    - `get_alerts()` → `{"alerts": []}`
    - `resolve_alert()` → `{"resolved": True}`
  - **Resultado esperado**: Archivo creado con ~40 líneas
  - **Verificación**: Import exitoso

#### 2.7 Crear MockNLPService
- [ ] **Tarea**: Crear `tests/mocks/mock_nlp_service.py`
  - **Contenido**: Clase con métodos async
  - **Métodos necesarios**:
    - `get_sessions()` → `{"sessions": []}`
    - `cleanup_sessions()` → `{"deleted": 0}`
  - **Resultado esperado**: Archivo creado con ~40 líneas
  - **Verificación**: Import exitoso

#### 2.8 Crear mock consolidado
- [ ] **Tarea**: Actualizar `tests/mocks/__init__.py`
  - **Contenido**: Exports de todos los mocks
  ```python
  from .mock_performance_optimizer import MockPerformanceOptimizer
  from .mock_database_tuner import MockDatabaseTuner
  from .mock_cache_tuner import MockCacheTuner
  from .mock_scaling_service import MockScalingService
  from .mock_alerting_service import MockAlertingService
  from .mock_nlp_service import MockNLPService
  
  __all__ = [
      "MockPerformanceOptimizer",
      "MockDatabaseTuner",
      "MockCacheTuner",
      "MockScalingService",
      "MockAlertingService",
      "MockNLPService",
  ]
  ```
  - **Resultado esperado**: Archivo actualizado
  - **Verificación**: `python -c "from tests.mocks import *; print('OK')"`

---

### FASE 3: ACTUALIZAR CONFTEST.PY (30 min)

#### 3.1 Agregar imports de mocks
- [ ] **Tarea**: Agregar al inicio de `conftest.py`
  ```python
  from tests.mocks import (
      MockPerformanceOptimizer,
      MockDatabaseTuner,
      MockCacheTuner,
      MockScalingService,
      MockAlertingService,
      MockNLPService,
  )
  ```
  - **Ubicación**: Después de imports existentes (línea ~12)
  - **Resultado esperado**: Sin errores de import
  - **Verificación**: `python -m pytest --collect-only tests/auth/`

#### 3.2 Modificar fixture test_app
- [ ] **Tarea**: Actualizar fixture `test_app` en `conftest.py`
  ```python
  @pytest_asyncio.fixture
  async def test_app():
      from app.main import app
      
      # Inyectar mocks de servicios de performance
      app.state.performance_optimizer = MockPerformanceOptimizer()
      app.state.database_tuner = MockDatabaseTuner()
      app.state.cache_tuner = MockCacheTuner()
      app.state.scaling_service = MockScalingService()
      app.state.alerting_service = MockAlertingService()
      
      # Inyectar mocks de servicios de NLP
      app.state.nlp_service = MockNLPService()
      
      # Rate limiter en memoria
      app.state.limiter = Limiter(
          key_func=get_remote_address, 
          storage_uri="memory://"
      )
      
      return app
  ```
  - **Ubicación**: Reemplazar fixture existente (línea ~62-68)
  - **Resultado esperado**: Fixture actualizado
  - **Verificación**: Tests recolectan correctamente

#### 3.3 Agregar fixture test_client
- [ ] **Tarea**: Crear fixture `test_client` usando `test_app`
  ```python
  @pytest_asyncio.fixture
  async def test_client(test_app):
      async with httpx.AsyncClient(
          app=test_app, 
          base_url="http://test"
      ) as client:
          yield client
  ```
  - **Ubicación**: Después de fixture `test_app`
  - **Resultado esperado**: Fixture creado
  - **Verificación**: Tests pueden usar `test_client`

---

### FASE 4: VALIDACIÓN INCREMENTAL (30 min)

#### 4.1 Validar tests de metrics (baseline)
- [ ] **Tarea**: Ejecutar tests de metrics IP filter
  ```bash
  cd agente-hotel-api
  pytest tests/security/test_metrics_ip_filter.py -v
  ```
  - **Resultado esperado**: 12/12 passing ✅ (ya funcionan)
  - **Si falla**: Revisar que no rompimos nada en conftest

#### 4.2 Validar 1 test de performance
- [ ] **Tarea**: Ejecutar un solo test de performance
  ```bash
  pytest tests/auth/test_performance_auth.py::test_endpoints_require_authentication[GET-/api/v1/performance/status] -vv
  ```
  - **Resultado esperado**: 
    - ❌ Antes: `404 Not Found`
    - ✅ Después: `401 Unauthorized` (PASS)
  - **Si falla con 404**: Verificar que routers están montados
  - **Si falla con otro error**: Revisar mock methods

#### 4.3 Validar todos los tests de performance
- [ ] **Tarea**: Ejecutar suite completa de performance auth
  ```bash
  pytest tests/auth/test_performance_auth.py -v
  ```
  - **Resultado esperado**: 70/70 passing ✅
  - **Si fallan algunos**: Revisar mocks faltantes o métodos incorrectos

#### 4.4 Validar 1 test de NLP
- [ ] **Tarea**: Ejecutar un solo test de NLP admin
  ```bash
  pytest tests/auth/test_nlp_admin_auth.py::test_admin_endpoints_require_authentication[GET-/api/nlp/admin/sessions] -vv
  ```
  - **Resultado esperado**: 
    - ❌ Antes: `404 Not Found`
    - ✅ Después: `401 Unauthorized` (PASS)
  - **Si falla**: Revicar MockNLPService

#### 4.5 Validar todos los tests de NLP
- [ ] **Tarea**: Ejecutar suite completa de NLP admin auth
  ```bash
  pytest tests/auth/test_nlp_admin_auth.py -v
  ```
  - **Resultado esperado**: 22/22 passing ✅
  - **Si fallan algunos**: Revisar mocks o fixtures

#### 4.6 Validación completa de seguridad
- [ ] **Tarea**: Ejecutar TODOS los tests de autenticación
  ```bash
  pytest tests/auth/ tests/security/test_metrics_ip_filter.py -v --tb=short
  ```
  - **Resultado esperado**: 104/104 passing ✅
  - **Capturar output**: Guardar para documentación
  - **Si fallan**: Revisar errores específicos y corregir

---

### FASE 5: DOCUMENTACIÓN Y COMMIT (30 min)

#### 5.1 Capturar evidencia
- [ ] **Tarea**: Generar reporte de coverage
  ```bash
  pytest tests/auth/ tests/security/test_metrics_ip_filter.py -v --cov=app.routers --cov-report=term-missing > test_results.txt
  ```
  - **Resultado esperado**: Archivo con resultados + coverage
  - **Guardar**: Para incluir en documentación

#### 5.2 Actualizar SECURITY_HARDENING_REPORT.md
- [ ] **Tarea**: Agregar sección "Test Validation" al reporte
  - **Contenido**:
    - Resultados de tests (104/104 passing)
    - Coverage de routers protegidos
    - Evidencia de 401/403 funcionando correctamente
  - **Ubicación**: Nueva sección al final del documento
  - **Resultado esperado**: Documento actualizado

#### 5.3 Actualizar deployment readiness
- [ ] **Tarea**: Actualizar métricas en `FINAL_WORK_SUMMARY.md`
  - **Cambios**:
    - Tests de Seguridad: 12/104 → 104/104 ✅
    - Deployment Readiness: 9.3/10 → 9.7/10
  - **Resultado esperado**: Métricas actualizadas

#### 5.4 Crear resumen de cambios
- [ ] **Tarea**: Listar archivos modificados
  ```bash
  git status --short
  ```
  - **Resultado esperado**: 
    - 7 archivos nuevos (mocks)
    - 1 archivo modificado (conftest.py)
    - 2 archivos actualizados (docs)
  - **Verificación**: Revisar que no haya archivos no deseados

#### 5.5 Commit de cambios
- [ ] **Tarea**: Hacer commit con mensaje descriptivo
  ```bash
  git add tests/mocks/ tests/conftest.py docs/SECURITY_HARDENING_REPORT.md
  git commit -m "test(security): Corregir fixtures para tests de autenticación

- Crear mocks de servicios (7 archivos en tests/mocks/)
  - MockPerformanceOptimizer, MockDatabaseTuner, MockCacheTuner
  - MockScalingService, MockAlertingService, MockNLPService
- Actualizar conftest.py para inyectar mocks en app.state
- Resolver 404 → 401 en tests de performance y nlp auth
- Resultados: 104/104 tests de seguridad passing ✅
- Deployment Readiness: 9.3/10 → 9.7/10 (+4.3%)"
  ```
  - **Resultado esperado**: Commit creado
  - **Verificación**: `git log --oneline -1`

#### 5.6 Push a GitHub
- [ ] **Tarea**: Subir cambios al repositorio
  ```bash
  git push origin main
  ```
  - **Resultado esperado**: Push exitoso
  - **Verificación**: Revisar en GitHub web

---

## 🎯 CRITERIOS DE ÉXITO

### Métricas Objetivo
- [x] **Tests passing**: 104/104 (100%) ✅
- [x] **Coverage routers protegidos**: >85%
- [x] **Deployment Readiness**: 9.7/10
- [x] **Sin regresiones**: Tests existentes siguen pasando
- [x] **Documentación actualizada**: Evidencia en reporte

### Validaciones Finales
- [ ] ✅ `pytest tests/auth/test_performance_auth.py` → 70/70 passing
- [ ] ✅ `pytest tests/auth/test_nlp_admin_auth.py` → 22/22 passing
- [ ] ✅ `pytest tests/security/test_metrics_ip_filter.py` → 12/12 passing
- [ ] ✅ Sin errores 404 en tests de autenticación
- [ ] ✅ Tokens JWT inválidos retornan 403 Forbidden
- [ ] ✅ Requests sin token retornan 401 Unauthorized

---

## 📊 TRACKING DE PROGRESO

### Estado Inicial
```
Tests de Seguridad: 12/104 passing (11.5%)
Deployment Readiness: 9.3/10
Blocker para Staging: ✅ SÍ
```

### Estado Actual (actualizar en tiempo real)
```
Fase 1: [ ] PENDIENTE (0/2 tareas)
Fase 2: [ ] PENDIENTE (0/8 tareas)
Fase 3: [ ] PENDIENTE (0/3 tareas)
Fase 4: [ ] PENDIENTE (0/6 tareas)
Fase 5: [ ] PENDIENTE (0/6 tareas)

TOTAL: 0/25 tareas completadas (0%)
```

### Estado Final (objetivo)
```
Tests de Seguridad: 104/104 passing (100%) ✅
Deployment Readiness: 9.7/10 (+4.3%)
Blocker para Staging: ❌ NO
```

---

## 🚨 CONTINGENCIAS

### Problema 1: Import errors en mocks
**Síntoma**: `ModuleNotFoundError: No module named 'tests.mocks'`  
**Solución**:
1. Verificar que `tests/mocks/__init__.py` existe
2. Ejecutar `python -c "import sys; print(sys.path)"`
3. Agregar `PYTHONPATH=. pytest ...`

### Problema 2: Tests siguen retornando 404
**Síntoma**: Después de agregar mocks, tests aún fallan con 404  
**Solución**:
1. Verificar que `app.state.X = MockX()` se ejecuta antes de tests
2. Revisar que routers están incluidos en `app.main`
3. Debug: Agregar `print(app.routes)` en fixture

### Problema 3: Errores en métodos de mocks
**Síntoma**: `AttributeError: 'MockX' object has no attribute 'method_name'`  
**Solución**:
1. Revisar router para ver qué métodos se llaman
2. Agregar métodos faltantes al mock
3. Asegurar que métodos son `async def` si se esperan coroutines

### Problema 4: Tests pasan pero con warnings
**Síntoma**: Tests passing pero muchos warnings  
**Solución**:
1. Revisar warnings específicos
2. Filtrar warnings de librerías externas en `pytest.ini`
3. Corregir deprecations en código propio

---

## 📅 TIMELINE ESTIMADO

| Fase | Duración | Inicio | Fin | Status |
|------|----------|--------|-----|--------|
| Fase 1: Análisis | 15 min | - | - | ⏸️ PENDIENTE |
| Fase 2: Mocks | 60 min | - | - | ⏸️ PENDIENTE |
| Fase 3: Conftest | 30 min | - | - | ⏸️ PENDIENTE |
| Fase 4: Validación | 30 min | - | - | ⏸️ PENDIENTE |
| Fase 5: Documentación | 30 min | - | - | ⏸️ PENDIENTE |
| **TOTAL** | **2.5-3h** | - | - | ⏸️ PENDIENTE |

---

## 🔗 SIGUIENTE PASO DESPUÉS DE ESTO

Una vez completado este blueprint (104/104 tests passing):

1. **Configurar `.env` de staging** (30 min)
2. **Deploy a staging** (2-3 horas)
3. **Smoke tests en staging** (1 hora)
4. **Monitoreo 24h** (1 día)
5. **Configurar `.env` producción** (30 min)
6. **Deploy a producción** (2-3 horas)

---

**Elaborado por**: AI Agent  
**Fecha**: Noviembre 6, 2025  
**Versión**: 1.0  
**Estado**: ⏸️ LISTO PARA EJECUCIÓN
