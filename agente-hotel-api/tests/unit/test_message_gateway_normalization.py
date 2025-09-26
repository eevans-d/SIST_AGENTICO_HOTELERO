import pytest
from app.services.message_gateway import MessageGateway, MessageNormalizationError


@pytest.fixture
def gateway():
    return MessageGateway()


def test_normalize_whatsapp_ok_text(gateway):
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "ABCD1234",
                                    "type": "text",
                                    "from": "59811112222",
                                    "timestamp": "1696000000",
                                    "text": {"body": "Hola"},
                                }
                            ],
                            "contacts": [{"wa_id": "59811112222"}],
                        }
                    }
                ]
            }
        ]
    }
    msg = gateway.normalize_whatsapp_message(payload)
    assert msg.user_id == "59811112222"
    assert msg.texto == "Hola"
    assert msg.canal == "whatsapp"
    assert msg.tenant_id


@pytest.mark.parametrize(
    "payload,code",
    [
        ({}, "missing_entry"),
        ({"entry": [{"changes": []}]}, "missing_changes"),
        ({"entry": [{"changes": [{"value": {"messages": []}}]}]}, "missing_messages"),
    ],
)
def test_normalize_whatsapp_errors(gateway, payload, code):
    with pytest.raises(MessageNormalizationError) as exc:
        gateway.normalize_whatsapp_message(payload)
    assert code in str(exc.value)
