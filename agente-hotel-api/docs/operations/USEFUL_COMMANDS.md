# 🚀 Comandos Útiles - Sistema Agente Hotelero IA

**Quick Reference Guide**  
**Version:** 1.0.0  
**Actualizado:** 2025-10-09

---

## 📋 Validación y Health Checks

### Validación Rápida
```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api
./scripts/quick_validation.sh
```

### Validación de Performance System
```bash
./scripts/validate_performance_system.sh
```

### Health Check del Sistema
```bash
make health
```

---

## 🧪 Testing

### Ejecutar Todos los Tests
```bash
poetry run pytest tests/ -v
```

### Tests por Categoría
```bash
# Unit tests
poetry run pytest tests/unit/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# E2E tests
poetry run pytest tests/e2e/ -v
```

### Tests de Phase 12
```bash
# Performance Optimizer
poetry run pytest tests/unit/test_performance_optimizer.py -v

# Resource Monitor
poetry run pytest tests/unit/test_resource_monitor.py -v

# Optimization System (integration)
poetry run pytest tests/integration/test_optimization_system.py -v
```

### Con Coverage
```bash
poetry run pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🐳 Docker

### Iniciar Sistema Completo
```bash
make docker-up
# o
docker-compose up -d --build
```

### Ver Logs
```bash
# Todos los servicios
make logs

# Servicio específico
docker-compose logs -f agente-api

# Solo errores
docker-compose logs -f agente-api | grep ERROR
```

### Detener Sistema
```bash
make docker-down
# o
docker-compose down
```

### Rebuild Completo
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Ver Estado de Servicios
```bash
docker-compose ps
```

---

## 🔧 Development

### Setup Inicial
```bash
make dev-setup
make install
```

### Formatear Código
```bash
make fmt
```

### Lint
```bash
make lint
```

### Security Scan
```bash
make security-fast
```

### Limpiar Cache
```bash
make clean
```

### Limpieza Profunda
```bash
./scripts/deep_cleanup.sh
```

---

## 📊 Performance y Optimization

### Estado de Optimization System
```bash
curl http://localhost:8000/api/v1/performance/status | jq
```

### Métricas Actuales
```bash
curl http://localhost:8000/api/v1/performance/metrics | jq
```

### Ejecutar Optimización Manual
```bash
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute | jq
```

### Ver Reporte de Optimizaciones
```bash
curl http://localhost:8000/api/v1/performance/optimization/report | jq
```

### Estado de Scaling
```bash
curl http://localhost:8000/api/v1/performance/scaling/status | jq
```

### Ver Alertas Activas
```bash
curl http://localhost:8000/api/v1/performance/alerts | jq
```

### Recomendaciones del Sistema
```bash
curl http://localhost:8000/api/v1/performance/recommendations | jq
```

---

## 📈 Monitoring

### Ver Métricas de Prometheus
```bash
# Desde el contenedor
curl http://localhost:9090/metrics

# Métricas de la aplicación
curl http://localhost:8000/metrics
```

### Acceder a Grafana
```bash
# URL: http://localhost:3000
# Usuario: admin
# Password: (ver .env)
```

### Acceder a Prometheus
```bash
# URL: http://localhost:9090
```

---

## 💾 Backup y Restore

### Crear Backup
```bash
./scripts/backup.sh
```

### Restaurar Backup
```bash
./scripts/restore.sh <backup_file>
```

### Listar Backups
```bash
ls -lh backups/
```

---

## 🔍 Debugging

### Ver Logs en Tiempo Real
```bash
# Todos los servicios
docker-compose logs -f

# Solo agente-api
docker-compose logs -f agente-api

# Con grep para filtrar
docker-compose logs -f agente-api | grep ERROR
docker-compose logs -f agente-api | grep performance
```

### Entrar al Contenedor
```bash
docker-compose exec agente-api bash
```

### Ver Variables de Entorno
```bash
docker-compose exec agente-api env | grep -E "^(REDIS|POSTGRES|PMS)"
```

### Verificar Conectividad
```bash
# PostgreSQL
docker-compose exec agente-api pg_isready -h postgres -U hotel_agent

# Redis
docker-compose exec agente-api redis-cli -h redis ping

# PMS
curl http://localhost:8080/api/health
```

---

## 🗄️ Database

### Conectar a PostgreSQL
```bash
docker-compose exec postgres psql -U hotel_agent -d hotel_agent_db
```

### Queries Útiles
```sql
-- Ver tablas
\dt

-- Ver sesiones activas
SELECT * FROM sessions WHERE expires_at > NOW();

-- Ver locks activos
SELECT * FROM lock_audit WHERE released_at IS NULL;

-- Ver tenants
SELECT * FROM tenants;

-- Estadísticas de tablas
SELECT schemaname, tablename, n_live_tup, n_dead_tup 
FROM pg_stat_user_tables;
```

### Ejecutar Migrations (si aplica)
```bash
docker-compose exec agente-api alembic upgrade head
```

---

## 🔴 Redis

### Conectar a Redis
```bash
docker-compose exec redis redis-cli
```

### Comandos Útiles
```redis
# Ver todas las keys
KEYS *

# Ver cache de disponibilidad
KEYS availability:*

# Ver feature flags
KEYS feature_flag:*

# Ver locks
KEYS lock:*

# Ver info del servidor
INFO

# Ver memoria usada
INFO memory

# Ver estadísticas de cache
INFO stats
```

---

## 🚀 Deploy

### Deploy a Staging
```bash
./scripts/deploy.sh staging
```

### Deploy a Production
```bash
./scripts/deploy.sh production
```

### Rollback
```bash
./scripts/rollback.sh <version>
```

---

## 📊 Estadísticas del Proyecto

### Contar Líneas de Código
```bash
# Python en app/
find app -name "*.py" -exec wc -l {} + | tail -1

# Tests
find tests -name "*.py" -exec wc -l {} + | tail -1

# Total Python
find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" -exec wc -l {} + | tail -1
```

### Contar Archivos
```bash
# Archivos Python
find app -name "*.py" | wc -l

# Tests
find tests -name "*.py" | wc -l

# Documentos
find . -name "*.md" ! -path "*/.venv/*" | wc -l
```

### Tamaños
```bash
# Por directorio
du -sh app/ tests/ docs/ docker/ scripts/

# Total del proyecto
du -sh .
```

---

## 🧹 Limpieza

### Limpiar Cache Python
```bash
find . -type d -name "__pycache__" ! -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" ! -path "*/.venv/*" -delete
```

### Limpiar Docker
```bash
# Eliminar contenedores detenidos
docker container prune

# Eliminar imágenes sin usar
docker image prune

# Limpieza completa
docker system prune -a
```

### Limpiar Logs
```bash
find . -name "*.log" -mtime +7 -delete
```

---

## 🔐 Security

### Escanear Vulnerabilidades
```bash
make security-fast
```

### Escanear Secrets
```bash
docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source /path -v
```

### Actualizar Dependencias
```bash
poetry update
poetry show --outdated
```

---

## 🎯 Performance Profiling

### Profile de Requests
```bash
# Con cURL y tiempo
time curl http://localhost:8000/api/v1/health/ready

# Con Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/health/live
```

### Benchmark con k6
```bash
./tools/k6-v0.46.0-linux-amd64/k6 run tests/load/basic_load_test.js
```

---

## 📝 Git Commands

### Status Detallado
```bash
git status -sb
git diff --stat
```

### Commit con Template
```bash
git commit -m "feat: descripción corta

- Detalle 1
- Detalle 2

Impact: descripción del impacto"
```

### Ver Historia
```bash
git log --oneline --graph --all --decorate
```

### Limpiar Git
```bash
git gc --aggressive --prune=now
git remote prune origin
```

---

## 🆘 Troubleshooting

### Sistema no Inicia
```bash
# Ver logs de todos los servicios
docker-compose logs

# Verificar puertos en uso
netstat -tulpn | grep -E ":(8000|5432|6379|9090|3000)"

# Recrear contenedores
docker-compose down -v
docker-compose up -d
```

### Performance Degradado
```bash
# Ver métricas
curl http://localhost:8000/api/v1/performance/metrics | jq

# Ver alertas
curl http://localhost:8000/api/v1/performance/alerts | jq

# Ejecutar optimización
curl -X POST http://localhost:8000/api/v1/performance/optimization/execute
```

### Tests Fallan
```bash
# Limpiar cache
rm -rf .pytest_cache __pycache__

# Reinstalar dependencias
poetry install --no-cache

# Ejecutar con verbose
poetry run pytest tests/ -vv --tb=long
```

---

## 📚 Documentación

### Ver Documentación Local
```bash
# Abrir README principal
cat README.md

# Abrir documentación de Phase 12
cat docs/PHASE_12_SUMMARY.md

# Abrir guía de operaciones
cat docs/OPERATIONS_MANUAL.md

# Ver resumen ejecutivo
cat docs/EXECUTIVE_SUMMARY_20251009.md
```

---

## 🎯 Quick Shortcuts

```bash
# Alias útiles (agregar a ~/.bashrc)
alias ag-up='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && make docker-up'
alias ag-down='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && make docker-down'
alias ag-logs='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && make logs'
alias ag-test='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && poetry run pytest tests/ -v'
alias ag-health='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && make health'
alias ag-validate='cd ~/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api && ./scripts/quick_validation.sh'
```

---

**Mantenedor:** Sistema Agente Hotelero IA  
**Última Actualización:** 2025-10-09  
**Versión:** 1.0.0
