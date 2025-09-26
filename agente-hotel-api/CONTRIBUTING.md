# CONTRIBUTING - Agente Hotelero IA

Este documento establece cómo colaborar sin introducir desviaciones, deuda innecesaria o scope creep.

## Principios
1. Shipping > Perfección (calidad mínima + reversibilidad garantizada).
2. Observabilidad y Seguridad son no negociables.
3. Cada cambio debe trazar a un issue o decision record.
4. Feature experimental => detrás de feature flag + plan de retiro.
5. Multi-tenant: nunca introducir claves sin namespace si impactan usuario.

## Flujo de Trabajo
1. Crear/usar issue existente (ver `PHASE5_ISSUES_EXPORT.md` o issues en GitHub).
2. Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `perf/` + slug corto (ej: `feat/canary-diff`).
3. PR debe incluir:
   - Resumen negocio / técnico (máx 5 líneas).
   - Checklist de `docs/DOD_CHECKLIST.md` (copiar las relevantes, marcar N/A justificando).
   - Riesgo residual + plan rollback (si aplica).
   - Flags agregados (si hay) + fecha objetivo de remoción.
4. Commits: estilo conventional commits (ej: `feat(nlp): fallback ratio metric`).
5. Aprobaciones: mínimo 1 revisor técnico para cambios de código de servicio; 2 si modifica seguridad, migraciones o build.

## Definition of Ready (DoR)
Un issue NO ingresa a ciclo si falta:
- Objetivo claro (qué valor entrega y a quién).
- Criterios de aceptación verificables.
- Métricas/observabilidad definidas (qué medimos tras deploy).
- Señal de reversibilidad (rollback o flag).
- Riesgos conocidos listados.

## Definition of Done (DoD)
Ver `docs/DOD_CHECKLIST.md` (debe copiarse parcialmente al PR y marcarse).

## Anti‑Patrones (Bloqueos Automáticos)
- "Pequeñas mejoras" sin issue => Rechazado.
- Añadir dependencias pesadas sin justificación escrita => Rechazado.
- Código sin tests mínimos (happy + error) donde aplica => Rechazado.
- Métrica nueva con cardinalidad no evaluada => Revisión requerida.
- Cambio de umbral SLO sin decision record => Rechazado.

## Métricas Internas de Contribución
- Lead time PR (apertura→merge) objetivo < 48h.
- Rollbacks originados por contribución < 2%.
- PRs sin issue vinculado: 0.

## Escalación
Bloqueos >24h escalan a Tech Lead; >48h escalan a SRE / Product según tipo.

## Seguridad
Antes de mergear: ejecutar lint + escaneos (Make targets) si pipeline falla local.

## Contacto
Ver `docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md` para roles y responsabilidades.
