from app.services.metrics_service import metrics_service


def test_confidence_categorization_boundaries():
    assert metrics_service.categorize_confidence(0.0) == "low"
    assert metrics_service.categorize_confidence(0.44) == "low"
    assert metrics_service.categorize_confidence(0.45) == "medium"
    assert metrics_service.categorize_confidence(0.74) == "medium"
    assert metrics_service.categorize_confidence(0.75) == "high"


def test_record_confidence_increment(monkeypatch):
    calls = {"count": 0}

    class DummyCounter:
        def labels(self, **kwargs):  # noqa: D401
            calls["count"] += 1
            return self

        def inc(self):
            return 1

    dummy = DummyCounter()
    monkeypatch.setattr(metrics_service, "nlp_confidence_category_total", dummy)
    metrics_service.record_nlp_confidence(0.2)
    metrics_service.record_nlp_confidence(0.5)
    metrics_service.record_nlp_confidence(0.9)
    assert calls["count"] == 3


def test_record_fallback_increment(monkeypatch):
    calls = {"count": 0}

    class DummyCounter:
        def labels(self, **kwargs):
            calls["count"] += 1
            return self

        def inc(self):
            return 1

    dummy = DummyCounter()
    monkeypatch.setattr(metrics_service, "nlp_fallback_total", dummy)
    metrics_service.record_nlp_fallback("very_low_confidence")
    metrics_service.record_nlp_fallback("low_confidence_hint")
    assert calls["count"] == 2
