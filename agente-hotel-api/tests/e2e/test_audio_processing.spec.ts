/**
 * E2E Tests: Audio Processing
 * 
 * Valida el flujo completo de mensajes de voz:
 * WhatsApp audio → Download → STT (Whisper) → NLP → Response
 * 
 * Ejecutar:
 *   npx playwright test tests/e2e/test_audio_processing.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ===== FIXTURES =====

const AUDIO_FIXTURES = {
  spanish_availability: path.join(__dirname, '../fixtures/audio/spanish_availability.ogg'),
  english_pricing: path.join(__dirname, '../fixtures/audio/english_pricing.ogg'),
  noisy_audio: path.join(__dirname, '../fixtures/audio/noisy_background.ogg'),
  long_audio: path.join(__dirname, '../fixtures/audio/long_monologue.ogg'),
};

// ===== HELPERS =====

async function sendAudioMessage(
  page: Page,
  audioPath: string,
  userId: string = 'audio_test_001'
): Promise<void> {
  // Mock de audio ID (en realidad WhatsApp lo genera)
  const audioId = `audio_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
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
            type: 'audio',
            audio: {
              id: audioId,
              mime_type: 'audio/ogg; codecs=opus',
            },
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

async function getAudioProcessingStatus(page: Page, audioId: string): Promise<any> {
  const response = await page.request.get(`/api/audio/status/${audioId}`);
  return await response.json();
}

// ===== TESTS =====

test.describe('Audio Processing E2E', () => {

  test('Audio en español: disponibilidad → STT → NLP → Response', async ({ page }) => {
    const userId = 'audio_user_001';
    
    // Enviar mensaje de audio
    await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId);
    
    // Esperar procesamiento (STT puede tardar 2-5 segundos)
    await page.waitForTimeout(6000);
    
    // Verificar respuesta
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.transcription).toBeDefined();
    expect(data.transcription.toLowerCase()).toContain('disponibilidad');
    expect(data.response).toBeDefined();
    expect(data.response.toLowerCase()).toContain('habitación');
  });

  test('Audio en inglés: pricing → STT → NLP → Response', async ({ page }) => {
    const userId = 'audio_user_002';
    
    await sendAudioMessage(page, AUDIO_FIXTURES.english_pricing, userId);
    await page.waitForTimeout(6000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.transcription.toLowerCase()).toContain('price');
    expect(data.response).toMatch(/\$|price|cost/i);
  });

  test('Audio con ruido de fondo se transcribe correctamente', async ({ page }) => {
    const userId = 'audio_user_003';
    
    await sendAudioMessage(page, AUDIO_FIXTURES.noisy_audio, userId);
    await page.waitForTimeout(8000); // Ruido puede requerir más tiempo
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    // Transcripción debe existir aunque haya ruido
    expect(data.transcription).toBeDefined();
    expect(data.transcription.length).toBeGreaterThan(10);
    
    // Confidence score debe ser razonable
    expect(data.transcription_confidence).toBeGreaterThan(0.5);
  });

  test('Audio largo (>30s) se procesa sin timeout', async ({ page }) => {
    const userId = 'audio_user_004';
    
    await sendAudioMessage(page, AUDIO_FIXTURES.long_audio, userId);
    
    // Audio largo puede tardar hasta 15 segundos
    await page.waitForTimeout(16000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.transcription).toBeDefined();
    expect(data.transcription.length).toBeGreaterThan(100);
    expect(data.processing_time_ms).toBeLessThan(15000);
  });

  test('Audio con formato inválido devuelve error claro', async ({ page }) => {
    const userId = 'audio_user_005';
    const invalidAudioPath = path.join(__dirname, '../fixtures/audio/invalid.mp3');
    
    await sendAudioMessage(page, invalidAudioPath, userId);
    await page.waitForTimeout(3000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.error).toBeDefined();
    expect(data.error).toMatch(/formato|audio|inválido/i);
  });

  test('Audio vacío (silencio) se detecta', async ({ page }) => {
    const userId = 'audio_user_006';
    const silentAudioPath = path.join(__dirname, '../fixtures/audio/silence.ogg');
    
    await sendAudioMessage(page, silentAudioPath, userId);
    await page.waitForTimeout(4000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.transcription).toBeDefined();
    expect(data.transcription.length).toBeLessThan(10);
    expect(data.response).toMatch(/no escuché|silencio|audio vacío/i);
  });

});

test.describe('Audio Processing Performance', () => {

  test('P95 latency de audio processing < 5s', async ({ page }) => {
    const latencies: number[] = [];
    
    for (let i = 0; i < 20; i++) {
      const userId = `perf_audio_${i}`;
      const start = Date.now();
      
      await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId);
      
      // Poll hasta que esté procesado
      let processed = false;
      while (!processed && Date.now() - start < 15000) {
        await page.waitForTimeout(500);
        const response = await page.request.get(`/api/sessions/${userId}/last-message`);
        const data = await response.json();
        if (data.transcription) {
          processed = true;
        }
      }
      
      const latency = Date.now() - start;
      latencies.push(latency);
    }
    
    // Calcular P95
    latencies.sort((a, b) => a - b);
    const p95Index = Math.floor(latencies.length * 0.95);
    const p95 = latencies[p95Index];
    
    console.log(`Audio P95 latency: ${p95}ms`);
    console.log(`Min: ${latencies[0]}ms, Max: ${latencies[latencies.length - 1]}ms`);
    
    expect(p95).toBeLessThan(5000);
  });

  test('Throughput de audio: 10 audios concurrentes procesados correctamente', async ({ page }) => {
    const userIds = Array.from({ length: 10 }, (_, i) => `concurrent_audio_${i}`);
    const start = Date.now();
    
    // Enviar todos los audios simultáneamente
    const promises = userIds.map(userId => 
      sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId)
    );
    await Promise.all(promises);
    
    // Esperar procesamiento
    await page.waitForTimeout(10000);
    
    // Verificar que todos se procesaron
    let successCount = 0;
    for (const userId of userIds) {
      const response = await page.request.get(`/api/sessions/${userId}/last-message`);
      const data = await response.json();
      if (data.transcription) {
        successCount++;
      }
    }
    
    const totalTime = Date.now() - start;
    console.log(`Processed ${successCount}/10 audios in ${totalTime}ms`);
    
    expect(successCount).toBe(10);
    expect(totalTime).toBeLessThan(15000); // Menos de 15s para 10 audios
  });

});

test.describe('Audio Caching', () => {

  test('Mismo audio procesado 2 veces usa cache en segunda llamada', async ({ page }) => {
    const userId1 = 'cache_test_001';
    const userId2 = 'cache_test_002';
    
    // Primera procesamiento (sin cache)
    const start1 = Date.now();
    await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId1);
    await page.waitForTimeout(6000);
    const latency1 = Date.now() - start1;
    
    // Segunda procesamiento (con cache - mismo audio hash)
    const start2 = Date.now();
    await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId2);
    await page.waitForTimeout(2000);
    const latency2 = Date.now() - start2;
    
    console.log(`First: ${latency1}ms, Second (cached): ${latency2}ms`);
    
    // Segunda llamada debe ser significativamente más rápida
    expect(latency2).toBeLessThan(latency1 * 0.5);
  });

});

test.describe('Audio Error Handling', () => {

  test('Falla de descarga de audio se maneja correctamente', async ({ page }) => {
    // Mock de endpoint de descarga fallido
    await page.route('**/media/download/**', route => route.abort());
    
    const userId = 'error_test_001';
    await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId);
    await page.waitForTimeout(3000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    expect(data.error).toBeDefined();
    expect(data.error).toMatch(/descarga|download|failed/i);
  });

  test('Falla de STT (Whisper) devuelve fallback', async ({ page }) => {
    // Mock de endpoint de Whisper fallido
    await page.route('**/openai/audio/transcriptions', route => route.abort());
    
    const userId = 'error_test_002';
    await sendAudioMessage(page, AUDIO_FIXTURES.spanish_availability, userId);
    await page.waitForTimeout(3000);
    
    const response = await page.request.get(`/api/sessions/${userId}/last-message`);
    const data = await response.json();
    
    // Debe haber un fallback response
    expect(data.response).toBeDefined();
    expect(data.response).toMatch(/no pude procesar|audio|intenta de nuevo/i);
  });

});
