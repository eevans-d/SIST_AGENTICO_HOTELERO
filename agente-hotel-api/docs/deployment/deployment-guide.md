# Guía de Despliegue y Operaciones - Agente Hotel IA

## Índice
1. [Ambientes de Despliegue](#1-ambientes-de-despliegue)
2. [Requisitos Previos](#2-requisitos-previos)
3. [Proceso de Despliegue a Staging](#3-proceso-de-despliegue-a-staging)
4. [Monitoreo y Validación Canary](#4-monitoreo-y-validación-canary)
5. [Despliegue a Producción](#5-despliegue-a-producción)
6. [Rollback](#6-rollback)
7. [Gestión de Secrets](#7-gestión-de-secrets)
8. [Monitoreo y Alertas](#8-monitoreo-y-alertas)
9. [Troubleshooting Común](#9-troubleshooting-común)
10. [Plan de Respuesta a Incidentes](#10-plan-de-respuesta-a-incidentes)

## 1. Ambientes de Despliegue

El sistema Agente Hotel IA consta de tres ambientes principales:

### 1.1. Desarrollo (Development)
- **Propósito**: Desarrollo y pruebas locales
- **URL**: http://localhost:8000
- **Configuración**: `docker-compose.yml` y `.env`
- **PMS**: Normalmente usa mock (PMS_TYPE=mock)

### 1.2. Staging
- **Propósito**: Pruebas previas a producción
- **URL**: https://staging.agente-hotel.com
- **Configuración**: `docker-compose.staging.yml` y `.env.staging`
- **PMS**: Conexión real a QloApps de staging

### 1.3. Producción
- **Propósito**: Ambiente de producción
- **URL**: https://api.agente-hotel.com
- **Configuración**: `docker-compose.production.yml` y `.env.production`
- **PMS**: Conexión real a QloApps de producción

## 2. Requisitos Previos

### 2.1. Software Requerido
- Docker y Docker Compose
- Git
- Python 3.10+ (para scripts locales)
- jq (para procesamiento JSON)
- bc (para cálculos en scripts de monitoreo)

### 2.2. Accesos Necesarios
- Credenciales de acceso a los servidores de staging y producción
- Tokens para APIs de WhatsApp y Gmail
- Credenciales de API de QloApps
- Acceso al registro Docker (opcional)

## 3. Proceso de Despliegue a Staging

### 3.1. Preparación del Ambiente
```bash
# Clonar repositorio (si es necesario)
git clone https://github.com/eevans-d/SIST_AGENTICO_HOTELERO.git
cd SIST_AGENTICO_HOTELERO/agente-hotel-api

# Crear y configurar .env.staging
cp .env.staging.template .env.staging
nano .env.staging  # Editar con valores reales
```

### 3.2. Validación de Configuración
```bash
# Verificar conexión con QloApps
python scripts/setup_qloapps.py connection

# Realizar verificaciones previas al despliegue
make preflight ENVIRONMENT=staging
```

### 3.3. Despliegue a Staging
```bash
# Método 1: Script automatizado
bash scripts/deploy-staging.sh

# Método 2: Manual con Docker Compose
docker-compose -f docker-compose.staging.yml --env-file .env.staging down
docker-compose -f docker-compose.staging.yml --env-file .env.staging build
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d
```

### 3.4. Verificación Post-Despliegue
```bash
# Verificar logs
docker-compose -f docker-compose.staging.yml logs -f

# Verificar endpoints de salud
curl https://staging.agente-hotel.com/health/live
curl https://staging.agente-hotel.com/health/ready

# Verificar métricas
curl http://localhost:9091/metrics | grep pms_
```

## 4. Monitoreo y Validación Canary

### 4.1. Período de Estabilización
- Esperar al menos 15-30 minutos después del despliegue para permitir la estabilización del sistema.
- Monitorear logs y métricas activamente durante este período.

### 4.2. Ejecución de Análisis Canary
```bash
# Ejecutar script de monitoreo canary
bash scripts/canary-monitor.sh

# Para personalizar umbrales
LATENCY_THRESHOLD=1.2 ERROR_RATE_THRESHOLD=0.03 bash scripts/canary-monitor.sh
```

### 4.3. Interpretación de Resultados
- El script generará un archivo `.playbook/canary_diff_report.json` con los resultados
- **PASS**: Todas las métricas están dentro de los umbrales aceptables
- **WARNING**: Hay métricas que muestran tendencias preocupantes pero no críticas
- **FAIL**: Una o más métricas están fuera de los umbrales aceptables

### 4.4. Pruebas Funcionales Críticas
Realizar pruebas manuales de los flujos críticos:

1. **Disponibilidad**: Consultar disponibilidad para diferentes fechas
2. **Reservas**: Crear una reserva de prueba
3. **WhatsApp**: Verificar flujo de conversación básico
4. **Gmail**: Verificar procesamiento de correos

## 5. Despliegue a Producción

### 5.1. Requisitos Previos
- Despliegue exitoso en staging
- Análisis canary PASS
- Pruebas funcionales exitosas
- Aprobación del equipo

### 5.2. Preparación
```bash
# Actualizar rama principal
git checkout main
git pull origin main

# Crear y configurar .env.production (si no existe)
cp .env.staging .env.production
nano .env.production  # Ajustar valores para producción
```

### 5.3. Despliegue
```bash
# Crear backup antes del despliegue
make backup ENVIRONMENT=production

# Despliegue
docker-compose -f docker-compose.production.yml --env-file .env.production build
docker-compose -f docker-compose.production.yml --env-file .env.production up -d
```

### 5.4. Verificación Post-Despliegue
```bash
# Verificar logs
docker-compose -f docker-compose.production.yml logs -f

# Verificar endpoints de salud
curl https://api.agente-hotel.com/health/live
curl https://api.agente-hotel.com/health/ready
```

## 6. Rollback

### 6.1. Criterios para Rollback
- Error rate > 2%
- Latencia P95 aumenta más de 20% respecto a baseline
- Circuit breaker en estado OPEN por más de 5 minutos
- Fallos en pruebas funcionales críticas

### 6.2. Proceso de Rollback
```bash
# Restaurar versión anterior
docker-compose -f docker-compose.production.yml --env-file .env.production down
git checkout [TAG_ANTERIOR]
docker-compose -f docker-compose.production.yml --env-file .env.production build
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# Restaurar datos (solo si es necesario)
make restore ENVIRONMENT=production BACKUP_DATE=YYYYMMDD_HHMMSS
```

### 6.3. Notificación Post-Rollback
- Informar al equipo sobre el rollback
- Documentar el problema y las acciones tomadas
- Planificar una investigación detallada

## 7. Gestión de Secrets

### 7.1. Ubicación de Secrets
- Los secrets están almacenados en archivos `.env.[environment]`
- Nunca se deben commitear estos archivos al repositorio

### 7.2. Rotación de Secrets
- **API Keys**: Rotación trimestral
- **Tokens de WhatsApp**: Rotación cuando se acerque la fecha de expiración
- **Contraseñas de DB**: Rotación semestral

### 7.3. Procedimiento de Rotación
```bash
# 1. Generar nuevo secret en el servicio correspondiente
# 2. Actualizar el archivo .env correspondiente
nano .env.production

# 3. Reiniciar el servicio para aplicar cambios
docker-compose -f docker-compose.production.yml restart [service_name]
```

## 8. Monitoreo y Alertas

### 8.1. Dashboards
- **Grafana**: https://grafana.agente-hotel.com
  - Dashboard principal: Agente Hotel Overview
  - Dashboard PMS: QloApps Integration
  - Dashboard WhatsApp: Conversational Metrics

### 8.2. Alertas Configuradas
- **Alta prioridad**:
  - Circuit breaker en estado OPEN > 5 min
  - Error rate > 2% durante 5 min
  - Latencia P95 > 2s durante 5 min
  
- **Media prioridad**:
  - Circuit breaker en estado HALF-OPEN > 15 min
  - Error rate > 1% durante 15 min
  - Latencia P95 > 1s durante 15 min

### 8.3. Canales de Notificación
- Slack: #agente-hotel-alerts
- Email: alerts@example.com

## 9. Troubleshooting Común

### 9.1. Problemas de Conexión con QloApps
```bash
# Verificar configuración PMS
grep -E "^PMS_" .env.production

# Probar conexión directamente
python scripts/setup_qloapps.py connection

# Verificar estado del circuit breaker
curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state
```

### 9.2. Problemas con WhatsApp API
```bash
# Verificar configuración WhatsApp
grep -E "^WHATSAPP_" .env.production

# Verificar logs específicos
docker-compose -f docker-compose.production.yml logs agente-api | grep -i whatsapp
```

### 9.3. Problemas de Rendimiento
```bash
# Verificar uso de recursos
docker stats

# Verificar latencia del API
curl http://localhost:9090/api/v1/query?query=histogram_quantile\(0.95,\ rate\(http_request_duration_seconds_bucket\[5m\]\)\)

# Verificar hit rate de caché
curl http://localhost:9090/api/v1/query?query=sum\(rate\(pms_cache_hits_total\[5m\]\)\)\ /\ \(sum\(rate\(pms_cache_hits_total\[5m\]\)\)\ +\ sum\(rate\(pms_cache_misses_total\[5m\]\)\)\)
```

## 10. Plan de Respuesta a Incidentes

### 10.1. Niveles de Severidad

| Nivel | Descripción | Tiempo de Respuesta | Equipo Involucrado |
|-------|-------------|---------------------|---------------------|
| P1    | Sistema completamente caído o inutilizable | Inmediato (< 15 min) | Todo el equipo + Gerencia |
| P2    | Función crítica afectada | < 30 min | Equipo técnico |
| P3    | Función no crítica afectada | < 2 horas | Desarrollador de guardia |
| P4    | Problema menor | < 24 horas | Asignado en siguiente sprint |

### 10.2. Proceso de Escalamiento

1. **Detección**: Alerta automática o reporte manual
2. **Evaluación**: Determinar nivel de severidad
3. **Comunicación**: Notificar según nivel de severidad
4. **Mitigación**: Aplicar solución temporal si es posible
5. **Resolución**: Implementar solución definitiva
6. **Revisión**: Análisis post-mortem

### 10.3. Contactos de Emergencia

| Rol | Responsabilidad | Contacto |
|-----|----------------|----------|
| SRE de guardia | Primera respuesta | sre@example.com / +1234567890 |
| Lead Developer | Problemas técnicos complejos | lead@example.com / +1234567891 |
| Product Manager | Comunicación con clientes | pm@example.com / +1234567892 |

---

## Anexo: Comandos Útiles

### Monitoreo
```bash
# Ver logs en tiempo real
docker-compose -f docker-compose.production.yml logs -f

# Ver logs de un servicio específico
docker-compose -f docker-compose.production.yml logs -f agente-api

# Ver uso de recursos
docker stats
```

### Gestión de Datos
```bash
# Backup manual
make backup ENVIRONMENT=production

# Restaurar backup
make restore ENVIRONMENT=production BACKUP_DATE=20251005_153045
```

### Mantenimiento
```bash
# Limpiar logs antiguos
find ./logs -type f -name "*.log" -mtime +30 -delete

# Limpiar imágenes Docker no utilizadas
docker system prune -a --volumes
```

### Seguridad
```bash
# Verificar vulnerabilidades de seguridad
make security-fast

# Verificar secrets expuestos
make lint
```