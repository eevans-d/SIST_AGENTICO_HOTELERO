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
        
        # ---- Hotel Business Metrics ----
        # Reservation funnel metrics
        self.reservation_inquiries_total = Counter(
            "hotel_reservation_inquiries_total", "Total reservation inquiries", ["source", "room_type"]
        )
        self.reservation_confirmed_total = Counter(
            "hotel_reservations_confirmed_total", "Total confirmed reservations", ["room_type", "lead_time"]
        )
        self.reservation_cancelled_total = Counter(
            "hotel_reservations_cancelled_total", "Total cancelled reservations", ["reason", "room_type"]
        )
        
        # Occupancy and revenue metrics
        self.room_occupancy_rate = Gauge(
            "hotel_room_occupancy_rate", "Current room occupancy rate (0-1)", ["room_type"]
        )
        self.average_daily_rate = Gauge(
            "hotel_average_daily_rate", "Average daily rate in currency units", ["room_type"]
        )
        self.revenue_per_available_room = Gauge(
            "hotel_revenue_per_available_room", "RevPAR metric", ["room_type"]
        )
        
        # Guest communication metrics  
        self.guest_response_time = Histogram(
            "hotel_guest_response_time_seconds", "Time to respond to guest queries", ["channel", "intent"]
        )
        self.guest_satisfaction_score = Gauge(
            "hotel_guest_satisfaction_score", "Guest satisfaction score (1-5)", ["interaction_type"]
        )
        
        # PMS integration health
        self.pms_operation_success_rate = Gauge(
            "hotel_pms_operation_success_rate", "PMS operation success rate (0-1)", ["operation"]
        )
        self.availability_check_duration = Histogram(
            "hotel_availability_check_duration_seconds", "Time to check room availability"
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
    
    # ---- Hotel Business Operations ----
    def record_reservation_inquiry(self, source: str, room_type: str):
        """Record a reservation inquiry from a guest"""
        self.reservation_inquiries_total.labels(source=source, room_type=room_type).inc()
    
    def record_reservation_confirmed(self, room_type: str, lead_time_days: int):
        """Record a confirmed reservation"""
        lead_time_category = "same_day" if lead_time_days == 0 else (
            "1-7_days" if lead_time_days <= 7 else "8+_days"
        )
        self.reservation_confirmed_total.labels(room_type=room_type, lead_time=lead_time_category).inc()
    
    def record_reservation_cancelled(self, reason: str, room_type: str):
        """Record a cancelled reservation"""
        self.reservation_cancelled_total.labels(reason=reason, room_type=room_type).inc()
    
    def update_occupancy_metrics(self, room_type: str, occupancy_rate: float, adr: float):
        """Update occupancy and revenue metrics"""
        self.room_occupancy_rate.labels(room_type=room_type).set(occupancy_rate)
        self.average_daily_rate.labels(room_type=room_type).set(adr)
        self.revenue_per_available_room.labels(room_type=room_type).set(occupancy_rate * adr)
    
    def record_guest_response_time(self, channel: str, intent: str, response_time_seconds: float):
        """Record time to respond to guest queries"""
        self.guest_response_time.labels(channel=channel, intent=intent).observe(response_time_seconds)
    
    def update_guest_satisfaction(self, interaction_type: str, score: float):
        """Update guest satisfaction score (1-5 scale)"""
        self.guest_satisfaction_score.labels(interaction_type=interaction_type).set(score)
    
    def record_pms_operation(self, operation: str, success: bool, duration_seconds: float = None):
        """Record PMS operation success/failure and duration"""
        if operation == "availability_check" and duration_seconds:
            self.availability_check_duration.observe(duration_seconds)
        
        # Track success rates (would need historical tracking for true rate calculation)
        # For now, this is a simplified version
        current_rate = 1.0 if success else 0.0
        self.pms_operation_success_rate.labels(operation=operation).set(current_rate)


metrics_service = MetricsService()
