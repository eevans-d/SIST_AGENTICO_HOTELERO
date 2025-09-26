# Working Agreement - Equipo Agente Hotelero

## Objetivo
Maximizar foco, minimizar re-trabajo y evitar expansiones no controladas del alcance.

## Reglas de Foco
- Máx 1 epic activa en paralelo (salvo hotfix crítico).
- WIP por persona: 1 (feature) + 1 (pequeña tarea <1h) como máximo.
- Scope freeze tras aprobar preflight para release.

## Reuniones
- Daily (<=10 min): Ayer / Hoy / Bloqueos / Riesgos.
- Go/No-Go: sólo para decisiones de release (ver playbook), no para refinar detalles.
- Retro ligera: quincenal (15 min) enfocada en fricción operativa.

## Comunicación
- Canales sincronizados: PR comentarios / issues / runbooks.
- Nada de decisiones sólo en chat: registrar en issue o decision record.

## Flags y Experimentos
- Todo experimento nuevo requiere flag + plan de expiración.
- Flags sin uso 30 días => candidatos a retirada (issue automático).

## Gestión de Riesgos
- Riesgo detectado (latencia, error rate) > umbral => etiqueta `risk-hot` + evaluación inmediata.
- Incidente Sev1/2 => post-mortem dentro de 48h.

## Calidad y Seguridad
- Ningún merge a `main` sin CI verde.
- Umbrales smoke fallan => bloquea release.
- Secrets expuestos => rotación inmediata + revisión de historial.

## Resolución de Conflictos
1. Intento directo entre involucrados.
2. Escalación a Tech Lead.
3. Escalación a Product/SRE según naturaleza.

## Revisión y Vigencia
Este acuerdo se revisa cada 30 días o tras un incidente mayor.
