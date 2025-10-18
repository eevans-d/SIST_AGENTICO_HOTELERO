# 🤖 PROMPTS PARA COMET - DEPLOYMENT EN FLY.IO WEB

**Para usar con**: Comet (Asistente de navegador)  
**Plataforma**: Fly.io Web Dashboard  
**Objetivo**: Deployar Agente Hotelero IA desde la interfaz web

---

## 📋 PROMPT 1: SETUP INICIAL Y CREACIÓN DE APP

Copia y pega este prompt a Comet cuando estés en https://fly.io/dashboard:

```
Estoy en el dashboard de Fly.io y necesito deployar mi aplicación "Agente Hotelero IA" desde mi repositorio de GitHub.

CONTEXTO DEL PROYECTO:
- Repositorio: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO
- Branch: main
- Dockerfile: Dockerfile.production (multi-stage build)
- Puerto interno: 8000
- Región preferida: Miami (mia)
- Nombre de app sugerido: agente-hotel

PASOS QUE NECESITO QUE REALICES EN LA INTERFAZ WEB:

1. CREAR NUEVA APLICACIÓN:
   - Busca el botón "Create App" o "New App" en el dashboard
   - Nombre de la app: "agente-hotel"
   - Región primaria: Miami (mia) o la más cercana disponible
   - NO crear PostgreSQL todavía (lo haremos después)

2. CONECTAR CON GITHUB:
   - Si hay opción "Deploy from GitHub", úsala
   - Conecta con mi repositorio: eevans-d/SIST_AGENTICO_HOTELERO
   - Branch: main
   - Dockerfile path: Dockerfile.production

3. CONFIGURACIÓN INICIAL:
   - Builder: Docker
   - Build strategy: Dockerfile
   - Context: . (raíz del repo)
   - Target: production (si pregunta por build target)

4. NO DEPLOYAR AÚN:
   - Si hay opción "Deploy Now", NO la uses todavía
   - Primero necesitamos configurar secretos y PostgreSQL

5. INFORMARME:
   - Cuando hayas completado estos pasos, dime qué opciones ves disponibles
   - Especialmente busca secciones como: "Secrets", "Environment Variables", "Database", "Settings"

ARCHIVOS DE REFERENCIA EN MI PROYECTO:
- fly.toml: Configuración completa con todas las especificaciones
- .env.fly.local: Todos los secretos ya generados (NO compartir públicamente)
- COMANDOS-FLYIO-LISTOS.md: Comandos de referencia

¿Puedes completar estos pasos navegando por la interfaz web de Fly.io?
```

---

## 📋 PROMPT 2: CONFIGURAR SECRETOS Y DATABASE (DESPUÉS DEL PROMPT 1)

Usa este prompt después de que Comet complete el Prompt 1:

```
Perfecto. Ahora necesito configurar los secretos y la base de datos PostgreSQL para la app "agente-hotel".

SECRETOS QUE DEBEN CONFIGURARSE:
Busca la sección "Secrets" o "Environment Variables" en el dashboard de la app.

SECRETOS CRÍTICOS (obligatorios):
1. SECRET_KEY = 77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
2. JWT_SECRET = 77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
3. JWT_REFRESH_SECRET = 77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
4. ENCRYPTION_KEY = 77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
5. WHATSAPP_VERIFY_TOKEN = 45428a63a31eab2be9643bc5d813ece2
6. SMTP_PASSWORD = BIFB4mEwpvPJqPkea/xMlXxvmTsrr3dqwfZ2V5pL1Po=
7. REDIS_PASSWORD = KZg82ONKfwE6mIsXk8jkDhnxOQEOhxaSyxyLPnv6d/w=
8. GRAFANA_ADMIN_PASSWORD = DcDYhhUf6fwMTK91hbERCxD+ujMqYaX4OpN60wfkE5U=

PASOS:
1. AGREGAR SECRETOS:
   - Busca la sección "Secrets" o "Environment" en el menú lateral de la app
   - Agrega cada uno de los 8 secretos listados arriba
   - Asegúrate de usar exactamente los nombres (SECRET_KEY, JWT_SECRET, etc.)
   - Copia los valores exactamente como están (incluyendo los símbolos =, +, etc.)

2. CREAR BASE DE DATOS POSTGRESQL:
   - Busca la opción "Add Database" o "PostgreSQL" en el dashboard
   - Nombre sugerido: agente-hotel-db
   - Región: Same as app (Miami/mia)
   - Plan: Development (el más económico para empezar)
   - Después de crear, busca la opción "Attach to app" o "Connect to agente-hotel"
   - Esto debería agregar automáticamente la variable DATABASE_URL

3. VERIFICAR CONFIGURACIÓN:
   - Revisa que todos los 8 secretos estén agregados
   - Verifica que aparece DATABASE_URL (agregado automáticamente por PostgreSQL)
   - Confirma que la base de datos está "Attached" a la app agente-hotel

4. CONFIGURACIÓN ADICIONAL (si hay opción en la web):
   - Health check path: /health/live
   - Internal port: 8000
   - Min instances: 1
   - Max instances: 2 (para empezar)

5. INFORMARME:
   - ¿Todos los secretos fueron agregados exitosamente?
   - ¿La base de datos PostgreSQL está conectada?
   - ¿Hay algún botón "Deploy" o "Deploy Now" visible?

NO USES VALORES PLACEHOLDER O FICTICIOS - usa exactamente los valores que proporcioné arriba.
```

---

## 📋 PROMPT 3: DEPLOY FINAL (DESPUÉS DEL PROMPT 2)

Usa este prompt cuando Comet haya configurado secretos y database:

```
Excelente. Ahora vamos a deployar la aplicación.

PASOS FINALES:

1. INICIAR DEPLOYMENT:
   - Busca el botón "Deploy", "Deploy Now", o "Manual Deploy"
   - Si pregunta por deployment method: "Deploy from GitHub"
   - Branch: main
   - Confirma que usará Dockerfile.production

2. MONITOREAR BUILD:
   - Observa los logs de build en tiempo real (si están disponibles)
   - El build debería tomar 3-5 minutos
   - Busca mensajes de éxito como:
     * "Build successful"
     * "Image pushed"
     * "Deployment successful"

3. VERIFICAR HEALTH CHECKS:
   - Después del deploy, busca la sección "Health Checks" o "Monitoring"
   - Verifica que el health check en /health/live esté pasando (verde)
   - Puede tardar 30-60 segundos después del deploy inicial

4. OBTENER URL DE LA APP:
   - Busca la URL pública de la aplicación (debería ser algo como agente-hotel.fly.dev)
   - Copia esa URL

5. PROBAR LA APLICACIÓN:
   - Abre la URL en una nueva pestaña
   - Agrega /health/live al final (ej: https://agente-hotel.fly.dev/health/live)
   - Deberías ver una respuesta JSON como: {"status": "alive", "timestamp": "..."}

6. VERIFICAR LOGS (opcional):
   - Si hay una sección "Logs" o "Runtime Logs", ábrela
   - Busca errores en rojo (si los hay, cópialos para análisis)
   - Los logs normales deberían mostrar: "Application startup complete", "Uvicorn running", etc.

7. INFORMARME:
   - URL pública de la aplicación
   - Estado del health check (passing/failing)
   - Si ves algún error en logs, cópialo completo
   - Tiempo que tomó el deployment

SI ALGO FALLA:
- Copia el mensaje de error completo
- Revisa la sección "Events" o "Activity" para más detalles
- Verifica que todos los secretos estén configurados (Prompt 2)
- Confirma que la base de datos está attached

¿Puedes completar el deployment y verificar que todo funcione?
```

---

## 🎯 ALTERNATIVA: PROMPT TODO-EN-UNO (Si Comet puede manejar tareas largas)

Si prefieres un solo prompt largo, usa este:

```
Necesito tu ayuda para deployar mi aplicación "Agente Hotelero IA" en Fly.io usando la interfaz web.

INFORMACIÓN DEL PROYECTO:
- Repositorio GitHub: https://github.com/eevans-d/SIST_AGENTICO_HOTELERO
- Branch: main
- Dockerfile: Dockerfile.production
- Puerto: 8000
- Región: Miami (mia)
- Nombre app: agente-hotel

SECRETOS A CONFIGURAR (cópialos exactamente):
- SECRET_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
- JWT_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
- JWT_REFRESH_SECRET=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
- ENCRYPTION_KEY=77d029579f0b13b908435c21d43b6f1e20c287a695518e12c230d5050451f04c
- WHATSAPP_VERIFY_TOKEN=45428a63a31eab2be9643bc5d813ece2
- SMTP_PASSWORD=BIFB4mEwpvPJqPkea/xMlXxvmTsrr3dqwfZ2V5pL1Po=
- REDIS_PASSWORD=KZg82ONKfwE6mIsXk8jkDhnxOQEOhxaSyxyLPnv6d/w=
- GRAFANA_ADMIN_PASSWORD=DcDYhhUf6fwMTK91hbERCxD+ujMqYaX4OpN60wfkE5U=

TAREAS A REALIZAR EN ORDEN:

1. Crear app "agente-hotel" conectada a mi repo de GitHub
2. Configurar los 8 secretos en la sección Secrets/Environment
3. Crear base de datos PostgreSQL llamada "agente-hotel-db" y attacharla
4. Configurar health check en /health/live con puerto 8000
5. Deployar usando Dockerfile.production del branch main
6. Verificar que /health/live responda correctamente
7. Darme la URL pública y estado del deployment

Explícame cada paso mientras lo realizas y avísame si encuentras algún problema.
```

---

## 📝 NOTAS IMPORTANTES PARA TI

**Antes de compartir con Comet:**
1. ✅ Asegúrate de estar logueado en Fly.io
2. ✅ Abre https://fly.io/dashboard en tu navegador
3. ✅ Ten acceso a tu repositorio GitHub conectado

**Después del deployment:**
1. Verifica la URL: https://agente-hotel.fly.dev/health/live
2. Revisa logs en la web si hay errores
3. Si falla, consulta FLY-TROUBLESHOOTING.md

**Limitaciones de la interfaz web:**
- Es posible que algunas configuraciones avanzadas (como fly.toml completo) no estén disponibles en la UI web
- Si Comet no puede completar algo, siempre puedes usar flyctl CLI con COMANDOS-FLYIO-LISTOS.md

**Archivos de respaldo:**
- COMANDOS-FLYIO-LISTOS.md: Comandos CLI si la web no funciona
- scripts/deploy-fly-now.sh: Script interactivo para CLI
- FLY-TROUBLESHOOTING.md: Soluciones a problemas comunes

---

## 🎯 RECOMENDACIÓN

**Empieza con PROMPT 1**, espera a que Comet complete la tarea, revisa el resultado, y luego pasa al PROMPT 2, y finalmente al PROMPT 3.

Esto le da a Comet tareas más manejables y te permite verificar cada paso.

**¡Buena suerte con el deployment! 🚀**
