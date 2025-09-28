#!/usr/bin/env python3
"""Preflight: genera un reporte estructurado (JSON) con risk_score y validaciones.

Inputs:
  - .playbook/project_config.yml
  - Env opcional:
      READINESS_SCORE (0-10)
      MVP_SCORE (0-10)
      SECURITY_GATE (PASS|FAIL)
      CHANGE_COMPLEXITY (low|medium|high)
      BLOCKING_ISSUES (coma separada)

Salida: preflight_report.json
Exit codes:
 0 OK
 2 si SECURITY_GATE=FAIL
 3 si faltan artefactos críticos
"""

from __future__ import annotations
import json
import os
import sys
import enum
import pathlib
from dataclasses import dataclass
from typing import Dict, Any

try:
    import yaml  # type: ignore
except Exception:
    print("❌ Falta dependencia 'pyyaml' (instalar para preflight)", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".playbook" / "project_config.yml"
OUTPUT_PATH = ROOT / ".playbook" / "preflight_report.json"

ARTIFACTS_REQUIRED = [
    "docs/DOD_CHECKLIST.md",
    "CONTRIBUTING.md",
    "docs/playbook/PLAYBOOK_GOBERNANZA_PROPOSITO.md",
    "docs/playbook/WORKING_AGREEMENT.md",
]


class Mode(enum.Enum):
    A = "A"
    B = "B"
    C = "C"


@dataclass
class RiskWeights:
    readiness: float
    mvp: float
    security: float


MODE_WEIGHTS: Dict[Mode, RiskWeights] = {
    Mode.A: RiskWeights(0.6, 0.4, 0.1),
    Mode.B: RiskWeights(0.5, 0.5, 0.2),
    Mode.C: RiskWeights(0.4, 0.4, 0.4),
}

MODE_THRESHOLDS = {
    Mode.A: {"go": 60, "canary": 75},
    Mode.B: {"go": 50, "canary": 65},
    Mode.C: {"go": 40, "canary": 55},
}

CHANGE_PENALTY = {"low": 0, "medium": 5, "high": 12}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config no encontrada: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env_score(name: str, default: float) -> float:
    val = os.getenv(name, str(default)).strip()
    try:
        x = float(val)
        return max(0.0, min(10.0, x))
    except ValueError:
        return default


def main():
    cfg = load_config()
    mode_value = cfg.get("project", {}).get("mode", "B")
    try:
        mode = Mode(mode_value)
    except Exception:
        mode = Mode.B

    readiness_score = env_score("READINESS_SCORE", 7.0)
    mvp_score = env_score("MVP_SCORE", 7.0)
    security_gate_raw = os.getenv("SECURITY_GATE", "PASS").upper()
    security_score = 10.0 if security_gate_raw == "PASS" else 0.0
    complexity = os.getenv("CHANGE_COMPLEXITY", "medium").lower()
    penalty = CHANGE_PENALTY.get(complexity, 5)
    blocking_issues_env = os.getenv("BLOCKING_ISSUES", "").strip()
    blocking_issues = [x.strip() for x in blocking_issues_env.split(",") if x.strip()]

    weights = MODE_WEIGHTS[mode]
    base_component = (
        (readiness_score * weights.readiness) + (mvp_score * weights.mvp) + (security_score * weights.security)
    )
    # Escalar base component (max teórico 10 * sum pesos) a 0-100
    max_possible = 10 * (weights.readiness + weights.mvp + weights.security)
    normalized = (base_component / max_possible) * 100
    risk_score = max(0, 100 - normalized + penalty)
    thresholds = MODE_THRESHOLDS[mode]
    decision = (
        "GO" if risk_score <= thresholds["go"] else ("GO_CANARY" if risk_score <= thresholds["canary"] else "NO_GO")
    )

    artifacts_missing = [a for a in ARTIFACTS_REQUIRED if not (ROOT / a).exists()]

    data: Dict[str, Any] = {
        "mode": mode.value,
        "weights": weights.__dict__,
        "scores": {
            "readiness": readiness_score,
            "mvp": mvp_score,
            "security_gate": security_gate_raw,
        },
        "complexity": complexity,
        "penalty": penalty,
        "risk_score": round(risk_score, 2),
        "thresholds": thresholds,
        "decision": decision,
        "blocking_issues": blocking_issues,
        "artifacts_missing": artifacts_missing,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data, indent=2))

    if security_gate_raw == "FAIL":
        sys.exit(2)
    if artifacts_missing:
        sys.exit(3)
    if decision == "NO_GO":
        sys.exit(4)


if __name__ == "__main__":
    main()
