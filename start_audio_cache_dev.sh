#!/bin/bash
# Script para iniciar rápidamente el entorno de desarrollo de caché de audio

echo "=== Iniciando entorno de desarrollo para caché de audio ==="

# Actualizar repositorio
echo "Actualizando repositorio..."
git pull origin main

# Iniciar servicios Docker
echo "Iniciando servicios con Docker Compose..."
cd agente-hotel-api
make docker-up

# Ejecutar pruebas de caché de audio
echo "Ejecutando pruebas de caché de audio..."
make test TEST_PATH=tests/unit/test_audio_cache_service.py

# Mostrar estadísticas del servicio
echo "=== Resumen del sistema de caché ==="
echo "Archivos principales:"
echo "- app/services/audio_cache_service.py: Implementación principal del sistema de caché"
echo "- app/services/audio_processor.py: Integración con el procesador de audio"
echo "- app/routers/admin.py: Endpoints de administración"
echo "- docs/AUDIO_CACHE.md: Documentación detallada"
echo "- docs/AUDIO_CACHE_STATUS.md: Plan de trabajo actual"

# Mostrar tareas pendientes
echo ""
echo "=== Tareas pendientes para hoy ==="
echo "1. Implementar limpieza automática de caché cuando supere cierto tamaño"
echo "2. Añadir compresión opcional para archivos de audio grandes"
echo "3. Crear dashboard en Grafana para visualizar métricas de caché"
echo "4. Implementar pruebas de rendimiento para verificar mejoras de latencia"

echo ""
echo "¡Listo para continuar el desarrollo!"
echo ""