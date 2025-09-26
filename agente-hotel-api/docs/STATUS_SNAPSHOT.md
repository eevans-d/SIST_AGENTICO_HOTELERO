# Status Snapshot
Generado: 2025-09-26T04:11:54Z

## Últimos Commits
5f8b424 docs(playbook): DoD checklist y documento de propósito/gobernanza
4cb40fb docs(decision): DEC-20250926-01 thresholds & canary baseline
4dcf251 chore(issues): script fase5 mejorado (offline export) + export inicial issues
2af2027 feat(metrics): métricas NLP (confianza y fallbacks) + artefacto smoke en CI
448fccd chore(phase5): script automatizado para creación de issues y target make
06c1b1d docs(phase5): backlog detallado de issues propuestos
310dbbf docs(pr): añadir draft de Pull Request para groundwork fase 5
e815e9c test(tenant): añadir pruebas unitarias de TenantContext y doc smoke gating
b443133 chore(perf): gating smoke test con summary JSON y script eval
c51eeba feat(phase5): tenant context service, extracción tenant gateway, canary script inicial, k6 smoke test y workflow CI

## Top Issues (Phase 5 Export)
| Title | Labels | Body |
| chore(canary): tráfico sintético y comparación baseline vs canary | phase5,enhancement,performance,reliability,priority | Generar tráfico controlado (k6) antes y durante canary; comparar p95 y error rate.<br>Criterios:<br>- Baseline previo<br>- Reporte delta JSON<br>- Falla si p95_canary > p95_base *1.10 o error_rate_canary > error_rate_base *1.5 (mínimos absolutos). |
| feat(tenant): mapping dinámico persistente | phase5,enhancement,multi-tenant,priority | Reemplazar mapa en memoria por tabla 'tenants'. Cache Redis 60s. Match por patrón. Tests de aislamiento. |
| reliability(gating): thresholds adaptativos (error budget) | phase5,enhancement,reliability,performance,priority | Ajustar umbral P95 smoke según error budget restante (Prometheus). <80% => 420ms, <60% => 400ms. |
| feat(nlp): métrica fallback low confidence | phase5,enhancement,nlp,observability,priority | Exponer counter/fallback y recording rule ratio 5m. Panel en dashboard. |
| feat(admin): endpoint listado feature flags | phase5,enhancement,admin,priority | GET /admin/feature-flags => [{'flag','value','source'}]. Protegido por auth. Tests. |
| perf(smoke): publicar artifact y summary en CI | phase5,enhancement,performance,ci,priority | Subir smoke-summary.json como artifact + job summary p95/error_rate. Tabla histórica futura. |
| observability(canary): panel comparativo baseline vs canary | phase5,enhancement,observability,grafana,priority | Dashboard con series p95, error rate y delta porcentual. Añadir alertas suaves si delta>10%. |
| feat(tracing): esqueleto OpenTelemetry | phase5,enhancement,observability,tracing,priority | Añadir dependencias OTel, tracer básico (fastapi middleware), export a stdout. Sampling 1%. |
| feat(flags): invalidación push cache local | phase5,enhancement,feature-flags,priority | Canal Redis pub/sub 'feature_flags_events' para invalidar cache local en FeatureFlagService. |
| docs(tenant): guía multi-tenant avanzada | phase5,enhancement,documentation,multi-tenant,priority | Documentar segmentación, aislamiento futuro (DB/schema), patrones de escalado y riesgos. |

## Artefactos Clave
- DoD: docs/DOD_CHECKLIST.md
- Working Agreement: docs/playbook/WORKING_AGREEMENT.md
- Playbook Gobernanza: docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md
- Project Config: .playbook/project_config.yml
- Decision Records: docs/DEC-*

## Próximas Prioridades Sugeridas
1. Canary diff métrico (baseline vs canary)
2. Mapping dinámico tenants
3. Métrica fallback ratio + panel NLP
4. Endpoint admin feature flags
5. Thresholds adaptativos (error budget)
