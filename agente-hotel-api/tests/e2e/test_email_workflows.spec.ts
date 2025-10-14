/**
 * E2E Tests: Email Workflows
 * 
 * Valida envío automático de emails en diferentes escenarios:
 * - Confirmación de reserva
 * - Modificación de reserva
 * - Cancelación
 * - Recordatorios pre-check-in
 * - Facturas post-check-out
 * 
 * Ejecutar:
 *   npx playwright test tests/e2e/test_email_workflows.spec.ts
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
  
  await page.request.post('/webhooks/whatsapp', { data: payload });
}

async function getLastResponse(page: Page, userId: string): Promise<string> {
  await page.waitForTimeout(2000);
  const response = await page.request.get(`/api/sessions/${userId}/last-message`);
  const data = await response.json();
  return data.response || '';
}

async function getEmailQueue(page: Page): Promise<any[]> {
  const response = await page.request.get('/admin/email-queue/all');
  return await response.json();
}

async function getEmailDetails(page: Page, emailId: string): Promise<any> {
  const response = await page.request.get(`/admin/email-queue/${emailId}`);
  return await response.json();
}

// ===== TESTS =====

test.describe('Reservation Confirmation Emails', () => {

  test('Reserva confirmada → Email con detalles completos', async ({ page }) => {
    const userId = 'email_confirm_001';
    
    // Hacer reserva completa
    await sendMessage(page, 'Reservar habitación deluxe del 10 al 12 de marzo', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'Carlos Ruiz, carlos.ruiz@test.com, +34611222333', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'Confirmo la reserva', userId);
    const response = await getLastResponse(page, userId);
    
    // Extraer código de reserva del mensaje
    const reservationCode = response.match(/RES-\d+-\d+/)?.[0];
    expect(reservationCode).toBeDefined();
    
    // Verificar que email está en cola
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const confirmationEmail = emailQueue.find(e => 
      e.type === 'reservation_confirmation' && 
      e.reservation_id === reservationCode
    );
    
    expect(confirmationEmail).toBeDefined();
    expect(confirmationEmail.to).toBe('carlos.ruiz@test.com');
    expect(confirmationEmail.subject).toMatch(/Confirmación de reserva/i);
    
    // Verificar contenido del email
    const emailDetails = await getEmailDetails(page, confirmationEmail.id);
    expect(emailDetails.html_body).toContain(reservationCode);
    expect(emailDetails.html_body).toContain('10 de marzo');
    expect(emailDetails.html_body).toContain('12 de marzo');
    expect(emailDetails.html_body).toContain('deluxe');
    expect(emailDetails.html_body).toContain('Carlos Ruiz');
  });

  test('Email incluye código QR para check-in rápido', async ({ page }) => {
    const userId = 'email_qr_001';
    
    await sendMessage(page, 'Reservar del 5 al 7 de abril, Ana López, ana@test.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    const emailDetails = await getEmailDetails(page, email.id);
    
    // Verificar QR code embebido
    expect(emailDetails.html_body).toMatch(/data:image\/png;base64,.*qr/i);
  });

  test('Email multiidioma según preferencia del huésped', async ({ page }) => {
    const userId = 'email_lang_001';
    
    // Conversación en inglés
    await sendMessage(page, 'Book room from April 10 to 12', userId);
    await getLastResponse(page, userId);
    
    await sendMessage(page, 'John Smith, john@test.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirm', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    
    // Subject debe estar en inglés
    expect(email.subject).toMatch(/Reservation Confirmation|Booking Confirmed/i);
  });

});

test.describe('Modification Emails', () => {

  test('Modificación de fecha → Email con cambios destacados', async ({ page }) => {
    const userId = 'email_modify_001';
    
    // Modificar reserva existente
    await sendMessage(page, 'Modificar reserva RES-20240115-001, nueva fecha: del 20 al 22 de enero', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo cambio', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const modificationEmail = emailQueue.find(e => e.type === 'reservation_modification');
    
    expect(modificationEmail).toBeDefined();
    
    const emailDetails = await getEmailDetails(page, modificationEmail.id);
    // Debe mostrar fechas anteriores y nuevas
    expect(emailDetails.html_body).toMatch(/fecha anterior|previous date/i);
    expect(emailDetails.html_body).toMatch(/nueva fecha|new date/i);
    expect(emailDetails.html_body).toContain('20 de enero');
    expect(emailDetails.html_body).toContain('22 de enero');
  });

  test('Upgrade de habitación → Email con diferencia de precio', async ({ page }) => {
    const userId = 'email_upgrade_001';
    
    await sendMessage(page, 'Reserva RES-20240120-005, upgrade a suite', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Acepto', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    const emailDetails = await getEmailDetails(page, email.id);
    
    expect(emailDetails.html_body).toMatch(/upgrade|mejora/i);
    expect(emailDetails.html_body).toMatch(/\$|€|precio adicional/i);
  });

});

test.describe('Cancellation Emails', () => {

  test('Cancelación con reembolso → Email con detalles de reembolso', async ({ page }) => {
    const userId = 'email_cancel_001';
    
    await sendMessage(page, 'Cancelar reserva RES-20240201-003', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Sí, cancelo', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const cancelEmail = emailQueue.find(e => e.type === 'reservation_cancellation');
    
    expect(cancelEmail).toBeDefined();
    
    const emailDetails = await getEmailDetails(page, cancelEmail.id);
    expect(emailDetails.html_body).toMatch(/cancelación confirmada|cancelled/i);
    expect(emailDetails.html_body).toMatch(/reembolso|refund/i);
    expect(emailDetails.html_body).toMatch(/5-7 días hábiles|business days/i);
  });

  test('Cancelación con penalización → Email explica cargo', async ({ page }) => {
    const userId = 'email_penalty_001';
    
    await sendMessage(page, 'Cancelar RES-20240115-006 (check-in mañana)', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Entiendo, cancelo', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    const emailDetails = await getEmailDetails(page, email.id);
    
    expect(emailDetails.html_body).toMatch(/penalización|penalty|cargo/i);
    expect(emailDetails.html_body).toMatch(/50%|primera noche/i);
  });

});

test.describe('Reminder Emails', () => {

  test('Recordatorio 48h antes del check-in', async ({ page }) => {
    // Simular trigger del cronjob de recordatorios
    await page.request.post('/admin/cron/trigger-reminders');
    
    await page.waitForTimeout(2000);
    const emailQueue = await getEmailQueue(page);
    const reminderEmails = emailQueue.filter(e => e.type === 'check_in_reminder');
    
    expect(reminderEmails.length).toBeGreaterThan(0);
    
    // Verificar contenido del primer recordatorio
    const emailDetails = await getEmailDetails(page, reminderEmails[0].id);
    expect(emailDetails.subject).toMatch(/Recordatorio|Reminder.*check-in/i);
    expect(emailDetails.html_body).toMatch(/48 horas|2 days/i);
    expect(emailDetails.html_body).toMatch(/hora de llegada|arrival time/i);
  });

  test('Recordatorio incluye instrucciones de llegada', async ({ page }) => {
    await page.request.post('/admin/cron/trigger-reminders');
    await page.waitForTimeout(2000);
    
    const emailQueue = await getEmailQueue(page);
    const reminderEmail = emailQueue.find(e => e.type === 'check_in_reminder');
    
    if (reminderEmail) {
      const emailDetails = await getEmailDetails(page, reminderEmail.id);
      expect(emailDetails.html_body).toMatch(/dirección|address|cómo llegar/i);
      expect(emailDetails.html_body).toMatch(/parking|estacionamiento/i);
    }
  });

});

test.describe('Invoice Emails', () => {

  test('Factura post-check-out con desglose completo', async ({ page }) => {
    const userId = 'email_invoice_001';
    
    // Simular check-out con factura
    await sendMessage(page, 'Check-out, necesito factura a nombre de Empresa XYZ, RFC: ABC123456', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Email: facturas@empresa.com', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const invoiceEmail = emailQueue.find(e => e.type === 'invoice');
    
    expect(invoiceEmail).toBeDefined();
    expect(invoiceEmail.to).toBe('facturas@empresa.com');
    
    const emailDetails = await getEmailDetails(page, invoiceEmail.id);
    expect(emailDetails.html_body).toContain('Empresa XYZ');
    expect(emailDetails.html_body).toContain('ABC123456');
    expect(emailDetails.html_body).toMatch(/factura|invoice/i);
    expect(emailDetails.html_body).toMatch(/subtotal|iva|total/i);
    
    // Debe incluir PDF adjunto
    expect(emailDetails.attachments).toBeDefined();
    expect(emailDetails.attachments.length).toBeGreaterThan(0);
    expect(emailDetails.attachments[0].filename).toMatch(/\.pdf$/i);
  });

});

test.describe('Email Delivery & Resilience', () => {

  test('Email fallido se reintenta automáticamente', async ({ page }) => {
    // Simular SMTP down temporalmente
    await page.request.post('/admin/chaos/smtp-down', { data: { duration_seconds: 5 } });
    
    const userId = 'email_retry_001';
    await sendMessage(page, 'Reservar del 1 al 3 de mayo, Test User, test@retry.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    // Esperar recovery
    await page.waitForTimeout(8000);
    
    // Verificar que email fue reenviado
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue.find(e => e.to === 'test@retry.com');
    
    expect(email).toBeDefined();
    expect(email.retry_count).toBeGreaterThan(0);
    expect(email.status).toBe('sent');
  });

  test('Email inválido se marca como failed con razón clara', async ({ page }) => {
    const userId = 'email_invalid_001';
    
    await sendMessage(page, 'Reservar del 5 al 7 de junio, User Invalid, invalid@@@domain', userId);
    await getLastResponse(page, userId);
    
    const response = await getLastResponse(page, userId);
    expect(response).toMatch(/email.*inválido/i);
  });

  test('Cola de emails no excede 1000 pendientes (alerting)', async ({ page }) => {
    const queueStats = await page.request.get('/admin/email-queue/stats');
    const stats = await queueStats.json();
    
    expect(stats.pending_count).toBeLessThan(1000);
    
    if (stats.pending_count > 800) {
      // Debe haber alertas configuradas
      expect(stats.alert_triggered).toBe(true);
    }
  });

});

test.describe('Email Template Validation', () => {

  test('Todos los placeholders se reemplazan correctamente', async ({ page }) => {
    const userId = 'email_template_001';
    
    await sendMessage(page, 'Reservar del 10 al 12 de julio, María García, maria@test.com, +34600111222', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    const emailDetails = await getEmailDetails(page, email.id);
    
    // No debe haber placeholders sin reemplazar
    expect(emailDetails.html_body).not.toMatch(/\{\{.*\}\}/);
    expect(emailDetails.html_body).not.toMatch(/%[A-Z_]+%/);
    
    // Debe tener datos reales
    expect(emailDetails.html_body).toContain('María García');
    expect(emailDetails.html_body).toContain('10 de julio');
    expect(emailDetails.html_body).toContain('+34600111222');
  });

  test('Links en email son válidos y trackables', async ({ page }) => {
    const userId = 'email_links_001';
    
    await sendMessage(page, 'Reservar del 1 al 3 de agosto, Pedro Sánchez, pedro@test.com', userId);
    await getLastResponse(page, userId);
    await sendMessage(page, 'Confirmo', userId);
    await getLastResponse(page, userId);
    
    await page.waitForTimeout(1000);
    const emailQueue = await getEmailQueue(page);
    const email = emailQueue[emailQueue.length - 1];
    const emailDetails = await getEmailDetails(page, email.id);
    
    // Extraer links del HTML
    const linkMatches = emailDetails.html_body.matchAll(/href="([^"]+)"/g);
    const links = Array.from(linkMatches).map(m => m[1]);
    
    expect(links.length).toBeGreaterThan(0);
    
    // Todos los links deben tener tracking parameter
    links.forEach(link => {
      expect(link).toMatch(/utm_source|tracking_id|t=/);
    });
  });

});
