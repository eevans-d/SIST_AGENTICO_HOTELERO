# P003: Matriz de Cobertura de Testing

**Fecha**: 2025-10-14  
**Proyecto**: Agente Hotelero IA  
**Tipo Sistema**: Agente IA Conversacional + PMS Integration  
**Stack Testing**: pytest + Playwright + k6 + custom agent tests

---

## 📊 1. MATRIZ DE COBERTURA ACTUAL VS OBJETIVO

| Categoría | Subcategoría | Actual | Objetivo | Gap | Prioridad | Estado |
|-----------|--------------|--------|----------|-----|-----------|--------|
| **UNIT TESTS** | Services | 15 tests | 50 tests | 35 | 🔴 Alta | ⏳ |
| | Models/Schemas | 0 tests | 20 tests | 20 | 🔴 Alta | ❌ |
| | Utils/Core | 5 tests | 15 tests | 10 | 🟡 Media | ⏳ |
| | **Subtotal Unit** | **20** | **85** | **65** | | **24%** |
| **INTEGRATION** | API Endpoints | 0 tests | 25 tests | 25 | 🔴 Alta | ❌ |
| | Database | 0 tests | 10 tests | 10 | 🔴 Alta | ❌ |
| | External Services | 3 tests | 15 tests | 12 | 🔴 Alta | ⏳ |
| | **Subtotal Integration** | **3** | **50** | **47** | | **6%** |
| **E2E** | Critical Flows | 5 tests | 15 tests | 10 | 🔴 Alta | ⏳ |
| | User Journeys | 0 tests | 10 tests | 10 | 🟡 Media | ❌ |
| | Error Scenarios | 0 tests | 8 tests | 8 | 🟡 Media | ❌ |
| | **Subtotal E2E** | **5** | **33** | **28** | | **15%** |
| **LOAD** | Baseline | 0 tests | 3 tests | 3 | 🟡 Media | ❌ |
| | Spike | 0 tests | 2 tests | 2 | 🟡 Media | ❌ |
| | Soak | 0 tests | 1 test | 1 | 🟢 Baja | ❌ |
| | **Subtotal Load** | **0** | **6** | **6** | | **0%** |
| **SECURITY** | Input Validation | 0 tests | 10 tests | 10 | 🔴 Alta | ❌ |
| | Authentication | 2 tests | 8 tests | 6 | 🔴 Alta | ⏳ |
| | Authorization | 0 tests | 8 tests | 8 | 🔴 Alta | ❌ |
| | Prompt Injection | 0 tests | 20 tests | 20 | 🔴 Alta | ❌ |
| | PII Leakage | 0 tests | 5 tests | 5 | 🔴 Alta | ❌ |
| | **Subtotal Security** | **2** | **51** | **49** | | **4%** |
| **AGENT-SPECIFIC** | Consistency | 0 tests | 10 tests | 10 | 🔴 Alta | ❌ |
| | Loop Detection | 0 tests | 5 tests | 5 | 🔴 Alta | ❌ |
| | Memory Leaks | 0 tests | 5 tests | 5 | 🟡 Media | ❌ |
| | Context Management | 0 tests | 8 tests | 8 | 🟡 Media | ❌ |
| | Tool Execution | 0 tests | 10 tests | 10 | 🔴 Alta | ❌ |
| | **Subtotal Agent** | **0** | **38** | **38** | | **0%** |
| | | | | | | |
| **TOTAL** | | **30** | **263** | **233** | | **11%** |

### Cobertura de Código (pytest-cov)

```
Name                          Stmts   Miss  Cover
------------------------------------------------
app/services/orchestrator.py    150     80    47%
app/services/nlp_engine.py      180    120    33%
app/services/pms_adapter.py      120     55    54%
app/services/whatsapp_client.py  160    140    13%
app/services/gmail_client.py     140    130     7%
app/services/alert_service.py     85     12    86%
app/core/security.py              90     60    33%
------------------------------------------------
TOTAL                           2450   1385    44%
```

**Target**: 70% overall, 85% en servicios críticos

---

## 🚨 2. FLUJOS CRÍTICOS SIN COBERTURA (Top 10)

### 1. **Conversación Multi-Turn con Contexto** ❌ CRÍTICO
- **Descripción**: Usuario mantiene conversación de 5+ mensajes con el agente
- **Componentes**: NLPEngine → Orchestrator → SessionManager → WhatsApp
- **Riesgos**: Pérdida de contexto, respuestas incoherentes, loops
- **Cobertura Actual**: 0%
- **Tests Necesarios**: E2E + Agent Consistency
- **Esfuerzo**: 2 días

### 2. **Prompt Injection en Input del Usuario** ❌ CRÍTICO
- **Descripción**: Intentos maliciosos de manipular el agente
- **Componentes**: NLPEngine input sanitization
- **Riesgos**: System prompt leakage, jailbreak, data exfiltration
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Security suite (20 tests)
- **Esfuerzo**: 3 días

### 3. **PMS Fallback Chain (Circuit Breaker)** ⚠️ ALTO
- **Descripción**: QloApps falla, sistema degrada gracefully
- **Componentes**: PMSAdapter → CircuitBreaker → Mock PMS
- **Riesgos**: Timeouts, usuarios bloqueados, pérdida de reservas
- **Cobertura Actual**: 54% (solo unit)
- **Tests Necesarios**: Integration + E2E fallback
- **Esfuerzo**: 2 días

### 4. **Audio Processing End-to-End** ⚠️ ALTO
- **Descripción**: Mensaje de voz WhatsApp → STT → Agente → TTS → Respuesta
- **Componentes**: WhatsAppClient → AudioProcessor → Whisper → NLP
- **Riesgos**: Transcripción incorrecta, idioma erróneo, fallos de audio
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Integration + E2E audio
- **Esfuerzo**: 3 días

### 5. **Memory Leak en Sesiones Largas** ⚠️ ALTO
- **Descripción**: Memoria crece indefinidamente en conversaciones >30 min
- **Componentes**: SessionManager → Redis → Contexto LLM
- **Riesgos**: OOM kills, degradación de performance
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Memory profiling tests
- **Esfuerzo**: 2 días

### 6. **Loop Detection en Razonamiento del Agente** ⚠️ ALTO
- **Descripción**: Agente entra en ciclo infinito de razonamiento
- **Componentes**: Orchestrator → NLPEngine loop detector
- **Riesgos**: Costos LLM descontrolados, timeouts, UX horrible
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Agent loop tests + circuit breaker
- **Esfuerzo**: 2 días

### 7. **Rate Limiting bajo Carga** 🟡 MEDIO
- **Descripción**: Sistema maneja 100+ requests concurrentes
- **Componentes**: SlowAPI + Redis rate limiter
- **Riesgos**: Bloqueo legítimo de usuarios, bypass de rate limits
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Load tests (k6)
- **Esfuerzo**: 1 día

### 8. **PII Leakage en Logs/Respuestas** 🟡 MEDIO
- **Descripción**: Emails, teléfonos, DNI expuestos en logs
- **Componentes**: Security filters + Logging middleware
- **Riesgos**: Violación GDPR, multas, pérdida confianza
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Security PII tests
- **Esfuerzo**: 1 día

### 9. **Gmail Integration Complete Flow** 🟡 MEDIO
- **Descripción**: Email → Parse → Agente → Respuesta automática
- **Componentes**: GmailClient → Orchestrator → TemplateService
- **Riesgos**: Emails perdidos, respuestas incorrectas, spam
- **Cobertura Actual**: 7%
- **Tests Necesarios**: Integration + E2E email
- **Esfuerzo**: 2 días

### 10. **Database Connection Pool Exhaustion** 🟡 MEDIO
- **Descripción**: Pool de PostgreSQL se agota bajo carga
- **Componentes**: SQLAlchemy AsyncEngine → Connection pool
- **Riesgos**: "Too many connections", timeouts, downtime
- **Cobertura Actual**: 0%
- **Tests Necesarios**: Load + Chaos tests
- **Esfuerzo**: 1 día

---

## 📅 3. PLAN DE IMPLEMENTACIÓN (4 Semanas)

### 🔴 SEMANA 1: Quick Wins - Security Basics (40h)

**Objetivo**: Eliminar riesgos de seguridad más críticos

#### Tests a Crear:

1. **`tests/security/test_prompt_injection.py`** (12h)
   - 20 casos de inyección de prompt
   - Direct, indirect, jailbreak, encoding
   - Validar filtrado y respuestas seguras

2. **`tests/security/test_pii_leakage.py`** (6h)
   - Regex para detectar PII en logs
   - Email, teléfono, DNI, tarjetas
   - Validar redacción automática

3. **`tests/security/test_input_validation.py`** (6h)
   - XSS, SQL injection, path traversal
   - Payloads maliciosos en campos de texto
   - Sanitización de HTML

4. **`tests/unit/test_security_filters.py`** (4h)
   - Unit tests de `app/core/security.py`
   - Validadores, sanitizers, encoders

5. **`tests/e2e/critical/test_auth_flow.spec.ts`** (8h)
   - Login, logout, refresh token
   - CSRF protection
   - Session hijacking attempts

6. **CI Integration** (4h)
   - Añadir security tests a pipeline
   - Fail on critical security issues

**Entregable**: 45+ security tests, CI configurado

---

### ⚡ SEMANA 2: Agent-Specific Tests (40h)

**Objetivo**: Validar comportamiento correcto del agente IA

#### Tests a Crear:

1. **`tests/agent/test_consistency.py`** (8h)
   ```python
   # Validar que respuestas son consistentes
   # Métricas: similitud >85%, std <0.15
   # 10 escenarios con 100 ejecuciones cada uno
   ```

2. **`tests/agent/test_loop_detection.py`** (6h)
   ```python
   # Detectar ciclos de razonamiento
   # Circuit breaker a los 20 pasos
   # Métricas: loops detectados, tiempo de detección
   ```

3. **`tests/agent/test_memory_leaks.py`** (10h)
   ```python
   # Monitorear memoria con tracemalloc + psutil
   # Sesiones largas (30 min simulados)
   # Validar liberación de memoria al cerrar sesión
   ```

4. **`tests/agent/test_context_management.py`** (8h)
   ```python
   # Contexto se mantiene en multi-turn
   # Máximos de tokens respetados
   # Truncamiento inteligente de contexto
   ```

5. **`tests/agent/test_tool_execution.py`** (6h)
   ```python
   # Agente llama herramientas correctamente
   # PMS, email, WhatsApp tools
   # Manejo de errores de tools
   ```

6. **Monitoring Integration** (2h)
   - Métricas Prometheus para agent behavior
   - Alertas para anomalías

**Entregable**: 38 agent tests, monitoreo configurado

---

### 🚀 SEMANA 3: Integration & E2E Core (40h)

**Objetivo**: Cobertura de flujos críticos end-to-end

#### Tests a Crear:

1. **`tests/e2e/critical/test_conversation_multitur n.spec.ts`** (8h)
   ```typescript
   // Usuario tiene conversación de 5+ mensajes
   // Contexto se mantiene
   // Tiempos de respuesta <3s
   ```

2. **`tests/e2e/critical/test_audio_processing.spec.ts`** (10h)
   ```typescript
   // Mensaje de voz → STT → Agente → TTS → Respuesta
   // Idiomas: ES, EN, PT
   // Validar transcripción y síntesis
   ```

3. **`tests/integration/test_pms_fallback_chain.py`** (8h)
   ```python
   # QloApps down → Mock PMS
   # Circuit breaker funciona
   # Degradación graceful
   ```

4. **`tests/integration/test_gmail_complete_flow.py`** (8h)
   ```python
   # Email recibido → Parse → Agente → Respuesta
   # Attachments handling
   # Spam detection
   ```

5. **`tests/integration/test_database_operations.py`** (4h)
   ```python
   # CRUD completo de sesiones, locks, audits
   # Transacciones, rollbacks
   # Connection pool behavior
   ```

6. **Playwright Configuration** (2h)
   - `playwright.config.ts` con retries
   - Fixtures para auth, mocks
   - Reportes HTML

**Entregable**: 40 integration + E2E tests

---

### 📊 SEMANA 4: Performance & Monitoring (40h)

**Objetivo**: Validar performance bajo carga

#### Tests a Crear:

1. **`tests/load/k6-scenarios.js`** (12h)
   ```javascript
   // Normal load: 50 VUs por 10 min
   // Spike: 0→200 VUs en 1 min
   // Soak: 30 VUs por 2 horas
   // SLOs: P95 <2s, error rate <1%
   ```

2. **`tests/load/k6-conversation-flow.js`** (6h)
   ```javascript
   // Simular conversaciones reales
   // Multi-turn, context, tools
   // Medir tokens, costos, latencia
   ```

3. **`tests/chaos/test_resilience.py`** (8h)
   ```python
   # Failover de DB
   # Redis connection loss
   # LLM timeouts
   # Validar recuperación automática
   ```

4. **`tests/performance/test_token_efficiency.py`** (6h)
   ```python
   # Medir tokens por conversación
   # Comparar con baseline
   # Detectar regresiones >20%
   ```

5. **Dashboard & Alerts** (8h)
   - Grafana dashboard de tests
   - Alertas para fallos de tests
   - Métricas de coverage trending

**Entregable**: 6 load tests, chaos tests, monitoring

---

## 📝 4. TEMPLATES INICIALES

### E2E Test Template (Playwright)

<function_calls>
<invoke name="create_file">
<parameter name="content">import { test, expect, Page } from '@playwright/test';

/**
 * Template para tests E2E de flujos críticos del agente
 * 
 * Setup:
 * npm install --save-dev @playwright/test
 * npx playwright install
 */

test.describe('Flujo Crítico: [NOMBRE DEL FLUJO]', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    
    // Configurar mocks si es necesario
    await page.route('**/api/pms/**', route => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ available: true })
      });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Usuario inicia conversación y recibe respuesta coherente', async () => {
    const startTime = Date.now();
    
    // Acción del usuario
    const messageInput = page.getByTestId('message-input');
    await messageInput.fill('¿Cuál es el estado de mi reserva #12345?');
    
    const sendButton = page.getByTestId('send-button');
    await sendButton.click();

    // Esperar respuesta del agente
    const agentResponse = page.getByTestId('agent-response').first();
    await expect(agentResponse).toBeVisible({ timeout: 5000 });

    // Validar contenido de la respuesta
    const responseText = (await agentResponse.textContent()) || '';
    expect(responseText.toLowerCase()).toContain('reserva');
    expect(responseText.length).toBeGreaterThan(20);

    // Validar tiempo de respuesta
    const responseTime = Date.now() - startTime;
    expect(responseTime).toBeLessThan(3000); // <3s SLO

    // Capturar screenshot para debugging
    await page.screenshot({ path: 'test-results/conversation-flow.png' });
  });

  test('Conversación multi-turn mantiene contexto', async () => {
    // Mensaje 1
    await page.getByTestId('message-input').fill('Hola, necesito ayuda con una reserva');
    await page.getByTestId('send-button').click();
    await page.getByTestId('agent-response').first().waitFor();

    // Mensaje 2 (referencia implícita a mensaje 1)
    await page.getByTestId('message-input').fill('¿Cuánto cuesta?');
    await page.getByTestId('send-button').click();

    // Validar que el agente entendió el contexto
    const responses = page.getByTestId('agent-response');
    await expect(responses).toHaveCount(2);
    
    const secondResponse = (await responses.nth(1).textContent()) || '';
    expect(secondResponse.toLowerCase()).not.toContain('no entiendo');
    expect(secondResponse.toLowerCase()).toMatch(/precio|costo|valor/);
  });

  test('Manejo graceful de errores del backend', async () => {
    // Simular error de red
    await page.route('**/api/chat', route => route.abort('failed'));

    await page.getByTestId('message-input').fill('Test error handling');
    await page.getByTestId('send-button').click();

    // Validar mensaje de error amigable
    const errorMessage = page.getByTestId('error-message');
    await expect(errorMessage).toBeVisible({ timeout: 2000 });
    await expect(errorMessage).toContainText(/intenta.*nuevamente|error.*temporal/i);
    
    // Validar que el botón de retry aparece
    const retryButton = page.getByTestId('retry-button');
    await expect(retryButton).toBeVisible();
  });

  test('Performance: P95 latencia bajo carga simulada', async () => {
    const latencies: number[] = [];
    const iterations = 20;

    for (let i = 0; i < iterations; i++) {
      const start = Date.now();
      
      await page.getByTestId('message-input').fill(`Mensaje de prueba ${i}`);
      await page.getByTestId('send-button').click();
      await page.getByTestId('agent-response').nth(i).waitFor({ timeout: 5000 });
      
      latencies.push(Date.now() - start);
      
      // Pequeña pausa entre requests
      await page.waitForTimeout(100);
    }

    // Calcular P95
    latencies.sort((a, b) => a - b);
    const p95Index = Math.floor(latencies.length * 0.95);
    const p95 = latencies[p95Index];

    console.log(`P95 Latency: ${p95}ms`);
    console.log(`Avg Latency: ${latencies.reduce((a, b) => a + b) / latencies.length}ms`);

    expect(p95).toBeLessThan(2000); // SLO: P95 <2s
  });
});
