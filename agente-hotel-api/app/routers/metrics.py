# [PROMPT GA-02] app/routers/metrics.py

from fastapi import APIRouter, Response, Request, HTTPException
from prometheus_client import Gauge, generate_latest
from app.core.settings import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])

# Readiness/Dependencies metrics
# - dependency_up{name}: 1 si la dependencia está OK en el último readiness check, 0 si no
# - readiness_up: 1 si todas las dependencias están OK, 0 si alguna falla
# - readiness_last_check_timestamp: epoch del último readiness check (para condicionar alertas)
dependency_up = Gauge("dependency_up", "Dependency up status (1 up, 0 down)", ["name"])
readiness_up = Gauge("readiness_up", "Overall readiness status (1 ready, 0 not ready)")
readiness_last_check_timestamp = Gauge(
    "readiness_last_check_timestamp", "Epoch seconds of last /health/ready execution"
)


def get_real_client_ip(request: Request) -> str:
    """
    Extraer IP real del cliente con precedencia:
    1. X-Forwarded-For (primera IP de la lista, detrás de proxies)
    2. X-Real-IP (proxy directo)
    3. request.client.host (conexión directa)

    NOTA: En producción con nginx/traefik, X-Forwarded-For debe contener
    la IP real del cliente como primera entrada.
    """
    # X-Forwarded-For puede tener múltiples IPs: "client, proxy1, proxy2"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Tomar la primera IP (cliente real)
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug(f"Client IP from X-Forwarded-For: {client_ip}")
        return client_ip

    # X-Real-IP es set por proxies como nginx
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        logger.debug(f"Client IP from X-Real-IP: {real_ip}")
        return real_ip

    # Fallback: conexión directa
    if request.client and request.client.host:
        logger.debug(f"Client IP from request.client: {request.client.host}")
        return request.client.host

    # Último fallback (no debería ocurrir)
    logger.warning("Could not determine client IP, using 0.0.0.0")
    return "0.0.0.0"


@router.get("/metrics")
async def metrics(request: Request):
    """
    Endpoint para Prometheus scraping con IP allowlist.

    Solo permite acceso desde IPs configuradas en settings.metrics_allowed_ips.
    En desarrollo, por defecto permite localhost (127.0.0.1, ::1).
    En producción, debe configurarse con IPs de Prometheus server.

    Returns:
        Response: Prometheus metrics en formato text/plain

    Raises:
        HTTPException: 403 Forbidden si IP no está en allowlist
    """
    settings = get_settings()
    client_ip = get_real_client_ip(request)

    # Validar IP contra allowlist
    if client_ip not in settings.metrics_allowed_ips:
        logger.warning(
            f"Metrics access denied for IP {client_ip}. "
            f"Allowed IPs: {settings.metrics_allowed_ips}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Forbidden",
                "message": f"IP {client_ip} is not authorized to access metrics",
                "hint": "Configure metrics_allowed_ips in settings to grant access"
            }
        )

    logger.info(f"Metrics access granted for IP {client_ip}")
    return Response(content=generate_latest(), media_type="text/plain")
