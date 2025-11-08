# Blueprint de Próximos Pasos y Checklist Operativo

Fecha: 2025-11-08  
Ámbito: Staging Deploy, Alerting, Cobertura, Performance, Seguridad, NLP

## 0) Estado actual
- Staging listo (GO), métricas clave instrumentadas, dashboards provisionados.
- Health/readiness OK, preflight GO (risk_score=30).

## 1) Staging Deploy (operativo)
- [ ] Generar `.env.staging` desde plantilla (secretos sin `change-me`).
- [ ] Crear tag `vSTAGING-YYYYMMDD` y push.
- [ ] `docker compose -f docker-compose.staging.yml --profile pms up -d`.
- [ ] Validar `/health/ready` (3 veces, 200).
- [ ] Ejecutar `scripts/smoke_staging.sh` y archivar salida.
- [ ] Completar `STAGING-PREDEPLOY-CHECKLIST.md` sección Post-Despliegue.

## 2) Alerting (antes de producción)
- [ ] Añadir receiver Slack (webhook) y/o email en Alertmanager.
- [ ] Test alert: forzar alerta baja y verificar recepción.
- [ ] Documentar playbook de alerta crítica (P0, P1, P2).

## 3) Cobertura y Calidad (Fase 3)
- [ ] make target `coverage-report` (pytest --cov --cov-report html).
- [ ] Umbral incremental: fallo si cobertura < 32% (pytest.ini).
- [ ] Tests críticos: orchestrator (happy path), pms_adapter (CB estados), session_manager (TTL), lock_service (atomicidad básica).
- [ ] Objetivo intermedio: 55% global, 85% en críticos.

## 4) Performance y Canary
- [ ] Script canary diff (usar `make canary-diff BASELINE=main`).
- [ ] Umbrales: P95 <= +10%, error rate <= +50% vs baseline.
- [ ] Documentar pasos y PromQL en Readiness Report.

## 5) Seguridad
- [ ] Validar cabeceras Nginx endurecidas.
- [ ] `make security-fast` y resolver hallazgos.
- [ ] Revisión secretos: rotación y scopes mínimos.

## 6) NLP (no bloqueante)
- [ ] Aislar spacy en imports (fallback ya activo).
- [ ] Documentar instalación opcional para entornos con GPU/CPU.

## Entregables
- `.env.staging.template` + `.env.staging` (local).
- `scripts/smoke_staging.sh`.
- Alertmanager `config.yml` con receivers placeholders.
- `coverage-report` (htmlcov) y umbral en `pytest.ini`.
- Readiness Report actualizado con canary diff.

---
Firmas:
- Dev Backend ____  |  Ops/SRE ____  |  Producto ____
