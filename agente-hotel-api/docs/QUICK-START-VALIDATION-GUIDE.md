# 🚀 Quick Start: Validación de Ítems (Para Cada Responsable)

**Versión**: 1.0  
**Propósito**: Guía rápida paso-a-paso para validar cada ítem del checklist

---

## 5 Pasos Simples para Validar un Ítem

### Paso 1: Obtener el Ítem Asignado (2 min)

1. Abre el tracking dashboard (Google Sheet compartido)
2. Filtra por tu nombre en la columna "Responsable"
3. Ve el primer ítem con status "PENDING"
4. Copia el ID (ej: 1.1, 2.3, etc.)

---

### Paso 2: Leer los Criterios (3 min)

1. Abre `docs/P020-PRODUCTION-READINESS-CHECKLIST.md`
2. Busca tu ítem por ID
3. Lee:
   - Descripción del ítem
   - Criterios específicos a validar
   - Evidencia requerida

**Ejemplo - Ítem 1.1 (Kubernetes Cluster)**:
```
DESCRIPCIÓN: Kubernetes cluster completamente operacional
CRITERIOS:
  ☐ Todos los nodos en estado "Ready"
  ☐ API server respondiendo
  ☐ DNS funcionando
  ☐ Networking OK
EVIDENCIA: Screenshot de `kubectl get nodes`
```

---

### Paso 3: Ejecutar la Validación (15-45 min)

**Según el tipo de ítem:**

#### A. Validación de Infraestructura
```bash
# Ejemplo: Validar Kubernetes cluster
$ kubectl get nodes
$ kubectl get pods -A
$ kubectl cluster-info

# Capturar screenshot de la salida
```

#### B. Validación de Seguridad
```bash
# Ejemplo: Validar SSL certificates
$ openssl s_client -connect api.hotel.com:443
$ kubectl get secret -A | grep tls
```

#### C. Validación de Base de Datos
```bash
# Ejemplo: Validar backups configurados
$ psql -U admin -d hotel_db -c "SELECT * FROM pg_stat_database;"
$ ls -la /backups/daily/
```

#### D. Validación de Monitoring
```
# Acceder a Grafana dashboards
# Verificar métricas específicas
# Capturar screenshots de gráficos
```

#### E. Validación Manual (Documentación/Procesos)
```
# Leer documento
# Verificar cumplimiento
# Documentar hallazgos
```

---

### Paso 4: Documentar la Evidencia (10 min)

1. **Copia el template**:
   - Abre `docs/EVIDENCE-TEMPLATE.md`
   - Haz una copia: `evidence_[categoría]_[id]_[nombre].md`
   - Guarda en carpeta de evidencias

2. **Completa las secciones principales**:
   ```
   1. ID del Ítem: 1.1
   2. Categoría: Infraestructura
   3. Responsable: Tu nombre
   4. Fecha: [Hoy]
   
   5. Resultado: [ ] PASS ✅  [ ] PARTIAL 🟡  [ ] FAIL ❌
   
   6. Criterios Verificados:
      ☑️ Criterio 1: PASS
      ☑️ Criterio 2: PASS
      ☑️ Criterio 3: FAIL → Gap identificado
   
   7. Evidencias Adjuntas:
      - screenshot_1.1_nodes.png
      - screenshot_1.1_api.png
   
   8. Procedimiento Ejecutado:
      $ kubectl get nodes
      $ kubectl cluster-info
   
   9. Resultado:
      ✅ PASS - Todos los criterios cumplidos
   ```

3. **Adjunta los screenshots/logs**:
   - Guarda en: `evidences/attachments/[id]/`
   - Nomina: `screenshot_[id]_[descripción].png`
   - Incluye timestamp en screenshot si es posible

---

### Paso 5: Actualizar el Dashboard (5 min)

1. Abre el tracking dashboard (Google Sheet)
2. Encuentra tu ítem (búsqueda por ID)
3. Actualiza las columnas:
   - **Status**: PASS / PARTIAL / FAIL
   - **Score**: 10 si PASS, 5-9 si PARTIAL, 0 si FAIL
   - **Evidence Link**: URL a tu archivo de evidencia
   - **Notas**: Cualquier información adicional
   - **Fecha**: Hoy

4. **Si FAIL**: 
   - Reporta inmediatamente en Slack #pre-launch-validations
   - Etiqueta: Engineering Manager + responsable categoría
   - Mensaje: "[BLOCKER] Ítem 1.1 FAIL - [Descripción breve del problema]"

5. **Si PARTIAL**:
   - Documenta el gap específico en la evidencia
   - Nota en dashboard: "Gap: [descripción], Mitigación: [plan]"

---

## 📚 Validación por Categoría

### Categoría 1: Infraestructura (DevOps Lead)

**Ítems 1.1 - 1.20**

**Herramientas necesarias**:
- kubectl
- helm
- docker
- AWS CLI o equivalente

**Tiempo estimado por ítem**: 15-30 min

**Ejemplo rápido**:
```bash
# 1.1: Kubernetes cluster operacional
kubectl get nodes
kubectl get pod -A

# 1.2: Nodos con suficiente recursos
kubectl top nodes

# 1.3: Networking OK
kubectl get networkpolicies -A

# 1.4: Storage provisioner
kubectl get storageclasses
```

---

### Categoría 2: Seguridad (Security Engineer)

**Ítems 2.1 - 2.15**

**Herramientas necesarias**:
- openssl
- nmap
- git-secrets / gitleaks
- kubesec / trivy

**Tiempo estimado por ítem**: 20-45 min

**Ejemplo rápido**:
```bash
# 2.1: SSL/TLS certificados válidos
openssl s_client -connect api.hotel.com:443 -showcerts

# 2.2: Secrets no en git
git log --all --full-history -S "password" --oneline

# 2.3: RBAC configurado
kubectl auth can-i get pods --as=system:serviceaccount:default:myapp

# 2.4: Network policies
kubectl get networkpolicies -A
```

---

### Categoría 3: Base de Datos (DBA/Backend Lead)

**Ítems 3.1 - 3.12**

**Herramientas necesarias**:
- psql
- pg_dump
- pgbackrest o similar

**Tiempo estimado por ítem**: 15-25 min

**Ejemplo rápido**:
```bash
# 3.1: PostgreSQL en estado óptimo
psql -U admin -d hotel_db -c "SELECT * FROM pg_stat_database;"

# 3.2: Backups configurados
pg_dump --verbose hotel_db | wc -l

# 3.3: Replicación OK
psql -c "SELECT * FROM pg_stat_replication;"

# 3.4: Permisos correctos
psql -c "\dp+" 
```

---

### Categoría 4: Monitoring (SRE)

**Ítems 4.1 - 4.18**

**Herramientas necesarias**:
- Browser (para Grafana)
- prometheus-cli
- alertmanager

**Tiempo estimado por ítem**: 10-20 min

**Ejemplo rápido**:
```
# 4.1: Prometheus scrapeando correctamente
→ Abre Prometheus dashboard
→ Verifica "Targets" - todos "UP"
→ Captura screenshot

# 4.2: Grafana dashboards operativos
→ Abre Grafana
→ Verifica dashboard "System Health"
→ Verifica métricas en tiempo real
→ Captura screenshot

# 4.3: Alertas configuradas
→ AlertManager UI
→ Verifica alertas activas/inactivas
→ Captura screenshot
```

---

### Categoría 5: Backup/DR (DevOps Lead)

**Ítems 5.1 - 5.12**

**Herramientas necesarias**:
- Backup scripts
- rsync / S3 CLI
- pg_restore

**Tiempo estimado por ítem**: 20-45 min

**Ejemplo rápido**:
```bash
# 5.1: Backups diarios completados
ls -la /backups/daily/ | grep $(date +%Y-%m-%d)

# 5.2: Últimos 7 days backups existen
ls -la /backups/daily/ | tail -7

# 5.3: Backups replicated a S3
aws s3 ls s3://backups/hotel/daily/ --recursive | tail -5

# 5.4: Restore script funciona
./scripts/restore_backup.sh --dry-run
```

---

## ⚡ Tips Rápidos

### Validación Eficiente

1. **Agrupa ítems relacionados**:
   - No cambies de contexto entre ítems
   - Valida 3-4 ítems seguidos en el mismo servicio

2. **Reutiliza comandos**:
   - Crea un script con todos los comandos de tu categoría
   - Ejecuta de una vez
   - Captura toda la salida

3. **Screenshots efectivos**:
   - Incluye timestamp visible
   - Captura el output completo (scroll si es necesario)
   - Nombra con descripción clara

4. **Notas en evidencia**:
   - Si algo está "mostly OK" → PARTIAL
   - Documenta qué está faltando exactamente
   - Sugiere plan de mitigación

---

## ❌ Si Encuentras un FAIL

### Acción Inmediata (Mismo día)

1. **En el dashboard**: Marca como FAIL
2. **En Slack**: Post en #pre-launch-validations
   ```
   🚨 [BLOCKER] Ítem 2.3 FAIL
   Descripción: SSL certificate expirado
   Impacto: CRÍTICO - API no accesible
   Solución: Renovar certificado ASAP
   Owner: Security Engineer
   ETA: [Cuándo se puede resolver]
   ```

3. **En la evidencia**: Documenta:
   - Qué falta exactamente
   - Impacto de la falta
   - Opción 1: Remediar (acciones, timeline)
   - Opción 2: Workaround (si existe)
   - Opción 3: Aplazar lanzamiento

---

## 🟡 Si Encuentras un PARTIAL

### Acción en el Dashboard

1. Marca como PARTIAL
2. Escribe notas clara: "Gap: [qué falta]"
3. En evidencia: Describe el gap + plan de mitigación
4. Mensajea al lead (no urgente como FAIL)

**Ejemplo**:
```
Status: PARTIAL
Gap: 3 de 5 nodos con CPU >50%
Mitigación: Auto-scaling iniciará si pasa 70%
ETA: OK para lanzamiento con monitoreo cercano
```

---

## ✅ Si Encuentras un PASS

### Acción en el Dashboard

1. Marca como PASS
2. Score: 10
3. En Slack: Post progreso en daily standup

---

## 📊 Tracking tu Progreso

**En el dashboard**:
- Columna "Status": Cuántos PASS / PARTIAL / FAIL tienes hoy
- Columna "Score": Promedio de tus ítems

**Objetivo diario**:
- Día 1: 10-15 ítems
- Día 2: 15-20 ítems
- Día 3-5: 15-20 ítems/día
- Día 6: Compilación de resultados

---

## 🆘 Si Te Atascas

### Opciones de Ayuda

1. **Pregunta en daily standup** (17:00)
   - Describe qué no funciona
   - Pide sugerencias del equipo

2. **Slack #pre-launch-validations**
   - Busca si alguien tuvo el mismo problema
   - Si no, pregunta
   - Tiempo de respuesta esperado: 2 horas

3. **Engineering Manager**
   - Si es bloqueador crítico
   - Si necesitas permiso para modificar algo
   - Contacto directo si el Slack no responde rápido

---

## ⏱️ Timeline de Ejemplo (Un Día)

```
09:00 - 09:30 | Leer ítems asignados (3-4 items)
09:30 - 11:00 | Validar ítems 1, 2, 3
11:00 - 11:15 | Documentar evidencias
11:15 - 11:30 | Actualizar dashboard

13:30 - 14:30 | Validar ítems 4, 5
14:30 - 15:00 | Documentar y dashboard

16:00 - 17:00 | Validar ítem 6 + buffer
17:00 - 17:15 | Daily standup: reportar progreso

Total: 3-4 ítems validados, evidencia completa
```

---

## 🎯 Checklist Antes de Marcar PASS

```
Para cada ítem PASS, verificar:

☑️ Leí la descripción del ítem completamente
☑️ Validé TODOS los criterios
☑️ Capturé evidencia (screenshot/log/documento)
☑️ Creé archivo de evidencia con template
☑️ Adjunté screenshots en carpeta attachments/
☑️ Actualicé dashboard con URL de evidencia
☑️ Escribí notas claras en dashboard
☑️ Si hay gaps → documentados con mitigación
☑️ No hay FAIL items marcados como PASS por error
```

---

## 📞 Contactos Rápidos

- **Para preguntas sobre el proceso**: #pre-launch-validations en Slack
- **Para bloqueos críticos**: Engineering Manager (Slack DM)
- **Para preguntas técnicas de tu área**: Lead de tu categoría
- **Para decisiones sobre Go/No-Go**: CTO (para Day 7)

---

**¡Listo para validar! Cualquier pregunta, pregunta en Slack. A trabajar! 💪**

---

## Apéndice: Comandos Útiles Rápidos

```bash
# Kubernetes
kubectl get nodes
kubectl get pods -A
kubectl describe node [node-name]
kubectl logs -n [namespace] [pod-name]

# PostgreSQL
psql -U admin -d hotel_db -c "SELECT version();"
pg_dump --verbose hotel_db

# Docker
docker ps
docker logs [container]
docker inspect [container]

# Monitoring
curl http://prometheus:9090/api/v1/query?query=up
curl http://grafana:3000/api/health

# System
df -h
du -sh /backups/
top
ps aux | grep [process]
```

---

**Última actualización**: 16 de octubre de 2025  
**Versión**: 1.0
