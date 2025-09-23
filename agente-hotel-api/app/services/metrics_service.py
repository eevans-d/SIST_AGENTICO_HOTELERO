# [PROMPT 2.9] app/services/metrics_service.py

from prometheus_client import Histogram, Counter, Gauge


class MetricsService:
    def __init__(self) -> None:
        # Histograma de latencia por método y endpoint (nombre alineado a dashboards)
        self.request_latency = Histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint", "status_code"],
        )
        # Contador total de requests (nombre alineado a dashboards/alertas)
        self.requests_total = Counter(
            "http_requests_total", "HTTP requests total", ["method", "endpoint", "status_code"]
        )
        # Gauge de conexiones activas (opcional)
        self.active_connections = Gauge("active_connections", "Active connections")

    def record_request_latency(self, method: str, endpoint: str, latency: float, status_code: int):
        labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code),
        }
        self.request_latency.labels(**labels).observe(latency)
        self.requests_total.labels(**labels).inc()

    def check_slo_violations(self) -> list:
        # Placeholder: devolvería lista de violaciones basado en distribución
        return []


metrics_service = MetricsService()
