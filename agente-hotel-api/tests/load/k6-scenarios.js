/**
 * K6 Load Testing Scenarios para Agente Hotelero IA
 * 
 * Ejecutar:
 *   k6 run tests/load/k6-scenarios.js
 *   k6 run --env SCENARIO=spike tests/load/k6-scenarios.js
 *   k6 run --env SCENARIO=soak tests/load/k6-scenarios.js
 * 
 * Métricas clave:
 * - http_req_duration: P95 < 3000ms (SLO)
 * - http_req_failed: < 1% (tasa de error)
 * - iterations: Conversaciones completadas
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// ===== CONFIGURACIÓN =====

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'normal';  // normal | spike | soak | stress

// Métricas personalizadas
const conversationDuration = new Trend('conversation_duration', true);
const messageLatency = new Trend('message_latency', true);
const pmsLatency = new Trend('pms_operation_latency', true);
const errorRate = new Rate('errors');
const conversationSuccess = new Rate('conversation_success');
const nlpAccuracy = new Counter('nlp_intent_accuracy');

// ===== ESCENARIOS DE CARGA =====

export const options = {
    scenarios: {
        // NORMAL: Carga típica de producción
        normal: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 10 },   // Ramp-up a 10 usuarios
                { duration: '5m', target: 10 },   // Mantener 10 usuarios
                { duration: '2m', target: 20 },   // Pico moderado
                { duration: '5m', target: 20 },   // Mantener pico
                { duration: '2m', target: 0 },    // Ramp-down
            ],
            gracefulRampDown: '30s',
            exec: 'normalConversation',
        },

        // SPIKE: Picos repentinos de tráfico
        spike: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 5 },    // Carga base
                { duration: '30s', target: 50 },  // SPIKE repentino
                { duration: '3m', target: 50 },   // Mantener spike
                { duration: '1m', target: 5 },    // Vuelta a baseline
                { duration: '30s', target: 0 },
            ],
            exec: 'normalConversation',
        },

        // SOAK: Test de resistencia prolongada (memory leaks, degradación)
        soak: {
            executor: 'constant-vus',
            vus: 15,
            duration: '30m',  // 30 minutos de carga constante
            exec: 'normalConversation',
        },

        // STRESS: Encontrar el breaking point
        stress: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 20 },
                { duration: '2m', target: 40 },
                { duration: '2m', target: 60 },
                { duration: '2m', target: 80 },
                { duration: '2m', target: 100 },
                { duration: '5m', target: 100 },
                { duration: '2m', target: 0 },
            ],
            exec: 'normalConversation',
        },
    },

    // Thresholds (SLOs del sistema)
    thresholds: {
        // Latencia P95 < 3s (según SLO del proyecto)
        'http_req_duration{scenario:normal}': ['p(95)<3000'],
        'http_req_duration{scenario:spike}': ['p(95)<5000'],
        'http_req_duration{scenario:soak}': ['p(95)<3000'],
        'http_req_duration{scenario:stress}': ['p(95)<10000'],
        
        // Tasa de error < 1%
        'http_req_failed': ['rate<0.01'],
        
        // 95% de conversaciones exitosas
        'conversation_success': ['rate>0.95'],
        
        // Checks deben pasar >98%
        'checks': ['rate>0.98'],
    },

    // Configuración HTTP
    insecureSkipTLSVerify: true,
    noConnectionReuse: false,
    userAgent: 'K6LoadTest/1.0',
};

// ===== DATOS DE PRUEBA =====

const TEST_USERS = [
    { id: 'user_001', name: 'Juan Pérez' },
    { id: 'user_002', name: 'María García' },
    { id: 'user_003', name: 'Carlos López' },
    { id: 'user_004', name: 'Ana Martínez' },
    { id: 'user_005', name: 'Luis Fernández' },
];

const CONVERSATION_FLOWS = [
    // Flujo 1: Consulta de disponibilidad
    {
        name: 'availability_check',
        messages: [
            '¿Tienen habitaciones disponibles para el 15 de enero?',
            'Para 2 personas',
            'Perfecto, gracias',
        ],
        expectedIntents: ['check_availability', 'provide_details', 'thank_you'],
    },
    
    // Flujo 2: Consulta de políticas
    {
        name: 'policy_inquiry',
        messages: [
            '¿Cuál es su política de cancelación?',
            '¿Y el horario de check-in?',
            'Entendido, muchas gracias',
        ],
        expectedIntents: ['cancellation_policy', 'checkin_info', 'thank_you'],
    },
    
    // Flujo 3: Modificación de reserva
    {
        name: 'modify_reservation',
        messages: [
            'Tengo la reserva #12345',
            'Quiero cambiar la fecha al 20 de enero',
            '¿Hay recargo por el cambio?',
            'Ok, procede con el cambio',
        ],
        expectedIntents: ['retrieve_reservation', 'modify_dates', 'pricing_info', 'confirm_action'],
    },
    
    // Flujo 4: Quejas/problemas
    {
        name: 'complaint',
        messages: [
            'Tengo un problema con mi reserva',
            'No me llegó el email de confirmación',
            '¿Pueden reenviarlo?',
        ],
        expectedIntents: ['report_issue', 'clarify_issue', 'request_action'],
    },
    
    // Flujo 5: Audio message (simulado)
    {
        name: 'audio_query',
        messages: [
            '[AUDIO] Hola, quisiera saber precios para fin de semana',
            'Dos noches',
        ],
        expectedIntents: ['check_pricing', 'provide_details'],
    },
];

// ===== FUNCIONES DE CONVERSACIÓN =====

export function normalConversation() {
    const user = randomItem(TEST_USERS);
    const flow = randomItem(CONVERSATION_FLOWS);
    
    group(`Conversación: ${flow.name}`, () => {
        const conversationStart = Date.now();
        let conversationPassed = true;
        
        // Iterar sobre mensajes del flujo
        flow.messages.forEach((message, index) => {
            const expectedIntent = flow.expectedIntents[index];
            
            group(`Mensaje ${index + 1}: ${expectedIntent}`, () => {
                const messageStart = Date.now();
                
                // Payload del webhook (simula WhatsApp)
                const payload = JSON.stringify({
                    object: 'whatsapp_business_account',
                    entry: [{
                        id: 'entry_001',
                        changes: [{
                            value: {
                                messaging_product: 'whatsapp',
                                metadata: { phone_number_id: '123456789' },
                                messages: [{
                                    from: user.id,
                                    id: `msg_${Date.now()}_${randomIntBetween(1000, 9999)}`,
                                    timestamp: Math.floor(Date.now() / 1000),
                                    type: message.includes('[AUDIO]') ? 'audio' : 'text',
                                    text: message.includes('[AUDIO]') ? undefined : { body: message },
                                    audio: message.includes('[AUDIO]') ? {
                                        id: `audio_${Date.now()}`,
                                        mime_type: 'audio/ogg; codecs=opus',
                                    } : undefined,
                                }],
                            },
                            field: 'messages',
                        }],
                    }],
                });
                
                // Enviar mensaje al webhook
                const response = http.post(
                    `${BASE_URL}/webhooks/whatsapp`,
                    payload,
                    {
                        headers: {
                            'Content-Type': 'application/json',
                            'X-K6-User': user.id,
                            'X-K6-Flow': flow.name,
                        },
                        tags: {
                            scenario: SCENARIO,
                            flow: flow.name,
                            intent: expectedIntent,
                        },
                    }
                );
                
                const messageEnd = Date.now();
                messageLatency.add(messageEnd - messageStart);
                
                // Validaciones
                const checkResult = check(response, {
                    'Status es 200': (r) => r.status === 200,
                    'Respuesta válida': (r) => {
                        try {
                            const body = JSON.parse(r.body);
                            return body.status === 'received' || body.status === 'processing';
                        } catch {
                            return false;
                        }
                    },
                    'Tiempo de respuesta < 3s': (r) => r.timings.duration < 3000,
                    'No hay errores 5xx': (r) => r.status < 500,
                });
                
                if (!checkResult) {
                    conversationPassed = false;
                    errorRate.add(1);
                    console.log(`❌ Error en mensaje ${index + 1}: ${response.status} - ${response.body}`);
                } else {
                    errorRate.add(0);
                }
                
                // Verificar intent correcto (si el sistema lo expone)
                if (response.status === 200) {
                    try {
                        const body = JSON.parse(response.body);
                        if (body.intent === expectedIntent) {
                            nlpAccuracy.add(1);
                        }
                    } catch (e) {
                        // Intent no disponible en respuesta
                    }
                }
                
                // Pausa realista entre mensajes (2-5 segundos)
                sleep(randomIntBetween(2, 5));
            });
        });
        
        const conversationEnd = Date.now();
        conversationDuration.add(conversationEnd - conversationStart);
        conversationSuccess.add(conversationPassed ? 1 : 0);
    });
}

// ===== TEST DE OPERACIONES PMS =====

export function pmsLoadTest() {
    group('PMS Operations Load', () => {
        const operations = [
            { endpoint: '/api/pms/availability', method: 'GET', params: { checkin: '2025-01-15', checkout: '2025-01-17' } },
            { endpoint: '/api/pms/reservations', method: 'GET', params: { user_id: randomItem(TEST_USERS).id } },
            { endpoint: '/api/pms/policies', method: 'GET' },
        ];
        
        operations.forEach((op) => {
            const startTime = Date.now();
            const url = `${BASE_URL}${op.endpoint}?${new URLSearchParams(op.params).toString()}`;
            
            const response = http.get(url, {
                headers: { 'X-K6-Test': 'pms_load' },
                tags: { endpoint: op.endpoint },
            });
            
            const duration = Date.now() - startTime;
            pmsLatency.add(duration);
            
            check(response, {
                'PMS responde 200': (r) => r.status === 200,
                'PMS responde < 2s': (r) => r.timings.duration < 2000,
            });
            
            sleep(1);
        });
    });
}

// ===== TEST DE LÍMITE DE TASA =====

export function rateLimitTest() {
    group('Rate Limit Test', () => {
        const user = randomItem(TEST_USERS);
        let blockedRequests = 0;
        
        // Enviar 150 requests en 1 minuto (límite es 120/min según main.py)
        for (let i = 0; i < 150; i++) {
            const response = http.post(
                `${BASE_URL}/webhooks/whatsapp`,
                JSON.stringify({
                    object: 'whatsapp_business_account',
                    entry: [{
                        changes: [{
                            value: {
                                messages: [{
                                    from: user.id,
                                    text: { body: 'Test rate limit' },
                                }],
                            },
                        }],
                    }],
                }),
                { headers: { 'Content-Type': 'application/json' } }
            );
            
            if (response.status === 429) {
                blockedRequests++;
            }
            
            sleep(0.4);  // 150 requests en ~60 segundos
        }
        
        check({ blockedRequests }, {
            'Rate limit activo (>20 bloqueados)': (data) => data.blockedRequests > 20,
        });
    });
}

// ===== HEALTH CHECK DURANTE CARGA =====

export function healthCheckDuringLoad() {
    const response = http.get(`${BASE_URL}/health/ready`);
    
    check(response, {
        'Health check OK durante carga': (r) => r.status === 200,
        'Health check rápido < 500ms': (r) => r.timings.duration < 500,
    });
}

// ===== TEARDOWN: REPORTE FINAL =====

export function teardown(data) {
    console.log('\n========================================');
    console.log('📊 K6 LOAD TEST REPORT');
    console.log('========================================');
    console.log(`Scenario: ${SCENARIO}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log('========================================\n');
}

// ===== SETUP: VALIDACIONES INICIALES =====

export function setup() {
    // Validar que el servicio está disponible
    const healthCheck = http.get(`${BASE_URL}/health/live`);
    
    if (healthCheck.status !== 200) {
        throw new Error(`❌ Servicio no disponible: ${healthCheck.status}`);
    }
    
    console.log('✅ Servicio disponible, iniciando load test...');
    return { startTime: Date.now() };
}
