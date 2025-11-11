#!/usr/bin/env python3
"""
Prueba de carga para el Sistema Agente Hotelero IA.

Este script utiliza Locust para simular múltiples usuarios interactuando con el sistema,
probando los diferentes endpoints y flujos de conversación.

Uso:
    1. Instalar dependencias: pip install locust
    2. Ejecutar: locust -f load_test.py
    3. Abrir interfaz web: http://localhost:8089
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List

try:
    from locust import HttpUser as LocustHttpUser, between, task  # type: ignore
    _LOCUST_AVAILABLE = True
except Exception:  # Locust no instalado
    import pytest
    pytestmark = pytest.mark.skip(reason="Locust no instalado: load test se ejecuta solo en entorno performance")
    _LOCUST_AVAILABLE = False
    class LocustHttpUser(object):  # Fallback base vacío
        pass

    def between(*args, **kwargs):  # type: ignore
        return None

    def task(*args, **kwargs):  # type: ignore
        def _decorator(fn):
            return fn
        return _decorator

# Configuración global
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Mensajes de prueba para simular conversaciones de WhatsApp
WHATSAPP_TEST_MESSAGES = [
    "Hola, quiero información sobre disponibilidad",
    "¿Tienen habitaciones disponibles para el próximo fin de semana?",
    "Quiero reservar una habitación doble",
    "¿Cuál es el precio por noche?",
    "¿Tienen desayuno incluido?",
    "¿Puedo hacer check-in tarde?",
    "¿Tienen habitaciones con vista al mar?",
    "¿Cómo puedo cancelar una reserva?",
    "¿Aceptan mascotas?",
    "¿Tienen servicio de traslado desde el aeropuerto?",
]


# Fechas para consultas de disponibilidad (próximos 90 días)
def generate_test_dates() -> List[Dict[str, str]]:
    """Genera fechas de prueba para consultas de disponibilidad."""
    dates = []
    today = datetime.now()

    for i in range(1, 90, 3):
        check_in = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        check_out = (today + timedelta(days=i + 2)).strftime("%Y-%m-%d")
        dates.append({"check_in": check_in, "check_out": check_out})

    return dates


TEST_DATES = generate_test_dates()

# IDs de prueba para simular diferentes usuarios/dispositivos
TEST_PHONE_NUMBERS = [
    "5491112345678",
    "5491187654321",
    "5491156781234",
    "5491143216789",
    "5491132165478",
    "5491198761234",
    "5491145678123",
    "5491123415678",
    "5491134567812",
    "5491178123456",
]


if _LOCUST_AVAILABLE:
    class WhatsAppUser(LocustHttpUser):  # type: ignore[misc]
        """Simula usuarios interactuando a través de WhatsApp."""

        wait_time = between(5, 30)

        def on_start(self):
            self.phone_number = random.choice(TEST_PHONE_NUMBERS)
            self.session_id = f"test_session_{self.phone_number}"

        @task(2)
        def send_text_message(self):
            message = random.choice(WHATSAPP_TEST_MESSAGES)

            payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "TEST_ACCOUNT_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": self.phone_number,
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": self.phone_number}],
                                    "messages": [
                                        {
                                            "from": self.phone_number,
                                            "id": f"test_msg_{time.time()}",
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": message},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            with self.client.post(
                "/webhooks/whatsapp", json=payload, headers=DEFAULT_HEADERS, catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Error al enviar mensaje: {response.text}")

        @task(1)
        def ask_availability(self):
            date_range = random.choice(TEST_DATES)
            message = f"¿Tienen disponibilidad desde el {date_range['check_in']} hasta el {date_range['check_out']}?"

            payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "TEST_ACCOUNT_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": self.phone_number,
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": self.phone_number}],
                                    "messages": [
                                        {
                                            "from": self.phone_number,
                                            "id": f"test_msg_{time.time()}",
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": message},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            with self.client.post(
                "/webhooks/whatsapp", json=payload, headers=DEFAULT_HEADERS, catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Error al enviar mensaje: {response.text}")

    class ApiUser(LocustHttpUser):  # type: ignore[misc]
        """Simula usuarios utilizando la API directamente."""

        wait_time = between(5, 15)

        @task(10)
        def check_health(self):
            with self.client.get("/health/live", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Error en health/live: {response.text}")
            with self.client.get("/health/ready", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Error en health/ready: {response.text}")

        @task(2)
        def get_metrics(self):
            with self.client.get("/metrics", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Error en metrics: {response.text}")

        @task(1)
        def check_feature_flags(self):
            with self.client.get("/admin/feature-flags", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Error en feature-flags: {response.text}")

    class ReservationUser(LocustHttpUser):  # type: ignore[misc]
        """Simula usuarios realizando reservas."""

        wait_time = between(30, 60)

        def on_start(self):
            self.phone_number = random.choice(TEST_PHONE_NUMBERS)
            self.session_id = f"test_session_{self.phone_number}"

        def get_random_date_range(self) -> Dict[str, str]:
            return random.choice(TEST_DATES)

        @task
        def reservation_flow(self):
            date_range = self.get_random_date_range()
            message = f"¿Tienen disponibilidad desde el {date_range['check_in']} hasta el {date_range['check_out']}?"

            availability_payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "TEST_ACCOUNT_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": self.phone_number,
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": self.phone_number}],
                                    "messages": [
                                        {
                                            "from": self.phone_number,
                                            "id": f"test_msg_{time.time()}",
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": message},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            with self.client.post(
                "/webhooks/whatsapp", json=availability_payload, headers=DEFAULT_HEADERS, catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Error al consultar disponibilidad: {response.text}")
                    return

            time.sleep(random.uniform(5, 10))

            confirm_payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "TEST_ACCOUNT_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": self.phone_number,
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": self.phone_number}],
                                    "messages": [
                                        {
                                            "from": self.phone_number,
                                            "id": f"test_msg_{time.time()}",
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": "Sí, quiero reservar una habitación doble"},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            with self.client.post(
                "/webhooks/whatsapp", json=confirm_payload, headers=DEFAULT_HEADERS, catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Error al confirmar reserva: {response.text}")
                    return

            time.sleep(random.uniform(5, 10))

            contact_payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "TEST_ACCOUNT_ID",
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": self.phone_number,
                                        "phone_number_id": "PHONE_NUMBER_ID",
                                    },
                                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": self.phone_number}],
                                    "messages": [
                                        {
                                            "from": self.phone_number,
                                            "id": f"test_msg_{time.time()}",
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": "Mi nombre es Usuario Prueba, mi email es test@example.com"},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            with self.client.post(
                "/webhooks/whatsapp", json=contact_payload, headers=DEFAULT_HEADERS, catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Error al enviar información de contacto: {response.text}")


if __name__ == "__main__":
    print("Ejecutar con: locust -f load_test.py")
