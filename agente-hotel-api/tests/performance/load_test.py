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

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from locust import HttpUser, between, task

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
        check_out = (today + timedelta(days=i+2)).strftime("%Y-%m-%d")
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


class WhatsAppUser(HttpUser):
    """
    Simula usuarios interactuando a través de WhatsApp.
    
    Esta clase envía mensajes al webhook de WhatsApp en formato similar
    al de la API de WhatsApp, probando la capacidad del sistema para
    procesar mensajes entrantes.
    """
    # Tiempo de espera entre solicitudes (entre 5 y 30 segundos)
    wait_time = between(5, 30)
    
    def on_start(self):
        """Inicialización por usuario."""
        self.phone_number = random.choice(TEST_PHONE_NUMBERS)
        self.session_id = f"test_session_{self.phone_number}"
    
    @task(2)
    def send_text_message(self):
        """Envía un mensaje de texto aleatorio."""
        message = random.choice(WHATSAPP_TEST_MESSAGES)
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number,
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "Test User"
                            },
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"test_msg_{time.time()}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": message
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Enviar webhook
        with self.client.post(
            "/webhooks/whatsapp",
            json=payload,
            headers=DEFAULT_HEADERS,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Error al enviar mensaje: {response.text}")
    
    @task(1)
    def ask_availability(self):
        """Consulta disponibilidad con fechas aleatorias."""
        date_range = random.choice(TEST_DATES)
        message = f"¿Tienen disponibilidad desde el {date_range['check_in']} hasta el {date_range['check_out']}?"
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number,
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "Test User"
                            },
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"test_msg_{time.time()}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": message
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Enviar webhook
        with self.client.post(
            "/webhooks/whatsapp",
            json=payload,
            headers=DEFAULT_HEADERS,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Error al enviar mensaje: {response.text}")


class ApiUser(HttpUser):
    """
    Simula usuarios utilizando la API directamente.
    
    Esta clase prueba los endpoints de la API, como los endpoints de salud,
    métricas y administrativos.
    """
    # Tiempo de espera entre solicitudes (entre 5 y 15 segundos)
    wait_time = between(5, 15)
    
    @task(10)
    def check_health(self):
        """Verifica el endpoint de salud."""
        with self.client.get("/health/live", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Error en health/live: {response.text}")
        
        with self.client.get("/health/ready", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Error en health/ready: {response.text}")
    
    @task(2)
    def get_metrics(self):
        """Obtiene métricas de Prometheus."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Error en metrics: {response.text}")
    
    @task(1)
    def check_feature_flags(self):
        """Consulta los feature flags activos."""
        with self.client.get("/admin/feature-flags", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Error en feature-flags: {response.text}")


class ReservationUser(HttpUser):
    """
    Simula usuarios realizando reservas.
    
    Esta clase prueba el flujo completo de reservas, desde la consulta
    de disponibilidad hasta la creación de reservas.
    """
    # Tiempo de espera entre solicitudes (entre 30 y 60 segundos)
    wait_time = between(30, 60)
    
    def on_start(self):
        """Inicialización por usuario."""
        self.phone_number = random.choice(TEST_PHONE_NUMBERS)
        self.session_id = f"test_session_{self.phone_number}"
    
    def get_random_date_range(self) -> Dict[str, str]:
        """Obtiene un rango de fechas aleatorio."""
        return random.choice(TEST_DATES)
    
    @task
    def reservation_flow(self):
        """Simula un flujo completo de reserva."""
        # 1. Consultar disponibilidad
        date_range = self.get_random_date_range()
        message = f"¿Tienen disponibilidad desde el {date_range['check_in']} hasta el {date_range['check_out']}?"
        
        availability_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number,
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "Test User"
                            },
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"test_msg_{time.time()}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": message
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Enviar mensaje de disponibilidad
        with self.client.post(
            "/webhooks/whatsapp",
            json=availability_payload,
            headers=DEFAULT_HEADERS,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Error al consultar disponibilidad: {response.text}")
                return
        
        # Esperar para simular tiempo de respuesta del usuario
        time.sleep(random.uniform(5, 10))
        
        # 2. Confirmar reserva
        confirm_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number,
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "Test User"
                            },
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"test_msg_{time.time()}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": "Sí, quiero reservar una habitación doble"
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Enviar mensaje de confirmación
        with self.client.post(
            "/webhooks/whatsapp",
            json=confirm_payload,
            headers=DEFAULT_HEADERS,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Error al confirmar reserva: {response.text}")
                return
        
        # Esperar para simular tiempo de respuesta del usuario
        time.sleep(random.uniform(5, 10))
        
        # 3. Proporcionar información de contacto
        contact_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number,
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "Test User"
                            },
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"test_msg_{time.time()}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": "Mi nombre es Usuario Prueba, mi email es test@example.com"
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Enviar información de contacto
        with self.client.post(
            "/webhooks/whatsapp",
            json=contact_payload,
            headers=DEFAULT_HEADERS,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Error al enviar información de contacto: {response.text}")


if __name__ == "__main__":
    print("Ejecutar con: locust -f load_test.py")