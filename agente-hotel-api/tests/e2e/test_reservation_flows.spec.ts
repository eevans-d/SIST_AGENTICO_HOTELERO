/**
 * E2E Tests: Reservation Complete Flows
 * 
 * Valida flujos completos de reserva:
 * - Consulta → Cotización → Confirmación → Pago → Email confirmación
 * - Modificación (fecha, tipo habitación)
 * - Cancelación con política de reembolso
 * 
 * Ejecutar:
 *   npx playwright test tests/e2e/test_reservation_flows.spec.ts
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

async function getReservationStatus(page: Page, reservationId: string): Promise<any> {
  const response = await page.request.get(`/api/reservations/${reservationId}`);
  return await response.json();
}

// ===== TESTS =====

test.describe('Complete Reservation Flow', () => {

  test('Flujo completo: Consulta → Cotización → Reserva → Confirmación', async ({ page }) => {
    const userId = 'reservation_001';
    
    // Paso 1: Consulta de disponibilidad
    await sendMessage(page, '¿Tienen habitaciones para el 20 de febrero?', userId);
    let response = await getLastResponse(page, userId);
    expect(response.toLowerCase()).toContain('disponibilidad');
    
    // Paso 2: Especificar detalles
    await sendMessage(page, 'Para 2 adultos, 3 noches', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/precio|total|costo/i);
    
    // Paso 3: Confirmar datos de huésped
    await sendMessage(page, 'Juan Pérez, juan.perez@hotel.com, +34600123456', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/confirmar|datos|correctos/i);
    
    // Paso 4: Confirmar reserva
    await sendMessage(page, 'Sí, confirmo la reserva', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/reserva confirmada|código|RES-\d+/i);
    
    // Paso 5: Verificar que se envió email
    const session = await page.request.get(`/api/sessions/${userId}`);
    const sessionData = await session.json();
    expect(sessionData.email_sent).toBe(true);
    expect(sessionData.reservation_id).toMatch(/^RES-\d+$/);
    
    // Paso 6: Validar estado en PMS
    const reservationStatus = await getReservationStatus(page, sessionData.reservation_id);
    expect(reservationStatus.status).toBe('confirmed');
    expect(reservationStatus.guest_name).toBe('Juan Pérez');
  });

  test('Reserva con pago anticipado', async ({ page }) => {
    const userId = 'reservation_002';
    
    await sendMessage(page, 'Quiero reservar habitación deluxe del 10 al 12 de marzo', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'María García, maria@test.com, +34611222333', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'Quiero pagar por adelantado', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe devolver link de pago
    expect(response).toMatch(/link de pago|stripe|payment/i);
    expect(response).toContain('https://');
  });

  test('Reserva para grupo (>4 personas)', async ({ page }) => {
    const userId = 'reservation_003';
    
    await sendMessage(page, '¿Tienen disponibilidad para 8 personas del 15 al 18 de abril?', userId);
    const response = await getLastResponse(page, userId);
    
    // Grupo grande debe sugerir múltiples habitaciones
    expect(response).toMatch(/habitaciones|rooms|múltiples/i);
    expect(response).toMatch(/descuento|discount/i); // Descuento por grupo
  });

});

test.describe('Reservation Modification Flow', () => {

  test('Modificar fecha de reserva existente', async ({ page }) => {
    const userId = 'modification_001';
    
    // Crear reserva base
    await sendMessage(page, 'Tengo una reserva RES-20240115-001 y quiero cambiar fecha', userId);
    let response = await getLastResponse(page, userId);
    expect(response).toMatch(/nueva fecha|cuándo/i);
    
    // Nueva fecha
    await sendMessage(page, 'Del 20 al 23 de enero', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/disponibilidad|confirmada|precio/i);
    
    // Confirmar cambio
    await sendMessage(page, 'Sí, confirmo el cambio', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/modificada|actualizada/i);
    
    // Verificar email de modificación enviado
    const session = await page.request.get(`/api/sessions/${userId}`);
    const sessionData = await session.json();
    expect(sessionData.modification_email_sent).toBe(true);
  });

  test('Cambiar tipo de habitación (upgrade)', async ({ page }) => {
    const userId = 'modification_002';
    
    await sendMessage(page, 'Reserva RES-20240120-005, quiero upgrade a suite', userId);
    let response = await getLastResponse(page, userId);
    expect(response).toMatch(/diferencia|adicional|precio/i);
    
    await sendMessage(page, 'Acepto la diferencia', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/upgrade confirmado|suite/i);
  });

  test('Agregar servicios adicionales (desayuno, parking)', async ({ page }) => {
    const userId = 'modification_003';
    
    await sendMessage(page, 'Reserva RES-20240125-010, agregar desayuno y parking', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/desayuno|breakfast/i);
    expect(response).toMatch(/parking|estacionamiento/i);
    expect(response).toMatch(/total|adicional/i);
  });

});

test.describe('Cancellation Flow', () => {

  test('Cancelación con reembolso completo (>48h)', async ({ page }) => {
    const userId = 'cancellation_001';
    
    await sendMessage(page, 'Quiero cancelar mi reserva RES-20240201-003', userId);
    let response = await getLastResponse(page, userId);
    expect(response).toMatch(/política|reembolso|cancelación/i);
    
    await sendMessage(page, 'Sí, cancelo la reserva', userId);
    response = await getLastResponse(page, userId);
    
    // Debe confirmar reembolso completo
    expect(response).toMatch(/cancelada|reembolso completo|100%/i);
    
    // Verificar estado en PMS
    const reservationStatus = await getReservationStatus(page, 'RES-20240201-003');
    expect(reservationStatus.status).toBe('cancelled');
  });

  test('Cancelación con penalización (<48h)', async ({ page }) => {
    const userId = 'cancellation_002';
    
    // Simular reserva cercana
    await sendMessage(page, 'Cancelar reserva RES-20240115-006 (check-in mañana)', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe informar penalización
    expect(response).toMatch(/penalización|cargo|50%|primera noche/i);
  });

  test('Cancelación por fuerza mayor (flexible)', async ({ page }) => {
    const userId = 'cancellation_003';
    
    await sendMessage(page, 'Necesito cancelar RES-20240210-008 por emergencia médica', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe ofrecer flexibilidad
    expect(response).toMatch(/contactaremos|atención especial|documentación/i);
  });

});

test.describe('Check-in/Check-out Flow', () => {

  test('Check-in anticipado (early check-in)', async ({ page }) => {
    const userId = 'checkin_001';
    
    await sendMessage(page, 'Reserva RES-20240118-004, puedo hacer check-in a las 10am?', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/check-in|disponibilidad|cargo adicional/i);
  });

  test('Check-out tardío (late check-out)', async ({ page }) => {
    const userId = 'checkout_001';
    
    await sendMessage(page, 'Necesito check-out a las 3pm en vez de 12pm', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/check-out|cargo|adicional|sujeto a disponibilidad/i);
  });

  test('Check-out y solicitar factura', async ({ page }) => {
    const userId = 'checkout_002';
    
    await sendMessage(page, 'Hago check-out ahora, necesito factura a nombre de Empresa SA, RFC: ABC123456', userId);
    let response = await getLastResponse(page, userId);
    expect(response).toMatch(/factura|RFC|email/i);
    
    await sendMessage(page, 'facturas@empresa.com', userId);
    response = await getLastResponse(page, userId);
    expect(response).toMatch(/factura enviada|recibirá/i);
  });

});

test.describe('Edge Cases', () => {

  test('Reserva para fechas no disponibles', async ({ page }) => {
    const userId = 'edge_001';
    
    await sendMessage(page, 'Habitación para el 31 de diciembre', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe ofrecer alternativas
    expect(response).toMatch(/no disponible|completo|alternativas|fechas cercanas/i);
  });

  test('Reserva con datos incompletos', async ({ page }) => {
    const userId = 'edge_002';
    
    await sendMessage(page, 'Quiero reservar', userId);
    const response = await getLastResponse(page, userId);
    
    // Debe solicitar información
    expect(response).toMatch(/cuándo|fecha|personas|cuántos días/i);
  });

  test('Modificar reserva no existente', async ({ page }) => {
    const userId = 'edge_003';
    
    await sendMessage(page, 'Modificar reserva RES-99999999-999', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/no encontrada|código incorrecto|verificar/i);
  });

  test('Reserva duplicada (mismo usuario, mismas fechas)', async ({ page }) => {
    const userId = 'edge_004';
    
    // Primera reserva
    await sendMessage(page, 'Habitación del 10 al 12 de mayo, Juan López, juan@test.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    // Intentar reservar de nuevo
    await sendMessage(page, 'Habitación del 10 al 12 de mayo, Juan López, juan@test.com', userId);
    const response = await getLastResponse(page, userId);
    
    expect(response).toMatch(/ya tiene una reserva|duplicada/i);
  });

});

test.describe('Performance Validation', () => {

  test('Flujo completo de reserva < 8 segundos', async ({ page }) => {
    const userId = 'perf_001';
    const start = Date.now();
    
    await sendMessage(page, '¿Habitación para el 15 de junio?', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'Pedro Sánchez, pedro@test.com, 2 noches', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    const totalTime = Date.now() - start;
    console.log(`Complete reservation flow: ${totalTime}ms`);
    
    expect(totalTime).toBeLessThan(8000);
  });

});
