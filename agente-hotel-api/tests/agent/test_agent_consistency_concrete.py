"""
P006: Agent Consistency Tests - IMPLEMENTACIÓN CONCRETA

Tests de consistencia del agente IA para validar:
- Determinismo en respuestas
- Preservación de contexto
- Consistencia temporal
- Comportamiento bajo carga

Ejecutar:
    pytest tests/agent/test_agent_consistency_concrete.py -v --tb=short
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
import hashlib

from app.services.orchestrator import Orchestrator
from app.services.nlp_engine import NLPEngine
from app.services.session_manager import SessionManager
from app.models.unified_message import UnifiedMessage


# ===== FIXTURES =====


@pytest_asyncio.fixture
async def orchestrator():
    """Orchestrator instance"""
    orch = Orchestrator()
    await orch.start()
    yield orch
    await orch.stop()


@pytest_asyncio.fixture
async def nlp_engine():
    """NLP engine instance"""
    engine = NLPEngine()
    await engine.start()
    yield engine
    await engine.stop()


@pytest_asyncio.fixture
async def session_manager():
    """Session manager instance"""
    manager = SessionManager()
    await manager.start()
    yield manager
    await manager.stop()


# ===== RESPONSE CONSISTENCY =====


class TestResponseDeterminism:
    """Validar que mismo input produce output consistente"""

    @pytest.mark.asyncio
    async def test_identical_greeting_produces_same_response(self, orchestrator):
        """Saludo idéntico debe producir respuesta consistente"""
        user_id = "consistency_greeting_001"

        responses = []
        for i in range(5):
            msg = UnifiedMessage(
                message_id=f"greeting_{i}",
                user_id=user_id,
                text="Hola, buenos días",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            result = await orchestrator.process_message(msg)
            responses.append(result["response"])

        # Todas las respuestas deben ser idénticas o muy similares
        unique_responses = len(set(responses))
        assert unique_responses <= 2, f"Too many variations: {unique_responses} unique responses"

    @pytest.mark.asyncio
    async def test_availability_query_intent_consistency(self, nlp_engine):
        """Consultas de disponibilidad deben detectar mismo intent"""
        queries = [
            "¿Tienen habitaciones disponibles?",
            "Hay cuartos libres?",
            "Disponibilidad para mañana",
        ]

        intents = []
        for query in queries:
            result = await nlp_engine.parse_intent(query)
            intents.append(result.intent)

        # Todos deben ser availability-related
        for intent in intents:
            assert intent in ["check_availability", "inquire", "availability"], f"Unexpected intent: {intent}"

    @pytest.mark.asyncio
    async def test_entity_extraction_stable(self, nlp_engine):
        """Extracción de entidades debe ser estable"""
        text = "Habitación para 2 personas del 15 al 18 de marzo"

        all_entities = []
        for _ in range(5):
            result = await nlp_engine.parse_intent(text)
            entities = {
                "guests": result.entities.get("guests"),
                "check_in_date": result.entities.get("check_in"),
                "check_out_date": result.entities.get("check_out"),
            }
            all_entities.append(str(entities))  # Stringify for comparison

        # Todas las extracciones deben ser idénticas
        unique_extractions = len(set(all_entities))
        assert unique_extractions == 1, f"Inconsistent extractions: {unique_extractions} variants"

    @pytest.mark.asyncio
    async def test_pricing_response_template_consistent(self, orchestrator):
        """Template de respuesta de pricing debe ser consistente"""
        user_id = "pricing_consistency_001"

        responses = []
        for i in range(5):
            msg = UnifiedMessage(
                message_id=f"pricing_{i}",
                user_id=user_id,
                text="¿Cuánto cuesta una habitación?",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            result = await orchestrator.process_message(msg)
            responses.append(result["response"])

        # Hashear respuestas para detectar similitud
        hashes = [hashlib.md5(r.encode()).hexdigest()[:10] for r in responses]
        unique_hashes = set(hashes)

        # Máximo 2 variaciones aceptables
        assert len(unique_hashes) <= 2, f"Too many response variations: {len(unique_hashes)}"

    @pytest.mark.asyncio
    async def test_error_messages_deterministic(self, orchestrator):
        """Mensajes de error deben ser determinísticos"""
        user_id = "error_consistency_001"

        error_responses = []
        for i in range(3):
            msg = UnifiedMessage(
                message_id=f"error_{i}",
                user_id=user_id,
                text="Reservar para el 31 de febrero",  # Fecha inválida
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            result = await orchestrator.process_message(msg)
            error_responses.append(result["response"])

        # Mensajes de error deben ser idénticos
        assert len(set(error_responses)) == 1, f"Inconsistent error messages: {set(error_responses)}"

    @pytest.mark.asyncio
    async def test_confidence_scores_stable(self, nlp_engine):
        """Confidence scores deben tener baja variación"""
        text = "Quiero hacer una reserva"

        confidences = []
        for _ in range(10):
            result = await nlp_engine.parse_intent(text)
            confidences.append(result.confidence)

        # Calcular coeficiente de variación (CV)
        avg_conf = sum(confidences) / len(confidences)
        variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
        std_dev = variance**0.5
        cv = std_dev / avg_conf if avg_conf > 0 else 0

        # CV debe ser menor a 10%
        assert cv < 0.10, f"High confidence variation: CV={cv:.2%}"

    @pytest.mark.asyncio
    async def test_language_detection_consistent(self, nlp_engine):
        """Detección de idioma debe ser consistente"""
        test_cases = {
            "es": "¿Tienen habitaciones disponibles?",
            "en": "Do you have rooms available?",
        }

        for expected_lang, text in test_cases.items():
            detected_langs = []
            for _ in range(5):
                result = await nlp_engine.parse_intent(text)
                detected_langs.append(result.language)

            # Todas las detecciones deben ser idénticas
            assert len(set(detected_langs)) == 1, f"Inconsistent language detection: {set(detected_langs)}"
            assert detected_langs[0] == expected_lang, f"Wrong language: {detected_langs[0]} vs {expected_lang}"

    @pytest.mark.asyncio
    async def test_pii_redaction_always_applied(self, orchestrator):
        """Redacción de PII debe aplicarse siempre"""
        user_id = "pii_consistency_001"

        for i in range(5):
            msg = UnifiedMessage(
                message_id=f"pii_{i}",
                user_id=user_id,
                text="Mi email es carlos@test.com y teléfono +34611222333",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            result = await orchestrator.process_message(msg)

            # PII nunca debe aparecer en respuesta o logs
            response_lower = result["response"].lower()
            assert "carlos@test.com" not in response_lower, "Email leaked"
            assert "+34611222333" not in str(result), "Phone leaked"


# ===== CONTEXT PRESERVATION =====


class TestContextConsistency:
    """Validar preservación y manejo de contexto"""

    @pytest.mark.asyncio
    async def test_context_preserved_between_messages(self, orchestrator, session_manager):
        """Contexto debe preservarse entre mensajes"""
        user_id = "context_preserve_001"

        # Mensaje 1: Establecer contexto
        msg1 = UnifiedMessage(
            message_id="ctx_msg1",
            user_id=user_id,
            text="Habitación para 2 personas",
            timestamp=datetime.now(),
            channel="whatsapp",
        )
        await orchestrator.process_message(msg1)

        # Mensaje 2: Usar contexto implícito
        msg2 = UnifiedMessage(
            message_id="ctx_msg2",
            user_id=user_id,
            text="Del 20 al 23 de marzo",
            timestamp=datetime.now() + timedelta(seconds=5),
            channel="whatsapp",
        )
        result2 = await orchestrator.process_message(msg2)

        # Respuesta debe reflejar contexto previo (2 personas)
        response = result2["response"].lower()
        assert any(word in response for word in ["2 personas", "dos huéspedes", "2 adultos"]), (
            "Context not preserved in response"
        )

        # Verificar sesión
        session = await session_manager.get_session(user_id)
        assert session.get("guest_count") == 2 or session.get("guests") == 2, "Guest count not in session"

    @pytest.mark.asyncio
    async def test_context_isolated_between_users(self, orchestrator, session_manager):
        """Contexto debe estar aislado entre usuarios"""
        user1 = "user_isolation_001"
        user2 = "user_isolation_002"

        # Usuario 1: 2 personas
        msg1 = UnifiedMessage(
            message_id="iso1", user_id=user1, text="Para 2 personas", timestamp=datetime.now(), channel="whatsapp"
        )
        await orchestrator.process_message(msg1)

        # Usuario 2: 4 personas
        msg2 = UnifiedMessage(
            message_id="iso2", user_id=user2, text="Para 4 personas", timestamp=datetime.now(), channel="whatsapp"
        )
        await orchestrator.process_message(msg2)

        # Verificar aislamiento
        session1 = await session_manager.get_session(user1)
        session2 = await session_manager.get_session(user2)

        guests1 = session1.get("guest_count") or session1.get("guests")
        guests2 = session2.get("guest_count") or session2.get("guests")

        assert guests1 == 2, f"User 1 context contaminated: {guests1}"
        assert guests2 == 4, f"User 2 context contaminated: {guests2}"

    @pytest.mark.asyncio
    async def test_context_cleared_after_timeout(self, orchestrator, session_manager):
        """Contexto debe limpiarse después de timeout"""
        user_id = "context_timeout_001"

        # Establecer contexto
        msg1 = UnifiedMessage(
            message_id="timeout1",
            user_id=user_id,
            text="Habitación deluxe",
            timestamp=datetime.now(),
            channel="whatsapp",
        )
        await orchestrator.process_message(msg1)

        # Forzar expiración de sesión
        await session_manager.expire_session(user_id)
        await asyncio.sleep(1)

        # Nuevo mensaje después de timeout
        msg2 = UnifiedMessage(
            message_id="timeout2",
            user_id=user_id,
            text="Hola",
            timestamp=datetime.now() + timedelta(minutes=31),
            channel="whatsapp",
        )
        await orchestrator.process_message(msg2)

        # Sesión debe estar vacía o reseteada
        session = await session_manager.get_session(user_id)
        assert session.get("room_type") != "deluxe", "Context not cleared"

    @pytest.mark.asyncio
    async def test_context_updated_on_correction(self, orchestrator, session_manager):
        """Contexto debe actualizarse cuando usuario corrige"""
        user_id = "context_update_001"

        # Información inicial
        msg1 = UnifiedMessage(
            message_id="upd1", user_id=user_id, text="Para 2 personas", timestamp=datetime.now(), channel="whatsapp"
        )
        await orchestrator.process_message(msg1)

        # Corrección
        msg2 = UnifiedMessage(
            message_id="upd2",
            user_id=user_id,
            text="Perdón, somos 3 personas",
            timestamp=datetime.now() + timedelta(seconds=5),
            channel="whatsapp",
        )
        await orchestrator.process_message(msg2)

        # Contexto debe reflejar corrección
        session = await session_manager.get_session(user_id)
        guests = session.get("guest_count") or session.get("guests")
        assert guests == 3, f"Context not updated: {guests}"

    @pytest.mark.asyncio
    async def test_multi_intent_context_handling(self, orchestrator):
        """Contexto debe manejarse en conversaciones multi-intent"""
        user_id = "multi_intent_001"

        # Intent 1: Availability
        msg1 = UnifiedMessage(
            message_id="mi1",
            user_id=user_id,
            text="¿Tienen habitaciones?",
            timestamp=datetime.now(),
            channel="whatsapp",
        )
        await orchestrator.process_message(msg1)

        # Intent 2: Pricing (manteniendo contexto)
        msg2 = UnifiedMessage(
            message_id="mi2",
            user_id=user_id,
            text="¿Cuánto cuesta?",
            timestamp=datetime.now() + timedelta(seconds=3),
            channel="whatsapp",
        )
        result2 = await orchestrator.process_message(msg2)

        # Debe responder sobre precio
        response = result2["response"].lower()
        assert any(word in response for word in ["precio", "cuesta", "€", "$"]), "Didn't answer pricing question"


# ===== TEMPORAL CONSISTENCY =====


class TestTemporalConsistency:
    """Validar consistencia en respuestas temporales"""

    @pytest.mark.asyncio
    async def test_date_validation_stable(self, nlp_engine):
        """Validación de fechas debe ser consistente"""
        past_date = "Reservar para el 1 de enero de 2020"

        validations = []
        for _ in range(5):
            result = await nlp_engine.parse_intent(past_date)
            # Asumiendo que devuelve error o validation status
            validations.append(result.entities.get("date_valid", True))

        # Todas deben detectar fecha inválida
        assert all(not v for v in validations) or all("past" in str(v).lower() for v in validations), (
            "Inconsistent date validation"
        )

    @pytest.mark.asyncio
    async def test_business_hours_response_stable(self, orchestrator):
        """Información de horarios debe ser consistente"""
        user_id = "hours_consistency_001"

        responses = []
        for i in range(5):
            msg = UnifiedMessage(
                message_id=f"hours_{i}",
                user_id=user_id,
                text="¿A qué hora abren?",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            result = await orchestrator.process_message(msg)
            responses.append(result["response"])

        # Horarios deben ser idénticos
        assert len(set(responses)) == 1, f"Inconsistent hours: {set(responses)}"


# ===== LOAD CONSISTENCY =====


class TestLoadConsistency:
    """Validar consistencia bajo carga concurrente"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_user(self, orchestrator):
        """Múltiples requests del mismo usuario deben ser consistentes"""
        user_id = "concurrent_user_001"

        # Crear 10 mensajes idénticos
        messages = [
            UnifiedMessage(
                message_id=f"conc_{i}",
                user_id=user_id,
                text="¿Tienen habitaciones?",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            for i in range(10)
        ]

        # Procesar concurrentemente
        tasks = [orchestrator.process_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Contar éxitos
        successful = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful) / len(results)

        assert success_rate >= 0.8, f"Low success rate: {success_rate:.1%}"

    @pytest.mark.asyncio
    async def test_different_users_concurrent(self, orchestrator):
        """Requests de diferentes usuarios no deben interferir"""
        # 10 usuarios diferentes
        messages = [
            UnifiedMessage(
                message_id=f"user{i}_msg",
                user_id=f"concurrent_test_{i}",
                text=f"Habitación para {i + 1} personas",
                timestamp=datetime.now(),
                channel="whatsapp",
            )
            for i in range(10)
        ]

        # Procesar concurrentemente
        tasks = [orchestrator.process_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Todos deben procesarse exitosamente
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"Errors in concurrent processing: {len(errors)}"

    @pytest.mark.asyncio
    async def test_response_latency_stable_under_load(self, orchestrator):
        """Latencia debe ser estable bajo carga moderada"""
        import time

        user_id = "latency_test_001"

        latencies = []
        for i in range(20):
            msg = UnifiedMessage(
                message_id=f"lat_{i}",
                user_id=user_id,
                text="Disponibilidad",
                timestamp=datetime.now(),
                channel="whatsapp",
            )

            start = time.time()
            await orchestrator.process_message(msg)
            latency = time.time() - start
            latencies.append(latency)

        # Calcular P95
        latencies_sorted = sorted(latencies)
        p95 = latencies_sorted[int(len(latencies) * 0.95)]

        # P95 debe ser razonable
        assert p95 < 3.0, f"P95 latency too high: {p95:.2f}s"

        # Calcular coeficiente de variación
        avg = sum(latencies) / len(latencies)
        variance = sum((lat - avg) ** 2 for lat in latencies) / len(latencies)
        std_dev = variance**0.5
        cv = std_dev / avg if avg > 0 else 0

        # CV debe ser menor a 50%
        assert cv < 0.5, f"High latency variation: CV={cv:.1%}"


# ===== EDGE CASES =====


class TestConsistencyEdgeCases:
    """Tests de casos extremos"""

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, orchestrator):
        """Mensajes vacíos deben manejarse consistentemente"""
        user_id = "empty_msg_001"

        responses = []
        for i in range(3):
            msg = UnifiedMessage(
                message_id=f"empty_{i}", user_id=user_id, text="", timestamp=datetime.now(), channel="whatsapp"
            )
            result = await orchestrator.process_message(msg)
            responses.append(result["response"])

        # Respuestas deben ser consistentes
        assert len(set(responses)) <= 1, "Inconsistent empty message handling"

    @pytest.mark.asyncio
    async def test_special_characters_stable(self, nlp_engine):
        """Caracteres especiales deben manejarse consistentemente"""
        texts_with_special = [
            "¿Habitación disponible? 😊",
            "Reserva para 2 personas ✨",
        ]

        for text in texts_with_special:
            intents = []
            for _ in range(3):
                result = await nlp_engine.parse_intent(text)
                intents.append(result.intent)

            # Intent debe ser consistente
            assert len(set(intents)) == 1, f"Inconsistent intent with special chars: {set(intents)}"

    @pytest.mark.asyncio
    async def test_very_long_message_handling(self, orchestrator):
        """Mensajes muy largos deben manejarse consistentemente"""
        user_id = "long_msg_001"
        long_text = "Necesito reservar " * 100  # ~300 palabras

        responses = []
        for i in range(3):
            msg = UnifiedMessage(
                message_id=f"long_{i}", user_id=user_id, text=long_text, timestamp=datetime.now(), channel="whatsapp"
            )
            result = await orchestrator.process_message(msg)
            responses.append(result["response"])

        # Manejo debe ser consistente (truncar, error, etc.)
        assert len(set(responses)) <= 2, "Inconsistent long message handling"
