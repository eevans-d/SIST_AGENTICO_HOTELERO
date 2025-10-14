# [PHASE D.6] tests/load/locustfile.py

"""
Locust load testing script para Agente Hotel API.

Simula carga realista de usuarios consultando disponibilidad y haciendo reservas.

Uso:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Con parámetros:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m
"""

from locust import HttpUser, task, between, events
import random
from datetime import datetime, timedelta


class HotelGuestUser(HttpUser):
    """Simula un usuario consultando y reservando en el hotel."""

    # Tiempo de espera entre requests (simulando usuario real)
    wait_time = between(2, 5)

    # Tenant ID para multi-tenant testing
    tenant_id = "hotel-default"

    def on_start(self):
        """Ejecutado al inicio de cada usuario virtual."""
        self.user_id = f"test_user_{random.randint(1000, 9999)}"
        self.checkin = datetime.now() + timedelta(days=random.randint(1, 30))
        self.checkout = self.checkin + timedelta(days=random.randint(1, 7))

    @task(3)
    def check_health(self):
        """Health check - peso 3 (más frecuente)."""
        with self.client.get("/health/live", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(10)
    def check_availability(self):
        """Consulta disponibilidad - peso 10 (operación principal)."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "123456"},
                                "messages": [
                                    {
                                        "from": self.user_id,
                                        "id": f"msg_{random.randint(1000, 9999)}",
                                        "timestamp": str(int(datetime.now().timestamp())),
                                        "type": "text",
                                        "text": {
                                            "body": f"Hola, quisiera saber disponibilidad para {self.checkin.strftime('%Y-%m-%d')}"
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=mock_signature_for_testing",  # En load testing, bypass signature
        }

        with self.client.post("/webhooks/whatsapp", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Availability check failed: {response.status_code}")

    @task(5)
    def make_reservation(self):
        """Intento de reserva - peso 5."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "123456"},
                                "messages": [
                                    {
                                        "from": self.user_id,
                                        "id": f"msg_{random.randint(1000, 9999)}",
                                        "timestamp": str(int(datetime.now().timestamp())),
                                        "type": "text",
                                        "text": {
                                            "body": f"Quiero reservar habitación del {self.checkin.strftime('%d/%m')} al {self.checkout.strftime('%d/%m')}"
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        headers = {"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=mock_signature_for_testing"}

        with self.client.post("/webhooks/whatsapp", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Reservation failed: {response.status_code}")

    @task(2)
    def get_metrics(self):
        """Consulta métricas - peso 2 (menos frecuente)."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")

    @task(1)
    def admin_dashboard(self):
        """Acceso al dashboard admin - peso 1 (poco frecuente)."""
        # Simula token de autenticación
        headers = {"Authorization": "Bearer test_token"}

        with self.client.get("/admin/dashboard", headers=headers, catch_response=True) as response:
            if response.status_code in [200, 401]:  # 401 es esperado sin auth real
                response.success()
            else:
                response.failure(f"Admin dashboard failed: {response.status_code}")


@events.init_command_line_parser.add_listener
def _(parser):
    """Añade argumentos personalizados a Locust CLI."""
    parser.add_argument("--tenant-id", type=str, default="hotel-default", help="Tenant ID para testing multi-tenant")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Ejecutado al inicio del test."""
    print("🚀 Iniciando load testing de Agente Hotel API")
    print(f"   Target: {environment.host}")
    print(
        f"   Tenant: {environment.parsed_options.tenant_id if hasattr(environment.parsed_options, 'tenant_id') else 'default'}"
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Ejecutado al finalizar el test."""
    print("✅ Load testing completado")
    stats = environment.stats
    print(f"   Total requests: {stats.total.num_requests}")
    print(f"   Failures: {stats.total.num_failures}")
    print(f"   Avg response time: {stats.total.avg_response_time:.2f}ms")
    print(f"   RPS: {stats.total.total_rps:.2f}")
