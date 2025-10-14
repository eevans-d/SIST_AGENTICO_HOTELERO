#!/usr/bin/env python3
"""
[PROMPT 2.5 + E.3] scripts/parse_rasa_results.py
Rasa NLU Performance Report Parser
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def parse_intent_report(report_path: Path) -> Dict[str, Any]:
    """Parse Rasa intent_report.json and extract key metrics."""

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract overall metrics
    accuracy = data.get("accuracy", 0.0)
    weighted_avg = data.get("weighted avg", {})

    precision = weighted_avg.get("precision", 0.0)
    recall = weighted_avg.get("recall", 0.0)
    f1_score = weighted_avg.get("f1-score", 0.0)
    support = weighted_avg.get("support", 0)

    # Extract per-intent metrics
    intents = {}
    for key, value in data.items():
        if isinstance(value, dict) and "precision" in value:
            intents[key] = {
                "precision": value.get("precision", 0.0),
                "recall": value.get("recall", 0.0),
                "f1_score": value.get("f1-score", 0.0),
                "support": value.get("support", 0),
            }

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "support": support,
        "intents": intents,
    }


def format_report(metrics: Dict[str, Any]) -> str:
    """Format metrics into human-readable report."""

    lines = [
        "=" * 60,
        "RASA NLU PERFORMANCE REPORT",
        "=" * 60,
        "",
        "OVERALL METRICS",
        "-" * 60,
        f"Accuracy:  {metrics['accuracy']:.2%}",
        f"Precision: {metrics['precision']:.2%}",
        f"Recall:    {metrics['recall']:.2%}",
        f"F1-Score:  {metrics['f1_score']:.2%}",
        f"Support:   {metrics['support']} examples",
        "",
        "PER-INTENT PERFORMANCE",
        "-" * 60,
    ]

    # Sort intents by F1-score (descending)
    sorted_intents = sorted(metrics["intents"].items(), key=lambda x: x[1]["f1_score"], reverse=True)

    for intent_name, intent_metrics in sorted_intents:
        lines.append(f"\n{intent_name}:")
        lines.append(f"  Precision: {intent_metrics['precision']:.2%}")
        lines.append(f"  Recall:    {intent_metrics['recall']:.2%}")
        lines.append(f"  F1-Score:  {intent_metrics['f1_score']:.2%}")
        lines.append(f"  Support:   {intent_metrics['support']} examples")

    # Production readiness assessment
    lines.extend(
        [
            "",
            "PRODUCTION READINESS",
            "-" * 60,
        ]
    )

    checks = [
        ("Accuracy ≥ 85%", metrics["accuracy"] >= 0.85),
        ("Precision ≥ 85%", metrics["precision"] >= 0.85),
        ("Recall ≥ 80%", metrics["recall"] >= 0.80),
        ("F1-Score ≥ 82%", metrics["f1_score"] >= 0.82),
    ]

    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        lines.append(f"{status}  {check_name}")

    all_passed = all(passed for _, passed in checks)
    lines.extend(
        [
            "",
            "=" * 60,
            f"VERDICT: {'✅ PRODUCTION READY' if all_passed else '⚠️  NEEDS IMPROVEMENT'}",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def main():
    """Main entry point."""

    if len(sys.argv) < 2:
        print("Usage: python parse_rasa_results.py <intent_report.json>", file=sys.stderr)
        sys.exit(1)

    report_path = Path(sys.argv[1])

    if not report_path.exists():
        print(f"Error: File not found: {report_path}", file=sys.stderr)
        sys.exit(1)

    try:
        metrics = parse_intent_report(report_path)
        report = format_report(metrics)
        print(report)
    except Exception as e:
        print(f"Error parsing report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
