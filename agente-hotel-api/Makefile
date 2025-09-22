.PHONY: install fmt lint test run build clean help dev-setup docker-up docker-down backup restore logs health

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
	@docker exec -it agente_alertmanager sh -c 'cat /etc/alertmanager/generated.yml || echo "generated.yml no disponible aún"'

test-alert-429: ## Genera tráfico para provocar 429 en /webhooks/whatsapp
	@chmod +x scripts/generate_429.sh
	@HOST=localhost PORT=8000 REQUESTS=90 DELAY_MS=30 bash scripts/generate_429.sh

help: ## Muestra esta ayuda
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z0-9_\-]+:.*?##/ {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


.DEFAULT_GOAL := help
