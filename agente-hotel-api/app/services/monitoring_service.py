# [PROMPT 3.5] app/services/monitoring_service.py


# ... (definición de métricas custom)


class MonitoringService:
    def __init__(self):
        self.sli_thresholds = {
            "latency_text_p95": 3.0,
            "latency_audio_p95": 15.0,
            "error_rate_5xx": 0.01,
            "pms_availability": 0.995,
        }

    async def check_slo_violations(self) -> list:
        # Lógica para calcular SLIs y compararlos con los thresholds
        return []


monitoring_service = MonitoringService()
