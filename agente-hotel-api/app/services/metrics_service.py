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
        # Gauge para feature flags (1=enabled,0=disabled)
        self.feature_flag_enabled = Gauge(
            "feature_flag_enabled", "Estado actual de un feature flag", ["flag"]
        )
        # Métricas multi-tenant (fase 5 groundwork)
        self.tenant_request_total = Counter(
            "tenant_request_total", "Total de requests por tenant", ["tenant_id"]
        )
        self.tenant_request_errors = Counter(
            "tenant_request_errors", "Errores de requests por tenant", ["tenant_id"]
        )
        # Métricas NLP (fase 5) – categorías de confianza y fallbacks activados
        self.nlp_confidence_category_total = Counter(
            "nlp_confidence_category_total",
            "Total de intents clasificados por categoría de confianza",
            ["category"],
        )
        self.nlp_fallback_total = Counter(
            "nlp_fallback_total", "Total de fallbacks NLP activados por razón", ["reason"]
        )

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

    # ---- Feature Flags ----
    def update_feature_flag(self, flag: str, enabled: bool):
        self.feature_flag_enabled.labels(flag=flag).set(1 if enabled else 0)

    # ---- Tenancy ----
    def inc_tenant_request(self, tenant_id: str, error: bool = False):
        self.tenant_request_total.labels(tenant_id=tenant_id).inc()
        if error:
            self.tenant_request_errors.labels(tenant_id=tenant_id).inc()

    # ---- NLP Confidence & Fallback ----
    def categorize_confidence(self, confidence: float) -> str:
        if confidence < 0.45:
            return "low"
        if confidence < 0.75:
            return "medium"
        return "high"

    def record_nlp_confidence(self, confidence: float):
        category = self.categorize_confidence(confidence)
        try:
            self.nlp_confidence_category_total.labels(category=category).inc()
        except Exception:  # pragma: no cover
            pass
        return category

    def record_nlp_fallback(self, reason: str):
        try:
            self.nlp_fallback_total.labels(reason=reason).inc()
        except Exception:  # pragma: no cover
            pass


metrics_service = MetricsService()
