#!/usr/bin/env bash
# [PROMPT GA-01] Script de Health Check
set -euo pipefail

docker compose ps

# Ejecuta un pequeño script de Python dentro del contenedor para evitar depender de curl/wget
docker compose exec agente-api python - <<'PY'
import sys
import urllib.request
try:
	with urllib.request.urlopen('http://localhost:8000/health/ready', timeout=5) as r:
		if r.status != 200:
			print('Health check failed with status', r.status)
			sys.exit(1)
		print('Health check OK')
except Exception as e:
	print('Health check error:', e)
	sys.exit(1)
PY
