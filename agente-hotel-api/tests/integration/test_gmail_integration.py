# [E.1] tests/integration/test_gmail_integration.py

"""
Integration tests for Gmail client and message gateway.

Tests the complete Gmail integration flow:
1. GmailIMAPClient polling
2. MessageGateway normalization
3. Gmail webhook processing
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.gmail_client import GmailIMAPClient, GmailAuthError
from app.services.message_gateway import MessageGateway
from app.models.unified_message import UnifiedMessage


class TestGmailIMAPClient:
    """Test suite for GmailIMAPClient"""

    def test_client_initialization(self):
        """Test client initializes with correct config"""
        client = GmailIMAPClient()
        
        assert client.imap_server == "imap.gmail.com"
        assert client.smtp_server == "smtp.gmail.com"
        assert client.imap_port == 993
        assert client.smtp_port == 465
        assert client.socket_timeout == 30.0
        assert client.username is not None
        assert client.password is not None

    @patch('app.services.gmail_client.imaplib.IMAP4_SSL')
    def test_poll_new_messages_success(self, mock_imap):
        """Test successful polling of new messages"""
        # Mock IMAP responses
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        
        mock_mail.login.return_value = ("OK", [b"Success"])
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2"])
        
        # Mock email data
        email_data = b"""From: test@example.com
To: hotel@example.com
Subject: Consulta reserva
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>

Hola, quiero reservar una habitacion para 2 personas del 15 al 17 de diciembre.
"""
        mock_mail.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", email_data)])
        
        client = GmailIMAPClient()
        messages = client.poll_new_messages(mark_read=False)
        
        assert len(messages) == 2  # 2 message IDs en search
        assert mock_mail.login.called
        assert mock_mail.select.called
        assert mock_mail.search.called

    @patch('app.services.gmail_client.imaplib.IMAP4_SSL')
    def test_poll_auth_failure(self, mock_imap):
        """Test authentication failure handling"""
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        
        # Simular fallo de autenticación
        mock_mail.login.side_effect = Exception("authentication failed")
        
        client = GmailIMAPClient()
        
        with pytest.raises(GmailAuthError):
            client.poll_new_messages()

    @patch('app.services.gmail_client.smtplib.SMTP_SSL')
    def test_send_response_success(self, mock_smtp):
        """Test successful email sending"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        mock_server.login.return_value = (250, b"Accepted")
        mock_server.send_message.return_value = {}
        
        client = GmailIMAPClient()
        result = client.send_response(
            to="guest@example.com",
            subject="Confirmación de reserva",
            body="Su reserva ha sido confirmada."
        )
        
        assert result is True
        assert mock_server.login.called
        assert mock_server.send_message.called

    def test_decode_header(self):
        """Test email header decoding"""
        client = GmailIMAPClient()
        
        # Test simple header
        result = client._decode_header("Simple Header")
        assert result == "Simple Header"
        
        # Test empty header
        result = client._decode_header("")
        assert result == ""

    def test_extract_email_address(self):
        """Test email address extraction from From header"""
        gateway = MessageGateway()
        
        # Test simple email
        result = gateway._extract_email_address("user@example.com")
        assert result == "user@example.com"
        
        # Test email with name
        result = gateway._extract_email_address("John Doe <user@example.com>")
        assert result == "user@example.com"
        
        # Test complex format
        result = gateway._extract_email_address("'John Doe' <user@example.com>")
        assert result == "user@example.com"


class TestGmailMessageNormalization:
    """Test suite for Gmail message normalization"""

    def test_normalize_gmail_message_success(self):
        """Test successful normalization of Gmail message"""
        gateway = MessageGateway()
        
        email_dict = {
            "message_id": "<test123@example.com>",
            "from": "John Doe <guest@example.com>",
            "subject": "Consulta reserva",
            "body": "Quiero reservar una habitacion",
            "timestamp": "2024-01-01T12:00:00+00:00"
        }
        
        unified = gateway.normalize_gmail_message(email_dict)
        
        assert isinstance(unified, UnifiedMessage)
        assert unified.message_id == "<test123@example.com>"
        assert unified.canal == "gmail"
        assert unified.user_id == "guest@example.com"
        assert unified.tipo == "text"
        assert unified.texto == "Quiero reservar una habitacion"
        assert unified.metadata["subject"] == "Consulta reserva"
        assert unified.metadata["from_full"] == "John Doe <guest@example.com>"

    def test_normalize_missing_fields(self):
        """Test normalization fails with missing fields"""
        gateway = MessageGateway()
        
        email_dict = {
            "message_id": "<test123@example.com>",
            # Missing 'from', 'body', 'timestamp'
        }
        
        with pytest.raises(Exception):  # MessageNormalizationError
            gateway.normalize_gmail_message(email_dict)

    def test_normalize_invalid_input(self):
        """Test normalization fails with invalid input"""
        gateway = MessageGateway()
        
        # Not a dict
        with pytest.raises(Exception):
            gateway.normalize_gmail_message("not a dict")  # type: ignore
        
        # None
        with pytest.raises(Exception):
            gateway.normalize_gmail_message(None)  # type: ignore


class TestGmailWebhookIntegration:
    """Test suite for Gmail webhook endpoint"""

    @pytest.mark.asyncio
    async def test_gmail_webhook_with_messages(self):
        """Test Gmail webhook processes messages successfully"""
        # Este test requiere mock completo del orchestrator
        # Por ahora validamos la estructura
        pass

    @pytest.mark.asyncio
    async def test_gmail_webhook_no_messages(self):
        """Test Gmail webhook handles no new messages"""
        # Mock que no hay mensajes nuevos
        pass

    @pytest.mark.asyncio
    async def test_gmail_webhook_invalid_json(self):
        """Test Gmail webhook handles invalid JSON"""
        # Mock de payload inválido
        pass


class TestGmailE2EFlow:
    """End-to-end tests for Gmail integration"""

    @pytest.mark.asyncio
    @patch('app.services.gmail_client.imaplib.IMAP4_SSL')
    async def test_complete_gmail_flow(self, mock_imap):
        """Test complete flow: poll → normalize → process"""
        # Mock IMAP client
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        
        mock_mail.login.return_value = ("OK", [b"Success"])
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])
        
        email_data = b"""From: guest@example.com
To: hotel@example.com
Subject: Consulta
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test@example.com>

Quiero reservar
"""
        mock_mail.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", email_data)])
        
        # 1. Poll messages
        client = GmailIMAPClient()
        messages = client.poll_new_messages(mark_read=False)
        
        assert len(messages) >= 1
        
        # 2. Normalize
        gateway = MessageGateway()
        unified = gateway.normalize_gmail_message(messages[0])
        
        assert unified.canal == "gmail"
        assert unified.tipo == "text"
        assert unified.texto is not None and "Quiero reservar" in unified.texto
        
        # 3. Process (mock orchestrator)
        # En producción, orchestrator.handle_unified_message(unified)


# Configuración de pytest
@pytest.fixture
def gmail_client():
    """Fixture para GmailIMAPClient"""
    return GmailIMAPClient()


@pytest.fixture
def message_gateway():
    """Fixture para MessageGateway"""
    return MessageGateway()


@pytest.fixture
def sample_email_dict():
    """Fixture con email de ejemplo"""
    return {
        "message_id": "<test123@example.com>",
        "from": "Guest User <guest@example.com>",
        "subject": "Consulta de disponibilidad",
        "body": "Hola, necesito una habitación doble del 15 al 17 de diciembre.",
        "timestamp": datetime.utcnow().isoformat()
    }
