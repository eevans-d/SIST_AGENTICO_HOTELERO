# Fase 5 – Backlog de Issues Propuestos

Este documento consolida las tareas siguientes tras el groundwork inicial (tenant básico, flags, canary inicial, smoke gating).

## Prioridad Alta (A)
### 1. chore(canary): tráfico sintético y comparación baseline vs canary
Descripción: Generar tráfico controlado (k6 corto) antes y durante canary y comparar p95 & error rate entre ambas instancias.
Criterio Aceptación:
- Script canary genera baseline antes del despliegue
- Reporte con delta (% de cambio p95 y error_rate)
- Falla si p95_canary > p95_base * 1.10 o error_rate_canary > error_rate_base * 1.5 (mínimos absolutos configurables)
Artifact: `reports/canary/canary-report-<timestamp>.json`

### 2. feat(tenant): mapping dinámico persistente
Descripción: Reemplazar mapa en memoria por carga desde tabla (p.ej. `tenants` en Postgres) con cache Redis TTL 60s.
Criterio Aceptación:
- Tabla `tenants(id, pattern, active)`
- Servicio con match por patrón (regex simple) sobre user_id
- Tests de carga y fallback

### 3. reliability(gating): thresholds adaptativos basados en error budget
Descripción: Ajustar P95 límite smoke según error budget restante.
Criterio Aceptación:
- Script `eval-smoke.sh` consulta Prometheus (error_budget_remaining)
- Regla: si budget <80% bajar umbral p95 a 420ms; si <60% a 400ms

## Prioridad Media (B)
### 4. feat(nlp): métrica nlp_fallback_low_confidence_ratio
Descripción: Exponer ratio de mensajes con fallback por low confidence.
Criterio Aceptación:
- Counter incrementa en fallback
- Recording rule ratio 5m
- Panel en dashboard

### 5. feat(admin): endpoint /admin/feature-flags (GET)
Descripción: Listar flags actuales, fuente (default/redis), valor efectivo.
Criterio Aceptación:
- Respuesta: [{"flag","value","source"}]
- Protegido por auth existente

### 6. perf(smoke): publicar artifact JSON en workflow
Descripción: Subir `smoke-summary.json` como artifact y añadir job summary en CI.
Criterio Aceptación:
- Paso GitHub Actions con `actions/upload-artifact`
- Paso final con resumen p95 / error rate

## Prioridad Baja (C)
### 7. observability(canary): panel comparativo baseline vs canary
Descripción: Dashboard con dos series paralelas (p95, error rate) y delta.
### 8. tracing: esqueleto OpenTelemetry
Descripción: Añadir dependencias OTel y tracer básico (no obligatorio en prod aún).
### 9. feat(flags): invalidación push
Descripción: Invalidate local cache de flags al cambiar valor (pub/sub Redis canal `feature_flags_events`).
### 10. docs: guía multi-tenant avanzada
Descripción: Escenarios de segmentación, límites, aislamiento futuro.

## Refinamientos Técnicos
| Issue | Tipo | Estimación | Dependencias |
|-------|------|-----------|--------------|
| Canary comparación | chore | 5-6h | Script actual canary |
| Mapping dinámico tenant | feat | 4h | DB migración |
| Threshold adaptativo | reliability | 2h | Prometheus up |
| Métrica NLP fallback | feat | 1.5h | Orchestrator flags |
| Endpoint flags | feat | 2h | Auth admin |
| Artifact smoke | perf | 1h | CI pipeline |
| Panel comparativo | obs | 1.5h | Métricas canary |
| OTel esqueleto | feat | 3h | Ninguna |
| Invalidation flags | feat | 2h | Redis pub/sub |
| Docs multi-tenant | docs | 2h | Mapping dinámico |

## Dependencias / Orden Recomendado
1. Mapping dinámico tenant (evita rehecho en capas superiores)
2. Canary comparación baseline
3. Threshold adaptativo
4. Métrica NLP fallback
5. Endpoint flags + artifact smoke
6. Invalidation flags + panel comparativo
7. OTel + docs multi-tenant

## Riesgos y Mitigación
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Query Prometheus lenta en gating | Retarda CI | Cache local 5m / reducir ventanas |
| Overhead canary sintético | Costo compute | Ejecutar solo en main & pre-release |
| Regex tenant costosa | Latencia entrada | Precompilar patrones + cache LRU |
| Telemetría extra aumenta latencia | P95 sube | Sampling / tracer noop en dev |

## Métricas a Incorporar (Nuevas)
- `canary_p95_seconds{phase}` (baseline/canary) – push gateway o etiquetado temporal
- `nlp_fallback_low_confidence_total`
- `feature_flag_cache_invalidations_total`

## Notas
Mantener cada issue autocontenida; PRs pequeños y revisables. Agregar etiquetas: `phase5`, `performance`, `reliability`, `multi-tenant` según corresponda.
