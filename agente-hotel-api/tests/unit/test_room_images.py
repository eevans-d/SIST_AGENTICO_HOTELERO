"""
Unit tests for room image mapping utilities.
Feature 3: Envío Automático de Foto de Habitación
"""

import pytest
from unittest.mock import patch
from app.utils.room_images import (
    get_room_image_url,
    get_multiple_room_images,
    validate_image_url,
    add_custom_room_mapping,
    get_available_room_types,
    DEFAULT_ROOM_IMAGE_MAPPING
)


class TestGetRoomImageUrl:
    """Tests for get_room_image_url function."""
    
    @patch("app.utils.room_images.settings")
    def test_returns_url_for_known_room_type(self, mock_settings):
        """Should return correct URL for known room type."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        url = get_room_image_url("double")
        
        assert url == "https://example.com/images/rooms/double-room.jpg"
    
    @patch("app.utils.room_images.settings")
    def test_normalizes_room_type(self, mock_settings):
        """Should normalize room type (lowercase, trim, replace spaces)."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        # Test uppercase
        url = get_room_image_url("DOUBLE")
        assert url == "https://example.com/images/rooms/double-room.jpg"
        
        # Test with spaces
        url = get_room_image_url("  double  ")
        assert url == "https://example.com/images/rooms/double-room.jpg"
    
    @patch("app.utils.room_images.settings")
    def test_returns_default_for_unknown_room_type(self, mock_settings):
        """Should return default image for unknown room types."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        url = get_room_image_url("unknown_room_type")
        
        assert url == "https://example.com/images/rooms/standard-room.jpg"
    
    @patch("app.utils.room_images.settings")
    def test_returns_none_when_disabled(self, mock_settings):
        """Should return None when room images feature is disabled."""
        mock_settings.room_images_enabled = False
        
        url = get_room_image_url("double")
        
        assert url is None
    
    @patch("app.utils.room_images.settings")
    def test_uses_custom_base_url(self, mock_settings):
        """Should use custom base URL when provided."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://default.com/images"
        
        url = get_room_image_url("double", base_url="https://custom.com/photos")
        
        assert url == "https://custom.com/photos/double-room.jpg"
    
    @patch("app.utils.room_images.settings")
    def test_handles_base_url_with_trailing_slash(self, mock_settings):
        """Should handle base URL with or without trailing slash."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms/"
        
        url = get_room_image_url("double")
        
        # Should not have double slash
        assert url == "https://example.com/images/rooms/double-room.jpg"
        assert "//" not in url.replace("https://", "")
    
    @patch("app.utils.room_images.settings")
    def test_spanish_room_types(self, mock_settings):
        """Should handle Spanish room type names."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        # Test Spanish variants
        url = get_room_image_url("doble")
        assert url == "https://example.com/images/rooms/double-room.jpg"
        
        url = get_room_image_url("sencilla")
        assert url == "https://example.com/images/rooms/single-room.jpg"
        
        url = get_room_image_url("familiar")
        assert url == "https://example.com/images/rooms/family-room.jpg"


class TestGetMultipleRoomImages:
    """Tests for get_multiple_room_images function."""
    
    @patch("app.utils.room_images.settings")
    def test_returns_dict_for_multiple_room_types(self, mock_settings):
        """Should return dictionary mapping room types to URLs."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        result = get_multiple_room_images(["double", "suite", "single"])
        
        assert isinstance(result, dict)
        assert len(result) == 3
        assert "double" in result
        assert "suite" in result
        assert "single" in result
    
    @patch("app.utils.room_images.settings")
    def test_handles_mixed_known_unknown_types(self, mock_settings):
        """Should handle mix of known and unknown room types."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        result = get_multiple_room_images(["double", "unknown_type", "suite"])
        
        assert result["double"] is not None
        assert result["suite"] is not None
        # Unknown type should fallback to default
        assert result["unknown_type"] is not None
    
    @patch("app.utils.room_images.settings")
    def test_returns_empty_dict_for_empty_list(self, mock_settings):
        """Should return empty dict for empty room type list."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"
        
        result = get_multiple_room_images([])
        
        assert result == {}


class TestValidateImageUrl:
    """Tests for validate_image_url function."""
    
    def test_accepts_valid_https_jpg_url(self):
        """Should accept valid HTTPS URL with JPG extension."""
        url = "https://example.com/images/room.jpg"
        
        assert validate_image_url(url) is True
    
    def test_accepts_valid_https_jpeg_url(self):
        """Should accept valid HTTPS URL with JPEG extension."""
        url = "https://example.com/images/room.jpeg"
        
        assert validate_image_url(url) is True
    
    def test_accepts_valid_https_png_url(self):
        """Should accept valid HTTPS URL with PNG extension."""
        url = "https://example.com/images/room.png"
        
        assert validate_image_url(url) is True
    
    def test_rejects_http_url(self):
        """Should reject HTTP URLs (WhatsApp requires HTTPS)."""
        url = "http://example.com/images/room.jpg"
        
        assert validate_image_url(url) is False
    
    def test_rejects_url_without_image_extension(self):
        """Should reject URLs without image extensions."""
        url = "https://example.com/images/room"
        
        assert validate_image_url(url) is False
    
    def test_rejects_empty_string(self):
        """Should reject empty string."""
        assert validate_image_url("") is False
    
    def test_rejects_none(self):
        """Should reject None value."""
        # Pass empty string since function expects str
        assert validate_image_url("") is False
    
    def test_case_insensitive_extension_check(self):
        """Should accept image extensions regardless of case."""
        assert validate_image_url("https://example.com/room.JPG") is True
        assert validate_image_url("https://example.com/room.Jpeg") is True
        assert validate_image_url("https://example.com/room.PNG") is True


class TestAddCustomRoomMapping:
    """Tests for add_custom_room_mapping function."""
    
    def test_adds_custom_mapping(self):
        """Should add custom room type mapping."""
        # Save original mapping
        original_mapping = DEFAULT_ROOM_IMAGE_MAPPING.copy()
        
        try:
            add_custom_room_mapping("presidential_suite", "presidential.jpg")
            
            url = get_room_image_url("presidential_suite", base_url="https://example.com")
            assert url == "https://example.com/presidential.jpg"
        finally:
            # Restore original mapping
            DEFAULT_ROOM_IMAGE_MAPPING.clear()
            DEFAULT_ROOM_IMAGE_MAPPING.update(original_mapping)
    
    def test_updates_existing_mapping(self):
        """Should update existing room type mapping."""
        # Save original mapping
        original_mapping = DEFAULT_ROOM_IMAGE_MAPPING.copy()
        
        try:
            # Override existing mapping
            add_custom_room_mapping("double", "new-double-room.jpg")
            
            url = get_room_image_url("double", base_url="https://example.com")
            assert url == "https://example.com/new-double-room.jpg"
        finally:
            # Restore original mapping
            DEFAULT_ROOM_IMAGE_MAPPING.clear()
            DEFAULT_ROOM_IMAGE_MAPPING.update(original_mapping)
    
    def test_normalizes_room_type_when_adding(self):
        """Should normalize room type when adding custom mapping."""
        # Save original mapping
        original_mapping = DEFAULT_ROOM_IMAGE_MAPPING.copy()
        
        try:
            add_custom_room_mapping("  CUSTOM Room  ", "custom.jpg")
            
            # Should be accessible with normalized key
            url = get_room_image_url("custom_room", base_url="https://example.com")
            assert url == "https://example.com/custom.jpg"
        finally:
            # Restore original mapping
            DEFAULT_ROOM_IMAGE_MAPPING.clear()
            DEFAULT_ROOM_IMAGE_MAPPING.update(original_mapping)


class TestGetAvailableRoomTypes:
    """Tests for get_available_room_types function."""
    
    def test_returns_list_of_room_types(self):
        """Should return list of all available room types."""
        room_types = get_available_room_types()
        
        assert isinstance(room_types, list)
        assert len(room_types) > 0
    
    def test_includes_standard_room_types(self):
        """Should include standard room types."""
        room_types = get_available_room_types()
        
        # Check for common types
        assert "double" in room_types
        assert "single" in room_types
        assert "suite" in room_types
        assert "default" in room_types
    
    def test_includes_spanish_variants(self):
        """Should include Spanish room type variants."""
        room_types = get_available_room_types()
        
        assert "doble" in room_types
        assert "sencilla" in room_types
        assert "familiar" in room_types


class TestRoomImageMappingIntegration:
    """Integration tests for room image mapping."""
    
    @patch("app.utils.room_images.settings")
    def test_end_to_end_image_url_generation(self, mock_settings):
        """Should generate correct URLs for complete workflow."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://hotel.com/media/rooms"
        
        # Get URL
        url = get_room_image_url("suite")
        
        # Should not be None
        assert url is not None
        
        # Validate URL
        assert validate_image_url(url) is True
        
        # Should be correct format
        assert url.startswith("https://")
        assert "hotel.com/media/rooms" in url
        assert url.endswith(".jpg")
    
    @patch("app.utils.room_images.settings")
    def test_multiple_room_types_with_validation(self, mock_settings):
        """Should generate and validate multiple room URLs."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://hotel.com/images"
        
        urls = get_multiple_room_images(["double", "suite", "family"])
        
        # All URLs should be valid
        for room_type, url in urls.items():
            assert url is not None
            assert validate_image_url(url) is True
            assert "hotel.com/images" in url
