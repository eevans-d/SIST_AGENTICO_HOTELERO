# Especificación Técnica: Agente Recepcionista Hotelero

**Versión:** 1.0
**Fecha:** 2025-09-23
**Estado:** Documento Base Consolidado

## 1. Resumen del Proyecto

### 1.1. Objetivo
Implementar un **Agente Recepcionista Hotelero 24/7** que automatiza la atención al cliente a través de WhatsApp (texto y audio) y Gmail. El sistema está diseñado para integrarse profundamente con un Property Management System (PMS) existente (como QloApps), que actúa como la única fuente de verdad para la gestión de disponibilidad, tarifas y reservas.

### 1.2. Filosofía de Diseño: PMS-Céntrico
La arquitectura se basa en el principio **"PMS Maneja, Agente Comunica"**. El agente no duplica la lógica de negocio del hotel (gestión de inventario, precios, clientes), sino que actúa como una capa de interfaz conversacional inteligente que consume la API del PMS. Este enfoque reduce drásticamente la complejidad y el tiempo de desarrollo.

### 1.3. Stack Tecnológico
- **Backend:** Python 3.12+ con **FastAPI**.
- **Property Management System (PMS):** Integración con **QloApps** (o similar con API REST).
- **Base de Datos (Agente):** **PostgreSQL** con **SQLAlchemy** para almacenar logs, trazas de conversaciones y estados de sesión.
- **Caché y Locks:** **Redis** para cachear respuestas del PMS y gestionar locks distribuidos que evitan el doble-booking.
- **Procesamiento de Lenguaje Natural (NLP):** **Rasa** y/o **spaCy** para la interpretación de intenciones y extracción de entidades.
- **Procesamiento de Audio:** **Whisper** (Speech-to-Text) y **Coqui/eSpeak-NG** (Text-to-Speech).
- **Infraestructura:** **Docker Compose** para orquestar todos los servicios.
- **Proxy Inverso:** **NGINX** para gestionar el tráfico y la seguridad.
- **Monitoreo y Alertas:** Stack de **Prometheus**, **Grafana** y **Alertmanager**.

## 2. Arquitectura General

El sistema está compuesto por varios servicios interconectados, orquestados por Docker Compose:

1.  **Canales de Entrada (WhatsApp/Gmail):** Reciben los mensajes de los clientes.
2.  **Message Gateway (FastAPI):** Un punto de entrada único que normaliza los mensajes de los diferentes canales.
3.  **Orquestador (FastAPI):** El cerebro del agente. Procesa los mensajes, invoca al motor de NLP y al pipeline de audio, y aplica la lógica de negocio.
4.  **PMS Adapter:** Una capa de abstracción que se comunica con la API del PMS (QloApps). Implementa lógica de caché (Redis) y reintentos para robustez.
5.  **PMS (QloApps):** El sistema externo que gestiona el hotel. Es la fuente de verdad.
6.  **Stack de Monitoreo:** Servicios dedicados para la observabilidad del sistema.

## 3. Flujo de Reserva End-to-End

1.  **Consulta:** El cliente envía un mensaje (texto o audio) por WhatsApp, ej: *"¿Tenés lugar para 2 personas del 15 al 17 de diciembre?"*.
2.  **Procesamiento:** El Orquestador recibe el mensaje. Si es audio, lo transcribe con Whisper. El motor NLP identifica la intención (`check_availability`) y las entidades (fechas, huéspedes).
3.  **Consulta al PMS:** El Agente, a través del PMS Adapter, consulta la disponibilidad y precios en la API de QloApps.
4.  **Respuesta al Cliente:** El Agente genera una respuesta en texto (y opcionalmente en audio), ej: *"Sí, tenemos habitación doble disponible por $12,000 la noche. ¿Querés confirmar la reserva?"*.
5.  **Pre-Reserva y Lock:** Si el cliente confirma, el Agente crea un **lock distribuido en Redis** para esa habitación y fechas (con un TTL de 20 min), evitando que otro cliente la reserve simultáneamente.
6.  **Instrucciones de Pago:** El Agente envía las instrucciones para el pago de la seña y solicita el envío del comprobante.
7.  **Confirmación Manual:** El personal del hotel verifica el comprobante en el Dashboard de Staff y hace clic en "Confirmar".
8.  **Confirmación en PMS:** Al recibir la confirmación del staff, el Agente realiza la reserva final en la API de QloApps, libera el lock de Redis y envía el voucher de confirmación al cliente.

## 4. API Endpoints y Webhooks

-   `GET /webhooks/whatsapp`: Endpoint para la verificación del webhook de Meta (WhatsApp).
-   `POST /webhooks/whatsapp`: Recibe los eventos y mensajes de WhatsApp. La firma de la petición (`X-Hub-Signature-256`) se valida con un secreto (`WHATSAPP_APP_SECRET`) para seguridad.
-   `GET /admin/dashboard`: Sirve el dashboard web para el personal del hotel.
-   `GET /admin/dashboard-data`: API interna que provee datos en tiempo real al dashboard.
-   `POST /admin/confirm-reservation/{id}`: Endpoint que el staff utiliza para confirmar una reserva tras verificar el pago.
-   `GET /health/live` y `GET /health/ready`: Endpoints de salud para monitoreo. `ready` verifica la conectividad con servicios externos como el PMS y la base de datos.
-   `GET /metrics`: Expone métricas detalladas en formato Prometheus.

## 5. Seguridad, Robustez y Observabilidad

-   **Seguridad de Webhooks:** Las peticiones de WhatsApp se validan mediante una firma HMAC-SHA256.
-   **Rate Limiting:** Se aplica limitación de peticiones (usando SlowAPI y Redis) a los endpoints públicos para prevenir abusos.
-   **Circuit Breaker:** El PMS Adapter implementa un patrón de Circuit Breaker para evitar sobrecargar al PMS si este presenta fallos, mejorando la resiliencia del agente.
-   **Observabilidad Avanzada:** El sistema expone métricas detalladas para Prometheus, incluyendo latencia de la API, tasa de errores, estado del Circuit Breaker y métricas de negocio. Se proveen dashboards de Grafana pre-configurados y un sistema de alertas con Alertmanager.

## 6. Infraestructura y Despliegue (Docker)

-   **Orquestación:** Todo el stack (Agente, PMS, Bases de Datos, Redis, NGINX, Monitoreo) se define y gestiona a través de `docker-compose.yml`.
-   **Redes:** Se utilizan redes de Docker separadas (`frontend_network` y `backend_network`) para aislar los componentes y mejorar la seguridad.
-   **Automatización:** Se proporciona un `Makefile` con comandos para simplificar operaciones comunes como `make docker-up`, `make health` y `make backup`.
-   **Configuración:** La configuración se maneja exclusivamente a través de variables de entorno, siguiendo las mejores prácticas de 12-Factor App. Se provee un archivo `.env.example` como plantilla.
