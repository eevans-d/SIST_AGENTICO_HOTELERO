import pytest

from tests.factories import unified_message, iso_day, tenant_meta, pms_late_checkout_available


@pytest.mark.asyncio
async def test_unified_message_factory_defaults():
    msg = unified_message()
    assert msg.canal == "whatsapp"
    assert msg.tipo == "text"
    assert msg.texto is not None
    assert isinstance(msg.timestamp_iso, str)


def test_iso_day_helper():
    today = iso_day(0)
    tomorrow = iso_day(1)
    assert len(today) == 10 and today.count("-") == 2
    assert len(tomorrow) == 10 and tomorrow.count("-") == 2


def test_tenant_meta_helper():
    meta = tenant_meta(start=8, end=17, timezone_str="America/Argentina/Buenos_Aires")
    assert meta["business_hours_start"] == 8
    assert meta["business_hours_end"] == 17
    assert meta["business_hours_timezone"] == "America/Argentina/Buenos_Aires"


def test_pms_late_checkout_helpers():
    ok = pms_late_checkout_available(fee=1000, requested_time="15:00")
    assert ok["available"] is True and ok["fee"] == 1000 and ok["requested_time"] == "15:00"
