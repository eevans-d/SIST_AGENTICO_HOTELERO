## FASE 3: Cobertura & Resiliencia

Objetivo general: Elevar la robustez del sistema antes de endurecer umbrales de despliegue.

### Metas cuantitativas iniciales
- Cobertura mínima inmediata: 35% (objetivo progresivo hasta 40%).
- Tests críticos de resiliencia añadidos: Circuit Breaker, LockService, SessionManager TTL.
- Tiempos de respuesta P95 no deben aumentar >10% tras incorporación de nuevas capas de verificación.

### Alcances técnicos
1. Circuit Breaker: Verificar transición CLOSED→OPEN ante fallos repetidos y HALF_OPEN→CLOSED tras éxito.
2. Locks de reserva: Asegurar atomicidad (un único lock por rango solapado) y control de extensiones.
3. Sesiones: Validar actualización de sesión sin pérdida de contexto y actualización de métrica `session_active_total`.
4. Umbral de cobertura: Ajustar `--cov-fail-under` a 35 tras confirmar nuevas pruebas verdes.
5. Alerting real: Parametrizar receptores Slack y Email sin credenciales duras.
6. Canary helper: Script para latencia P95 y error rate (Prometheus) para pre-deploy comparativo.
7. Rollback runbook: Procedimiento ≤15min para revertir release staging.
8. Índices DB: Recomendaciones de índices para sesiones y reservas proyectadas.
9. Reporte de progreso: Registrar cobertura y evolución en este documento tras cada incremento ≥2%.

### Riesgos y mitigaciones
- Riesgo: Fluctuación de cobertura por código no instrumentado → Mitigación: excluir tests y mocks del source.
- Riesgo: Flakiness en tests async → Mitigación: evitar sleeps arbitrarios, usar in-memory fakes.
- Riesgo: Falsos positivos de CB → Mitigación: usar excepción específica `RuntimeError` en tests.

### Próximos pasos inmediatos
1. Añadir tests CB y locks (completado).
2. Añadir test SessionManager TTL y métrica.
3. Subir umbral cobertura a 35% cuando se confirme ≥35.
4. Crear script canary y runbook rollback.

### Registro de avances
- Inicialización de la fase: Documento creado (fecha: 2025-11-08)
- Tests Circuit Breaker, LockService y SessionManager TTL: completados
- Alertmanager config templated + script render: completado
- Canary metrics helper script: completado
- Runbook rollback: completado
- Cobertura full suite actual (parcial fallida por dependencias externas): ~22.21% (no subir umbral todavía)
- Cobertura focalizada (solo nuevos tests resiliencia): alta en módulos afectados (100% en `circuit_breaker.py`, 80% `lock_service.py`, mejora parcial en `session_manager.py`)
- Próximo objetivo: aislar suites pesadas (spacy, Postgres) con marcadores para elevar cobertura efectiva unit a ≥35% antes de cambiar `--cov-fail-under`.

---
Mantener este documento actualizado en cada cambio material de resiliencia o cobertura.
