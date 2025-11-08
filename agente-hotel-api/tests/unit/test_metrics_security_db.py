from prometheus_client import REGISTRY

from app.services.metrics_service import metrics_service


def _get_metric_value(name: str, label_filter: dict | None = None) -> float:
    for metric in REGISTRY.collect():
        if metric.name == name:
            total = 0.0
            for sample in metric.samples:
                if sample.name != name:
                    continue
                if label_filter:
                    # All labels in filter must match
                    if any(sample.labels.get(k) != v for k, v in label_filter.items()):
                        continue
                total += sample.value
            return total
    return 0.0


def test_password_rotation_counter_increments():
    before_success = _get_metric_value("password_rotations_total", {"result": "success"})
    before_failed = _get_metric_value("password_rotations_total", {"result": "failed"})

    metrics_service.inc_password_rotation("success")
    metrics_service.inc_password_rotation("failed")

    after_success = _get_metric_value("password_rotations_total", {"result": "success"})
    after_failed = _get_metric_value("password_rotations_total", {"result": "failed"})

    assert after_success == before_success + 1, "Debe incrementar rotaciones successful"
    assert after_failed == before_failed + 1, "Debe incrementar rotaciones failed"


def test_set_jwt_sessions_active_sets_value():
    metrics_service.set_jwt_sessions_active(5)
    value = _get_metric_value("jwt_sessions_active")
    assert value == 5
    metrics_service.set_jwt_sessions_active(-3)  # valores negativos se normalizan a 0
    value2 = _get_metric_value("jwt_sessions_active")
    assert value2 == 0


def test_set_db_connections_active_sets_value_and_backcompat():
    metrics_service.set_db_connections_active(7)
    val_primary = _get_metric_value("db_connections_active")
    val_legacy = _get_metric_value("active_connections")
    assert val_primary == 7
    assert val_legacy == 7


def test_statement_timeout_counter_increment():
    before = _get_metric_value("db_statement_timeouts_total")
    metrics_service.inc_statement_timeout()
    after = _get_metric_value("db_statement_timeouts_total")
    assert after == before + 1
