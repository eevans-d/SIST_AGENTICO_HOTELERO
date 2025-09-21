#!/usr/bin/env bash
# [PROMPT GA-01] Script de Health Check
set -e

docker compose ps
docker compose exec agente-api curl -f http://localhost:8000/health/ready
