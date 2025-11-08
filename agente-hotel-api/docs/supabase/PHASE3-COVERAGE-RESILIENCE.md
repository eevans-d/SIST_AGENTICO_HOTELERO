# FASE 3: Cobertura y Resiliencia

Estado inicial (baseline 2025-11-08):
- Cobertura global: ~31% (threshold actual --cov-fail-under=32)
- Servicios críticos (<objetivo 85%>): orchestrator, pms_adapter, session_manager, lock_service.
- Circuit breaker PMS: tests presentes (métricas y apertura) pero falta prueba end-to-end de ciclo completo CLOSED→OPEN→HALF_OPEN→CLOSED.
- Locks: Cobertura parcial; sin prueba de contención simultánea alta.
- Session TTL: Sin prueba explícita de preservación TTL tras updates.

## Objetivos Medibles
1. Cobertura global → 40% (hito intermedio) en ≤ 5 días laborales.
2. Cobertura crítica (archivos clave) → 60% mínimo en esta fase (luego fase 4 → 85%).
3. Añadir pruebas de resiliencia:
   - Circuit breaker ciclo completo (incluyendo HALF_OPEN success y HALF_OPEN failure).
   - Atomicidad de lock ante 10 corrutinas concurrentes.
   - TTL sesión conserva expiración ±5% tras actualización.
4. Script canary helper para emitir P95 y error_rate comparables (baseline vs staging).
5. Runbook rollback estandarizado ≤ 15 min ejecución.
6. Revisión de índices DB con al menos 3 recomendaciones accionables.

## KPIs y Métricas
- kpi_coverage_global_phase3_target = 0.40
- kpi_coverage_critical_phase3_target = 0.60
- kpi_resilience_tests_added = 3
- kpi_lock_contention_success_rate = 100% (solo un ganador por intento)
- kpi_ttl_preservation_delta_seconds < 0.05 * ttl_configurada

## Plan de Incremento de Cobertura (Iterativo)
| Semana | Acción | Archivos | Meta % local |
|--------|--------|----------|--------------|
| 1 | Añadir tests CB ciclo completo + lock atomicidad | circuit_breaker.py, lock_service.py | 33-34% |
| 2 | Añadir session TTL + escenarios de cache optimizer | session_manager.py, cache_optimizer.py | 36-38% |
| 3 | Añadir tests de fallbacks NLP + feature flags | orchestrator.py, feature_flag_service.py | 38-40% |

(Se evalúa subir threshold tras consolidar cada escalón sin romper pipeline.)

## Riesgos
- Subir threshold demasiado pronto → build roja recurrente.
- Tests de tiempos (HALF_OPEN) flakey si sleep insuficiente.
- Contención con Redis real puede requerir backoff.

Mitigaciones:
- Usar recovery_timeout reducido en test (100ms).
- Aislar lock test con cliente Redis in-memory stub.
- No subir threshold hasta ver cobertura >= target escalón.

## Checklist de Ejecución
- [x] Documento fase 3 creado.
- [ ] Test circuito breaker ciclo completo.
- [ ] Test lock atomicidad (10 corrutinas, 1 éxito único, resto fallback).
- [ ] Test session TTL preservación.
- [ ] Subir threshold cobertura a 33-35 (cuando >=35% real).
- [ ] Script canary metrics helper.
- [ ] Runbook rollback staging.
- [ ] Revisión índices DB + recomendaciones.
- [ ] Reporte progreso cobertura (Makefile target coverage-report).

## Próximo Paso Inmediato
Implementar test de ciclo completo circuit breaker con recovery_timeout reducido.
