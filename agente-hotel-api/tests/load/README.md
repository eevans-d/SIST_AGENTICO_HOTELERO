# P010: Load Testing & Performance

## 📋 Overview

Load testing suite para validar performance del sistema bajo diferentes condiciones de carga:

- **Normal Load**: Carga típica de producción (120 VUs, 5 min)
- **Spike Load**: Elasticidad ante picos repentinos (0→500 VUs)
- **Soak Test**: Estabilidad long-running (200 VUs, 30 min)
- **Stress Test**: Breaking point y graceful degradation

## 🎯 SLOs Validados

| Scenario | P95 Latency | Error Rate | Success Rate |
|----------|-------------|------------|--------------|
| **Normal** | < 3s | < 1% | > 99% |
| **Spike** | < 5s | < 5% | > 95% |
| **Soak** | < 3.5s | < 2% | > 98% |
| **Stress** | < 10s | < 20% | > 80% |

## 🚀 Ejecución

### Prerequisitos

```bash
# Instalar k6
# MacOS
brew install k6

# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6

# Docker
docker pull grafana/k6
```

### Ejecutar Todos los Scenarios

```bash
# Desde root del proyecto
k6 run tests/load/k6-scenarios.js
```

Esto ejecutará los 4 scenarios en secuencia:
1. Normal Load (5 min)
2. Spike Load (3 min)
3. Soak Test (30 min)
4. Stress Test (16 min)

**Total duration**: ~54 minutos

### Ejecutar Scenario Individual

#### Normal Load (5 min)
```bash
k6 run tests/load/k6-scenarios.js --scenario normal_load
```

#### Spike Load (3 min)
```bash
k6 run tests/load/k6-scenarios.js --scenario spike_load
```

#### Soak Test (30 min)
```bash
k6 run tests/load/k6-scenarios.js --scenario soak_test
```

#### Stress Test (16 min)
```bash
k6 run tests/load/k6-scenarios.js --scenario stress_test
```

### Ejecutar con Output Personalizado

```bash
# JSON output
k6 run --out json=results/k6-results.json tests/load/k6-scenarios.js

# InfluxDB (para visualización en Grafana)
k6 run --out influxdb=http://localhost:8086/k6 tests/load/k6-scenarios.js

# CSV output
k6 run --out csv=results/k6-results.csv tests/load/k6-scenarios.js
```

## 📊 Validación de Resultados

Después de ejecutar los tests, validar SLOs:

```bash
python tests/load/validate_k6_results.py results/k6-summary.json
```

Output esperado:
```
================================================================================
K6 LOAD TEST VALIDATION
================================================================================

📊 GENERAL METRICS
--------------------------------------------------------------------------------
  HTTP Request Duration:
    - Avg: 1234.56ms
    - P95: 2345.67ms
    - P99: 3456.78ms
  Iterations:
    - Total: 12345
    - Rate: 45.67/s
  Virtual Users:
    - Max: 500

🎯 SCENARIO: NORMAL
--------------------------------------------------------------------------------
  ✅ P95 Latency: 2345.67ms (SLO: < 3000ms)
  ✅ Error Rate: 0.45% (SLO: < 1%)
  ✅ Success Rate: 99.55% (SLO: > 99%)

================================================================================
VALIDATION SUMMARY
================================================================================

✅ Passed Checks: 12
❌ SLO Violations: 0

RESULT: ✅ PASSED - All SLOs met
================================================================================
```

## 📈 Métricas Monitoreadas

### Métricas HTTP
- `http_req_duration`: Latencia de requests (P95, P99, avg)
- `http_req_failed`: Tasa de error
- `http_reqs`: Throughput (requests/sec)

### Métricas Personalizadas
- `reservation_duration`: Tiempo de creación de reserva
- `availability_duration`: Tiempo de consulta de disponibilidad
- `whatsapp_duration`: Tiempo de procesamiento de mensajes WhatsApp
- `pms_calls`: Contador de llamadas al PMS
- `circuit_breaker_opens`: Contador de circuit breaker abierto
- `rate_limit_hits`: Contador de rate limiting (429)
- `concurrent_users`: Gauge de usuarios concurrentes

### Checks
- Validación de status codes (200, 201, 202)
- Validación de response bodies (formato JSON válido)
- Validación de tiempos de respuesta individuales

## 🔧 Configuración

### Variables de Entorno

```bash
# URL base del sistema
export BASE_URL=http://localhost:8000

# Token de WhatsApp (para autenticación)
export WHATSAPP_TOKEN=your_test_token_here
```

### Ajustar Thresholds

Editar `tests/load/k6-scenarios.js`:

```javascript
export const options = {
  thresholds: {
    'http_req_duration{scenario:normal}': ['p(95)<3000'],  // Cambiar valor
    'errors{scenario:normal}': ['rate<0.01'],              // Cambiar valor
    // ...
  },
};
```

## 🐛 Troubleshooting

### Error: "Sistema no ready"
```bash
# Verificar health del sistema
curl http://localhost:8000/health/ready

# Si retorna 503, verificar:
# - PostgreSQL está corriendo
# - Redis está corriendo
# - PMS adapter está configurado
```

### Error: "Too many open files"
```bash
# Aumentar límite de file descriptors (Linux/Mac)
ulimit -n 10000
```

### Rate Limiting Durante Tests
```bash
# Desactivar rate limiting para tests (solo desarrollo)
# En .env:
DEBUG=true  # Esto deshabilita rate limiting
```

### Resultados Inconsistentes
```bash
# Limpiar cache entre runs
redis-cli FLUSHALL

# Reiniciar servicios
docker compose restart
```

## 📚 Recursos Adicionales

- [k6 Documentation](https://k6.io/docs/)
- [k6 Test Types](https://k6.io/docs/test-types/introduction/)
- [k6 Metrics](https://k6.io/docs/using-k6/metrics/)
- [k6 Thresholds](https://k6.io/docs/using-k6/thresholds/)

## ✅ Checklist de Ejecución

Antes de ejecutar load tests en producción:

- [ ] Sistema en estado estable (sin deploys recientes)
- [ ] Monitoreo activo (Prometheus + Grafana)
- [ ] Alert manager configurado
- [ ] Backup reciente de base de datos
- [ ] Rate limiting ajustado (o deshabilitado para tests)
- [ ] Recursos suficientes (CPU, memoria, conexiones DB)
- [ ] Ventana de mantenimiento programada (para soak test)
- [ ] Stakeholders notificados

## 🎯 Criterios de Aceptación

Para considerar P010 completado:

- [x] Archivo `k6-scenarios.js` con 4 scenarios implementados
- [x] Script `validate_k6_results.py` funcional
- [x] README con instrucciones de ejecución
- [ ] Al menos 1 run exitoso de cada scenario
- [ ] Validación de SLOs pasando
- [ ] Reporte de resultados documentado

---

**Prioridad**: ALTA 🟡  
**Esfuerzo estimado**: 4 horas  
**Tests implementados**: 4 scenarios + validación
