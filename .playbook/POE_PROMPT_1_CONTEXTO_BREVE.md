# PROMPT 1 – Contexto de Knowledge Base (Versión Compacta para Poe.com)

## 📦 Origen de los Archivos de Conocimiento

El conocimiento de este bot proviene de **4 archivos `.txt`** generados con un script de extracción TIER-priorizado (`prepare_for_poe.py`) del repositorio **SIST_AGENTICO_HOTELERO**.

### Estructura de los Archivos

- **`parte_1.txt` (630 KB)**  
  Documentación crítica y prompts de diseño:
  - `.playbook/POE_PROMPT_*` (prompts originales)
  - `.playbook/PRODUCTION_READINESS_CHECKLIST.md`
  - `MASTER_PROJECT_GUIDE.md`
  - READMEs principales (proyecto, infra, database, performance)

- **`parte_2.txt` (138 KB)**  
  Infraestructura y deployment:
  - `docker-compose.yml`, `docker-compose.staging.yml`, `docker-compose.production.yml`
  - `Dockerfile`, `Dockerfile.production`
  - `Makefile` (46 targets)
  - Scripts de deployment (`deploy-staging.sh`, `preflight.py`, `canary-deploy.sh`)
  - Configuración Prometheus/Grafana

- **`parte_3.txt` (84 KB)**  
  Tests críticos y blueprints:
  - Tests unitarios/integración/chaos del orchestrator
  - Blueprints de optimización y roadmaps
  - Documentación de arquitectura

- **`parte_4.txt` (7.7 MB)**  
  Resto del código y documentación:
  - 684 archivos (servicios, modelos, routers, utils, docs extendidas)

### Metadata del Proyecto

- **Commit base**: `97676bcc27f7f999f602432a07383ce09c5dee68`
- **Branch**: `feature/etapa2-qloapps-integration`
- **Deployment readiness**: 8.9/10
- **Test coverage**: 31% (28/891 tests passing)
- **CVE status**: 0 CRITICAL
- **Stack**: Python 3.12.3, FastAPI, Docker Compose (7 servicios: agente-api, postgres, redis, prometheus, grafana, alertmanager, jaeger)

### Formato de los Archivos

Todos los archivos incluyen para cada entrada:
- Ruta relativa al proyecto
- TIER de prioridad (1=CRITICAL → 5=MISC)
- Tamaño en bytes
- Checksum SHA256 (primeros 16 caracteres)

---

**Uso en Poe.com**: Esta nota puede incluirse opcionalmente al inicio del system prompt o como mensaje inicial si el bot necesita entender el contexto de su knowledge base. No es necesario incluir los detalles de implementación del script de extracción.
