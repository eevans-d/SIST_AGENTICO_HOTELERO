"""
[PROMPT 2.5 + E.3] app/services/entity_extractors.py
Entity Extractors for Hotel Domain
Post-processing and normalization of Rasa NLU entities.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from ..core.logging import logger


class DateExtractor:
    """
    Extract and normalize dates from text and Rasa entities.
    
    Handles:
    - Absolute dates: "15 de diciembre", "2024-01-15"
    - Relative dates: "mañana", "próximo fin de semana", "en 3 días"
    - Date ranges: "del 10 al 15", "del lunes al viernes"
    """
    
    # Spanish month names
    MONTHS = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    
    # Relative date keywords
    RELATIVE_KEYWORDS = {
        "hoy": 0,
        "mañana": 1,
        "pasado mañana": 2,
        "este fin de semana": 5,  # Next Saturday
        "próximo fin de semana": 7,
        "la próxima semana": 7,
        "este mes": 15,
        "próximo mes": 30,
    }
    
    @classmethod
    def extract(cls, entities: List[Dict[str, Any]], text: str) -> Dict[str, Optional[datetime]]:
        """
        Extract check-in and check-out dates from entities and text.
        
        Args:
            entities: Rasa entities list
            text: Original message text
        
        Returns:
            dict with "check_in" and "check_out" datetime objects
        """
        result = {"check_in": None, "check_out": None}
        
        # Extract from Rasa entities first
        date_entities = [e for e in entities if e.get("entity") == "date"]
        
        if date_entities:
            # Parse first date as check-in
            if len(date_entities) >= 1:
                result["check_in"] = cls._parse_date_entity(date_entities[0], text)
            
            # Parse second date as check-out
            if len(date_entities) >= 2:
                result["check_out"] = cls._parse_date_entity(date_entities[1], text)
        
        # Fallback: extract from text using regex
        if not result["check_in"]:
            result["check_in"] = cls._extract_from_text(text)
        
        # If only check-in found, assume 1 night stay
        if result["check_in"] and not result["check_out"]:
            result["check_out"] = result["check_in"] + timedelta(days=1)
        
        return result
    
    @classmethod
    def _parse_date_entity(cls, entity: Dict[str, Any], text: str) -> Optional[datetime]:
        """Parse Rasa date entity to datetime."""
        value = entity.get("value", "")
        
        try:
            # Try ISO format first
            if re.match(r"\d{4}-\d{2}-\d{2}", value):
                return datetime.fromisoformat(value)
            
            # Try dateutil parser (handles many formats)
            return date_parser.parse(value, dayfirst=True)
        
        except (ValueError, date_parser.ParserError):
            logger.warning(f"Failed to parse date entity: {value}")
            return None
    
    @classmethod
    def _extract_from_text(cls, text: str) -> Optional[datetime]:
        """Extract date from text using patterns."""
        text_lower = text.lower()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check relative keywords
        for keyword, days_offset in cls.RELATIVE_KEYWORDS.items():
            if keyword in text_lower:
                return today + timedelta(days=days_offset)
        
        # Pattern: "del X al Y" or "del X"
        del_pattern = r"del\s+(\d{1,2})(?:\s+al\s+(\d{1,2}))?"
        match = re.search(del_pattern, text_lower)
        if match:
            day = int(match.group(1))
            # Assume current month if no month specified
            current_month = today.month
            current_year = today.year
            
            try:
                date_obj = datetime(current_year, current_month, day)
                # If date is in the past, assume next month
                if date_obj < today:
                    date_obj = date_obj + relativedelta(months=1)
                return date_obj
            except ValueError:
                pass
        
        # Pattern: "15 de diciembre"
        date_pattern = r"(\d{1,2})\s+de\s+(" + "|".join(cls.MONTHS.keys()) + r")"
        match = re.search(date_pattern, text_lower)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = cls.MONTHS.get(month_name)
            current_year = today.year
            
            try:
                date_obj = datetime(current_year, month, day)
                # If date is in the past, assume next year
                if date_obj < today:
                    date_obj = datetime(current_year + 1, month, day)
                return date_obj
            except ValueError:
                pass
        
        return None


class NumberExtractor:
    """
    Extract numbers from entities (guests, nights, rooms).
    """
    
    # Spanish number words
    NUMBER_WORDS = {
        "uno": 1, "un": 1, "una": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }
    
    @classmethod
    def extract_guests(cls, entities: List[Dict[str, Any]], text: str) -> int:
        """
        Extract number of guests from entities or text.
        
        Args:
            entities: Rasa entities list
            text: Original message text
        
        Returns:
            Number of guests (default: 2)
        """
        # Check entities for number
        number_entities = [e for e in entities if e.get("entity") in ["number", "guests"]]
        if number_entities:
            value = number_entities[0].get("value")
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        
        # Extract from text
        text_lower = text.lower()
        
        # Pattern: "para X personas"
        persona_pattern = r"para\s+(\d+)\s+personas?"
        match = re.search(persona_pattern, text_lower)
        if match:
            return int(match.group(1))
        
        # Pattern: "X adultos"
        adulto_pattern = r"(\d+)\s+adultos?"
        match = re.search(adulto_pattern, text_lower)
        if match:
            return int(match.group(1))
        
        # Check number words
        for word, value in cls.NUMBER_WORDS.items():
            if f"{word} persona" in text_lower or f"{word} adulto" in text_lower:
                return value
        
        # Default: 2 guests
        return 2
    
    @classmethod
    def extract_nights(cls, entities: List[Dict[str, Any]], text: str) -> int:
        """
        Extract number of nights from entities or text.
        
        Args:
            entities: Rasa entities list
            text: Original message text
        
        Returns:
            Number of nights (default: 1)
        """
        text_lower = text.lower()
        
        # Pattern: "X noches"
        noche_pattern = r"(\d+)\s+noches?"
        match = re.search(noche_pattern, text_lower)
        if match:
            return int(match.group(1))
        
        # Check number words
        for word, value in cls.NUMBER_WORDS.items():
            if f"{word} noche" in text_lower:
                return value
        
        # Default: 1 night
        return 1


class RoomTypeExtractor:
    """
    Extract and normalize room type from text.
    """
    
    # Room type synonyms
    ROOM_TYPES = {
        "simple": ["simple", "individual", "single"],
        "doble": ["doble", "double", "matrimonial", "dos camas"],
        "triple": ["triple", "3 personas"],
        "familiar": ["familiar", "family", "4 personas"],
        "suite": ["suite", "junior suite", "master suite"],
        "ejecutiva": ["ejecutiva", "executive", "business"],
    }
    
    @classmethod
    def extract(cls, entities: List[Dict[str, Any]], text: str) -> Optional[str]:
        """
        Extract room type from entities or text.
        
        Args:
            entities: Rasa entities list
            text: Original message text
        
        Returns:
            Room type (normalized) or None
        """
        text_lower = text.lower()
        
        # Check entities first
        room_entities = [e for e in entities if e.get("entity") == "room_type"]
        if room_entities:
            value = room_entities[0].get("value", "").lower()
            return cls._normalize_room_type(value)
        
        # Search for room type keywords in text
        for room_type, synonyms in cls.ROOM_TYPES.items():
            for synonym in synonyms:
                if synonym in text_lower:
                    return room_type
        
        return None
    
    @classmethod
    def _normalize_room_type(cls, value: str) -> str:
        """Normalize room type value to standard name."""
        for room_type, synonyms in cls.ROOM_TYPES.items():
            if value in synonyms:
                return room_type
        return value


class AmenityExtractor:
    """
    Extract amenities mentioned in text.
    """
    
    AMENITIES = [
        "piscina", "pileta", "pool",
        "gimnasio", "gym", "fitness",
        "wifi", "internet",
        "desayuno", "breakfast",
        "estacionamiento", "parking", "cochera",
        "spa", "sauna",
        "restaurante", "restaurant",
        "bar",
        "aire acondicionado", "ac", "aire",
        "calefacción", "calefaccion",
        "tv", "television",
        "minibar",
        "caja fuerte", "safe",
    ]
    
    @classmethod
    def extract(cls, text: str) -> List[str]:
        """
        Extract mentioned amenities from text.
        
        Args:
            text: Original message text
        
        Returns:
            List of amenity names
        """
        text_lower = text.lower()
        found_amenities = []
        
        for amenity in cls.AMENITIES:
            if amenity in text_lower:
                # Normalize to standard name
                normalized = cls._normalize_amenity(amenity)
                if normalized not in found_amenities:
                    found_amenities.append(normalized)
        
        return found_amenities
    
    @classmethod
    def _normalize_amenity(cls, value: str) -> str:
        """Normalize amenity name."""
        normalizations = {
            "pileta": "piscina",
            "pool": "piscina",
            "gym": "gimnasio",
            "fitness": "gimnasio",
            "internet": "wifi",
            "breakfast": "desayuno",
            "parking": "estacionamiento",
            "cochera": "estacionamiento",
            "restaurant": "restaurante",
            "ac": "aire acondicionado",
            "aire": "aire acondicionado",
            "calefaccion": "calefacción",
            "television": "tv",
            "safe": "caja fuerte",
        }
        return normalizations.get(value, value)


def extract_all_entities(text: str, rasa_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract and normalize all entities from text and Rasa results.
    
    Args:
        text: Original message text
        rasa_entities: Entities from Rasa NLU
    
    Returns:
        dict with all extracted entities:
        {
            "dates": {"check_in": datetime, "check_out": datetime},
            "guests": int,
            "nights": int,
            "room_type": str,
            "amenities": List[str]
        }
    """
    return {
        "dates": DateExtractor.extract(rasa_entities, text),
        "guests": NumberExtractor.extract_guests(rasa_entities, text),
        "nights": NumberExtractor.extract_nights(rasa_entities, text),
        "room_type": RoomTypeExtractor.extract(rasa_entities, text),
        "amenities": AmenityExtractor.extract(text)
    }
