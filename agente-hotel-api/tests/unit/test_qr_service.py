"""
Unit tests for QR Service.
Feature 5: QR Codes en Confirmaciones

Nota: Requiere la librería externa "qrcode". Si no está instalada en el
perfil base, omitimos este módulo para no romper la suite mínima.

Tests:
- QR code generation for bookings
- QR code generation for check-in
- QR code generation for services
- Error handling
- Cleanup functionality
- Statistics
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import json
from datetime import datetime

try:
    import qrcode  # noqa: F401
    from app.services.qr_service import QRService, get_qr_service  # type: ignore
except Exception:  # noqa: BLE001
    pytest.skip("Librería qrcode no disponible en el entorno base", allow_module_level=True)


class TestQRService:
    """Unit tests for QR Service."""

    @pytest.fixture
    def qr_service(self):
        """Create QR service instance for testing."""
        return QRService()

    @pytest.fixture
    def sample_booking_data(self):
        """Sample booking data for testing."""
        return {
            "booking_id": "HTL-12345",
            "guest_name": "Juan Pérez",
            "check_in_date": "2025-10-15",
            "check_out_date": "2025-10-17",
            "room_number": "205",
            "hotel_name": "Hotel Test",
        }

    def test_generate_booking_qr_success(self, qr_service, sample_booking_data):
        """Test successful booking QR code generation."""
        result = qr_service.generate_booking_qr(**sample_booking_data)

        assert result["success"] is True
        assert result["qr_data"]["type"] == "booking_confirmation"
        assert result["qr_data"]["booking_id"] == "HTL-12345"
        assert result["qr_data"]["guest_name"] == "Juan Pérez"
        assert result["qr_data"]["check_in"] == "2025-10-15"
        assert result["qr_data"]["check_out"] == "2025-10-17"
        assert result["qr_data"]["hotel"] == "Hotel Test"
        assert "generated_at" in result["qr_data"]

        # Verify file was created
        assert result["file_path"] is not None
        assert Path(result["file_path"]).exists()
        assert result["filename"].startswith("booking_HTL-12345_")
        assert result["filename"].endswith(".png")
        assert result["size_bytes"] > 0

    def test_generate_booking_qr_with_room_number(self, qr_service, sample_booking_data):
        """Test booking QR generation includes room number when provided."""
        result = qr_service.generate_booking_qr(**sample_booking_data)

        assert result["success"] is True
        assert result["qr_data"]["room_number"] == "205"

    def test_generate_booking_qr_without_room_number(self, qr_service, sample_booking_data):
        """Test booking QR generation without room number."""
        del sample_booking_data["room_number"]
        result = qr_service.generate_booking_qr(**sample_booking_data)

        assert result["success"] is True
        assert "room_number" not in result["qr_data"]

    def test_generate_checkin_qr_success(self, qr_service):
        """Test successful check-in QR code generation."""
        result = qr_service.generate_checkin_qr(booking_id="HTL-12345", room_number="205", access_code="ABCD1234")

        assert result["success"] is True
        assert result["qr_data"]["type"] == "mobile_checkin"
        assert result["qr_data"]["booking_id"] == "HTL-12345"
        assert result["qr_data"]["room_number"] == "205"
        assert result["qr_data"]["access_code"] == "ABCD1234"

        # Verify file was created
        assert Path(result["file_path"]).exists()
        assert result["filename"].startswith("checkin_HTL-12345_")

    def test_generate_checkin_qr_without_access_code(self, qr_service):
        """Test check-in QR generation without access code."""
        result = qr_service.generate_checkin_qr(booking_id="HTL-12345", room_number="205")

        assert result["success"] is True
        assert "access_code" not in result["qr_data"]

    def test_generate_service_qr_success(self, qr_service):
        """Test successful service QR code generation."""
        service_data = {"wifi_password": "hotel123", "network_name": "Hotel_Guest"}

        result = qr_service.generate_service_qr("wifi", service_data)

        assert result["success"] is True
        assert result["qr_data"]["type"] == "service_wifi"
        assert result["qr_data"]["service_data"] == service_data

        # Verify file was created
        assert Path(result["file_path"]).exists()
        assert result["filename"].startswith("service_wifi_")

    def test_generate_service_qr_different_types(self, qr_service):
        """Test service QR generation for different service types."""
        service_types = ["restaurant", "spa", "gym", "concierge"]

        for service_type in service_types:
            result = qr_service.generate_service_qr(service_type, {"service_id": f"{service_type}_001"})

            assert result["success"] is True
            assert result["qr_data"]["type"] == f"service_{service_type}"
            assert Path(result["file_path"]).exists()

    @patch("app.services.qr_service.qrcode.QRCode")
    def test_generate_booking_qr_error_handling(self, mock_qr_code, qr_service, sample_booking_data):
        """Test error handling during QR generation."""
        mock_qr_code.side_effect = Exception("QR generation failed")

        result = qr_service.generate_booking_qr(**sample_booking_data)

        assert result["success"] is False
        assert "QR generation failed" in result["error"]
        assert result["qr_data"] is None
        assert result["file_path"] is None

    @patch("app.services.qr_service.qrcode.QRCode")
    def test_generate_checkin_qr_error_handling(self, mock_qr_code, qr_service):
        """Test error handling during check-in QR generation."""
        mock_qr_code.side_effect = Exception("QR generation failed")

        result = qr_service.generate_checkin_qr(booking_id="HTL-12345", room_number="205")

        assert result["success"] is False
        assert result["qr_data"] is None

    @patch("app.services.qr_service.qrcode.QRCode")
    def test_generate_service_qr_error_handling(self, mock_qr_code, qr_service):
        """Test error handling during service QR generation."""
        mock_qr_code.side_effect = Exception("QR generation failed")

        result = qr_service.generate_service_qr("wifi", {"password": "test"})

        assert result["success"] is False
        assert result["qr_data"] is None

    def test_qr_data_structure_booking(self, qr_service, sample_booking_data):
        """Test QR data structure for booking QR codes."""
        result = qr_service.generate_booking_qr(**sample_booking_data)
        qr_data = result["qr_data"]

        # Parse the QR data to verify it's valid JSON
        qr_json = json.dumps(qr_data)
        parsed_data = json.loads(qr_json)

        assert parsed_data["type"] == "booking_confirmation"
        assert "generated_at" in parsed_data

        # Verify timestamp format
        generated_at = datetime.fromisoformat(parsed_data["generated_at"])
        assert isinstance(generated_at, datetime)

    def test_qr_data_structure_checkin(self, qr_service):
        """Test QR data structure for check-in QR codes."""
        result = qr_service.generate_checkin_qr("HTL-12345", "205")
        qr_data = result["qr_data"]

        qr_json = json.dumps(qr_data)
        parsed_data = json.loads(qr_json)

        assert parsed_data["type"] == "mobile_checkin"
        assert "generated_at" in parsed_data

    def test_cleanup_old_qr_codes_success(self, qr_service):
        """Test successful cleanup of old QR codes."""
        # Generate some QR codes first
        qr_service.generate_booking_qr("HTL-001", "Test Guest", "2025-10-15", "2025-10-17")
        qr_service.generate_checkin_qr("HTL-002", "101")

        # Mock file modification times to be old
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 0  # Very old timestamp

            with patch("pathlib.Path.unlink"):
                result = qr_service.cleanup_old_qr_codes(max_age_hours=1)

                assert result["success"] is True
                assert result["deleted_count"] >= 0
                assert "deleted_size_mb" in result

    def test_cleanup_old_qr_codes_error_handling(self, qr_service):
        """Test error handling during cleanup."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.side_effect = Exception("Glob failed")

            result = qr_service.cleanup_old_qr_codes()

            assert result["success"] is False
            assert "Glob failed" in result["error"]
            assert result["deleted_count"] == 0

    def test_get_qr_stats_success(self, qr_service):
        """Test getting QR statistics."""
        # Generate some QR codes
        qr_service.generate_booking_qr("HTL-001", "Test Guest", "2025-10-15", "2025-10-17")
        qr_service.generate_checkin_qr("HTL-002", "101")
        qr_service.generate_service_qr("wifi", {"password": "test"})

        stats = qr_service.get_qr_stats()

        assert stats["total_files"] >= 3
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] >= 0
        assert "by_type" in stats
        assert stats["by_type"]["booking"] >= 1
        assert stats["by_type"]["checkin"] >= 1
        assert stats["by_type"]["service"] >= 1
        assert "temp_dir" in stats

    def test_get_qr_stats_empty_directory(self, qr_service):
        """Test getting stats when directory is empty."""
        # Mock empty directory
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = []

            stats = qr_service.get_qr_stats()

            assert stats["total_files"] == 0
            assert stats["total_size_bytes"] == 0
            assert stats["total_size_mb"] == 0.0
            assert stats["by_type"] == {}

    def test_get_qr_stats_error_handling(self, qr_service):
        """Test error handling in get_qr_stats."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.side_effect = Exception("Glob failed")

            stats = qr_service.get_qr_stats()

            assert stats["total_files"] == 0
            assert stats["total_size_bytes"] == 0
            assert "error" in stats

    def test_add_branding_success(self, qr_service):
        """Test adding branding to QR images."""
        # Generate a QR to test branding
        result = qr_service.generate_booking_qr("HTL-001", "Test Guest", "2025-10-15", "2025-10-17")

        # Verify file exists and has reasonable size (indicating branding was added)
        assert Path(result["file_path"]).exists()
        file_size = Path(result["file_path"]).stat().st_size
        assert file_size > 1000  # Should be larger than minimal QR due to branding

    @patch("app.services.qr_service.ImageDraw.Draw")
    def test_add_branding_error_handling(self, mock_draw, qr_service):
        """Test error handling in branding addition."""
        mock_draw.side_effect = Exception("Draw failed")

        # Should still generate QR even if branding fails
        result = qr_service.generate_booking_qr("HTL-001", "Test Guest", "2025-10-15", "2025-10-17")

        assert result["success"] is True
        assert Path(result["file_path"]).exists()

    def test_singleton_pattern(self):
        """Test that get_qr_service returns the same instance."""
        service1 = get_qr_service()
        service2 = get_qr_service()

        assert service1 is service2
        assert isinstance(service1, QRService)

    def test_temp_directory_creation(self, qr_service):
        """Test that temp directory is created on initialization."""
        assert qr_service.temp_dir.exists()
        assert qr_service.temp_dir.is_dir()

    def test_qr_config_values(self, qr_service):
        """Test QR configuration values are set correctly."""
        config = qr_service.qr_config

        assert config["version"] == 1
        assert config["error_correction"] is not None
        assert config["box_size"] == 10
        assert config["border"] == 4

    def test_file_naming_patterns(self, qr_service):
        """Test that generated files follow naming patterns."""
        # Booking QR
        booking_result = qr_service.generate_booking_qr("HTL-001", "Test", "2025-10-15", "2025-10-17")
        assert booking_result["filename"].startswith("booking_HTL-001_")
        assert booking_result["filename"].endswith(".png")

        # Check-in QR
        checkin_result = qr_service.generate_checkin_qr("HTL-002", "101")
        assert checkin_result["filename"].startswith("checkin_HTL-002_")
        assert checkin_result["filename"].endswith(".png")

        # Service QR
        service_result = qr_service.generate_service_qr("wifi", {"test": "data"})
        assert service_result["filename"].startswith("service_wifi_")
        assert service_result["filename"].endswith(".png")

    def test_file_cleanup_after_tests(self, qr_service):
        """Test cleanup functionality works after generating test files."""
        initial_stats = qr_service.get_qr_stats()

        # Generate some files
        qr_service.generate_booking_qr("TEST-001", "Test", "2025-10-15", "2025-10-17")
        qr_service.generate_checkin_qr("TEST-002", "101")

        after_stats = qr_service.get_qr_stats()
        assert after_stats["total_files"] >= initial_stats["total_files"] + 2

        # Clean up (with 0 hours to force deletion)
        cleanup_result = qr_service.cleanup_old_qr_codes(max_age_hours=0)
        assert cleanup_result["success"] is True
        assert cleanup_result["deleted_count"] >= 2

    def test_qr_data_json_serializable(self, qr_service):
        """Test that all QR data is JSON serializable."""
        booking_result = qr_service.generate_booking_qr("HTL-001", "Test Guest", "2025-10-15", "2025-10-17")

        # Should not raise exception
        json_str = json.dumps(booking_result["qr_data"])
        parsed_back = json.loads(json_str)

        assert parsed_back["booking_id"] == "HTL-001"
        assert parsed_back["type"] == "booking_confirmation"
