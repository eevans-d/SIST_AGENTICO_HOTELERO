"""
Room images mapping and utilities.
Feature 3: Envío Automático de Foto de Habitación

Maps room types to their corresponding image URLs and provides utilities.
"""

from typing import Optional, Dict
from ..core.settings import settings
from ..core.logging import logger


# Default room type to image filename mapping
# This can be overridden per tenant via database configuration
DEFAULT_ROOM_IMAGE_MAPPING: Dict[str, str] = {
    # Standard room types
    "single": "single-room.jpg",
    "individual": "single-room.jpg",
    "sencilla": "single-room.jpg",
    
    "double": "double-room.jpg",
    "doble": "double-room.jpg",
    "matrimonial": "double-room.jpg",
    "twin": "twin-room.jpg",
    
    "triple": "triple-room.jpg",
    
    "suite": "suite.jpg",
    "junior_suite": "junior-suite.jpg",
    "master_suite": "master-suite.jpg",
    
    "family": "family-room.jpg",
    "familiar": "family-room.jpg",
    
    "deluxe": "deluxe-room.jpg",
    "premium": "premium-room.jpg",
    "executive": "executive-room.jpg",
    
    # Special categories
    "accessible": "accessible-room.jpg",
    "accesible": "accessible-room.jpg",
    
    "penthouse": "penthouse.jpg",
    
    # Default fallback
    "standard": "standard-room.jpg",
    "default": "standard-room.jpg",
}


def get_room_image_url(room_type: str, base_url: Optional[str] = None) -> Optional[str]:
    """
    Get the image URL for a given room type.
    
    Args:
        room_type: Type of room (e.g., "double", "suite")
        base_url: Base URL for images (defaults to settings)
        
    Returns:
        Full URL to the room image, or None if images disabled or not found
        
    Example:
        >>> get_room_image_url("double")
        "https://example.com/images/rooms/double-room.jpg"
    """
    # Check if room images feature is enabled
    if not settings.room_images_enabled:
        logger.debug("room_images.disabled", room_type=room_type)
        return None
    
    # Use settings base URL if not provided
    if base_url is None:
        base_url = settings.room_images_base_url
    
    # Normalize room type (lowercase, trim spaces)
    room_type_normalized = room_type.lower().strip().replace(" ", "_")
    
    # Get image filename from mapping
    image_filename = DEFAULT_ROOM_IMAGE_MAPPING.get(
        room_type_normalized,
        DEFAULT_ROOM_IMAGE_MAPPING.get("default")
    )
    
    if not image_filename:
        logger.warning(
            "room_images.no_mapping",
            room_type=room_type,
            room_type_normalized=room_type_normalized
        )
        return None
    
    # Construct full URL
    # Ensure base_url ends with / and image_filename doesn't start with /
    base_url = base_url.rstrip("/")
    image_filename = image_filename.lstrip("/")
    full_url = f"{base_url}/{image_filename}"
    
    logger.debug(
        "room_images.resolved",
        room_type=room_type,
        image_url=full_url
    )
    
    return full_url


def get_multiple_room_images(room_types: list[str], base_url: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Get image URLs for multiple room types.
    
    Args:
        room_types: List of room types
        base_url: Base URL for images (defaults to settings)
        
    Returns:
        Dictionary mapping room types to their image URLs
        
    Example:
        >>> get_multiple_room_images(["double", "suite"])
        {"double": "https://example.com/images/rooms/double-room.jpg",
         "suite": "https://example.com/images/rooms/suite.jpg"}
    """
    return {
        room_type: get_room_image_url(room_type, base_url)
        for room_type in room_types
    }


def validate_image_url(image_url: str) -> bool:
    """
    Validate that an image URL is properly formatted.
    
    Args:
        image_url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
        
    Note:
        WhatsApp requires HTTPS URLs for media
    """
    if not image_url:
        return False
    
    # Must be HTTPS (WhatsApp requirement)
    if not image_url.startswith("https://"):
        logger.warning(
            "room_images.invalid_url",
            image_url=image_url,
            reason="Must use HTTPS"
        )
        return False
    
    # Should end with image extension
    valid_extensions = [".jpg", ".jpeg", ".png"]
    if not any(image_url.lower().endswith(ext) for ext in valid_extensions):
        logger.warning(
            "room_images.invalid_url",
            image_url=image_url,
            reason="Invalid image extension"
        )
        return False
    
    return True


def add_custom_room_mapping(room_type: str, image_filename: str) -> None:
    """
    Add or update a custom room type mapping.
    
    Args:
        room_type: Room type identifier
        image_filename: Filename of the image
        
    Note:
        This modifies the in-memory mapping. For persistent mappings,
        use database configuration or settings override.
    """
    room_type_normalized = room_type.lower().strip().replace(" ", "_")
    DEFAULT_ROOM_IMAGE_MAPPING[room_type_normalized] = image_filename
    
    logger.info(
        "room_images.custom_mapping_added",
        room_type=room_type,
        image_filename=image_filename
    )


def get_available_room_types() -> list[str]:
    """
    Get list of all room types that have image mappings.
    
    Returns:
        List of room type identifiers
    """
    return list(DEFAULT_ROOM_IMAGE_MAPPING.keys())
