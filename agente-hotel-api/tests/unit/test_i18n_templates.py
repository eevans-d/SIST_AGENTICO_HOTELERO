import pytest

from app.services.template_service import TemplateService


@pytest.mark.asyncio
async def test_template_service_i18n_basic():
    svc = TemplateService()

    # Default language is ES
    text_es = svc.get_response(
        "availability_found",
        checkin="2025-10-20",
        checkout="2025-10-22",
        room_type="Doble",
        guests=2,
        price=100,
        total=200,
    )
    assert "¿Querés reservar?" in text_es or "¿Quieres reservar?" in text_es

    # Switch to EN
    svc.set_language("en")
    text_en = svc.get_response(
        "availability_found",
        checkin="2025-10-20",
        checkout="2025-10-22",
        room_type="Double",
        guests=2,
        price=100,
        total=200,
    )
    assert "Would you like to book?" in text_en


@pytest.mark.asyncio
async def test_template_service_fallback_to_es_when_missing():
    svc = TemplateService()
    svc.set_language("en")
    # Use a key that exists in ES dictionary for sure and may not be fully translated elsewhere
    text = svc.get_response("confirmation_received")
    assert isinstance(text, str) and len(text) > 0


@pytest.mark.asyncio
async def test_interactive_buttons_i18n_selection():
    svc = TemplateService()

    # ES by default
    data_es = svc.get_interactive_buttons(
        "availability_confirmation",
        checkin="2025-10-20",
        checkout="2025-10-22",
        room_type="Doble",
        guests=2,
        price=100,
        total=200,
    )
    assert data_es.get("header_text", "").lower().startswith("disponibilidad")
    titles_es = [b.get("title", "") for b in data_es.get("action_buttons", [])]
    assert any("Reservar" in t for t in titles_es)

    # EN
    svc.set_language("en")
    data_en = svc.get_interactive_buttons(
        "availability_confirmation",
        checkin="2025-10-20",
        checkout="2025-10-22",
        room_type="Double",
        guests=2,
        price=100,
        total=200,
    )
    assert data_en.get("header_text", "").lower().startswith("availability")
    titles_en = [b.get("title", "") for b in data_en.get("action_buttons", [])]
    assert any("Book now" in t for t in titles_en)


@pytest.mark.asyncio
async def test_interactive_list_i18n_selection():
    svc = TemplateService()

    list_es = svc.get_interactive_list(
        "room_options",
        checkin="2025-10-20",
        checkout="2025-10-22",
        price_single=50,
        price_double=80,
        price_prem_single=90,
        price_prem_double=120,
    )
    assert list_es.get("list_button_text") == "Ver habitaciones"

    svc.set_language("en")
    list_en = svc.get_interactive_list(
        "room_options",
        checkin="2025-10-20",
        checkout="2025-10-22",
        price_single=50,
        price_double=80,
        price_prem_single=90,
        price_prem_double=120,
    )
    assert list_en.get("list_button_text") == "See rooms"
