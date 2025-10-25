# Runbook: Base de Datos No Disponible

## Síntomas
- `/health/ready` devuelve 503 (readiness fail)
- Logs contienen: `Error conectando a Postgres: connection refused`
- Las reservas fallan con `DatabaseError`

## Causas Probables
1. Neon está fuera de servicio o reiniciando
2. Conexión agotada (connection pool lleno)
3. Red interrumpida (Fly ↔ Neon)
4. Credenciales DATABASE_URL expiradas

## Resolución

### Paso 1: Confirmar estado (1-2 min)
```bash
# 1a. Verificar health endpoint
curl https://agente-hotel-api.fly.dev/health/ready

# 1b. Ver logs recientes en Fly
flyctl logs -a agente-hotel-api --limit 50

# 1c. Si ves "connection pool exhausted": restart necesario
```

### Paso 2: Reiniciar máquinas Fly (3-5 min)
```bash
# Soft restart (recarga sin downtime si tienes 2+ máquinas)
flyctl restart -a agente-hotel-api

# Alternativa: hard restart (30s downtime)
flyctl apps restart agente-hotel-api
```

### Paso 3: Verificar conectividad Neon (2 min)
1. Ve a https://console.neon.tech/
2. Busca el proyecto "agente-hotel-prod"
3. Verifica estado de la DB (debe estar "Ready")
4. Si no: espera 5-10 min (puede estar reiniciando)

### Paso 4: Si persiste, restaurar desde backup (5-15 min)
1. Obtén backup más reciente en Neon dashboard
2. Crea branch temporal para restore:
   ```bash
   neon branch create agente-hotel-prod recovery-backup-$(date +%s)
   ```
3. Apunta DATABASE_URL al recovery branch
4. Verifica /health/ready pasa
5. Promoted recovery branch a main (si todo ok)

### Paso 5: Alertas a stakeholders
- **Slack**: #ops-alerts
- **Email**: ops-team@hotel.ai
- **Mensaje**: "DB restored from backup. Impact: [duración] downtime. Root cause: [causa]"

## Validación Final
```bash
# Debe pasar ambos en < 2s
curl https://agente-hotel-api.fly.dev/health/live
curl https://agente-hotel-api.fly.dev/health/ready

# Prueba funcional: envía un Intent de prueba via WhatsApp
# Debe llegar a /webhooks/whatsapp sin errores
```

## Escalación
- **Si > 15 min downtime**: Contactar L2 Engineering
- **Si > 1 hora**: Contactar L3 Architecture (posible Neon outage)

---

**MTTR esperado**: 10-15 minutos
**Última actualización**: 25-Oct-2025
