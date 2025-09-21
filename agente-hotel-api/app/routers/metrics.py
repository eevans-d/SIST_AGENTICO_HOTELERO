# [PROMPT GA-02] app/routers/metrics.py

from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest

router = APIRouter(tags=["Metrics"])

# Definir métricas
http_requests_total = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])

request_duration_seconds = Histogram("request_duration_seconds", "Request duration", ["method", "endpoint"])

active_connections = Gauge("active_connections", "Active connections")


@router.get("/metrics")
async def metrics():
    """Endpoint para Prometheus scraping"""
    return Response(content=generate_latest(), media_type="text/plain")
