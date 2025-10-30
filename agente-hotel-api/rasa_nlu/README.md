# Rasa NLU (Opcional/Legado)

Esta carpeta contiene configuraciones y datos de ejemplo para entrenar modelos de Rasa NLU.

- No es necesaria para ejecutar la app ni para pasar los tests actuales: el `NLPEngine` funciona en modo fallback cuando no hay modelos.
- Úsalo solo si deseas entrenar/ probar modelos Rasa localmente.
- Si no vas a trabajar con Rasa, puedes ignorar esta carpeta.

## Entrenamiento (opcional)

Requisitos: entorno con Rasa instalado.

```bash
# Ejemplo (ajusta según tu setup)
rasa train --config rasa_nlu/config.yml --domain rasa_nlu/domain.yml --data rasa_nlu/data
```

## Integración con la app

El `NLPEngine` detecta la ausencia de modelos y entra en fallback. Si deseas habilitar modelos reales:
- Configura rutas de modelos en settings/variables de entorno.
- Asegúrate de cargar el agente Rasa y manejar sus dependencias.
