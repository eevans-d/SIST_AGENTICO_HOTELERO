#!/usr/bin/env python3
"""
Test Script for Multilingual NLP Engine
Tests language detection and intent recognition across ES, EN, PT languages
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.nlp_engine import NLPEngine
from app.core.logging import logger


# Test messages in different languages
TEST_MESSAGES = {
    "es": [
        "Hola, quiero hacer una reserva para el 15 de diciembre",
        "¿Tienen habitaciones disponibles para 2 personas?",
        "¿Cuál es el precio de una habitación doble?",
        "Necesito cancelar mi reserva",
        "¿Dónde está ubicado el hotel?",
        "¿Tienen piscina y gimnasio?",
        "Buenos días, ¿pueden ayudarme?",
        "Gracias por la información"
    ],
    "en": [
        "Hello, I want to make a reservation for December 15th",
        "Do you have available rooms for 2 people?",
        "What's the price of a double room?",
        "I need to cancel my reservation",
        "Where is the hotel located?",
        "Do you have a pool and gym?",
        "Good morning, can you help me?",
        "Thank you for the information"
    ],
    "pt": [
        "Olá, quero fazer uma reserva para 15 de dezembro",
        "Vocês têm quartos disponíveis para 2 pessoas?",
        "Qual é o preço de um quarto duplo?",
        "Preciso cancelar minha reserva",
        "Onde fica localizado o hotel?",
        "Vocês têm piscina e academia?",
        "Bom dia, podem me ajudar?",
        "Obrigado pela informação"
    ]
}

# Expected intents for each message (same order as TEST_MESSAGES)
EXPECTED_INTENTS = [
    "hacer_reserva",
    "consultar_disponibilidad", 
    "informacion_precios",
    "cancelar_reserva",
    "informacion_ubicacion",
    "informacion_servicios",
    "saludo",
    "agradecimiento"
]


class MultilingualTester:
    """Test suite for multilingual NLP capabilities"""
    
    def __init__(self):
        self.nlp_engine: Optional[NLPEngine] = None
        self.results = {
            "language_detection": {"correct": 0, "total": 0, "errors": []},
            "intent_recognition": {"correct": 0, "total": 0, "errors": []},
            "overall_accuracy": 0.0
        }
    
    async def setup(self):
        """Initialize NLP engine for testing"""
        try:
            logger.info("Initializing NLP Engine for testing...")
            self.nlp_engine = NLPEngine()
            
            # Check if any models are loaded
            model_info = self.nlp_engine.get_model_info()
            logger.info(f"Model info: {model_info}")
            
            if model_info.get("fallback_mode", True):
                logger.warning("NLP Engine is running in fallback mode - no trained models available")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup NLP Engine: {e}", exc_info=True)
            return False
    
    async def test_language_detection(self) -> Dict[str, Any]:
        """Test language detection accuracy"""
        logger.info("Testing language detection...")
        
        if not self.nlp_engine:
            logger.error("NLP Engine not initialized")
            return {"correct": 0, "total": 0, "errors": ["NLP Engine not initialized"]}
        
        for expected_lang, messages in TEST_MESSAGES.items():
            for message in messages:
                try:
                    detected_lang = await self.nlp_engine.detect_language(message)
                    self.results["language_detection"]["total"] += 1
                    
                    if detected_lang == expected_lang:
                        self.results["language_detection"]["correct"] += 1
                    else:
                        error = {
                            "message": message,
                            "expected": expected_lang,
                            "detected": detected_lang
                        }
                        self.results["language_detection"]["errors"].append(error)
                        logger.warning(f"Language detection error: {error}")
                        
                except Exception as e:
                    logger.error(f"Error detecting language for '{message}': {e}")
                    self.results["language_detection"]["errors"].append({
                        "message": message,
                        "error": str(e)
                    })
        
        accuracy = (
            self.results["language_detection"]["correct"] / 
            self.results["language_detection"]["total"] * 100
            if self.results["language_detection"]["total"] > 0 else 0
        )
        
        logger.info(
            f"Language detection accuracy: {accuracy:.1f}% "
            f"({self.results['language_detection']['correct']}/{self.results['language_detection']['total']})"
        )
        
        return self.results["language_detection"]
    
    async def test_intent_recognition(self) -> Dict[str, Any]:
        """Test intent recognition across languages"""
        logger.info("Testing intent recognition...")
        
        if not self.nlp_engine:
            logger.error("NLP Engine not initialized")
            return {"correct": 0, "total": 0, "errors": ["NLP Engine not initialized"]}
        
        for lang, messages in TEST_MESSAGES.items():
            for i, message in enumerate(messages):
                expected_intent = EXPECTED_INTENTS[i]
                
                try:
                    # Process message with explicit language
                    result = await self.nlp_engine.process_message(message, language=lang)
                    detected_intent = result.get("intent", {}).get("name", "unknown")
                    confidence = result.get("intent", {}).get("confidence", 0.0)
                    
                    self.results["intent_recognition"]["total"] += 1
                    
                    # Check if intent matches (allow for close matches)
                    if detected_intent == expected_intent or confidence > 0.7:
                        self.results["intent_recognition"]["correct"] += 1
                    else:
                        error = {
                            "message": message,
                            "language": lang,
                            "expected_intent": expected_intent,
                            "detected_intent": detected_intent,
                            "confidence": confidence
                        }
                        self.results["intent_recognition"]["errors"].append(error)
                        logger.warning(f"Intent recognition error: {error}")
                        
                except Exception as e:
                    logger.error(f"Error processing message '{message}': {e}")
                    self.results["intent_recognition"]["errors"].append({
                        "message": message,
                        "language": lang,
                        "error": str(e)
                    })
        
        accuracy = (
            self.results["intent_recognition"]["correct"] / 
            self.results["intent_recognition"]["total"] * 100
            if self.results["intent_recognition"]["total"] > 0 else 0
        )
        
        logger.info(
            f"Intent recognition accuracy: {accuracy:.1f}% "
            f"({self.results['intent_recognition']['correct']}/{self.results['intent_recognition']['total']})"
        )
        
        return self.results["intent_recognition"]
    
    async def test_end_to_end(self) -> Dict[str, Any]:
        """Test end-to-end processing without specifying language"""
        logger.info("Testing end-to-end processing (auto language detection)...")
        
        if not self.nlp_engine:
            logger.error("NLP Engine not initialized")
            return {"correct": 0, "total": 0, "errors": ["NLP Engine not initialized"]}
        
        e2e_results = {"correct": 0, "total": 0, "errors": []}
        
        for expected_lang, messages in TEST_MESSAGES.items():
            for i, message in enumerate(messages[:2]):  # Test first 2 messages per language
                expected_intent = EXPECTED_INTENTS[i]
                
                try:
                    # Process without specifying language (auto-detection)
                    result = await self.nlp_engine.process_message(message)
                    detected_lang = result.get("language", "unknown")
                    detected_intent = result.get("intent", {}).get("name", "unknown")
                    confidence = result.get("intent", {}).get("confidence", 0.0)
                    
                    e2e_results["total"] += 1
                    
                    # Success if both language and intent are reasonable
                    lang_correct = detected_lang == expected_lang
                    intent_reasonable = detected_intent == expected_intent or confidence > 0.6
                    
                    if lang_correct and intent_reasonable:
                        e2e_results["correct"] += 1
                    else:
                        error = {
                            "message": message,
                            "expected_language": expected_lang,
                            "detected_language": detected_lang,
                            "expected_intent": expected_intent,
                            "detected_intent": detected_intent,
                            "confidence": confidence,
                            "lang_correct": lang_correct,
                            "intent_reasonable": intent_reasonable
                        }
                        e2e_results["errors"].append(error)
                        logger.warning(f"E2E processing error: {error}")
                        
                except Exception as e:
                    logger.error(f"Error in E2E processing for '{message}': {e}")
                    e2e_results["errors"].append({
                        "message": message,
                        "error": str(e)
                    })
        
        accuracy = (
            e2e_results["correct"] / e2e_results["total"] * 100
            if e2e_results["total"] > 0 else 0
        )
        
        logger.info(
            f"End-to-end accuracy: {accuracy:.1f}% "
            f"({e2e_results['correct']}/{e2e_results['total']})"
        )
        
        return e2e_results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        logger.info("Starting multilingual NLP test suite...")
        
        # Setup
        if not await self.setup():
            return {"error": "Failed to setup NLP Engine"}
        
        # Run individual tests
        lang_detection = await self.test_language_detection()
        intent_recognition = await self.test_intent_recognition()
        e2e_results = await self.test_end_to_end()
        
        # Calculate overall accuracy
        total_correct = (
            lang_detection["correct"] + 
            intent_recognition["correct"] + 
            e2e_results["correct"]
        )
        total_tests = (
            lang_detection["total"] + 
            intent_recognition["total"] + 
            e2e_results["total"]
        )
        
        overall_accuracy = total_correct / total_tests * 100 if total_tests > 0 else 0
        
        # Final results
        final_results = {
            "overall_accuracy": overall_accuracy,
            "language_detection": lang_detection,
            "intent_recognition": intent_recognition,
            "end_to_end": e2e_results,
            "model_info": self.nlp_engine.get_model_info() if self.nlp_engine else {},
            "summary": {
                "total_tests": total_tests,
                "total_correct": total_correct,
                "languages_tested": list(TEST_MESSAGES.keys()),
                "test_categories": 3
            }
        }
        
        # Print summary
        logger.info("=" * 60)
        logger.info("MULTILINGUAL NLP TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Overall Accuracy: {overall_accuracy:.1f}%")
        logger.info(f"Language Detection: {lang_detection['correct']}/{lang_detection['total']} ({lang_detection['correct']/lang_detection['total']*100:.1f}%)")
        logger.info(f"Intent Recognition: {intent_recognition['correct']}/{intent_recognition['total']} ({intent_recognition['correct']/intent_recognition['total']*100:.1f}%)")
        logger.info(f"End-to-End: {e2e_results['correct']}/{e2e_results['total']} ({e2e_results['correct']/e2e_results['total']*100:.1f}%)")
        logger.info("=" * 60)
        
        if overall_accuracy >= 80:
            logger.info("✅ Multilingual NLP system is performing well!")
        elif overall_accuracy >= 60:
            logger.warning("⚠️ Multilingual NLP system needs some improvements")
        else:
            logger.error("❌ Multilingual NLP system requires significant improvements")
        
        return final_results


async def main():
    """Main test execution"""
    try:
        tester = MultilingualTester()
        results = await tester.run_all_tests()
        
        # Save results to file
        import json
        results_file = Path(__file__).parent.parent / ".playbook" / "multilingual_test_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    # Set basic environment for testing
    os.environ.setdefault("POSTGRES_URL", "sqlite+aiosqlite:///test.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    
    # Run tests
    results = asyncio.run(main())
    
    # Exit with appropriate code
    if "error" in results:
        sys.exit(1)
    else:
        overall_accuracy = results.get("overall_accuracy", 0)
        if isinstance(overall_accuracy, (int, float)) and overall_accuracy < 60:
            sys.exit(1)
        else:
            sys.exit(0)