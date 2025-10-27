---
title: Release Checklist - Agente Hotelero API
last_updated: 2025-10-27
owner: Backend AI Team
---

# Release Checklist (staging/production)

1) Verificación previa
- [ ] `scripts/final-verification.sh` → 0 FAIL, ≤2 WARN
- [ ] Trivy: sin CRITICAL/HIGH no justificados (waivers documentados)
- [ ] Tests de humo: `pytest tests/test_health.py` OK

2) Configuración
- [ ] Secrets actualizados en Fly (DB/Redis/JWT/etc.)
- [ ] Flags de readiness correctos para entorno
- [ ] PMS_TYPE correcto (mock en dev, qloapps en stage/prod)

3) Build & Deploy
- [ ] Build en CI: ruff OK, mypy warn-only, tests rápidos OK
- [ ] Imagen con `Dockerfile.optimized` (INCLUDE_AUDIO según necesidad)
- [ ] Deploy ejecutado y health `/health/ready` en 200

4) Post-deploy
- [ ] Logs sin errores recurrentes
- [ ] Métricas estables (latencia P95, error rate, circuit breaker)
- [ ] Alertas Prometheus activas y saneadas

5) Documentación
- [ ] Actualizar `README-Infra.md` si hubo cambios relevantes
- [ ] Registrar versión/notas en CHANGELOG o equivalente
