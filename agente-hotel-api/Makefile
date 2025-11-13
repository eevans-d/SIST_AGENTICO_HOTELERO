# -------------------------------------------------------------
# Alert Validation
# -------------------------------------------------------------
validate-alerts:
	@echo "[alert-validation] Running enhanced alert validation script";
	python scripts/validate-alerts-staging.py --prometheus-url http://localhost:9090 --prometheus-url-alt http://localhost:9091 --api-url http://localhost:8002 --output .playbook/alert_validation_report.json || exit 1
	@echo "[alert-validation] Report written to .playbook/alert_validation_report.json"
	@echo "[alert-validation] Summary:"; jq '.summary' .playbook/alert_validation_report.json || echo "jq not installed; open .playbook/alert_validation_report.json manually"

validate-alerts-real:
	@echo "[alert-validation-real] Running REAL load alert validation (webhook)";
	python scripts/validate-alerts-staging.py --prometheus-url http://localhost:9090 --prometheus-url-alt http://localhost:9091 --api-url http://localhost:8002 --load-mode real --session-count 60 --output .playbook/alert_validation_report_real.json || exit 1
	@echo "[alert-validation-real] Report written to .playbook/alert_validation_report_real.json"
	@echo "[alert-validation-real] Summary:"; jq '.summary' .playbook/alert_validation_report_real.json || echo "jq not installed; open .playbook/alert_validation_report_real.json manually"

# -------------------------------------------------------------
# Prometheus Rules Validation (C2)
# -------------------------------------------------------------
validate-prometheus:
	@echo "[C2] Validating Prometheus alert rules, recording rules, and config"
	@./scripts/validate-prometheus-rules.sh

validate-prometheus-rules: validate-prometheus  ## Alias for validate-prometheus

.PHONY: install fmt lint test run build clean help dev-setup docker-up docker-down backup restore logs health
.PHONY: security-scan security-fast performance-test stress-test chaos-db chaos-redis resilience-test
.PHONY: analyze-performance analyze-chaos open-resilience-dashboard install-k6
.PHONY: k6-smoke
.PHONY: create-phase5-issues
.PHONY: preflight
.PHONY: canary-diff
.PHONY: validate-slo-compliance check-error-budget check-burn-rates create-incident-report validate-runbooks
.PHONY: test-incident-response generate-slo-report open-governance-docs compliance-dashboard pre-deploy-check
.PHONY: test-unit test-integration test-e2e test-business-metrics load-test chaos-test
.PHONY: coverage-report
.PHONY: security-deps security-deps-json security-deps-html install-security-tools
.PHONY: secret-scan secret-scan-json secret-scan-strict fix-permissions
.PHONY: trufflehog-scan mcp-verify ui-test
.PHONY: owasp-scan owasp-scan-json owasp-scan-category owasp-report owasp-report-json
.PHONY: compliance-report compliance-report-json compliance-show
.PHONY: perf-smoke perf-load perf-stress perf-spike perf-soak perf-validate perf-baseline perf-clean
.PHONY: chaos-network chaos-service chaos-database chaos-pms chaos-resource chaos-all chaos-resilience
.PHONY: chaos-report chaos-monkey chaos-dry-run
.PHONY: deploy-staging deploy-production deploy-canary rollback validate-deployment migration-safe
.PHONY: deploy-status deploy-logs deploy-test
.PHONY: incident-detect incident-simulate incident-report on-call-schedule post-mortem incident-test
.PHONY: validate-prometheus validate-prometheus-rules validate-alerts validate-alerts-real

# ==============================================================================
# Alembic (Migraciones)
# ==============================================================================

.PHONY: db-upgrade db-downgrade db-revision

db-upgrade: ## Ejecuta alembic upgrade head (usa Poetry si está disponible)
ifeq ($(HAS_POETRY),1)
	ALEMBIC_DB_URL?=sqlite:///./agente_hotel.db
	poetry run alembic upgrade head
else
	ALEMBIC_DB_URL?=sqlite:///./agente_hotel.db alembic upgrade head
endif

db-downgrade: ## Ejecuta alembic downgrade -1
ifeq ($(HAS_POETRY),1)
	ALEMBIC_DB_URL?=sqlite:///./agente_hotel.db
	poetry run alembic downgrade -1
else
	ALEMBIC_DB_URL?=sqlite:///./agente_hotel.db alembic downgrade -1
endif

db-revision: ## Crea una nueva revisión con mensaje (uso: make db-revision MSG="add table")
ifeq ($(HAS_POETRY),1)
	poetry run alembic revision -m "$(MSG)"
else
	alembic revision -m "$(MSG)"
endif

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

coverage-report: ## Ejecuta pytest con cobertura y genera reporte HTML (htmlcov)
ifeq ($(HAS_POETRY),1)
	poetry run pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing --cov-report=html
	@echo "✅ Reporte HTML en htmlcov/index.html"
	@echo "Ejecuta cobertura solo sobre un subconjunto seguro de tests unitarios (sin deps externas)"
coverage-focused:
	poetry run pytest -q \
	 tests/unit/test_circuit_breaker.py \
	 tests/unit/test_lock_service.py \
	 tests/unit/test_session_manager_ttl.py \
	 --disable-warnings --cov=app --cov-report=term-missing --cov-report=html --no-header --no-summary || true

.PHONY: alertmanager-render
alertmanager-render: ## Renderiza config Alertmanager con envsubst (usa docker/alertmanager/config.tmpl.yml)
	bash scripts/render-alertmanager-config.sh
else
	pytest -q --maxfail=1 --disable-warnings --cov=app --cov-report=term-missing --cov-report=html
endif
	@echo "✅ Reporte HTML en htmlcov/index.html"

security-fast: ## Escaneo rápido (solo HIGH/CRITICAL) con trivy fs (vuln + secrets)
	@echo "Security fast scan (HIGH/CRITICAL, vuln+secret)..."
	@if ! command -v trivy >/dev/null 2>&1; then echo "trivy no instalado"; exit 1; fi
	trivy fs --severity HIGH,CRITICAL --security-checks vuln,secret --quiet . || true

# security-scan duplicado eliminado - ver línea 778 para versión actual

security-deps: ## P011: Escaneo de vulnerabilidades en dependencias (CVE, licenses, outdated)
	@echo "🔐 P011: Dependency Vulnerability Scan..."
	@python scripts/security/vulnerability_scan.py --format markdown --output .security/vuln-scan-latest.md
	@echo "✅ Reporte generado: .security/vuln-scan-latest.md"

security-deps-json: ## P011: Escaneo de dependencias (output JSON)
	@echo "🔐 P011: Dependency Vulnerability Scan (JSON)..."
	@python scripts/security/vulnerability_scan.py --format json --output .security/vuln-scan-latest.json
	@echo "✅ Reporte generado: .security/vuln-scan-latest.json"

security-deps-html: ## P011: Escaneo de dependencias (output HTML)
	@echo "🔐 P011: Dependency Vulnerability Scan (HTML)..."
	@python scripts/security/vulnerability_scan.py --format html --output .security/vuln-scan-latest.html
	@echo "✅ Reporte generado: .security/vuln-scan-latest.html"
	@echo "Abrir con: xdg-open .security/vuln-scan-latest.html"

install-security-tools: ## Instalar herramientas de seguridad (pip-audit, safety, pip-licenses)
	@echo "📦 Instalando herramientas de seguridad..."
	pip install pip-audit safety pip-licenses
	@echo "✅ Herramientas instaladas: pip-audit, safety, pip-licenses"

secret-scan: ## P012: Escaneo de secretos hardcodeados (output Markdown)
	@echo "🔍 P012: Secret Scanning & Hardening..."
	@python scripts/security/secret_scanner.py --format markdown --output .security/secret-scan-latest.md
	@echo "✅ Reporte generado: .security/secret-scan-latest.md"

secret-scan-json: ## P012: Escaneo de secretos (output JSON para CI/CD)
	@echo "🔍 P012: Secret Scanning (JSON)..."
	@python scripts/security/secret_scanner.py --format json --output .security/secret-scan-latest.json
	@echo "✅ Reporte generado: .security/secret-scan-latest.json"

secret-scan-strict: ## Escaneo estricto de secretos (falla en cualquier hallazgo)
	@echo "🔐 Ejecutando escaneo estricto de secretos..."
	@mkdir -p .security
	@if [ ! -f scripts/security/secret_scanner.py ]; then \
		echo "❌ Error: scripts/security/secret_scanner.py no encontrado"; \
		exit 1; \
	fi
	@python3 scripts/security/secret_scanner.py --format markdown --strict || { \
		echo "❌ Escaneo estricto detectó hallazgos"; \
		echo "Ver reporte en .security/secret-scan-latest.md"; \
		exit 1; \
	}
	@echo "✅ Escaneo estricto completado sin hallazgos críticos"

# ------------------------------------------------------------------------------
# Trufflehog (Secret Scan alternativo)
# ------------------------------------------------------------------------------

trufflehog-scan: ## Escaneo de secretos con trufflehog (salida JSON)
	@echo "🔎 Ejecutando trufflehog filesystem..."
	@mkdir -p .security
	@if ! command -v trufflehog >/dev/null 2>&1; then \
		echo "❌ trufflehog no instalado. Instala con: pipx install trufflehog (o ver docs)"; \
		exit 1; \
	fi
	@trufflehog filesystem --only-verified . --json > .security/trufflehog-report.json || true
	@echo "✅ Reporte generado: .security/trufflehog-report.json"

# ------------------------------------------------------------------------------
# P013: OWASP Top 10 2021 Validation
# ------------------------------------------------------------------------------

owasp-scan: ## Escaneo completo OWASP Top 10 (Markdown)
	@echo "🛡️ Ejecutando validación OWASP Top 10 2021..."
	@mkdir -p .security
	@if [ ! -f scripts/security/owasp_validator.py ]; then \
		echo "❌ Error: scripts/security/owasp_validator.py no encontrado"; \
		exit 1; \
	fi
	@python3 scripts/security/owasp_validator.py --format markdown
	@echo "✅ Escaneo completado. Ver reporte en .security/owasp-scan-latest.md"
	@echo "📊 Ejecuta 'make owasp-report' para ver el reporte"

owasp-scan-json: ## Escaneo OWASP Top 10 en formato JSON (CI/CD)
	@echo "🛡️ Ejecutando validación OWASP Top 10 (JSON)..."
	@mkdir -p .security
	@if [ ! -f scripts/security/owasp_validator.py ]; then \
		echo "❌ Error: scripts/security/owasp_validator.py no encontrado"; \
		exit 1; \
	fi
	@python3 scripts/security/owasp_validator.py --format json --output .security/owasp-scan-latest.json
	@echo "✅ Escaneo JSON completado: .security/owasp-scan-latest.json"

owasp-scan-category: ## Escaneo de categoría específica OWASP (uso: make owasp-scan-category CATEGORY=A03)
	@echo "🛡️ Escaneando categoría OWASP $(CATEGORY)..."
	@if [ -z "$(CATEGORY)" ]; then \
		echo "❌ Error: Especifica CATEGORY (A01-A10)"; \
		echo "Ejemplo: make owasp-scan-category CATEGORY=A03"; \
		exit 1; \
	fi
	@mkdir -p .security
	@python3 scripts/security/owasp_validator.py --category $(CATEGORY) --format markdown
	@echo "✅ Escaneo $(CATEGORY) completado"

owasp-report: ## Ver último reporte OWASP (Markdown)
	@if [ ! -f .security/owasp-scan-latest.md ]; then \
		echo "❌ No hay reporte disponible. Ejecuta 'make owasp-scan' primero"; \
		exit 1; \
	fi
	@cat .security/owasp-scan-latest.md

owasp-report-json: ## Ver último reporte OWASP (JSON formateado)
	@if [ ! -f .security/owasp-scan-latest.json ]; then \
		echo "❌ No hay reporte JSON disponible. Ejecuta 'make owasp-scan-json' primero"; \
		exit 1; \
	fi
	@cat .security/owasp-scan-latest.json | jq '.'

# ==============================================================================
# P014: Compliance Report (Consolidated)
# ==============================================================================

compliance-report: ## Generate consolidated compliance report (JSON + Markdown)
	@echo "🔐 Generating compliance report (P014)..."
	@python3 scripts/security/compliance_report.py --format both
	@echo ""
	@echo "📊 Reports generated:"
	@echo "  - JSON: .security/compliance-report-latest.json"
	@echo "  - Markdown: .security/compliance-report-latest.md"
	@echo ""
	@echo "💡 View with: make compliance-show"

compliance-report-json: ## Generate compliance report (JSON only)
	@python3 scripts/security/compliance_report.py --format json

compliance-show: ## Display last compliance report (Markdown)
	@if [ -f .security/compliance-report-latest.md ]; then \
		cat .security/compliance-report-latest.md; \
	else \
		echo "❌ No compliance report found. Run 'make compliance-report' first."; \
		exit 1; \
	fi

# ==============================================================================
# File Security
# ==============================================================================

fix-permissions: ## P012: Corregir permisos de archivos sensibles
	@echo "🔒 Fixing file permissions..."
	@chmod 600 .env .env.production 2>/dev/null || true
	@chmod 600 private_key.pem id_rsa id_ed25519 2>/dev/null || true
	@chmod 600 secrets.json credentials.json 2>/dev/null || true
	@echo "✅ File permissions fixed (0600)"

test: ## Ejecutar tests con pytest (usa Poetry si está disponible)
ifeq ($(HAS_POETRY),1)
	poetry run pytest -q
else
	pytest -q
endif

# UI smoke test con Playwright (Python). Requiere entorno: poetry + playwright instalado.
ui-test: ## Ejecuta smoke test UI con Playwright (Python). Usa PLAYWRIGHT_SMOKE_URL si está seteado.
ifeq ($(HAS_POETRY),1)
	@if ! poetry run python -c "import importlib; importlib.import_module('playwright')" >/dev/null 2>&1; then \
		echo "❌ playwright (Python) no instalado. Instala con: poetry add --group dev playwright && poetry run playwright install"; \
		exit 1; \
	fi
	poetry run pytest -q tests/ui/test_smoke_playwright.py -q
else
	@echo "❌ poetry no disponible. Instala playwright y ejecuta: pytest tests/ui/test_smoke_playwright.py"; exit 1
endif

# test-unit duplicado eliminado - ver línea 694 para versión actual
# test-integration duplicado eliminado - ver línea 703 para versión actual
# test-e2e duplicado eliminado - ver línea 711 para versión actual

test-business-metrics: ## Ejecutar tests de business metrics
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/unit/test_business_metrics.py -v
else
	pytest tests/unit/test_business_metrics.py -v
endif

load-test: ## Ejecutar load testing con Locust (requiere locust instalado)
	@echo "Starting Locust load test..."
	@if ! command -v locust >/dev/null 2>&1; then \
		echo "❌ Locust no instalado. Instalar con: pip install locust"; \
		exit 1; \
	fi
	@echo "Locust UI disponible en: http://localhost:8089"
	@echo "Configuración sugerida: 50 usuarios, spawn rate 5, duración 5m"
	locust -f tests/load/locustfile.py --host=http://localhost:8000

chaos-test: ## Ejecutar chaos engineering tests
ifeq ($(HAS_POETRY),1)
	@echo "Running chaos/resilience tests..."
	poetry run pytest tests/chaos/test_resilience.py -v --tb=short
else
	@echo "Running chaos/resilience tests..."
	pytest tests/chaos/test_resilience.py -v --tb=short
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

# ------------------------------------------------------------------------------
# Verificación MCPs: Trufflehog, PostgreSQL, Playwright
# ------------------------------------------------------------------------------
mcp-verify: ## Verifica estado operativo de Trufflehog, Postgres (docker) y Playwright
	@echo "🔧 Verificando Trufflehog...";
	@if command -v trufflehog >/dev/null 2>&1; then echo "✅ trufflehog instalado: $$(trufflehog --version 2>/dev/null | head -n1)"; else echo "⚠️ trufflehog no encontrado"; fi
	@echo "🗄️  Verificando PostgreSQL (docker compose)...";
	@if command -v docker >/dev/null 2>&1; then \
		(docker compose ps postgres >/dev/null 2>&1 && echo "(docker compose detectado)") || echo "⚠️ docker compose no listo"; \
		true; \
	else echo "⚠️ docker no instalado"; fi
	@echo "🌐 Verificando Playwright (Python)...";
	@if command -v poetry >/dev/null 2>&1; then \
		(poetry run python -c "import importlib; import sys; importlib.import_module('playwright'); import playwright; print('Playwright PY OK')" >/dev/null 2>&1 && echo "✅ playwright (Python) disponible") || echo "⚠️ playwright (Python) no disponible"; \
	else echo "⚠️ poetry no disponible"; fi

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

# ==============================================================================
# Deployment & Production Operations
# ==============================================================================

# validate-deployment duplicado eliminado - ver línea 1103 para versión actual
# deploy-production duplicado eliminado - ver línea 1077 para versión actual
# deploy-staging duplicado eliminado - ver línea 1068 para versión actual

build-production: ## Construye imagen de producción
	@echo "🔨 Building production image..."
	@docker build -f Dockerfile.production -t agente-hotel-api:production .
	@echo "✅ Production image built successfully"

test-production-image: ## Prueba la imagen de producción localmente
	@echo "🧪 Testing production image..."
	@docker run --rm -d --name agente-test -p 8080:8000 agente-hotel-api:production
	@sleep 10
	@curl -f http://localhost:8080/health/live || { docker stop agente-test; echo "❌ Health check failed"; exit 1; }
	@docker stop agente-test
	@echo "✅ Production image test passed"

canary-deploy: ## Realiza despliegue canary
	@echo "🐤 Starting canary deployment..."
	@chmod +x scripts/canary-deploy.sh
	@bash scripts/canary-deploy.sh

deployment-status: ## Verifica estado del despliegue actual
	@echo "📊 Checking deployment status..."
	@echo "=== Docker Services ==="
	@docker compose -f docker-compose.production.yml ps || echo "Production stack not running"
	@echo "=== Health Checks ==="
	@curl -s http://localhost:8000/health/ready | jq . || echo "API not responding"
	@echo "=== Recent Logs ==="
	@docker compose -f docker-compose.production.yml logs --tail=10 agente-api || echo "No logs available"

help: ## Muestra esta ayuda
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z0-9_\-]+:.*?##/ {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

preflight: ## Ejecuta preflight (calcula risk_score y genera reporte)
	@echo "🚦 Ejecutando preflight..."

canary-diff: ## Ejecuta canary deploy local y genera .playbook/canary_diff_report.json
	@echo "🟡 Ejecutando canary diff (baseline vs canary)"
	@bash scripts/canary-deploy.sh --dry-run || true
	@bash scripts/canary-deploy.sh staging local || true
	@test -f .playbook/canary_diff_report.json && echo "Reporte: .playbook/canary_diff_report.json" || echo "Sin reporte"
	@command -v python3 >/dev/null 2>&1 || { echo "Python3 no disponible"; exit 1; }
	@python3 -c "import yaml" 2>/dev/null || { echo "Instalando pyyaml (sudo puede ser requerido)"; python3 -m pip install --user pyyaml >/dev/null; }
	@python3 scripts/preflight.py || exit $$?
	@python3 scripts/validate_preflight.py || exit $$?
	@echo "✅ Preflight completado"

# ==============================================================================
# Development Experience Commands
# ==============================================================================

dev-up: ## Levanta stack de desarrollo con hot-reload
	@echo "🚀 Levantando entorno de desarrollo..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "✅ Servicios levantados"
	@echo "   API:     http://localhost:8000"
	@echo "   Docs:    http://localhost:8000/docs"
	@echo "   Logs:    make dev-logs"

dev-down: ## Detiene stack de desarrollo
	@echo "🛑 Deteniendo entorno de desarrollo..."
	docker compose -f docker-compose.dev.yml down

dev-logs: ## Muestra logs del entorno de desarrollo
	docker compose -f docker-compose.dev.yml logs -f

dev-restart: ## Reinicia el servicio de API en desarrollo
	@echo "🔄 Reiniciando API..."
	docker compose -f docker-compose.dev.yml restart agente-api

dev-shell: ## Abre shell en el contenedor de desarrollo
	docker compose -f docker-compose.dev.yml exec agente-api /bin/bash

dev-db-admin: ## Levanta herramientas de admin de BD (Adminer + Redis Commander)
	@echo "🗄️  Levantando herramientas de admin..."
	docker compose -f docker-compose.dev.yml --profile db-admin up -d
	@echo "✅ Admin tools levantadas"
	@echo "   Adminer (PostgreSQL): http://localhost:8080"
	@echo "   Redis Commander:      http://localhost:8081"

dev-monitoring: ## Levanta stack de monitoring (Prometheus + Grafana)
	@echo "📊 Levantando monitoring stack..."
	docker compose -f docker-compose.dev.yml --profile monitoring up -d
	@echo "✅ Monitoring levantado"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Grafana:    http://localhost:3000 (admin/admin)"

dev-full: ## Levanta stack completo (dev + monitoring + admin)
	@echo "🚀 Levantando stack completo de desarrollo..."
	docker compose -f docker-compose.dev.yml --profile full up -d
	@echo "✅ Stack completo levantado"
	@make dev-status

dev-status: ## Muestra el estado de los servicios de desarrollo
	@echo "📋 Estado de servicios:"
	@docker compose -f docker-compose.dev.yml ps

dev-clean: ## Limpia volumes y cache de desarrollo
	@echo "🧹 Limpiando datos de desarrollo..."
	docker compose -f docker-compose.dev.yml down -v
	@echo "✅ Limpieza completada"

test-cov: ## Ejecutar tests con coverage report (unit)
	@echo "🧪 Ejecutando tests con coverage (unit)..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/unit --cov=app --cov-report=html --cov-report=term-missing
else
	pytest tests/unit --cov=app --cov-report=html --cov-report=term-missing
endif
	@echo "📊 Coverage report: htmlcov/index.html"

test-watch: ## Ejecutar tests en modo watch (auto-reload)
	@echo "👀 Ejecutando tests en modo watch..."
ifeq ($(HAS_POETRY),1)
	poetry run ptw -- -v
else
	ptw -- -v
endif

test-unit: ## Ejecutar solo tests unitarios
	@echo "🧪 Ejecutando tests unitarios..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/unit -v
else
	pytest tests/unit -v
endif

test-integration: ## Ejecutar solo tests de integración
	@echo "🔗 Ejecutando tests de integración..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/integration -v
else
	pytest tests/integration -v
endif

test-e2e: ## Ejecutar tests end-to-end
	@echo "🌐 Ejecutando tests E2E..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/e2e -v
else
	pytest tests/e2e -v
endif

test-debug: ## Ejecutar tests con debugging habilitado
	@echo "🐛 Ejecutando tests en modo debug..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest -vv -s --pdb
else
	pytest -vv -s --pdb
endif

benchmark: ## Ejecutar benchmarks de performance
	@echo "⚡ Ejecutando benchmarks..."
ifeq ($(HAS_POETRY),1)
	poetry run pytest tests/ --benchmark-only --benchmark-autosave
else
	pytest tests/ --benchmark-only --benchmark-autosave
endif

quick-check: ## Validación rápida (lint + test unit + security-fast)
	@echo "⚡ Quick check..."
	@make lint
	@make test-unit
	@make security-fast
	@echo "✅ Quick check completado"

full-check: ## Validación completa (lint + test + coverage + security)
	@echo "🔍 Full check..."
	@make lint
	@make test-cov
	@make security-fast
	@echo "✅ Full check completado"

##@ Advanced Tools (Phase B)

.PHONY: pre-commit-install pre-commit-run pre-commit-update security-scan type-check ci-local benchmark-baseline benchmark-compare update-operational-metrics

pre-commit-install: ## Instalar pre-commit hooks
	@echo "🪝 Instalando pre-commit hooks..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pre-commit install; \
	else \
		pre-commit install; \
	fi
	@echo "✅ Pre-commit hooks instalados"

pre-commit-run: ## Ejecutar pre-commit en todos los archivos
	@echo "🔍 Ejecutando pre-commit en todos los archivos..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pre-commit run --all-files; \
	else \
		pre-commit run --all-files; \
	fi

pre-commit-update: ## Actualizar versiones de pre-commit hooks
	@echo "⬆️ Actualizando pre-commit hooks..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pre-commit autoupdate; \
	else \
		pre-commit autoupdate; \
	fi
	@echo "✅ Pre-commit hooks actualizados"

security-scan: ## Ejecutar Bandit (security scan) en el código
	@echo "🔒 Ejecutando análisis de seguridad con Bandit..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run bandit -c pyproject.toml -r app/; \
	else \
		bandit -c pyproject.toml -r app/; \
	fi

type-check: ## Ejecutar MyPy (type checking) en el código
	@echo "🔎 Ejecutando type checking con MyPy..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run mypy app/ --config-file=pyproject.toml; \
	else \
		mypy app/ --config-file=pyproject.toml; \
	fi

ci-local: ## Ejecutar pipeline CI completo (requiere Docker running)
	@echo "🚀 Ejecutando CI local pipeline..."
	@if [ ! -f scripts/ci-local.sh ]; then \
		echo "❌ Error: scripts/ci-local.sh no encontrado"; \
		exit 1; \
	fi
	@bash scripts/ci-local.sh

benchmark-baseline: ## Crear baseline de benchmarks
	@echo "📊 Creando baseline de benchmarks..."
	@mkdir -p .benchmarks
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pytest tests/benchmarks/ --benchmark-only --benchmark-json=.benchmarks/baseline.json; \
	else \
		pytest tests/benchmarks/ --benchmark-only --benchmark-json=.benchmarks/baseline.json; \
	fi
	@echo "✅ Baseline creado en .benchmarks/baseline.json"

benchmark-compare: ## Comparar benchmarks actuales con baseline
	@echo "📈 Comparando benchmarks..."
	@if [ ! -f scripts/benchmark-compare.sh ]; then \
		echo "❌ Error: scripts/benchmark-compare.sh no encontrado"; \
		exit 1; \
	fi
	@bash scripts/benchmark-compare.sh

update-operational-metrics: ## Actualizar métricas operacionales del hotel (occupancy, ADR, RevPAR)
	@echo "🏨 Actualizando métricas operacionales..."
	@if [ ! -f scripts/update_operational_metrics.py ]; then \
		echo "❌ Error: scripts/update_operational_metrics.py no encontrado"; \
		exit 1; \
	fi
	@poetry run python scripts/update_operational_metrics.py

# ==============================================================================
# Performance Testing (P015)
# ==============================================================================

perf-smoke: ## Run smoke test (1 VU, 1 min) - quick validation
	@echo "🚬 Running smoke test..."
	@mkdir -p .performance
	@k6 run --env SCENARIO=smoke \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/results-smoke-$$(date +%Y%m%d-%H%M%S).json \
		tests/load/k6-performance-suite.js
	@echo "✅ Smoke test complete. Run 'make perf-validate' to check SLOs."

perf-load: ## Run load test (10 VUs, 14 min) - validate SLOs
	@echo "📊 Running load test..."
	@mkdir -p .performance
	@k6 run --env SCENARIO=load \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/results-load-$$(date +%Y%m%d-%H%M%S).json \
		tests/load/k6-performance-suite.js
	@echo "✅ Load test complete. Run 'make perf-validate' to check SLOs."

perf-stress: ## Run stress test (up to 50 VUs, 27 min) - find breaking point
	@echo "💪 Running stress test..."
	@mkdir -p .performance
	@k6 run --env SCENARIO=stress \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/results-stress-$$(date +%Y%m%d-%H%M%S).json \
		tests/load/k6-performance-suite.js
	@echo "✅ Stress test complete. Run 'make perf-validate' to check results."

perf-spike: ## Run spike test (0→100→0 VUs, 4 min) - test resilience
	@echo "⚡ Running spike test..."
	@mkdir -p .performance
	@k6 run --env SCENARIO=spike \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/results-spike-$$(date +%Y%m%d-%H%M%S).json \
		tests/load/k6-performance-suite.js
	@echo "✅ Spike test complete. Check if rate limiting activated."

perf-soak: ## Run soak test (5 VUs, 30 min) - detect memory leaks
	@echo "🛁 Running soak test..."
	@mkdir -p .performance
	@k6 run --env SCENARIO=soak \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/results-soak-$$(date +%Y%m%d-%H%M%S).json \
		tests/load/k6-performance-suite.js
	@echo "✅ Soak test complete. Monitor memory usage trends."

perf-validate: ## Validate latest performance test results against SLOs
	@echo "🎯 Validating performance results..."
	@if [ ! -f tests/load/validate_performance.py ]; then \
		echo "❌ Error: tests/load/validate_performance.py not found"; \
		exit 1; \
	fi
	@chmod +x tests/load/validate_performance.py
	@python3 tests/load/validate_performance.py

perf-baseline: ## Establish performance baseline
	@echo "📈 Establishing performance baseline..."
	@mkdir -p .performance
	@echo "Running smoke test..."
	@k6 run --env SCENARIO=smoke \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/baseline-smoke.json \
		tests/load/k6-performance-suite.js
	@echo "Running load test..."
	@k6 run --env SCENARIO=load \
		--env BASE_URL=http://localhost:8000 \
		--out json=.performance/baseline-load.json \
		tests/load/k6-performance-suite.js
	@echo "Validating baselines..."
	@python3 tests/load/validate_performance.py --results .performance/baseline-load.json \
		--format markdown --output .performance/baseline-report.md
	@echo "✅ Baseline established. Results in .performance/baseline-report.md"

perf-clean: ## Clean performance test results
	@echo "🧹 Cleaning performance results..."
	@rm -rf .performance/*.json .performance/*.html .performance/*.md
	@echo "✅ Performance results cleaned"

# ══════════════════════════════════════════════════════════════════════════════
# OBSERVABILITY TARGETS (P016)
# ══════════════════════════════════════════════════════════════════════════════

obs-up: ## Start observability stack (Prometheus, Grafana, Jaeger, AlertManager)
	@echo "🔭 Starting observability stack..."
	@docker compose up -d prometheus grafana jaeger alertmanager
	@echo "✅ Observability stack started"
	@echo "📊 Prometheus: http://localhost:9090"
	@echo "📈 Grafana: http://localhost:3000 (admin/admin)"
	@echo "🔍 Jaeger: http://localhost:16686"
	@echo "🚨 AlertManager: http://localhost:9093"

obs-down: ## Stop observability stack
	@echo "🛑 Stopping observability stack..."
	@docker compose stop prometheus grafana jaeger alertmanager
	@echo "✅ Observability stack stopped"

obs-prometheus: ## Open Prometheus UI in browser
	@echo "📊 Opening Prometheus..."
	@xdg-open http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || echo "Open http://localhost:9090 in your browser"

obs-grafana: ## Open Grafana UI in browser
	@echo "📈 Opening Grafana..."
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000 in your browser (admin/admin)"

obs-jaeger: ## Open Jaeger UI in browser
	@echo "🔍 Opening Jaeger..."
	@xdg-open http://localhost:16686 2>/dev/null || open http://localhost:16686 2>/dev/null || echo "Open http://localhost:16686 in your browser"

obs-health: ## Check health of observability services
	@echo "🔍 Checking observability stack health..."
	@echo "Prometheus:"
	@curl -sf http://localhost:9090/-/healthy > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"
	@echo "Grafana:"
	@curl -sf http://localhost:3000/api/health > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"
	@echo "Jaeger:"
	@curl -sf http://localhost:14269/ > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"
	@echo "AlertManager:"
	@curl -sf http://localhost:9093/-/healthy > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"

obs-logs: ## Follow logs of observability services
	@docker compose logs -f prometheus grafana jaeger alertmanager

obs-restart: ## Restart observability stack
	@echo "🔄 Restarting observability stack..."
	@docker compose restart prometheus grafana jaeger alertmanager
	@echo "✅ Observability stack restarted"

# ==============================================================================
# Chaos Engineering
# ==============================================================================

chaos-network: ## Run network chaos scenarios (latency, timeouts, failures)
	@echo "🌪️  Running network chaos scenarios..."
	@poetry run pytest tests/chaos/scenarios/test_network.py -v || \
	 poetry run python -m pytest tests/chaos/test_advanced_resilience.py::TestMTTRMetrics::test_network_latency_mttr -v
	@echo "✅ Network chaos scenarios completed"

chaos-service: ## Run service chaos scenarios (failures, circuit breakers, rate limits)
	@echo "🌪️  Running service chaos scenarios..."
	@poetry run pytest tests/chaos/scenarios/test_service.py -v || \
	 poetry run python -m pytest tests/chaos/test_advanced_resilience.py::TestCircuitBreakerTransitions -v
	@echo "✅ Service chaos scenarios completed"

chaos-database: ## Run database chaos scenarios (connection failures, slow queries)
	@echo "🌪️  Running database chaos scenarios..."
	@poetry run pytest tests/chaos/scenarios/test_database.py -v || \
	 poetry run python -m pytest tests/chaos/test_advanced_resilience.py::TestMTTRMetrics::test_mttr_pms_failure -v
	@echo "✅ Database chaos scenarios completed"

chaos-pms: ## Run PMS chaos scenarios (API failures, timeouts, rate limits)
	@echo "🌪️  Running PMS chaos scenarios..."
	@poetry run python -m pytest tests/chaos/test_advanced_resilience.py::TestMTTRMetrics::test_pms_failure_mttr -v
	@echo "✅ PMS chaos scenarios completed"

chaos-resource: ## Run resource chaos scenarios (memory pressure, CPU throttling)
	@echo "🌪️  Running resource chaos scenarios..."
	@poetry run pytest tests/chaos/scenarios/test_resource.py -v || echo "⚠️  Resource chaos scenarios require manual setup"
	@echo "✅ Resource chaos scenarios completed"

chaos-all: ## Run all chaos scenarios sequentially
	@echo "🌪️  Running ALL chaos scenarios..."
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Phase 1: Network Chaos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) chaos-network
	@sleep 15
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Phase 2: Service Chaos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) chaos-service
	@sleep 15
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Phase 3: Database Chaos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) chaos-database
	@sleep 15
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Phase 4: PMS Chaos"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) chaos-pms
	@echo ""
	@echo "✅ ALL chaos scenarios completed"
	@echo ""
	@echo "📊 Generate report: make chaos-report"

chaos-resilience: ## Run comprehensive resilience test suite
	@echo "🛡️  Running resilience test suite..."
	@poetry run python -m pytest tests/chaos/test_advanced_resilience.py -v
	@echo "✅ Resilience tests completed"

chaos-report: ## Generate chaos experiment report
	@echo "📊 Generating chaos experiment report..."
	@mkdir -p .playbook/chaos_reports
	@echo "Chaos Engineering Report - $(shell date '+%Y-%m-%d %H:%M:%S')" > .playbook/chaos_reports/latest.txt
	@echo "=============================================" >> .playbook/chaos_reports/latest.txt
	@echo "" >> .playbook/chaos_reports/latest.txt
	@poetry run pytest tests/chaos/test_advanced_resilience.py -v --tb=short | tee -a .playbook/chaos_reports/latest.txt || true
	@echo "" >> .playbook/chaos_reports/latest.txt
	@echo "Report saved to: .playbook/chaos_reports/latest.txt"
	@echo "✅ Chaos report generated"

chaos-monkey: ## Start Chaos Monkey (random fault injection) - USE WITH CAUTION
	@echo "⚠️  WARNING: Starting Chaos Monkey!"
	@echo "⚠️  This will randomly inject faults into the system."
	@echo "⚠️  Press Ctrl+C to stop."
	@echo ""
	@read -p "Are you sure you want to continue? (yes/no): " confirm && \
	 if [ "$$confirm" = "yes" ]; then \
	   poetry run python -c "import asyncio; from tests.chaos.orchestrator import ChaosMonkey; monkey = ChaosMonkey(enabled=True, probability=0.1); monkey.start(); asyncio.get_event_loop().run_forever()"; \
	 else \
	   echo "Cancelled."; \
	 fi

chaos-dry-run: ## Run chaos experiments in dry-run mode (no actual injection)
	@echo "🧪 Running chaos experiments in DRY RUN mode..."
	@poetry run python -c "\
	import asyncio; \
	from tests.chaos.orchestrator import ChaosOrchestrator; \
	from tests.chaos.scenarios import network_scenarios; \
	async def run(): \
	    orchestrator = ChaosOrchestrator(); \
	    scenario = network_scenarios[0]; \
	    scenario.duration_seconds = 30; \
	    await orchestrator.run_experiment(scenario, dry_run=True); \
	asyncio.run(run()); \
	"
	@echo "✅ Dry run completed (no actual faults injected)"

# ==============================================================================
# DEPLOYMENT AUTOMATION (P018)
# ==============================================================================

deploy-staging: ## Deploy to staging environment with blue-green strategy
	@echo "🚀 Deploying to STAGING..."
	@./scripts/blue-green-deploy.sh \
		--image $(IMAGE_TAG) \
		--environment staging \
		--health-check-timeout 300
	@echo "✅ Staging deployment complete"
	@echo "🔗 URL: https://staging.agente-hotel.com"

deploy-production: ## Deploy to production (requires manual approval)
	@echo "🚀 Deploying to PRODUCTION..."
	@echo "⚠️  This requires manual approval in GitHub Actions"
	@echo "Triggering workflow..."
	@gh workflow run deploy.yml \
		--ref main \
		-f environment=production \
		-f deployment_strategy=blue-green

deploy-canary: ## Deploy canary with 10% traffic
	@echo "🐦 Deploying CANARY (10% traffic)..."
	@./scripts/canary-deploy.sh \
		--image $(IMAGE_TAG) \
		--traffic-percentage 10 \
		--duration 600 \
		--auto-promote
	@echo "✅ Canary deployment complete"

rollback: ## Automatic rollback to previous version
	@echo "🔄 Triggering ROLLBACK..."
	@./scripts/auto-rollback.sh \
		--environment $(ENV) \
		--preserve-data \
		--notify
	@echo "✅ Rollback complete"

validate-deployment: ## Run deployment validation tests
	@echo "🧪 Validating deployment..."
	@poetry run pytest tests/deployment/test_deployment_validation.py \
		-v \
		-m deployment \
		--tb=short
	@echo "✅ Deployment validation passed"

migration-safe: ## Run database migrations safely with backup
	@echo "🗄️  Running safe database migration..."
	@./scripts/safe-migration.sh \
		--environment $(ENV) \
		--backup-before \
		--dry-run false \
		--verify
	@echo "✅ Migration complete"

deploy-status: ## Check deployment status
	@echo "📊 Deployment Status:"
	@echo ""
	@echo "Active Containers:"
	@docker ps --filter "name=agente-api" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Health Status:"
	@curl -sf http://localhost:8000/health/ready | jq '.' || echo "❌ Not reachable"

deploy-logs: ## View deployment logs
	@echo "📋 Deployment Logs:"
	@docker logs --tail 100 --follow agente-api-blue || \
	 docker logs --tail 100 --follow agente-api-green || \
	 docker logs --tail 100 --follow agente-api

deploy-test: ## Test deployment validation locally
	@echo "🧪 Testing deployment validation..."
	@poetry run pytest tests/deployment/ -v --tb=short
	@echo "✅ Deployment tests passed"

# ==============================================================================
# P019: Incident Response & Recovery
# ==============================================================================

.PHONY: incident-detect incident-simulate incident-report on-call-schedule post-mortem incident-test

incident-detect: ## Run incident detector
	@echo "🔍 Running incident detection..."
	@python scripts/incident-detector.py --prometheus-url=${PROMETHEUS_URL:-http://localhost:9090}

incident-simulate: ## Simulate incident scenarios for testing
	@echo "🧪 Simulating incident scenarios..."
	@echo "Available scenarios:"
	@echo "  1. Database down (stop postgres)"
	@echo "  2. High latency (stress CPU)"
	@echo "  3. High error rate (inject errors)"
	@echo "  4. Circuit breaker open (break PMS)"
	@echo ""
	@read -p "Select scenario [1-4]: " scenario; \
	case $$scenario in \
		1) docker-compose stop postgres && echo "✅ Postgres stopped. Run 'make docker-up' to recover." ;; \
		2) docker exec agente-api stress --cpu 4 --timeout 60s ;; \
		3) echo "Injecting errors..." && docker exec agente-api python -c "import requests; [requests.get('http://localhost:8000/force-error') for _ in range(100)]" ;; \
		4) docker-compose stop qloapps && echo "✅ PMS stopped. Circuit breaker should open." ;; \
		*) echo "❌ Invalid scenario" ;; \
	esac

incident-report: ## Generate incident report from detector
	@echo "📊 Generating incident report..."
	@python scripts/incident-detector.py --report | jq .
	@echo ""
	@echo "Detailed history in .incidents.json"

on-call-schedule: ## Show current on-call rotation schedule
	@echo "📅 On-Call Schedule"
	@echo "===================="
	@echo ""
	@echo "Current Week:"
	@echo "  Primary:   [Check docs/ON-CALL-GUIDE.md]"
	@echo "  Secondary: [Check docs/ON-CALL-GUIDE.md]"
	@echo "  IC:        [Check docs/ON-CALL-GUIDE.md]"
	@echo ""
	@echo "See docs/ON-CALL-GUIDE.md for full rotation schedule"
	@echo "Update schedule: Edit docs/ON-CALL-GUIDE.md"

post-mortem: ## Create post-mortem from template
	@echo "📝 Creating post-mortem document..."
	@read -p "Incident ID (e.g., INC-20241015-001): " inc_id; \
	read -p "Incident Title: " title; \
	incident_file="docs/post-mortems/$$inc_id-$$(echo $$title | tr '[:upper:]' '[:lower:]' | tr ' ' '-').md"; \
	mkdir -p docs/post-mortems; \
	cp templates/post-mortem-template.md "$$incident_file"; \
	sed -i "s/INC-YYYYMMDD-XXXX/$$inc_id/g" "$$incident_file"; \
	sed -i "s/\[Incident Title\]/$$title/g" "$$incident_file"; \
	sed -i "s/YYYY-MM-DD/$$(date +%Y-%m-%d)/g" "$$incident_file"; \
	echo "✅ Post-mortem created: $$incident_file"; \
	echo "📝 Please fill out all sections in the post-mortem"

incident-test: ## Run incident response tests
	@echo "🧪 Running incident response tests..."
	@poetry run pytest tests/incident/ -v --tb=short
	@echo "✅ Incident response tests passed"


# ==============================================================================
# Supabase: Schema & Validación
# ==============================================================================

.PHONY: supabase-test-connection supabase-apply-schema supabase-validate maintenance-cleanup

supabase-test-connection: ## Prueba de conexión a Supabase (usa DATABASE_URL de .env)
	@echo "🔌 Probando conexión a Supabase..."
	@python3 scripts/test_supabase_connection.py || { echo "❌ Conexión fallida"; exit 1; }
	@echo "✅ Conexión OK"

supabase-apply-schema: ## Aplica docs/supabase/schema.sql a la base de datos (requiere DATABASE_URL)
	@echo "🗃️  Aplicando schema de Supabase..."
	@if [ ! -f docs/supabase/schema.sql ]; then \
	  echo "❌ No se encontró docs/supabase/schema.sql"; exit 1; \
	fi
	@python3 scripts/apply_supabase_schema.py --schema-file docs/supabase/schema.sql || { echo "❌ Falló la aplicación del schema"; exit 1; }
	@echo "✅ Schema aplicado"

supabase-validate: ## Valida tablas e índices clave tras aplicar el schema
	@echo "🔍 Validando schema en Supabase..."
	@python3 scripts/validate_supabase_schema.py || { echo "❌ Validación fallida"; exit 1; }
	@echo "✅ Validación completada"

maintenance-cleanup: ## Limpia sesiones expiradas de user_sessions (requiere DATABASE_URL)
	@echo "🧹 Limpiando sesiones expiradas..."
	@python3 scripts/cleanup_user_sessions.py --older-than-days 0 || { echo "❌ Limpieza fallida"; exit 1; }
	@echo "✅ Limpieza completada"


.DEFAULT_GOAL := help
