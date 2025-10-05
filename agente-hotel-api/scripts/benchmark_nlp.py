#!/usr/bin/env python3
"""
[PROMPT 2.5 + E.3] scripts/benchmark_nlp.py
Rasa NLU Performance Benchmarking Script
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.nlp_engine import NLPEngine
from app.core.logging import logger


class NLPBenchmark:
    """
    Benchmark Rasa NLU model performance.
    
    Tests:
    - Intent classification accuracy
    - Per-intent precision/recall/F1
    - Confidence calibration
    - Entity extraction accuracy
    - Inference latency
    """
    
    def __init__(self, model_path: str = None):
        """Initialize benchmark with NLP engine."""
        self.engine = NLPEngine(model_path=model_path)
        self.results = {
            "intent_predictions": [],
            "entity_predictions": [],
            "latencies": [],
            "errors": []
        }
    
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """
        Get test cases for benchmarking.
        
        Returns:
            List of test cases with expected intent and entities
        """
        return [
            # ==================== CHECK AVAILABILITY ====================
            {
                "text": "¿Hay disponibilidad para mañana?",
                "expected_intent": "check_availability",
                "expected_entities": ["date"]
            },
            {
                "text": "Tienen lugar para el 15 de octubre?",
                "expected_intent": "check_availability",
                "expected_entities": ["date"]
            },
            {
                "text": "Para 3 personas del 10 al 15",
                "expected_intent": "check_availability",
                "expected_entities": ["number", "date"]
            },
            {
                "text": "Consulto por disponibilidad fin de semana",
                "expected_intent": "check_availability",
                "expected_entities": []
            },
            
            # ==================== MAKE RESERVATION ====================
            {
                "text": "Quiero hacer una reserva",
                "expected_intent": "make_reservation",
                "expected_entities": []
            },
            {
                "text": "Reservame una habitación doble para el 20",
                "expected_intent": "make_reservation",
                "expected_entities": ["room_type", "date"]
            },
            {
                "text": "Dale, confirmo la reserva",
                "expected_intent": "make_reservation",
                "expected_entities": []
            },
            
            # ==================== CANCEL RESERVATION ====================
            {
                "text": "Necesito cancelar mi reserva",
                "expected_intent": "cancel_reservation",
                "expected_entities": []
            },
            {
                "text": "Quiero anular el booking",
                "expected_intent": "cancel_reservation",
                "expected_entities": []
            },
            {
                "text": "Tengo que cancelar por favor",
                "expected_intent": "cancel_reservation",
                "expected_entities": []
            },
            
            # ==================== MODIFY RESERVATION ====================
            {
                "text": "Quiero cambiar las fechas",
                "expected_intent": "modify_reservation",
                "expected_entities": []
            },
            {
                "text": "Puedo modificar mi reserva?",
                "expected_intent": "modify_reservation",
                "expected_entities": []
            },
            {
                "text": "Necesito agregar una noche más",
                "expected_intent": "modify_reservation",
                "expected_entities": ["number"]
            },
            
            # ==================== ASK PRICE ====================
            {
                "text": "Cuánto cuesta la habitación?",
                "expected_intent": "ask_price",
                "expected_entities": []
            },
            {
                "text": "Precio de la doble por favor",
                "expected_intent": "ask_price",
                "expected_entities": ["room_type"]
            },
            {
                "text": "Tarifa por noche?",
                "expected_intent": "ask_price",
                "expected_entities": []
            },
            
            # ==================== ASK AMENITIES ====================
            {
                "text": "Tiene piscina el hotel?",
                "expected_intent": "ask_amenities",
                "expected_entities": ["amenity"]
            },
            {
                "text": "Qué servicios incluye?",
                "expected_intent": "ask_amenities",
                "expected_entities": []
            },
            {
                "text": "Hay gimnasio y wifi?",
                "expected_intent": "ask_amenities",
                "expected_entities": ["amenity"]
            },
            
            # ==================== ASK LOCATION ====================
            {
                "text": "Dónde están ubicados?",
                "expected_intent": "ask_location",
                "expected_entities": []
            },
            {
                "text": "Cómo llego desde el aeropuerto?",
                "expected_intent": "ask_location",
                "expected_entities": []
            },
            
            # ==================== ASK POLICIES ====================
            {
                "text": "Cuál es el horario de check in?",
                "expected_intent": "ask_policies",
                "expected_entities": []
            },
            {
                "text": "Política de cancelación?",
                "expected_intent": "ask_policies",
                "expected_entities": []
            },
            {
                "text": "Se aceptan mascotas?",
                "expected_intent": "ask_policies",
                "expected_entities": []
            },
            
            # ==================== GREETING ====================
            {
                "text": "Hola",
                "expected_intent": "greeting",
                "expected_entities": []
            },
            {
                "text": "Buenos días",
                "expected_intent": "greeting",
                "expected_entities": []
            },
            
            # ==================== GOODBYE ====================
            {
                "text": "Chau gracias",
                "expected_intent": "goodbye",
                "expected_entities": []
            },
            {
                "text": "Hasta luego",
                "expected_intent": "goodbye",
                "expected_entities": []
            },
            
            # ==================== AFFIRM ====================
            {
                "text": "Sí",
                "expected_intent": "affirm",
                "expected_entities": []
            },
            {
                "text": "Dale ok",
                "expected_intent": "affirm",
                "expected_entities": []
            },
            
            # ==================== DENY ====================
            {
                "text": "No gracias",
                "expected_intent": "deny",
                "expected_entities": []
            },
            {
                "text": "Nop",
                "expected_intent": "deny",
                "expected_entities": []
            },
            
            # ==================== HELP ====================
            {
                "text": "Ayuda por favor",
                "expected_intent": "help",
                "expected_entities": []
            },
            {
                "text": "Qué puedo hacer?",
                "expected_intent": "help",
                "expected_entities": []
            },
            
            # ==================== OUT OF SCOPE ====================
            {
                "text": "Qué hora es?",
                "expected_intent": "out_of_scope",
                "expected_entities": []
            },
            {
                "text": "asdfghjkl",
                "expected_intent": "out_of_scope",
                "expected_entities": []
            },
        ]
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """
        Run complete benchmark suite.
        
        Returns:
            dict with benchmark results
        """
        logger.info("Starting NLP benchmark...")
        
        test_cases = self.get_test_cases()
        total = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Running test {i}/{total}: {test_case['text'][:50]}...")
            
            try:
                start_time = datetime.now()
                result = await self.engine.process_message(test_case["text"])
                latency = (datetime.now() - start_time).total_seconds() * 1000  # ms
                
                # Store results
                self.results["intent_predictions"].append({
                    "text": test_case["text"],
                    "expected": test_case["expected_intent"],
                    "predicted": result["intent"]["name"],
                    "confidence": result["intent"]["confidence"],
                    "correct": result["intent"]["name"] == test_case["expected_intent"]
                })
                
                self.results["entity_predictions"].append({
                    "text": test_case["text"],
                    "expected": test_case["expected_entities"],
                    "predicted": [e["entity"] for e in result.get("entities", [])],
                    "correct": set([e["entity"] for e in result.get("entities", [])]) == set(test_case["expected_entities"])
                })
                
                self.results["latencies"].append(latency)
                
            except Exception as e:
                logger.error(f"Benchmark test failed: {e}")
                self.results["errors"].append({
                    "text": test_case["text"],
                    "error": str(e)
                })
        
        logger.info("Benchmark complete. Calculating metrics...")
        return self.calculate_metrics()
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics from results.
        
        Returns:
            dict with calculated metrics
        """
        # Overall intent accuracy
        total_intents = len(self.results["intent_predictions"])
        correct_intents = sum(1 for p in self.results["intent_predictions"] if p["correct"])
        intent_accuracy = correct_intents / total_intents if total_intents > 0 else 0.0
        
        # Per-intent metrics
        per_intent_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "correct": 0, "total": 0})
        
        for pred in self.results["intent_predictions"]:
            expected = pred["expected"]
            predicted = pred["predicted"]
            
            per_intent_stats[expected]["total"] += 1
            
            if predicted == expected:
                per_intent_stats[expected]["tp"] += 1
                per_intent_stats[expected]["correct"] += 1
            else:
                per_intent_stats[expected]["fn"] += 1
                per_intent_stats[predicted]["fp"] += 1
        
        # Calculate precision, recall, F1 for each intent
        per_intent_metrics = {}
        for intent, stats in per_intent_stats.items():
            tp = stats["tp"]
            fp = stats["fp"]
            fn = stats["fn"]
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            per_intent_metrics[intent] = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "support": stats["total"],
                "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            }
        
        # Weighted averages
        total_support = sum(m["support"] for m in per_intent_metrics.values())
        weighted_precision = sum(m["precision"] * m["support"] for m in per_intent_metrics.values()) / total_support if total_support > 0 else 0.0
        weighted_recall = sum(m["recall"] * m["support"] for m in per_intent_metrics.values()) / total_support if total_support > 0 else 0.0
        weighted_f1 = sum(m["f1_score"] * m["support"] for m in per_intent_metrics.values()) / total_support if total_support > 0 else 0.0
        
        # Entity accuracy
        total_entities = len(self.results["entity_predictions"])
        correct_entities = sum(1 for p in self.results["entity_predictions"] if p["correct"])
        entity_accuracy = correct_entities / total_entities if total_entities > 0 else 0.0
        
        # Latency stats
        latencies = self.results["latencies"]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0.0
        
        # Confidence calibration
        high_confidence = [p for p in self.results["intent_predictions"] if p["confidence"] >= 0.85]
        high_conf_accuracy = sum(1 for p in high_confidence if p["correct"]) / len(high_confidence) if high_confidence else 0.0
        
        return {
            "overall": {
                "intent_accuracy": intent_accuracy,
                "entity_accuracy": entity_accuracy,
                "weighted_precision": weighted_precision,
                "weighted_recall": weighted_recall,
                "weighted_f1": weighted_f1,
                "total_tests": total_intents,
                "errors": len(self.results["errors"])
            },
            "per_intent": per_intent_metrics,
            "latency": {
                "avg_ms": avg_latency,
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency
            },
            "confidence_calibration": {
                "high_confidence_accuracy": high_conf_accuracy,
                "high_confidence_count": len(high_confidence)
            },
            "errors": self.results["errors"]
        }
    
    def generate_report(self, metrics: Dict[str, Any]) -> str:
        """
        Generate human-readable benchmark report.
        
        Args:
            metrics: Calculated metrics
        
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 80,
            "RASA NLU BENCHMARK REPORT",
            "=" * 80,
            "",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Model: {self.engine.get_model_info()['model_version']}",
            f"Test Cases: {metrics['overall']['total_tests']}",
            "",
            "OVERALL PERFORMANCE",
            "-" * 80,
            f"Intent Accuracy:     {metrics['overall']['intent_accuracy']:.2%}",
            f"Entity Accuracy:     {metrics['overall']['entity_accuracy']:.2%}",
            f"Weighted Precision:  {metrics['overall']['weighted_precision']:.2%}",
            f"Weighted Recall:     {metrics['overall']['weighted_recall']:.2%}",
            f"Weighted F1-Score:   {metrics['overall']['weighted_f1']:.2%}",
            "",
            "PER-INTENT PERFORMANCE",
            "-" * 80,
        ]
        
        # Sort intents by F1 score
        sorted_intents = sorted(
            metrics["per_intent"].items(),
            key=lambda x: x[1]["f1_score"],
            reverse=True
        )
        
        for intent, stats in sorted_intents:
            lines.extend([
                f"\n{intent}:",
                f"  Precision:  {stats['precision']:.2%}",
                f"  Recall:     {stats['recall']:.2%}",
                f"  F1-Score:   {stats['f1_score']:.2%}",
                f"  Accuracy:   {stats['accuracy']:.2%}",
                f"  Support:    {stats['support']} examples"
            ])
        
        lines.extend([
            "",
            "LATENCY",
            "-" * 80,
            f"Average:    {metrics['latency']['avg_ms']:.2f} ms",
            f"P50:        {metrics['latency']['p50_ms']:.2f} ms",
            f"P95:        {metrics['latency']['p95_ms']:.2f} ms",
            f"P99:        {metrics['latency']['p99_ms']:.2f} ms",
            "",
            "CONFIDENCE CALIBRATION",
            "-" * 80,
            f"High Confidence (≥0.85) Accuracy: {metrics['confidence_calibration']['high_confidence_accuracy']:.2%}",
            f"High Confidence Count: {metrics['confidence_calibration']['high_confidence_count']}",
            "",
            "PRODUCTION READINESS",
            "-" * 80,
        ])
        
        # Production readiness checks
        checks = [
            ("Intent Accuracy ≥ 85%", metrics['overall']['intent_accuracy'] >= 0.85),
            ("Weighted Precision ≥ 85%", metrics['overall']['weighted_precision'] >= 0.85),
            ("Weighted Recall ≥ 80%", metrics['overall']['weighted_recall'] >= 0.80),
            ("Weighted F1 ≥ 82%", metrics['overall']['weighted_f1'] >= 0.82),
            ("Avg Latency < 100ms", metrics['latency']['avg_ms'] < 100),
            ("P95 Latency < 200ms", metrics['latency']['p95_ms'] < 200),
        ]
        
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            lines.append(f"{status}  {check_name}")
        
        all_passed = all(passed for _, passed in checks)
        
        lines.extend([
            "",
            "=" * 80,
            f"VERDICT: {'✅ PRODUCTION READY' if all_passed else '⚠️  NEEDS IMPROVEMENT'}",
            "=" * 80,
        ])
        
        if metrics['overall']['errors'] > 0:
            lines.extend([
                "",
                "ERRORS",
                "-" * 80,
            ])
            for error in metrics['errors']:
                lines.append(f"- {error['text'][:50]}... → {error['error']}")
        
        return "\n".join(lines)


async def main():
    """Main entry point."""
    print("🚀 Starting Rasa NLU Benchmark...\n")
    
    # Initialize benchmark
    benchmark = NLPBenchmark()
    
    # Check if model is loaded
    model_info = benchmark.engine.get_model_info()
    if not model_info["agent_loaded"]:
        print("❌ ERROR: No Rasa model loaded!")
        print("Train a model first: ./scripts/train_rasa.sh")
        sys.exit(1)
    
    print(f"Model: {model_info['model_version']}")
    print(f"Loaded at: {model_info['model_loaded_at']}")
    print()
    
    # Run benchmark
    metrics = await benchmark.run_benchmark()
    
    # Generate report
    report = benchmark.generate_report(metrics)
    print("\n" + report)
    
    # Save results
    results_dir = Path(__file__).parent.parent / ".playbook" / "rasa_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_path = results_dir / f"benchmark_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\n📊 Results saved to: {json_path}")
    
    # Save report
    report_path = results_dir / f"benchmark_{timestamp}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"📄 Report saved to: {report_path}")
    
    # Exit with appropriate code
    if metrics["overall"]["intent_accuracy"] >= 0.85:
        print("\n✅ Benchmark PASSED")
        sys.exit(0)
    else:
        print("\n⚠️  Benchmark FAILED (accuracy below 85%)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
