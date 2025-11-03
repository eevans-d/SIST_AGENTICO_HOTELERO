# Estado del Proyecto (29-10-2025)

Esta es la fuente de verdad y "único hilo" sobre la situación actual y próximos pasos.

## Situación actual

- Funcionalidad de envío de imágenes (text_with_image y audio_with_image) estabilizada.
- Suite de integración de imágenes pasando: `tests/integration/test_image_sending.py` ✅
- Cambios relevantes ya comiteados y pusheados a `main`.

## Cambios recientes (resumen)

- Orchestrator
  - Salidas estructuradas para `text`, `text_with_image` y `audio_with_image` (incluye `original_message`).
  - Uso de `nlp_engine.process_text(...)` para alinear con los tests.
  - `get_room_image_url` y `validate_image_url` expuestos a nivel de módulo (facilita patch en tests).
  - Resolución de URL de imagen usando `settings.room_images_base_url` (patchable).
  - Compat audio: usa `transcribe_audio` si está disponible; mapea `transcript`/`text`.
- NLPEngine: agregado shim `process_text()` que delega a `process_message()`.
- AudioProcessor: agregado shim `transcribe_audio()` que delega a `transcribe_whatsapp_audio()`.
- Webhook WhatsApp: manejo de `response_type="text"` añadido.

## Pruebas clave

- Integración imágenes: PASS
  - `tests/integration/test_image_sending.py`
- Spot-check adicional: algunos tests de integración de intents complejos muestran fallos no relacionados a imágenes (ver pendientes).

## Pendientes inmediatos

1) Estabilizar integración `handle_intent_integration`
   - Revisar y ajustar flujos:
     - Creación de reserva: asegurar que se invoque `create_reservation` en estado `creating_reservation`.
     - Generación de QR: exponer `generate_qr_code` en `app.services.orchestrator` (similar a los helpers de imagen) para parcheo en tests.
     - Mensajes de horario comercial: ajustar textos para cumplir asserts de tests.

2) Telemetría opcional
   - Dashboard de Grafana mínimo para `whatsapp_text_image_consolidated_total` (si se decide activar/monitorizar la consolidación).

## Riesgos/Notas

- Librerías opcionales no instaladas (p. ej., fastText, Rasa): el motor NLP corre en modo fallback (esperado en tests). No es bloqueo.
- Mantener `response` en `text_with_image` para compatibilidad con código existente.

## Cómo probar rápido

```bash
# Ejecutar suite de imágenes
cd agente-hotel-api
pytest -q tests/integration/test_image_sending.py

# Spot-check de intents (puede fallar en pendientes)
pytest -q tests/integration/test_handle_intent_integration.py -q
```

## Registro de cambios (último commit relevante)

- Mensaje: "test(image): stabilize image sending tests"
- Rama: `main`

