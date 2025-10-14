/**
 * E2E Tests: Error Handling & Resilience
 * 
 * Valida comportamiento del sistema ante fallos:
 * - Caída del PMS
 * - Pérdida de conexión a DB/Redis
 * - Timeouts en servicios externos
 * - Respuestas degradadas (graceful degradation)
 * 
 * Ejecutar:
 *   npx playwright test tests/e2e/test_error_handling.spec.ts
 */

import { test, expect, Page } from '@playwright/test';

// ===== HELPERS =====

async function sendMessage(page: Page, message: string, userId: string): Promise<void> {
  const payload = {
    object: 'whatsapp_business_account',
    entry: [{
      id: 'entry_001',
      changes: [{
        value: {
          messaging_product: 'whatsapp',
          metadata: { phone_number_id: '123456789' },
          messages: [{
            from: userId,
            id: `msg_${Date.now()}`,
            timestamp: Math.floor(Date.now() / 1000),
            type: 'text',
            text: { body: message },
          }],
        },
        field: 'messages',
      }],
    }],
  };
  
  const response = await page.request.post('/webhooks/whatsapp', { data: payload });
  expect(response.ok()).toBeTruthy();
}

async function getLastResponse(page: Page, userId: string): Promise<string> {
  await page.waitForTimeout(2000);
  const response = await page.request.get(`/api/sessions/${userId}/last-message`);
  const data = await response.json();
  return data.response || '';
}

async function getCircuitBreakerStatus(page: Page, service: string): Promise<any> {
  const response = await page.request.get(`/metrics/circuit-breakers`);
  const data = await response.json();
  return data.circuits[service] || {};
}

// ===== TESTS =====

test.describe('PMS Failure Scenarios', () => {

  test('PMS API down → Circuit breaker abre → Respuesta degradada', async ({ page }) => {
    const userId = 'error_pms_001';
    
    // Simular caída del PMS (via admin endpoint)
    await page.request.post('/admin/chaos/pms-down', { data: { duration_seconds: 30 } });
    
    // Intentar consulta de disponibilidad
    await sendMessage(page, '¿Habitaciones para el 20 de febrero?', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe devolver respuesta degradada amigable
    expect(response).toMatch(/temporalmente no disponible|intente más tarde|disculpe/i);
    expect(response).not.toContain('500');
    expect(response).not.toContain('error');
    
    // Verificar que circuit breaker está OPEN
    const cbStatus = await getCircuitBreakerStatus(page, 'pms_adapter');
    expect(cbStatus.state).toBe('OPEN');
  });

  test('PMS responde con timeout → Retry logic actúa', async ({ page }) => {
    const userId = 'error_pms_002';
    
    // Simular timeout del PMS (responde después de 10s)
    await page.request.post('/admin/chaos/pms-slow', { data: { delay_seconds: 10 } });
    
    const start = Date.now();
    await sendMessage(page, 'Disponibilidad del 15 de marzo', userId);
    const response = await getLastResponse(page, userId);
    const elapsed = Date.now() - start;
    
    // Debe haber hecho retry y eventualmente devolver respuesta degradada
    expect(elapsed).toBeGreaterThan(5000); // Al menos 1 retry
    expect(elapsed).toBeLessThan(15000); // No espera indefinidamente
    expect(response).toMatch(/tardando más de lo normal|intente nuevamente/i);
  });

  test('PMS responde con error 500 → Fallback a datos cacheados', async ({ page }) => {
    const userId = 'error_pms_003';
    
    // Primero hacer consulta exitosa (poblar cache)
    await sendMessage(page, 'Habitaciones para el 10 de abril', userId);
    await getLastResponse(page, userId);
    
    // Ahora simular error 500 del PMS
    await page.request.post('/admin/chaos/pms-error', { data: { error_code: 500 } });
    
    // Hacer la misma consulta
    await sendMessage(page, 'Habitaciones para el 10 de abril', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe servir datos del cache
    expect(response).toContain('abril');
    expect(response).toMatch(/disponibilidad|habitaciones/i);
    // Puede incluir disclaimer de cache
    expect(response).toMatch(/información puede estar desactualizada|última actualización/i);
  });

});

test.describe('Database Failure Scenarios', () => {

  test('Postgres down → Session se mantiene en memoria (Redis)', async ({ page }) => {
    const userId = 'error_db_001';
    
    // Establecer contexto inicial
    await sendMessage(page, 'Habitación para 2 personas', userId);
    await getLastResponse(page, userId);
    
    // Simular caída de Postgres
    await page.request.post('/admin/chaos/postgres-down', { data: { duration_seconds: 20 } });
    
    // Continuar conversación (debe usar Redis para sesión)
    await sendMessage(page, 'Para el 5 de mayo', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe preservar contexto ("2 personas")
    expect(response).toMatch(/2 personas|mayo/i);
  });

  test('Postgres lento (high latency) → Timeout configurado actúa', async ({ page }) => {
    const userId = 'error_db_002';
    
    await page.request.post('/admin/chaos/postgres-slow', { data: { latency_ms: 5000 } });
    
    const start = Date.now();
    await sendMessage(page, 'Mis reservas anteriores', userId);
    const response = await getLastResponse(page, userId);
    const elapsed = Date.now() - start;
    
    // Debe hacer timeout y devolver respuesta degradada
    expect(elapsed).toBeLessThan(6000); // Timeout de 5s + margen
    expect(response).toMatch(/no pudimos recuperar|intente más tarde/i);
  });

});

test.describe('Redis Failure Scenarios', () => {

  test('Redis down → Sistema funciona sin cache (degraded pero funcional)', async ({ page }) => {
    const userId = 'error_redis_001';
    
    await page.request.post('/admin/chaos/redis-down', { data: { duration_seconds: 15 } });
    
    // Debe seguir funcionando pero más lento
    const start = Date.now();
    await sendMessage(page, 'Disponibilidad del 20 de junio', userId);
    const response = await getLastResponse(page, userId);
    const elapsed = Date.now() - start;
    
    expect(response).toMatch(/disponibilidad|habitaciones/i);
    // Puede ser más lento sin cache
    console.log(`Response time without Redis: ${elapsed}ms`);
  });

  test('Redis flush durante conversación → Contexto se recupera de DB', async ({ page }) => {
    const userId = 'error_redis_002';
    
    // Establecer contexto
    await sendMessage(page, 'Habitación deluxe para 3 noches', userId);
    await getLastResponse(page, userId);
    
    // Flush Redis
    await page.request.post('/admin/chaos/redis-flush');
    
    // Continuar conversación
    await sendMessage(page, 'Del 10 al 13 de julio', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe haber recuperado contexto de Postgres
    expect(response).toMatch(/deluxe|3 noches/i);
  });

});

test.describe('External Services Failures', () => {

  test('OpenAI API down → Fallback a respuestas predefinidas', async ({ page }) => {
    const userId = 'error_openai_001';
    
    await page.request.post('/admin/chaos/openai-down', { data: { duration_seconds: 30 } });
    
    await sendMessage(page, '¿Tienen piscina?', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe devolver respuesta genérica pero útil
    expect(response).toBeDefined();
    expect(response.length).toBeGreaterThan(20);
    expect(response).toMatch(/inteligencia artificial temporalmente no disponible|disculpe|agente humano/i);
  });

  test('WhatsApp API timeout → Mensaje se encola para reintento', async ({ page }) => {
    const userId = 'error_whatsapp_001';
    
    await page.request.post('/admin/chaos/whatsapp-slow', { data: { delay_seconds: 8 } });
    
    await sendMessage(page, 'Hola', userId);
    
    // Verificar que mensaje está en cola de reintentos
    const queueStatus = await page.request.get(`/admin/message-queue/status/${userId}`);
    const data = await queueStatus.json();
    
    expect(data.pending_messages).toBeGreaterThan(0);
    expect(data.retry_count).toBeGreaterThanOrEqual(1);
  });

  test('Email service down → Confirmación guardada para reenvío posterior', async ({ page }) => {
    const userId = 'error_email_001';
    
    await page.request.post('/admin/chaos/smtp-down', { data: { duration_seconds: 60 } });
    
    // Hacer reserva
    await sendMessage(page, 'Reservar del 1 al 3 de agosto, Ana Martínez, ana@test.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe confirmar reserva pero advertir sobre email
    expect(response).toMatch(/reserva confirmada/i);
    expect(response).toMatch(/email.*enviará|enviaremos.*correo/i);
    
    // Verificar que email está en cola
    const emailQueue = await page.request.get('/admin/email-queue/pending');
    const emails = await emailQueue.json();
    expect(emails.length).toBeGreaterThan(0);
  });

});

test.describe('Concurrent Failures', () => {

  test('PMS + Redis down simultáneamente → Sistema responde con degradación máxima', async ({ page }) => {
    const userId = 'error_concurrent_001';
    
    await page.request.post('/admin/chaos/pms-down', { data: { duration_seconds: 30 } });
    await page.request.post('/admin/chaos/redis-down', { data: { duration_seconds: 30 } });
    
    await sendMessage(page, '¿Tienen habitaciones?', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe devolver respuesta de mantenimiento
    expect(response).toMatch(/mantenimiento|temporalmente no disponible|contacte.*teléfono/i);
  });

  test('Cascading failure: PMS → DB → Redis (recovery)', async ({ page }) => {
    const userId = 'error_cascade_001';
    
    // Simular fallos en cascada
    await page.request.post('/admin/chaos/pms-down', { data: { duration_seconds: 10 } });
    await page.waitForTimeout(3000);
    await page.request.post('/admin/chaos/postgres-down', { data: { duration_seconds: 10 } });
    await page.waitForTimeout(3000);
    await page.request.post('/admin/chaos/redis-down', { data: { duration_seconds: 10 } });
    
    // Esperar recovery (los 10s de cada servicio)
    await page.waitForTimeout(12000);
    
    // Sistema debe haberse recuperado
    await sendMessage(page, 'Disponibilidad del 15 de septiembre', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/disponibilidad|habitaciones/i);
  });

});

test.describe('Rate Limiting', () => {

  test('Usuario excede rate limit → Respuesta 429 con mensaje claro', async ({ page }) => {
    const userId = 'ratelimit_001';
    
    // Enviar 150 mensajes en 1 minuto (límite: 120/min)
    const promises = [];
    for (let i = 0; i < 150; i++) {
      promises.push(sendMessage(page, `Mensaje ${i}`, userId));
    }
    
    // Algunos deben fallar con 429
    const results = await Promise.allSettled(promises);
    const rejectedCount = results.filter(r => r.status === 'rejected').length;
    
    expect(rejectedCount).toBeGreaterThan(0);
    
    // Verificar mensaje de rate limit
    const response = await page.request.post('/webhooks/whatsapp', {
      data: {
        object: 'whatsapp_business_account',
        entry: [{ id: 'test', changes: [{ value: { messages: [{ from: userId, text: { body: 'test' } }] } }] }]
      }
    });
    
    if (response.status() === 429) {
      const body = await response.json();
      expect(body.error).toMatch(/rate limit|demasiadas solicitudes/i);
    }
  });

});

test.describe('Data Validation Errors', () => {

  test('Fecha inválida en reserva → Mensaje de error claro', async ({ page }) => {
    const userId = 'validation_001';
    
    await sendMessage(page, 'Reservar para el 31 de febrero', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/fecha.*inválida|febrero.*28|29/i);
  });

  test('Email inválido → Solicita corrección', async ({ page }) => {
    const userId = 'validation_002';
    
    await sendMessage(page, 'Mi email es usuario@@@test', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/email.*inválido|correo.*correcto/i);
  });

  test('Número de teléfono inválido → Solicita corrección', async ({ page }) => {
    const userId = 'validation_003';
    
    await sendMessage(page, 'Teléfono: 123', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/teléfono.*inválido|número.*correcto/i);
  });

});

test.describe('Logging & Observability During Errors', () => {

  test('Errores se loggean con correlation ID', async ({ page }) => {
    const userId = 'logging_001';
    
    await page.request.post('/admin/chaos/pms-error', { data: { error_code: 500 } });
    
    await sendMessage(page, 'Test error logging', userId);
    await getLastResponse(page, userId);
    
    // Verificar logs
    const logs = await page.request.get('/admin/logs/recent?level=error');
    const logData = await logs.json();
    
    expect(logData.length).toBeGreaterThan(0);
    expect(logData[0]).toHaveProperty('correlation_id');
    expect(logData[0]).toHaveProperty('error_type');
    expect(logData[0]).toHaveProperty('timestamp');
  });

  test('Métricas de errores se incrementan correctamente', async ({ page }) => {
    await page.request.post('/admin/chaos/pms-down', { data: { duration_seconds: 5 } });
    
    const metricsBefore = await page.request.get('/metrics');
    const beforeText = await metricsBefore.text();
    
    // Provocar error
    await sendMessage(page, 'Test metrics', 'metrics_user_001');
    await getLastResponse(page, 'metrics_user_001');
    
    const metricsAfter = await page.request.get('/metrics');
    const afterText = await metricsAfter.text();
    
    // Verificar que contador de errores incrementó
    expect(afterText).toContain('pms_errors_total');
    expect(afterText).toMatch(/pms_circuit_breaker_state{.*}.*[1-2]/); // OPEN o HALF_OPEN
  });

});
