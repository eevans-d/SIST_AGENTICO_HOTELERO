# Fase 3: Performance Testing & Chaos Engineering

## Resumen

La **Fase 3** implementa un framework completo de pruebas de rendimiento y chaos engineering para validar la resiliencia del sistema bajo condiciones extremas y fallos simulados.

## Componentes Implementados

### 1. Framework de Pruebas de Rendimiento (k6)

#### Pruebas de Carga (`load-test.js`)
```bash
make performance-test
```

**Características:**
- Simulación de comportamiento realista de usuarios
- Perfil de carga multi-etapa (10→50→100→200→0 usuarios)
- Métricas customizadas (errorRate, responseTime, requests)
- Selección aleatoria de endpoints con pesos realistas
- Patrones de sleep variables para simular interacción humana

**Métricas Recolectadas:**
- Tasas de error por endpoint
- Tiempos de respuesta (P95, P99)
- Throughput de requests
- Distribución de carga por servicio

#### Pruebas de Estrés (`stress-test.js`)
```bash
make stress-test
```

**Características:**
- Análisis de punto de ruptura (hasta 500 VUs)
- Detección de errores críticos
- Medición de tiempo de recuperación
- Verificación post-test de salud del sistema
- Métricas de degradación gradual

### 2. Chaos Engineering

#### Simulación de Falla de Base de Datos
```bash
make chaos-db
```

**Escenarios:**
- Parada abrupta de PostgreSQL
- Monitoreo de comportamiento durante falla
- Medición de tiempo de detección
- Validación de circuit breakers
- Análisis de recuperación automática

#### Simulación de Falla de Cache Redis
```bash
make chaos-redis
```

**Escenarios:**
- Parada del servicio Redis
- Partición de red simulada
- Presión de memoria extrema
- Degradación gradual de performance
- Recuperación de cache warming

### 3. Dashboard de Resiliencia

**Ubicación:** `docker/grafana/dashboards/resilience-dashboard.json`

**Métricas Visualizadas:**
- **SLO Overall:** Success rate y error budget consumption
- **Burn Rates:** Fast (5m) y Slow (1h) burn rates
- **Circuit Breakers:** Estado en tiempo real
- **Cache Performance:** Hit ratios y degradación
- **Predictive Metrics:** Failure ratios y tiempo hasta circuit breaker open

**Acceso:**
```bash
make open-resilience-dashboard
# URL: http://localhost:3000/d/resilience-chaos/
```

### 4. Suite Integrada de Pruebas

#### Test Suite Completo
```bash
make resilience-test
```

**Flujo Automatizado:**
1. **Pruebas de Performance:** Load test → Recovery → Stress test
2. **Chaos Engineering:** DB failure → Recovery → Redis failure
3. **Recolección de Métricas:** Queries automáticas a Prometheus
4. **Generación de Reportes:** Markdown reports con análisis

#### Reportes Generados
- `performance-summary-{timestamp}.md`
- `chaos-summary-{timestamp}.md`
- `resilience-report-{timestamp}.md`
- Raw data: JSON outputs de k6 y logs de chaos

### 5. Análisis y Visualización

#### Análisis de Performance
```bash
make analyze-performance REPORT=20241203_143022
```

#### Análisis de Chaos
```bash
make analyze-chaos REPORT=20241203_143022
```

## Integración con Guardrails

Todas las pruebas respetan los límites configurados en `guardrails.conf`:

- **Timeouts:** Tests limitados a duración máxima
- **Recovery Periods:** Esperas obligatorias entre tests
- **Resource Limits:** Prevención de resource exhaustion
- **Circuit Breakers:** Respeto a umbrales de seguridad

## Casos de Uso

### Desarrollo
- Validación de cambios bajo carga
- Detección temprana de regressions de performance
- Testing de nuevas features con chaos injection

### Staging
- Validación pre-producción completa
- Calibración de circuit breakers
- Tuning de cache strategies

### Producción
- Health checks regulares programados
- Validación post-deploy
- Análisis de incident response

## Métricas Clave

### Performance
- **Throughput:** Requests/second sostenible
- **Latency:** P95 < 500ms, P99 < 1s
- **Error Rate:** < 1% bajo carga normal
- **Breaking Point:** Identificación de límites

### Resilience
- **Circuit Breaker Response:** < 10s para abrir
- **Recovery Time:** < 30s post-falla
- **Graceful Degradation:** Funcionalidad core mantenida
- **Data Consistency:** Sin pérdida durante fallos

## Comandos de Instalación

```bash
# Instalar k6
make install-k6

# Validar setup completo
make validate-guardrails
make test-circuit-breakers
```

## Próximos Pasos (Fase 4)

1. **Governance:** Políticas de testing obligatorio
2. **Runbooks:** Procedimientos detallados de incident response
3. **SLO Tuning:** Ajuste fino basado en resultados
4. **Automation:** CI/CD integration para pruebas automáticas

## Archivos Clave

```
tests/performance/
├── load-test.js           # Pruebas de carga realistas
└── stress-test.js         # Análisis de punto de ruptura

scripts/
├── chaos-db-failure.sh    # Simulación falla DB
├── chaos-redis-failure.sh # Simulación falla cache
├── resilience-test-suite.sh # Suite completa
└── guardrails.conf        # Configuración de límites

docker/grafana/dashboards/
└── resilience-dashboard.json # Dashboard Grafana

reports/resilience/        # Directorio de reportes
├── *-{timestamp}.json     # Raw data
├── *-{timestamp}.log      # Chaos logs
└── *-{timestamp}.md       # Análisis y resúmenes
```

---

**Estado:** ✅ **FASE 3 COMPLETADA**
**Validación:** Todas las pruebas funcionan correctamente
**Dashboard:** Disponible en Grafana
**Integración:** Makefile actualizado con todos los comandos