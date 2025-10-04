# 🐛 Debugging Guide - Agente Hotelero

Guía completa para debugging y troubleshooting en desarrollo.

## 📋 Contenido

- [Quick Debugging](#quick-debugging)
- [Common Issues](#common-issues)
- [Debugging Tools](#debugging-tools)
- [Performance Issues](#performance-issues)
- [Database Issues](#database-issues)
- [Redis Issues](#redis-issues)
- [API Issues](#api-issues)
- [Docker Issues](#docker-issues)

---

## ⚡ Quick Debugging

### First Steps (Always!)

```bash
# 1. Ver estado de servicios
make dev-status

# 2. Ver logs en tiempo real
make dev-logs

# 3. Health check
make health

# 4. Verificar tests
make test
```

### Emergency Commands

```bash
# Reiniciar todo
make dev-down && make dev-up

# Limpiar y empezar de cero
make dev-clean && make dev-up

# Ver logs de un servicio específico
docker compose -f docker-compose.dev.yml logs agente-api

# Shell en el contenedor
make dev-shell
```

---

## 🔧 Common Issues

### Issue 1: "Cannot connect to Docker daemon"

**Síntoma:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solución:**
```bash
# Linux
sudo systemctl start docker

# macOS
# Abrir Docker Desktop

# Verificar
docker ps
```

---

### Issue 2: "Port already in use"

**Síntoma:**
```
Error: bind: address already in use
```

**Solución:**
```bash
# Ver qué está usando el puerto
lsof -i :8000  # Cambiar 8000 por tu puerto
# o
netstat -tulpn | grep 8000

# Matar proceso
kill -9 <PID>

# O cambiar puerto en docker-compose.dev.yml
ports:
  - "8001:8000"  # Usa 8001 externamente
```

---

### Issue 3: "Module not found"

**Síntoma:**
```python
ModuleNotFoundError: No module named 'xxx'
```

**Solución:**
```bash
# 1. Verificar que está en pyproject.toml
cat pyproject.toml | grep xxx

# 2. Reinstalar dependencias
poetry install --all-extras

# 3. Rebuild Docker
make dev-down
docker compose -f docker-compose.dev.yml build --no-cache
make dev-up

# 4. Verificar en el contenedor
make dev-shell
poetry show
```

---

### Issue 4: "Tests failing after merge"

**Síntoma:**
```
FAILED tests/xxx.py::test_xxx
```

**Diagnóstico:**
```bash
# 1. Ejecutar test específico con verbose
pytest tests/xxx.py::test_xxx -vv -s

# 2. Con debugging
pytest tests/xxx.py::test_xxx -vv -s --pdb

# 3. Ver fixtures
pytest tests/xxx.py --fixtures

# 4. Limpiar cache
pytest --cache-clear
```

**Solución:**
```bash
# 1. Actualizar fixtures si schema cambió
# 2. Verificar mocks están actualizados
# 3. Revisar cambios en dependencias
```

---

### Issue 5: "Database migration error"

**Síntoma:**
```
alembic.util.exc.CommandError: Can't locate revision
```

**Solución:**
```bash
# 1. Ver estado actual
alembic current

# 2. Ver historia
alembic history

# 3. Reset (CUIDADO: borra datos)
make dev-clean
make dev-up

# 4. Aplicar migraciones
alembic upgrade head
```

---

### Issue 6: "Redis connection refused"

**Síntoma:**
```
redis.exceptions.ConnectionError: Connection refused
```

**Diagnóstico:**
```bash
# 1. Verificar Redis está corriendo
docker compose -f docker-compose.dev.yml ps redis

# 2. Ver logs
docker compose -f docker-compose.dev.yml logs redis

# 3. Probar conexión
docker compose -f docker-compose.dev.yml exec redis redis-cli -a dev_redis_password ping
```

**Solución:**
```bash
# 1. Reiniciar Redis
docker compose -f docker-compose.dev.yml restart redis

# 2. Verificar configuración en .env
REDIS_URL=redis://:dev_redis_password@redis:6379/0

# 3. Verificar password
REDIS_PASSWORD=dev_redis_password
```

---

### Issue 7: "Hot-reload not working"

**Síntoma:**
Cambios en código no se reflejan automáticamente

**Solución:**
```bash
# 1. Verificar volumen está montado
docker compose -f docker-compose.dev.yml config | grep -A 5 volumes

# 2. Verificar comando uvicorn
docker compose -f docker-compose.dev.yml exec agente-api ps aux | grep uvicorn

# 3. Reiniciar servicio
make dev-restart

# 4. Si sigue sin funcionar, agregar a .env:
WATCHFILES_FORCE_POLLING=true
```

---

## 🔍 Debugging Tools

### 1. Python Debugger (pdb)

```python
# En tu código
import pdb; pdb.set_trace()

# O mejor, ipdb (más features)
import ipdb; ipdb.set_trace()

# Comandos útiles en pdb:
# n - next line
# s - step into
# c - continue
# l - list code
# p variable - print variable
# pp variable - pretty print
# h - help
```

### 2. Remote Debugging (VS Code)

**Setup (.vscode/launch.json):**
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        }
    ]
}
```

**En tu código:**
```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()
# Tu código aquí
```

### 3. Logging

```python
import structlog
logger = structlog.get_logger()

# Debug info
logger.debug("Debug message", key="value")

# Info
logger.info("Info message", user_id=123)

# Warning
logger.warning("Warning message", error="details")

# Error
logger.error("Error message", exc_info=True)

# Ver logs filtrados
docker compose -f docker-compose.dev.yml logs agente-api | grep ERROR
```

### 4. Prometheus Metrics

```bash
# Ver métricas
curl http://localhost:8000/metrics

# Grafana dashboards
open http://localhost:3000

# Prometheus queries
open http://localhost:9090/graph
```

### 5. Database Inspector

```bash
# Adminer (GUI)
make dev-db-admin
open http://localhost:8080

# PostgreSQL CLI
docker compose -f docker-compose.dev.yml exec postgres psql -U agente -d agente_hotel

# Queries útiles:
\dt              # List tables
\d table_name    # Describe table
SELECT * FROM users LIMIT 5;
```

### 6. Redis Inspector

```bash
# Redis Commander (GUI)
make dev-db-admin
open http://localhost:8081

# Redis CLI
docker compose -f docker-compose.dev.yml exec redis redis-cli -a dev_redis_password

# Comandos útiles:
KEYS *           # Ver todas las keys
GET key_name     # Obtener valor
DEL key_name     # Borrar key
FLUSHDB          # Limpiar base actual
```

---

## ⚡ Performance Issues

### Issue: Slow API Response

**Diagnóstico:**
```bash
# 1. Benchmark específico
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/api/endpoint

# 2. Load test
k6 run tests/performance/load_test.js

# 3. Profile con py-spy
docker compose -f docker-compose.dev.yml exec agente-api pip install py-spy
docker compose -f docker-compose.dev.yml exec agente-api py-spy top --pid 1
```

**Soluciones comunes:**
- Agregar índices en DB
- Implementar caching (Redis)
- Optimizar queries N+1
- Usar async donde sea posible
- Pagination en listados

### Issue: High Memory Usage

**Diagnóstico:**
```bash
# Ver uso de memoria
docker stats

# Profiling de memoria
docker compose -f docker-compose.dev.yml exec agente-api pip install memory_profiler
# Agregar @profile decorator a función
# Ejecutar con: python -m memory_profiler script.py
```

**Soluciones:**
- Verificar memory leaks
- Limpiar conexiones DB
- Reducir tamaño de cache Redis
- Optimizar carga de datos

---

## 💾 Database Issues

### Ver Queries Lentos

```sql
-- PostgreSQL: Queries lentas
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE query != '<IDLE>' AND now() - query_start > interval '5 seconds';

-- Queries más ejecutadas
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

### Reset Database

```bash
# CUIDADO: Borra todos los datos
make dev-down
docker volume rm agente_postgres_dev_data
make dev-up
```

### Backup & Restore

```bash
# Backup
docker compose -f docker-compose.dev.yml exec postgres pg_dump -U agente agente_hotel > backup.sql

# Restore
docker compose -f docker-compose.dev.yml exec -T postgres psql -U agente agente_hotel < backup.sql
```

---

## 📡 API Issues

### Debug Request/Response

```python
# Middleware para logging completo
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers)
    )
    
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start
    logger.info(
        "request_completed",
        status_code=response.status_code,
        duration=duration
    )
    
    return response
```

### Test with curl

```bash
# GET request
curl -v http://localhost:8000/api/endpoint

# POST request
curl -v -X POST http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# With auth
curl -v http://localhost:8000/api/endpoint \
  -H "Authorization: Bearer YOUR_TOKEN"

# Save response
curl http://localhost:8000/api/endpoint > response.json
```

---

## 🐳 Docker Issues

### Container Won't Start

```bash
# Ver logs completos
docker compose -f docker-compose.dev.yml logs agente-api

# Ver eventos
docker events

# Inspeccionar contenedor
docker inspect agente_hotel_api_dev

# Verificar recursos
docker system df
```

### Clean Docker State

```bash
# Limpiar contenedores parados
docker container prune

# Limpiar imágenes no usadas
docker image prune -a

# Limpiar volúmenes no usados
docker volume prune

# Limpiar todo (CUIDADO!)
docker system prune -a --volumes
```

### Build Issues

```bash
# Rebuild sin cache
docker compose -f docker-compose.dev.yml build --no-cache agente-api

# Ver capas de imagen
docker history agente-hotel-api:latest

# Debug build
docker compose -f docker-compose.dev.yml build --progress=plain agente-api
```

---

## 📊 Monitoring & Observability

### Check Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics | grep my_metric

# Grafana
open http://localhost:3000
# Login: admin/admin
```

### Logs Analysis

```bash
# Ver logs estructurados
docker compose -f docker-compose.dev.yml logs agente-api | jq

# Filtrar por nivel
docker compose -f docker-compose.dev.yml logs agente-api | grep ERROR

# Últimas 100 líneas
docker compose -f docker-compose.dev.yml logs --tail=100 agente-api

# Desde timestamp
docker compose -f docker-compose.dev.yml logs --since="2025-10-04T10:00:00" agente-api
```

---

## 🆘 Getting Help

### Information to Include in Bug Reports

```bash
# 1. Versión del sistema
cat /etc/os-release

# 2. Versión de Docker
docker --version
docker compose version

# 3. Estado de servicios
make dev-status

# 4. Logs relevantes
make dev-logs | tail -100

# 5. Configuración (sin secretos!)
cat .env | grep -v PASSWORD | grep -v SECRET
```

### Create Issue Template

```markdown
## Bug Description
[Clear description of the issue]

## Steps to Reproduce
1. ...
2. ...
3. ...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: [e.g., Ubuntu 22.04]
- Docker: [version]
- Python: [version]

## Logs
```
[Paste relevant logs]
```

## Additional Context
[Any other information]
```

---

## 💡 Pro Tips

1. **Siempre verifica logs primero**: `make dev-logs`
2. **Usa debug logging**: Set `LOG_LEVEL=DEBUG` en `.env`
3. **Reproduce en tests**: Agregar test que reproduce el bug
4. **Usa breakpoints**: Mejor que `print()` statements
5. **Documenta soluciones**: Actualiza esta guía cuando resuelvas algo nuevo

---

**¿Encontraste algo que debería estar aquí?**  
¡Haz un PR agregándolo! 🚀
