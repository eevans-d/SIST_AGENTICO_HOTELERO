# Manual de Operaciones - Agente Hotelero IA System

## Resumen Ejecutivo

El Sistema de Agente Hotelero IA es una plataforma integral de automatización hotelera que maneja comunicaciones multicanal (WhatsApp, Gmail), gestión de reservas (QloApps PMS), y proporciona business intelligence avanzado con capacidades de monitoreo en tiempo real.

### Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   PMS Backend   │
│   (Grafana)     │◄──►│  (FastAPI)      │◄──►│   (QloApps)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Cache Layer   │    │   Database      │
│  (Prometheus)   │    │    (Redis)      │    │ (PostgreSQL)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 1. Monitoreo de Sistemas

### 1.1 Dashboard Principal de Operaciones

#### KPIs Críticos para Monitorear Diariamente
- **Disponibilidad del Sistema**: >99.5%
- **Tiempo de Respuesta API**: <500ms P95
- **Tasa de Éxito de Mensajes**: >98%
- **Ocupación Hotelera**: Tiempo real
- **Satisfacción del Huésped**: Score promedio
- **Revenue per Available Room (RevPAR)**: Diario

#### URLs de Acceso
```
- Dashboard Principal: http://localhost:3000/d/hotel-ops
- Métricas Técnicas: http://localhost:3000/d/tech-metrics
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093
- API Health: http://localhost:8000/health/ready
```

### 1.2 Alertas Críticas

#### Nivel CRÍTICO (Respuesta Inmediata)
- **API Completamente Caída**: `up{job="agente-api"} == 0`
- **Base de Datos Inaccesible**: Conexiones fallando >1 minuto
- **Memoria >95%**: Riesgo de crash inminente
- **Disco >95%**: Sistema puede detenerse

#### Nivel ALTO (Respuesta <15 minutos)
- **Latencia API >2s**: Performance degradada
- **Tasa de Error >5%**: Problemas con huéspedes
- **PMS Integration Falla**: Reservas afectadas
- **WhatsApp Webhook Down**: Comunicación interrumpida

#### Nivel MEDIO (Respuesta <1 hora)
- **Memoria >85%**: Planificar escalado
- **Disco >80%**: Limpiar logs
- **Certificados SSL <30 días**: Renovar pronto

### 1.3 Comandos de Monitoreo Rápido

#### Verificación de Estado General
```bash
# Health check completo
./scripts/monitoring.sh quick

# Estado de todos los servicios
docker-compose ps

# Logs en tiempo real
docker-compose logs -f --tail=100
```

#### Métricas de Performance
```bash
# CPU y memoria de contenedores
docker stats --no-stream

# Latencia de API
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health/ready

# Consultas activas en BD
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

---

## 2. Gestión de Reservas

### 2.1 Flujo de Reservas por WhatsApp

#### Estados de Reserva
1. **INQUIRY**: Huésped solicita información
2. **QUOTE_SENT**: Cotización enviada
3. **PENDING_CONFIRMATION**: Esperando confirmación
4. **CONFIRMED**: Reserva confirmada en PMS
5. **CHECKED_IN**: Huésped en hotel
6. **CHECKED_OUT**: Reserva completada
7. **CANCELLED**: Reserva cancelada

#### Monitoreo de Reservas
```bash
# Reservas pendientes de confirmación
curl -s "http://localhost:8000/api/v1/reservations?status=PENDING_CONFIRMATION" | jq '.count'

# Reservas del día
curl -s "http://localhost:8000/api/v1/reservations?date=$(date +%Y-%m-%d)" | jq '.reservations[] | {guest_name, room_type, status}'

# Ocupación actual
curl -s "http://localhost:8000/api/v1/occupancy" | jq '.occupancy_rate'
```

### 2.2 Integración con PMS (QloApps)

#### Verificación de Conectividad PMS
```bash
# Test de conexión directa
curl -X GET "$PMS_BASE_URL/api/health"

# Verificar circuit breaker
curl -s http://localhost:8000/metrics | grep pms_circuit_breaker_state

# Logs de PMS adapter
grep "PMS" /var/log/agente-hotel/app.log | tail -20
```

#### Sincronización Manual
```bash
# Forzar sincronización de disponibilidad
curl -X POST "http://localhost:8000/api/v1/admin/sync/availability"

# Verificar inconsistencias
curl -X GET "http://localhost:8000/api/v1/admin/audit/pms"
```

---

## 3. Comunicaciones Multicanal

### 3.1 WhatsApp Business API

#### Configuración del Webhook
```bash
# Verificar webhook configurado
curl -X GET "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID/webhooks" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Test del webhook local
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "test",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "messages": [{
            "from": "1234567890",
            "id": "test_message_id",
            "timestamp": "1234567890",
            "text": {"body": "Hola, quiero hacer una reserva"},
            "type": "text"
          }]
        }
      }]
    }]
  }'
```

#### Métricas de WhatsApp
```bash
# Mensajes procesados en las últimas 24h
curl -s "http://localhost:8000/metrics" | grep whatsapp_messages_total

# Tasa de respuesta promedio
curl -s "http://localhost:8000/api/v1/metrics/whatsapp" | jq '.average_response_time'

# Mensajes fallidos
grep "whatsapp.*error" /var/log/agente-hotel/app.log | wc -l
```

### 3.2 Integración Gmail

#### Verificación de Credenciales
```bash
# Test de conexión Gmail
curl -X GET "http://localhost:8000/api/v1/admin/gmail/test"

# Emails procesados
curl -s "http://localhost:8000/metrics" | grep gmail_emails_total

# Último email procesado
curl -s "http://localhost:8000/api/v1/admin/gmail/status" | jq '.last_processed'
```

---

## 4. Mantenimiento Preventivo

### 4.1 Tareas Diarias (Automatizadas)

#### Script de Mantenimiento Diario
```bash
#!/bin/bash
# scripts/daily-maintenance.sh

# 1. Verificar salud del sistema
./scripts/monitoring.sh quick

# 2. Limpiar logs antiguos
find /var/log/agente-hotel -name "*.log" -mtime +7 -delete

# 3. Backup incremental
./scripts/backup.sh incremental

# 4. Limpiar cache expirado
docker exec redis-agente-prod redis-cli FLUSHEXPIRED

# 5. Verificar espacio en disco
df -h / | awk 'NR==2 {if ($5+0 > 80) print "WARNING: Disk usage " $5}'

# 6. Generar reporte diario
./scripts/monitoring.sh report
```

### 4.2 Tareas Semanales

#### Backup Completo
```bash
# scripts/weekly-maintenance.sh

# Backup completo del sistema
./scripts/backup.sh full

# Optimización de base de datos
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "VACUUM ANALYZE;"

# Rotación de logs
logrotate /etc/logrotate.d/agente-hotel

# Verificar certificados SSL
openssl x509 -in /etc/ssl/agente-hotel/server.crt -noout -enddate

# Test de recuperación (ambiente de staging)
if [ "$ENVIRONMENT" = "staging" ]; then
    ./scripts/disaster-recovery-test.sh
fi
```

### 4.3 Tareas Mensuales

#### Análisis de Performance
```bash
# scripts/monthly-maintenance.sh

# Análisis de queries lentas
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"

# Estadísticas de cache
docker exec redis-agente-prod redis-cli INFO stats

# Reindexación de base de datos
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "REINDEX DATABASE agente_db;"

# Audit de seguridad
./scripts/security-audit.sh

# Actualización de dependencias (staging primero)
if [ "$ENVIRONMENT" = "staging" ]; then
    poetry update
    ./scripts/test-all.sh
fi
```

---

## 5. Troubleshooting Común

### 5.1 Problemas de Performance

#### API Lenta (>2s response time)
```bash
# 1. Verificar carga del sistema
top
htop

# 2. Verificar queries lentas
docker logs postgres-agente-prod | grep "slow query"

# 3. Verificar cache hit rate
docker exec redis-agente-prod redis-cli INFO stats | grep hit_rate

# 4. Aumentar recursos si es necesario
docker update --memory=4g --cpus=2 agente-hotel-api-prod
```

#### Base de Datos con Muchas Conexiones
```bash
# Verificar conexiones activas
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "
SELECT pid, usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE state = 'active';"

# Matar conexiones idle
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"
```

### 5.2 Problemas de Integración

#### PMS No Responde
```bash
# 1. Verificar estado del servicio QloApps
curl -f http://localhost/api/health || echo "PMS Down"

# 2. Verificar logs de QloApps
docker logs qloapps-prod | tail -50

# 3. Reiniciar PMS si es necesario
docker restart qloapps-prod

# 4. Verificar circuit breaker
curl http://localhost:8000/api/v1/admin/pms/circuit-breaker/status
```

#### WhatsApp Webhook No Funciona
```bash
# 1. Verificar configuración del webhook
curl -X GET "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID/webhooks" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 2. Verificar logs de webhook
grep "webhook" /var/log/agente-hotel/app.log | tail -20

# 3. Re-configurar webhook si es necesario
curl -X POST "https://graph.facebook.com/v18.0/$PHONE_NUMBER_ID/webhooks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "webhooks": [
      {
        "callback_url": "https://your-domain.com/webhook/whatsapp",
        "verify_token": "'$WHATSAPP_VERIFY_TOKEN'",
        "fields": ["messages"]
      }
    ]
  }'
```

### 5.3 Problemas de Memoria

#### Memoria Agotada
```bash
# 1. Identificar proceso que consume más memoria
docker stats --no-stream | sort -k 7 -hr

# 2. Verificar logs por memory leaks
grep -i "memory\|oom" /var/log/agente-hotel/*.log

# 3. Reiniciar servicios con alta memoria
docker restart [container-with-high-memory]

# 4. Limpiar cache si es necesario
docker exec redis-agente-prod redis-cli FLUSHALL
```

---

## 6. Procedimientos de Emergencia

### 6.1 Sistema Completamente Caído

#### Proceso de Recuperación Rápida
```bash
# 1. Verificar estado de Docker
sudo systemctl status docker
sudo systemctl restart docker

# 2. Levantar servicios críticos primero
docker-compose -f deploy/docker-compose.production.yml up -d postgres-prod redis-prod

# 3. Esperar a que DBs estén listas
sleep 60

# 4. Levantar aplicación principal
docker-compose -f deploy/docker-compose.production.yml up -d agente-api

# 5. Verificar salud
./scripts/monitoring.sh quick

# 6. Levantar servicios de monitoreo
docker-compose -f deploy/docker-compose.production.yml up -d prometheus-prod grafana-prod
```

### 6.2 Corrupción de Base de Datos

#### Proceso de Recuperación
```bash
# 1. Detener aplicación para evitar más daño
docker stop agente-hotel-api-prod

# 2. Verificar integridad de PostgreSQL
docker exec postgres-agente-prod pg_dump -U agente_user agente_db > /tmp/test_dump.sql

# 3. Si el dump falla, restaurar desde backup más reciente
./scripts/restore.sh /var/backups/agente-hotel/latest/

# 4. Verificar integridad post-restauración
docker exec postgres-agente-prod psql -U agente_user -d agente_db -c "SELECT count(*) FROM reservations;"

# 5. Reiniciar aplicación
docker start agente-hotel-api-prod
```

### 6.3 Compromiso de Seguridad

#### Respuesta a Incidente de Seguridad
```bash
# 1. INMEDIATO: Aislar el sistema
iptables -A INPUT -j DROP  # Bloquear todo tráfico entrante

# 2. Preservar evidencia
cp /var/log/agente-hotel/*.log /forensics/$(date +%Y%m%d_%H%M%S)/
docker logs agente-hotel-api-prod > /forensics/$(date +%Y%m%d_%H%M%S)/docker.log

# 3. Verificar integridad de datos críticos
./scripts/security-audit.sh full

# 4. Cambiar todas las credenciales
./scripts/rotate-credentials.sh

# 5. Restaurar tráfico cuando sea seguro
iptables -F  # Limpiar reglas de firewall
```

---

## 7. Métricas de Business Intelligence

### 7.1 KPIs de Negocio

#### Métricas de Revenue
```bash
# RevPAR (Revenue per Available Room) del día
curl -s "http://localhost:8000/api/v1/metrics/revpar?date=$(date +%Y-%m-%d)" | jq '.revpar'

# ADR (Average Daily Rate)
curl -s "http://localhost:8000/api/v1/metrics/adr" | jq '.adr'

# Ocupación por tipo de habitación
curl -s "http://localhost:8000/api/v1/metrics/occupancy-by-room-type" | jq '.'
```

#### Métricas de Satisfacción
```bash
# Score promedio de satisfacción
curl -s "http://localhost:8000/api/v1/metrics/satisfaction" | jq '.average_score'

# Tiempo promedio de respuesta a huéspedes
curl -s "http://localhost:8000/api/v1/metrics/response-time" | jq '.average_response_time_minutes'

# Tasa de conversión de consultas a reservas
curl -s "http://localhost:8000/api/v1/metrics/conversion-rate" | jq '.conversion_rate'
```

### 7.2 Reportes Automáticos

#### Reporte Diario Ejecutivo
```bash
# scripts/daily-executive-report.sh

DATE=$(date +%Y-%m-%d)
REPORT_FILE="/reports/executive_report_$DATE.json"

# Generar reporte ejecutivo
curl -s "http://localhost:8000/api/v1/reports/executive-daily" > "$REPORT_FILE"

# Enviar por email (si está configurado)
if [ -n "$EXECUTIVE_EMAIL" ]; then
    python3 scripts/send-executive-report.py "$REPORT_FILE" "$EXECUTIVE_EMAIL"
fi
```

---

## 8. Contactos de Emergencia

### 8.1 Escalación de Incidentes

#### Nivel 1 - Soporte Técnico (24/7)
- **Email**: soporte-l1@agente-hotelero.com
- **Slack**: #incident-response
- **Phone**: +34-XXX-XXX-XXX

#### Nivel 2 - Ingeniería Senior
- **Email**: soporte-l2@agente-hotelero.com
- **Slack**: #engineering-senior
- **On-call**: PagerDuty

#### Nivel 3 - Arquitectura y CTO
- **Email**: cto@agente-hotelero.com
- **Phone**: +34-XXX-XXX-XXX (Solo emergencias críticas)

### 8.2 Proveedores Críticos

#### WhatsApp Business API
- **Soporte**: https://business.facebook.com/support
- **Documentación**: https://developers.facebook.com/docs/whatsapp

#### QloApps PMS
- **Soporte**: support@qloapps.com
- **Documentación**: https://qloapps.com/support

---

## 9. Checklist de Operaciones

### 9.1 Checklist Diario
- [ ] Verificar dashboard de salud del sistema
- [ ] Revisar alertas pendientes
- [ ] Verificar métricas de performance (latencia <500ms)
- [ ] Verificar tasa de mensajes procesados
- [ ] Verificar ocupación hotelera
- [ ] Revisar logs de errores
- [ ] Verificar espacio en disco (<80%)
- [ ] Backup incremental completado

### 9.2 Checklist Semanal
- [ ] Backup completo realizado
- [ ] Optimización de base de datos ejecutada
- [ ] Rotación de logs completada
- [ ] Verificar certificados SSL (>30 días restantes)
- [ ] Revisar métricas de satisfacción del huésped
- [ ] Análisis de tendencias de ocupación
- [ ] Test de procedimientos de emergencia

### 9.3 Checklist Mensual
- [ ] Análisis de queries lentas
- [ ] Reindexación de base de datos
- [ ] Audit de seguridad
- [ ] Revisión de capacidad y escalado
- [ ] Actualización de dependencias (staging)
- [ ] Revisión de métricas de business intelligence
- [ ] Training del equipo en nuevas funcionalidades

---

*Manual de Operaciones v2.0 - Última actualización: Diciembre 2024*

**Nota Importante**: Este manual debe mantenerse actualizado con cualquier cambio en la arquitectura del sistema. Para cambios críticos, notificar al equipo de operaciones con al menos 48 horas de anticipación.