"""
Agent Consistency Testing Template

Valida que el agente IA produce respuestas consistentes bajo el mismo contexto.
Detecta regresiones en comportamiento y calidad de respuestas.
"""

import pytest
import asyncio
import statistics
from difflib import SequenceMatcher
from typing import List, Dict
import warnings

# Ajustar import según la estructura del proyecto
from app.services.nlp_engine import NLPEngine


class AgentConsistencyTester:
    """Helper class para medir consistencia de respuestas del agente"""

    def __init__(self, agent_client):
        self.agent = agent_client
        self.results = []

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud entre dos textos (0-1)"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    async def test_scenario(self, prompt: str, iterations: int = 100, context: Dict = None) -> Dict:
        """
        Ejecuta el mismo prompt N veces y analiza variabilidad

        Returns:
            Dict con métricas de consistencia
        """
        responses = []

        for i in range(iterations):
            result = await self.agent.chat(prompt, user_id=f"test_user_{i}", context=context)
            response_text = result.get("response", "") if isinstance(result, dict) else str(result)
            responses.append(response_text)

            # Pequeña pausa para no saturar
            if i % 10 == 0:
                await asyncio.sleep(0.1)

        # Calcular métricas de consistencia
        unique_responses = len(set(responses))
        similarities = []

        # Comparar todas las respuestas con la primera (baseline)
        baseline = responses[0]
        for response in responses[1:]:
            sim = self.calculate_similarity(baseline, response)
            similarities.append(sim)

        avg_similarity = statistics.mean(similarities) if similarities else 1.0
        std_similarity = statistics.stdev(similarities) if len(similarities) > 1 else 0.0
        min_similarity = min(similarities) if similarities else 1.0

        result = {
            "prompt": prompt,
            "iterations": iterations,
            "unique_responses": unique_responses,
            "avg_similarity": avg_similarity,
            "std_similarity": std_similarity,
            "min_similarity": min_similarity,
            "responses_sample": responses[:5],  # Primeras 5 para debugging
        }

        self.results.append(result)
        return result


@pytest.fixture
async def agent():
    """Fixture del agente IA"""
    nlp_engine = NLPEngine()
    await nlp_engine.start()
    yield nlp_engine
    await nlp_engine.stop()


@pytest.fixture
def consistency_tester(agent):
    """Fixture del tester de consistencia"""
    return AgentConsistencyTester(agent)


# ===== ESCENARIOS DE CONSISTENCIA =====


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        {
            "name": "Consulta de disponibilidad simple",
            "prompt": "¿Tienen habitaciones disponibles para el 15 de diciembre?",
            "expected_similarity": 0.85,
            "max_unique": 10,
        },
        {
            "name": "Pregunta sobre políticas",
            "prompt": "¿Cuál es la política de cancelación del hotel?",
            "expected_similarity": 0.90,  # Debe ser muy consistente (política fija)
            "max_unique": 5,
        },
        {
            "name": "Saludo inicial",
            "prompt": "Hola, ¿puedes ayudarme?",
            "expected_similarity": 0.80,  # Puede variar más (personalización)
            "max_unique": 15,
        },
    ],
)
async def test_agent_consistency(consistency_tester, scenario):
    """
    Test parametrizado de consistencia del agente

    Métricas objetivo:
    - Similitud promedio >85%
    - Respuestas únicas <10/100
    - Std <0.15
    """
    result = await consistency_tester.test_scenario(prompt=scenario["prompt"], iterations=100)

    print(f"\n{'=' * 60}")
    print(f"Escenario: {scenario['name']}")
    print(f"{'=' * 60}")
    print(f"Prompt: {result['prompt']}")
    print(f"Iteraciones: {result['iterations']}")
    print(f"Respuestas únicas: {result['unique_responses']}")
    print(f"Similitud promedio: {result['avg_similarity']:.2%}")
    print(f"Desviación estándar: {result['std_similarity']:.4f}")
    print(f"Similitud mínima: {result['min_similarity']:.2%}")
    print("\nEjemplos de respuestas:")
    for i, resp in enumerate(result["responses_sample"], 1):
        print(f"  {i}. {resp[:80]}...")

    # Assertions
    assert result["avg_similarity"] >= scenario["expected_similarity"], (
        f"Similitud promedio muy baja: {result['avg_similarity']:.2%} < {scenario['expected_similarity']:.2%}"
    )

    assert result["unique_responses"] <= scenario["max_unique"], (
        f"Demasiadas respuestas únicas: {result['unique_responses']} > {scenario['max_unique']}"
    )

    assert result["std_similarity"] < 0.15, f"Desviación estándar muy alta: {result['std_similarity']:.4f}"

    # Warning si hay comportamiento sospechoso
    if result["unique_responses"] > 50:
        warnings.warn(
            f"⚠️  Escenario '{scenario['name']}' tiene {result['unique_responses']} respuestas únicas (>50). "
            "Revisar si el agente es demasiado aleatorio.",
            UserWarning,
        )


@pytest.mark.asyncio
async def test_consistency_with_context(consistency_tester):
    """
    Validar que con el mismo contexto, las respuestas son más consistentes
    """
    context = {
        "user_name": "Juan Pérez",
        "reservation_id": "RES-12345",
        "check_in": "2025-12-15",
        "room_type": "Suite Deluxe",
    }

    result = await consistency_tester.test_scenario(
        prompt="¿Puedo hacer late checkout?", iterations=50, context=context
    )

    print(f"\n{'=' * 60}")
    print("Test: Consistencia CON contexto")
    print(f"{'=' * 60}")
    print(f"Contexto: {context}")
    print(f"Similitud promedio: {result['avg_similarity']:.2%}")
    print(f"Respuestas únicas: {result['unique_responses']}")

    # Con contexto, debería ser MUY consistente
    assert result["avg_similarity"] >= 0.90, "Con contexto fijo, la similitud debe ser >90%"

    assert result["unique_responses"] <= 5, "Con contexto fijo, no debería haber más de 5 respuestas únicas"


@pytest.mark.asyncio
async def test_consistency_temporal(agent):
    """
    Validar que el agente es consistente a lo largo del tiempo
    (no hay drift en el comportamiento)
    """
    prompt = "¿Cuánto cuesta una habitación doble?"

    # Batch 1: Ahora
    responses_batch1 = []
    for _ in range(20):
        result = await agent.chat(prompt, user_id="test_temporal_1")
        response_text = result.get("response", "") if isinstance(result, dict) else str(result)
        responses_batch1.append(response_text)

    # Simular paso del tiempo (en tests reales, esperar minutos/horas)
    await asyncio.sleep(1)

    # Batch 2: Después
    responses_batch2 = []
    for _ in range(20):
        result = await agent.chat(prompt, user_id="test_temporal_2")
        response_text = result.get("response", "") if isinstance(result, dict) else str(result)
        responses_batch2.append(response_text)

    # Comparar ambos batches
    baseline_1 = responses_batch1[0]
    baseline_2 = responses_batch2[0]

    similarity_temporal = SequenceMatcher(None, baseline_1.lower(), baseline_2.lower()).ratio()

    print(f"\n{'=' * 60}")
    print("Test: Consistencia TEMPORAL")
    print(f"{'=' * 60}")
    print(f"Similitud entre batches: {similarity_temporal:.2%}")
    print(f"Batch 1 sample: {baseline_1[:100]}...")
    print(f"Batch 2 sample: {baseline_2[:100]}...")

    # No debería haber drift temporal significativo
    assert similarity_temporal >= 0.80, f"Drift temporal detectado: similitud entre batches = {similarity_temporal:.2%}"


@pytest.mark.asyncio
async def test_consistency_under_load(agent):
    """
    Validar consistencia bajo carga concurrente
    """
    prompt = "¿Ofrecen desayuno incluido?"
    concurrent_requests = 50

    # Ejecutar requests concurrentes
    tasks = [agent.chat(prompt, user_id=f"concurrent_{i}") for i in range(concurrent_requests)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filtrar errores
    successful_responses = [
        r.get("response", "") if isinstance(r, dict) else str(r) for r in results if not isinstance(r, Exception)
    ]

    errors = [r for r in results if isinstance(r, Exception)]

    print(f"\n{'=' * 60}")
    print("Test: Consistencia BAJO CARGA")
    print(f"{'=' * 60}")
    print(f"Requests totales: {concurrent_requests}")
    print(f"Exitosos: {len(successful_responses)}")
    print(f"Errores: {len(errors)}")

    # Calcular similitud de respuestas exitosas
    if len(successful_responses) >= 2:
        baseline = successful_responses[0]
        similarities = [
            SequenceMatcher(None, baseline.lower(), resp.lower()).ratio() for resp in successful_responses[1:]
        ]
        avg_sim = statistics.mean(similarities)

        print(f"Similitud promedio: {avg_sim:.2%}")

        # Bajo carga, debería mantener consistencia
        assert avg_sim >= 0.75, f"Consistencia degradada bajo carga: {avg_sim:.2%} < 75%"

    # No más de 10% de errores
    error_rate = len(errors) / concurrent_requests
    assert error_rate < 0.10, f"Tasa de error muy alta bajo carga: {error_rate:.2%}"


# ===== HELPERS Y UTILITIES =====


def generate_consistency_report(results: List[Dict]) -> str:
    """Genera reporte HTML de consistencia"""
    html = f"""
    <html>
    <head>
        <title>Agent Consistency Report</title>
        <style>
            body {{ font-family: Arial; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #4CAF50; color: white; }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🔍 Agent Consistency Report</h1>
        <p><strong>Generated:</strong> {asyncio.get_event_loop().time()}</p>
        
        <table>
            <tr>
                <th>Scenario</th>
                <th>Iterations</th>
                <th>Unique Responses</th>
                <th>Avg Similarity</th>
                <th>Std Dev</th>
                <th>Status</th>
            </tr>
    """

    for result in results:
        status = "PASS" if result["avg_similarity"] >= 0.85 else "FAIL"
        status_class = "pass" if status == "PASS" else "fail"

        html += f"""
            <tr>
                <td>{result["prompt"][:50]}...</td>
                <td>{result["iterations"]}</td>
                <td>{result["unique_responses"]}</td>
                <td>{result["avg_similarity"]:.2%}</td>
                <td>{result["std_similarity"]:.4f}</td>
                <td class="{status_class}">{status}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    # Ejecutar con: pytest tests/agent/test_consistency.py -v -s
    pytest.main([__file__, "-v", "-s", "--tb=short"])
