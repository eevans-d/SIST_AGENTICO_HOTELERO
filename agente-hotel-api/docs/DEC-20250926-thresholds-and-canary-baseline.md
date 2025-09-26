# Decision Record: Thresholds & Canary Baseline (2025-09-26)

Status: Accepted
Owner: Equipo Plataforma / Fase 5

## Contexto
Se establecieron umbrales iniciales de rendimiento y confiabilidad para:
- Gating de smoke test en CI
- Fallback NLP
- Preparación de canary avanzado (baseline vs canary)
- Próxima introducción de thresholds adaptativos ligados al error budget

## Decisión
1. Umbral smoke gating (CI):
   - P95 (endpoint /health/live bajo carga ligera k6 smoke): 450 ms (hard fail)
   - Error rate (smoke_error_rate): < 1%
2. Objetivo interno (post optimización ligera): P95 400 ms (no gating todavía, sólo observación)
3. Categorías NLP confianza:
   - low: < 0.45
   - medium: 0.45 ≤ x < 0.75
   - high: ≥ 0.75
4. Reglas fallback NLP (feature flag `nlp.fallback.enhanced` ON):
   - very_low_confidence (<0.45) => respuesta de clarificación agresiva
   - low_confidence_hint (0.45–0.75) => marca metadata `low_confidence` y sugiere reformulación
5. Futuros thresholds adaptativos (issue: reliability(gating)):
   - Si error budget consumido > 20% => bajar P95 gating a 420 ms
   - Si error budget consumido > 40% => bajar P95 gating a 400 ms
6. Condiciones preliminares para canary baseline diff:
   - baseline_window: últimos 5 minutos antes de canary start
   - canary_window: minutos 2–7 del canary (primer minuto de calentamiento excluido)
   - Criterios fallar:
     - p95_canary > p95_baseline * 1.10
     - error_rate_canary > error_rate_baseline * 1.5 (mínimo absoluto 0.5% si baseline casi 0)
     - fallback_ratio_canary > fallback_ratio_baseline * 1.25 (mínimo absoluto 5%) [metric a implementar]
7. Métricas derivadas a instrumentar (pendientes):
   - nlp_fallback_ratio = sum(nlp_fallback_total) / sum(orchestrator_messages_total)
   - error_budget_consumption (grabado en script periódico o consulta PromQL)

## Justificación
- Los umbrales parten de datos limitados: se fijan conservadores para detectar regresiones tempranas.
- Multiplicadores (1.10 / 1.5 / 1.25) equilibran sensibilidad vs falsos positivos en canary.
- Clasificación de confianza NLP alineada con práctica común (tramos bajo/medio/alto para ajustar fallback UX).
- Estrategia adaptativa busca preservar el error budget mensualmente sin bloquear desarrollo cuando hay holgura.

## Alternativas Consideradas
- Gating sólo en average (rechazado: no captura colas largas P95/P99).
- Fallback thresholds dinámicos por intent (rechazado fase inicial: aumenta complejidad sin baseline suficiente).
- Ventana baseline de 15m (rechazado: ralentiza ciclo de despliegue y reduce reactividad).

## Riesgos
| Riesgo | Mitigación |
|--------|------------|
| Falsos positivos canary por tráfico insuficiente | Añadir mínimo de requests por ventana antes de evaluar |
| Overfitting thresholds a /health/live | Añadir endpoints críticos a smoke en iteración 2 |
| Fallback agresivo degrada UX | Monitorear ratio y ajustar tramos si > 25% sostenido |

## Acciones de Seguimiento
- Implementar script PromQL para baseline/canary (issue canary diff)
- Añadir cálculo de fallback_ratio (counter derivado o recording rule)
- Ajustar workflow perf-smoke para publicar summary en job summary (issue artifact ya creado)
- Crear panel "NLP Quality" en Grafana (issue observability canary / nlp)

## Revisión
Reevaluar el 2025-10-10 o antes si:
- P95 real promedio < 300 ms 7 días → bajar threshold gating inicial
- Fallback ratio < 8% sostenido → reconsiderar tramos de confianza

---
Decision ID: DEC-20250926-01
