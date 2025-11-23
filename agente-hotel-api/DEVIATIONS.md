# Desviaciones del Plan Original

## GA-01: Ruta del Proyecto

- **Desviación:** El proyecto fue creado en `/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api` en lugar de la ruta solicitada `~/ProyectosIA/activos/apis/agente-hotel-api`.
- **Razón:** Restricciones del entorno de ejecución limitan la escritura de archivos al directorio de trabajo `/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO`.
- **Impacto:** Ninguno a nivel funcional. El usuario deberá mover el directorio del proyecto a la ubicación final deseada si es necesario.

## E-04: Implementación de Audio Processing (7 de octubre, 2025)

- **Mejora:** Se implementó respuesta combinada de audio y ubicación para mensajes de voz.
- **Detalles:**
  - Se creó un nuevo tipo de respuesta `audio_with_location` en el Orchestrator.
  - Se añadió soporte en WebhookRouter para manejar este tipo de respuestas.
  - Se implementó un nuevo método en TemplateService para generar contenido combinado.
  - Se modificó el manejo del intent `hotel_location` para responder con audio cuando recibe mensajes de voz.
- **Documentación:** Se actualizó `docs/WHATSAPP_AUDIO_INTEGRATION.md` con detalles de la implementación.
- **Pruebas:** Se crearon pruebas en `tests/unit/test_location_handler.py` y `tests/unit/test_audio_location_webhook.py`.
- **Estado:** Completa y probada; cumple requisitos de la Fase E.4 del proyecto.

## E-04.1: Expansión de Capacidades de Audio (7 de octubre, 2025)

- **Mejora:** Se extendió el soporte de respuestas de audio a más intents del sistema.
- **Detalles:**
  - Se mejoró el manejo del intent `make_reservation` para responder con audio cuando recibe mensajes de voz.
  - Se actualizó el intent `show_room_options` para enviar audio explicativo seguido de opciones interactivas.
  - Se implementó respuesta de audio para el caso fallback por defecto cuando el mensaje original es de voz.
  - Se añadió el tipo de respuesta `audio` con soporte para mensajes de seguimiento (`follow_up`).
- **Mejoras de Resiliencia:**
  - Se implementó manejo de errores robusto para todos los casos de generación de audio.
  - Se añadió degradación elegante en caso de fallo en la generación de audio.
- **Documentación:** Se ha actualizado `docs/AUDIO_RESPONSES.md` con patrones de diseño, implementación y casos de uso.
- **Pruebas:** Creadas pruebas en `tests/unit/test_audio_response_types.py` y `tests/unit/test_audio_follow_up_webhook.py`.
- **Estado:** Completamente implementado y documentado; cumple los requisitos de la Fase E.4.1 del proyecto.

## E-04.2: Extensión de Audio a Intents Adicionales (7 de octubre, 2025)

- **Mejora:** Se extendió el soporte de respuestas de audio a intents adicionales del sistema hotelero.
- **Detalles:**
  - Se añadió soporte de audio para el intent `guest_services` (información sobre servicios para huéspedes).
  - Se implementó respuesta de audio para `hotel_amenities` (amenidades del hotel).
  - Se añadió soporte de audio para `check_in_info` (información sobre proceso de check-in).
  - Se implementó respuesta de audio para `check_out_info` (información sobre proceso de check-out).
  - Se añadió soporte de audio para `cancellation_policy` (política de cancelación).
  - Todos los nuevos intents siguen el patrón consistente: respuesta de audio para mensajes de voz, texto para mensajes escritos.
- **Plantillas:** Se añadieron nuevas plantillas de texto en `TemplateService` para todos los intents nuevos.
- **Patrones:** Se mantiene consistencia en el manejo de errores con degradación elegante a respuestas de texto.
- **Documentación:** Se actualizó `docs/AUDIO_RESPONSES.md` con los nuevos intents y sus comportamientos.
- **Pruebas:** Creadas pruebas exhaustivas en `tests/unit/test_extended_audio_intents.py`.
- **Estado:** Completamente implementado y probado; amplía significativamente la cobertura de respuestas de audio del sistema.

## Refactorización Asíncrona del Adaptador PMS y Corrección de Flujos (22 de noviembre, 2025)

- **Mejora:** Refactorización completa de `PMSAdapter` para usar `async/await` de forma nativa y corrección de flujos de negocio.
- **Detalles:**
  - Se migró `PMSAdapter` y `QloAppsClient` a métodos totalmente asíncronos.
  - Se corrigió el flujo de `late_checkout` en el `Orchestrator` para manejar correctamente las cancelaciones (`deny`, `no`, `cancel`) limpiando el estado de la sesión.
  - Se solucionaron discrepancias de tipos en `pms_adapter.py` y sus dependencias (15 errores de `mypy` resueltos).
  - Se actualizaron los tests de integración (`test_late_checkout_flow.py`) para reflejar la estructura de datos real de la sesión (diccionario en lugar de booleano).
- **Calidad:**
  - `mypy` pasa sin errores en `app/services/pms_adapter.py`.
  - Tests de integración `test_late_checkout_flow.py` pasando (10/10).
- **Estado:** Completo y validado.

## INFRA-01: Configuración de Base de Datos para Supabase (23 de noviembre, 2025)

- **Desviación:** Se deshabilitaron los *prepared statements* en la configuración de `asyncpg` / SQLAlchemy.
- **Razón:** Supabase utiliza `pgbouncer` en modo transacción, lo cual es incompatible con *prepared statements* por defecto en `asyncpg`.
- **Implementación:** Se configuró `statement_cache_size=0` y `prepare_threshold=None` en `app/core/database.py`.
- **Impacto:** Previene errores `DuplicatePreparedStatementError` durante el inicio y operación de la aplicación.

## INFRA-02: Manejo de Métricas Prometheus (23 de noviembre, 2025)

- **Desviación:** Se implementó un patrón "get or create" para la instanciación de métricas Prometheus.
- **Razón:** El cliente de Prometheus lanza errores `Duplicated timeseries` si se intenta re-declarar una métrica que ya existe en el registro global (común durante *hot reloads* o reinicios de componentes).
- **Implementación:** Se crearon wrappers `_get_or_create_*` en `app/services/business_metrics.py` y `app/monitoring/business_metrics.py`.
- **Impacto:** Mayor estabilidad en el reinicio de servicios y durante el desarrollo con *auto-reload*.
