# [PROMPT 2.9] app/services/metrics_service.py

from prometheus_client import Counter, Histogram, Gauge
from ..core.prometheus import (
    registry,
    http_requests_total as core_http_requests_total,
    http_request_duration_seconds as core_http_request_duration_seconds,
)


# ===================== NORMALIZACIÓN MENSAJES =====================
MESSAGE_NORMALIZED_TOTAL = Counter(
    "message_normalized_total",
    "Total de mensajes inbound normalizados por canal y tenant",
    ["canal", "tenant_id"],
    registry=registry,
)

MESSAGE_NORMALIZATION_ERRORS_TOTAL = Counter(
    "message_normalization_errors_total",
    "Errores de normalización de mensajes inbound por canal y tipo",
    ["canal", "error_type"],
    registry=registry,
)

MESSAGE_NORMALIZATION_LATENCY_SECONDS = Histogram(
    "message_normalization_latency_seconds",
    "Latencia de normalización de mensajes por canal",
    ["canal"],
    registry=registry,
)


class MetricsService:
    def __init__(self) -> None:
        # Histograma de latencia por método y endpoint (nombre alineado a dashboards)
        # Usar métricas centrales para evitar duplicidades
        self.request_latency = core_http_request_duration_seconds
        # Contador total de requests (métrica central)
        self.requests_total = core_http_requests_total
        # Gauge de conexiones activas (opcional)
        self.active_connections = Gauge("active_connections", "Active connections", registry=registry)
        # Gauge para feature flags (1=enabled,0=disabled)
        self.feature_flag_enabled = Gauge(
            "feature_flag_enabled", "Estado actual de un feature flag", ["flag"], registry=registry
        )
        # Métricas multi-tenant (fase 5 groundwork)
        self.tenant_request_total = Counter(
            "tenant_request_total", "Total de requests por tenant", ["tenant_id"], registry=registry
        )
        self.tenant_request_errors = Counter(
            "tenant_request_errors", "Errores de requests por tenant", ["tenant_id"], registry=registry
        )
        # Métricas NLP (fase 5) – categorías de confianza y fallbacks activados
        self.nlp_confidence_category_total = Counter(
            "nlp_confidence_category_total",
            "Total de intents clasificados por categoría de confianza",
            ["category"],
            registry=registry,
        )
        self.nlp_fallback_total = Counter(
            "nlp_fallback_total", "Total de fallbacks NLP activados por razón", ["reason"], registry=registry
        )

        # ---- Seguridad / Sesiones / Base de Datos ----
        # Gauge de sesiones JWT activas (en BD): recuento de sesiones no expiradas y no revocadas
        self.jwt_sessions_active = Gauge(
            "jwt_sessions_active",
            "Número de sesiones JWT activas (no expiradas, no revocadas) registradas en BD",
            registry=registry,
        )

        # Gauge de conexiones activas a la base de datos (vista desde la app)
        self.db_connections_active = Gauge(
            "db_connections_active",
            "Número de conexiones activas a la base de datos (pg_stat_activity)",
            registry=registry,
        )

        # Contador de rotaciones de password
        self.password_rotations_total = Counter(
            "password_rotations_total",
            "Total de rotaciones de password por resultado",
            ["result"],
            registry=registry,
        )

        # Contador de timeouts de sentencias (statement_timeout)
        self.db_statement_timeouts_total = Counter(
            "db_statement_timeouts_total",
            "Total de ocurrencias de statement_timeout detectadas en la aplicación",
            registry=registry,
        )

    def record_request_latency(self, method: str, endpoint: str, latency: float, status_code: int):
        # Histograma no incluye status_code; el contador sí
        self.request_latency.labels(method=method, endpoint=endpoint).observe(latency)
        self.requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()

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

    # ---- Normalización de Mensajes ----
    def record_message_normalized(self, canal: str, tenant_id: str = "unknown"):
        try:
            MESSAGE_NORMALIZED_TOTAL.labels(canal=canal, tenant_id=tenant_id or "unknown").inc()
        except Exception:
            pass

    def record_message_normalization_error(self, canal: str, error_type: str):
        try:
            MESSAGE_NORMALIZATION_ERRORS_TOTAL.labels(canal=canal, error_type=error_type[:32]).inc()
        except Exception:
            pass

    def time_message_normalization(self, canal: str):
        return MESSAGE_NORMALIZATION_LATENCY_SECONDS.labels(canal=canal).time()

    # ---- Seguridad / Sesiones / BD (helpers públicos) ----
    def set_jwt_sessions_active(self, count: int):
        try:
            self.jwt_sessions_active.set(max(0, int(count)))
        except Exception:
            pass

    def set_db_connections_active(self, count: int):
        try:
            self.db_connections_active.set(max(0, int(count)))
            # Mantener compatibilidad con gauge genérico si alguien lo usa
            try:
                self.active_connections.set(max(0, int(count)))
            except Exception:
                pass
        except Exception:
            pass

    def inc_password_rotation(self, result: str = "success"):
        try:
            self.password_rotations_total.labels(result=result).inc()
        except Exception:
            pass

    def inc_statement_timeout(self):
        try:
            self.db_statement_timeouts_total.inc()
        except Exception:
            pass


metrics_service = MetricsService()
