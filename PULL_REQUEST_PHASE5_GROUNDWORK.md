# feat(phase5): groundwork multi-tenant, canary inicial y smoke performance gating

## Resumen
Introduce groundwork de Fase 5:
- Tenancy lógico básico (`tenant_context` + propagación en gateway y orchestrator)
- Feature flags groundwork (añadidos previamente) + fallback NLP mejorado activable
- Canary script inicial: despliegue aislado, readiness, captura de p95 base y gating preliminar
- Smoke test k6 + gating en CI (P95 ≤ 450ms, error_rate ≤ 1%)
- Métricas nuevas: `feature_flag_enabled`, `tenant_request_total`, `tenant_request_errors`
- Documentación ampliada (`README-Infra.md` sección Performance Smoke Gating)
- Tests unitarios: feature flags (previo) + tenant context

## Archivos modificados
- agente-hotel-api/.github/workflows/perf-smoke.yml
- agente-hotel-api/Makefile
- agente-hotel-api/README-Infra.md
- agente-hotel-api/app/services/message_gateway.py
- agente-hotel-api/app/services/tenant_context.py
- agente-hotel-api/scripts/canary-deploy.sh
- agente-hotel-api/scripts/eval-smoke.sh
- agente-hotel-api/tests/performance/smoke-test.js
- agente-hotel-api/tests/unit/test_tenant_context.py

## Cómo Probar
```bash
# 1. Smoke local
make -C agente-hotel-api k6-smoke

# 2. Canary dry-run
tpush=$(git rev-parse --short HEAD)
(cd agente-hotel-api && bash scripts/canary-deploy.sh --dry-run staging $tpush)

# 3. Canary real (requiere stack + Prometheus en marcha)
(cd agente-hotel-api && bash scripts/canary-deploy.sh staging $tpush)
```

Verificar summary:
```bash
cat agente-hotel-api/reports/performance/smoke-summary.json
```

## Limitaciones Actuales
| Área | Limitación | Plan Futuro |
|------|------------|-------------|
| Tenancy | Mapping estático en memoria | Carga dinámica desde DB/config | 
| Canary | No compara baseline vs canary con tráfico real | Generar tráfico dirigido + PromQL diff |
| Gating | Umbrales fijos | Ajuste adaptativo según error budget |
| NLP | Sin métrica fallback ratio | Exponer `nlp_fallback_low_confidence_ratio` |
| Flags | Sin endpoint de inspección | Endpoint admin /admin/feature-flags |

## Riesgos & Mitigación
| Riesgo | Mitigación |
|--------|-----------|
| Falsos positivos en gating por baja muestra | Aumentar duración en entornos ruidosos |
| Tenant incorrecto para un user_id nuevo | Fallback seguro a `default` + logging |
| Canary no detecta degradaciones leves | Añadir comparación relativa baseline/canary |
| Float drifts p95 en ambiente bajo tráfico | Usar tráfico sintético controlado |

## Métricas Clave Añadidas
- `feature_flag_enabled{flag="..."}`
- `tenant_request_total{tenant_id}` / `tenant_request_errors{tenant_id}`

## Checklist PR
- [ ] CI verde
- [ ] Gating smoke pasa (p95 y error_rate OK)
- [ ] Docs actualizadas
- [ ] Revisión de seguridad superficial (sin secretos expuestos)
- [ ] Preparar tag post-merge: `v0.5.0-phase5-start`

## Próximos Issues Sugeridos
1. chore(canary): generar tráfico sintético y comparar baseline vs canary
2. feat(tenant): fuente persistente dynamic mapping
3. perf(smoke): publicar artifact y graficar histórico p95 (dashboard)
4. feat(nlp): métrica fallback ratio
5. feat(admin): endpoint listado flags/tenants
6. reliability(gating): ajuste dinámico thresholds por error budget

---
Listo para revisión. Comentarios y ajustes bienvenidos.
