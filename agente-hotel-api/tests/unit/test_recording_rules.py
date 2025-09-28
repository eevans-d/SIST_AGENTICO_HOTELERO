import re
from pathlib import Path

CRITICAL_RULES = [
    "pms_cache_hit_ratio",
    "pms_cb_failure_ratio_1m",
    "pms_cb_failure_streak_fraction",
    "pms_cb_minutes_to_open_estimate",
    "pms_cb_risk_imminent",
]

RULES_FILE = Path(__file__).parent.parent.parent / "docker" / "prometheus" / "recording_rules.tmpl.yml"


def test_critical_recording_rules_present():
    text = RULES_FILE.read_text(encoding="utf-8")
    # Simplista: buscar 'record: <name>'
    missing = []
    for rule in CRITICAL_RULES:
        pattern = rf"record:\s+{re.escape(rule)}\b"
        if not re.search(pattern, text):
            missing.append(rule)
    assert not missing, f"Faltan reglas críticas en recording_rules.tmpl.yml: {missing}"
