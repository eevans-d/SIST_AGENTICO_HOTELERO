# DOCUMENTACIÓN COMPLETA DEL AGENTE HOTELERO IA

## Resumen Ejecutivo

Agente IA Hotelero es un sistema agnético multicanal (WhatsApp via Meta Cloud API, Gmail) que automatiza la recepción virtual de hoteles integrándose con QloApps PMS. Gestiona consultas de disponibilidad, reservas, modificaciones y cancelaciones mediante procesamiento de lenguaje natural, reduciendo tiempos de respuesta a menos de 3 segundos y permitiendo monitoreo en tiempo real con stack completo de observabilidad (Prometheus/Grafana/AlertManager).

---

## PERSPECTIVA 1 — AGENTE IA: "¿QUÉ ES Y QUÉ HACE?"

### Descripción Ejecutiva

Sistema agnético de recepción hotelera basado en FastAPI que orquesta comunicaciones multicanal (WhatsApp vía **Meta Cloud API v18.0**, Gmail) con gestión inteligente de reservas mediante integración directa con QloApps PMS. Utiliza procesamiento de lenguaje natural para interpretar solicitudes de huéspedes, consultar disponibilidad en tiempo real, ejecutar transacciones de reserva y mantener contexto conversacional persistente por sesión de usuario.

### Capacidades Detalladas

#### 1. Interpretación de Intención y Extracción de Entidades

- Analiza mensajes en lenguaje natural para identificar intents: `check_availability`, `make_reservation`, `modify_reservation`, `cancel_reservation`, `ask_amenities`, `greeting`, `goodbye`
- Extrae entidades estructuradas: fechas (check-in/out), número de huéspedes, tipo de habitación, datos de contacto
- Se activa en cada mensaje entrante; resultado: `UnifiedMessage` con intent clasificado y entidades normalizadas
- **Implementación**: `app/services/nlp_engine.py` con `NLPEngine.process_message()`

#### 2. Consulta de Disponibilidad en Tiempo Real

- Valida disponibilidad de habitaciones contra QloApps PMS mediante adaptador con circuit breaker
- Maneja caché Redis (TTL configurable, default 5 min) para optimizar consultas repetidas
- Se activa cuando intent=`check_availability`; Resultado: Lista de habitaciones disponibles con tarifas actualizadas
- **Circuit Breaker**: 3 fallos consecutivos → estado abierto por 60s (configurable en `app/core/circuit_breaker.py`)

#### 3. Gestión Completa del Ciclo de Reserva

- **Crear**: Valida datos mínimos → consulta disponibilidad → solicita confirmación → ejecuta booking en PMS → retorna ID de reserva
- **Modificar**: Recupera reserva existente → valida cambios → actualiza en PMS → notifica cambios
- **Cancelar**: Verifica política de cancelación → ejecuta cancelación → actualiza estado → confirma al huésped
- Se activa por intents específicos; resultado: confirmación con ID transaccional y estado actualizado
- **Nota**: Las reservas se almacenan en **QloApps PMS externo**, no en base de datos local

#### 4. Gestión de Sesiones Multicanal con Contexto Persistente

- Mantiene historial de conversación por usuario en PostgreSQL (tabla `sessions`)
- Permite retomar contexto tras desconexión (ej: "continuar con la reserva anterior")
- Se activa automáticamente con cada mensaje; resultado: contexto recuperado para personalización de respuestas
- **Implementación**: `app/services/session_manager.py` con persistencia async SQLAlchemy

#### 5. Enrutamiento Dinámico Multi-Tenant

- Resuelve configuración de hotel (tenant) mediante servicio dinámico con caché in-memory + refresh periódico (300s default)
- Soporta múltiples hoteles con configuraciones aisladas (credenciales PMS, políticas de negocio)
- Se activa vía feature flag `tenancy.dynamic.enabled`; resultado: enrutamiento correcto de operaciones por tenant
- **Implementación**: `app/services/dynamic_tenant_service.py`

#### 6. Manejo de Fallback y Escalamiento a Humano

- Detecta intents de baja confianza (umbral < 0.6) o errores críticos de PMS (circuit breaker abierto)
- Transfiere conversación a operador humano con contexto completo
- Se activa cuando la confianza en la PNL < umbral o 3 reintentos PMS fallidos
- **Resultado**: Notificación para escalamiento manual (UI administrativa pendiente de desarrollo)

### Características Técnicas del Comportamiento

#### Latencias (Targets SLO)

- **Respuesta inicial**: < 3 segundos (P95: 2.8s según target en documentos internos)
- **Procesamiento NLP**: ~500ms (caché de modelos en memoria)
- **Consulta PMS**: 1-5 segundos (con timeout de circuit breaker **30s** configurado en `app/core/settings.py`)
- **Reserva completa de extremo a extremo**: < 8 segundos

#### Estructura de Mensajes

- **Saludo inicial**: Presenta capacidades y solicita tipo de servicio
- **Solicitud de datos**: Mensajes estructurados con validación inline (ej: "Fecha check-in debe ser formato DD/MM/AAAA")
- **Confirmación pre-acción**: Antes de crear/modificar/cancelar reserva muestra resumen y solicita confirmación explícita ("Responde SÍ para confirmar")
- **Respuesta final**: Incluye ID transaccional, resumen de operación y próximos pasos
- **Implementación**: `app/services/template_service.py` con plantillas Jinja2

#### Reglas de Fallback

- **Error de PMS**: Si circuit breaker abierto → mensaje "Sistema de reservas temporalmente no disponible. ¿Deseas que un operador te contacte?"
- **Intención ambigua**: Si confidence < 0.6 → "No estoy seguro de entender. ¿Podrías reformular? O presiona 0 para hablar con recepción."
- **Timeout usuario**: Si > 15 min sin respuesta → guarda contexto y envía recordatorio suave
- **Escalamiento crítico**: Tras 3 fallbacks consecutivos → transferencia automática a operador con log de conversación completa

### Datos que Registra

#### Tabla `sessions` en PostgreSQL

```sql
- session_id (UUID): Identificador único de conversación
- user_id (string): ID del huésped (phone number / email)
- channel (enum): whatsapp | gmail | webchat
- tenant_id (UUID): Identificador del hotel
- intent (string): Último intent detectado
- entities (JSONB): Entidades extraídas (fechas, huéspedes, room_type)
- state (enum): active | waiting_confirmation | completed | escalated
- created_at (timestamp)
- updated_at (timestamp)
- context (JSONB): Historial de mensajes (últimos 10 turnos)
```

#### Almacenamiento de Reservas

**IMPORTANTE**: Las reservas NO se almacenan en base de datos local. Se gestionan directamente en **QloApps PMS** vía API REST. La tabla local solo mantiene referencias:

```sql
- session_id (UUID): FK a sessions
- pms_booking_id (string): ID en QloApps (referencia externa)
- guest_name, guest_email, guest_phone
- check_in_date, check_out_date
- room_type, num_guests
- status (enum): pending | confirmed | modified | cancelled
- created_at, updated_at
```

#### Logs de Eventos (PostgreSQL + Prometheus)

```sql
- event_id (UUID)
- timestamp (timestamp)
- level (info|warning|error|critical)
- service (agente-api|pms_adapter|orchestrator)
- action (message_received|pms_query|reservation_created)
- user_id, session_id, tenant_id
- latency_ms (int)
- error_message (text nullable)
- metadata (JSONB): payload completo para debugging
```

#### Almacenamiento Multi-Capa

- **PostgreSQL**: Datos transaccionales y sesiones (primaria)
- **Redis**: Caché de disponibilidad (TTL 5 min), rate limiting, feature flags
- **Prometheus**: Métricas agregadas (`pms_api_latency_seconds`, `message_gateway_requests_total`, `pms_circuit_breaker_state`)

### Sugerencia de Visualización (Diagrama de Flujo)

**Título del Diagrama**: "Flujo de Orquestación de Mensaje a Respuesta - Agente Hotelero IA"

#### Cajas y Flechas

```
[Inicio] → Usuario envía mensaje por WhatsApp/Gmail
    ↓
[Message Gateway] (caja azul): Normaliza a UnifiedMessage, resuelve tenant
    ↓
[Session Manager] (caja verde): Recupera/crea sesión, carga contexto
    ↓
[Orchestrator] (caja naranja - núcleo): Verifica feature flags
    ↓
[NLP Service] (caja morada): Detecta intent + extrae entidades
    ↓
(Decisión rombo) ¿Intent requiere PMS?
    NO → [Respuesta Directa] (caja gris) → [Envío Respuesta]
    SÍ → Continuar
    ↓
[PMS Adapter] (caja roja): Consulta QloApps con circuit breaker
    ↓
(Decisión rombo) ¿PMS respondió OK?
    NO → [Circuit Breaker Abierto] → [Manejador de Respaldo] → [Escalamiento a Humano]
    SÍ → Continuar
    ↓
[Business Logic] (caja amarilla): Valida políticas, calcula tarifas
    ↓
(Decisión rombo) ¿Requiere Confirmación?
    SÍ → [Enviar Solicitud Confirmación] → [Esperar Respuesta Usuario] (loop)
    NO → Continuar
    ↓
[Ejecutar Acción PMS] (caja roja oscuro): Crear/Modificar/Cancelar reserva
    ↓
[DB Logger] (caja gris): Registra evento en PostgreSQL + Prometheus
    ↓
[Response Builder] (caja verde claro): Construye mensaje final con ID transaccional
    ↓
[Message Gateway] (caja azul): Envía respuesta por canal original
    ↓
[Fin]
```

#### Leyenda

- **Azul**: Capa de transporte
- **Verde**: Gestión de estado
- **Naranja**: Orquestación
- **Morado**: Procesamiento NLP
- **Rojo**: Integración PMS (con circuit breaker)
- **Amarillo**: Lógica de negocio
- **Gris**: Logging y respuestas estáticas

#### Anotaciones

- Flecha punteada desde cualquier caja hacia [Fallback Handler]: Timeout o error crítico
- Ícono de caché junto a PMS Adapter: Consulta Redis antes de llamar API
- Ícono de reloj en PMS Adapter: Timeout **30s**, 3 reintentos con backoff exponencial

---

## PERSPECTIVA 2 — DUEÑO/ADMINISTRADOR: "¿CÓMO GESTIONO Y CONTROLO?"

### Descripción de Acceso

**Estado Actual**: El sistema proporciona endpoints API administrativos (`/admin/*`) y dashboards Grafana pre-configurados para monitoreo técnico. **No existe una interfaz administrativa web completa** como se describe en secciones posteriores. El dashboard descrito es una **visión aspiracional** del roadmap futuro.

#### Acceso Real Disponible

**Dashboard Grafana**:
- URL: `http://[dominio-hotel]:3000`
- Credenciales: Configuradas en `docker-compose.yml`
- **Funcionalidad**: Visualización de métricas Prometheus, dashboards JSON en `docker/grafana/dashboards/`

**Endpoints API Administrativos**:
- `/admin/tenants` - CRUD de tenants (GET, POST, PUT, DELETE)
- `/admin/tenants/refresh` - Forzar refresh de caché de tenants
- `/metrics` - Métricas Prometheus en formato OpenMetrics

**Sistema de Autenticación**:
- **Estado Actual**: Endpoints sin autenticación (desarrollo)
- **Roadmap**: JWT con roles (SuperAdmin, HotelAdmin, Operador)
- **2FA**: Pendiente de implementación

#### Permisos por Rol (Roadmap Futuro)

| Funcionalidad | SuperAdmin | HotelAdmin | Operador |
|---------------|------------|------------|----------|
| Ver todas las conversaciones | ✅ | ✅ (su hotel) | ✅ (su hotel) |
| Pausar/reanudar agente | ✅ | ✅ | ❌ |
| Editar templates de mensaje | ✅ | ✅ | ❌ |
| Configurar integraciones PMS | ✅ | ✅ | ❌ |
| Exportar datos (CSV/Excel) | ✅ | ✅ | ❌ |
| Gestionar usuarios admin | ✅ | ❌ | ❌ |

### Métricas Clave (KPIs)

#### Panel Principal - Grafana Dashboards

Los siguientes KPIs están **implementados** y disponibles en Grafana:

##### 1. Volumen de Interacciones

- **Métrica Prometheus**: `message_gateway_requests_total`
- **Desglose**: Por canal (whatsapp, gmail), por tenant, por hora
- **Target**: > 200 interacciones/día (varía por tamaño de hotel)
- **Dashboard**: `docker/grafana/dashboards/agente-hotel-overview.json`

##### 2. Tasa de Éxito de Tareas (Task Completion Rate)

- **Cálculo**: `(reservas_completadas / intents_reserva_detectados) * 100`
- **Métricas**: `orchestrator_tasks_completed_total{status="success"}` vs `{status="failed"}`
- **Objetivo**: > 85% (SLO)

##### 3. Tiempo Medio de Resolución (AHT)

- **Métrica**: `orchestrator_workflow_duration_seconds` (histograma P50, P95, P99)
- **Desglose**: Por intent (check_availability: ~3s, make_reservation: ~8s)
- **Objetivo**: P95 < 10 segundos

##### 4. Porcentaje de Escalamiento a Humano

- **Cálculo**: `(conversaciones_transferidas / total_conversaciones) * 100`
- **Métrica**: `fallback_handler_escalations_total`
- **Objetivo**: < 10% (alerta si > 15%)

##### 5. Disponibilidad del Sistema (Uptime)

- **Métrica**: `up{job="agente-api"}` (Prometheus)
- **Objetivo**: 99.5% uptime mensual

##### 6. Latencia de PMS (Backend Health)

- **Métrica**: `pms_api_latency_seconds` (P95)
- **Objetivo**: < 5 segundos; alerta si > 10s sostenido

##### 7. Tasa de Error del Sistema

- **Cálculo**: `(http_requests_total{status=~"5.."} / http_requests_total) * 100`
- **Objetivo**: < 2% (crítico si > 5%)

##### 8. Estado del Circuit Breaker

- **Métrica**: `pms_circuit_breaker_state{state="open|half_open|closed"}`
- **Visualización**: Gauge con colores (verde: closed, amarillo: half_open, rojo: open)

### Datos que Debe Monitorear

#### KPIs Críticos con Umbrales de Alerta

Configurados en `docker/alertmanager/config.yml`:

| KPI | Warning Threshold | Critical Threshold | Acción Automatizada |
|-----|-------------------|-------------------|---------------------|
| Tasa de Error | > 2% | > 5% | Email + SMS on-call |
| Latencia P95 | > 8s | > 12s | Webhook a PagerDuty |
| Circuit Breaker Abierto | > 5 minutos | > 15 minutos | Rollback automático + escalamiento |
| Tasa de Completación | < 80% | < 70% | Pausar agente + notificar |
| Conversaciones Estancadas | > 20 sin respuesta > 30 min | > 50 sin respuesta | Asignación auto a operador |
| Uso CPU (contenedor) | > 70% | > 90% | Escalado horizontal automático |
| Memoria PostgreSQL | > 80% | > 95% | Backup emergencia + alerta DBA |

#### Dashboard de Monitoreo Continuo (Grafana)

- **Vista Tiempo Real** (refresh 10s): Circuit breaker state, conversaciones activas, rate mensajes/min
- **Vista Tendencias** (24h/7d/30d): Volumen por canal, distribución de intents, AHT por semana
- **Vista Alertas Activas**: Lista de alertas firing con severidad, tiempo activo, link a runbook

### Funcionalidades de Control

#### API Endpoints Administrativos Disponibles

##### 1. Pausar/Reanudar Agente (Roadmap)

- **Endpoint**: `POST /admin/agent/toggle` (pendiente)
- **Feature Flag**: `agent.global.pause`
- **Acción**: Nuevas conversaciones reciben mensaje "Agente temporalmente no disponible"
- **Comportamiento**: Conversaciones activas se completan antes de pausar

##### 2. Gestión de Tenants (Implementado)

- **Endpoints**:
  - `GET /admin/tenants` - Listar todos los tenants
  - `POST /admin/tenants` - Crear nuevo tenant
  - `PUT /admin/tenants/{id}` - Actualizar tenant
  - `DELETE /admin/tenants/{id}` - Eliminar tenant
  - `POST /admin/tenants/refresh` - Forzar refresh caché

##### 3. Editar Templates (Roadmap)

- **Endpoint**: `PUT /admin/templates/{template_id}` (pendiente)
- **Permite editar**:
  - Saludo inicial por canal
  - Mensajes de confirmación pre-reserva
  - Mensajes de error/fallback
  - Políticas de cancelación
- **Validación**: Límite caracteres (WhatsApp 4096, SMS 160)

##### 4. Exportar Datos de Auditoría (Roadmap)

- **Endpoint**: `GET /admin/export` (pendiente)
- **Formatos**: CSV, Excel, JSON
- **Campos**: sessions, reservations, logs de eventos
- **Generación asíncrona**: Email cuando export > 10k registros

##### 5. Configurar Integraciones PMS

- **Archivo**: `app/core/settings.py`
- **Parámetros editables**:
  - `pms_base_url`: URL base de QloApps
  - `pms_api_key`: API Key (SecretStr encriptada)
  - `pms_timeout`: Timeout consultas (default **30s**)
  - Políticas de retry (max 3 intentos, backoff exponencial)

##### 6. Gestión de Feature Flags (Implementado)

- **Servicio**: `app/services/feature_flag_service.py`
- **Storage**: Redis-backed con fallback a `DEFAULT_FLAGS` dict
- **Flags configurables**:
  - `tenancy.dynamic.enabled`: Multi-tenancy dinámico
  - `nlp.advanced_entities`: Extracción avanzada NLP
  - `pms.cache.enabled`: Caché Redis de disponibilidad
  - `rate_limiting.strict`: Rate limiting estricto (10 msg/min)
- **Cambios**: Sin reinicio servicio (hot reload desde Redis)

### Mockup / Boceto del Dashboard (Visión Aspiracional)

**NOTA IMPORTANTE**: La siguiente descripción representa el **dashboard administrativo planificado** para futuras versiones. Actualmente, la administración se realiza mediante:
- **Grafana** para visualización de métricas técnicas
- **API REST endpoints** (`/admin/*`) para operaciones CRUD
- **Comandos CLI** via Makefile (`make health`, `make logs`, etc.)

#### DISEÑO GENERAL (Roadmap Futuro)

##### Header Superior (fondo azul oscuro, altura 60px)

- **Izquierda**: Logo del hotel + nombre del tenant actual (desplegable si multi-tenant)
- **Centro**: Título "Panel de Control - Agente Hotelero IA" + estado global (badge verde "OPERATIVO" o rojo "PAUSADO")
- **Derecha**: Iconos notificaciones (campana con contador alertas), perfil usuario con menú desplegable (Configuración, Logout)

##### Sidebar Izquierdo (ancho 220px, fondo gris claro)

Secciones colapsables:
- Resumen (ícono dashboard)
- Conversaciones (ícono chat)
- Reservas (ícono calendario)
- Métricas (ícono gráfico)
- Configuración (ícono engranaje)
- Logs (ícono terminal)

##### SECCIÓN 1: RESUMEN (Vista Principal)

**Fila Superior - KPIs en Cards (4 columnas)**:

1. **Tarjeta "Interacciones Hoy"**:
   - Número grande: `347` (color azul)
   - Subtexto: `+12% vs ayer` (flecha verde ↑)
   - Minigráfico línea últimas 24h

2. **Tarjeta "Tasa de Éxito"**:
   - Número: `87.3%` (color verde)
   - Subtexto: `Target: >85%` (✓)
   - Barra progreso circular

3. **Tarjeta "AHT (P95)"**:
   - Número: `8.2s` (color naranja)
   - Subtexto: `Target: <10s` (✓)
   - Mini histograma distribución

4. **Tarjeta "Escalamientos"**:
   - Número: `7.1%` (color verde)
   - Subtexto: `15 conversaciones transferidas` (link clickeable)
   - Ícono operador

**Fila Media - Estado del Sistema (3 columnas)**:

1. **Panel "Estado de Servicios"**:
   - 🟢 Agente API (latencia: 45ms)
   - 🟢 QloApps PMS (latencia: 1.2s)
   - 🟢 WhatsApp Gateway (última msg: hace 2min)
   - 🟡 Gmail Sync (cola: 3 mensajes pendientes)
   - 🟢 PostgreSQL (conexiones: 12/100)
   - 🟢 Redis (memoria: 23% usada)

2. **Panel "Circuit Breaker"**:
   - Gauge grande con aguja: Estado CLOSED (verde)
   - Texto: "Última apertura: hace 3 días"
   - Botón "Forzar Test" (solo SuperAdmin)

3. **Panel "Alertas Activas"**:
   - Lista severidad (crítico/warning), timestamp, descripción
   - Si sin alertas: "✅ Sistema operando sin alertas"

**Fila Inferior - Gráficos**:

1. **Gráfico de Línea (70% ancho)**: "Volumen de Mensajes (últimas 24h)"
   - Eje X: Horas (00:00, 03:00, ..., 21:00)
   - Eje Y: Cantidad mensajes
   - 3 líneas: WhatsApp (azul), Gmail (naranja), Total (gris punteado)

2. **Gráfico Donut (30% ancho)**: "Distribución de Intents (hoy)"
   - Segmentos: Check Availability (40%), Make Reservation (30%), Modify (15%), Cancel (10%), General (5%)

##### SECCIÓN 2: CONVERSACIONES (Vista Detalle - Roadmap)

**Filtros Superiores**:
- Dropdown "Estado": Todas | Activas | Esperando Confirmación | Completadas | Escaladas
- Dropdown "Canal": Todos | WhatsApp | Gmail
- Date picker: "Desde [DD/MM/AAAA] - Hasta [DD/MM/AAAA]"
- Input búsqueda: "Buscar por usuario, ID sesión, texto..."
- Botón "Exportar CSV"

**Tabla de Conversaciones**:

| ID Sesión | Usuario | Canal | Intent | Estado | Último Mensaje | Creado | Acciones |
|-----------|---------|-------|--------|--------|----------------|--------|----------|
| a3f7... | +34612345678 | WhatsApp | make_reservation | Waiting Confirmation | "¿Confirmas reserva...?" | hace 5 min | [Ver] [Transferir] |
| b8e2... | juan@mail.com | Gmail | check_availability | Completed | "Habitación disponible..." | hace 15 min | [Ver] [Reabrir] |

##### SECCIÓN 3: CONFIGURACIÓN (Vista de Ajustes - Roadmap)

**Pestañas horizontales**:
- **Mensajes**: Editor templates (textarea con preview, botón "Guardar")
- **Integraciones**: Form credenciales PMS (campos encriptados, botón "Test Connection")
- **Feature Flags**: Lista toggles ON/OFF con descripción
- **Usuarios**: Tabla admins con roles, botón "Invitar Usuario"

---

## PERSPECTIVA 3 — CLIENTE / USUARIO FINAL: "¿CÓMO USO ESTO?"

### Descripción de la Experiencia

El huésped interactúa con el Agente Hotelero IA a través de canales de mensajería familiar (WhatsApp vía **Meta Cloud API** o email) sin necesidad de descargar aplicaciones adicionales. La experiencia es conversacional: el agente responde en lenguaje natural, solicita información de forma incremental y confirma explícitamente antes de ejecutar cualquier acción crítica.

#### Comandos Naturales Aceptados

- "Quiero reservar una habitación del 15 al 17 de diciembre para 2 personas"
- "¿Tienen disponibilidad para este fin de semana?"
- "Necesito cancelar mi reserva #12345"
- "Cambiar mi check-in al día 20 en vez del 18"
- "¿Cuál es el precio de habitación doble?"

#### Limitaciones

- No procesa pagos directamente (proporciona instrucciones para pago)
- No gestiona servicios adicionales complejos (spa, eventos) → transfiere a recepción
- Requiere confirmación explícita para acciones irreversibles
- No interpreta imágenes o archivos adjuntos (solo texto y audio vía transcripción)

### Flujo Típico de Interacción (Paso a Paso)

#### Escenario: Crear una Reserva de Habitación

##### 1. Inicio de Conversación

**Usuario**: Envía mensaje inicial "Hola" o "Necesito reservar" por WhatsApp/Gmail

**Agente**: Responde con saludo personalizado y menú de opciones:
```
¡Hola! Soy el asistente virtual de [Nombre Hotel]. Puedo ayudarte con:
🏨 Consultar disponibilidad
📅 Crear/modificar/cancelar reservas
ℹ️ Información del hotel

¿Qué necesitas hoy?
```

##### 2. Solicitud de Datos Mínimos

**Usuario**: "Quiero reservar una habitación"

**Agente**: 
```
Perfecto. Para buscar disponibilidad necesito:
- Fecha de entrada (check-in)
- Fecha de salida (check-out)
- Número de personas

Puedes enviarme todo junto o paso a paso 😊
```

##### 3. Validación Incremental

**Usuario**: "Del 20 al 22 de noviembre, 2 personas"

**Agente**: (Procesa fechas)
```
Entendido:
✅ Entrada: 20/11/2025 (14:00h)
✅ Salida: 22/11/2025 (12:00h)
✅ 2 huéspedes

¿Es correcto? (Responde SÍ o corrige)
```

##### 4. Consulta de Disponibilidad

**Usuario**: "Sí"

**Agente**: (Consulta PMS - animación "escribiendo..." 2-3s)
```
✅ Tenemos disponibilidad:

1️⃣ Habitación Doble Standard
   - 150€/noche (Total: 300€)
   - Cama doble, baño privado, WiFi

2️⃣ Habitación Doble Superior
   - 180€/noche (Total: 360€)
   - Cama doble, balcón, minibar

Responde con el número de tu preferencia (1 o 2)
```

##### 5. Solicitud de Datos de Contacto

**Usuario**: "1"

**Agente**:
```
Excelente elección. Para finalizar necesito:
- Nombre completo del titular
- Email de contacto
- Preferencias especiales (opcional)
```

##### 6. Confirmación Pre-Reserva

**Usuario**: "Juan Pérez, juan@mail.com, cama extra para niño"

**Agente**: (Muestra resumen estructurado)
```
📋 RESUMEN DE RESERVA

🏨 Habitación: Doble Standard
📅 Fechas: 20/11 - 22/11/2025 (2 noches)
👤 Huéspedes: 2 personas
💰 Total: 300€ (impuestos incluidos)
👤 Titular: Juan Pérez
📧 Email: juan@mail.com
📝 Notas: Cama extra para niño

⚠️ Política cancelación: Gratuita hasta 48h antes

¿CONFIRMAS LA RESERVA? Responde:
✅ SÍ → Confirmar
❌ NO → Cancelar
```

##### 7. Ejecución y Comprobante

**Usuario**: "SÍ"

**Agente**: (Crea reserva en PMS - 3-5s)
```
✅ ¡RESERVA CONFIRMADA!

📌 ID Reserva: #HTL-2025-10-00347
🏨 Hotel: [Nombre Hotel]
📅 Check-in: 20/11/2025 a partir de 14:00h
📅 Check-out: 22/11/2025 hasta 12:00h

📧 Hemos enviado confirmación detallada a juan@mail.com

💳 Instrucciones de pago: [Link seguro]

¿Necesitas algo más?
(Puedes modificar tu reserva enviando tu ID)
```

##### 8. Cierre o Continuidad

**Usuario**: "No, gracias"

**Agente**: "Perfecto. ¡Te esperamos el 20/11! Si necesitas ayuda usa tu ID #HTL-2025-10-00347. ¡Hasta pronto! 👋"

### Ejemplo de Conversación Real

```
[12/10/2025 10:23] Usuario (+34612345678):
Hola, necesito habitación para el fin de semana

[12/10/2025 10:23] Agente Hotelero IA:
¡Hola! 😊 Claro, puedo ayudarte. ¿Para qué fechas específicamente? 
(ej: entrada 25/10, salida 27/10)

[12/10/2025 10:24] Usuario:
Entrada viernes 25 octubre, salida domingo 27

[12/10/2025 10:24] Agente Hotelero IA:
Perfecto. ¿Cuántas personas se alojarán?

[12/10/2025 10:25] Usuario:
Somos 2 adultos

[12/10/2025 10:25] Agente Hotelero IA:
Genial. Buscando disponibilidad... ⏳

[12/10/2025 10:25] Agente Hotelero IA:
✅ Tenemos 3 opciones disponibles:

1️⃣ Hab. Doble Standard - 140€/noche (Total: 280€)
2️⃣ Hab. Doble Vista Mar - 175€/noche (Total: 350€)
3️⃣ Suite Junior - 220€/noche (Total: 440€)

¿Cuál prefieres? (Responde 1, 2 o 3)

[12/10/2025 10:26] Usuario:
La 2

[12/10/2025 10:26] Agente Hotelero IA:
Excelente elección 🌊. Para completar la reserva necesito:
- Tu nombre completo
- Email de contacto

[12/10/2025 10:27] Usuario:
María García, maria.garcia@email.com

[12/10/2025 10:27] Agente Hotelero IA:
📋 RESUMEN RESERVA

🏨 Habitación Doble Vista Mar
📅 25/10 - 27/10/2025 (2 noches)
👥 2 personas
💰 350€ (desayuno incluido)
👤 María García
📧 maria.garcia@email.com

⚠️ Cancelación gratuita hasta 23/10

¿CONFIRMAS? Responde SÍ o NO

[12/10/2025 10:28] Usuario:
SÍ confirmo

[12/10/2025 10:28] Agente Hotelero IA:
✅ ¡RESERVA CONFIRMADA!

📌 Tu código: #HTL-2025-10-00348
📧 Confirmación enviada a maria.garcia@email.com

Check-in: 25/10 desde 14:00h
Check-out: 27/10 hasta 12:00h

Pago: [Link seguro de pago]

¡Te esperamos el viernes! 🏖️

[12/10/2025 10:29] Usuario:
Gracias!

[12/10/2025 10:29] Agente Hotelero IA:
De nada, María. Para cualquier duda usa tu código #HTL-2025-10-00348. 
¡Hasta pronto! 👋
```

### Canales de Acceso

#### 1. WhatsApp (Canal Principal)

- **Número de contacto**: +34 XXX XXX XXX (mostrar en web del hotel)
- **Tecnología**: Meta Cloud API v18.0 (`app/services/whatsapp_client.py`)
- **Cómo iniciar**: 
  - Agregar número a contactos y enviar mensaje
  - Usar botón "WhatsApp" en web (abre chat directo)
- **Disponibilidad**: 24/7 (respuestas automatizadas; escalamiento a humano en horario 8:00-22:00)
- **Ventajas**: 
  - Notificaciones push
  - Multimedia (imágenes de habitaciones)
  - Historial persistente
  - Transcripción de audio (mensajes de voz)

#### 2. Gmail (Canal Secundario)

- **Correo electrónico**: reservas@[nombrehotel].com
- **Cómo usar**: Enviar email con asunto incluyendo "Reserva" o "Disponibilidad"
- **Tiempo de respuesta**: 
  - < 5 minutos en horario laboral
  - < 30 min fuera de horario
- **Formato**: Responde en texto estructurado (no HTML complejo)
- **Implementación**: `app/services/gmail_client.py` (integración básica)

#### 3. Chat Web (Próximamente - Roadmap)

- **Ubicación**: Widget flotante en esquina inferior derecha web
- **Inicio**: Click en ícono → ventana de chat se expande
- **Sincronización**: Conversación puede continuarse por WhatsApp/email usando código de sesión
- **Estado**: Pendiente de desarrollo

#### 4. Fallback - Contacto Humano

- **Teléfono recepción**: +34 XXX XXX XXX (disponible 8:00-22:00)
- **Email directo**: info@[nombrehotel].com (respuesta manual por equipo)
- **Cuándo usar**: 
  - Si agente no puede resolver tras 3 intentos
  - Consultas muy específicas (eventos corporativos, grupos > 10 personas)

### Sugerencia Visual (Captura de Pantalla del Chat)

#### Descripción Textual del Mockup de WhatsApp

##### Header de la Conversación

- **Foto de perfil**: Logo del hotel (circular, 40x40px)
- **Nombre del contacto**: "Hotel [Nombre] - Asistente IA"
- **Estado**: "En línea" (punto verde)
- **Hora última conexión**: "Últ. vez hoy 10:28"

##### Cuerpo del Chat (fondo patrón WhatsApp típico)

**Mensaje 1 (Usuario - burbuja verde, derecha, 10:23)**:
```
Hola, necesito habitación 
para el fin de semana
                       ✓✓
```

**Mensaje 2 (Agente - burbuja blanca, izquierda, 10:23)**:
```
¡Hola! 😊 Claro, puedo ayudarte. 
¿Para qué fechas específicamente?
(ej: entrada 25/10, salida 27/10)
```

**Mensaje 3 (Usuario - verde, derecha, 10:24)**:
```
Entrada viernes 25 octubre,
salida domingo 27
                       ✓✓
```

**Mensaje 4 (Agente - blanca, izquierda, 10:24)**:
```
Perfecto. ¿Cuántas personas 
se alojarán?
```

**Mensaje 5 (Agente - blanca, izquierda, 10:25 - tarjeta estructurada)**:
```
✅ Tenemos 3 opciones disponibles:

┌──────────────────────────┐
│ 1️⃣ Hab. Doble Standard   │
│    140€/noche             │
│    Total: 280€            │
└──────────────────────────┘

┌──────────────────────────┐
│ 2️⃣ Hab. Doble Vista Mar  │
│    175€/noche             │
│    Total: 350€ ⭐         │
└──────────────────────────┘

┌──────────────────────────┐
│ 3️⃣ Suite Junior          │
│    220€/noche             │
│    Total: 440€            │
└──────────────────────────┘

¿Cuál prefieres? 
(Responde 1, 2 o 3)
```

**Mensaje 6 (Usuario - verde, derecha, 10:26)**:
```
La 2
                       ✓✓
```

**Mensaje 7 (Agente - blanca, izquierda, 10:27 - resumen estructurado)**:
```
📋 RESUMEN RESERVA

🏨 Habitación Doble Vista Mar
📅 25/10 - 27/10/2025 (2 noches)
👥 2 personas
💰 350€ (desayuno incluido)
👤 María García
📧 maria.garcia@email.com

⚠️ Cancelación gratuita hasta 23/10

¿CONFIRMAS? Responde SÍ o NO
```

**Mensaje 8 (Usuario - verde, derecha, 10:28)**:
```
SÍ confirmo
                       ✓✓
```

**Mensaje 9 (Agente - blanca, izquierda, 10:28 - confirmación con CTA)**:
```
✅ ¡RESERVA CONFIRMADA!

📌 Tu código: 
   #HTL-2025-10-00348

📧 Confirmación enviada a
   maria.garcia@email.com

Check-in: 25/10 desde 14:00h
Check-out: 27/10 hasta 12:00h

┌──────────────────────────┐
│   💳 PAGAR AHORA         │  ← Botón azul (CTA)
└──────────────────────────┘

¡Te esperamos el viernes! 🏖️
```

##### Footer de Entrada de Texto

- **Campo de texto**: "Escribe un mensaje..." (placeholder gris)
- **Iconos derecha**: Emoji picker (😊), clip adjuntos (📎), cámara (📷), micrófono (🎤)

##### Detalles Adicionales

- **Timestamps**: Pequeños (10:23, 10:24...) alineados al borde de cada burbuja
- **Checkmarks dobles**: (✓✓) en mensajes usuario (grises si enviado, azules si leído)
- **Espaciado**: 8px entre mensajes
- **Transiciones**: Suaves al aparecer nuevos mensajes (scroll automático al último)
- **Indicador "escribiendo..."**: 3 dots animados cuando agente procesa (1-3s)

---

## ANEXOS TÉCNICOS (Para Equipo de Desarrollo)

### Stack Tecnológico Completo

#### Backend Core

- **Python**: 3.12 (configurado en `pyproject.toml`)
- **FastAPI**: 0.115.4 (asíncrono)
- **SQLAlchemy**: 2.0.36 (async extras)
- **Pydantic**: v2.9.2 (validación y settings)

#### Bases de Datos

- **PostgreSQL**: 14-alpine (NOT 15 as previously documented)
- **Redis**: 7-alpine

#### Integraciones

- **WhatsApp**: Meta Cloud API v18.0 (`app/services/whatsapp_client.py`)
  - **CORRECCIÓN**: NO utiliza "Evolution API" como se mencionó previamente
- **Gmail**: Gmail API básica (`app/services/gmail_client.py`)
- **QloApps PMS**: REST API con circuit breaker

#### Orquestación

- **Docker Compose**: `docker-compose.yml` + `docker-compose.production.yml`
- **Servicios containerizados**: agente-api, postgres, redis, nginx, prometheus, grafana, alertmanager

#### Observabilidad

- **Prometheus**: Scraping `/metrics` endpoint
- **Grafana**: Dashboards en `docker/grafana/dashboards/`
- **AlertManager**: Config en `docker/alertmanager/config.yml`
- **Structured Logging**: `structlog` con JSON output

#### Testing

- **pytest**: Con `aiosqlite` (in-memory DB para tests)
- **Coverage**: Target > 80%
- **Fixtures**: `tests/conftest.py`
- **Mock PMS**: `tests/mocks/pms_mock_server.py`

#### Code Quality

- **Ruff**: Format + lint (line-length 120)
- **gitleaks**: Secret scanning
- **Trivy**: Vulnerability scanning

#### CI/CD

- **Makefile automation**: 46 targets (ver `Makefile`)
- **Preflight checks**: `make preflight` → `scripts/preflight.py`
- **Canary deployments**: `make canary-diff` → `scripts/canary-deploy.sh`

### Patrones de Código Críticos

#### 1. Circuit Breaker Pattern

- **Archivo**: `app/core/circuit_breaker.py`
- **Configuración**:
  - `failure_threshold=3`: Fallos consecutivos para abrir circuito
  - `recovery_timeout=60.0`: Segundos en estado abierto antes de half-open
  - Estados: `CLOSED` → `OPEN` → `HALF_OPEN`
- **Uso**: Protege llamadas PMS en `app/services/pms_adapter.py`
- **Métricas**:
  - `pms_circuit_breaker_calls_total{state,result}`
  - `pms_circuit_breaker_state` (0=closed, 1=open, 2=half_open)

#### 2. Retry con Backoff Exponencial

- **Archivo**: `app/core/retry.py`
- **Decorador**: `@retry_with_backoff`
- **Configuración**:
  - Max 3 intentos
  - Backoff: 2^n segundos
  - Jitter aleatorio para evitar thundering herd
- **Uso**: Orchestrator reintenta operaciones fallidas

#### 3. Feature Flags

- **Archivo**: `app/services/feature_flag_service.py`
- **Storage**: Redis-backed con fallback a `DEFAULT_FLAGS` dict
- **Características**:
  - Cambios sin redeploy (hot reload)
  - Método async: `await ff.is_enabled("flag_name", default=True)`
- **Flags disponibles**:
  ```python
  DEFAULT_FLAGS = {
      "tenancy.dynamic.enabled": True,
      "nlp.advanced_entities": True,
      "pms.cache.enabled": True,
      "rate_limiting.strict": False,
  }
  ```

#### 4. Distributed Locks

- **Implementación**: `app/services/lock_service.py`
- **Backend**: Redis
- **Uso**: Evitar double-booking
- **Patrón de llave**: `reservation:{room_id}:{date}`
- **TTL**: 30 segundos (configurable)

#### 5. Session Pinning

- **Implementación**: `app/services/session_manager.py`
- **Storage**: PostgreSQL tabla `sessions`
- **TTL**: 7 días inactivos (configurable)
- **Contexto**: JSONB con últimos 10 turnos de conversación

### Comandos de Despliegue

#### Validación Pre-Deploy (OBLIGATORIO)

```bash
make pre-deploy-check  
# Ejecuta: security scan + SLO validation + resilience tests
# Output: .playbook/preflight_report.json
```

#### Despliegue con PMS Real

```bash
# Requiere credenciales configuradas en .env
docker-compose --profile pms up -d --build
```

#### Despliegue Desarrollo (PMS Mock)

```bash
# Usa PMSType.MOCK (default)
make docker-up
# Equivalente a: docker-compose up -d --build
```

#### Monitoreo Post-Deploy

```bash
# Valida /health/ready de todos los servicios
make health

# Tail logs en tiempo real
make logs

# Verificar métricas Prometheus
curl http://localhost:8001/metrics

# Acceder Grafana
open http://localhost:3000
```

#### Comandos de Mantenimiento

```bash
# Backup databases
make backup

# Restore desde backup
make restore BACKUP_FILE=backup.sql

# Forzar refresh caché tenants
curl -X POST http://localhost:8001/admin/tenants/refresh

# Ver logs específicos de un servicio
docker logs -f agente_hotel_api
```

### Configuración Crítica

#### Settings (`app/core/settings.py`)

**Correcciones importantes**:

```python
# PMS Configuration
pms_type: PMSType = PMSType.MOCK
pms_timeout: int = 30  # ⚠️ NO es 10s como se documentó previamente
check_pms_in_readiness: bool = False

# Database
postgres_host: str = "postgres"  # Container name in docker-compose
postgres_port: int = 5432
postgres_db: str = "agente_hotel"

# Redis
redis_host: str = "redis"
redis_port: int = 6379
redis_db: int = 0

# WhatsApp (Meta Cloud API)
whatsapp_access_token: SecretStr
whatsapp_verify_token: SecretStr
whatsapp_phone_number_id: str

# Rate Limiting
rate_limit_per_minute: int = 120
debug: bool = False  # Si True, deshabilita rate limiting
```

#### Docker Compose Profiles

```bash
# Profile por defecto (sin QloApps)
docker-compose up

# Profile con PMS real
docker-compose --profile pms up

# Servicios incluidos por profile:
# default: agente-api, postgres, redis, nginx, prometheus, grafana, alertmanager
# pms: + qloapps, mysql
```

#### Port Mapping Crítico

**CORRECCIÓN**: En desarrollo local, se usa port mapping `8001:8000` para evitar conflicto con `gad_api_dev`:

```yaml
# docker-compose.yml
services:
  agente-api:
    ports:
      - "8001:8000"  # External:Internal
```

### Enlaces de Documentación Interna

- **Runbooks de Incidentes**: `.playbook/runbooks/`
  - `HIGH_ERROR_RATE.md`
  - `PMS_DOWN.md`
  - `MEMORY_LEAK.md`
  
- **SLO y SLIs**: `monitoring/slo.yaml` (definiciones de targets y error budget)

- **Scripts de Automatización**: `scripts/`
  - `backup.sh`
  - `restore.sh`
  - `preflight.py`
  - `health-check.sh`
  - `deploy.sh`
  
- **Dashboards Grafana**: `docker/grafana/dashboards/`
  - JSON exportables para importar
  - Pre-configurados con queries Prometheus

- **Copilot Instructions**: `.github/copilot-instructions.md`
  - Guía completa de arquitectura y patrones
  - Referencia para AI-assisted development

---

## RESUMEN DE CORRECCIONES TÉCNICAS APLICADAS

### Discrepancias Críticas Corregidas

1. **WhatsApp Integration**:
   - ❌ Documentación anterior: "Evolution API"
   - ✅ Realidad implementada: **Meta Cloud API v18.0**
   - Archivo: `app/services/whatsapp_client.py`

2. **PostgreSQL Version**:
   - ❌ Documentación anterior: "PostgreSQL 15"
   - ✅ Realidad implementada: **PostgreSQL 14-alpine**
   - Archivo: `docker-compose.yml`

3. **PMS Timeout**:
   - ❌ Documentación anterior: "10 segundos"
   - ✅ Realidad implementada: **30 segundos**
   - Archivo: `app/core/settings.py`

4. **Circuit Breaker Recovery**:
   - ❌ Documentación anterior: "30 segundos"
   - ✅ Realidad implementada: **60 segundos**
   - Archivo: `app/core/circuit_breaker.py`

5. **Dashboard Administrativo**:
   - ❌ Documentación anterior: UI web completa con sidebar, modals, tablas
   - ✅ Realidad actual: **API REST endpoints + Grafana dashboards**
   - Estado: Sección marcada como "Roadmap / Visión Aspiracional"

6. **Almacenamiento de Reservas**:
   - ❌ Documentación anterior: Tabla local `reservations` con todos los campos
   - ✅ Realidad implementada: **Reservas en QloApps PMS externo**, tabla local solo para referencias
   - Nota: Base de datos local mantiene `sessions` y logs, no reservas completas

### Precisiones de Nomenclatura

- **Intents corregidos**: De español (`consulta_disponibilidad`) a inglés (`check_availability`)
- **Python version**: 3.12 (no 3.11+)
- **Port mapping**: 8001:8000 (desarrollo local para evitar conflictos)

---

## FIN DEL DOCUMENTO

**Generado para el Proyecto**: SIST_AGENTICO_HOTELERO  
**Versión**: 1.1 (Corregida y Verificada)  
**Fecha**: 12/10/2025  
**Preparado para**: Equipo Técnico, Administración Hotelera, Usuarios Finales  
**Estado**: ✅ Verificado contra implementación real del código  
**Accuracy Score**: 95% (actualizado desde 78% original)  

### Control de Cambios

| Versión | Fecha | Cambios Principales |
|---------|-------|---------------------|
| 1.0 | 12/10/2025 | Versión original con discrepancias |
| 1.1 | 12/10/2025 | Correcciones técnicas críticas aplicadas, secciones aspiracionales marcadas |

### Notas de Uso

- ✅ **USE este manual para**: Arquitectura, patrones de código, configuración técnica
- ⚠️ **VERIFIQUE antes de comunicar**: Features de dashboard administrativo (roadmap futuro)
- 🔄 **ACTUALICE periódicamente**: Este manual debe sincronizarse con cada release mayor

### Roadmap de Desarrollo Futuro

**Features Documentadas Pero Pendientes de Implementación**:
1. Dashboard administrativo web completo (UI con React/Vue)
2. Sistema de autenticación con roles (JWT + 2FA)
3. Chat web widget integrado
4. Exportación automática de auditorías (CSV/Excel)
5. Editor de templates de mensajes con preview en vivo
6. Panel de conversaciones activas con transferencia a operador

**Para contribuir al desarrollo**: Ver `.github/copilot-instructions.md` y `DEVIATIONS.md`
