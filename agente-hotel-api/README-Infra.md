# [PROMPT GA-01] Documentación de Infraestructura

## Stack Tecnológico

- **Orquestación:** Docker Compose
- **Reverse Proxy:** NGINX
- **Servicios:**
  - `agente-api`: Aplicación FastAPI.
  - `qloapps`: PMS.
  - `postgres`: Base de datos para el agente.
  - `mysql`: Base de datos para QloApps.
  - `redis`: Cache y locks.
  - `prometheus`, `grafana`, `alertmanager`: Stack de monitorización.

## Redes

- `frontend_network`: Expuesta al exterior, para NGINX.
- `backend_network`: Red interna para la comunicación entre servicios.

## Comandos

- `make docker-up`: Inicia el stack.
- `make docker-down`: Detiene el stack.
- `make health`: Verifica la salud de los servicios.
- `make backup`: Crea un backup de las bases de datos.
