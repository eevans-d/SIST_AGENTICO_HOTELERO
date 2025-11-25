#!/usr/bin/env python3
"""
Validación de Credenciales para ETAPA 2
Verifica que todas las credenciales necesarias estén configuradas.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Carga un archivo .env y retorna dict con las variables."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def check_credential(
    env_vars: Dict[str, str], 
    key: str, 
    default_invalid: List[str] = None
) -> Tuple[bool, str]:
    """
    Verifica si una credencial está configurada correctamente.
    
    Returns:
        (is_valid, value)
    """
    if default_invalid is None:
        default_invalid = ["", "your_", "change-me", "sk_test_", "dummy"]
    
    value = env_vars.get(key, "")
    
    if not value:
        return False, ""
    
    # Verificar si es un valor dummy/placeholder
    for invalid in default_invalid:
        if invalid and value.startswith(invalid):
            return False, value
    
    return True, value


def validate_qloapps_credentials(env_vars: Dict[str, str]) -> List[Dict]:
    """Valida credenciales de QloApps PMS."""
    results = []
    
    credentials = [
        ("QLOAPPS_BASE_URL", ["http://localhost", "http://127.0.0.1", "change-me"]),
        ("QLOAPPS_API_KEY", ["change-me", "dummy", "test_"]),
        ("QLOAPPS_USERNAME", ["admin", "test", "change-me"]),
        ("QLOAPPS_PASSWORD", ["change-me", "password", "admin123"]),
    ]
    
    for key, invalid_values in credentials:
        is_valid, value = check_credential(env_vars, key, invalid_values)
        results.append({
            "service": "QloApps PMS",
            "credential": key,
            "valid": is_valid,
            "value": value[:20] + "..." if len(value) > 20 else value
        })
    
    return results


def validate_whatsapp_credentials(env_vars: Dict[str, str]) -> List[Dict]:
    """Valida credenciales de WhatsApp Meta Cloud API."""
    results = []
    
    credentials = [
        ("WHATSAPP_ACCESS_TOKEN", ["change-me", "EAA"]),
        ("WHATSAPP_PHONE_NUMBER_ID", ["change-me", "123456"]),
        ("WHATSAPP_BUSINESS_ACCOUNT_ID", ["change-me", "123456"]),
        ("WHATSAPP_VERIFY_TOKEN", ["change-me", "my_webhook_token"]),
    ]
    
    for key, invalid_values in credentials:
        is_valid, value = check_credential(env_vars, key, invalid_values)
        results.append({
            "service": "WhatsApp",
            "credential": key,
            "valid": is_valid,
            "value": value[:20] + "..." if len(value) > 20 else value
        })
    
    return results


def validate_gmail_credentials(env_vars: Dict[str, str]) -> List[Dict]:
    """Valida credenciales de Gmail OAuth2."""
    results = []
    
    credentials = [
        ("GMAIL_CLIENT_ID", ["change-me", "your_client_id"]),
        ("GMAIL_CLIENT_SECRET", ["change-me", "your_client_secret"]),
        ("GMAIL_REFRESH_TOKEN", ["change-me", "your_refresh_token"]),
        ("GMAIL_SENDER_EMAIL", ["change-me", "noreply@"]),
    ]
    
    for key, invalid_values in credentials:
        is_valid, value = check_credential(env_vars, key, invalid_values)
        results.append({
            "service": "Gmail",
            "credential": key,
            "valid": is_valid,
            "value": value[:30] + "..." if len(value) > 30 else value
        })
    
    return results


def print_results(results: List[Dict]):
    """Imprime resultados de validación."""
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}VALIDACIÓN DE CREDENCIALES - ETAPA 2{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    services = {}
    for result in results:
        service = result["service"]
        if service not in services:
            services[service] = []
        services[service].append(result)
    
    total_valid = sum(1 for r in results if r["valid"])
    total_invalid = len(results) - total_valid
    
    for service, creds in services.items():
        print(f"{BOLD}{service}:{RESET}")
        for cred in creds:
            status = f"{GREEN}✓ VÁLIDA{RESET}" if cred["valid"] else f"{RED}✗ FALTA{RESET}"
            value_display = f"({cred['value']})" if cred["value"] else "(no configurada)"
            print(f"  {cred['credential']:35s} {status:20s} {value_display}")
        print()
    
    print(f"{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}RESUMEN:{RESET}")
    print(f"  {GREEN}Válidas:{RESET} {total_valid}/{len(results)}")
    print(f"  {RED}Faltantes:{RESET} {total_invalid}/{len(results)}")
    
    if total_invalid == 0:
        print(f"\n{GREEN}{BOLD}✓ Todas las credenciales están configuradas correctamente{RESET}")
        print(f"{GREEN}  Puedes proceder con ETAPA 2{RESET}\n")
        return True
    else:
        print(f"\n{YELLOW}{BOLD}⚠ Faltan {total_invalid} credenciales por configurar{RESET}")
        print(f"{YELLOW}  Consulta docs/SECRETS_GUIDE.md para obtener las credenciales{RESET}\n")
        return False


def main():
    """Ejecuta validación de credenciales."""
    project_root = Path(__file__).parent.parent
    
    # Intentar cargar diferentes archivos .env
    env_files = [
        project_root / ".env",
        project_root / ".env.production",
        project_root / ".env.staging",
    ]
    
    env_vars = {}
    loaded_file = None
    
    for env_file in env_files:
        if env_file.exists():
            env_vars = load_env_file(env_file)
            loaded_file = env_file.name
            break
    
    if not env_vars:
        print(f"{RED}Error: No se encontró ningún archivo .env{RESET}")
        return 1
    
    print(f"{BOLD}Archivo cargado: {loaded_file}{RESET}")
    
    # Validar credenciales
    results = []
    results.extend(validate_qloapps_credentials(env_vars))
    results.extend(validate_whatsapp_credentials(env_vars))
    results.extend(validate_gmail_credentials(env_vars))
    
    # Imprimir resultados
    all_valid = print_results(results)
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())
