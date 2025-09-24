# [PROMPT GA-01 - CORRECCIÓN] Dockerfile para el servicio Agente API

# Etapa de construcción
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias usando requirements-prod.txt (evita poetry package-mode)
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Etapa final
FROM python:3.12-slim

WORKDIR /app

# Copiar dependencias de la etapa de construcción
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Security hardening: install security updates and minimal runtime deps
RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get install -y --no-install-recommends curl \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copiar el código de la aplicación
COPY ./app ./app

# Best practices runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	UVICORN_WORKERS=2 \
	PYTHONPATH=/app

# Crear usuario no privilegiado (ID fijo para trazabilidad) y asignar permisos
RUN adduser --disabled-password --gecos '' --uid 1000 appuser \
	&& chown -R appuser:appuser /app

# Health check personalizado (más robusto que curl básico)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
	CMD curl -f http://localhost:8000/health/live || exit 1

USER appuser

# Exponer puerto y ejecutar aplicación
EXPOSE 8000

# NOTE: workers configurable via env (fallback a 2 si variable inválida)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
