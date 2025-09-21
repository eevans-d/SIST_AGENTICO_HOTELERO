# [PROMPT 2.5] app/services/nlp_engine.py

from typing import Optional
# from rasa.core.agent import Agent


class NLPEngine:
    def __init__(self, model_path: Optional[str] = None):
        # self.agent = Agent.load(model_path) if model_path else None
        pass

    async def process_message(self, text: str) -> dict:
        """Procesa un mensaje de texto para extraer intent y entidades."""
        # if not self.agent:
        #     return {"intent": {"name": "unknown", "confidence": 0.0}, "entities": []}
        # result = await self.agent.parse_message(message_data=text)
        # return result
        # Mock response hasta que se entrene y cargue un modelo Rasa
        return {"intent": {"name": "check_availability", "confidence": 0.95}, "entities": []}

    def handle_low_confidence(self, intent: dict) -> Optional[dict]:
        confidence = intent.get("confidence", 0.0)
        if confidence < 0.7:
            return {
                "response": "¿En qué puedo ayudarte?\n1️⃣ Consultar disponibilidad\n2️⃣ Ver precios\n3️⃣ Información del hotel\n4️⃣ Hablar con recepción",
                "requires_human": confidence < 0.3,
            }
        return None
