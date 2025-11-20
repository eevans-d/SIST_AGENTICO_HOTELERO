# Backup & Restore Procedures

**Sistema**: PostgreSQL en Neon  
**RPO (Recovery Point Objective)**: 6 horas (snapshots automáticos)  
**RTO (Recovery Time Objective)**: 15 minutos (PITR via branch)  
**Backup Retention**: 7 días automáticos (Neon PITR) + manuales indefinidos

---

## 1. Estrategia de Backups

### 1.1 Backups Automáticos (Neon)

Neon proporciona automáticamente:
- **Snapshots diarios**: Retenidos por 7 días
- **PITR (Point-in-Time Recovery)**: Último 7 días de logs (granularidad: ~segundos)
- **Branching**: Crea branches desde cualquier punto en tiempo

**¿Cuándo usar?**
- Pérdida accidental de datos: PITR (primeras 7 días)
- Corrupción gradual: Snapshot más antiguo disponible (hasta 7 días atrás)
- Desarrollo/testing: Branch de snapshot, sin afectar producción

### 1.2 Backups Manuales (pg_dump)

Script: `scripts/db-backup-restore.sh backup`

**Ventajas:**
- Almacenamiento indefinido (tuyo control)
- Documentación externa (gitops, S3, etc.)
- Portabilidad (restore en otra instancia)

**Desventajas:**
- Toma 5-15 min según tamaño DB
- Requiere `pg_dump` en cliente
- Consume ancho de banda

**Uso:**
```bash
# Backup manual
./scripts/db-backup-restore.sh backup
# Output: ./.backups/backup_manual_20251025_143000.sql

# Listar backups
./scripts/db-backup-restore.sh list
```

---

## 2. PITR (Point-in-Time Recovery)

**Escenario**: Querys destructivas ejecutadas a las 14:30. Necesitas volver a 14:29:45.

### 2.1 Procedimiento via UI (5-10 min)

1. **Accede Neon Console**: https://console.neon.tech/
2. **Proyecto**: "agente-hotel-prod"
3. **Branches** → Click "Create branch"
4. **"Create from backup"** → Selecciona **Timestamp**: 2025-10-25 14:29:45 UTC
5. **Nombre branch**: `recovery-2025-10-25-14-29-45`
6. **Espera**: ~30 segundos para que Neon cree branch con datos históricos
7. **Copia CONNECTION STRING**: del nuevo branch
8. **Valida** datos en branch (lectura)
9. **Decide**: ¿Promote a main o descarta?

### 2.2 Procedimiento via CLI (2-3 min)

```bash
# Prerequisito: neon CLI instalada
# npm install -g @neondatabase/cli
# neon auth

# 1. Crear branch de PITR
neon branch create recovery-pitr-20251025 \
  --project-id agente-hotel-prod \
  --from-timestamp 2025-10-25T14:29:45Z

# 2. Obtener connection string
RECOVERY_URL=$(neon connection-string recovery-pitr-20251025 \
  --project-id agente-hotel-prod)

# 3. Validar datos
psql "$RECOVERY_URL" -c "SELECT * FROM guests LIMIT 5;"

# 4. Si OK, promote a main (CUIDADO: REEMPLAZA MAIN)
neon branch promote recovery-pitr-20251025 \
  --project-id agente-hotel-prod

# 5. Redeploy app
(Comando de deploy)
```

### 2.3 Después de Promote: Validación

```bash
# 1. Espera 30s para que Neon replique
sleep 30

# 2. Verifica health
curl -f <APP_URL>/health/ready
# Output: {"status": "ready", "services": {"postgres": "ok", ...}}

# 3. Verifica datos via API
curl <APP_URL>/api/guests -H "Authorization: Bearer ..."

# 4. Valida logs (último 5 min)
(Comando de logs) | grep ERROR
```

---

## 3. Branch-Based Restore

**Escenario**: Corrupción de tabla "reservations". Quieres restore sin afectar otros datos.

### 3.1 Crear Branch de Backup (UI)

1. **Neon Console** → Branches
2. **"Create branch"** → **Selecciona date**: "2025-10-23 (3 days ago)"
3. **Nombre**: `restore-reservations-20251023`
4. **Obtén CONNECTION STRING**
5. **Restore selectivamente**: Dumpa tabla específica, restaura en main
   ```bash
   # Conecta al branch "limpio"
   psql "$RECOVERY_URL" -c "COPY reservations TO STDOUT;" > clean_reservations.sql
   
   # Conecta a main y restaura
   psql "$DATABASE_URL" < clean_reservations.sql
   ```

### 3.2 Promote Branch a Main

Si todo el branch es válido:

```bash
# CLI: Promote branch a main
neon branch promote restore-reservations-20251023 \
  --project-id agente-hotel-prod

# Redeploy app para sincronizar
(Comando de deploy)
```

---

## 4. Backups Manuales (pg_dump)

### 4.1 Crear Backup

```bash
# Script automatizado
./scripts/db-backup-restore.sh backup
# → ./.backups/backup_manual_20251025_143000.sql (~50MB si DB normal)

# O manualmente
export DATABASE_URL="postgresql://..."
pg_dump -Fc "$DATABASE_URL" > backup_20251025.dump

# Comprimir para almacenamiento
gzip backup_20251025.dump  # → backup_20251025.dump.gz (~10MB)
```

### 4.2 Restaurar desde Backup Manual

```bash
# En local (test)
createdb hotel_test
pg_restore -d hotel_test backup_20251025.dump

# En producción (CUIDADO)
pg_restore -d hotel "$DATABASE_URL" backup_20251025.dump

# O crear connection string nueva
createdb -h $PG_HOST -U $PG_USER hotel_restored
pg_restore -d hotel_restored backup_20251025.dump
```

### 4.3 Almacenar Backups (Externos)

```bash
# Opción 1: AWS S3
aws s3 cp backup_20251025.dump.gz s3://backups-agente/backups/

# Opción 2: Google Cloud Storage
gsutil cp backup_20251025.dump.gz gs://backups-agente/backups/

# Opción 3: Git (si pequeño <100MB)
git-lfs install
git add backups/backup_20251025.dump.gz
git commit -m "backup: 2025-10-25"
git push

# Opción 4: Local (en .gitignore)
# .gitignore: .backups/
```

---

## 5. Automatización (Scheduled Backups)

### 5.1 GitHub Actions (Diario 02:00 UTC)

Crear `.github/workflows/backup-database.yml`:

```yaml
name: Database Backup

on:
  schedule:
    - cron: '0 2 * * *'  # Cada día 02:00 UTC
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install PostgreSQL Client
        run: sudo apt-get install -y postgresql-client

      - name: Backup Database
        run: |
          BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
          pg_dump -Fc "${{ secrets.DATABASE_URL }}" > "$BACKUP_FILE"
          echo "BACKUP_FILE=$BACKUP_FILE" >> $GITHUB_ENV

      - name: Upload to S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          aws s3 cp "$BACKUP_FILE" s3://backups-agente/backups/

      - name: Cleanup old backups (>30 days)
        run: |
          aws s3 rm s3://backups-agente/backups/ --recursive \
            --exclude "*" --include "backup_*" \
            --older-than 30
```

### 5.2 Validar Backup Integrity

```bash
#!/bin/bash
# Después de cada backup, verificar que sea válido

BACKUP_FILE="$1"
TEMP_DB="backup_validation_test"

# 1. Crear DB temporal
createdb "$TEMP_DB"

# 2. Restaurar backup en DB temporal
pg_restore -d "$TEMP_DB" "$BACKUP_FILE" 2>&1 | \
  grep -E 'ERROR|CRITICAL' && exit 1

# 3. Validar tablas principales existen
psql "$TEMP_DB" -c "
  SELECT COUNT(*) FROM information_schema.tables 
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
"

# 4. Cleanup
dropdb "$TEMP_DB"

echo "✅ Backup válido: $BACKUP_FILE"
```

---

## 6. Incident Response: Pérdida de Datos

### 6.1 Detección

**Síntomas:**
- Falta datos en tabla critical (guests, reservations, etc.)
- Aplicación devuelve 500 al consultar tabla
- Logs: `relation "xxx" does not exist`

**Validación rápida:**
```bash
# Conecta a DB
psql "$DATABASE_URL"

# Cuenta filas esperadas
SELECT COUNT(*) FROM reservations;  -- ¿Debería ser >1000?

# Valida integridad
PRAGMA integrity_check;  -- Si es SQLite
-- O para PostgreSQL:
ANALYZE;
```

### 6.2 Opción 1: PITR (Recomendado si <7 días atrás)

**Paso 1**: Crear branch de PITR a antes de la corrupción
```bash
# Estima: Corrupción ocurrió hace 2 horas (12:30)
# Restore a 11:00 para estar seguro
neon branch create recovery-pitr-20251025 \
  --project-id agente-hotel-prod \
  --from-timestamp 2025-10-25T11:00:00Z
```

**Paso 2**: Validar datos en branch

**Paso 3**: Si OK, Promote a main y redeploy

**RTO**: 10-15 minutos (incluye validación)

### 6.3 Opción 2: Backup Manual (Si >7 días atrás)

**Paso 1**: Ubicar backup más reciente válido
```bash
ls -lh .backups/backup_*.sql | tail -5
```

**Paso 2**: Crear DB nueva, restaurar
```bash
pg_restore -Fc -d hotel_restored backup_20251020.dump
```

**Paso 3**: Validar datos

**Paso 4**: Cambiar CONNECTION STRING en la plataforma
```bash
(Comando para actualizar variable de entorno DATABASE_URL)
(Comando de deploy)
```

**RTO**: 20-30 minutos (incluye validación + deploy)

### 6.4 Notificación & Post-Mortem

```bash
# 1. Notifica stakeholders
# "Pérdida de datos detectada. Iniciando recovery. ETA 15 min"

# 2. Valida post-recovery
curl -f https://agente-hotel-api.fly.dev/health/ready

# 3. Crea issue post-mortem
gh issue create \
  --title "Post-Mortem: Data Loss 2025-10-25" \
  --body "
  ## Timeline
  - 12:30: Corrupción detectada
  - 12:35: PITR iniciado
  - 12:48: Recovery completado
  
  ## Causa Raíz
  [Investigar]
  
  ## Acciones Preventivas
  [Listar]
  "
```

---

## 7. Testing: Restore Drills

**Cadencia**: Mensual (primer lunes 10:00 UTC)

### 7.1 Test PITR

```bash
# 1. Crea branch de PITR actual (1 hora atrás)
neon branch create drill-pitr-$(date +%Y%m%d) \
  --project-id agente-hotel-prod \
  --from-timestamp $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)

# 2. Valida datos (lectura)
psql $(neon connection-string drill-pitr-$(date +%Y%m%d)) \
  -c "SELECT COUNT(*) FROM reservations;"

# 3. Documenta resultado
echo "✅ PITR Test $(date): SUCCESS" >> restore_drills.log

# 4. Cleanup
neon branch delete drill-pitr-$(date +%Y%m%d) --project-id agente-hotel-prod
```

### 7.2 Test Backup Manual

```bash
# 1. Extrae backup más reciente
LATEST_BACKUP=$(ls -t .backups/*.sql | head -1)

# 2. Restaura en DB temporal
createdb test_restore
pg_restore -d test_restore "$LATEST_BACKUP"

# 3. Valida
psql test_restore -c "SELECT * FROM guests LIMIT 1;"

# 4. Cleanup
dropdb test_restore

echo "✅ Manual Restore Test $(date): SUCCESS" >> restore_drills.log
```

---

## 8. Monitoring & Alertas

### 8.1 Métricas Prometheus

```yaml
# En prometheus.yml
- job_name: 'neon_backups'
  static_configs:
    - targets: ['localhost:9100']
  metrics:
    - neon_backup_age_hours
    - neon_pitr_available_days
```

### 8.2 Alertas

```yaml
# AlertManager configuration
- alert: BackupOlderThan24Hours
  expr: neon_backup_age_hours > 24
  annotations:
    summary: "Backup is {{ $value }} hours old"

- alert: PITRWindowClosing
  expr: neon_pitr_available_days < 1
  annotations:
    summary: "PITR window expires in {{ $value }} days"
```

### 8.3 Health Check

```bash
# Endpoint: GET /health/backup
# Response:
{
  "status": "healthy",
  "last_backup": "2025-10-25T02:00:00Z",
  "backup_age_hours": 14,
  "pitr_available_days": 5,
  "neon_branch_count": 1
}
```

---

## 9. Checklists

### 9.1 Configuración Inicial

- [ ] Neon project creado: "agente-hotel-prod"
- [ ] PITR habilitado (automático en Neon, verificar en settings)
- [ ] pg_dump instalado localmente: `pg_dump --version`
- [ ] AWS CLI configurado (si usas S3): `aws s3 ls`
- [ ] `.backups/` en `.gitignore`
- [ ] GitHub Actions workflow agregado: `.github/workflows/backup-database.yml`
- [ ] Script de backup: `scripts/db-backup-restore.sh` ejecutable (`chmod +x`)
- [ ] Documentación linkeada en README.md

### 9.2 Validación Pre-Producción

- [ ] PITR restore test exitoso (1 mes atrás)
- [ ] Backup manual restore test exitoso
- [ ] Health check endpoint responde: `/health/backup`
- [ ] Alertas configuradas en Alertmanager
- [ ] RTO/RPO validados (10-15 min PITR, 6h snapshots)
- [ ] Post-mortem runbook disponible: `docs/operations/incident-db-down.md`

### 9.3 Validación Post-Producción (Mensual)

- [ ] PITR test ejecutado (drill-pitr-YYYYMMDD)
- [ ] Backup manual test ejecutado
- [ ] Documentar resultados en `restore_drills.log`
- [ ] Revisar logs de alerts (si las hay)
- [ ] Actualizar runbook si aprendizajes

---

## 10. Referencias

**Neon Docs:**
- PITR: https://neon.tech/docs/manage/point-in-time-recovery
- Branching: https://neon.tech/docs/manage/branches
- Connection Strings: https://neon.tech/docs/connect/connection-details

**PostgreSQL Docs:**
- pg_dump: https://www.postgresql.org/docs/14/app-pgdump.html
- pg_restore: https://www.postgresql.org/docs/14/app-pgrestore.html
- Backup Strategies: https://www.postgresql.org/docs/14/backup.html

**Cloud Providers:**
- AWS S3: https://docs.aws.amazon.com/s3/
- Google Cloud Storage: https://cloud.google.com/storage/docs
- Azure Backup: https://azure.microsoft.com/en-us/services/backup/

---

**Last Updated**: 2025-10-25  
**Maintained By**: Backend Ops  
**Review Frequency**: Monthly
