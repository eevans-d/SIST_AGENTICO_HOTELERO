# 📋 CHECKLISTS Y TEMPLATES EJECUTABLES - PLAN DE OPTIMIZACIÓN

**Documento**: Checklists paso a paso + templates  
**Versión**: 1.0  
**Objetivo**: Hacer ejecutable el plan de optimización  

---

## FASE 1: AUDITORÍA INICIAL - CHECKLIST

### 1.1 Escaneo de Dependencias

```bash
# Task ID: AUDIT-001
# Descripción: Verificar vulnerabilidades en dependencias

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Paso 1: Audit de vulnerabilidades
pip-audit --skip-editable

# Paso 2: Análisis de CVE con poetry
poetry audit

# Paso 3: Generar reporte
# Esperado: 0 CRITICAL, 0 HIGH (según copilot-instructions)

# Resultado esperado:
# ✅ python-jose: 3.5.0 (CVE-2024-33663 FIXED)
# ✅ No other HIGH/CRITICAL issues
```

**Checklist**:
```
☐ pip-audit ejecutado sin CRITICAL
☐ poetry audit sin HIGH
☐ CVE-2024-33663 confirmado como FIXED
☐ Reporte guardado: audit_report_$(date +%Y%m%d).json
☐ Dependencias documentadas en AUDIT-DEPENDENCIES.md
```

---

### 1.2 Análisis de Imports Circulares

```bash
# Task ID: AUDIT-002
# Descripción: Detectar imports circulares

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Paso 1: Compilar para detectar imports circulares
python -m py_compile app/main.py
python -m py_compile app/services/orchestrator.py
python -m py_compile app/services/pms_adapter.py
python -m py_compile app/services/message_gateway.py

# Paso 2: Análisis profundo con pipdeptree
pipdeptree --warn fail -p app

# Paso 3: Análisis manual de imports críticos
# Archivos con alto riesgo:
# - app/services/feature_flag_service.py (used by message_gateway)
# - app/services/message_gateway.py (used by orchestrator)
# - app/services/orchestrator.py (uses PMS adapter)

# Ejecutar:
python << 'EOF'
import ast
import os

def find_imports(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    
    return imports

# Check critical files
files = [
    "app/services/orchestrator.py",
    "app/services/pms_adapter.py",
    "app/services/message_gateway.py",
    "app/services/feature_flag_service.py",
]

for file in files:
    if os.path.exists(file):
        imports = find_imports(file)
        print(f"\n{file}:")
        for imp in sorted(set(imports)):
            if imp and imp.startswith("app."):
                print(f"  → {imp}")
EOF
```

**Checklist**:
```
☐ py_compile exitoso para todos los servicios
☐ No imports circulares detectados
☐ Imports analizados y documentados
☐ feature_flag_service no importado en message_gateway (✅ usa DEFAULT_FLAGS)
☐ Reporte: CIRCULAR-IMPORTS-AUDIT.md
```

---

### 1.3 Detección de Código Muerto

```bash
# Task ID: AUDIT-003
# Descripción: Detectar código no utilizado

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Paso 1: Usar vulture para detectar código muerto
pip install vulture
vulture app/ --min-confidence 80 > dead_code_report.txt

# Paso 2: Análisis manual
# Buscar funciones/métodos no usados
grep -r "def " app/ | grep -v "__" | while read line; do
    func=$(echo "$line" | cut -d: -f2 | sed 's/.*def \([^(]*\).*/\1/')
    grep_results=$(grep -r "$func" app/ --exclude-dir=__pycache__ | wc -l)
    if [ $grep_results -lt 3 ]; then
        echo "Posible código muerto: $line"
    fi
done

# Paso 3: Generar reporte
python << 'EOF'
import os
import ast
from collections import defaultdict

class FunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = {}
    
    def visit_FunctionDef(self, node):
        self.functions[node.name] = {
            'line': node.lineno,
            'file': None
        }
        self.generic_visit(node)

def find_unused_functions():
    unused = []
    for root, dirs, files in os.walk('app'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    try:
                        tree = ast.parse(f.read())
                        visitor = FunctionVisitor()
                        visitor.visit(tree)
                        for func, info in visitor.functions.items():
                            if func.startswith('_') or func.startswith('__'):
                                continue
                            # Check if used elsewhere
                            info['file'] = filepath
                            unused.append((filepath, func, info['line']))
                    except:
                        pass
    
    return unused

unused_funcs = find_unused_functions()
with open('dead_code_report.json', 'w') as f:
    import json
    json.dump(unused_funcs, f, indent=2)

print(f"Found {len(unused_funcs)} potentially unused functions")
EOF

cat dead_code_report.txt
```

**Checklist**:
```
☐ vulture scan ejecutado
☐ Reporte de código muerto generado
☐ Funciones no críticas identificadas
☐ Funciones críticas revisadas manualmente
☐ Decisión tomada: eliminar o mantener
☐ Reporte final: DEAD-CODE-AUDIT.md
```

---

### 1.4 Revisión de Patrones Async/Await

```bash
# Task ID: AUDIT-004
# Descripción: Auditar uso correcto de async/await

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

python << 'EOF'
import ast
import os

class AsyncVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
    
    def visit_Call(self, node):
        # Check for async function calls without await
        if isinstance(node.func, ast.Attribute):
            # Check if calling async function
            if hasattr(node.func, 'id') and node.func.id.endswith('_async'):
                if not isinstance(node, ast.Await):
                    self.issues.append({
                        'line': node.lineno,
                        'type': 'missing_await',
                        'func': ast.get_source_segment(open(self.filename).read(), node)
                    })
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        if node.name.startswith('async_'):
            # Check if all external calls awaited
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if not isinstance(child, ast.Await):
                        if hasattr(child.func, 'attr'):
                            if child.func.attr.startswith('get_') or child.func.attr.endswith('_async'):
                                self.issues.append({
                                    'line': child.lineno,
                                    'type': 'potentially_missing_await',
                                    'function': node.name
                                })
        self.generic_visit(node)

async_issues = []
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                try:
                    content = f.read()
                    tree = ast.parse(content)
                    visitor = AsyncVisitor(filepath)
                    visitor.visit(tree)
                    for issue in visitor.issues:
                        async_issues.append({
                            'file': filepath,
                            **issue
                        })
                except:
                    pass

print("ASYNC/AWAIT AUDIT RESULTS:")
print(f"Total issues: {len(async_issues)}\n")
for issue in async_issues[:20]:  # Show first 20
    print(f"  {issue['file']}:{issue['line']} - {issue['type']}")

with open('async_audit.json', 'w') as f:
    import json
    json.dump(async_issues, f, indent=2)
EOF
```

**Checklist**:
```
☐ Escaneo de async/await completado
☐ Todos los await presentes donde necesarios
☐ No hay bloqueos sincronos en contexto async
☐ Reporte: ASYNC-AUDIT.md
☐ Issues críticos escalados
```

---

### 1.5 Análisis de Manejo de Excepciones

```bash
# Task ID: AUDIT-005

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Paso 1: Buscar bare except
grep -r "except:" app/ --include="*.py" | grep -v "__pycache__"

# Paso 2: Buscar exceptions no logueadas
grep -r "except.*:" app/ --include="*.py" -A 1 | grep -v "logger\." | grep -v "raise"

# Paso 3: Script de análisis
python << 'EOF'
import ast
import os

class ExceptionVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
    
    def visit_Try(self, node):
        for handler in node.handlers:
            # Check for bare except
            if handler.type is None:
                self.issues.append({
                    'line': handler.lineno,
                    'type': 'bare_except',
                    'file': self.filename
                })
            
            # Check if exception is handled (should have at least logging or raise)
            if handler.body:
                has_logging = False
                has_raise = False
                
                for stmt in handler.body:
                    if isinstance(stmt, ast.Expr):
                        if isinstance(stmt.value, ast.Call):
                            if hasattr(stmt.value.func, 'attr'):
                                if stmt.value.func.attr in ['error', 'warning', 'exception']:
                                    has_logging = True
                    elif isinstance(stmt, ast.Raise):
                        has_raise = True
                
                if not (has_logging or has_raise):
                    self.issues.append({
                        'line': handler.lineno,
                        'type': 'unhandled_exception',
                        'file': self.filename,
                        'description': 'Exception caught but not logged/raised'
                    })
        
        self.generic_visit(node)

exception_issues = []
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                try:
                    tree = ast.parse(f.read())
                    visitor = ExceptionVisitor(filepath)
                    visitor.visit(tree)
                    exception_issues.extend(visitor.issues)
                except:
                    pass

print("EXCEPTION HANDLING AUDIT:")
print(f"Total issues: {len(exception_issues)}\n")

bare_excepts = [i for i in exception_issues if i['type'] == 'bare_except']
unhandled = [i for i in exception_issues if i['type'] == 'unhandled_exception']

print(f"Bare excepts: {len(bare_excepts)}")
for issue in bare_excepts:
    print(f"  {issue['file']}:{issue['line']}")

print(f"\nUnhandled exceptions: {len(unhandled)}")
for issue in unhandled[:10]:
    print(f"  {issue['file']}:{issue['line']} - {issue['description']}")

with open('exception_audit.json', 'w') as f:
    import json
    json.dump(exception_issues, f, indent=2)
EOF

cat exception_audit.json
```

**Checklist**:
```
☐ No bare excepts encontrados (o documentados)
☐ Todas las excepciones loguean
☐ Excepciones críticas re-raised
☐ Reporte: EXCEPTION-HANDLING-AUDIT.md
```

---

### 1.6 Matriz Final de Riesgos

```bash
# Task ID: AUDIT-006

python << 'EOF'
import json
from datetime import datetime

# Crear matriz de riesgos basada en auditoría
risk_matrix = {
    "audit_date": datetime.now().isoformat(),
    "version": "1.0",
    "findings": [
        {
            "component": "orchestrator.py",
            "function": "process_message()",
            "risk": "Intent not found in dispatcher",
            "severity": "HIGH",
            "probability": "MEDIUM",
            "impact": "CRITICAL",
            "priority": "P0",
            "mitigation": "Use dict.get() with default handler",
            "status": "OPEN"
        },
        {
            "component": "pms_adapter.py",
            "function": "check_availability()",
            "risk": "Circuit breaker state race condition",
            "severity": "MEDIUM",
            "probability": "LOW",
            "impact": "HIGH",
            "priority": "P1",
            "mitigation": "Implement lock-based state machine",
            "status": "OPEN"
        },
        {
            "component": "lock_service.py",
            "function": "acquire_lock()",
            "risk": "Deadlock on lock acquisition",
            "severity": "HIGH",
            "probability": "MEDIUM",
            "impact": "CRITICAL",
            "priority": "P0",
            "mitigation": "Implement timeout + auto-release via Redis TTL",
            "status": "OPEN"
        },
        {
            "component": "session_manager.py",
            "function": "save_session()",
            "risk": "Session data corruption",
            "severity": "MEDIUM",
            "probability": "LOW",
            "impact": "MEDIUM",
            "priority": "P2",
            "mitigation": "Strict validation on load, graceful recovery",
            "status": "OPEN"
        },
        {
            "component": "message_gateway.py",
            "function": "normalize_message()",
            "risk": "Tenant resolution incorrect",
            "severity": "CRITICAL",
            "probability": "MEDIUM",
            "impact": "CRITICAL",
            "priority": "P0",
            "mitigation": "Explicit logging at each fallback step",
            "status": "OPEN"
        }
    ]
}

with open('AUDIT-RISK-MATRIX.json', 'w') as f:
    json.dump(risk_matrix, f, indent=2)

print("Risk matrix creada:")
print(json.dumps(risk_matrix, indent=2))
EOF
```

**Checklist**:
```
☐ Risk matrix completada
☐ Todos P0 identificados
☐ Mitigaciones documentadas
☐ Archivo: AUDIT-RISK-MATRIX.json generado
```

---

## FASE 2: ANÁLISIS DE RIESGOS - CHECKLIST

### 2.1 Crear Scenarios de Fallo

```bash
# Task ID: RISK-001

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

cat > FAILURE-SCENARIOS.md << 'EOF'
# Escenarios de Fallo Crítico

## 1. PMS Complete Unavailability

**Trigger**: PMS service down for >5 minutes

**Expected Behavior**:
1. Circuit breaker trips after 5 failures
2. All availability checks return graceful "unavailable" message
3. App continues to process other requests
4. Alert sent to on-call engineer

**Test**: 
- Stop PMS mock server
- Verify circuit breaker state = OPEN
- Verify error response to guest

## 2. PostgreSQL Connection Pool Exhaustion

**Trigger**: Heavy load causes 20/20 connections in use

**Expected Behavior**:
1. New queries queue with timeout
2. After 30s timeout, graceful error returned
3. Existing connections completed, new requests proceed
4. Alert on pool utilization

**Test**:
- Run load test with high concurrency
- Monitor pool metrics
- Verify recovery after load drops

## 3. Redis Memory Overflow

**Trigger**: Cache grows beyond memory limit

**Expected Behavior**:
1. Redis LRU eviction starts
2. Cache hits decrease, but app continues
3. No data loss, worst case cache misses

**Test**:
- Fill cache with large sessions
- Verify LRU eviction active
- Check app functionality with reduced cache

## 4. Concurrent Bookings Same Room

**Trigger**: Two guests book same room/date simultaneously

**Expected Behavior**:
1. Lock service serializes access
2. First guest gets room
3. Second guest gets graceful "room unavailable" response
4. No overbooking

**Test**:
- Concurrent requests from 2 guests
- Verify only one succeeds
- Verify lock prevents double-booking

## 5. Circuit Breaker Stuck OPEN

**Trigger**: Transient PMS errors trigger CB, but PMS recovers

**Expected Behavior**:
1. CB enters HALF_OPEN after 30s
2. Next request tests PMS
3. If success, CB goes to CLOSED
4. If failure, CB goes back to OPEN

**Test**:
- Trigger 5 PMS errors
- Verify CB OPEN
- Wait 30s
- Verify CB HALF_OPEN
- Verify recovery

## 6-15. [Continue with remaining 10 scenarios...]

EOF

cat FAILURE-SCENARIOS.md
```

**Checklist**:
```
☐ 15 scenarios de fallo documentados
☐ Cada scenario tiene trigger, expected behavior, test
☐ Scenarios cubren todos los componentes críticos
☐ Archivo: FAILURE-SCENARIOS.md
```

---

## FASE 3: REFACTORING CRÍTICO - TEMPLATE

### 3.1 Template para Refactoring de Función Crítica

```bash
# Task ID: REFACTOR-001

cat > REFACTORING-TEMPLATE.md << 'EOF'
# Template para Refactoring de Función Crítica

## Paso 1: Pre-Refactoring Analysis

```python
# Current implementation
async def process_message(self, message: UnifiedMessage):
    intent = self.nlp_engine.detect_intent(message.text)
    handler = self._intent_handlers.get(intent)  # ❌ KeyError risk
    response = handler(message)
    return response
```

**Análisis de riesgos actuales**:
- ❌ No maneja intent no encontrado
- ❌ No valida confidence del NLP
- ❌ No maneja excepciones del handler
- ❌ No tiene timeout
- ❌ No loguea decisiones

## Paso 2: Improved Implementation

```python
async def process_message(
    self,
    message: UnifiedMessage,
    timeout: float = HANDLER_TIMEOUT
) -> Response:
    """Process unified message with resilience.
    
    Args:
        message: Normalized message from any channel
        timeout: Max time to process (seconds)
    
    Returns:
        Response with type (text|audio) and content
    
    Raises:
        ProcessingTimeoutError: If timeout exceeded
        ProcessingError: If unrecoverable error
    """
    
    start_time = time.time()
    
    try:
        # Step 1: Detect intent with validation
        logger.info("intent_detection_start", guest_id=message.sender_id)
        
        try:
            intent_result = await asyncio.wait_for(
                self.nlp_engine.detect_intent(message.text),
                timeout=NLP_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("nlp_timeout", text_length=len(message.text))
            return self._handle_nlp_timeout_response()
        
        if not intent_result:
            logger.warning("no_intent_detected", message_id=message.id)
            return await self._handle_fallback(message)
        
        intent = intent_result.type
        confidence = intent_result.confidence
        
        # Step 2: Validate confidence threshold
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.info(
                "low_confidence_fallback",
                intent=intent,
                confidence=confidence,
                threshold=MIN_CONFIDENCE_THRESHOLD
            )
            return await self._handle_fallback(message)
        
        logger.info("intent_detected", intent=intent, confidence=confidence)
        
        # Step 3: Get handler with safe lookup
        handler = self._intent_handlers.get(intent)
        if not handler:
            logger.warning("handler_not_found", intent=intent)
            return await self._handle_unknown_intent(intent, message)
        
        # Step 4: Execute handler with timeout protection
        logger.info("handler_execution_start", intent=intent)
        
        try:
            response = await asyncio.wait_for(
                handler(message),
                timeout=timeout
            )
            
            # Step 5: Validate response
            if not response:
                logger.error("handler_returned_none", intent=intent)
                return self._handle_error_response(None)
            
            logger.info(
                "handler_success",
                intent=intent,
                duration=time.time() - start_time
            )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error("handler_timeout", intent=intent, timeout=timeout)
            return self._handle_timeout_response()
        
        except PMSError as e:
            # PMS-specific error - circuit breaker may be open
            logger.error("pms_error", intent=intent, error=str(e))
            
            if self.pms_adapter.circuit_breaker.is_open():
                return self._handle_pms_unavailable_response()
            else:
                return self._handle_error_response(e)
        
        except SessionError as e:
            logger.error("session_error", intent=intent, error=str(e))
            return self._handle_session_error_response()
        
        except Exception as e:
            logger.error("handler_unexpected_error", intent=intent, error=str(e))
            return self._handle_error_response(e)
    
    except Exception as e:
        logger.critical("orchestrator_critical_error", error=str(e))
        return self._handle_critical_error_response()
```

## Paso 3: Testing Strategy

```python
# test_orchestrator_refactored.py

@pytest.mark.asyncio
async def test_unknown_intent_fallback():
    """Unknown intent → fallback handler"""
    message = UnifiedMessage(text="xyz unknown intent xyz")
    response = await orchestrator.process_message(message)
    assert response.type == "fallback"
    assert "I didn't understand" in response.text

@pytest.mark.asyncio
async def test_low_confidence_fallback():
    """Low confidence intent → fallback"""
    mock_nlp.return_value = IntentResult(type="booking", confidence=0.3)
    message = UnifiedMessage(text="maybe book a room?")
    response = await orchestrator.process_message(message)
    assert response.type == "fallback"

@pytest.mark.asyncio
async def test_handler_timeout():
    """Handler timeout → graceful response"""
    async def slow_handler(msg):
        await asyncio.sleep(10)
    
    orchestrator._intent_handlers["booking"] = slow_handler
    message = UnifiedMessage(text="book a room")
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            orchestrator.process_message(message, timeout=0.1),
            timeout=1
        )

@pytest.mark.asyncio
async def test_pms_error_circuit_breaker_open():
    """PMS error + CB open → unavailable response"""
    orchestrator.pms_adapter.circuit_breaker.set_open()
    message = UnifiedMessage(text="check availability")
    response = await orchestrator.process_message(message)
    assert "temporarily unavailable" in response.text
```

## Paso 4: Migration Checklist

```
☐ Código refactoreado escrito
☐ Pruebas unitarias pasando (100% de casos)
☐ Pruebas de integración pasando
☐ Code review aprobado
☐ Load testing validado
☐ Benchmark comparado (antes/después)
☐ Rollback plan documentado
☐ PR creado y merged
☐ Deployment realizado
☐ Monitores validados
```

EOF

cat REFACTORING-TEMPLATE.md
```

**Checklist**:
```
☐ Template creado
☐ 5 funciones críticas refactoreadas:
   ☐ orchestrator.process_message()
   ☐ pms_adapter.check_availability()
   ☐ lock_service.acquire_lock()
   ☐ session_manager.get_or_create()
   ☐ message_gateway.normalize_message()
☐ PRs creados para cada refactoring
```

---

## FASE 4: TESTING EXHAUSTIVO - SCAFFOLD

### 4.1 Crear Test Suite para Función Crítica

```bash
# Task ID: TEST-001

mkdir -p /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api/tests/test_suites

cat > /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api/tests/test_suites/test_orchestrator_comprehensive.py << 'EOF'
"""
Comprehensive test suite for Orchestrator
Covers: Normal paths, edge cases, failures, timeouts, etc.
Target: 90%+ coverage of orchestrator.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.models.schemas import Response
from app.exceptions.pms_exceptions import PMSError, PMSTimeoutError

class TestOrchestratorProcessMessage:
    """Test orchestrator.process_message() - CRITICAL FUNCTION"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator with mocks"""
        orch = Orchestrator()
        orch.nlp_engine = AsyncMock()
        orch.pms_adapter = AsyncMock()
        orch.session_manager = AsyncMock()
        orch._intent_handlers = {}
        return orch
    
    @pytest.mark.asyncio
    async def test_happy_path_availability_check(self, orchestrator):
        """Happy path: availability check succeeds"""
        # Setup
        message = UnifiedMessage(
            text="check availability for 2 rooms",
            sender_id="guest-123",
            channel="whatsapp"
        )
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="check_availability",
            confidence=0.95
        )
        
        async def mock_handler(msg):
            return Response(type="text", content={"text": "Here's availability..."})
        
        orchestrator._intent_handlers["check_availability"] = mock_handler
        
        # Execute
        response = await orchestrator.process_message(message)
        
        # Assert
        assert response.type == "text"
        assert "availability" in response.content["text"]
    
    @pytest.mark.asyncio
    async def test_unknown_intent_returns_fallback(self, orchestrator):
        """Unknown intent → fallback handler"""
        message = UnifiedMessage(text="blah blah unknown")
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="UNKNOWN_INTENT_XYZ",
            confidence=0.5
        )
        
        orchestrator._handle_fallback = AsyncMock(
            return_value=Response(type="text", content={"text": "I didn't understand"})
        )
        
        response = await orchestrator.process_message(message)
        
        assert response.type == "fallback" or "understand" in response.content.get("text", "")
        orchestrator._handle_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_fallback(self, orchestrator):
        """Low confidence NLP → fallback"""
        message = UnifiedMessage(text="maybe book something?")
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="booking",
            confidence=0.25  # Below threshold
        )
        
        orchestrator._handle_fallback = AsyncMock(
            return_value=Response(type="text", content={"text": "Please clarify"})
        )
        
        response = await orchestrator.process_message(message)
        
        orchestrator._handle_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handler_timeout_graceful_response(self, orchestrator):
        """Handler timeout → graceful degradation"""
        message = UnifiedMessage(text="book a room")
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="booking",
            confidence=0.95
        )
        
        async def slow_handler(msg):
            await asyncio.sleep(10)  # Slow!
        
        orchestrator._intent_handlers["booking"] = slow_handler
        orchestrator._handle_timeout_response = MagicMock(
            return_value=Response(type="text", content={"text": "Request timed out"})
        )
        
        # With short timeout, should get timeout response
        with patch('app.services.orchestrator.HANDLER_TIMEOUT', 0.1):
            response = await orchestrator.process_message(message, timeout=0.1)
            assert response is not None  # Should not crash
    
    @pytest.mark.asyncio
    async def test_handler_exception_caught_and_logged(self, orchestrator):
        """Handler exception → caught, not propagated"""
        message = UnifiedMessage(text="book a room")
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="booking",
            confidence=0.95
        )
        
        async def failing_handler(msg):
            raise ValueError("Something went wrong")
        
        orchestrator._intent_handlers["booking"] = failing_handler
        orchestrator._handle_error_response = MagicMock(
            return_value=Response(type="text", content={"text": "Error occurred"})
        )
        
        # Should not raise
        response = await orchestrator.process_message(message)
        
        assert response is not None
        orchestrator._handle_error_response.assert_called()
    
    @pytest.mark.asyncio
    async def test_pms_circuit_breaker_open_graceful_response(self, orchestrator):
        """PMS circuit breaker OPEN → graceful response"""
        message = UnifiedMessage(text="check availability")
        
        orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
            type="check_availability",
            confidence=0.95
        )
        
        # Mock circuit breaker open
        orchestrator.pms_adapter.circuit_breaker = MagicMock()
        orchestrator.pms_adapter.circuit_breaker.is_open.return_value = True
        
        orchestrator._handle_pms_unavailable_response = MagicMock(
            return_value=Response(type="text", content={"text": "PMS temporarily unavailable"})
        )
        
        async def handler_that_needs_pms(msg):
            # Handler should check CB before making PMS calls
            if orchestrator.pms_adapter.circuit_breaker.is_open():
                raise PMSError("Circuit breaker open")
        
        orchestrator._intent_handlers["check_availability"] = handler_that_needs_pms
        
        response = await orchestrator.process_message(message)
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_nlp_timeout_graceful_handling(self, orchestrator):
        """NLP timeout → graceful response"""
        message = UnifiedMessage(text="test")
        
        async def nlp_timeout(*args, **kwargs):
            await asyncio.sleep(10)
        
        orchestrator.nlp_engine.detect_intent = nlp_timeout
        orchestrator._handle_nlp_timeout_response = MagicMock(
            return_value=Response(type="text", content={"text": "Processing timeout"})
        )
        
        with patch('app.services.orchestrator.NLP_TIMEOUT', 0.1):
            response = await orchestrator.process_message(message, timeout=1)
            assert response is not None

# Ejecutar todas las pruebas
# pytest tests/test_suites/test_orchestrator_comprehensive.py -v --tb=short
EOF

echo "✅ Test suite creada"
```

**Checklist**:
```
☐ Test suite para orchestrator.py creada (90%+ coverage)
☐ Test suite para pms_adapter.py creada
☐ Test suite para lock_service.py creada
☐ Test suite para session_manager.py creada
☐ Todas las pruebas pasando
☐ Coverage report generado
☐ Archivo: COVERAGE-REPORT.md
```

---

## RESUMEN DE CHECKLISTS

### AUDIT Phase
- ☐ Dependencias auditadas (CVE, vulnerabilidades)
- ☐ Imports circulares analizados
- ☐ Código muerto identificado
- ☐ Async/await auditado
- ☐ Exception handling revisado
- ☐ Risk matrix creada

### RISK Phase
- ☐ 15 failure scenarios documentados
- ☐ Mitigaciones identificadas
- ☐ Tests para cada scenario creados

### REFACTOR Phase
- ☐ 5 funciones críticas refactoreadas
- ☐ Code review aprobado
- ☐ PRs merged

### TEST Phase
- ☐ Test coverage 85%+
- ☐ Chaos tests implementados
- ☐ Performance benchmarks creados

### PERF Phase
- ☐ Baseline benchmarks creados
- ☐ Optimizaciones implementadas
- ☐ P95 latency <500ms validado

### MONITOR Phase
- ☐ Prometheus metrics definidas
- ☐ Grafana dashboards creados
- ☐ Alertas configuradas
- ☐ Jaeger tracing habilitado

### DOCS Phase
- ☐ 5+ runbooks creados
- ☐ Troubleshooting tree documentado
- ☐ Operational checklist creado

---

**Próximo paso**: Ejecutar Fase 1 - AUDIT
