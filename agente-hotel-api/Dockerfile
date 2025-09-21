# [PROMPT GA-01 - CORRECCIÓN] Dockerfile para el servicio Agente API

# Etapa de construcción
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar uv
RUN pip install uv

# Copiar solo el archivo de dependencias y instalar
COPY pyproject.toml ./
RUN uv pip install --system --no-cache --all-extras -r pyproject.toml

# Etapa final
FROM python:3.12-slim

WORKDIR /app

# Copiar dependencias de la etapa de construcción
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar el código de la aplicación
COPY ./app ./app

# Exponer puerto y ejecutar aplicación
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
