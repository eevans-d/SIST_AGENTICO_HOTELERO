# [PHASE D.6] tests/unit/test_business_metrics.py

"""
Unit tests para business metrics helpers.
Verifica que todas las funciones auxiliares funcionen correctamente.
"""

import pytest
from app.services.business_metrics import (
    record_reservation,
    failed_reservations,
    intents_detected,
    nlp_fallbacks,
    messages_by_channel,
    update_operational_metrics,
)


class TestBusinessMetrics:
    """Test suite para business metrics module."""

    def test_record_reservation_basic(self):
        """Test básico de record_reservation."""
        # Arrange
        status = "confirmed"
        channel = "whatsapp"
        room_type = "standard"
        value = 150.0
        nights = 2
        lead_time_days = 7
        
        # Act
        try:
            record_reservation(status, channel, room_type, value, nights, lead_time_days)
            success = True
        except Exception:
            success = False
        
        # Assert
        assert success, "record_reservation should not raise exception with valid data"

    def test_record_reservation_with_different_room_types(self):
        """Test record_reservation con diferentes tipos de habitación."""
        room_types = ["standard", "deluxe", "suite"]
        
        for room_type in room_types:
            try:
                record_reservation("confirmed", "whatsapp", room_type, 100.0, 2, 7)
                success = True
            except Exception:
                success = False
            
            assert success, f"record_reservation should work with room_type={room_type}"

    def test_failed_reservations_counter(self):
        """Test que failed_reservations incrementa correctamente."""
        # Arrange
        initial_value = failed_reservations._value.get()
        
        # Act
        failed_reservations.inc()
        
        # Assert
        new_value = failed_reservations._value.get()
        assert new_value > initial_value, "failed_reservations counter should increment"

    def test_intents_detected_with_labels(self):
        """Test intents_detected con diferentes labels."""
        # Arrange
        intents = ["check_availability", "make_reservation", "pricing_info"]
        confidence_levels = ["high", "medium", "low"]
        
        # Act & Assert
        for intent in intents:
            for confidence in confidence_levels:
                try:
                    intents_detected.labels(intent=intent, confidence_level=confidence).inc()
                    success = True
                except Exception:
                    success = False
                
                assert success, f"intents_detected should work with intent={intent}, confidence={confidence}"

    def test_nlp_fallbacks_increment(self):
        """Test que nlp_fallbacks puede incrementar."""
        # Arrange
        initial = nlp_fallbacks._value.get()
        
        # Act
        nlp_fallbacks.inc()
        
        # Assert
        new_value = nlp_fallbacks._value.get()
        assert new_value > initial, "nlp_fallbacks should increment"

    def test_messages_by_channel_labels(self):
        """Test messages_by_channel con diferentes canales."""
        # Arrange
        channels = ["whatsapp", "gmail", "telegram"]
        
        # Act & Assert
        for channel in channels:
            try:
                messages_by_channel.labels(channel=channel).inc()
                success = True
            except Exception:
                success = False
            
            assert success, f"messages_by_channel should work with channel={channel}"

    def test_update_operational_metrics(self):
        """Test update_operational_metrics ejecuta sin errores."""
        # Act
        try:
            update_operational_metrics(
                current_occupancy=75.5,
                rooms_available={"standard": 10, "deluxe": 5, "suite": 2},
                daily_rev=5000.0,
                adr=125.0
            )
            success = True
        except Exception:
            success = False
        
        # Assert
        assert success, "update_operational_metrics should execute without errors"

    def test_record_reservation_edge_cases(self):
        """Test edge cases para record_reservation."""
        # Test con diferentes status
        statuses = ["confirmed", "pending", "failed"]
        for status in statuses:
            try:
                record_reservation(status, "whatsapp", "standard", 100.0, 2, 7)
                success = True
            except Exception:
                success = False
            assert success, f"Should handle status={status}"
        
        # Test con precio 0
        try:
            record_reservation("confirmed", "whatsapp", "standard", 0.0, 2, 7)
            success = True
        except Exception:
            success = False
        assert success, "Should handle 0 value"
        
        # Test con 0 noches
        try:
            record_reservation("confirmed", "whatsapp", "standard", 100.0, 0, 7)
            success = True
        except Exception:
            success = False
        assert success, "Should handle 0 nights"

    @pytest.mark.parametrize("status,channel,room_type,value,nights,lead_time", [
        ("confirmed", "whatsapp", "standard", 75.0, 1, 3),
        ("confirmed", "gmail", "deluxe", 150.0, 2, 7),
        ("pending", "whatsapp", "suite", 300.0, 3, 14),
        ("confirmed", "gmail", "presidential", 500.0, 5, 30),
    ])
    def test_record_reservation_parametrized(self, status, channel, room_type, value, nights, lead_time):
        """Test parametrizado para diferentes combinaciones."""
        try:
            record_reservation(status, channel, room_type, value, nights, lead_time)
            success = True
        except Exception:
            success = False
        
        assert success, f"Should work with status={status}, channel={channel}, room_type={room_type}"
