#!/usr/bin/env python3
"""
Script de validación de credenciales para ETAPA 2
Verifica que todas las configuraciones necesarias estén presentes y funcionales

Uso:
    python scripts/validate_etapa2_credentials.py
"""

import os
import sys
from pathlib import Path
import asyncio
import httpx
from dotenv import load_dotenv

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    """Imprime header con formato"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}  {text}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")


def print_check(name: str, status: bool, details: str = ""):
    """Imprime resultado de check"""
    symbol = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    status_text = f"{GREEN}OK{RESET}" if status else f"{RED}FAIL{RESET}"
    print(f"{symbol} {name:40} [{status_text}] {details}")


def check_env_var(var_name: str, required: bool = True) -> tuple[bool, str]:
    """Verifica que variable de entorno exista y no sea placeholder"""
    value = os.getenv(var_name)
    
    if not value:
        return (not required, "Not set (optional)" if not required else "Missing")
    
    # Check for placeholders
    placeholders = [
        "CAMBIAR",
        "GENERA_",
        "OBTEN_",
        "_AQUI",
        "cambia_esto",
        "tu-email",
        "000000",
    ]
    
    if any(ph in value for ph in placeholders):
        return (False, f"Placeholder detected: {value[:30]}...")
    
    return (True, f"Set ({len(value)} chars)")


async def validate_postgres(url: str) -> tuple[bool, str]:
    """Valida conexión a PostgreSQL"""
    try:
        # Intentar importar asyncpg
        import asyncpg
        
        # Extraer componentes de la URL
        conn = await asyncpg.connect(url)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        
        return (True, f"Connected: {version[:50]}...")
    except ImportError:
        return (False, "asyncpg not installed")
    except Exception as e:
        return (False, f"Connection failed: {str(e)[:50]}")


async def validate_redis(url: str) -> tuple[bool, str]:
    """Valida conexión a Redis"""
    try:
        import aioredis
        
        redis = await aioredis.from_url(url)
        pong = await redis.ping()
        await redis.close()
        
        return (pong, "PONG received" if pong else "PING failed")
    except ImportError:
        return (False, "aioredis not installed")
    except Exception as e:
        return (False, f"Connection failed: {str(e)[:50]}")


async def validate_qloapps(base_url: str, api_key: str) -> tuple[bool, str]:
    """Valida conexión a QloApps PMS"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Intenta ping endpoint (ajustar según API real)
            response = await client.get(
                f"{base_url}/api/health",
                headers=headers
            )
            
            if response.status_code == 200:
                return (True, f"Status {response.status_code}")
            else:
                return (False, f"HTTP {response.status_code}")
                
    except httpx.TimeoutException:
        return (False, "Connection timeout")
    except Exception as e:
        return (False, f"Error: {str(e)[:50]}")


async def validate_whatsapp(access_token: str, phone_id: str) -> tuple[bool, str]:
    """Valida credenciales de WhatsApp"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Verifica que el token tenga acceso al phone number
            url = f"https://graph.facebook.com/v18.0/{phone_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return (True, f"Phone verified: {data.get('display_phone_number', 'N/A')}")
            else:
                return (False, f"HTTP {response.status_code}")
                
    except Exception as e:
        return (False, f"Error: {str(e)[:50]}")


async def main():
    """Ejecuta todas las validaciones"""
    
    print_header("ETAPA 2 - Validación de Credenciales")
    
    # Cargar .env.production
    env_path = Path(__file__).parent.parent / ".env.production"
    
    if not env_path.exists():
        print(f"{RED}ERROR: .env.production not found at {env_path}{RESET}")
        sys.exit(1)
    
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
    
    # Contadores
    total_checks = 0
    passed_checks = 0
    
    # 1. Environment Config
    print_header("1. Environment Configuration")
    
    checks = [
        ("ENVIRONMENT", True),
        ("DEBUG", True),
        ("USE_SUPABASE", True),
        ("SECRET_KEY", True),
    ]
    
    for var, required in checks:
        total_checks += 1
        status, details = check_env_var(var, required)
        print_check(var, status, details)
        if status:
            passed_checks += 1
    
    # 2. Database
    print_header("2. Database Configuration")
    
    postgres_url = os.getenv("POSTGRES_URL")
    total_checks += 1
    status, details = check_env_var("POSTGRES_URL", True)
    print_check("POSTGRES_URL", status, details)
    if status:
        passed_checks += 1
        
        # Validar conexión
        total_checks += 1
        status, details = await validate_postgres(postgres_url)
        print_check("Postgres Connection", status, details)
        if status:
            passed_checks += 1
    
    # 3. Redis
    print_header("3. Redis Configuration")
    
    redis_url = os.getenv("REDIS_URL")
    total_checks += 1
    status, details = check_env_var("REDIS_URL", True)
    print_check("REDIS_URL", status, details)
    if status:
        passed_checks += 1
        
        # Validar conexión
        total_checks += 1
        status, details = await validate_redis(redis_url)
        print_check("Redis Connection", status, details)
        if status:
            passed_checks += 1
    
    # 4. PMS (QloApps)
    print_header("4. PMS Configuration (QloApps)")
    
    pms_checks = [
        ("PMS_TYPE", True),
        ("PMS_BASE_URL", True),
        ("PMS_API_KEY", True),
        ("PMS_AUTH_TOKEN", True),
        ("CHECK_PMS_IN_READINESS", True),
    ]
    
    for var, required in pms_checks:
        total_checks += 1
        status, details = check_env_var(var, required)
        print_check(var, status, details)
        if status:
            passed_checks += 1
    
    # Validar conexión a QloApps
    pms_type = os.getenv("PMS_TYPE")
    if pms_type == "qloapps":
        pms_url = os.getenv("PMS_BASE_URL")
        pms_key = os.getenv("PMS_API_KEY")
        
        if pms_url and pms_key and "[" not in pms_url:
            total_checks += 1
            status, details = await validate_qloapps(pms_url, pms_key)
            print_check("QloApps Connection", status, details)
            if status:
                passed_checks += 1
    else:
        print(f"{YELLOW}ℹ PMS_TYPE={pms_type} (skipping QloApps connection test){RESET}")
    
    # 5. WhatsApp
    print_header("5. WhatsApp Configuration")
    
    wa_checks = [
        ("WHATSAPP_API_URL", True),
        ("WHATSAPP_ACCESS_TOKEN", True),
        ("WHATSAPP_PHONE_NUMBER_ID", True),
        ("WHATSAPP_BUSINESS_ACCOUNT_ID", True),
        ("WHATSAPP_WEBHOOK_VERIFY_TOKEN", True),
        ("WHATSAPP_APP_SECRET", True),
    ]
    
    for var, required in wa_checks:
        total_checks += 1
        status, details = check_env_var(var, required)
        print_check(var, status, details)
        if status:
            passed_checks += 1
    
    # Validar credenciales WhatsApp
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    wa_phone = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if wa_token and wa_phone and "[" not in wa_token:
        total_checks += 1
        status, details = await validate_whatsapp(wa_token, wa_phone)
        print_check("WhatsApp API", status, details)
        if status:
            passed_checks += 1
    
    # 6. Gmail
    print_header("6. Gmail Configuration")
    
    gmail_checks = [
        ("GMAIL_CLIENT_ID", True),
        ("GMAIL_CLIENT_SECRET", True),
        ("GMAIL_REFRESH_TOKEN", True),
        ("GMAIL_FROM_EMAIL", True),
    ]
    
    for var, required in gmail_checks:
        total_checks += 1
        status, details = check_env_var(var, required)
        print_check(var, status, details)
        if status:
            passed_checks += 1
    
    # 7. Security
    print_header("7. Security Configuration")
    
    security_checks = [
        ("CORS_ALLOWED_ORIGINS", True),
        ("ALLOWED_HOSTS", True),
        ("COOP_ENABLED", True),
        ("COEP_ENABLED", True),
    ]
    
    for var, required in security_checks:
        total_checks += 1
        status, details = check_env_var(var, required)
        print_check(var, status, details)
        if status:
            passed_checks += 1
    
    # Resumen final
    print_header("Validation Summary")
    
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    color = GREEN if percentage == 100 else (YELLOW if percentage >= 70 else RED)
    
    print(f"Total Checks:  {total_checks}")
    print(f"Passed:        {color}{passed_checks}{RESET}")
    print(f"Failed:        {RED}{total_checks - passed_checks}{RESET}")
    print(f"Completion:    {color}{percentage:.1f}%{RESET}")
    
    if percentage == 100:
        print(f"\n{GREEN}✓ All checks passed! Ready for ETAPA 2 deployment.{RESET}")
        return 0
    elif percentage >= 70:
        print(f"\n{YELLOW}⚠ Some checks failed. Review missing credentials.{RESET}")
        return 1
    else:
        print(f"\n{RED}✗ Critical checks failed. Cannot proceed with ETAPA 2.{RESET}")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
