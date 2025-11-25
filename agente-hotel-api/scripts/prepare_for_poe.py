#!/usr/bin/env python3
"""
Extractor de Repositorio para Poe.com Knowledge Base
=====================================================

Genera 4 archivos .txt (~20-22 MB c/u) con contenido TIER-priorizado
del proyecto SIST_AGENTICO_HOTELERO para subir a bot o3-pro en Poe.com.

Basado en: .playbook/POE_PROMPT_1_EXTRACCION_PERSONALIZADO.md
Versión: 1.0 (Personalizada)
Python: 3.8+ (sin dependencias externas - solo stdlib)

Uso:
    python3 prepare_for_poe.py [--output-dir POE_KNOWLEDGE_FILES]
    
Output:
    POE_KNOWLEDGE_FILES/
        parte_1.txt (~22 MB) - TIER 1+2 (docs críticas + código core)
        parte_2.txt (~22 MB) - TIER 3 (infraestructura)
        parte_3.txt (~22 MB) - TIER 4 (tests + docs extendidas)
        parte_4.txt (~5-10 MB) - TIER 5 (miscelánea)
        manifest.json (~50 KB) - Índice maestro con metadata
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime
from collections import defaultdict

# ============================================================================
# CONFIGURACIÓN DEL PROYECTO
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
COMMIT_HASH = "97676bcc27f7f999f602432a07383ce09c5dee68"
DEPLOYMENT_READINESS = "8.9/10"
TEST_COVERAGE = "31%"
CVE_STATUS = "0 CRITICAL"

# Límites de Poe.com
MAX_FILE_SIZE_MB = 23
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
TARGET_FILE_SIZE_MB = 22
TARGET_FILE_SIZE_BYTES = TARGET_FILE_SIZE_MB * 1024 * 1024

# ============================================================================
# TIER PRIORIZACIÓN (basado en PROMPT 1 personalizado)
# ============================================================================

TIER_1_CRITICAL = [
    # Documentación arquitectural crítica
    ".github/copilot-instructions.md",
    "MASTER_PROJECT_GUIDE.md",
    "README.md",
    "agente-hotel-api/README.md",
    "agente-hotel-api/README-Infra.md",
    "agente-hotel-api/README-Database.md",
    "agente-hotel-api/README-PERFORMANCE.md",
    
    # Playbooks ejecutivos
    ".playbook/PRODUCTION_READINESS_CHECKLIST.md",
    ".playbook/POE_PROMPT_1_EXTRACCION_PERSONALIZADO.md",
    ".playbook/POE_PROMPT_2_SYSTEM_PERSONALIZADO.md",
    ".playbook/POE_PROMPT_3_CASOS_USO_PERSONALIZADO.md",
    ".playbook/POE_INTEGRACION_RESUMEN_EJECUTIVO.md",
]

TIER_2_CORE_CODE = [
    # Core services (cerebro del sistema)
    "agente-hotel-api/app/services/orchestrator.py",
    "agente-hotel-api/app/services/session_manager.py",
    "agente-hotel-api/app/services/pms_adapter.py",
    "agente-hotel-api/app/services/message_gateway.py",
    "agente-hotel-api/app/services/feature_flag_service.py",
    "agente-hotel-api/app/services/lock_service.py",
    "agente-hotel-api/app/services/whatsapp_client.py",
    "agente-hotel-api/app/services/gmail_client.py",
    
    # FastAPI app + middleware
    "agente-hotel-api/app/main.py",
    "agente-hotel-api/app/core/settings.py",
    "agente-hotel-api/app/core/logging.py",
    "agente-hotel-api/app/core/middleware.py",
    "agente-hotel-api/app/core/circuit_breaker.py",
    "agente-hotel-api/app/core/retry.py",
    
    # Routers
    "agente-hotel-api/app/routers/webhooks.py",
    "agente-hotel-api/app/routers/health.py",
    
    # Models
    "agente-hotel-api/app/models/unified_message.py",
    "agente-hotel-api/app/models/session.py",
]

TIER_3_INFRASTRUCTURE = [
    # Docker Compose
    "agente-hotel-api/docker-compose.yml",
    "agente-hotel-api/docker-compose.staging.yml",
    "agente-hotel-api/docker-compose.production.yml",
    "agente-hotel-api/Dockerfile",
    "agente-hotel-api/Dockerfile.production",
    
    # Makefile
    "agente-hotel-api/Makefile",
    
    # Scripts críticos
    "agente-hotel-api/scripts/deploy-staging.sh",
    "agente-hotel-api/scripts/preflight.py",
    "agente-hotel-api/scripts/canary-deploy.sh",
    
    # Prometheus + Grafana
    "agente-hotel-api/docker/prometheus/prometheus.yml",
    "agente-hotel-api/docker/prometheus/recording_rules.yml",
    "agente-hotel-api/docker/prometheus/alerts.yml",
    "agente-hotel-api/docker/grafana/dashboards/orchestrator.json",
]

TIER_4_TESTS_DOCS = [
    # Tests críticos
    "agente-hotel-api/tests/unit/test_orchestrator.py",
    "agente-hotel-api/tests/integration/test_orchestrator_integration.py",
    "agente-hotel-api/tests/chaos/test_circuit_breaker_resilience.py",
    
    # Docs extendidas
    "agente-hotel-api/docs/START-HERE.md",
    "agente-hotel-api/docs/BLUEPRINT_v2_DEFINITIVO.md",
    "agente-hotel-api/docs/ROADMAP_EXECUTION_BLUEPRINT.md",
]

# Extensiones a incluir
INCLUDE_EXTENSIONS = {
    ".py", ".md", ".yml", ".yaml", ".json", 
    ".txt", ".sh", ".env.example", 
    "Dockerfile", "Makefile", ".ini"
}

# Exclusiones (archivos muy grandes o no relevantes)
EXCLUDE_PATTERNS = [
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    ".benchmarks/",
    ".performance/",
    "htmlcov/",
    "logs/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    "node_modules/",
    ".venv/",
    "venv/",
    ".git/",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".coverage",
    "coverage.xml",
]

# ============================================================================
# UTILIDADES
# ============================================================================

def should_include_file(file_path: Path) -> bool:
    """Determina si un archivo debe ser incluido en la extracción."""
    # Convertir a string relativo al proyecto root
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    
    # Verificar exclusiones
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_path:
            return False
    
    # Verificar extensión
    if file_path.suffix in INCLUDE_EXTENSIONS or file_path.name in INCLUDE_EXTENSIONS:
        return True
    
    # Archivos sin extensión (Dockerfile, Makefile, etc.)
    if file_path.is_file() and file_path.suffix == "" and file_path.name not in [".gitkeep"]:
        return True
    
    return False


def calculate_checksum(content: str) -> str:
    """Calcula SHA256 checksum de contenido."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def format_file_content(file_path: Path, rel_path: str) -> str:
    """
    Formatea contenido de archivo con header y footer.
    
    Formato:
        ═══════════════════════════════════════════════════════════════
        📄 ARCHIVO: path/to/file.py
        🏷️ TIER: 2 (CORE_CODE)
        📏 TAMAÑO: 12,345 bytes
        🔒 CHECKSUM: sha256:abc123...
        ═══════════════════════════════════════════════════════════════
        
        [CONTENIDO DEL ARCHIVO]
        
        ═══════════════════════════════════════════════════════════════
        ✅ FIN: path/to/file.py
        ═══════════════════════════════════════════════════════════════
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        return f"[ERROR leyendo {rel_path}: {e}]\n\n"
    
    tier = get_tier_for_file(rel_path)
    checksum = calculate_checksum(content)
    size = len(content.encode('utf-8'))
    
    header = (
        "═══════════════════════════════════════════════════════════════\n"
        f"📄 ARCHIVO: {rel_path}\n"
        f"🏷️ TIER: {tier}\n"
        f"📏 TAMAÑO: {size:,} bytes\n"
        f"🔒 CHECKSUM: sha256:{checksum[:16]}...\n"
        "═══════════════════════════════════════════════════════════════\n\n"
    )
    
    footer = (
        "\n"
        "═══════════════════════════════════════════════════════════════\n"
        f"✅ FIN: {rel_path}\n"
        "═══════════════════════════════════════════════════════════════\n\n"
    )
    
    return header + content + footer


def get_tier_for_file(rel_path: str) -> str:
    """Determina TIER de un archivo."""
    if rel_path in TIER_1_CRITICAL:
        return "1 (CRITICAL)"
    elif rel_path in TIER_2_CORE_CODE:
        return "2 (CORE_CODE)"
    elif rel_path in TIER_3_INFRASTRUCTURE:
        return "3 (INFRASTRUCTURE)"
    elif rel_path in TIER_4_TESTS_DOCS:
        return "4 (TESTS_DOCS)"
    else:
        return "5 (MISCELLANEOUS)"


def get_tier_priority(rel_path: str) -> int:
    """Retorna prioridad numérica de TIER (menor = mayor prioridad)."""
    if rel_path in TIER_1_CRITICAL:
        return 1
    elif rel_path in TIER_2_CORE_CODE:
        return 2
    elif rel_path in TIER_3_INFRASTRUCTURE:
        return 3
    elif rel_path in TIER_4_TESTS_DOCS:
        return 4
    else:
        return 5


# ============================================================================
# RECOLECCIÓN DE ARCHIVOS
# ============================================================================

def collect_files() -> Dict[int, List[Tuple[Path, str]]]:
    """
    Recolecta todos los archivos del repositorio organizados por TIER.
    
    Returns:
        Dict[tier_number, List[(absolute_path, relative_path)]]
    """
    tiers = defaultdict(list)
    
    print(f"🔍 Escaneando repositorio: {PROJECT_ROOT}")
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)
        
        # Filtrar directorios excluidos
        dirs[:] = [d for d in dirs if not any(pattern.rstrip('/') in d for pattern in EXCLUDE_PATTERNS)]
        
        for file_name in files:
            file_path = root_path / file_name
            
            if not should_include_file(file_path):
                continue
            
            rel_path = str(file_path.relative_to(PROJECT_ROOT))
            tier = get_tier_priority(rel_path)
            
            tiers[tier].append((file_path, rel_path))
    
    # Estadísticas
    total_files = sum(len(files) for files in tiers.values())
    print(f"✅ Archivos recolectados: {total_files}")
    for tier in sorted(tiers.keys()):
        print(f"   TIER {tier}: {len(tiers[tier])} archivos")
    
    return tiers


# ============================================================================
# BALANCEO Y DISTRIBUCIÓN
# ============================================================================

def distribute_files_to_parts(tiers: Dict[int, List[Tuple[Path, str]]]) -> List[List[Tuple[Path, str]]]:
    """
    Distribuye archivos en 4 partes balanceadas (~22 MB c/u).
    
    Estrategia:
        - TIER 1 + TIER 2 → Parte 1 (~22 MB)
        - TIER 3 → Parte 2 (~22 MB)
        - TIER 4 → Parte 3 (~22 MB)
        - TIER 5 → Parte 4 (resto)
    
    Si algún TIER excede 22 MB, se divide entre partes.
    """
    parts = [[], [], [], []]
    part_sizes = [0, 0, 0, 0]
    
    # Función helper para estimar tamaño de archivo formateado
    def estimate_formatted_size(file_path: Path) -> int:
        try:
            raw_size = file_path.stat().st_size
            # Header + footer ~300 bytes adicionales
            return raw_size + 300
        except:
            return 0
    
    # TIER 1 + TIER 2 → Parte 1
    print("\n📦 Distribuyendo TIER 1 (CRITICAL)...")
    for file_path, rel_path in sorted(tiers[1], key=lambda x: x[1]):
        size = estimate_formatted_size(file_path)
        if part_sizes[0] + size <= TARGET_FILE_SIZE_BYTES:
            parts[0].append((file_path, rel_path))
            part_sizes[0] += size
        else:
            # Si TIER 1 excede 22MB, overflow a Parte 2
            parts[1].append((file_path, rel_path))
            part_sizes[1] += size
    
    print(f"📦 Distribuyendo TIER 2 (CORE_CODE)...")
    for file_path, rel_path in sorted(tiers[2], key=lambda x: x[1]):
        size = estimate_formatted_size(file_path)
        if part_sizes[0] + size <= TARGET_FILE_SIZE_BYTES:
            parts[0].append((file_path, rel_path))
            part_sizes[0] += size
        else:
            parts[1].append((file_path, rel_path))
            part_sizes[1] += size
    
    # TIER 3 → Parte 2
    print(f"📦 Distribuyendo TIER 3 (INFRASTRUCTURE)...")
    for file_path, rel_path in sorted(tiers[3], key=lambda x: x[1]):
        size = estimate_formatted_size(file_path)
        if part_sizes[1] + size <= TARGET_FILE_SIZE_BYTES:
            parts[1].append((file_path, rel_path))
            part_sizes[1] += size
        else:
            parts[2].append((file_path, rel_path))
            part_sizes[2] += size
    
    # TIER 4 → Parte 3
    print(f"📦 Distribuyendo TIER 4 (TESTS_DOCS)...")
    for file_path, rel_path in sorted(tiers[4], key=lambda x: x[1]):
        size = estimate_formatted_size(file_path)
        if part_sizes[2] + size <= TARGET_FILE_SIZE_BYTES:
            parts[2].append((file_path, rel_path))
            part_sizes[2] += size
        else:
            parts[3].append((file_path, rel_path))
            part_sizes[3] += size
    
    # TIER 5 → Parte 4 (sin límite, es el resto)
    print(f"📦 Distribuyendo TIER 5 (MISCELLANEOUS)...")
    for file_path, rel_path in sorted(tiers[5], key=lambda x: x[1]):
        size = estimate_formatted_size(file_path)
        parts[3].append((file_path, rel_path))
        part_sizes[3] += size
    
    # Estadísticas
    print(f"\n📊 Distribución Final:")
    for i, (part, size) in enumerate(zip(parts, part_sizes), 1):
        size_mb = size / (1024 * 1024)
        print(f"   Parte {i}: {len(part)} archivos, {size_mb:.2f} MB")
    
    return parts


# ============================================================================
# GENERACIÓN DE ARCHIVOS
# ============================================================================

def generate_part_file(part_number: int, files: List[Tuple[Path, str]], output_dir: Path) -> Dict:
    """
    Genera archivo .txt para una parte.
    
    Returns:
        Metadata dict con estadísticas de la parte.
    """
    output_file = output_dir / f"parte_{part_number}.txt"
    
    print(f"\n✍️  Generando {output_file.name}...")
    
    # Header del archivo
    now = datetime.now().isoformat()
    header = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 SIST_AGENTICO_HOTELERO - Knowledge Base                     ║
║                          Parte {part_number} de 4                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

📅 FECHA GENERACIÓN: {now}
🔖 COMMIT HASH: {COMMIT_HASH}
📊 DEPLOYMENT READINESS: {DEPLOYMENT_READINESS}
🧪 TEST COVERAGE: {TEST_COVERAGE}
🔒 CVE STATUS: {CVE_STATUS}

📦 ARCHIVOS EN ESTA PARTE: {len(files)}

════════════════════════════════════════════════════════════════════════════════

"""
    
    content_parts = [header]
    file_metadata = []
    
    for file_path, rel_path in files:
        formatted_content = format_file_content(file_path, rel_path)
        content_parts.append(formatted_content)
        
        file_metadata.append({
            "path": rel_path,
            "tier": get_tier_for_file(rel_path),
            "size": len(formatted_content.encode('utf-8'))
        })
    
    # Footer del archivo
    footer = f"""
════════════════════════════════════════════════════════════════════════════════
╔══════════════════════════════════════════════════════════════════════════════╗
║                          FIN PARTE {part_number} de 4                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    content_parts.append(footer)
    
    full_content = "\n".join(content_parts)
    
    # Escribir archivo con BOM UTF-8
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(full_content)
    
    final_size = output_file.stat().st_size
    final_size_mb = final_size / (1024 * 1024)
    checksum = calculate_checksum(full_content)
    
    print(f"   ✅ {output_file.name}: {final_size_mb:.2f} MB, {len(files)} archivos")
    
    return {
        "part_number": part_number,
        "filename": output_file.name,
        "file_count": len(files),
        "size_bytes": final_size,
        "size_mb": round(final_size_mb, 2),
        "checksum": checksum,
        "files": file_metadata
    }


def generate_manifest(parts_metadata: List[Dict], output_dir: Path) -> None:
    """Genera manifest.json con índice maestro."""
    manifest = {
        "project": "SIST_AGENTICO_HOTELERO",
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "commit_hash": COMMIT_HASH,
        "deployment_readiness": DEPLOYMENT_READINESS,
        "test_coverage": TEST_COVERAGE,
        "cve_status": CVE_STATUS,
        "parts": parts_metadata,
        "total_files": sum(p["file_count"] for p in parts_metadata),
        "total_size_mb": sum(p["size_mb"] for p in parts_metadata),
        "critical_files_included": [
            f for f in TIER_1_CRITICAL[:5]  # Primeros 5 críticos
        ]
    }
    
    manifest_file = output_dir / "manifest.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Manifest generado: {manifest_file.name}")


# ============================================================================
# VALIDACIÓN
# ============================================================================

def validate_outputs(output_dir: Path) -> bool:
    """
    Valida que los 4 archivos y manifest existan y cumplan requisitos.
    
    Returns:
        True si validación exitosa, False si falla.
    """
    print("\n🔍 Validando outputs...")
    
    # Verificar 4 archivos .txt + manifest.json
    expected_files = [
        "parte_1.txt", "parte_2.txt", "parte_3.txt", "parte_4.txt", "manifest.json"
    ]
    
    for filename in expected_files:
        file_path = output_dir / filename
        if not file_path.exists():
            print(f"   ❌ Falta: {filename}")
            return False
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Validar tamaños
        if filename.endswith('.txt'):
            if size_mb > MAX_FILE_SIZE_MB:
                print(f"   ❌ {filename} excede límite: {size_mb:.2f} MB > {MAX_FILE_SIZE_MB} MB")
                return False
            print(f"   ✅ {filename}: {size_mb:.2f} MB")
        else:
            print(f"   ✅ {filename}: {size_mb:.4f} MB")
    
    # Verificar archivos críticos en Parte 1
    parte_1 = (output_dir / "parte_1.txt").read_text(encoding='utf-8-sig')
    
    critical_check = [
        ".github/copilot-instructions.md",
        "MASTER_PROJECT_GUIDE.md",
        "orchestrator.py"
    ]
    
    missing = []
    for critical in critical_check:
        if critical not in parte_1:
            missing.append(critical)
    
    if missing:
        print(f"\n   ⚠️  Advertencia: Archivos críticos NO encontrados en Parte 1:")
        for m in missing:
            print(f"      - {m}")
        print("   (Posiblemente en Parte 2 si Parte 1 excedió 22 MB)")
    else:
        print(f"\n   ✅ Archivos críticos verificados en Parte 1")
    
    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extractor de repositorio para Poe.com Knowledge Base"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=PROJECT_ROOT / "POE_KNOWLEDGE_FILES",
        help="Directorio de salida (default: POE_KNOWLEDGE_FILES/)"
    )
    
    args = parser.parse_args()
    output_dir = args.output_dir
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║       Extractor de Repositorio para Poe.com (o3-pro Knowledge Base)         ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"\n📂 Proyecto: {PROJECT_ROOT}")
    print(f"📂 Output: {output_dir}")
    print(f"🔖 Commit: {COMMIT_HASH}")
    
    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Paso 1: Recolectar archivos por TIER
    tiers = collect_files()
    
    # Paso 2: Distribuir en 4 partes
    parts = distribute_files_to_parts(tiers)
    
    # Paso 3: Generar archivos .txt
    parts_metadata = []
    for i, part_files in enumerate(parts, 1):
        metadata = generate_part_file(i, part_files, output_dir)
        parts_metadata.append(metadata)
    
    # Paso 4: Generar manifest.json
    generate_manifest(parts_metadata, output_dir)
    
    # Paso 5: Validar outputs
    if validate_outputs(output_dir):
        print("\n" + "="*80)
        print("✅ EXTRACCIÓN COMPLETADA EXITOSAMENTE")
        print("="*80)
        print(f"\n📦 Archivos generados en: {output_dir}")
        print("\nPróximos pasos:")
        print("  1. Subir los 4 archivos .txt a Poe.com (bot o3-pro)")
        print("  2. Configurar system prompt usando PROMPT 2")
        print("  3. Validar con casos de uso del PROMPT 3")
        return 0
    else:
        print("\n❌ VALIDACIÓN FALLÓ - Revisar outputs")
        return 1


if __name__ == "__main__":
    sys.exit(main())
