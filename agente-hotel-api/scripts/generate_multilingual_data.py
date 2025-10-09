"""
Script para generar dataset multilingüe para Rasa NLU.
Fase E.5 - Mejora del Motor NLP
"""

import argparse
from pathlib import Path
import yaml
import json

# Intenciones por idioma
INTENTS = {
    "es": [
        "check_availability",
        "make_reservation", 
        "get_prices",
        "modify_reservation",
        "cancel_reservation",
        "ask_services",
        "ask_location",
        "ask_policies",
        "greet",
        "goodbye",
        "thanks",
        "confirm",
        "deny"
    ],
    "en": [
        "check_availability",
        "make_reservation", 
        "get_prices",
        "modify_reservation",
        "cancel_reservation",
        "ask_services",
        "ask_location",
        "ask_policies",
        "greet",
        "goodbye",
        "thanks",
        "confirm",
        "deny"
    ],
    "pt": [
        "check_availability",
        "make_reservation", 
        "get_prices",
        "modify_reservation",
        "cancel_reservation",
        "ask_services",
        "ask_location",
        "ask_policies",
        "greet",
        "goodbye",
        "thanks",
        "confirm",
        "deny"
    ]
}

# Ejemplos multilingües por intención
EXAMPLES = {
    # Español
    "es": {
        "check_availability": [
            "¿Hay disponibilidad para el 15 de diciembre?",
            "¿Tenés algo libre para el finde que viene?",
            "¿Hay lugar para 2 personas la semana que viene?",
            "consulto por disponibilidad",
            "tenes lugar para manana?",
            "hola, hay disponibilidad del 10 al 15 de enero?",
            "para el 5 de febrero, dos noches, hay algo?",
            "me gustaria saber si tienen habitaciones libres",
            "hay disponibilidad para 3 personas",
            "del 1 al 5 de marzo",
            "para el proximo finde largo tienen algo?",
            "busco habitacion para el 20",
            "hay algo para el 25 de diciembre?",
            "tienen disponibilidad para año nuevo?",
            "para el dia de los enamorados, tenes algo?",
            "consulta de disponibilidad",
            "quisiera saber si tienen lugar",
            "tienen habitaciones disponibles?",
            "para cuatro personas del 10 al 12",
            "necesito una habitacion para el mes que viene"
        ],
        "make_reservation": [
            "Quiero reservar del 1 al 3 de enero para 2 personas",
            "Dale, reservame la doble",
            "Si, quiero hacer la reserva",
            "confirmo la reserva",
            "haceme la reserva para esas fechas",
            "reservame una habitacion por favor",
            "quiero confirmar",
            "si, por favor, reservala",
            "dale, genial. la quiero",
            "ok, como sigo para reservar?",
            "quiero pagar la seña",
            "como hago para confirmar la reserva?",
            "me interesa, quiero avanzar",
            "reservamela",
            "dale, la quiero",
            "quiero hacer una reserva"
        ],
        "get_prices": [
            "¿Cuánto cuesta la habitación doble?",
            "¿Qué precio tienen las habitaciones?",
            "¿Cuál es la tarifa para una noche?",
            "¿Tienen promociones para estadías largas?",
            "¿Cuánto me costaría quedarme una semana?",
            "precios para fin de semana",
            "tarifa por noche",
            "cuánto sale por persona?",
            "valor de la habitación",
            "tienen descuentos?",
            "hay alguna promoción?",
            "precio de la suite",
            "costo para 3 noches",
            "cuánto está la habitación con vista al mar?",
            "tarifa para habitación individual"
        ],
        "greet": [
            "hola",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "hey",
            "saludos",
            "qué tal",
            "cómo estás",
            "qué hay de nuevo",
            "buen día"
        ],
        "goodbye": [
            "adiós",
            "chau",
            "hasta luego",
            "nos vemos",
            "hasta pronto",
            "me despido",
            "nos hablamos después",
            "hasta mañana",
            "que tengas buen día",
            "me voy"
        ]
    },
    
    # Inglés
    "en": {
        "check_availability": [
            "Do you have any rooms available?",
            "Is there availability for December 15th?",
            "Do you have space for next weekend?",
            "I'm checking for availability",
            "Do you have rooms for tomorrow?",
            "Hello, do you have availability from January 10 to 15?",
            "For February 5th, two nights, do you have anything?",
            "I'd like to know if you have any rooms available",
            "Is there availability for 3 people?",
            "From March 1st to 5th",
            "Do you have anything for the upcoming long weekend?",
            "Looking for a room for the 20th",
            "Is there anything for December 25th?",
            "Do you have availability for New Year's?",
            "For Valentine's Day, do you have anything?"
        ],
        "make_reservation": [
            "I want to book from January 1st to 3rd for 2 people",
            "Ok, book me the double room",
            "Yes, I want to make the reservation",
            "I confirm the reservation",
            "Make the reservation for those dates",
            "Book me a room please",
            "I want to confirm",
            "Yes please, book it",
            "Great, I want it",
            "Ok, how do I proceed with the reservation?",
            "I want to pay the deposit",
            "How do I confirm the reservation?",
            "I'm interested, I want to proceed",
            "Book it for me",
            "Yes, I want it",
            "I want to make a reservation"
        ],
        "get_prices": [
            "How much does the double room cost?",
            "What are your room rates?",
            "What's the rate for one night?",
            "Do you have promotions for extended stays?",
            "How much would it cost me to stay for a week?",
            "Weekend prices",
            "Rate per night",
            "How much is it per person?",
            "Room price",
            "Do you have any discounts?",
            "Are there any promotions?",
            "Price for the suite",
            "Cost for 3 nights",
            "How much is the room with sea view?",
            "Rate for single room"
        ],
        "greet": [
            "hello",
            "good morning",
            "good afternoon",
            "good evening",
            "hey",
            "greetings",
            "hi there",
            "how are you",
            "what's up",
            "good day"
        ],
        "goodbye": [
            "goodbye",
            "bye",
            "see you later",
            "see you",
            "see you soon",
            "farewell",
            "talk to you later",
            "see you tomorrow",
            "have a good day",
            "I'm leaving"
        ]
    },
    
    # Portugués
    "pt": {
        "check_availability": [
            "Há disponibilidade para 15 de dezembro?",
            "Tem algo livre para o próximo fim de semana?",
            "Há espaço para 2 pessoas na próxima semana?",
            "Consulto por disponibilidade",
            "Tem lugar para amanhã?",
            "Olá, há disponibilidade de 10 a 15 de janeiro?",
            "Para 5 de fevereiro, duas noites, tem alguma coisa?",
            "Gostaria de saber se tem quartos disponíveis",
            "Há disponibilidade para 3 pessoas?",
            "De 1 a 5 de março",
            "Para o próximo feriado prolongado tem algo?",
            "Procuro quarto para o dia 20",
            "Tem algo para 25 de dezembro?",
            "Tem disponibilidade para o Ano Novo?",
            "Para o Dia dos Namorados, tem algo?"
        ],
        "make_reservation": [
            "Quero reservar de 1 a 3 de janeiro para 2 pessoas",
            "Ok, reserve-me o quarto duplo",
            "Sim, quero fazer a reserva",
            "Confirmo a reserva",
            "Faça a reserva para essas datas",
            "Reserve-me um quarto, por favor",
            "Quero confirmar",
            "Sim, por favor, reserve",
            "Ótimo, eu quero",
            "Ok, como procedo com a reserva?",
            "Quero pagar o depósito",
            "Como faço para confirmar a reserva?",
            "Estou interessado, quero prosseguir",
            "Reserve para mim",
            "Sim, eu quero",
            "Quero fazer uma reserva"
        ],
        "get_prices": [
            "Quanto custa o quarto duplo?",
            "Quais são os preços dos quartos?",
            "Qual é a tarifa para uma noite?",
            "Tem promoções para estadias longas?",
            "Quanto custaria ficar uma semana?",
            "Preços para fim de semana",
            "Tarifa por noite",
            "Quanto custa por pessoa?",
            "Valor do quarto",
            "Tem descontos?",
            "Há alguma promoção?",
            "Preço da suíte",
            "Custo para 3 noites",
            "Quanto está o quarto com vista para o mar?",
            "Tarifa para quarto individual"
        ],
        "greet": [
            "olá",
            "bom dia",
            "boa tarde",
            "boa noite",
            "oi",
            "saudações",
            "e aí",
            "como vai",
            "tudo bem",
            "bom dia"
        ],
        "goodbye": [
            "adeus",
            "tchau",
            "até logo",
            "nos vemos",
            "até breve",
            "despedida",
            "falamos depois",
            "até amanhã",
            "tenha um bom dia",
            "estou indo"
        ]
    }
}

def generate_multilingual_nlu_data():
    """
    Genera datos de entrenamiento multilingües para Rasa NLU.
    """
    nlu_data = {
        "version": "3.1",
        "nlu": []
    }
    
    # Agregar intenciones para cada idioma
    for language, intents in INTENTS.items():
        for intent in intents:
            # Verificar si hay ejemplos para este intent y lenguaje
            if intent in EXAMPLES.get(language, {}):
                examples = EXAMPLES[language][intent]
                
                # Crear entrada para este intent
                intent_entry = {
                    "intent": f"{intent}",
                    "examples": "\n".join(f"- {example}" for example in examples)
                }
                
                # Agregar al dataset
                nlu_data["nlu"].append(intent_entry)
    
    return nlu_data

def generate_domain_file():
    """
    Genera archivo domain.yml con intenciones y entidades.
    """
    # Obtener todas las intenciones únicas
    all_intents = set()
    for language, intents in INTENTS.items():
        for intent in intents:
            all_intents.add(intent)
    
    # Entidades comunes
    entities = [
        "check_in_date",
        "check_out_date",
        "num_guests",
        "room_type",
        "reservation_code",
        "location",
        "amenity",
        "price_range",
        "date_range"
    ]
    
    # Crear estructura de domain
    domain = {
        "version": "3.1",
        "intents": sorted(list(all_intents)),
        "entities": entities,
        "responses": {
            "utter_greet": [
                {"text": "¡Hola! ¿En qué puedo ayudarte?"},
                {"text": "Hello! How can I help you?"},
                {"text": "Olá! Como posso ajudá-lo?"}
            ],
            "utter_goodbye": [
                {"text": "¡Hasta luego! Gracias por contactarnos."},
                {"text": "Goodbye! Thank you for contacting us."},
                {"text": "Adeus! Obrigado por nos contatar."}
            ]
        },
        "session_config": {
            "session_expiration_time": 60,
            "carry_over_slots_to_new_session": True
        }
    }
    
    return domain

def generate_config_file():
    """
    Genera archivo config.yml con pipeline mejorado para múltiples idiomas.
    """
    config = {
        "recipe": "default.v1",
        "language": "es",  # Idioma principal (se detecta automáticamente)
        "pipeline": [
            # Tokenización
            {
                "name": "WhitespaceTokenizer"
            },
            # Featurizers
            {
                "name": "RegexFeaturizer"
            },
            {
                "name": "LexicalSyntacticFeaturizer"
            },
            # Language Model (SpaCy)
            {
                "name": "SpacyNLP",
                "model": "es_core_news_md",
                "case_sensitive": False
            },
            {
                "name": "SpacyTokenizer"
            },
            {
                "name": "SpacyFeaturizer"
            },
            # Word Embeddings
            {
                "name": "CountVectorsFeaturizer",
                "analyzer": "word",
                "min_ngram": 1,
                "max_ngram": 2
            },
            {
                "name": "CountVectorsFeaturizer",
                "analyzer": "char_wb",
                "min_ngram": 2,
                "max_ngram": 5
            },
            # Intent & Entity Classification
            {
                "name": "DIETClassifier",
                "epochs": 150,
                "constrain_similarities": True,
                "model_confidence": "softmax",
                "drop_rate": 0.2,
                "batch_size": [64, 256],
                "learning_rate": 0.001,
                "evaluate_every_number_of_epochs": 20,
                "evaluate_on_number_of_examples": 100
            },
            # Extracción de Entidades
            {
                "name": "RegexEntityExtractor",
                "case_sensitive": False,
                "use_lookup_tables": True,
                "use_regexes": True
            },
            {
                "name": "EntitySynonymMapper"
            },
            # Response Selector
            {
                "name": "ResponseSelector",
                "epochs": 100,
                "constrain_similarities": True,
                "retrieval_intent": "faq"
            },
            # Language Identification
            {
                "name": "LanguageIdentifierComponents.LanguageIdentifier",
                "model_name": "lid.176.bin",
                "threshold": 0.5
            }
        ],
        "policies": [
            {
                "name": "MemoizationPolicy",
                "max_history": 5
            },
            {
                "name": "RulePolicy",
                "core_fallback_threshold": 0.4,
                "core_fallback_action_name": "action_default_fallback"
            },
            {
                "name": "TEDPolicy",
                "max_history": 5,
                "epochs": 100,
                "constrain_similarities": True
            }
        ]
    }
    
    return config

def save_file(data, file_path, file_format):
    """
    Guarda los datos en el formato especificado.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        if file_format == "yaml":
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        elif file_format == "json":
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            f.write(data)

def main():
    """
    Función principal para generar archivos de configuración Rasa NLU multilingüe.
    """
    parser = argparse.ArgumentParser(description="Generador de dataset multilingüe para Rasa NLU")
    parser.add_argument(
        "--output-dir", 
        default="rasa_nlu_multilingual", 
        help="Directorio de salida para archivos generados"
    )
    args = parser.parse_args()
    
    # Crear directorio de salida
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Crear subdirectorios
    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Generar y guardar archivos
    print("Generando dataset NLU multilingüe...")
    nlu_data = generate_multilingual_nlu_data()
    save_file(nlu_data, data_dir / "nlu.yml", "yaml")
    
    print("Generando domain.yml...")
    domain = generate_domain_file()
    save_file(domain, output_dir / "domain.yml", "yaml")
    
    print("Generando config.yml...")
    config = generate_config_file()
    save_file(config, output_dir / "config.yml", "yaml")
    
    print(f"Archivos generados en: {output_dir}")
    print("Para entrenar el modelo ejecutar: rasa train --data data --config config.yml --domain domain.yml")

if __name__ == "__main__":
    main()