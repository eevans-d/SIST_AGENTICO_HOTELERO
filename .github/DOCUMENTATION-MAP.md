# �� AI Agent Documentation Map & Quick Reference

Este es un mapa visual de toda la documentación disponible para agentes IA en el proyecto Agente Hotelero.

---

## 🗺️ Documentación en .github/

```
.github/
│
├─ README.md ⭐ START HERE
│  └─ Centro de navegación para toda documentación
│  └─ Aprox: 5 min para leer
│  └─ Propósito: Orientación rápida
│
├─ copilot-instructions.md ⭐ DEFINITIVE REFERENCE
│  └─ Especificación técnica completa
│  └─ Aprox: 45 min para leer completo
│  └─ Propósito: Entender la arquitectura completa
│  └─ Secciones clave:
│     ├─ Core Patterns (5 patrones con código)
│     ├─ Development Workflows (locales y deployment)
│     ├─ Logging & Monitoring (estructurado)
│     ├─ Testing Structure (891 tests)
│     └─ Integration Points (WhatsApp, Gmail, PMS)
│
├─ AI-AGENT-QUICKSTART.md ⭐ START HERE FOR TASKS
│  └─ Guía de primeros pasos
│  └─ Aprox: 15 min para leer
│  └─ Propósito: Tareas comunes con código
│  └─ Secciones clave:
│     ├─ 30 Seconds Overview
│     ├─ First Steps (5-30 min)
│     ├─ Common Tasks (7 patrones)
│     ├─ Anti-Patterns (6 categorías)
│     ├─ Testing Quick Ref
│     ├─ Debugging Guide (5 scenarios)
│     └─ Learning Path (4 semanas)
│
├─ AI-AGENT-CONTRIBUTING.md ⭐ BEFORE COMMITTING
│  └─ Estándares de contribución
│  └─ Aprox: 25 min para leer
│  └─ Propósito: Escribir código de calidad
│  └─ Secciones clave:
│     ├─ Contribution Principles (4 prioridades)
│     ├─ Pre-Commit Checklist
│     ├─ Architecture Patterns (services, routers, models)
│     ├─ Code Examples (con código real)
│     ├─ Code Review Checklist (14 puntos)
│     ├─ Common Mistakes (7 categorías)
│     └─ Final PR Checklist
│
└─ DOCUMENTATION-MAP.md ← YOU ARE HERE
   └─ Este mapa visual
   └─ Aprox: 5 min para leer
   └─ Propósito: Navegar documentación rápidamente
```

---

## 🎯 Matriz de Decisión: Qué Leer

### "Quiero entender QUÉ es este proyecto"
```
1. Lee: .github/README.md (5 min)
   └─ Sección: Quick Start + Architecture Overview
```

### "Quiero empezar a trabajar YA"
```
1. Lee: .github/AI-AGENT-QUICKSTART.md (15 min)
   └─ Secciones: First Steps (30 min setup)
2. Ejecuta: make dev-setup && make docker-up (10 min)
3. Verifica: make health (2 min)
4. Elige una tarea → Busca en QUICKSTART
```

### "Quiero entender la arquitectura COMPLETAMENTE"
```
1. Lee: .github/copilot-instructions.md (45 min)
   └─ Enfoque en: Core Patterns + Services
2. Lee código: app/services/orchestrator.py (20 min)
3. Lee código: app/services/pms_adapter.py (15 min)
4. Lee tests: tests/integration/ (15 min)
5. Entender: traza un mensaje completo (10 min)
```

### "Voy a contribuir código"
```
1. Lee: .github/AI-AGENT-CONTRIBUTING.md (25 min)
   └─ Enfoque en: Pre-Commit Checklist + Code Examples
2. Lee: .github/AI-AGENT-QUICKSTART.md (10 min)
   └─ Para referencia rápida
3. Busca patrón similar en: app/services/ (5 min)
4. Sigue el patrón del ejemplo (5-30 min código)
5. Verifica: make fmt && make lint && make test (5 min)
```

### "Necesito debuggear AHORA"
```
1. Ve a: .github/AI-AGENT-QUICKSTART.md
   └─ Sección: "Debugging Common Issues"
2. Sigue pasos específicos para tu caso
3. Si no encuentras: .github/README.md → FAQ
```

### "Quiero agregar una nueva intención NLP"
```
1. Lee: .github/AI-AGENT-QUICKSTART.md
   └─ Sección: "Tarea: Agrega una nueva intención NLP"
2. Implementa: Sigue el patrón mostrado (1-2 horas)
3. Tests: Copia patrón de test existente (30 min)
4. Verifica: make test && make lint (5 min)
```

### "Quiero agregar una métrica Prometheus"
```
1. Lee: .github/AI-AGENT-CONTRIBUTING.md
   └─ Sección: "Metrics Contribution Guidelines"
2. Implementa: Patrón Counter/Histogram (15 min)
3. Documenta: README-Infra.md (10 min)
4. Verifica: make test (5 min)
```

### "Necesito hacer deploy a staging mañana"
```
1. Lee: ../CHECKLIST-DEPLOYMENT-MANANA.md
2. Lee: ../scripts/deploy-staging.sh
3. Ejecuta checklist paso a paso (60-90 min)
```

---

## 📖 Learning Paths Según Tu Experiencia

### Principiante Absoluto (AI Nuevo en el Proyecto)
```
Tiempo Total: ~3 horas

1. Leer (1 hora):
   - .github/README.md (5 min)
   - .github/AI-AGENT-QUICKSTART.md (15 min)
   - .github/copilot-instructions.md Core Patterns (40 min)

2. Hands-on (1 hora):
   - make dev-setup (5 min)
   - make docker-up (10 min)
   - make health (2 min)
   - Trazar mensaje en orchestrator.py (20 min)
   - Leer primer test (13 min)
   - make test (10 min)

3. Primera Tarea (1 hora):
   - Fijar un pequeño bug o añadir logs
   - Escribir test simple
   - Hacer commit
```

### Intermedio (AI con Experiencia en Python)
```
Tiempo Total: ~1.5 horas

1. Leer (30 min):
   - .github/AI-AGENT-QUICKSTART.md (10 min)
   - .github/AI-AGENT-CONTRIBUTING.md (20 min)

2. Code Exploration (30 min):
   - app/services/orchestrator.py - métodos handlers
   - app/services/pms_adapter.py - circuit breaker
   - tests/integration/test_orchestrator.py

3. Primera Tarea (30 min):
   - Implementar una tarea de complejidad media
   - Escribir tests completos
   - Hacer commit
```

### Avanzado (AI Senior Developer)
```
Tiempo Total: ~30 min

1. Lectura Rápida (15 min):
   - .github/copilot-instructions.md - Skip intro, go to code
   - .github/AI-AGENT-CONTRIBUTING.md - Review checklist

2. Code Dive (15 min):
   - Revisar arquitectura en app/services/
   - Revisar tests en tests/integration/
   - Identificar área de contribución

3. Empezar a Trabajar (Inmediato)
```

---

## 🔍 Búsqueda Rápida por Tema

### Orquestación del Mensaje
- **Cómo funciona**: copilot-instructions.md → "Orchestrator Pattern"
- **Código**: app/services/orchestrator.py líneas 48-100
- **Tests**: tests/integration/test_orchestrator.py
- **Task Guide**: AI-AGENT-QUICKSTART.md → "Tarea: Agrega nueva intención"

### Adaptador PMS
- **Cómo funciona**: copilot-instructions.md → "PMS Adapter Pattern"
- **Código**: app/services/pms_adapter.py
- **Resilencia**: app/core/circuit_breaker.py
- **Tests**: tests/integration/test_pms_integration.py
- **Debugging**: AI-AGENT-QUICKSTART.md → "Debugging"

### Normalización de Mensajes
- **Schema**: app/models/unified_message.py
- **Cómo se usa**: app/services/message_gateway.py
- **Ejemplos**: copilot-instructions.md → "Message Gateway Pattern"
- **Tests**: tests/unit/test_message_gateway.py

### Gestión de Sesiones
- **Cómo funciona**: copilot-instructions.md → "Session Management Pattern"
- **Código**: app/services/session_manager.py
- **Locks**: app/services/lock_service.py
- **ORM**: app/models/ (session-related tables)

### Testing
- **Estructura**: copilot-instructions.md → "Testing Structure"
- **Patterns**: AI-AGENT-QUICKSTART.md → "Testing Quick Reference"
- **Ejemplos**: tests/conftest.py
- **Guía**: AI-AGENT-CONTRIBUTING.md → "Tests Pattern"

### Monitoreo & Métricas
- **Prometheus**: copilot-instructions.md → "Prometheus Metrics"
- **Agregar métrica**: AI-AGENT-CONTRIBUTING.md → "Metrics Guidelines"
- **Referencia**: ../README-Infra.md

### Debugging
- **Guía**: AI-AGENT-QUICKSTART.md → "Debugging Common Issues"
- **Runbooks**: ../docs/runbooks/ (operaciones)
- **Health checks**: app/routers/health.py
- **Logs**: Structured logging en app/core/logging.py

---

## 📊 Documentación por Componente

### app/services/orchestrator.py
```
Aprende:
├─ copilot-instructions.md → Orchestrator Pattern
├─ AI-AGENT-QUICKSTART.md → "Tarea: Nueva intención"
├─ AI-AGENT-CONTRIBUTING.md → Services Pattern
└─ Código en:
   ├─ líneas 48-100: Intent dispatcher
   ├─ líneas 150-300: Handler methods
   └─ líneas 400+: Specific intents
```

### app/services/pms_adapter.py
```
Aprende:
├─ copilot-instructions.md → PMS Adapter Pattern
├─ app/core/circuit_breaker.py → CB implementation
├─ AI-AGENT-QUICKSTART.md → "Debugging"
└─ Código en:
   ├─ líneas 54-120: Circuit breaker setup
   ├─ líneas 200-250: API calls
   ├─ líneas 300+: Caching logic
   └─ líneas 400+: Error handling
```

### tests/
```
Aprende:
├─ copilot-instructions.md → Testing Structure
├─ AI-AGENT-QUICKSTART.md → Testing Quick Ref
├─ AI-AGENT-CONTRIBUTING.md → Tests Pattern
└─ Explora:
   ├─ tests/conftest.py: Fixtures
   ├─ tests/unit/: Unit test patterns
   ├─ tests/integration/: Integration patterns
   └─ tests/mocks/: Mock server
```

---

## ✅ Verificación Rápida

Antes de cualquier cambio:
```bash
# 1. ¿Leí la documentación correcta?
grep -r "tu-palabra-clave" .github/

# 2. ¿Encontré código similar?
grep -r "tu-patrón" app/

# 3. ¿Hay tests para esto?
grep -r "tu-funcionalidad" tests/

# 4. ¿Estoy siguiendo el pre-commit checklist?
cat .github/AI-AGENT-CONTRIBUTING.md | grep -A 20 "Pre-Commit"
```

---

## 📞 Documentation as Help

Si tienes una pregunta:

1. **Busca en copilot-instructions.md**
   ```bash
   grep -i "tu-pregunta" .github/copilot-instructions.md
   ```

2. **Si no encuentras, busca en QUICKSTART**
   ```bash
   grep -i "tu-pregunta" .github/AI-AGENT-QUICKSTART.md
   ```

3. **Si aún no hay respuesta, busca FAQ**
   - `.github/AI-AGENT-QUICKSTART.md` → FAQ section
   - `.github/README.md` → FAQ section

4. **Si nada funciona, busca patrón en código**
   ```bash
   grep -r "patrón-similar" app/ tests/
   ```

---

## 🎓 Knowledge Progression

**Semana 1**: Fundamentos
- Leer: copilot-instructions.md (completo)
- Ejecutar: make dev-setup && make docker-up
- Entender: Message flow en orchestrator

**Semana 2**: Tareas Simples
- Tarea 1: Fijar un bug pequeno
- Tarea 2: Agregar logs a operación
- Tarea 3: Escribir unit test simple

**Semana 3**: Tareas Intermedias
- Tarea 4: Nueva intención NLP
- Tarea 5: Nueva métrica Prometheus
- Tarea 6: Optimizar query

**Semana 4**: Tareas Complejas
- Tarea 7: Feature completa (services + tests)
- Tarea 8: Refactoring grande
- Tarea 9: Integración multi-servicio

---

## 📚 Reference Card

```
LECTURA RÁPIDA (5 MIN)
├─ .github/README.md
└─ This map

LECTURA MEDIA (15-25 MIN)
├─ .github/AI-AGENT-QUICKSTART.md
├─ .github/AI-AGENT-CONTRIBUTING.md
└─ .github/copilot-instructions.md [solo secciones]

LECTURA COMPLETA (45+ MIN)
├─ .github/copilot-instructions.md [completo]
├─ Código en app/services/
└─ Tests en tests/

EJECUCIÓN (10-90 MIN)
├─ make dev-setup
├─ make docker-up
├─ make test
├─ [tu código]
├─ make fmt && make lint && make test
└─ git commit
```

---

**Last Updated**: 2025-10-17  
**Status**: ✅ Complete Documentation Map  
**Next**: Pick a path above and start learning!
