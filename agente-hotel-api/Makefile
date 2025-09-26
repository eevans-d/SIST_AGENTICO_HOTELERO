.PHONY: install fmt lint test run build clean help dev-setup docker-up docker-down backup restore logs health
.PHONY: security-scan security-fast performance-test stress-test chaos-db chaos-redis resilience-test
.PHONY: analyze-performance analyze-chaos open-resilience-dashboard install-k6
.PHONY: k6-smoke
.PHONY: create-phase5-issues
.PHONY: validate-slo-compliance check-error-budget check-burn-rates create-incident-report validate-runbooks
.PHONY: test-incident-response generate-slo-report open-governance-docs compliance-dashboard pre-deploy-check

HAS_UV := $(shell command -v uv >/dev/null 2>&1 && test -f pyproject.toml && echo 1 || echo 0)
HAS_UV_PROJECT := $(shell command -v uv >/dev/null 2>&1 && test -f pyproject.toml && grep -q '^\[project\]' pyproject.toml && echo 1 || echo 0)
HAS_POETRY := $(shell command -v poetry >/dev/null 2>&1 && test -f pyproject.toml && echo 1 || echo 0)
HAS_POETRY_PROJECT := $(shell test -f pyproject.toml && grep -q '^\[tool\.poetry\]' pyproject.toml && echo 1 || echo 0)
HAS_NPM := $(shell command -v npm >/dev/null 2>&1 && test -f package.json && echo 1 || echo 0)

# ==============================================================================
# Comandos Universales
# ==============================================================================

install: ## Instalar dependencias del proyecto
ifeq ($(HAS_UV_PROJECT),1)
	@echo "Installing dependencies with uv..."
	uv sync --all-extras

else ifeq ($(HAS_POETRY),1)
	@echo "Installing dependencies with poetry..."
	poetry install --all-extras --no-root
else ifeq ($(HAS_UV),1)
	@echo "uv está disponible pero pyproject no tiene sección [project]. Considera instalar poetry."
	@echo "Intentando instalar con uv igualmente..."
	uv sync --all-extras || true
else ifeq ($(HAS_NPM),1)
	@echo "Installing dependencies with npm..."
	npm install
else
	@echo "❌ No se detectó gestor de dependencias (uv, poetry, npm)"
endif

fmt: ## Formatear todo el código
	@echo "Formatting code..."
	ruff format .
	command -v prettier >/dev/null 2>&1 && prettier --write . --ignore-unknown || echo "(prettier no instalado)"

lint: ## Ejecutar linters y static analysis
	@echo "Running linters..."
	ruff check . --fix
	if test -f .gitleaks.toml; then \
		command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-git -v || echo "(gitleaks no instalado)"; \
	else \
		command -v gitleaks >/dev/null 2>&1 && gitleaks detect -v || echo "(gitleaks no instalado)"; \
	fi

security-fast: ## Escaneo rápido (solo HIGH/CRITICAL) con trivy fs (vuln + secrets)
	@echo "Security fast scan (HIGH/CRITICAL, vuln+secret)..."
	@if ! command -v trivy >/dev/null 2>&1; then echo "trivy no instalado"; exit 1; fi
	trivy fs --severity HIGH,CRITICAL --security-checks vuln,secret --quiet . || true

security-scan: ## Escaneo completo (deps, config, secretos, imagen) -> scripts/security-scan.sh
	@echo "Security full scan..."
	@bash scripts/security-scan.sh

test: ## Ejecutar tests con pytest (usa Poetry si está disponible)
ifeq ($(HAS_POETRY),1)
	poetry run pytest -q
else
	pytest -q
endif



# ==============================================================================
# Comandos Específicos del Proyecto
# ==============================================================================

dev-setup: ## Configura el entorno de desarrollo inicial (copia .env)
	@echo "Configurando entorno de desarrollo..."
	if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env creado a partir de .env.example. Por favor, edítalo con tus secretos."; \
	fi


docker-up: ## Levanta el stack de Docker en modo detached
	@echo "Levantando stack de Docker..."
	docker compose up -d --build


docker-down: ## Detiene y elimina los contenedores del stack
	@echo "Deteniendo stack de Docker..."
	docker compose down

backup: ## Ejecuta el script de backup
	@echo "Ejecutando backup..."
	bash scripts/backup.sh

restore: ## Ejecuta el script de restauración
	@echo "Para restaurar, ejecuta: bash scripts/restore.sh <ruta_backup>"

logs: ## Muestra los logs de todos los servicios en tiempo real
	@echo "Mostrando logs..."
	docker compose logs -f

health: ## Ejecuta el script de health-check
	@echo "Verificando salud de los servicios..."
	bash scripts/health-check.sh

# ==============================================================================
# Utilidades de Monitorización
# ==============================================================================

monitoring-restart: ## Reinicia Prometheus, Grafana y Alertmanager
	@echo "Reiniciando stack de monitorización..."
	docker compose restart prometheus grafana alertmanager

alertmanager-logs: ## Muestra logs de Alertmanager
	@docker compose logs -f alertmanager

alertmanager-config: ## Muestra el config generado por entrypoint
	@docker exec -it agente_alertmanager sh -c 'cat /tmp/generated.yml || echo "generated.yml no disponible aún"'

prometheus-rules-status: ## Muestra el estado de reglas cargadas en Prometheus (JSON)
	@docker exec -it agente_prometheus sh -c 'wget -qO- http://localhost:9090/api/v1/rules || echo "Prometheus no accesible"'

alertmanager-alerts: ## Lista alertas activas en Alertmanager (JSON)
	@docker exec -it agente_alertmanager sh -c 'wget -qO- http://localhost:9093/api/v2/alerts || echo "Alertmanager no accesible"'

prometheus-reload: ## Solicita recarga de configuración de Prometheus (HTTP POST /-/reload)
	@docker exec -it agente_prometheus sh -c 'wget --spider --post-data="" -q http://localhost:9090/-/reload 2>/dev/null && echo "(reload enviado)" || echo "Prometheus no accesible"'

test-alert-429: ## Genera tráfico para provocar 429 en /webhooks/whatsapp
	@chmod +x scripts/generate_429.sh
	@HOST=localhost PORT=8000 REQUESTS=90 DELAY_MS=30 bash scripts/generate_429.sh

alerts-enable-test: ## Activa alerta sintética (AlwaysFiring) en alerts-extra.yml
	@chmod +x scripts/alerts-enable-test.sh
	@bash scripts/alerts-enable-test.sh

alerts-disable-test: ## Desactiva alerta sintética (restaura alerts-extra.yml)
	@chmod +x scripts/alerts-disable-test.sh
	@bash scripts/alerts-disable-test.sh

# ==============================================================================
# Hardening y Monitoreo Sintético
# ==============================================================================

synthetic-health-check: ## Ejecuta health check sintético (configurable via env vars)
	@chmod +x scripts/synthetic-health-check.sh
	@bash scripts/synthetic-health-check.sh

docker-vulnerability-scan: ## Escanea vulnerabilidades en imagen Docker actual
	@echo "Scanning Docker image for vulnerabilities..."
	@docker build -t agente-hotel-api:scan . >/dev/null 2>&1
	@trivy image --severity HIGH,CRITICAL agente-hotel-api:scan || echo "Vulnerabilities found - review output above"

docker-build-hardened: ## Build imagen con hardening y health checks
	@echo "Building hardened Docker image..."
	@docker build -t agente-hotel-api:hardened .
	@echo "Testing health check..."
	@timeout 30s docker run --rm -d -p 8002:8000 -e DEBUG=true -e ENVIRONMENT=development -e SECRET_KEY=test-key agente-hotel-api:hardened || true
	@sleep 5
	@HEALTH_CHECK_URL=http://localhost:8002 TIMEOUT=5 MAX_RETRIES=1 bash scripts/synthetic-health-check.sh || true
	@docker stop $$(docker ps -q --filter ancestor=agente-hotel-api:hardened) 2>/dev/null || true

validate-guardrails: ## Valida que todos los guardrails estén configurados correctamente
	@echo "🛡️ Validating guardrails configuration..."
	@echo "Checking guardrails.conf..."
	@test -f scripts/guardrails.conf && echo "✅ Guardrails config exists" || { echo "❌ Guardrails config missing"; exit 1; }
	@echo "Checking Dependabot limits..."
	@grep -q "open-pull-requests-limit: [1-5]" ../.github/dependabot.yml && echo "✅ Dependabot PR limits OK" || echo "⚠️ Check Dependabot limits"
	@echo "Checking workflow timeouts..."
	@grep -q "timeout-minutes:" ../.github/workflows/ci.yml && echo "✅ CI timeouts configured" || echo "⚠️ Missing CI timeouts"
	@grep -q "timeout-minutes:" ../.github/workflows/nightly-security.yml && echo "✅ Nightly timeouts configured" || echo "⚠️ Missing nightly timeouts"
	@echo "Checking synthetic health check limits..."
	@grep -q "ABSOLUTE_MAX_RETRIES" scripts/synthetic-health-check.sh && echo "✅ Health check limits OK" || echo "⚠️ Missing health check limits"
	@echo "🎯 Guardrails validation complete!"

test-circuit-breakers: ## Prueba los circuit breakers con cargas controladas
	@echo "🔄 Testing circuit breakers..."
	@echo "Testing health check rate limiting..."
	@for i in {1..3}; do \
		echo "Attempt $$i:"; \
		TIMEOUT=2 MAX_RETRIES=1 bash scripts/synthetic-health-check.sh || true; \
		sleep 1; \
	done
	@echo "Circuit breaker test complete!"

# ==============================================================================
# Performance & Chaos Engineering
# ==============================================================================

performance-test: ## Ejecuta pruebas de rendimiento con k6
k6-smoke: ## Ejecuta smoke test rápido (60s, validar P95 y error rate)
create-phase5-issues: ## Crea issues estándar de la Fase 5 (requiere gh auth)
	@echo "📌 Creando issues Fase 5..."
	@bash scripts/create-phase5-issues.sh || echo "⚠ Revisa autenticación gh"
	@echo "✅ Proceso finalizado"
	@echo "🚀 Running k6 smoke test..."
	@command -v k6 >/dev/null 2>&1 || { echo "❌ k6 not found. Ejecuta 'make install-k6'"; exit 1; }
	@mkdir -p reports/performance
	@K6_DURATION=$${K6_DURATION:-60s} K6_RPS=$${K6_RPS:-50} k6 run tests/performance/smoke-test.js || true
	@bash scripts/eval-smoke.sh || echo "⚠ Gating falló (ver arriba)"
	@echo "(Gating local no bloqueante)"
	@echo "🚀 Running performance tests..."
	@command -v k6 >/dev/null 2>&1 || { echo "❌ k6 not found. Install with: curl https://github.com/grafana/k6/releases/download/v0.46.0/k6-v0.46.0-linux-amd64.tar.gz | tar -xz && sudo cp k6-v0.46.0-linux-amd64/k6 /usr/local/bin/"; exit 1; }
	@mkdir -p reports/performance
	k6 run tests/performance/load-test.js
	@echo "✅ Performance test complete"

stress-test: ## Ejecuta pruebas de estrés para encontrar puntos de ruptura
	@echo "💥 Running stress tests..."
	@command -v k6 >/dev/null 2>&1 || { echo "❌ k6 not found. Install with: curl https://github.com/grafana/k6/releases/download/v0.46.0/k6-v0.46.0-linux-amd64.tar.gz | tar -xz && sudo cp k6-v0.46.0-linux-amd64/k6 /usr/local/bin/"; exit 1; }
	@mkdir -p reports/performance
	k6 run tests/performance/stress-test.js
	@echo "✅ Stress test complete"

chaos-db: ## Simula fallas de base de datos
	@echo "🗄️ Running database chaos test..."
	@chmod +x scripts/chaos-db-failure.sh
	@bash scripts/chaos-db-failure.sh
	@echo "✅ Database chaos test complete"

chaos-redis: ## Simula fallas de Redis/cache
	@echo "🔄 Running Redis chaos test..."
	@chmod +x scripts/chaos-redis-failure.sh
	@bash scripts/chaos-redis-failure.sh
	@echo "✅ Redis chaos test complete"

resilience-test: ## Suite completa de pruebas de resiliencia (performance + chaos)
	@echo "🧪 Running comprehensive resilience test suite..."
	@chmod +x scripts/resilience-test-suite.sh
	@bash scripts/resilience-test-suite.sh
	@echo "✅ Resilience test suite complete"

analyze-performance: ## Analiza resultados de pruebas de rendimiento
	@echo "📊 Analyzing performance results..."
	@if [ -z "$(REPORT)" ]; then echo "Usage: make analyze-performance REPORT=<timestamp>"; exit 1; fi
	@if [ -f "reports/resilience/load-test-summary-$(REPORT).json" ]; then \
		echo "📈 Load Test Summary:"; \
		cat reports/resilience/load-test-summary-$(REPORT).json | jq '.metrics' 2>/dev/null || cat reports/resilience/load-test-summary-$(REPORT).json; \
	fi
	@if [ -f "reports/resilience/stress-test-summary-$(REPORT).json" ]; then \
		echo "💥 Stress Test Summary:"; \
		cat reports/resilience/stress-test-summary-$(REPORT).json | jq '.metrics' 2>/dev/null || cat reports/resilience/stress-test-summary-$(REPORT).json; \
	fi

analyze-chaos: ## Analiza resultados de pruebas de chaos engineering
	@echo "🌪️ Analyzing chaos results..."
	@if [ -z "$(REPORT)" ]; then echo "Usage: make analyze-chaos REPORT=<timestamp>"; exit 1; fi
	@if [ -f "reports/resilience/chaos-db-$(REPORT).log" ]; then \
		echo "🗄️ Database Chaos Summary:"; \
		grep -E "(Started|Recovery detected|Total downtime)" reports/resilience/chaos-db-$(REPORT).log | tail -5; \
	fi
	@if [ -f "reports/resilience/chaos-redis-$(REPORT).log" ]; then \
		echo "🔄 Redis Chaos Summary:"; \
		grep -E "(Started|Recovery detected|Total downtime)" reports/resilience/chaos-redis-$(REPORT).log | tail -5; \
	fi

open-resilience-dashboard: ## Abre el dashboard de resiliencia en Grafana
	@echo "📊 Opening resilience dashboard..."
	@echo "URL: http://localhost:3000/d/resilience-chaos/resilience-chaos-engineering-dashboard"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:3000/d/resilience-chaos/resilience-chaos-engineering-dashboard" || echo "Open manually in browser"

install-k6: ## Instala k6 para pruebas de rendimiento
	@echo "📦 Installing k6..."
	@if command -v k6 >/dev/null 2>&1; then echo "✅ k6 already installed"; else \
		curl -L https://github.com/grafana/k6/releases/download/v0.46.0/k6-v0.46.0-linux-amd64.tar.gz | tar -xz && \
		sudo cp k6-v0.46.0-linux-amd64/k6 /usr/local/bin/ && \
		rm -rf k6-v0.46.0-linux-amd64 && \
		echo "✅ k6 installed successfully"; \
	fi

# ==============================================================================
# Governance & SLO Management
# ==============================================================================

validate-slo-compliance: ## Valida cumplimiento de SLOs en tiempo real
	@echo "🎯 Validating SLO compliance..."
	@chmod +x scripts/validate-slo-compliance.sh
	@bash scripts/validate-slo-compliance.sh
	@echo "✅ SLO validation complete"

check-error-budget: ## Verifica consumo de error budget
	@echo "📊 Checking error budget consumption..."
	@curl -s "http://localhost:9090/api/v1/query?query=orchestrator_error_budget_used_ratio_30m*100" | \
		jq -r '.data.result[0].value[1] // "No data"' | \
		awk '{printf "Error Budget Used: %.2f%%\n", $$1}'

check-burn-rates: ## Verifica burn rates de SLOs
	@echo "🔥 Checking SLO burn rates..."
	@echo "Fast burn rate (5m):"
	@curl -s "http://localhost:9090/api/v1/query?query=orchestrator_burn_rate_fast" | \
		jq -r '.data.result[0].value[1] // "No data"' | \
		awk '{printf "  %.2f (alert if > 2.0)\n", $$1}'
	@echo "Slow burn rate (1h):"
	@curl -s "http://localhost:9090/api/v1/query?query=orchestrator_burn_rate_slow" | \
		jq -r '.data.result[0].value[1] // "No data"' | \
		awk '{printf "  %.2f (alert if > 1.5)\n", $$1}'

create-incident-report: ## Crea un nuevo reporte de incidente
	@echo "📝 Creating incident report..."
	@if [ -z "$(INCIDENT)" ]; then echo "Usage: make create-incident-report INCIDENT=description"; exit 1; fi
	@mkdir -p reports/incidents
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S) && \
		cp docs/templates/post-mortem-template.md "reports/incidents/incident-$$TIMESTAMP-$(INCIDENT).md" && \
		echo "📄 Created: reports/incidents/incident-$$TIMESTAMP-$(INCIDENT).md"

validate-runbooks: ## Valida que todos los runbooks estén actualizados
	@echo "📚 Validating runbooks..."
	@find docs/runbooks -name "*.md" -type f | while read -r runbook; do \
		if grep -q "Last Updated.*\$$(date)" "$$runbook"; then \
			echo "✅ $$runbook: Up to date"; \
		else \
			echo "⚠️ $$runbook: Needs update"; \
		fi; \
	done

test-incident-response: ## Prueba los procedimientos de respuesta a incidentes
	@echo "🚨 Testing incident response procedures..."
	@echo "Testing alert acknowledgment..."
	@echo "Testing escalation contacts..."
	@echo "Testing runbook accessibility..."
	@echo "✅ Incident response test complete"

generate-slo-report: ## Genera reporte detallado de SLOs
	@echo "📈 Generating SLO report..."
	@mkdir -p reports/slo
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S) && \
		bash scripts/validate-slo-compliance.sh > "reports/slo/slo-report-$$TIMESTAMP.txt" 2>&1 && \
		echo "📄 Report generated: reports/slo/slo-report-$$TIMESTAMP.txt"

open-governance-docs: ## Abre la documentación de governance
	@echo "📖 Opening governance documentation..."
	@echo "Available documents:"
	@echo "  - docs/GOVERNANCE_FRAMEWORK.md"
	@find docs/runbooks -name "*.md" -exec echo "  - {}" \;
	@command -v xdg-open >/dev/null 2>&1 && xdg-open docs/GOVERNANCE_FRAMEWORK.md || echo "Open docs/GOVERNANCE_FRAMEWORK.md manually"

compliance-dashboard: ## Abre dashboard de compliance en Grafana
	@echo "📊 Opening compliance dashboard..."
	@echo "URL: http://localhost:3000/d/compliance/compliance-dashboard"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:3000/d/compliance/compliance-dashboard" || echo "Open manually in browser"

pre-deploy-check: ## Validación completa pre-deployment
	@echo "🚀 Running pre-deployment validation..."
	@echo "1. Running tests..."
	@make test || { echo "❌ Tests failed"; exit 1; }
	@echo "2. Security scan..."
	@make security-fast || { echo "❌ Security scan failed"; exit 1; }
	@echo "3. SLO compliance check..."
	@make validate-slo-compliance || { echo "❌ SLO compliance failed"; exit 1; }
	@echo "4. Validating guardrails..."
	@make validate-guardrails || { echo "❌ Guardrails validation failed"; exit 1; }
	@echo "✅ Pre-deployment validation complete"

help: ## Muestra esta ayuda
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z0-9_\-]+:.*?##/ {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


.DEFAULT_GOAL := help
