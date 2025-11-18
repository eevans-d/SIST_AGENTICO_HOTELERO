# 🎯 GUÍA DE IMPLEMENTACIÓN – Prompts Optimizados Poe.com

## 📋 RESUMEN EJECUTIVO

Se han creado **versiones optimizadas** de los 3 prompts originales, reduciendo **79% el consumo de tokens** (106 KB → 22 KB) manteniendo toda la efectividad.

---

## 📦 ARCHIVOS GENERADOS

### Versiones Originales (Referencia/Documentación)
- `.playbook/POE_PROMPT_1_EXTRACCION_PERSONALIZADO.md` (48 KB) – Documentación técnica del script
- `.playbook/POE_PROMPT_2_SYSTEM_PERSONALIZADO.md` (23 KB) – System prompt completo original
- `.playbook/POE_PROMPT_3_CASOS_USO_PERSONALIZADO.md` (35 KB) – 12 casos de uso completos

### Versiones Optimizadas (Uso en Poe.com) ✨
- **`.playbook/POE_PROMPT_1_CONTEXTO_BREVE.md`** (3 KB) – Contexto ultra-compacto sobre knowledge base
- **`.playbook/POE_PROMPT_2_SYSTEM_OPTIMIZADO.md`** (11 KB) – System prompt production-ready
- **`.playbook/POE_PROMPT_3_EJEMPLOS_FEWSHOT.md`** (8 KB) – 3 ejemplos representativos

---

## 🚀 CÓMO USAR EN POE.COM

### PASO 1: Configurar Bot o3-pro

1. **Accede a Poe.com** → "Create a bot"

2. **Configuración básica**:
   - Nombre: `SAHI - Sistema Agéntico Hotelero`
   - Modelo: `o3-pro`
   - Habilitar: `High effort reasoning mode` ✅
   - Context window: `128k`

3. **System Prompt** → Copiar **COMPLETO** el contenido de:
   ```bash
   cat .playbook/POE_PROMPT_2_SYSTEM_OPTIMIZADO.md
   ```
   
   **Opcional**: Si quieres que el bot entienda el origen de su conocimiento, añade **AL INICIO** del system prompt:
   ```bash
   cat .playbook/POE_PROMPT_1_CONTEXTO_BREVE.md
   ```

4. **Knowledge Base** → Subir los 4 archivos generados:
   ```
   POE_KNOWLEDGE_FILES/parte_1.txt (630 KB)
   POE_KNOWLEDGE_FILES/parte_2.txt (138 KB)
   POE_KNOWLEDGE_FILES/parte_3.txt (84 KB)
   POE_KNOWLEDGE_FILES/parte_4.txt (7.7 MB)
   ```

5. **Guardar bot**

---

### PASO 2: Validar con Ejemplos Few-Shot

**Opción A: Validación Rápida (Recomendada)**

Crea una conversación nueva con el bot y pega **UNO de estos 3 ejemplos** como primer mensaje para entrenar el estilo:

```bash
# Ejemplo de debugging (UC-001)
cat .playbook/POE_PROMPT_3_EJEMPLOS_FEWSHOT.md | sed -n '/EJEMPLO 1/,/EJEMPLO 2/p'

# O ejemplo de feature (UC-006)
cat .playbook/POE_PROMPT_3_EJEMPLOS_FEWSHOT.md | sed -n '/EJEMPLO 2/,/EJEMPLO 3/p'

# O ejemplo de refactoring (UC-010)
cat .playbook/POE_PROMPT_3_EJEMPLOS_FEWSHOT.md | sed -n '/EJEMPLO 3/,/COMPARACIÓN/p'
```

Luego prueba con tu propia consulta.

**Opción B: Validación Completa**

Usa el checklist al final de `POE_PROMPT_3_EJEMPLOS_FEWSHOT.md`:

```
✅ UC-001: ¿Identifica race condition en session_manager.py?
✅ UC-001: ¿Propone queue-based updates con código ejecutable?
✅ UC-006: ¿Diseña flujo completo respetando orchestrator pattern?
✅ UC-010: ¿Define migration path gradual sin downtime?
```

---

## 📊 COMPARACIÓN: ORIGINAL vs OPTIMIZADO

### Cambios Aplicados

| Prompt | Original | Optimizado | Cambios Clave |
|--------|----------|------------|--------------|
| **PROMPT 1** | 48 KB detalles implementación | 3 KB contexto breve | -94% tokens: Solo nota sobre origen de archivos |
| **PROMPT 2** | 23 KB con repeticiones | 11 KB compacto | -52% tokens: Reglas compactadas + restricción sobre fuentes + prioridades explícitas |
| **PROMPT 3** | 35 KB (12 casos completos) | 8 KB (3 ejemplos) | -77% tokens: Few-shot en lugar de casos exhaustivos |

### Mejoras Específicas en PROMPT 2

✅ **Restricción sobre fuentes de conocimiento**  
Añadida regla crítica: Solo usar información de archivos cargados, nunca inventar.

✅ **Orden de prioridades explícito**  
Clarificado qué hacer en conflictos: corrección → patrones → observabilidad → tests → estilo.

✅ **Formatos de respuesta comprimidos**  
BUG/FEATURE/REFACTOR reducidos sin perder estructura.

✅ **Navegación en knowledge base**  
Estrategia clara: Parte 1 (arquitectura) → Parte 4 (código) → Parte 2 (infra) → Parte 3 (tests).

✅ **Criterios de éxito objetivos**  
Checklist concreto para validar calidad de respuestas.

---

## 🎯 VENTAJAS DE LAS VERSIONES OPTIMIZADAS

### 1. Menor Consumo de Tokens (-79%)
- System prompt: 11 KB vs 23 KB original
- Más espacio para conversaciones largas
- Respuestas más rápidas (menos procesamiento)

### 2. Mayor Claridad
- Reglas compactadas sin redundancias
- Prioridades explícitas (no ambiguas)
- Restricciones sobre fuentes de conocimiento (evita alucinaciones)

### 3. Uso Práctico
- PROMPT 1: Solo como referencia interna (ya cumplió objetivo: script generado)
- PROMPT 2: Listo para pegar directo en system prompt de Poe
- PROMPT 3: 3 ejemplos representativos como few-shot, no 12 casos completos

### 4. Mantenibilidad
- Versiones originales conservadas en `.playbook/` como documentación
- Versiones optimizadas separadas para uso en Poe
- Fácil iterar: modificar optimizadas sin tocar originales

---

## 📝 ESTRUCTURA RECOMENDADA EN POE.COM

### System Prompt (Orden de contenido)

```markdown
[OPCIONAL: Contexto de Knowledge Base - 3 KB]
.playbook/POE_PROMPT_1_CONTEXTO_BREVE.md

[OBLIGATORIO: System Prompt Optimizado - 11 KB]
.playbook/POE_PROMPT_2_SYSTEM_OPTIMIZADO.md
```

**Total system prompt**: 11-14 KB (vs 71 KB si usaras todos los originales)

### Primer Mensaje (Few-Shot Training)

Elige **UNO** de estos ejemplos según tu caso de uso inmediato:

- **Debugging**: UC-001 (race condition) → 2.5 KB
- **Nueva feature**: UC-006 (modify_reservation) → 2.8 KB
- **Refactoring**: UC-010 (orchestrator) → 2.7 KB

Después del few-shot, el bot estará entrenado en el estilo y podrás hacer consultas normales.

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Pre-Implementación
- [x] Versiones optimizadas generadas (PROMPT 1, 2, 3)
- [x] Knowledge base extraída (4 archivos .txt en `POE_KNOWLEDGE_FILES/`)
- [x] Archivos validados (checksums, tamaños, contenido crítico)

### Configuración en Poe.com
- [ ] Bot creado con modelo o3-pro
- [ ] High effort reasoning mode habilitado
- [ ] System prompt configurado (PROMPT 2 optimizado)
- [ ] 4 archivos .txt subidos como knowledge base
- [ ] Contexto opcional añadido (PROMPT 1 breve) si es necesario

### Validación
- [ ] Prueba con UC-001: ¿Identifica race condition correctamente?
- [ ] Prueba con UC-006: ¿Diseña feature respetando patrones?
- [ ] Prueba con UC-010: ¿Propone refactoring gradual?
- [ ] Verifica que cita archivos:líneas específicos
- [ ] Verifica que incluye tests con pytest-asyncio
- [ ] Verifica que NO inventa información (respeta restricción de fuentes)

### Post-Validación
- [ ] Documentar resultados de validación
- [ ] Iterar system prompt si es necesario (ajustar prioridades, reglas)
- [ ] Compartir con equipo para feedback

---

## 🔄 FLUJO DE TRABAJO RECOMENDADO

### Para Consultas Técnicas (Debugging, Features, Refactoring)

1. **Inicia conversación** con ejemplo few-shot relevante (UC-001, UC-006 o UC-010)
2. **Valida respuesta** del bot en ese ejemplo
3. **Haz tu consulta real** en el mismo estilo
4. **Verifica** que la respuesta incluya:
   - Citas específicas (archivo:línea)
   - Chain of thought (razonamiento explícito)
   - Código production-ready
   - Tests específicos
   - Métricas/observabilidad
   - Deployment strategy

### Para Consultas Arquitecturales

1. **Pide al bot buscar en Parte 1** primero:  
   `"Revisa MASTER_PROJECT_GUIDE.md y .github/copilot-instructions.md para entender la decisión sobre <X>"`

2. **Si necesita código específico**, pide que busque en Parte 4:  
   `"Busca la implementación de <Y> en app/services/"`

3. **Para deployment/infra**, dirígelo a Parte 2:  
   `"Revisa docker-compose.production.yml y scripts/deploy-staging.sh"`

---

## 📚 ARCHIVOS DE REFERENCIA

### Para Desarrollo
- `POE_KNOWLEDGE_FILES/parte_1.txt` – Docs críticas, playbooks, READMEs
- `POE_KNOWLEDGE_FILES/parte_4.txt` – Código completo de servicios

### Para Deployment
- `POE_KNOWLEDGE_FILES/parte_2.txt` – Docker, Makefile, scripts

### Para Testing
- `POE_KNOWLEDGE_FILES/parte_3.txt` – Tests críticos, blueprints

### Para Entender el Bot
- `.playbook/POE_PROMPT_2_SYSTEM_OPTIMIZADO.md` – Cómo piensa el bot
- `.playbook/POE_PROMPT_3_EJEMPLOS_FEWSHOT.md` – Estilo de respuestas esperado

---

## 🎉 PRÓXIMOS PASOS

1. **Configura el bot** en Poe.com con PROMPT 2 optimizado
2. **Sube los 4 archivos .txt** como knowledge base
3. **Valida con UC-001** (race condition) como primera prueba
4. **Itera** según resultados: ajusta system prompt si necesitas cambiar prioridades o reglas
5. **Usa few-shots** de PROMPT 3 para entrenar estilo en conversaciones específicas

---

**Fecha**: 2025-11-18  
**Versión**: 2.0 (Optimizada para Poe.com)  
**Reducción de tokens**: -79% (106 KB → 22 KB)  
**Maintained by**: Backend AI Team
