# PROMPT PARA COMET - Crear Usuario Admin en Supabase

## CONTEXTO
Acabamos de completar la migración de autenticación a Supabase. El sistema ya no tiene usuarios mock y necesita un usuario admin inicial para poder autenticarse.

## OBJETIVO
Crear el usuario admin inicial en la base de datos Supabase usando el SQL Editor.

## CREDENCIALES NECESARIAS
- **Supabase Dashboard**: https://supabase.com/dashboard
- **Proyecto**: agente-hotelero (o el nombre que hayas configurado)
- Las credenciales de login están en tu gestor de contraseñas o en las variables de entorno

## INSTRUCCIONES PASO A PASO

### Paso 1: Acceder a Supabase Dashboard
1. Navega a: https://supabase.com/dashboard
2. Inicia sesión con tus credenciales
3. Selecciona el proyecto "agente-hotelero" (o el nombre correspondiente)

### Paso 2: Abrir SQL Editor
1. En el menú lateral izquierdo, busca y haz clic en "SQL Editor"
2. Haz clic en "New query" o "+ New query"

### Paso 3: Ejecutar SQL para Crear Admin
Copia y pega exactamente este SQL en el editor:

```sql
-- Crear usuario admin inicial
INSERT INTO users (
    id, 
    username, 
    email, 
    hashed_password, 
    role, 
    full_name,
    is_active, 
    is_superuser, 
    is_verified,
    mfa_enabled, 
    mfa_secret,
    failed_login_attempts,
    last_login,
    account_locked_until,
    tenant_id,
    password_last_changed, 
    password_must_change,
    created_at, 
    updated_at
) VALUES (
    gen_random_uuid()::text,
    'admin',
    'admin@hotelagenteia.com',
    '$2b$12$KIXxKv7W8YvN8ZhMqB.HNO6jb1gQZxZqZ5vYx9kJqF7KXmNxL6hC2',
    'admin',
    'System Administrator',
    true,
    true,
    true,
    false,
    NULL,
    0,
    NULL,
    NULL,
    NULL,
    NOW(),
    false,
    NOW(),
    NOW()
)
ON CONFLICT (username) DO NOTHING;

-- Verificar que el usuario fue creado
SELECT 
    id, 
    username, 
    email, 
    role, 
    is_active, 
    is_superuser,
    created_at
FROM users 
WHERE username = 'admin';
```

### Paso 4: Ejecutar la Query
1. Haz clic en el botón "Run" o presiona `Ctrl+Enter` (Windows/Linux) o `Cmd+Enter` (Mac)
2. Espera a que la query se ejecute

### Paso 5: Verificar Resultado
Deberías ver dos resultados:

**Resultado 1 (INSERT)**: 
- Mensaje: "Success. 1 rows affected" o similar
- Esto confirma que el usuario fue creado

**Resultado 2 (SELECT)**:
- Una tabla con los datos del usuario admin
- Verifica que:
  - `username` = 'admin'
  - `email` = 'admin@hotelagenteia.com'
  - `role` = 'admin'
  - `is_active` = true
  - `is_superuser` = true
  - `created_at` tiene una fecha/hora reciente

### Paso 6: Guardar Credenciales
**IMPORTANTE**: Anota estas credenciales en un lugar seguro:
- **Username**: `admin`
- **Password**: `admin123!`
- **Email**: `admin@hotelagenteia.com`

⚠️ **NOTA DE SEGURIDAD**: Cambia esta contraseña inmediatamente después del primer login en producción.

## VERIFICACIÓN ADICIONAL (OPCIONAL)

Si quieres verificar que todas las tablas se crearon correctamente, ejecuta:

```sql
-- Verificar estructura de tablas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('users', 'password_history', 'user_sessions', 'tenants')
ORDER BY table_name;
```

Deberías ver al menos:
- `password_history`
- `tenants`
- `user_sessions`
- `users`

## POSIBLES ERRORES Y SOLUCIONES

### Error: "relation 'users' does not exist"
**Causa**: La migración de Alembic no se ejecutó.
**Solución**: 
1. Vuelve a la terminal
2. Ejecuta: `cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api`
3. Ejecuta: `source .venv/bin/activate`
4. Ejecuta: `alembic upgrade head`
5. Vuelve a intentar el INSERT

### Error: "duplicate key value violates unique constraint"
**Causa**: El usuario 'admin' ya existe.
**Solución**: 
- Esto es normal si ya ejecutaste el SQL antes
- El `ON CONFLICT DO NOTHING` previene errores
- Ejecuta solo la parte del SELECT para verificar que existe:
```sql
SELECT id, username, email, role 
FROM users 
WHERE username = 'admin';
```

### Error: "column 'X' does not exist"
**Causa**: La estructura de la tabla no coincide con el SQL.
**Solución**:
1. Verifica la estructura actual:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;
```
2. Compara con los campos del INSERT
3. Ajusta el INSERT según la estructura real

## SIGUIENTE PASO DESPUÉS DE CREAR EL ADMIN

Una vez creado el usuario admin, el siguiente paso es probar el login:

```bash
# En tu terminal local
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123!"}'
```

**Respuesta esperada**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

## INFORMACIÓN DE CONTACTO Y SOPORTE

Si encuentras algún problema:
1. Toma screenshot del error en Supabase
2. Copia el mensaje de error completo
3. Verifica que estás en el proyecto correcto de Supabase
4. Verifica que la conexión a la base de datos está activa

## RESUMEN DE ACCIONES

✅ **Completar**:
1. [ ] Acceder a Supabase Dashboard
2. [ ] Abrir SQL Editor
3. [ ] Ejecutar SQL de creación de admin
4. [ ] Verificar que el usuario fue creado
5. [ ] Guardar credenciales de forma segura
6. [ ] (Opcional) Verificar estructura de tablas

✅ **Resultado esperado**:
- Usuario 'admin' creado en la tabla `users`
- Credenciales: admin / admin123!
- Listo para hacer login en la API

---

**Fecha de creación**: 2025-11-24
**Proyecto**: SIST_AGENTICO_HOTELERO
**Fase**: Post-Migración Supabase
**Prioridad**: 🔴 CRÍTICA - Primer paso necesario para usar el sistema
