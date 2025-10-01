#!/usr/bin/env python3
"""Valida que el preflight_report.json cumpla reglas adicionales (opcional).

Checks:
 - Archivo existe
 - decision != NO_GO
 - blocking_issues vacío
 - risk_score no aumenta >10% respecto a snapshot previo (si existe .playbook/preflight_prev.json)
"""

from __future__ import annotations
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / ".playbook" / "preflight_report.json"
PREV = ROOT / ".playbook" / "preflight_prev.json"


def main():
    if not REPORT.exists():
        print("❌ preflight_report.json no encontrado", file=sys.stderr)
        sys.exit(2)
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    decision = data.get("decision")
    if decision == "NO_GO":
        print("❌ Decision NO_GO - bloquear merge")
        sys.exit(3)
    blocking = data.get("blocking_issues", [])
    if blocking:
        print(f"❌ Blocking issues presentes: {blocking}")
        sys.exit(4)
    current_risk = data.get("risk_score", 100)
    if PREV.exists():
        prev = json.loads(PREV.read_text(encoding="utf-8"))
        prev_score = prev.get("risk_score", current_risk)
        if prev_score and current_risk > prev_score * 1.10:
            print(f"⚠ Riesgo incrementó >10% ({prev_score} -> {current_risk})")
    # Guardar snapshot como prev
    PREV.write_text(REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    print("✅ Preflight validación exitosa")


if __name__ == "__main__":
    main()
