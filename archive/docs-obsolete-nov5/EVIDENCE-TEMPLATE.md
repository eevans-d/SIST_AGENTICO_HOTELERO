# Template de Evidencia de Validación

**Versión**: 1.0  
**Propósito**: Formato estándar para documentar evidencias de validación de cada ítem del checklist P020

---

## Instrucciones de Uso

1. **Copiar este template** para cada ítem validado
2. **Nombrar el archivo**: `evidence_[categoría]_[número]_[nombre-corto].md`
   - Ejemplo: `evidence_1_1_kubernetes-cluster.md`
3. **Completar todas las secciones** marcadas como REQUERIDO
4. **Adjuntar screenshots/logs** en carpeta `evidences/attachments/`
5. **Guardar** en carpeta compartida del proyecto

---

## EVIDENCIA DE VALIDACIÓN

### 1. Información del Ítem

**ID del Ítem**: [Ej: 1.1]  
**Categoría**: [Ej: Infraestructura]  
**Descripción**: [Copiar descripción del checklist]  
**Criticidad**: [ ] Crítico  [ ] No crítico  
**Responsable**: [Nombre del validador]  
**Fecha de validación**: [YYYY-MM-DD]

---

### 2. Resultado de la Validación

**Status**: [ ] PASS ✅  [ ] PARTIAL 🟡  [ ] FAIL ❌  [ ] PENDING ⏳

**Score**: ___/10

---

### 3. Criterios de Validación (REQUERIDO)

Listar cada criterio del checklist y marcar si se cumple:

- [ ] **Criterio 1**: [Descripción]
  - **Status**: PASS/PARTIAL/FAIL
  - **Evidencia**: [Referencia a screenshot/log/documento]

- [ ] **Criterio 2**: [Descripción]
  - **Status**: PASS/PARTIAL/FAIL
  - **Evidencia**: [Referencia a screenshot/log/documento]

- [ ] **Criterio 3**: [Descripción]
  - **Status**: PASS/PARTIAL/FAIL
  - **Evidencia**: [Referencia a screenshot/log/documento]

[Agregar más criterios según sea necesario]

---

### 4. Evidencias Adjuntas (REQUERIDO)

Lista de archivos adjuntos con descripción:

1. **Screenshot 1**: `screenshot_[item-id]_[descripción].png`
   - **Descripción**: [Qué muestra el screenshot]
   - **Timestamp**: [Cuándo fue capturado]

2. **Log file 1**: `log_[item-id]_[descripción].txt`
   - **Descripción**: [Qué contiene el log]
   - **Período**: [Rango de tiempo del log]

3. **Documento 1**: `doc_[item-id]_[descripción].pdf`
   - **Descripción**: [Qué documenta]

[Agregar más evidencias según sea necesario]

---

### 5. Procedimiento de Validación (REQUERIDO)

Describir paso a paso cómo se realizó la validación:

```
1. [Paso 1 - Ej: Acceder a dashboard de Grafana]
2. [Paso 2 - Ej: Verificar panel "Kubernetes Cluster Health"]
3. [Paso 3 - Ej: Confirmar que todos los nodos están en estado "Ready"]
4. [Paso 4 - Ej: Capturar screenshot del dashboard]
5. [Paso 5 - Ej: Ejecutar comando `kubectl get nodes`]
6. [Paso 6 - Ej: Verificar salida del comando]
```

---

### 6. Comandos Ejecutados (si aplica)

```bash
# Listar comandos ejecutados durante la validación
$ comando1
$ comando2
$ comando3
```

**Salida relevante**:
```
[Pegar salida de comandos clave]
```

---

### 7. Configuraciones Verificadas (si aplica)

**Archivo**: [Ruta del archivo de configuración]  
**Sección**: [Sección relevante]

```yaml
# Configuración verificada
key1: value1
key2: value2
key3: value3
```

---

### 8. Métricas Observadas (si aplica)

| Métrica | Valor Observado | Threshold Esperado | Status |
|---------|-----------------|-------------------|---------|
| [Ej: CPU Usage] | [Ej: 45%] | [Ej: <80%] | ✅ PASS |
| [Ej: Memory Usage] | [Ej: 65%] | [Ej: <85%] | ✅ PASS |
| [Ej: Response Time] | [Ej: 120ms] | [Ej: <200ms] | ✅ PASS |

---

### 9. Gaps Identificados (si PARTIAL o FAIL)

**¿Se identificaron gaps?**: [ ] Sí  [ ] No

**Si SÍ, describir cada gap**:

#### Gap 1
- **Descripción**: [Qué gap se encontró]
- **Impacto**: [ ] Alto  [ ] Medio  [ ] Bajo
- **Likelihood**: [ ] Alta  [ ] Media  [ ] Baja
- **Clasificación de riesgo**: [CRÍTICO/ALTO/MEDIO/BAJO]
- **¿Bloquea lanzamiento?**: [ ] Sí  [ ] No

#### Gap 2
[Repetir para cada gap identificado]

---

### 10. Plan de Mitigación (si PARTIAL o FAIL)

**¿Se requiere mitigación?**: [ ] Sí  [ ] No

**Si SÍ, describir plan**:

#### Plan para Gap 1
- **Opción 1: Remediar**
  - **Acciones**: [Lista de acciones específicas]
  - **Owner**: [Responsable]
  - **Timeline**: [Cuándo se completará]
  - **Esfuerzo estimado**: [Horas/días]

- **Opción 2: Workaround**
  - **Descripción**: [Cómo se puede trabajar alrededor del gap]
  - **Limitaciones**: [Qué limitaciones tiene el workaround]
  - **Plan de resolución futura**: [Cuándo se resolverá definitivamente]

- **Opción 3: Aplazar lanzamiento**
  - **Justificación**: [Por qué es necesario aplazar]
  - **Nuevo timeline**: [Cuándo se podría lanzar]

**Recomendación**: [Cuál opción se recomienda y por qué]

---

### 11. Dependencias

**¿Este ítem depende de otros?**: [ ] Sí  [ ] No

**Si SÍ, listar dependencias**:
- Item ID: [Ej: 1.2] - Status: [PASS/PENDING/FAIL]
- Item ID: [Ej: 3.4] - Status: [PASS/PENDING/FAIL]

**¿Otros ítems dependen de este?**: [ ] Sí  [ ] No

**Si SÍ, listar dependientes**:
- Item ID: [Ej: 4.5] - [Descripción breve]

---

### 12. Notas Adicionales

[Cualquier información adicional relevante, observaciones, recomendaciones, etc.]

---

### 13. Aprobación

**Validado por**: [Nombre]  
**Fecha**: [YYYY-MM-DD]  
**Firma/Aprobación**: [Iniciales o "Approved"]

**Revisado por**: [Nombre del supervisor/lead]  
**Fecha de revisión**: [YYYY-MM-DD]  
**Firma/Aprobación**: [Iniciales o "Approved"]

---

## Checklist de Completitud

Antes de marcar la evidencia como completa, verificar:

- [ ] ID del ítem correcto
- [ ] Todos los criterios evaluados
- [ ] Evidencias adjuntas (screenshots/logs/docs)
- [ ] Procedimiento documentado
- [ ] Gaps identificados (si aplica)
- [ ] Plan de mitigación definido (si aplica)
- [ ] Firma del validador
- [ ] Revisión del lead/supervisor

---

**Archivo guardado en**: `evidences/[categoría]/evidence_[id]_[nombre].md`  
**Attachments en**: `evidences/attachments/[id]/`
