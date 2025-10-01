# ⚡ Quick Command Reference - Agente Hotelero IA

**Last Updated**: October 1, 2025  
**Purpose**: Fast reference for common operations  
**Keep this handy**: Bookmark for quick access

---

## 🚀 Quick Start (First Time)

```bash
# Clone repository
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api

# Setup environment
make dev-setup      # Creates .env from .env.example
make install        # Install dependencies

# Start services (with mock PMS)
make docker-up

# Verify everything works
make health
make test
```

---

## 🔄 Daily Development

### Start Your Day
```bash
# Pull latest changes
git pull origin main

# Update dependencies
make install

# Start services
make docker-up

# Check health
make health
```

### During Development
```bash
# Run tests continuously
make test

# Format code
make fmt

# Lint code
make lint

# View logs
make logs

# Follow specific service
docker compose logs -f agente-api
```

### End Your Day
```bash
# Stop services
make docker-down

# Commit changes
git add .
git commit -m "feat: your feature description"
git push origin your-branch
```

---

## 🧪 Testing

### Run All Tests
```bash
make test                # All 46 tests
```

### Run Specific Tests
```bash
# Unit tests only
poetry run pytest tests/unit/ -v

# Integration tests only
poetry run pytest tests/integration/ -v

# E2E tests only
poetry run pytest tests/e2e/ -v

# Specific test file
poetry run pytest tests/unit/test_pms_adapter.py -v

# Specific test function
poetry run pytest tests/unit/test_pms_adapter.py::test_circuit_breaker -v

# With coverage
poetry run pytest --cov=app --cov-report=html
```

### Test Debugging
```bash
# Run with debug output
poetry run pytest -vv -s

# Stop on first failure
poetry run pytest -x

# Last failed tests
poetry run pytest --lf

# Print 10 slowest tests
poetry run pytest --durations=10
```

---

## 🔍 Quality Checks

### All Quality Checks
```bash
make fmt            # Format code (ruff)
make lint           # Lint code (ruff + gitleaks)
make test           # Run tests
make preflight      # Risk assessment
```

### Individual Checks
```bash
# Format check only (no fix)
poetry run ruff format --check .

# Lint with auto-fix
poetry run ruff check . --fix

# Security scan
make security-fast

# Type checking (if mypy configured)
poetry run mypy app/
```

---

## 🐳 Docker Operations

### Basic Operations
```bash
# Start all services
make docker-up
# or: docker compose up -d

# Stop all services
make docker-down
# or: docker compose down

# Restart all services
docker compose restart

# Rebuild and start
docker compose up -d --build
```

### Service Management
```bash
# Start with real PMS
docker compose --profile pms up -d

# Start specific service
docker compose up -d agente-api

# Restart specific service
docker compose restart agente-api

# Stop specific service
docker compose stop agente-api

# Remove specific service
docker compose rm -f agente-api
```

### Logs and Debugging
```bash
# All logs
make logs
# or: docker compose logs -f

# Specific service logs
docker compose logs -f agente-api
docker compose logs -f postgres
docker compose logs -f redis

# Last 100 lines
docker compose logs --tail=100 agente-api

# Logs since timestamp
docker compose logs --since 2h agente-api
```

### Container Inspection
```bash
# List running containers
docker compose ps

# Inspect container
docker compose exec agente-api env

# Shell into container
docker compose exec agente-api bash
docker compose exec postgres psql -U hoteluser -d hoteldb
docker compose exec redis redis-cli

# Check resource usage
docker stats
```

### Volume Management
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect agente-hotel-api_postgres_data

# Remove all volumes (DANGEROUS)
docker compose down -v
```

---

## 🗄️ Database Operations

### PostgreSQL
```bash
# Connect to database
docker compose exec postgres psql -U hoteluser -d hoteldb

# Backup database
make backup
# or: docker compose exec postgres pg_dump -U hoteluser hoteldb > backup.sql

# Restore database
make restore
# or: docker compose exec -T postgres psql -U hoteluser hoteldb < backup.sql

# List tables
docker compose exec postgres psql -U hoteluser -d hoteldb -c "\dt"

# Check connections
docker compose exec postgres psql -U hoteluser -d hoteldb -c "SELECT * FROM pg_stat_activity;"
```

### Redis
```bash
# Connect to Redis
docker compose exec redis redis-cli

# Check keys
docker compose exec redis redis-cli KEYS "*"

# Get value
docker compose exec redis redis-cli GET "key_name"

# Flush all (DANGEROUS)
docker compose exec redis redis-cli FLUSHALL

# Check memory
docker compose exec redis redis-cli INFO memory
```

---

## 📊 Monitoring

### Health Checks
```bash
# All services
make health

# Individual endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics

# Check specific service
curl -I http://localhost:3000  # Grafana
curl -I http://localhost:9090  # Prometheus
curl -I http://localhost:9093  # AlertManager
```

### Metrics
```bash
# View all metrics
curl http://localhost:8000/metrics

# Specific metric
curl http://localhost:8000/metrics | grep pms_api_latency

# Prometheus queries
curl 'http://localhost:9090/api/v1/query?query=up'
curl 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])'
```

### Service Status
```bash
# Docker health
docker compose ps

# System resources
docker stats --no-stream

# Disk usage
docker system df
```

---

## 🚀 Deployment

### Pre-Deployment
```bash
# Run all checks
make test
make lint
make preflight

# Check risk score
make preflight | jq '.risk_score'

# Generate status report
./scripts/generate-status-summary.sh
```

### Staging Deployment
```bash
# Deploy to staging
./scripts/deploy.sh staging

# Verify deployment
make health
make test

# Monitor
make logs
```

### Production Deployment
```bash
# Backup first!
make backup

# Deploy to production
./scripts/deploy.sh production

# Verify
make health

# Run smoke tests
npm run smoke:test

# Monitor canary
make canary-diff
```

### Rollback
```bash
# Stop current deployment
docker compose down

# Restore from backup
./scripts/restore.sh <backup-timestamp>

# Start previous version
docker compose up -d

# Verify
make health
```

---

## 🔐 Secrets Management

### Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit secrets
nano .env
# or: vim .env

# Validate required vars
grep -v '^#' .env | grep -v '^$' | wc -l  # Count set vars

# Check specific var
echo $PMS_API_KEY
```

### Generate Secrets
```bash
# Generate random secret key
openssl rand -hex 32

# Generate JWT secret
openssl rand -base64 32

# Generate UUID
uuidgen
```

---

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check logs
make logs

# Check specific service
docker compose logs agente-api

# Verify configuration
docker compose config

# Remove and recreate
docker compose down
docker compose up -d --force-recreate
```

### Connection Issues
```bash
# Check network
docker network ls
docker network inspect agente-hotel-api_backend_network

# Test connectivity
docker compose exec agente-api ping postgres
docker compose exec agente-api nc -zv postgres 5432
docker compose exec agente-api nc -zv redis 6379
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Check slow queries (PostgreSQL)
docker compose exec postgres psql -U hoteluser -d hoteldb -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check Redis memory
docker compose exec redis redis-cli INFO memory
```

### Port Conflicts
```bash
# Check what's using port
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000

# Kill process on port
sudo kill -9 $(sudo lsof -t -i:8000)
```

---

## 🔄 Git Operations

### Branch Management
```bash
# Create feature branch
git checkout -b feature/your-feature

# Switch branches
git checkout main
git checkout feature/your-feature

# Update from main
git checkout main
git pull origin main
git checkout feature/your-feature
git merge main

# Delete local branch
git branch -d feature/your-feature

# Delete remote branch
git push origin --delete feature/your-feature
```

### Commits
```bash
# Stage changes
git add .
git add file1 file2

# Commit
git commit -m "feat: your message"
git commit -m "fix: bug fix"
git commit -m "docs: documentation update"

# Amend last commit
git commit --amend

# Interactive rebase (last 3 commits)
git rebase -i HEAD~3
```

### Pull Requests
```bash
# Push feature branch
git push origin feature/your-feature

# Update PR branch
git checkout feature/your-feature
git merge main
git push origin feature/your-feature
```

---

## 📦 Dependency Management

### Poetry Commands
```bash
# Install all dependencies
poetry install

# Add new dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show installed packages
poetry show

# Show outdated packages
poetry show --outdated

# Export requirements.txt
poetry export -f requirements.txt --output requirements.txt
```

---

## 🎯 Feature Flags

### Check Flags
```bash
# Via Redis CLI
docker compose exec redis redis-cli

# Get all flags
KEYS "feature_flag:*"

# Get specific flag
GET "feature_flag:tenancy.dynamic.enabled"

# Set flag
SET "feature_flag:tenancy.dynamic.enabled" "true"

# Delete flag
DEL "feature_flag:tenancy.dynamic.enabled"
```

### Via API (if endpoints exist)
```bash
# List flags
curl http://localhost:8000/admin/feature-flags

# Enable flag
curl -X PUT http://localhost:8000/admin/feature-flags/flag-name \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

---

## 📈 Performance Testing

### k6 Load Tests
```bash
# Run smoke test
npm run smoke:test

# Run load test
k6 run tests/performance/load-test.js

# Run with virtual users
k6 run --vus 10 --duration 30s tests/performance/load-test.js
```

### Benchmark Endpoints
```bash
# Using ab (Apache Bench)
ab -n 1000 -c 10 http://localhost:8000/health/live

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/health/live
```

---

## 🔔 Alerting

### AlertManager
```bash
# Check alerts
curl http://localhost:9093/api/v2/alerts

# Silence alert
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{"matchers":[{"name":"alertname","value":"HighErrorRate"}],"startsAt":"'$(date -Iseconds)'","endsAt":"'$(date -d '+1 hour' -Iseconds)'","createdBy":"admin","comment":"Planned maintenance"}'

# Delete silence
curl -X DELETE http://localhost:9093/api/v2/silence/{silence_id}
```

---

## 🆘 Emergency Procedures

### System Down
```bash
# 1. Check all services
docker compose ps

# 2. Check logs for errors
make logs | grep -i error

# 3. Restart services
docker compose restart

# 4. If still down, recreate
docker compose down
docker compose up -d --force-recreate

# 5. Verify health
make health
```

### High Load
```bash
# 1. Check resource usage
docker stats

# 2. Scale services (if configured)
docker compose up -d --scale agente-api=3

# 3. Check metrics
curl http://localhost:8000/metrics | grep -E "(cpu|memory|requests)"

# 4. Enable rate limiting
# Edit .env: RATELIMIT_ENABLED=true
docker compose restart agente-api
```

### Data Loss Prevention
```bash
# Immediate backup
make backup

# Copy to safe location
cp backup-$(date +%Y%m%d-%H%M%S).tar.gz /safe/location/
```

---

## 📱 Quick Service URLs

### Local Development
```
API:          http://localhost:8000
API Docs:     http://localhost:8000/docs
Metrics:      http://localhost:8000/metrics
Health Live:  http://localhost:8000/health/live
Health Ready: http://localhost:8000/health/ready

Grafana:      http://localhost:3000
Prometheus:   http://localhost:9090
AlertManager: http://localhost:9093
```

### Default Credentials
```
Grafana:
  User: admin
  Pass: admin (change on first login)
```

---

## 💡 Pro Tips

### Aliases (add to ~/.bashrc)
```bash
alias dc='docker compose'
alias dcu='docker compose up -d'
alias dcd='docker compose down'
alias dcl='docker compose logs -f'
alias dce='docker compose exec'
alias dcps='docker compose ps'

alias ptest='poetry run pytest'
alias plint='poetry run ruff check .'
alias pfmt='poetry run ruff format .'
```

### Watch Commands
```bash
# Watch service health
watch -n 5 'curl -s http://localhost:8000/health/ready | jq'

# Watch metrics
watch -n 5 'curl -s http://localhost:8000/metrics | grep -E "(requests|latency)"'

# Watch docker stats
watch -n 5 'docker stats --no-stream'
```

---

## 📞 Getting Help

### Documentation
```bash
# View documentation
cat DOCUMENTATION_INDEX.md
cat DEPLOYMENT_ACTION_PLAN.md
cat .github/copilot-instructions.md
```

### Logs
```bash
# Application logs
make logs

# Specific service
docker compose logs -f agente-api

# Error logs only
make logs | grep -i error
```

### Support Channels
- **Documentation**: `DOCUMENTATION_INDEX.md`
- **Troubleshooting**: `TROUBLESHOOTING_AUTOCURACION.md`
- **Operations**: `agente-hotel-api/docs/OPERATIONS_MANUAL.md`
- **AI Assistant**: Ask GitHub Copilot (trained on `.github/copilot-instructions.md`)

---

**Remember**: When in doubt, check `DOCUMENTATION_INDEX.md` for the full documentation map!

**Quick Help**: `make` (shows all available Makefile targets)
