# Playbook Universal de Finalización - Propósito, Uso y Gobernanza

## 1. Resumen Ejecutivo
El Playbook Universal acelera la transición de "casi terminado" a producción **con seguridad, reversibilidad y métricas objetivas**. Sustituye decisiones ad-hoc y perfeccionismo por un marco repetible basado en modos operativos (A/B/C) alineados al riesgo.

## 2. Objetivo Central
Establecer un proceso claro, mínimamente suficiente y escalable para lanzar valor temprano y frecuente sin comprometer seguridad, datos ni observabilidad.

## 3. Problemas que Resuelve
| Problema | Manifestación | Efecto | Solución del Playbook |
|----------|--------------|--------|------------------------|
| Perfeccionismo | "Falta una última mejora" | Retrasos | Modos + freeze de scope + triage|
| Scope creep | Features añadidas tardías | Desviación | Alarmas Amarilla/Roja |
| Falta de criterios | Debates subjetivos | Parálisis | Risk score + gates |
| Rollback débil | Miedo a desplegar | Lento time-to-value | Reversibilidad obligatoria |
| Falta observabilidad | Lanzar a ciegas | Incidentes largos | Dashboards + alertas mínimas |

## 4. Alcance y Fuera de Alcance
Incluye: fase final (80–90% completado) → release + monitoreo + post-lanzamiento corto.
Excluye: ideación, arquitectura primaria, descubrimiento de producto, roadmap > V1.2.

## 5. Audiencias y Roles
| Rol | Accountability Principal | En Fase Preflight | En Go/No-Go | Post-Deploy |
|-----|--------------------------|------------------|------------|-------------|
| Producto/PO | Valor y alcance | Define alcance final | Firma | Métricas negocio |
| Tech Lead | Calidad técnica | Coordina readiness | Firma | Validación técnica |
| SRE/DevOps | Operabilidad | Revisa observabilidad | Firma | Monitoreo / rollback |
| QA | Calidad funcional | Valida criterios | Advisory | Validaciones cruzadas |
| Seguridad | Riesgos críticos | Gates security | Veto si FAIL | Revisión findings |
| Release Manager | Orquestación | Controla checklist | Documenta decisión | Post-mortem |

## 6. Flujo de Uso (8 Pasos)
1. Seleccionar modo (A rapidez / B equilibrio / C fiabilidad).
2. Completar `project_config.yml` (metadatos, SLOs, contactos, flags críticos).
3. Ejecutar preflight → genera `preflight_report.json`.
4. Calcular risk_score y revisar gates (security/data/perf/obs).
5. Reunión Go/No-Go: firmar o escalar bloqueos.
6. Despliegue (canary / blue-green / estándar) con monitoreo continuo.
7. Reportes 1h / 4h / 24h, aplicar rollback si se cruzan umbrales.
8. Cierre: post-deploy report + post-mortem si hubo incidente (Sev1/2 o breach SLO).

## 7. Principios Rectores
- Shipping > Perfección (pero no sin seguridad y retorno rápido a estable).
- Métricas > Opiniones (todos los Go/No-Go sustentados en datos).
- Reversibilidad Primero (no hay release sin rollback probado <10 min).
- Observabilidad By Design (métricas + logs + correlación desde preflight).
- Simplicidad Forzada (cada sección debe justificar su utilidad tangible).

## 8. Modos Operativos (Resumen)
| Modo | Uso | Rigor | Estrategia Release | Umbral risk_score GO | Rollback Trigger Ejemplo |
|------|-----|-------|--------------------|----------------------|--------------------------|
| A Velocidad | MVP, beta interna | Ligero | Canary rápido 10→50→100% | ≤60 | error_rate>2% 10m |
| B Equilibrio | Core estándar | Medio | Canary 5→25→100% | ≤50 | error_rate>1% 10m |
| C Fiabilidad | Alta criticidad | Alto | Blue-green + validación | ≤40 | error_rate>0.5% 10m |

## 9. Risk Score (Simplificado)
`risk_score = 100 - (readiness*W1 + mvp*W2 + security_gate*W3) + change_complexity_penalty`

Pesos por modo:
- A: W1=0.6 W2=0.4 W3=0.1
- B: W1=0.5 W2=0.5 W3=0.2
- C: W1=0.4 W2=0.4 W3=0.4

## 10. Métricas Clave de Adopción (Meta-KPIs)
- Change Failure Rate ↓
- Time to Production desde “feature complete” ↓ 40–60%
- MTTR post-lanzamiento ↓ 30–50%
- % Releases con preflight PASS 1er intento ↑
- % Rollbacks < 2–5% según modo

## 11. Gobernanza y Cambios
- Versionado semántico del playbook: `docs/playbook/CHANGELOG.md`.
- Cambios mayores requieren mini-RFC (`docs/playbook/rfc/YYMMDD-id.md`).
- Excepciones: etiqueta `governance-exception`, caducan en 30 días.
- Auditoría trimestral: métricas de adopción + revisión de umbrales.

## 12. Integración CI/CD (Mínimos)
Jobs esperados:
- `preflight` (genera JSON y falla si blocking)
- `security` (SAST/SCA + secrets)
- `perf` (k6 smoke / load p95 & error)
- `deploy_canary` (estrategia controlada)
- `guardrail` (watch metrics + rollback auto)

## 13. Plantillas Clave
Ubicación sugerida:
```
.playbook/
  project_config.yml
  preflight_report.json
  rollback_runbook.json
  launch_decision.yml
```
GitHub Actions: `.github/workflows/deploy_with_gates.yml`

## 14. Rollback (Requisitos Mínimos)
- Tiempo objetivo < 10 min
- Procedimiento probado en staging / QA
- Validaciones: health, p95, error_rate, integridad datos
- Estrategia fallback alterna (ej. escala versión estable + desactiva flags)

## 15. Antipatrones a Vigilar
| Antipatrón | Señal | Acción |
|------------|-------|--------|
| “Solo un ajuste más” | >3 micro cambios día  | Activar alarma amarilla |
| Perfeccionismo UX | PRs sólo cosmética | Congelar cambios no críticos |
| Sin rollback ensayado | No existe runbook | Bloquear release |
| Scope creep tardío | Features fuera backlog | Reforzar freeze |

## 16. Alineación con Estándares
- DORA: lead time, failure rate, MTTR, frequency
- SRE: SLO, error budget, burn rate
- OWASP: controles base (Top10/ASVS nivel 1–2)
- Seguridad: SBOM, gestión de secretos, escaneo contínuo

## 17. Métricas Técnicas Base (Por Feature)
| Métrica | Por qué | Evita |
|---------|--------|-------|
| latency_p95 | UX y SLO | Degradación silenciosa |
| error_rate | Salud funcional | Falsos “OK” |
| fallback_ratio (NLP) | Calidad semántica | Respuestas pobres invisibles |
| throughput_rps | Saturación | Falta capacidad|
| retries_total | Ruido externo | Circuit breaker tardío |

## 18. Cadencia Recomendada
| Cadencia | Actividad | Owner |
|----------|----------|-------|
| Diario | Revisar p95/error/fallback | SRE |
| Semanal | Grooming flags y scope | Tech Lead |
| Quincenal | Ajuste thresholds | SRE + Producto |
| Mensual | Auditoría adopción playbook | Release Manager |
| Trimestral | Revisión mayor / RFCs | Comité Técnico |

## 19. FAQ Resumido
- ¿Sin staging? → Crear entorno mínimo o blue-green de baja exposición.
- ¿Security FAIL? → No-Go salvo override ejecutivo explícito.
- ¿Dudas en risk_score? → Elegir canary y reforzar monitoreo.
- ¿Rollback no probado? → Bloqueo inmediato.

## 20. Evolución del Documento
Registrar modificaciones significativas y su impacto. Mantener un backlog de mejoras del playbook.

---
**Versión:** 1.0 (Inicial incorporación proyecto Agente Hotelero)  
**Próxima Revisión Recomendada:** +30 días o tras primer release bajo el framework.
