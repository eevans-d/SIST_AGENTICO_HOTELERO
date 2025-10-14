/**
 * E2E Tests: Multi-Turn Conversations
 * 
 * Valida conversaciones complejas con múltiples mensajes y contexto preservado.
 * 
 * Ejecutar:
 *   npx playwright test tests/e2e/test_multiturn_conversations.spec.ts
 *   npx playwright test tests/e2e/test_multiturn_conversations.spec.ts --headed
 */

import { test, expect, Page } from '@playwright/test';

// ===== HELPERS =====

async function sendWhatsAppMessage(page: Page, message: string, userId: string = 'test_user_001'): Promise<void> {
  await page.goto('/webhooks/whatsapp', { method: 'POST' });
  
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
  
  const response = await page.request.post('/webhooks/whatsapp', {
    data: payload,
    headers: { 'Content-Type': 'application/json' },
  });
  
  expect(response.ok()).toBeTruthy();
}

async function getLastAgentResponse(page: Page, userId: string): Promise<string> {
  // Mock: En realidad se consultaría la sesión o base de datos
  const response = await page.request.get(`/api/sessions/${userId}/last-message`);
  const data = await response.json();
  return data.response || '';
}

// ===== TESTS =====

test.describe('Multi-Turn Conversations', () => {
  
  test.beforeEach(async ({ page }) => {
    // Setup: Limpiar sesiones previas
    await page.request.delete('/api/sessions/test_user_001');
  });

  test('Conversación de disponibilidad con contexto preservado', async ({ page }) => {
    const userId = 'test_user_001';
    
    // Turno 1: Consulta inicial
    await sendWhatsAppMessage(page, '¿Tienen habitaciones disponibles para el 15 de enero?', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('disponibilidad');
    
    // Turno 2: Agregar detalles (contexto implícito)
    await sendWhatsAppMessage(page, 'Para 2 personas', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toContain('2 personas');
    expect(response.toLowerCase()).toContain('15 de enero');
    
    // Turno 3: Preguntar precio (debe recordar fechas y huéspedes)
    await sendWhatsAppMessage(page, '¿Cuál es el precio?', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/\$|precio|costo/i);
    
    // Turno 4: Confirmar reserva
    await sendWhatsAppMessage(page, 'Quiero reservar', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('reserv');
  });

  test('Conversación de modificación de reserva', async ({ page }) => {
    const userId = 'test_user_002';
    
    // Turno 1: Identificar reserva
    await sendWhatsAppMessage(page, 'Tengo la reserva #12345', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response).toContain('12345');
    
    // Turno 2: Solicitar cambio (contexto de reserva preservado)
    await sendWhatsAppMessage(page, 'Quiero cambiar la fecha al 20 de enero', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('20 de enero');
    expect(response).toMatch(/cambio|modificación/i);
    
    // Turno 3: Preguntar por recargo
    await sendWhatsAppMessage(page, '¿Hay recargo por el cambio?', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/recargo|costo|gratis|sin cargo/i);
    
    // Turno 4: Confirmar cambio
    await sendWhatsAppMessage(page, 'Ok, procede con el cambio', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/confirmado|actualizado|modificado/i);
  });

  test('Conversación de queja con escalamiento', async ({ page }) => {
    const userId = 'test_user_003';
    
    // Turno 1: Reportar problema
    await sendWhatsAppMessage(page, 'Tengo un problema con mi reserva', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('problem');
    
    // Turno 2: Detallar problema
    await sendWhatsAppMessage(page, 'No me llegó el email de confirmación', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/email|correo|confirmación/i);
    
    // Turno 3: Solicitar reenvío
    await sendWhatsAppMessage(page, '¿Pueden reenviarlo?', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/reenviar|enviar|correo/i);
    
    // Turno 4: Escalamiento si no resuelto
    await sendWhatsAppMessage(page, 'Sigue sin llegarme', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/humano|asistente|gerente|equipo/i);
  });

  test('Conversación con información sensible redactada', async ({ page }) => {
    const userId = 'test_user_004';
    
    // Turno 1: Usuario proporciona PII
    await sendWhatsAppMessage(page, 'Mi email es juan.perez@hotel.com y mi DNI es 12345678', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    
    // PII debe estar redactada en logs (no en respuesta al usuario)
    const logs = await page.request.get('/api/logs?user_id=' + userId);
    const logsText = await logs.text();
    expect(logsText).not.toContain('juan.perez@hotel.com');
    expect(logsText).not.toContain('12345678');
    expect(logsText).toMatch(/\*\*\*|REDACTED|####/);
    
    // Respuesta debe usar info sin revelarla completa
    expect(response).toMatch(/juan|perez/i);
  });

  test('Conversación en múltiples idiomas (si soportado)', async ({ page }) => {
    const userId = 'test_user_005';
    
    // Turno 1: Español
    await sendWhatsAppMessage(page, '¿Tienen habitaciones?', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/sí|disponibilidad|habitaciones/i);
    
    // Turno 2: Inglés (cambio de idioma)
    await sendWhatsAppMessage(page, 'What is the price?', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/price|cost|\$|usd/i);
    
    // Turno 3: Volver a español
    await sendWhatsAppMessage(page, 'Gracias', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response).toMatch(/de nada|gracias|gusto/i);
  });

  test('Conversación con timeout de sesión', async ({ page }) => {
    const userId = 'test_user_006';
    
    // Turno 1: Iniciar conversación
    await sendWhatsAppMessage(page, '¿Tienen disponibilidad?', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('disponibilidad');
    
    // Simular timeout (30 minutos en producción, 5 segundos en test)
    await page.waitForTimeout(6000);
    
    // Turno 2: Después de timeout (contexto perdido)
    await sendWhatsAppMessage(page, 'Para 2 personas', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    
    // Agente debe pedir contexto nuevamente
    expect(response).toMatch(/puedo ayudar|qué necesitas|en qué puedo asistir/i);
  });

  test('Conversación con interrupción y cambio de tema', async ({ page }) => {
    const userId = 'test_user_007';
    
    // Turno 1: Consulta de disponibilidad
    await sendWhatsAppMessage(page, '¿Tienen habitaciones para el 15 de enero?', userId);
    await page.waitForTimeout(1000);
    
    // Turno 2: Cambio abrupto de tema (políticas)
    await sendWhatsAppMessage(page, '¿Cuál es su política de cancelación?', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('cancelación');
    expect(response).toMatch(/días|horas|política/i);
    
    // Turno 3: Volver al tema original
    await sendWhatsAppMessage(page, 'Ok, volviendo a la disponibilidad del 15', userId);
    await page.waitForTimeout(1000);
    response = await getLastAgentResponse(page, userId);
    expect(response.toLowerCase()).toContain('15 de enero');
  });

  test('Conversación con errores de tipeo y autocorrección', async ({ page }) => {
    const userId = 'test_user_008';
    
    // Turno 1: Mensaje con errores de tipeo
    await sendWhatsAppMessage(page, 'Tineen habitasiones para el 15 de enro?', userId);
    await page.waitForTimeout(1000);
    let response = await getLastAgentResponse(page, userId);
    
    // Agente debe entender la intención a pesar de errores
    expect(response.toLowerCase()).toContain('disponibilidad');
    expect(response).toMatch(/15|enero/i);
  });

});

test.describe('Performance de Multi-Turn', () => {
  
  test('P95 latency en conversación de 5 turnos < 3s por mensaje', async ({ page }) => {
    const userId = 'perf_test_001';
    const latencies: number[] = [];
    
    const messages = [
      '¿Tienen habitaciones?',
      'Para 2 personas',
      '¿Cuál es el precio?',
      'Quiero reservar',
      'Gracias',
    ];
    
    for (const message of messages) {
      const start = Date.now();
      await sendWhatsAppMessage(page, message, userId);
      await page.waitForTimeout(500);
      await getLastAgentResponse(page, userId);
      const latency = Date.now() - start;
      latencies.push(latency);
    }
    
    // Calcular P95
    latencies.sort((a, b) => a - b);
    const p95Index = Math.floor(latencies.length * 0.95);
    const p95 = latencies[p95Index];
    
    console.log(`P95 latency: ${p95}ms`);
    expect(p95).toBeLessThan(3000);
  });

});
