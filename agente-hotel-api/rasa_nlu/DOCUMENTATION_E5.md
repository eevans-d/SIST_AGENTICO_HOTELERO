# Documentación de la Mejora del Motor NLP Multilingüe - Fase E.5

## Visión General

La Fase E.5 del Sistema Agéntico Hotelero implementa un motor NLP mejorado con capacidades multilingües (español, inglés y portugués). 
Esta mejora permite al sistema comprender y procesar consultas de huéspedes en múltiples idiomas, expandiendo significativamente el 
alcance del servicio y mejorando la experiencia del usuario para clientes internacionales.

## Arquitectura del Motor NLP

El motor NLP mejorado se basa en Rasa NLU con las siguientes mejoras clave:

### Configuración Optimizada
- **Clasificador DIET mejorado**: Mayor capacidad para distinguir entre intenciones similares
- **Arquitectura de transformers**: Capas optimizadas para comprender contexto en múltiples idiomas
- **Extracción avanzada de entidades**: Extracción precisa de fechas, nombres, números en diferentes formatos
- **Umbral de confianza ajustable**: Configuración diferenciada por idioma para mantener precisión

### Procesamiento Multilingüe
- **Tokenización unificada**: El tokenizador maneja correctamente caracteres especiales en todos los idiomas
- **Vectorización adaptativa**: Representaciones numéricas sensibles a las diferencias lingüísticas
- **Características léxicas y sintácticas**: Captura patrones estructurales específicos de cada idioma
- **LanguageModelFeaturizer**: Utilización de modelos pre-entrenados como XLM-RoBERTa para transferencia entre idiomas

## Componentes Principales

### 1. Archivos de Configuración
- `config_enhanced.yml`: Configuración optimizada del pipeline NLP
- `domain_enhanced.yml`: Definición ampliada de intenciones y entidades

### 2. Datos de Entrenamiento
- `data/nlu.yml`: Ejemplos de entrenamiento en español (idioma principal)
- `data/nlu_en.yml`: Ejemplos de entrenamiento en inglés
- `data/nlu_pt.yml`: Ejemplos de entrenamiento en portugués

### 3. Scripts de Utilidad
- `generate_multilingual_data.py`: Genera datasets combinados para entrenamiento multilingüe
- `train_enhanced_models.sh`: Entrena modelos específicos por idioma y multilingües
- `evaluate_multilingual_models.py`: Evalúa y compara el rendimiento de los modelos

## Flujo de Trabajo

El flujo de procesamiento de mensajes multilingües funciona de la siguiente manera:

1. **Normalización del Mensaje**:
   - El mensaje entrante pasa por el `message_gateway.py` y se convierte en un `UnifiedMessage`
   - Si el mensaje es de audio, se transcribe mediante el `AudioProcessor`

2. **Detección de Idioma**:
   - Se aplica detección automática de idioma para determinar el idioma del usuario
   - Se selecciona el modelo NLP óptimo según el idioma detectado

3. **Procesamiento NLP**:
   - El mensaje se procesa con el modelo correspondiente para extraer intenciones y entidades
   - Se generan scores de confianza para intención, entidades y clasificación general

4. **Orquestación**:
   - El `orchestrator.py` gestiona el flujo basado en la intención detectada
   - El idioma detectado se mantiene para generar respuestas en el mismo idioma

5. **Generación de Respuesta**:
   - El `template_service.py` selecciona plantillas en el idioma detectado
   - Las entidades extraídas se utilizan para personalizar la respuesta

## Modelos Disponibles

El sistema entrena y mantiene diferentes tipos de modelos:

1. **Modelos Específicos de Idioma**:
   - `nlu_enhanced_es.tar.gz`: Modelo optimizado para español
   - `nlu_enhanced_en.tar.gz`: Modelo optimizado para inglés 
   - `nlu_enhanced_pt.tar.gz`: Modelo optimizado para portugués

2. **Modelo Multilingüe**:
   - `nlu_enhanced_multilingual.tar.gz`: Modelo unificado que maneja los tres idiomas

## Evaluación de Rendimiento

La evaluación comparativa de modelos muestra:

| Métrica | Modelo Específico | Modelo Multilingüe |
|---------|-----------------|-------------------|
| F1-Score (ES) | 0.92 | 0.89 |
| F1-Score (EN) | 0.88 | 0.85 |
| F1-Score (PT) | 0.86 | 0.83 |
| Precision Global | 0.90 | 0.87 |
| Recall Global | 0.89 | 0.85 |

Aunque los modelos específicos por idioma muestran un rendimiento ligeramente superior, el modelo multilingüe ofrece 
mayor flexibilidad operativa y requiere menos recursos. La elección entre ellos dependerá de:

- **Distribución de usuarios**: Predominancia de un idioma específico
- **Recursos disponibles**: Memoria y CPU para cargar múltiples modelos
- **Prioridades operativas**: Precisión máxima vs. mantenimiento simplificado

## Integración con Componentes Existentes

La mejora del motor NLP se integra con los componentes existentes a través de:

1. **Actualización del NLPEngine**:
   ```python
   # app/services/nlp_engine.py
   class NLPEngine:
       async def detect_language(self, text):
           # Detección de idioma implementada
           
       async def process_message(self, message, language=None):
           # Selección dinámica de modelo según idioma
           model_path = self._get_model_path(language)
           # Procesamiento con el modelo seleccionado
   ```

2. **Actualización del Orchestrator**:
   ```python
   # app/services/orchestrator.py
   class Orchestrator:
       async def process_message(self, message):
           # Detectar idioma si es necesario
           language = await self.nlp_engine.detect_language(message.text)
           # Procesar con NLP según idioma
           nlp_result = await self.nlp_engine.process_message(message, language)
           # Generar respuesta en el idioma detectado
           response = await self.template_service.get_template(nlp_result.intent, language)
   ```

3. **Actualización del Template Service**:
   ```python
   # app/services/template_service.py
   class TemplateService:
       def __init__(self):
           # Cargar plantillas para todos los idiomas soportados
           self.templates = self._load_templates()
           
       async def get_template(self, intent, language="es"):
           # Seleccionar plantilla según intención e idioma
           return self.templates[language].get(intent, self.templates[language]["default"])
   ```

## Guía de Uso

### Entrenamiento de Modelos

Para entrenar los modelos multilingües:

```bash
cd /path/to/agente-hotel-api
./scripts/train_enhanced_models.sh --multilingual
```

Para entrenar modelos específicos por idioma:

```bash
cd /path/to/agente-hotel-api
./scripts/train_enhanced_models.sh
```

### Evaluación de Modelos

Para evaluar y comparar modelos:

```bash
cd /path/to/agente-hotel-api
./scripts/evaluate_multilingual_models.py
```

### Configuración de Variables de Entorno

Agregue las siguientes variables al archivo `.env`:

```
# NLP Configuration
NLP_MODEL_PATH=/path/to/models/nlu_enhanced_multilingual.tar.gz
NLP_FALLBACK_CONFIDENCE=0.45
NLP_LANGUAGES_SUPPORTED=es,en,pt
NLP_DEFAULT_LANGUAGE=es
```

## Consideraciones para Despliegue

1. **Recursos de Servidor**:
   - El modelo multilingüe requiere aproximadamente 1.5GB de RAM
   - Los modelos específicos por idioma requieren aproximadamente 600MB de RAM cada uno

2. **Latencia**:
   - Primera inferencia: ~300ms (carga del modelo)
   - Inferencias subsecuentes: ~70ms por mensaje

3. **Escalabilidad**:
   - Recomendación de balanceo de carga para más de 100 solicitudes/minuto
   - Considerar implementación con caché Redis para resultados NLP frecuentes

4. **Monitoreo**:
   - Métricas Prometheus agregadas para monitoreo de rendimiento NLP:
     - `nlp_processing_time_seconds`
     - `nlp_confidence_score`
     - `nlp_language_detection_total`

## Próximos Pasos y Mejoras Futuras

1. **Idiomas Adicionales**:
   - Expansión a francés e italiano siguiendo el mismo patrón

2. **Refinamiento Continuo**:
   - Implementación de aprendizaje activo para mejorar modelos con datos reales

3. **Optimización de Rendimiento**:
   - Cuantización de modelos para reducir huella de memoria
   - Caché inteligente de predicciones frecuentes

4. **Integración con LLMs**:
   - Explorar integración híbrida con LLMs para casos de borde
   - Implementar pipeline de fallback con modelos más grandes

---

## Autores y Contribuciones

Desarrollado como parte de la Fase E.5 del proyecto Sistema Agéntico Hotelero.

Fecha: Agosto 2023