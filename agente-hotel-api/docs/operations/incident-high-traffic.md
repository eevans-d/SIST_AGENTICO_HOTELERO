# Runbook: Picos de Tráfico / Rate Limiting

## Síntomas
- `/health/live` y endpoints responden 200 OK
- Pero `/webhooks/whatsapp` devuelve **429 Too Many Requests**
- Logs: `RateLimitExceeded` o `rate limit: X requests per minute exceeded`
- Métrica: `http_requests_total{status="429"}` aumenta rápidamente

## Causas Probables
1. Ataque DDoS dirigido a webhooks (raro pero posible)
2. Cliente WhatsApp enviando mensajes duplicados (retry loop)
3. Evento legítimo de alto volumen (ej. promoción viral, evento)
4. Límite slowapi muy bajo (120/min por defecto)

## Resolución

### Paso 1: Confirmar rate limiting (1 min)
```bash
# Ver qué endpoints reciben más 429
flyctl logs -a agente-hotel-api | grep "429\|RateLimitExceeded"

# Medir tasa de requests exitosos (200, 201, etc.)
# vs rechazados (429)
```

### Paso 2: Identificar origen (2-5 min)
```bash
# Buscar IPs repetidas en logs de 429
flyctl logs -a agente-hotel-api --limit 500 | grep "429" | awk '{print $X}' | sort | uniq -c | sort -rn
# (Ajusta columna X según formato de logs)

# Si ves IP repetida: probablemente cliente legítimo con retry loop
# Si ves muchas IPs distintas: posible ataque DDoS
```

### Paso 3: Respuesta según tipo

#### Si es CLIENTE LEGÍTIMO (1-3 IPs)
1. Contacta al cliente (ej. partner hotel, sistema tercero)
2. Pídeles que exponencien sus retries (exponential backoff con jitter)
3. Opcionalmente: whitelist la IP (editar middleware de rate limiting)
4. Aumentar su cuota temporal si es necesario:
   ```python
   # En app/core/settings.py
   RATE_LIMIT_OVERRIDE = {
       "partner_hotel_ip": "1000/minute"  # Excepciones por IP
   }
   ```

#### Si es ATAQUE SOSPECHOSO (muchas IPs, pattern aleatorio)
1. **Activar protección**:
   ```bash
   # Escalar Fly.io a más máquinas temporalmente
   flyctl scale count 5 --app agente-hotel-api
   ```
2. **Implementar CAPTCHA o verificación** (más lento, pero seguro):
   - Modificar `/webhooks/whatsapp` para validar X-Hub-Signature
   - Meta Cloud siempre envía firma; verificar en middleware
3. **Contactar Fly.io DDoS protection** si ataque persiste

#### Si es EVENTO LEGÍTIMO (todos los clientes, no pattern)
1. **Escalar temporalmente**:
   ```bash
   # Aumentar máquinas en Fly
   flyctl scale count 10 --app agente-hotel-api
   
   # Aumentar límite en slowapi (temporal, en memory)
   # Nota: requiere restart si cambio en settings
   ```
2. **Monitorear**:
   - P95 latency debe mantenerse < 1s
   - Error rate debe mantenerse < 2%
3. **Post-pico**:
   - Reducir máquinas: `flyctl scale count 2`
   - Documentar: causa, duración, impacto

### Paso 4: Validación post-resolución
```bash
# Debe estar de nuevo en 200/201, sin 429
curl -i https://agente-hotel-api.fly.dev/webhooks/whatsapp -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Métrica debe mostrar 429 = 0 (o muy baja)
curl https://agente-hotel-api.fly.dev/metrics | grep "http_requests_total.*429"
```

## Alertas a Configurar (Grafana)
```prometheus
# Alert si 429 > 10 en 1 min (posible ataque)
rate(http_requests_total{status="429"}[1m]) > 10

# Alert si P95 latency > 2s (degradación)
histogram_quantile(0.95, http_request_duration_seconds) > 2
```

## Escalación
- **Si < 5 min**: Monitorear, probablemente se auto-resuelve
- **Si 5-30 min**: Escalar máquinas, investigar origen
- **Si > 30 min y no resolución**: Contactar L2 DevOps/SRE

---

**MTTR esperado**: 5-15 minutos  
**Estrategia**: Scale-first, investigate-after  
**Última actualización**: 25-Oct-2025
