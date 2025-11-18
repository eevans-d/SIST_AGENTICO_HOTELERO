# ⚡ SUPABASE - GUÍA DE EJECUCIÓN RÁPIDA

**Tiempo total estimado**: 30-40 minutos  
**Prerequisitos**: Cuenta en Supabase y Upstash

---

## 🎯 FASE 1: TÚ CREAS LOS SERVICIOS (15-20 min)

### Paso 1: Crear Proyecto Supabase

1. **Abrir navegador**: https://supabase.com/dashboard
2. **Iniciar sesión** con tu cuenta (GitHub/email)
3. **Click**: "New Project"
4. **Configurar**:
   ```
   Organization: [tu organización personal]
   Name: agente-hotelero-staging
   Database Password: [GENERAR UNA LARGA - min 32 caracteres]
   Region: South America (São Paulo)
   Pricing Plan: Pro ($25/mes)
   ```
5. **Esperar**: 2-3 minutos mientras se crea
6. **Guardar credenciales** (CRÍTICO):

   En el dashboard del proyecto recién creado:
   
   - **PROJECT_REF**: aparece en la URL
     ```
     URL: https://supabase.com/dashboard/project/abcd1234
     PROJECT_REF = abcd1234
     ```
   
   - **DB_PASSWORD**: la que generaste arriba
   
   - **ANON_KEY**: Settings → API → Project API keys → anon public
   
   - **SERVICE_ROLE_KEY**: Settings → API → Project API keys → service_role

   **Copia estos 4 valores a un bloc de notas temporal** (los usaremos en Fase 3)

---

### Paso 2: Crear Redis Upstash

1. **Abrir navegador**: https://upstash.com/
2. **Iniciar sesión** con GitHub
3. **Click**: "Create Database"
4. **Configurar**:
   ```
   Name: agente-hotelero-redis
   Type: Regional (no Global)
   Region: South America (São Paulo)
   Eviction Policy: allkeys-lru
   TLS: Enabled (default)
   ```
5. **Click**: "Create"
6. **Copiar URL Redis**:
   
   En el dashboard de la base de datos:
   - Tab: "Redis Connect"
   - Copiar URL que comienza con `rediss://` (doble s = TLS)
   
   Ejemplo:
   ```
   rediss://default:AaBb...XxYy@sa-east-1-12345.upstash.io:6379
   ```
   
   **Copia esta URL completa al bloc de notas**

---

## ✅ CHECKPOINT 1

Deberías tener en tu bloc de notas:

```
PROJECT_REF: abcd1234
DB_PASSWORD: tu_password_super_segura
ANON_KEY: eyJhbG...
SERVICE_ROLE_KEY: eyJhbG...
REDIS_URL: rediss://default:...@sa-east-1-xxxxx.upstash.io:6379
```

**Si tienes estos 5 valores, continúa a Fase 2** ✅

---

## 🤖 FASE 2: YO PREPARÉ TODO LO AUTOMATIZABLE (COMPLETADO)

✅ Archivo `.env.supabase` creado con placeholders  
✅ Script `scripts/setup_supabase.sql` creado (extensiones + índices + seed SQL)  
✅ Script `scripts/seed_supabase.py` creado (datos iniciales Python)  
✅ Makefile targets validados (`make supabase-validate`, etc.)

**Ahora necesito que pegues las credenciales en `.env.supabase`**

---

## 📝 FASE 3: PEGAS CREDENCIALES Y EJECUTAMOS (10-15 min)

### Paso 3: Editar `.env.supabase`

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Abrir archivo con nano
nano .env.supabase
```

**Reemplazar estos placeholders**:

1. Busca línea con `POSTGRES_URL=postgresql+asyncpg://postgres.[REF]:[DB_PASSWORD]@...`
2. Reemplaza `[REF]` → con tu `PROJECT_REF` (ej: `abcd1234`)
3. Reemplaza `[DB_PASSWORD]` → con tu contraseña de Supabase
4. Busca línea con `REDIS_URL=rediss://...`
5. **BORRA toda la línea** y pega la URL completa de Upstash
6. Busca `SECRET_KEY=GENERA_CON_PYTHON_SECRETS_TOKEN_URLSAFE_32`
7. Genera secret key:
   ```bash
   # En otra terminal (sin cerrar nano):
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # Copiar resultado
   ```
8. Reemplaza con el valor generado

**Guardar**: `Ctrl+O`, Enter, `Ctrl+X`

**Verificar**:
```bash
# Verificar que PROJECT_REF y DB_PASSWORD están reemplazados
grep "POSTGRES_URL" .env.supabase | grep -v "^\#"
# NO debe contener [REF] ni [DB_PASSWORD]

# Verificar que REDIS_URL está completa
grep "REDIS_URL" .env.supabase | grep -v "^\#"
# Debe empezar con rediss:// (doble s)
```

---

### Paso 4: Validar Conexión a Supabase

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-validate
```

**Salida esperada**:
```
🔍 Validating Supabase setup...
             version              
-----------------------------------
 PostgreSQL 15.x on x86_64-pc-linux-gnu...
✅ Supabase connection OK
```

**Si falla**:
- Verifica `POSTGRES_URL` no tiene espacios ni caracteres raros
- Confirma que `PROJECT_REF` y `DB_PASSWORD` son correctos
- Verifica que no tienes firewall bloqueando puerto 6543

---

### Paso 5: Ejecutar SQL Setup en Supabase Dashboard

**IMPORTANTE**: Este paso LO HACES TÚ en el navegador (yo no puedo acceder al dashboard).

1. **Abrir Supabase Dashboard**: https://supabase.com/dashboard
2. **Ir a tu proyecto**: `agente-hotelero-staging`
3. **Click**: SQL Editor (icono de terminal en sidebar)
4. **Click**: "New query"
5. **Abrir archivo SQL local**:
   ```bash
   cat scripts/setup_supabase.sql
   ```
6. **Copiar TODO el contenido** del archivo
7. **Pegar en SQL Editor** de Supabase
8. **Click**: "Run" (o `Ctrl+Enter`)

**IMPORTANTE**: Ejecuta **SOLO LA PARTE 1** (extensiones) ahora. Las PARTES 2 y 3 (índices + seed) las haremos DESPUÉS de las migraciones.

**Salida esperada**:
```
extension_name       | version
---------------------+---------
pg_stat_statements   | 1.10
pgcrypto             | 1.3
pg_trgm              | 1.6
uuid-ossp            | 1.1
```

---

### Paso 6: Ejecutar Migraciones Alembic

**Ahora SÍ puedo ejecutar comandos** (ya tienes credenciales configuradas):

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-migrate
```

**Salida esperada**:
```
🚀 Running Alembic migrations on Supabase...
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_add_tenants, multi-tenancy
INFO  [alembic.runtime.migration] Running upgrade 0002_add_tenants -> 0003_add_lock_audit, lock audit
INFO  [alembic.runtime.migration] Running upgrade 0003_add_lock_audit -> 0004_add_dlq, dead letter queue
✅ Migrations completed
```

---

### Paso 7: Ejecutar PARTE 2 del SQL (Índices)

**De nuevo en Supabase SQL Editor**:

1. **Ir a SQL Editor** (dashboard)
2. **Copiar SOLO LA PARTE 2** de `scripts/setup_supabase.sql` (líneas ~40-80)
3. **Pegar y Run**

**Salida esperada**: Lista de 8+ índices creados.

---

### Paso 8: Poblar Datos Iniciales (Seed)

**Opción A - SQL Manual** (en Supabase SQL Editor):

Copiar y ejecutar PARTE 3 de `scripts/setup_supabase.sql`:
```sql
INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
VALUES ('default', 'Default Tenant', 'active', NOW(), NOW())
ON CONFLICT (tenant_id) DO NOTHING;
```

**Opción B - Script Python** (yo lo ejecuto):

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Cargar variables
export $(cat .env.supabase | grep -v '^#' | xargs)

# Ejecutar seed
poetry run python scripts/seed_supabase.py
```

**Salida esperada**:
```
🌱 SUPABASE SEED SCRIPT
✅ Conexión exitosa
📦 Creando tenant default...
   ✅ Tenant creado: ID=1, tenant_id=default, name=Default Tenant
✅ SEED COMPLETADO
```

---

### Paso 9: Verificación Final

```bash
make supabase-quick-check
```

**Salida esperada**:
```
📊 Supabase quick check...
           List of relations
 Schema |          Name              | Type  |  Owner   
--------+----------------------------+-------+----------
 public | alembic_version            | table | postgres
 public | dlq_permanent_failures     | table | postgres
 public | lock_audit                 | table | postgres
 public | tenant_user_identifiers    | table | postgres
 public | tenants                    | table | postgres
 public | users                      | table | postgres

        extname        
-----------------------
 pg_stat_statements
 pgcrypto
 pg_trgm
 uuid-ossp

✅ Quick check complete
```

---

## ✅ CHECKLIST FINAL

- [ ] Proyecto Supabase creado (Plan Pro, São Paulo)
- [ ] Redis Upstash creado (regional, São Paulo)
- [ ] Credenciales guardadas (PROJECT_REF, DB_PASSWORD, REDIS_URL, etc.)
- [ ] `.env.supabase` editado sin placeholders
- [ ] `make supabase-validate` → conexión OK
- [ ] Extensiones PostgreSQL creadas (PARTE 1 SQL)
- [ ] `make supabase-migrate` → migraciones OK
- [ ] Índices creados (PARTE 2 SQL)
- [ ] Datos iniciales creados (PARTE 3 SQL o script Python)
- [ ] `make supabase-quick-check` → tablas + extensiones visibles

---

## 🎉 ¡LISTO!

Ahora puedes usar Supabase. Para arrancar la app con Supabase:

```bash
export $(cat .env.supabase | grep -v '^#' | xargs)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Deberías ver en logs:
```
INFO [app.core.database] Supabase detected: adjusting pool to 2/2 (from default 10/10)
```

---

## 📞 PRÓXIMOS PASOS

¿Quieres que ejecute alguno de los comandos automáticos ahora? Puedo ejecutar:
- `make supabase-validate` (si ya pegaste credenciales)
- `make supabase-migrate` (si validación pasó)
- `poetry run python scripts/seed_supabase.py` (si migraciones pasaron)

**Dime qué paso ya completaste y continúo con los comandos automáticos.**
