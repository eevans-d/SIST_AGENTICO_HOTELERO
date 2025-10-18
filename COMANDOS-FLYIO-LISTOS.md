# 🚀 COMANDOS COPY-PASTE PARA FLY.IO - LISTOS PARA USAR

**Tus secretos ya están generados y listos**  
**Fecha**: 2025-10-18  
**⚠️ Este documento contiene secretos - NO compartir públicamente**

---

## ⚡ OPCIÓN RÁPIDA - 5 COMANDOS

Copia y pega estos comandos **en orden**:

### 1. Autenticar en Fly.io
```bash
flyctl auth login
```

### 2. Launch app (interactivo)
```bash
flyctl launch --no-deploy
```
- Nombre sugerido: `agente-hotel`
- Región: `mia` (Miami)
- PostgreSQL: **NO** (lo crearemos en paso 3)
- Redis: **NO** (opcional después)

### 3. Crear PostgreSQL y attachar
```bash
flyctl postgres create --name agente-hotel-db --region mia
flyctl postgres attach --app agente-hotel agente-hotel-db
```

### 4. Setear TODOS los secretos críticos
```bash
flyctl secrets set \
  SECRET_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  JWT_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  JWT_REFRESH_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  ENCRYPTION_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c \
  WHATSAPP_VERIFY_TOKEN=45428a63a31eab2be9643bc5d813ece2 \
  SMTP_PASSWORD=BIFB4mEwpvPJqPkea/xMlXxvmTsrr3dqwfZ2V5pL1Po= \
  REDIS_PASSWORD=KZg82ONKfwE6mIsXk8jkDhnxOQEOhxaSyxyLPnv6d/w= \
  GRAFANA_ADMIN_PASSWORD=DcDYhhUf6fwMTK91hbERCxD+ujMqYaX4OpN60wfkE5U=
```

### 5. Deploy
```bash
flyctl deploy --verbose
```

---

## 📋 SECRETOS EXTERNOS (Reemplazar con tus valores)

Cuando tengas tus credenciales externas (WhatsApp, Gmail, OpenAI), ejecuta:

### WhatsApp (Meta Cloud API)
```bash
flyctl secrets set \
  WHATSAPP_API_KEY=TU_META_API_KEY_AQUI \
  WHATSAPP_BUSINESS_ACCOUNT_ID=TU_BUSINESS_ID_AQUI \
  WHATSAPP_PHONE_ID=TU_PHONE_ID_AQUI \
  WHATSAPP_PHONE_NUMBER=TU_NUMERO_AQUI
```

**Dónde obtener:**
- Ve a: https://developers.facebook.com/apps
- Tu App → WhatsApp → API Setup
- Copia: Phone Number ID, WhatsApp Business Account ID
- Copia: Temporary Access Token (o genera Permanent token)

### Gmail (OAuth)
```bash
flyctl secrets set \
  GMAIL_CLIENT_ID=TU_GMAIL_CLIENT_ID_AQUI \
  GMAIL_CLIENT_SECRET=TU_GMAIL_CLIENT_SECRET_AQUI \
  SMTP_USER=tu_email@gmail.com
```

**Dónde obtener:**
- Ve a: https://console.cloud.google.com/apis/credentials
- Crear credenciales → OAuth 2.0 Client ID
- Tipo: Web application
- Redirect URI: https://agente-hotel.fly.dev/auth/gmail/callback

### OpenAI (NLP)
```bash
flyctl secrets set \
  OPENAI_API_KEY=TU_OPENAI_API_KEY_AQUI
```

**Dónde obtener:**
- Ve a: https://platform.openai.com/api-keys
- Create new secret key
- Copia el key (solo se muestra 1 vez)

### QloApps PMS (Opcional)
```bash
flyctl secrets set \
  PMS_API_KEY=TU_QLOAPPS_API_KEY_AQUI \
  PMS_BASE_URL=https://tu-qloapps.com/api \
  PMS_TYPE=qloapps
```

---

## ✅ VERIFICACIÓN DESPUÉS DEL DEPLOY

### Ver status
```bash
flyctl status
```

### Ver logs en tiempo real
```bash
flyctl logs -f
```

### Ver todos los secrets configurados
```bash
flyctl secrets list
```

Deberías ver mínimo:
- SECRET_KEY
- JWT_SECRET
- JWT_REFRESH_SECRET
- ENCRYPTION_KEY
- DATABASE_URL (automático de PostgreSQL)
- WHATSAPP_VERIFY_TOKEN
- SMTP_PASSWORD
- REDIS_PASSWORD
- GRAFANA_ADMIN_PASSWORD

### Test health endpoint
```bash
curl https://agente-hotel.fly.dev/health/live
```

Respuesta esperada:
```json
{"status": "alive", "timestamp": "2025-10-18T..."}
```

### Test métricas (Prometheus)
```bash
curl https://agente-hotel.fly.dev/metrics
```

---

## 🔧 COMANDOS ÚTILES POST-DEPLOYMENT

### Acceder a consola SSH
```bash
flyctl ssh console
```

Dentro de la consola:
```bash
# Ver variables de entorno
printenv | grep -E "SECRET|JWT|DATABASE"

# Ver logs de app
tail -f /var/log/app.log

# Test local
curl localhost:8000/health/live

# Salir
exit
```

### Ver PostgreSQL
```bash
flyctl postgres connect -a agente-hotel-db
```

Dentro de psql:
```sql
\l              -- Listar bases de datos
\c agente_hotel -- Conectar a base de datos
\dt             -- Listar tablas
SELECT * FROM sessions LIMIT 5; -- Ver datos
\q              -- Salir
```

### Escalar app
```bash
# Más instancias
flyctl scale count=2

# Más memoria
flyctl scale memory=2048

# Ver configuración actual
flyctl scale show
```

### Rollback si algo falla
```bash
# Ver releases
flyctl releases

# Rollback a versión anterior
flyctl releases rollback
```

---

## 🎯 RESUMEN DE TUS SECRETOS GENERADOS

| Secret | Valor | Uso |
|--------|-------|-----|
| **SECRET_KEY** | `77d029579...51f04c` | JWT, sesiones, general |
| **JWT_SECRET** | `77d029579...51f04c` | Tokens JWT |
| **JWT_REFRESH_SECRET** | `77d029579...51f04c` | Refresh tokens |
| **ENCRYPTION_KEY** | `77d029579...51f04c` | Encriptar datos sensibles |
| **POSTGRES_PASSWORD** | `zAY+wsP5Z...KyMA=` | PostgreSQL |
| **MYSQL_PASSWORD** | `bUA0Wurk0...TDgk=` | MySQL (QloApps) |
| **MYSQL_ROOT_PASSWORD** | `O4eWzffi9...Za+Q=` | MySQL root |
| **REDIS_PASSWORD** | `KZg82ONKf...v6d/w=` | Redis caché |
| **WHATSAPP_VERIFY_TOKEN** | `45428a63a...13ece2` | WhatsApp webhook |
| **GRAFANA_ADMIN_PASSWORD** | `DcDYhhUf6...kE5U=` | Grafana UI |
| **SMTP_PASSWORD** | `BIFB4mEwp...pL1Po=` | Email SMTP |

⚠️ **ESTOS VALORES YA ESTÁN EN `.env.fly.local` (no en git)**

---

## 📦 ORDEN RECOMENDADO DE DEPLOYMENT

### Fase 1: Core (20 minutos)
1. ✅ Autenticar: `flyctl auth login`
2. ✅ Launch: `flyctl launch --no-deploy`
3. ✅ PostgreSQL: `flyctl postgres create` + `attach`
4. ✅ Secrets críticos: `flyctl secrets set ...`
5. ✅ Deploy: `flyctl deploy`
6. ✅ Verificar: `curl https://agente-hotel.fly.dev/health/live`

### Fase 2: Integraciones (cuando tengas credenciales)
7. ⏳ WhatsApp: `flyctl secrets set WHATSAPP_API_KEY=...`
8. ⏳ Gmail: `flyctl secrets set GMAIL_CLIENT_ID=...`
9. ⏳ OpenAI: `flyctl secrets set OPENAI_API_KEY=...`
10. ⏳ Redeploy: `flyctl deploy`

### Fase 3: Opcional
11. ⏳ Redis externo (Upstash)
12. ⏳ QloApps PMS real
13. ⏳ Custom domain
14. ⏳ Alertas y monitoring

---

## 🚨 TROUBLESHOOTING RÁPIDO

### Error: "App not found"
```bash
flyctl apps list
# Verifica que agente-hotel existe
```

### Error: "No DATABASE_URL"
```bash
# Verifica attachment
flyctl postgres list
flyctl postgres attach --app agente-hotel agente-hotel-db
```

### Error: Health checks failing
```bash
# Ver logs
flyctl logs -f

# Ver status
flyctl status

# Aumentar grace period en fly.toml si app tarda
# grace_period = 60000  # 60 segundos
```

### Error: Build failed
```bash
# Build local primero
docker build -f Dockerfile.production -t test .

# Si falla local, fix Dockerfile
# Si pasa local, redeploy
flyctl deploy --force-machines
```

---

## 📚 DOCUMENTACIÓN COMPLETA

Para más detalles, consulta:
- **`FLY-QUICK-ACTION.md`** - Guía rápida de 20 min
- **`FLY-SETUP-GUIDE.md`** - Setup detallado
- **`FLY-DEPLOY-GUIDE.md`** - Deployment completo
- **`FLY-SECRETS-GUIDE.md`** - Todo sobre secretos
- **`FLY-TROUBLESHOOTING.md`** - Solución de problemas
- **`FLY-QUICK-REFERENCE.md`** - Comandos cheatsheet

---

## ✨ ¡LISTO PARA DEPLOYAR!

Ahora tienes:
- ✅ Todos los secretos generados
- ✅ Comandos copy-paste listos
- ✅ Script interactivo (`scripts/deploy-fly-now.sh`)
- ✅ Archivo de secretos (`.env.fly.local`)
- ✅ Documentación completa

**Siguiente paso**: Ejecuta los 5 comandos de "OPCIÓN RÁPIDA" arriba 👆

**¡Adelante! 🚀**

---

**Documento generado**: 2025-10-18  
**Para**: Deployment de Agente Hotelero IA en Fly.io  
**Status**: ✅ Secretos generados y listos
