# PLAN DE CI/CD, MONITOREO Y BACKUPS PARA "SIST_AGENTICO_HOTELERO" (v2.0 - Revisado)

**Versión:** 2.0
**Fecha:** 2025-11-14
**Objetivo:** Establecer prácticas operativas robustas y seguras para el despliegue continuo, monitoreo y recuperación del proyecto.

---

## FASE 5.1: AUTOMATIZACIÓN DE DESPLIEGUES (CI/CD)

**Objetivo:** Configurar un flujo de trabajo con GitHub Actions para desplegar de forma segura los cambios en la base de datos (migraciones) y las Edge Functions.

### 1. Prerrequisitos
1.  **Repositorio en GitHub.**
2.  **Supabase CLI instalada y vinculada al proyecto.**
3.  **Secretos en GitHub** (`Settings` > `Secrets and variables` > `Actions`):
    *   `SUPABASE_ACCESS_TOKEN`: Tu token de acceso personal.
    *   `SUPABASE_DB_PASSWORD`: La contraseña de la base de datos.
    *   `PROJECT_ID`: El ID de tu proyecto (`ofbsjfmnladfzbjmcxhx`).

### 2. Flujo de Trabajo con Migraciones (Práctica Recomendada)

El uso de `supabase migration up` es más seguro que `db push` porque aplica un conjunto de cambios versionados, evitando acciones destructivas no intencionadas.

**Proceso de Desarrollo Local:**
1.  Realiza cambios en tu base de datos local (o a través del panel de Supabase).
2.  Ejecuta `supabase db diff -f nombre_de_la_migracion` para crear un nuevo archivo de migración en `supabase/migrations`.
3.  Haz `commit` de este nuevo archivo de migración a tu repositorio.

### 3. Código del Flujo de Trabajo (`deploy.yml`)

Este es el contenido actualizado para el archivo `.github/workflows/deploy.yml`.

```yaml
# File: .github/workflows/deploy.yml (VERSIÓN MEJORADA)

name: Deploy to Supabase

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1
        with:
          version: latest

      - name: Apply Database Migrations
        # Este comando aplica las migraciones pendientes desde la carpeta supabase/migrations.
        # Es la forma segura y versionada de actualizar la base de datos en producción.
        run: supabase migration up --project-ref ${{ secrets.PROJECT_ID }}
        env:
          # La contraseña es necesaria para ejecutar las migraciones
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}

      - name: Deploy Edge Functions
        run: supabase functions deploy --project-ref ${{ secrets.PROJECT_ID }} --no-verify-jwt
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
```

---

## FASE 5.2: MONITOREO Y ALERTAS

*   **Métricas de API:** Revisa la sección **"Reports"** para supervisar el tráfico y detectar errores.
*   **Logs de Funciones:** Encuéntralos en **"Edge Functions"** > (tu función) > **"Logs"**.
*   **Rendimiento de la Base de Datos:** Usa **"Database"** > **"Query Performance"** para identificar y optimizar consultas lentas.
*   **Alertas Avanzadas:** Configura **"Log Drains"** en los ajustes del proyecto para enviar logs a servicios externos y crear alertas personalizadas.

---

## FASE 5.3: BACKUPS Y RECUPERACIÓN

*   **Backups Automáticos:** Disponibles en los planes de pago de Supabase para recuperación a un punto en el tiempo (PITR).
*   **Backups Manuales (Plan Gratuito):**
    *   **Desde el Panel:** Ve a **"Database"** > **"Backups"** para generar un backup completo.
    *   **Desde la CLI (Recomendado para automatizar):** Usa `pg_dump` en un script o cron job.
    ```bash
    # Comando para crear un backup local de la base de datos remota
    pg_dump -h "aws-0-us-east-1.pooler.supabase.com" -p 6543 -U "postgres.[PROJECT_ID]" -F "c" -b -v -f "backup_$(date +%Y%m%d).sql" "postgres"
    ```
    *   Recuerda reemplazar `[PROJECT_ID]` y proporcionar la contraseña de la base de datos.