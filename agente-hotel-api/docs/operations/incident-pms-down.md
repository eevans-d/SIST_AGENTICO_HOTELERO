# Runbook: Sistema de Reservas PMS No Disponible

## Síntomas
- Endpoint `/webhooks/whatsapp` devuelve: `"pms_circuit_breaker": "open"`
- Logs contienen: `Circuit breaker is open` (repetido)
- Las intenciones de reserva fallan con fallback a cache
- Métrica: `pms_circuit_breaker_state` = 1

## Causas Probables
1. QloApps PMS fuera de servicio (5 fallos en 30s)
2. Timeout en requests PMS (> 15s sin respuesta)
3. Credenciales PMS expiradas (API_KEY, token)
4. Red interrumpida (App ↔ QloApps)

## Resolución

### Paso 1: Confirmar estado PMS (1-2 min)
```bash
# 1a. Ver logs
(Comando de logs) | grep -i "pms\|circuit"

# 1b. Buscar timestamp de apertura del CB
# Ej: "Circuit breaker opened at 2025-10-25T14:32:10Z"

# 1c. Medir latencia a PMS
curl -w "@curl-format.txt" -o /dev/null -s https://hotel-pms-url/api/availability
# Si > 15s: PMS lento o caído
```

### Paso 2: Contactar al equipo PMS (2-5 min)
1. Verifica dashboard de QloApps o tu proveedor PMS
2. Busca alertas o incidentes reportados
3. Si PMS está caído: esperar recovery (típicamente 5-10 min)
4. Si PMS está lento: contactar su soporte

### Paso 3: Circuit Breaker Recovery Automático (30 min)
- El CB entra en HALF_OPEN después de 30 segundos
- Si PMS vuelve: 1 request exitoso cierra el CB
- Reintenta operaciones cada 30s hasta que abra

**Para acelerar la recuperación**:
```bash
# Opción: Reiniciar app (reseta CB a CLOSED)
# PERO: esto cierra también cache. Solo si es crítico.
(Comando de reinicio)
```

### Paso 4: Fallback automático activo
Mientras PMS está caído, el sistema:
- ✅ Devuelve disponibilidad desde **cache** (hasta 5 min de antigüedad)
- ✅ Marca resultados como `"potentially_stale": true`
- ✅ No intenta crear nuevas reservas (para evitar conflictos)
- ⚠️ Usuarios ven "Info puede estar desactualizada"

### Paso 5: Post-Recovery
Una vez PMS vuelve (métricas `pms_circuit_breaker_state` = 0):
1. Verifica que /health/live pase
2. Prueba endpoint de disponibilidad:
   ```bash
   curl https://agente-hotel-api.fly.dev/api/v1/availability?checkin=2025-11-01
   # Debe devolver rooms SIN "potentially_stale": true
   ```
3. Notifica equipo: "PMS recovered, all systems nominal"

## Validación Final
```bash
# Métrica debe estar en 0 (CB CLOSED)
curl https://agente-hotel-api.fly.dev/metrics | grep pms_circuit_breaker_state

# Latencia normal (< 1s para GET, < 2s para POST)
curl -w "Response time: %{time_total}s\n" https://agente-hotel-api.fly.dev/health/live
```

## Escalación
- **Si > 30 min**: Contactar L2 PMS Team
- **Si > 2 horas**: Critical incident, escalate a C-level

---

**MTTR esperado**: 5-30 minutos (depende PMS)  
**Degradación aceptable**: Reservas pausadas, consultas desde cache OK  
**Última actualización**: 25-Oct-2025
