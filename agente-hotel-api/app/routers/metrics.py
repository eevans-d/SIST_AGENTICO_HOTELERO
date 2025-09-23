# [PROMPT GA-02] app/routers/metrics.py

from fastapi import APIRouter, Response
from prometheus_client import Gauge, generate_latest

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


@router.get("/metrics")
async def metrics():
    """Endpoint para Prometheus scraping"""
    return Response(content=generate_latest(), media_type="text/plain")
