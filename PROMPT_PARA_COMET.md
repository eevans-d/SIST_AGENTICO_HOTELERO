# 🎯 Prompt para COMET (Browser Assistant)

Contexto breve:
- Aplicación hotelera con IA en Fly.io (gru, región São Paulo).
- Objetivo: activar auto-deploy CI/CD y provisionar DB/Redis gestionados.
- Estado: Workflows listos en GitHub, solo faltan credenciales y servicios externos.

---

## 🔧 Tareas a ejecutar EN ORDEN (paso a paso)

### PASO 1: Obtener token Fly (ejecución LOCAL en terminal, NO en Comet)
```bash
flyctl auth login
flyctl auth token
```
Guarda el token (lo usarás en PASO 2).

---

### PASO 2: Agregar FLY_API_TOKEN en GitHub
1. Abre: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/settings/secrets/actions
2. Click "New repository secret"
3. Name: `FLY_API_TOKEN`
4. Value: pega el token del PASO 1
5. Click "Add secret"

---

### PASO 3: Provisionar Postgres (Neon)
1. Abre: https://console.neon.tech/
2. Click "Create project" → Nombre: `agente-hotel-prod`
3. Espera creación; luego crear DB `hotel` (o usar default)
4. Ve a "Connection details" y copia la URL completa (debe terminar con `?sslmode=require`)
5. Guarda: esta URL es tu `DATABASE_URL`

**Ejemplo (no real)**:
```
postgresql://user:pass@ep-xyz.us-east-1.aws.neon.tech:5432/hotel?sslmode=require
```

---

### PASO 4: Provisionar Redis (Upstash)
1. Abre: https://console.upstash.com/
2. Click "Create database" → Nombre: `agente-hotel-prod`
3. Región: Brasil si existe, sino US-East.
4. Copia la URL Redis (preferible "rediss://" con TLS)
5. Guarda: esta URL es tu `REDIS_URL`

**Ejemplo (no real)**:
```
rediss://default:token@us1-host.upstash.io:port
```

---

### PASO 5: Agregar DATABASE_URL y REDIS_URL en GitHub Secrets
1. Abre: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/settings/secrets/actions
2. Click "New repository secret"
   - Name: `DATABASE_URL`
   - Value: URL de Neon (PASO 3)
   - Add secret
3. Click "New repository secret" (otra vez)
   - Name: `REDIS_URL`
   - Value: URL de Upstash (PASO 4)
   - Add secret

---

### PASO 6: Disparar deploy automático
1. Abre: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO/actions
2. Selecciona workflow "Deploy to Fly.io"
3. Click "Run workflow" (workflow_dispatch)
4. Selecciona rama "main"
5. Click "Run workflow"
6. Espera a que termine (5-10 minutos)
7. Verifica que todos los steps estén en ✅:
   - ✅ Checkout
   - ✅ Setup Flyctl
   - ✅ Set Fly Secrets (DATABASE_URL)
   - ✅ Set Fly Secrets (REDIS_URL)
   - ✅ Deploy
   - ✅ Smoke health check

---

### PASO 7: Verificar salud en producción
Abre estos enlaces y confirma que devuelven `200 OK`:
1. https://agente-hotel-api.fly.dev/health/live
2. https://agente-hotel-api.fly.dev/health/ready
3. https://agente-hotel-api.fly.dev/ (debe mostrar JSON con "status": "active")

---

### PASO 8 (Opcional): Agregar dominio propio
1. Abre: https://fly.io/apps/agente-hotel-api → Certificates
2. Add certificate → ingresa tu dominio (ej. api.hotel.com)
3. Sigue instrucciones DNS
4. Espera emisión (~10 min)
5. Verifica HTTPS en tu dominio

---

## ✅ Checklist final

Marca cada paso conforme lo completes:

- [ ] PASO 1: Token Fly obtenido
- [ ] PASO 2: FLY_API_TOKEN en GitHub ✓
- [ ] PASO 3: Postgres (Neon) creado ✓
- [ ] PASO 4: Redis (Upstash) creado ✓
- [ ] PASO 5: DATABASE_URL y REDIS_URL en GitHub Secrets ✓
- [ ] PASO 6: Deploy ejecutado sin errores ✓
- [ ] PASO 7: /health/live y /health/ready responden 200 ✓
- [ ] PASO 8 (opcional): Dominio y TLS configurados ✓

---

## 🚨 Si algo falla

1. Ve a GitHub Actions → workflow fallido → abre los logs
2. Busca el paso que falló (ej. "Set Fly Secrets")
3. Revisa el error (suele ser: URL mal formada, secreto no existe, credenciales inválidas)
4. Corrige y reintenta PASO 6 (Run workflow)

**Errores comunes**:
- `sslmode=require` faltante en DATABASE_URL → añádelo
- `rediss://` (nota las 2 'ss') faltante en REDIS_URL → cambia a rediss
- Secret no encontrado → verifica que el nombre sea exacto (mayúsculas/minúsculas)

---

**Fin del prompt para Comet.**
