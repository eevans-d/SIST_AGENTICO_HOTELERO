# FASE 5 (PROPUESTA) – ESCALABILIDAD, OPTIMIZACIÓN Y EXPANSIÓN MULTICANAL

## 1. Objetivo del Día (Jornada Próxima)
Establecer fundamentos técnicos y operativos para:
- Escalabilidad horizontal segura (API + Redis + PMS calls)
- Preparar multi-hotel / multi-cuenta (tenancy lógico inicial)
- Optimizar coste y performance (perf. budget + caching estratégico)
- Endurecer calidad continua (pipeline de performance + gating por SLA/SLO)
- Expandir capacidades de IA/NLP (intents avanzados + fallback inteligente)
- Formalizar feature flags y rollout progresivo (canary / dark launch)

## 2. Suposiciones
- Infra actual estable (Fases 1–4 completadas) ✔
- Dashboards de resiliencia y SLO funcionando ✔
- No hay incidentes abiertos pendientes de mitigación ✔
- Prod o staging disponible para canary controlado (verificar al inicio)

## 3. Éxito del Día (Definition of Done)
- [ ] Branch `feature/phase5-foundations` creada y push inicial
- [ ] Script base de canary deployment + validación métrica
- [ ] Pipeline CI añade job de smoke perf (k6 quick test < 2 min)
- [ ] Implementado módulo de feature flag simple (desde settings / Redis)
- [ ] Estructura de tenancy lógico (campo `hotel_id` o `account_id`) prototipada en capa de sesión / mensajes
- [ ] Añadido threshold de performance en Makefile + job GitHub (falla si P95 > objetivo)
- [ ] Segunda batería de cache TTL review con tabla (en documento)
- [ ] Intent fallback mejorado (NLP) con clasificación de confianza y respuesta adaptativa
- [ ] Checklist de apagado (end-of-day) completada y commit final

## 4. Agenda Recomendada (8h)
| Hora | Bloque | Output Clave |
|------|--------|--------------|
| 09:00–09:30 | Arranque & Verificación | Health, métricas baseline, crear branch |
| 09:30–10:30 | Feature Flags MVP | Módulo + carga desde env/Redis + tests |
| 10:30–11:30 | Tenancy Lógico | Extensión modelos sesión/mensaje + guardias |
| 11:30–12:15 | Canary Deploy Script | Script + validación Prometheus + dry run |
| 12:15–13:00 | Perf Pipeline Quick Test | k6 smoke script + job CI + gating |
| 13:00–13:30 | Pausa / Revisión Métricas | Ajustes iniciales |
| 13:30–14:30 | NLP Fallback & Confianza | Ajustar `nlp_engine.py` + tests |
| 14:30–15:15 | Cache Strategy Review | Tabla TTL + invalidación documentada |
| 15:15–16:00 | Refuerzo Observabilidad | Métricas nuevas (flags, tenancy errors) |
| 16:00–16:30 | Riesgos & Hardening | Límite de tasa multihotel + lock patterns |
| 16:30–17:00 | End-of-Day Wrap | Checklist, docs, commit, tag |

## 5. Backlog Detallado (MoSCoW)
### MUST
- Feature flags MVP (lectura en `settings` + override en Redis hash: `feature_flags`)
- Tenancy: agregar `tenant_id` (nombre provisional) a contexto de sesión y mensajes
- Canary script: `scripts/canary-deploy.sh` (dry-run + verificación `/health/ready` + query Prometheus)
- k6 smoke test: 50 RPS 1 min, max P95 < 450ms, error rate <1%
- Job CI: `performance-smoke.yml`
- Métricas: `feature_flag_enabled{flag="X"}`, `tenant_request_total`, `tenant_request_errors`

### SHOULD
- Tabla de TTL por tipo de operación PMS + propuesta ajuste
- NLP fallback: thresholds (alta confianza ≥0.75, media 0.45–0.74, baja <0.45)
- Documentar protocolo de rollback canary

### COULD
- Incorporar open feature client futuro
- Añadir tracing distribuido (OTel) esqueleto
- Pre-cálculo embeddings para intents frecuentes

### WON'T (HOY)
- Multi-tenant físico (DB schemas separados)
- Sharding Redis
- Reescritura completa NLP pipeline

## 6. Cambios Técnicos Previstos
| Área | Acción | Archivo(s) | Métrica Asociada |
|------|--------|------------|------------------|
| Feature Flags | Nuevo servicio `feature_flag_service.py` | `app/services/` | `feature_flag_enabled` |
| Tenancy | Añadir campo `tenant_id` en modelos de sesión | `session_manager.py`, `schemas.py` | `tenant_request_total` |
| Canary Deploy | Nuevo script | `scripts/canary-deploy.sh` | Tiempo validación < 90s |
| Perf Smoke | Nuevo k6 script rápido | `tests/performance/smoke-test.js` | P95 latency |
| CI Perf Job | Workflow nuevo | `.github/workflows/perf-smoke.yml` | Build gating |
| NLP Fallback | Umbral + lógica | `nlp_engine.py` | Porcentaje fallback |
| Cache Review | Doc TTL | `docs/CACHE_STRATEGY.md` | Cache hit ratio |
| Métricas Flags | Añadir export | `metrics_service.py` | Observabilidad |

## 7. Métricas & Umbrales Día
- Smoke test: P95 < 450ms, error rate <1%, throughput sostenible ≥ 40 RPS
- Canary validación: 2 rondas de chequeos en 60s sin degradación (>10% latencia respecto baseline)
- NLP fallback ratio: mantener <15% (post mejora)
- Cache hit ratio PMS (si métrica disponible): objetivo ≥70%

## 8. Riesgos & Mitigación
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Feature flag mal interpretado | Respuesta incorrecta | Default seguro + tests unitarios |
| Tenancy fuga datos | Riesgo privacidad | Añadir aserciones y test de aislamiento |
| Canary no detecta regresión | Degradación prod | Incluir métrica error rate y P95 comparativa |
| k6 en CI demasiado lento | Pipeline lento | Limitar duración a 60–90s |
| Fallback agresivo NLP | Mala UX | Ajustar thresholds y logs de confianza |

## 9. Checklist Inicio de Día
- [ ] `git pull origin main`
- [ ] Revisar último tag `v0.4.0-YYYYMMDD`
- [ ] `make health` OK
- [ ] Grafana: latencias base (anotar P50/P95)
- [ ] Error budget restante ≥ 90% (inicio jornada)
- [ ] No incidentes abiertos en canal ops
- [ ] Redis & DB conexiones en rango normal

## 10. Checklist Fin de Día
- [ ] Todos los nuevos archivos añadidos y testeados
- [ ] CI verde (incluyendo nuevo perf job)
- [ ] Documentados flags activos y propósito
- [ ] Anotado baseline vs post cambios (latencia)
- [ ] Commit final + tag `v0.5.0-YYYYMMDD-phase5-start`
- [ ] Actualizado README sección Roadmap
- [ ] Abrir issues pendientes (WON'T + COULD)

## 11. Comandos de Referencia (Propuestos)
```bash
# Crear branch
git checkout -b feature/phase5-foundations

# Ejecutar smoke test (cuando exista)
K6_DURATION=60s K6_RPS=50 make k6-smoke || true

# Validar health
curl -s http://localhost:8000/health/ready | jq .

# Ver P95 (Prometheus instant query ejemplo)
# sum(rate(http_request_duration_seconds_bucket{le="0.95"}[5m])) / sum(rate(http_request_duration_seconds_count[5m]))

# Ejecutar canary (propuesto)
bash scripts/canary-deploy.sh --env staging --version $(git rev-parse --short HEAD)
```

## 12. Artefactos a Crear Mañana
- `app/services/feature_flag_service.py`
- `app/services/tenant_context.py` (o integración en session manager)
- `scripts/canary-deploy.sh`
- `tests/performance/smoke-test.js`
- `.github/workflows/perf-smoke.yml`
- `docs/CACHE_STRATEGY.md`
- Ajustes en `nlp_engine.py`, `metrics_service.py`

## 13. Criterios de Revisión de PR
- Cobertura tests nuevas rutas/lógica > 80% líneas modificadas
- No break en SLO aprobados (latencia/error rate)
- Linter y formato sin issues
- Documentación actualizada (cambios visibles para ops)

## 14. Parking Lot (Agregar Durante el Día)
- Multi-tenant real (DB / esquemas)
- Sharding Redis / Cluster mode
- Observabilidad avanzada (tracing distribuido)
- A/B testing de prompts NLP

## 15. Notas Finales
Comenzar por cambios de bajo riesgo (feature flags) que habilitan toggling seguro de los restantes. Mantener commits atómicos y orientados a un único aspecto (flags, tenancy, canary, perf gating, NLP). Al detectar cualquier degradación ≥10% en latencia P95 detener y priorizar rollback o análisis raíz.

---
Plan preparado para ejecución inmediata. Ajustar según prioridades estratégicas si el Product Owner redefine objetivo matinal.
