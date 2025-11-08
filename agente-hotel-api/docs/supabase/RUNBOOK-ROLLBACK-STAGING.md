# RUNBOOK: Rollback rápido a staging (≤ 15 minutos)

Este procedimiento revierte la versión de staging a un tag conocido estable.

## Requisitos
- Acceso al host de staging y al repositorio
- Tag estable existente (ej.: `vSTAGING-20251108`)

## Pasos
1) Confirmar tag objetivo y comunicar inicio (2 min)
- Verificar tag y commit:
  - git fetch --tags
  - git show <TAG>
- Avisar en canal de incidentes: "Inicio rollback a <TAG>"

2) Preparar artefactos (3-5 min)
- Checkout del tag:
  - git checkout <TAG>
- Renderizar Alertmanager (opcional):
  - make alertmanager-render
- Exportar env de staging (si aplica):
  - source .env.staging

3) Desplegar (5-7 min)
- Docker Compose staging:
  - docker compose -f docker-compose.staging.yml pull
  - docker compose -f docker-compose.staging.yml up -d --force-recreate

4) Verificación rápida (3-5 min)
- Healthchecks:
  - curl http://localhost:8002/health/live
  - curl http://localhost:8002/health/ready
- Métricas:
  - curl "http://localhost:9090/api/v1/query?query=up"
- Smoke (si aplica):
  - scripts/smoke_staging.sh

5) Cierre
- Comunicar "Rollback completado a <TAG>"
- Crear ticket de causa raíz si procede.

## Notas
- Si migraciones irreversibles: evaluar `alembic downgrade` antes del despliegue.
- Mantener al menos 2 tags estables disponibles.
