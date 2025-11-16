import re
from unittest.mock import Mock

from app.core.tracing import SafeSpanProcessor


class DummyExporter:
    """Minimal span exporter used for testing SafeSpanProcessor."""

    def __init__(self):
        self.exported_spans = []

    def export(self, spans):  # type: ignore[override]
        self.exported_spans.extend(spans)
        return None

    def shutdown(self):  # pragma: no cover - not needed in tests
        return None


def test_safe_span_processor_redacts_email_and_phone():
    exporter = DummyExporter()
    processor = SafeSpanProcessor(exporter)

    # Create a mock span with attributes
    span = Mock()
    span.attributes = {
        "user.email": "guest@example.com",
        "user.phone": "+54 9 11 1234-5678",
        "business.note": "Cliente contacto: guest@example.com / +54 9 11 1234-5678",
    }

    processor.on_end(span)

    # Verify PII was redacted
    for value in span.attributes.values():
        if isinstance(value, str):
            assert "guest@example.com" not in value
            assert "+54 9 11 1234-5678" not in value
            assert "[redacted]" in value or value == "[redacted]"


def test_safe_span_processor_keeps_non_pii_attributes():
    exporter = DummyExporter()
    processor = SafeSpanProcessor(exporter)

    # Create a mock span with non-PII attributes
    span = Mock()
    span.attributes = {"tenant.id": "hotel-123", "room.count": 3}

    processor.on_end(span)

    # Verify non-PII attributes remain unchanged
    assert span.attributes["tenant.id"] == "hotel-123"
    assert span.attributes["room.count"] == 3
