# Definition of Done (DoD) - Agente Hotelero

Esta checklist se aplica a TODA historia/feature/epic que llegue a merge en `main`.

## Núcleo (Obligatorio)
- [ ] Código implementado y revisado (peer review) sin comentarios bloqueantes.
- [ ] Tests: al menos 1 happy path + 1 error/edge relevante.
- [ ] Cobertura lógica en paths críticos (no se exige % global, sí riesgo cubierto).
- [ ] CI verde: lint, unit, (integration si aplica), smoke/performance gating.
- [ ] Sin TODO/FIXME críticos no vinculados a issue.
- [ ] Dependencias nuevas justificadas (sin inflar superficie de ataque).

## Observabilidad
- [ ] Métricas clave añadidas (si feature expone comportamiento medible).
- [ ] No incremento explosivo de cardinalidad (revisión manual < 200 series nuevas).
- [ ] Logs estructurados (sin PII, con `correlation_id`).
- [ ] Panel/Grafana actualizado o issue de panel creado.

## Feature Flags / Config
- [ ] Flag creado (si el cambio es degradable) con default seguro.
- [ ] Documentado en `feature_flag_service` / README sección flags.
- [ ] Plan de retiro del flag (fecha o condición) anotado en issue.

## Seguridad
- [ ] Inputs validados/sanitizados.
- [ ] Sin secretos en código/plano commits.
- [ ] Escaneos (gitleaks/Trivy) sin High/Critical nuevos.
- [ ] Permisos mínimos (principio de menor privilegio) respetados.

## Multi-Tenancy (si aplica)
- [ ] Keys/identificadores namespaced por `tenant_id`.
- [ ] Métricas incluyen `tenant_id` sólo si cardinalidad controlada.
- [ ] Mapeo de tenant dinámico soporta fallback seguro.

## PMS / Integraciones Externas (si aplica)
- [ ] Retries con backoff + circuit breaker evaluado.
- [ ] Cache/TLL definidos si es lectura idempotente frecuente.
- [ ] Errores externos traducidos a excepciones propias.

## Despliegue y Rollback
- [ ] Script/make target actualizado si se requiere paso nuevo.
- [ ] Cambio reversible (flag, rollback de schema, etc.).
- [ ] Canary path considerado (no rompe métricas existentes).

## Documentación
- [ ] README-Infra o doc específica actualizada.
- [ ] Decision record creado si se introdujo umbral/proceso nuevo.
- [ ] Runbook agregado/actualizado si afecta operación.

## Gobernanza / Gestión
- [ ] Issue(s) vinculados cerrados o movidos a "Done".
- [ ] Etiquetas correctas aplicadas (phase5, reliability, etc.).
- [ ] Changelog (si release multi-feature) preparado.

## Validación Final
- [ ] Riesgos residuales listados (si alguno) con owners.
- [ ] Confirmado que no hay regresiones en benchmarks smoke.
- [ ] Confirmado que los flags por defecto no abren comportamiento experimental en producción.

Firma del Revisor Técnico: __________________ Fecha: ___________

> Si alguna casilla no aplica, marcar N/A y documentar justificación breve en el PR.
