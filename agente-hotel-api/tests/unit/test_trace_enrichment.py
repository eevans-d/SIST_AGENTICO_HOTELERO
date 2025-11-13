"""
Tests for Trace Enrichment (H1)

Validates that business context is properly added to OpenTelemetry spans.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request

from app.core.tracing import enrich_span_from_request, enrich_span_with_business_context


@pytest.fixture
def mock_span():
    """Create a mock OpenTelemetry span."""
    span = Mock()
    span.is_recording.return_value = True
    span.attributes = {}
    
    # Mock set_attribute to store in attributes dict
    def mock_set_attribute(key, value):
        span.attributes[key] = value
    
    span.set_attribute.side_effect = mock_set_attribute
    return span


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request with state attributes."""
    request = Mock(spec=Request)
    request.state = Mock()
    request.state.tenant_id = "test-tenant-123"
    request.state.user_id = "guest-456"
    request.state.channel = "whatsapp"
    request.state.correlation_id = "corr-789"
    request.method = "POST"
    request.url = Mock()
    request.url.path = "/api/webhooks/whatsapp"
    return request


class TestEnrichSpanFromRequest:
    """Test enrich_span_from_request helper."""
    
    def test_enrich_span_with_all_attributes(self, mock_span, mock_request):
        """Test that all request attributes are added to span."""
        enrich_span_from_request(mock_span, mock_request)
        
        # Verify all attributes were set
        assert mock_span.attributes.get("tenant.id") == "test-tenant-123"
        assert mock_span.attributes.get("user.id") == "guest-456"
        assert mock_span.attributes.get("channel.type") == "whatsapp"
        assert mock_span.attributes.get("request.correlation_id") == "corr-789"
        assert mock_span.attributes.get("http.method") == "POST"
        assert mock_span.attributes.get("http.route") == "/api/webhooks/whatsapp"
    
    def test_enrich_span_with_partial_attributes(self, mock_span):
        """Test that enrichment works with missing attributes."""
        # Request with only some attributes
        request = Mock(spec=Request)
        # Use MagicMock with spec to avoid auto-generation of missing attributes
        class StateStub:
            tenant_id = "tenant-only"
            user_id = None
            channel = None
            canal = None
            correlation_id = None
        
        request.state = StateStub()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/health"
        
        enrich_span_from_request(mock_span, request)
        
        # Only tenant_id and http attrs should be set
        assert mock_span.attributes.get("tenant.id") == "tenant-only"
        assert "user.id" not in mock_span.attributes  # None values not added
        assert "channel.type" not in mock_span.attributes
        assert "request.correlation_id" not in mock_span.attributes
        assert mock_span.attributes.get("http.method") == "GET"
    
    def test_enrich_span_not_recording(self, mock_request):
        """Test that enrichment is skipped if span is not recording."""
        span = Mock()
        span.is_recording.return_value = False
        
        # Should not raise exception
        enrich_span_from_request(span, mock_request)
        
        # Verify set_attribute was never called
        span.set_attribute.assert_not_called()
    
    def test_enrich_span_with_canal_fallback(self, mock_span):
        """Test that 'canal' is used as fallback for 'channel'."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.channel = None  # No 'channel'
        request.state.canal = "gmail"  # But 'canal' exists (Spanish)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/webhooks/gmail"
        
        enrich_span_from_request(mock_span, request)
        
        # Should use 'canal' as fallback
        assert mock_span.attributes.get("channel.type") == "gmail"


class TestEnrichSpanWithBusinessContext:
    """Test enrich_span_with_business_context helper."""
    
    def test_enrich_with_intent_and_confidence(self, mock_span):
        """Test enrichment with NLP intent and confidence."""
        enrich_span_with_business_context(
            mock_span,
            intent="check_availability",
            confidence=0.95,
            operation="nlp_processing",
        )
        
        assert mock_span.attributes.get("business.intent") == "check_availability"
        assert mock_span.attributes.get("business.confidence") == 0.95
        assert mock_span.attributes.get("business.operation") == "nlp_processing"
    
    def test_enrich_with_custom_kwargs(self, mock_span):
        """Test enrichment with custom business attributes."""
        enrich_span_with_business_context(
            mock_span,
            operation="pms_query",
            check_in="2025-11-20",
            check_out="2025-11-22",
            room_type="deluxe",
            guests=2,
        )
        
        assert mock_span.attributes.get("business.operation") == "pms_query"
        assert mock_span.attributes.get("business.check_in") == "2025-11-20"
        assert mock_span.attributes.get("business.check_out") == "2025-11-22"
        assert mock_span.attributes.get("business.room_type") == "deluxe"
        assert mock_span.attributes.get("business.guests") == 2
    
    def test_enrich_with_none_values(self, mock_span):
        """Test that None values are not added to span."""
        enrich_span_with_business_context(
            mock_span,
            intent=None,
            confidence=None,
            operation="test",
            check_in=None,
        )
        
        # Only non-None operation should be set
        assert mock_span.attributes.get("business.operation") == "test"
        assert "business.intent" not in mock_span.attributes
        assert "business.confidence" not in mock_span.attributes
        assert "business.check_in" not in mock_span.attributes
    
    def test_enrich_with_non_primitive_values(self, mock_span):
        """Test that complex objects are converted to strings."""
        from datetime import date
        
        enrich_span_with_business_context(
            mock_span,
            operation="reservation",
            check_in_obj=date(2025, 11, 20),  # date object
            metadata={"key": "value"},  # dict
        )
        
        # Complex objects should be converted to string
        assert mock_span.attributes.get("business.check_in_obj") == "2025-11-20"
        assert "{'key': 'value'}" in mock_span.attributes.get("business.metadata", "")


class TestMiddlewareIntegration:
    """Test tracing enrichment middleware integration."""
    
    @pytest.mark.asyncio
    async def test_middleware_enriches_span(self, mock_request):
        """Test that middleware enriches spans automatically."""
        from app.core.middleware import tracing_enrichment_middleware
        
        # Mock call_next
        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response
        
        # Mock trace.get_current_span to return our mock span
        mock_span = Mock()
        mock_span.is_recording.return_value = True
        mock_span.attributes = {}
        
        def mock_set_attribute(key, value):
            mock_span.attributes[key] = value
        
        mock_span.set_attribute.side_effect = mock_set_attribute
        
        with patch('app.core.middleware.trace.get_current_span', return_value=mock_span):
            response = await tracing_enrichment_middleware(mock_request, mock_call_next)
            
            assert response.status_code == 200
        
        # Middleware should have added these attributes
        assert mock_span.attributes.get("tenant.id") == "test-tenant-123"
        assert mock_span.attributes.get("user.id") == "guest-456"
        assert mock_span.attributes.get("channel.type") == "whatsapp"
        assert mock_span.attributes.get("http.status_code") == 200
    
    @pytest.mark.asyncio
    async def test_middleware_handles_errors_gracefully(self):
        """Test that middleware doesn't fail when enrichment fails."""
        from app.core.middleware import tracing_enrichment_middleware
        
        # Request with broken state (to trigger exception)
        request = Mock(spec=Request)
        request.state = None  # This will cause AttributeError
        
        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response
        
        # Mock span
        mock_span = Mock()
        mock_span.is_recording.return_value = True
        
        with patch('app.core.middleware.trace.get_current_span', return_value=mock_span):
            # Should not raise exception
            response = await tracing_enrichment_middleware(request, mock_call_next)
            assert response.status_code == 200
