# [PROMPT 2.9] app/services/metrics_service.py


class MetricsService:
    def record_request_latency(self, endpoint: str, latency: float, status_code: int):
        # Lógica para registrar en métricas de Prometheus
        pass

    def check_slo_violations(self) -> list:
        # Lógica para comparar métricas actuales con SLOs
        # y retornar una lista de violaciones
        return []


metrics_service = MetricsService()
