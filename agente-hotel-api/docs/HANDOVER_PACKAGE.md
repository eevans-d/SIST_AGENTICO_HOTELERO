---
title: Handover Package - Agente Hotelero API
last_updated: 2025-10-26
owner: Backend AI Team
---

# Handover Package

Este documento resume todo lo necesario para transferir la operación del servicio.

## 1. Enlaces críticos
- Salud: https://agente-hotel-api.fly.dev/health/ready
- Monitoring (Fly): https://fly.io/apps/agente-hotel-api/monitoring
- Prometheus/Grafana/Alertmanager (local docker-compose)

## 2. Repositorio y estructura
- Raíz del proyecto: `agente-hotel-api/`
- Despliegue: `fly.toml` + `Dockerfile.optimized`
- Infra local: `docker-compose.yml`
- Observabilidad: `docker/` + `docs/operations/` + `docs/runbooks/`

## 3. Operación diaria
- Revisar health y métricas cada mañana.
- Seguir los runbooks de `docs/runbooks/` ante incidentes.
- Backups: `scripts/backup-restore.sh` (Postgres).

## 4. Despliegue
1. Revisar CI y verificador: `scripts/final-verification.sh`.
2. Deploy remoto: `flyctl deploy --remote-only -a agente-hotel-api`.
3. Validar /health/ready.

## 5. Seguridad
- Rotar secretos trimestralmente.
- Ejecutar `make security-fast` y revisar `trivy`.

## 6. Contactos
- On-call: Backend Lead (primario), DevOps (secundario).

Para más detalle, ver `docs/PRODUCTION-LAUNCH-RUNBOOK.md` y `DEPLOYMENT_STATUS.md`.
