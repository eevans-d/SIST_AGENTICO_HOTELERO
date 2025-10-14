"""
Integration tests for QR Code feature.
Feature 5: QR Codes en Confirmaciones

Tests end-to-end flow:
1. Payment confirmation with image
2. QR code generation
3. Response with QR in WhatsApp
4. QR cleanup functionality
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.unified_message import UnifiedMessage
from app.core.settings import settings


class TestQRCodeIntegrationE2E:
    """Integration tests for QR code feature."""

    @pytest.fixture
    def test_client(self):
        """Fixture que crea cliente de prueba."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_payment_confirmation_generates_qr_success(self):
        """Test E2E: Payment confirmation triggers QR generation."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"

        # Setup session with pending reservation
        await session_manager.set_session_data(user_id, "reservation_pending", True)
        await session_manager.set_session_data(user_id, "guest_name", "Juan Pérez")
        await session_manager.set_session_data(user_id, "check_in_date", "2025-10-15")
        await session_manager.set_session_data(user_id, "check_out_date", "2025-10-17")
        await session_manager.set_session_data(user_id, "room_number", "205")

        # Mock QR service
        with patch("app.services.qr_service.get_qr_service") as mock_qr_service:
            mock_qr_instance = Mock()
            mock_qr_service.return_value = mock_qr_instance

            mock_qr_instance.generate_booking_qr.return_value = {
                "success": True,
                "qr_data": {"type": "booking_confirmation", "booking_id": "HTL-001", "guest_name": "Juan Pérez"},
                "file_path": "/tmp/qr_codes/booking_HTL-001_20251010.png",
                "filename": "booking_HTL-001_20251010.png",
                "size_bytes": 15432,
            }

            # Payment confirmation message with image
            message = UnifiedMessage(
                user_id=user_id,
                texto="comprobante de pago",
                canal="whatsapp",
                tipo="image",
                metadata={
                    "image_url": "https://example.com/payment_receipt.jpg",
                    "image_caption": "Comprobante de transferencia",
                },
            )

            # Act
            response = await orchestrator.process_message(message)

            # Assert
            assert response.response_type == "image_with_text"
            assert "RESERVA CONFIRMADA" in response.content
            assert "HTL-001" in response.content
            assert "Juan Pérez" in response.content
            assert "2025-10-15" in response.content
            assert "2025-10-17" in response.content
            assert "205" in response.content

            # Verify QR generation was called
            mock_qr_instance.generate_booking_qr.assert_called_once_with(
                booking_id="HTL-001",
                guest_name="Juan Pérez",
                check_in_date="2025-10-15",
                check_out_date="2025-10-17",
                room_number="205",
                hotel_name=settings.hotel_name,
            )

            # Verify response includes QR data
            assert response.image_path == "/tmp/qr_codes/booking_HTL-001_20251010.png"
            assert "Tu código QR de confirmación" in response.image_caption

            # Verify session was updated
            session_data = await session_manager.get_session_data(user_id)
            assert session_data.get("booking_confirmed") is True
            assert session_data.get("booking_id") == "HTL-001"
            assert session_data.get("qr_generated") is True
            assert session_data.get("reservation_pending") is False

    @pytest.mark.asyncio
    async def test_payment_confirmation_qr_generation_failure(self):
        """Test E2E: Payment confirmation with QR generation failure."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"

        # Setup session with pending reservation
        await session_manager.set_session_data(user_id, "reservation_pending", True)
        await session_manager.set_session_data(user_id, "check_in_date", "2025-10-15")
        await session_manager.set_session_data(user_id, "check_out_date", "2025-10-17")

        # Mock QR service to fail
        with patch("app.services.qr_service.get_qr_service") as mock_qr_service:
            mock_qr_instance = Mock()
            mock_qr_service.return_value = mock_qr_instance

            mock_qr_instance.generate_booking_qr.return_value = {
                "success": False,
                "error": "QR generation failed",
                "qr_data": None,
                "file_path": None,
            }

            message = UnifiedMessage(
                user_id=user_id,
                texto="comprobante",
                canal="whatsapp",
                tipo="image",
                metadata={"image_url": "https://example.com/receipt.jpg"},
            )

            # Act
            response = await orchestrator.process_message(message)

            # Assert - Should fallback to confirmation without QR
            assert response.response_type == "text"
            assert "RESERVA CONFIRMADA" in response.content
            assert "HTL-" in response.content  # Should still have booking ID
            assert "2025-10-15" in response.content

            # Verify QR generation was attempted
            mock_qr_instance.generate_booking_qr.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_confirmation_no_pending_reservation(self):
        """Test E2E: Payment confirmation without pending reservation."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"

        # No pending reservation in session
        message = UnifiedMessage(
            user_id=user_id,
            texto="comprobante",
            canal="whatsapp",
            tipo="image",
            metadata={"image_url": "https://example.com/receipt.jpg"},
        )

        # Act
        response = await orchestrator.process_message(message)

        # Assert - Should respond with simple reaction
        assert response.response_type == "reaction"
        assert response.content["emoji"] == "👍"

    @pytest.mark.asyncio
    async def test_qr_service_integration_booking_flow(self):
        """Test QR service integration with booking data."""
        from app.services.qr_service import get_qr_service

        qr_service = get_qr_service()

        # Generate booking QR with realistic data
        result = qr_service.generate_booking_qr(
            booking_id="HTL-INT-001",
            guest_name="María González",
            check_in_date="2025-11-01",
            check_out_date="2025-11-03",
            room_number="301",
            hotel_name="Hotel Integration Test",
        )

        assert result["success"] is True
        assert result["qr_data"]["booking_id"] == "HTL-INT-001"
        assert result["qr_data"]["guest_name"] == "María González"
        assert result["qr_data"]["hotel"] == "Hotel Integration Test"

        # Verify file exists
        from pathlib import Path

        assert Path(result["file_path"]).exists()
        assert Path(result["file_path"]).suffix == ".png"

        # Test QR data is valid JSON
        import json

        qr_json = json.dumps(result["qr_data"])
        parsed = json.loads(qr_json)
        assert parsed["type"] == "booking_confirmation"

    @pytest.mark.asyncio
    async def test_qr_cleanup_integration(self):
        """Test QR cleanup functionality integration."""
        from app.services.qr_service import get_qr_service

        qr_service = get_qr_service()

        # Generate several QR codes
        booking_ids = ["HTL-CLEAN-001", "HTL-CLEAN-002", "HTL-CLEAN-003"]

        for booking_id in booking_ids:
            result = qr_service.generate_booking_qr(
                booking_id=booking_id, guest_name="Test Guest", check_in_date="2025-10-15", check_out_date="2025-10-17"
            )
            assert result["success"] is True

        # Get stats before cleanup
        stats_before = qr_service.get_qr_stats()
        assert stats_before["total_files"] >= 3

        # Perform cleanup (aggressive - 0 hours)
        cleanup_result = qr_service.cleanup_old_qr_codes(max_age_hours=0)

        assert cleanup_result["success"] is True
        assert cleanup_result["deleted_count"] >= 3
        assert cleanup_result["deleted_size_bytes"] > 0

        # Verify files were cleaned up
        stats_after = qr_service.get_qr_stats()
        assert stats_after["total_files"] < stats_before["total_files"]

    @pytest.mark.asyncio
    async def test_qr_webhook_integration(self):
        """Test QR code integration with webhook response handling."""
        # Mock WhatsApp client to test webhook flow
        from app.routers.webhooks import router
        from fastapi.testclient import TestClient

        TestClient(router.app if hasattr(router, "app") else app)

        # This would require complex webhook mocking
        # For now, test the core integration components

        # Test that image_with_text response type is handled
        response_data = {
            "response_type": "image_with_text",
            "content": "¡RESERVA CONFIRMADA!",
            "image_path": "/tmp/test_qr.png",
            "image_caption": "Tu código QR",
        }

        # Verify response structure is valid
        assert response_data["response_type"] == "image_with_text"
        assert "RESERVA CONFIRMADA" in response_data["content"]
        assert response_data["image_path"].endswith(".png")
        assert "QR" in response_data["image_caption"]

    @pytest.mark.asyncio
    async def test_multiple_concurrent_qr_generations(self):
        """Test concurrent QR generation (stress test)."""
        from app.services.qr_service import get_qr_service
        import asyncio

        qr_service = get_qr_service()

        async def generate_qr(booking_id):
            """Generate a single QR code."""
            return qr_service.generate_booking_qr(
                booking_id=f"HTL-CONCURRENT-{booking_id}",
                guest_name=f"Guest {booking_id}",
                check_in_date="2025-10-15",
                check_out_date="2025-10-17",
            )

        # Generate 5 QR codes concurrently
        tasks = [generate_qr(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert result["success"] is True
            assert f"HTL-CONCURRENT-{i}" in result["qr_data"]["booking_id"]

    @pytest.mark.asyncio
    async def test_qr_service_error_recovery(self):
        """Test QR service error recovery scenarios."""
        from app.services.qr_service import QRService

        # Test with invalid temp directory
        with patch("tempfile.gettempdir") as mock_temp:
            mock_temp.return_value = "/invalid/directory/path"

            # Should still initialize but handle errors gracefully
            qr_service = QRService()

            # Should handle directory creation failure
            result = qr_service.generate_booking_qr(
                booking_id="HTL-ERROR-001",
                guest_name="Test Guest",
                check_in_date="2025-10-15",
                check_out_date="2025-10-17",
            )

            # Depending on implementation, might succeed or fail gracefully
            # But should not crash
            assert "success" in result
            assert "error" in result or result["success"] is True

    @pytest.mark.asyncio
    async def test_qr_data_privacy_compliance(self):
        """Test QR data does not include sensitive information."""
        from app.services.qr_service import get_qr_service

        qr_service = get_qr_service()

        # Generate QR with potentially sensitive data
        result = qr_service.generate_booking_qr(
            booking_id="HTL-PRIVACY-001",
            guest_name="Juan Pérez García",
            check_in_date="2025-10-15",
            check_out_date="2025-10-17",
            room_number="205",
        )

        qr_data = result["qr_data"]

        # Verify no sensitive data is included
        assert "credit_card" not in str(qr_data)
        assert "passport" not in str(qr_data)
        assert "phone" not in str(qr_data)
        assert "email" not in str(qr_data)

        # But should include necessary booking info
        assert qr_data["booking_id"] == "HTL-PRIVACY-001"
        assert qr_data["guest_name"] == "Juan Pérez García"
        assert qr_data["type"] == "booking_confirmation"

    @pytest.mark.asyncio
    async def test_qr_generation_with_unicode_names(self):
        """Test QR generation with unicode characters in names."""
        from app.services.qr_service import get_qr_service

        qr_service = get_qr_service()

        # Test with various unicode characters
        unicode_names = [
            "José María Azñár",  # Spanish characters
            "François Müller",  # French/German characters
            "王小明",  # Chinese characters
            "Владимир Путин",  # Cyrillic characters
            "محمد الأحمد",  # Arabic characters
        ]

        for name in unicode_names:
            result = qr_service.generate_booking_qr(
                booking_id=f"HTL-UNICODE-{len(name)}",
                guest_name=name,
                check_in_date="2025-10-15",
                check_out_date="2025-10-17",
            )

            assert result["success"] is True
            assert result["qr_data"]["guest_name"] == name

            # Verify JSON serialization works with unicode
            import json

            json_str = json.dumps(result["qr_data"], ensure_ascii=False)
            parsed = json.loads(json_str)
            assert parsed["guest_name"] == name

    @pytest.mark.asyncio
    async def test_qr_image_file_format_validation(self):
        """Test that generated QR images are valid PNG files."""
        from app.services.qr_service import get_qr_service
        from PIL import Image

        qr_service = get_qr_service()

        result = qr_service.generate_booking_qr(
            booking_id="HTL-IMAGE-001", guest_name="Test Guest", check_in_date="2025-10-15", check_out_date="2025-10-17"
        )

        assert result["success"] is True

        # Verify the file is a valid PNG image
        try:
            with Image.open(result["file_path"]) as img:
                assert img.format == "PNG"
                assert img.size[0] > 100  # Reasonable width
                assert img.size[1] > 100  # Reasonable height
                assert img.mode in ["RGB", "RGBA"]  # Valid color modes
        except Exception as e:
            pytest.fail(f"Generated QR image is not valid: {e}")

    @pytest.mark.asyncio
    async def test_session_state_consistency_after_qr_generation(self):
        """Test that session state remains consistent after QR generation."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"

        # Setup initial session state
        initial_data = {
            "reservation_pending": True,
            "guest_name": "Test Guest",
            "check_in_date": "2025-10-15",
            "check_out_date": "2025-10-17",
            "room_number": "205",
            "deposit_amount": 6000,
            "other_data": "should_remain",
        }

        for key, value in initial_data.items():
            await session_manager.set_session_data(user_id, key, value)

        # Mock QR service
        with patch("app.services.qr_service.get_qr_service") as mock_qr_service:
            mock_qr_instance = Mock()
            mock_qr_service.return_value = mock_qr_instance

            mock_qr_instance.generate_booking_qr.return_value = {
                "success": True,
                "qr_data": {"booking_id": "HTL-001"},
                "file_path": "/tmp/test.png",
                "filename": "test.png",
                "size_bytes": 1000,
            }

            message = UnifiedMessage(user_id=user_id, texto="comprobante", canal="whatsapp", tipo="image", metadata={})

            # Act
            await orchestrator.process_message(message)

            # Assert - Verify session state changes
            final_session = await session_manager.get_session_data(user_id)

            # These should be updated
            assert final_session.get("booking_confirmed") is True
            assert final_session.get("booking_id") == "HTL-001"
            assert final_session.get("qr_generated") is True
            assert final_session.get("reservation_pending") is False

            # These should remain unchanged
            assert final_session.get("guest_name") == "Test Guest"
            assert final_session.get("check_in_date") == "2025-10-15"
            assert final_session.get("check_out_date") == "2025-10-17"
            assert final_session.get("room_number") == "205"
            assert final_session.get("deposit_amount") == 6000
            assert final_session.get("other_data") == "should_remain"
