#!/bin/bash
# Script de Hardening de Seguridad
# Aplica mejoras de seguridad al sistema

set -e

PROJECT_ROOT="/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api"
cd "$PROJECT_ROOT"

echo "🔐 INICIANDO HARDENING DE SEGURIDAD"
echo "======================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Verificar que no haya secretos expuestos
echo "1️⃣  Verificando exposición de secretos..."
if grep -r "password\s*=\s*['\"]" app/ --include="*.py" | grep -v ".pyc" | grep -v "SecretStr" | grep -v "# pragma: allowlist secret"; then
    echo -e "${YELLOW}⚠️  Posibles secretos expuestos encontrados${NC}"
    echo "   Usa SecretStr de Pydantic para campos sensibles"
else
    echo -e "${GREEN}✓${NC} No se encontraron secretos expuestos"
fi
echo ""

# 2. Agregar headers de seguridad en middleware
echo "2️⃣  Verificando middleware de seguridad..."
if grep -q "SecurityHeadersMiddleware" app/core/middleware.py; then
    echo -e "${GREEN}✓${NC} Middleware de seguridad encontrado"
else
    echo -e "${YELLOW}⚠️  Agregando middleware de seguridad${NC}"
    cat >> app/core/middleware.py << 'EOF'

class SecurityHeadersMiddleware:
    """Middleware para agregar headers de seguridad"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers["X-Content-Type-Options"] = "nosniff"
                    headers["X-Frame-Options"] = "DENY"
                    headers["X-XSS-Protection"] = "1; mode=block"
                    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                    headers["Content-Security-Policy"] = "default-src 'self'"
                await send(message)
            
            await self.app(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send)
EOF
fi
echo ""

# 3. Validar configuración de CORS
echo "3️⃣  Verificando configuración de CORS..."
if grep -q "allow_origins=\[" app/main.py; then
    echo -e "${GREEN}✓${NC} CORS configurado con lista específica"
else
    echo -e "${YELLOW}⚠️  CORS podría estar muy permisivo${NC}"
    echo "   Revisa la configuración en app/main.py"
fi
echo ""

# 4. Verificar rate limiting
echo "4️⃣  Verificando rate limiting..."
if grep -q "@limiter.limit" app/routers/*.py; then
    echo -e "${GREEN}✓${NC} Rate limiting implementado"
else
    echo -e "${YELLOW}⚠️  Considera agregar rate limiting a endpoints públicos${NC}"
fi
echo ""

# 5. Crear archivo de auditoría
echo "5️⃣  Creando sistema de auditoría..."
mkdir -p app/services/security

cat > app/services/security/audit_logger.py << 'EOF'
"""
Sistema de Auditoría de Seguridad
Registra eventos de seguridad importantes
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Tipos de eventos de auditoría"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    ACCESS_DENIED = "access_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class AuditLogger:
    """Logger especializado para eventos de seguridad"""
    
    @staticmethod
    async def log_event(
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Registrar evento de auditoría
        
        Args:
            event_type: Tipo de evento
            user_id: ID del usuario involucrado
            ip_address: IP de origen
            resource: Recurso accedido/modificado
            details: Detalles adicionales
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "resource": resource,
            "details": details or {}
        }
        
        logger.info(
            "security.audit",
            extra=audit_entry
        )
        
        # TODO: Persistir en DB para análisis histórico
        # await db.audit_logs.insert(audit_entry)

# Instancia global
audit_logger = AuditLogger()

async def get_audit_logger() -> AuditLogger:
    """Obtener instancia del audit logger"""
    return audit_logger
EOF

echo -e "${GREEN}✓${NC} Sistema de auditoría creado en app/services/security/audit_logger.py"
echo ""

# 6. Crear validador de entrada mejorado
echo "6️⃣  Creando validador de entrada robusto..."

cat > app/core/input_validator.py << 'EOF'
"""
Validador de Entrada Robusto
Protección contra inyección y XSS
"""

import re
from typing import Any
from html import escape

class InputValidator:
    """Validador de entrada para prevenir ataques"""
    
    # Patrones peligrosos
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*)",
        r"(;.*drop\b)",
        r"(;.*delete\b)",
        r"(exec\s*\()",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitizar string eliminando contenido peligroso"""
        if not isinstance(value, str):
            return value
        
        # Escapar HTML
        sanitized = escape(value)
        
        # Remover patrones XSS
        for pattern in cls.XSS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @classmethod
    def validate_no_sql_injection(cls, value: str) -> bool:
        """Verificar que no haya patrones de SQL injection"""
        if not isinstance(value, str):
            return True
        
        value_lower = value.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return False
        
        return True
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validar formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validar formato de teléfono"""
        # Acepta formatos: +1234567890, 123-456-7890, (123) 456-7890
        pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        return bool(re.match(pattern, phone))

# Instancia global
input_validator = InputValidator()

def get_input_validator() -> InputValidator:
    """Obtener instancia del validador"""
    return input_validator
EOF

echo -e "${GREEN}✓${NC} Validador de entrada creado en app/core/input_validator.py"
echo ""

# 7. Actualizar .gitignore para secretos
echo "7️⃣  Actualizando .gitignore..."
cat >> .gitignore << 'EOF'

# Secrets y configuración sensible
.env.production
*.pem
*.key
*.crt
secrets/
credentials/
*.secret

# Logs que podrían contener información sensible
*.log
logs/
audit_logs/

# Backups de base de datos
*.sql
*.dump
backups/
EOF

echo -e "${GREEN}✓${NC} .gitignore actualizado"
echo ""

# 8. Crear checklist de seguridad
echo "8️⃣  Creando checklist de seguridad..."

cat > docs/SECURITY_CHECKLIST.md << 'EOF'
# 🔐 Security Checklist - Agente Hotelero IA

## Pre-Deployment Security Checks

### Authentication & Authorization
- [ ] Todos los endpoints sensibles requieren autenticación
- [ ] Tokens expiran después de tiempo razonable
- [ ] Rotación de secrets implementada
- [ ] 2FA disponible para usuarios admin

### Input Validation
- [ ] Validación de entrada en todos los endpoints
- [ ] Sanitización de datos antes de guardar
- [ ] Rate limiting configurado
- [ ] File upload con validación de tipo y tamaño

### Data Protection
- [ ] Datos sensibles encriptados en reposo
- [ ] TLS/SSL configurado correctamente
- [ ] Secrets no están en código fuente
- [ ] Logs no contienen información sensible

### Infrastructure
- [ ] Firewall configurado
- [ ] Puertos no necesarios cerrados
- [ ] Contenedores sin privilegios root
- [ ] Red de servicios aislada

### Monitoring & Response
- [ ] Alertas de seguridad configuradas
- [ ] Logs de auditoría habilitados
- [ ] Plan de respuesta a incidentes documentado
- [ ] Backups regulares configurados

### Dependencies
- [ ] Dependencias actualizadas
- [ ] No hay vulnerabilidades conocidas
- [ ] Escaneo automático de vulnerabilidades
- [ ] Proceso de actualización documentado

### Code Security
- [ ] Sin secretos en código
- [ ] Sin SQL injection vulnerabilities
- [ ] Sin XSS vulnerabilities
- [ ] Sin CSRF vulnerabilities

## Regular Maintenance

### Weekly
- [ ] Revisar logs de auditoría
- [ ] Verificar alertas de seguridad
- [ ] Actualizar dependencias con parches de seguridad

### Monthly
- [ ] Escaneo completo de vulnerabilidades
- [ ] Revisar permisos de acceso
- [ ] Actualizar documentación de seguridad
- [ ] Test de penetración

### Quarterly
- [ ] Auditoría de seguridad completa
- [ ] Revisión de políticas de seguridad
- [ ] Entrenamiento de equipo en seguridad
- [ ] Actualización de plan de respuesta a incidentes
EOF

echo -e "${GREEN}✓${NC} Checklist de seguridad creado en docs/SECURITY_CHECKLIST.md"
echo ""

# 9. Crear script de rotación de secrets
echo "9️⃣  Creando script de rotación de secrets..."

cat > scripts/rotate_secrets.sh << 'EOF'
#!/bin/bash
# Script para rotar secrets de forma segura

set -e

echo "🔄 Rotación de Secrets"
echo "====================="
echo ""

# 1. Generar nuevos secrets
echo "Generando nuevos secrets..."
NEW_JWT_SECRET=$(openssl rand -hex 32)
NEW_API_KEY=$(openssl rand -hex 16)

echo "Nuevos secrets generados (guárdalos de forma segura):"
echo "JWT_SECRET: $NEW_JWT_SECRET"
echo "API_KEY: $NEW_API_KEY"
echo ""

# 2. Backup de configuración actual
echo "Creando backup de configuración actual..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 3. Actualizar .env
echo "Actualizando configuración..."
sed -i.bak "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT_SECRET/" .env
sed -i.bak "s/API_KEY=.*/API_KEY=$NEW_API_KEY/" .env

echo "✅ Secrets rotados exitosamente"
echo "⚠️  No olvides actualizar los secrets en:"
echo "   - Docker secrets"
echo "   - Variables de entorno de producción"
echo "   - Documentación de secrets"
EOF

chmod +x scripts/rotate_secrets.sh
echo -e "${GREEN}✓${NC} Script de rotación creado en scripts/rotate_secrets.sh"
echo ""

# REPORTE FINAL
echo ""
echo "======================================"
echo "✅ HARDENING DE SEGURIDAD COMPLETADO"
echo "======================================"
echo ""
echo "Archivos creados:"
echo "  - app/services/security/audit_logger.py"
echo "  - app/core/input_validator.py"
echo "  - docs/SECURITY_CHECKLIST.md"
echo "  - scripts/rotate_secrets.sh"
echo ""
echo "Próximos pasos:"
echo "  1. Revisar y aplicar SECURITY_CHECKLIST.md"
echo "  2. Integrar audit_logger en endpoints críticos"
echo "  3. Aplicar input_validator en validaciones Pydantic"
echo "  4. Programar rotación periódica de secrets"
echo ""
