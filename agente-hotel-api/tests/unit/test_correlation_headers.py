import pytest
from unittest.mock import MagicMock

from app.core.correlation import set_correlation_id
from app.services.whatsapp_client import WhatsAppMetaClient
from app.services.qloapps_client import QloAppsClient
from app.services.gmail_client import GmailIMAPClient


@pytest.mark.asyncio
async def test_whatsapp_client_propagates_correlation_headers(monkeypatch):
    set_correlation_id("corr-123")

    client = WhatsAppMetaClient()

    captured = {}

    async def fake_post(url, json=None, headers=None):
        # Simulate WhatsApp API success response
        captured["headers"] = headers or {}
        class _Resp:
            status_code = 200
            def json(self):
                return {"messages": [{"id": "wamid.test"}]}
        return _Resp()

    monkeypatch.setattr(client.client, "post", fake_post)

    await client.send_message(to="14155552671", text="hola")

    assert captured["headers"].get("X-Request-ID") == "corr-123"
    assert captured["headers"].get("X-Correlation-ID") == "corr-123"


@pytest.mark.asyncio
async def test_qloapps_client_propagates_correlation_headers(monkeypatch):
    set_correlation_id("corr-abc")

    qlo = QloAppsClient(base_url="https://hotel.test", api_key="key")

    captured = {}

    async def fake_request(method, url, params=None, json=None, headers=None):
        captured["headers"] = headers or {}
        class _Resp:
            status_code = 200
            content = b"{}"
            def json(self):
                return {"hotels": []}
        return _Resp()

    monkeypatch.setattr(qlo.client, "request", fake_request)

    await qlo.get_hotels()

    assert captured["headers"].get("X-Request-ID") == "corr-abc"
    assert captured["headers"].get("X-Correlation-ID") == "corr-abc"


def test_gmail_client_sets_correlation_headers_in_email(monkeypatch):
    set_correlation_id("corr-mail")

    sent = {}

    class DummySMTP:
        def __init__(self, *args, **kwargs):
            pass
        def login(self, *args, **kwargs):
            pass
        def send_message(self, msg):
            sent["msg"] = msg
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    # Patch SMTP_SSL constructor
    import app.services.gmail_client as gmail_client_module
    monkeypatch.setattr(gmail_client_module, "smtplib", MagicMock(SMTP_SSL=DummySMTP))

    gmail = GmailIMAPClient()
    assert gmail.send_response(to="guest@example.com", subject="Hi", body="Test")

    msg = sent["msg"]
    assert msg["X-Request-ID"] == "corr-mail"
    assert msg["X-Correlation-ID"] == "corr-mail"
