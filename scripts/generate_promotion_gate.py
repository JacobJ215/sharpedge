#!/usr/bin/env python3
"""Promotion gate report generator for SharpEdge model pipeline.

Reads walk-forward and calibration JSON reports to evaluate 5 named gates:
  1. calibration_brier_score  — brier < BRIER_THRESHOLD
  2. min_post_cost_edge       — overall_roi > MIN_POST_COST_EDGE (proxy)
  3. max_drawdown             — max_drawdown < MAX_DRAWDOWN_THRESHOLD
  4. walk_forward_badge       — badge in QUALITY_BADGE_REQUIRED
  5. paper_stability_days     — tracked manually, always null

Exit codes:
  0 — all automatable gates passed
  2 — one or more automatable gates failed

Usage:
    uv run python scripts/generate_promotion_gate.py --sport nba
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Thresholds (LOCKED)
# ---------------------------------------------------------------------------
MAX_DRAWDOWN_THRESHOLD = 0.20
MIN_POST_COST_EDGE = 0.02
BRIER_THRESHOLD = 0.22
QUALITY_BADGE_REQUIRED = ["high", "excellent"]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
CALIBRATION_REPORTS_DIR = DATA_DIR / "calibration_reports"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def evaluate_gates(wf_report: dict, cal_report: dict) -> dict:
    """Build 5-gate report dict from walk-forward and calibration reports."""
    brier = cal_report.get("brier_score", 1.0)
    overall_roi = wf_report.get("overall_roi", -1.0)
    max_dd = wf_report.get("max_drawdown", 1.0)
    badge = wf_report.get("quality_badge", "low")

    gates = {
        "calibration_brier_score": {
            "value": brier,
            "threshold": BRIER_THRESHOLD,
            "passed": brier < BRIER_THRESHOLD,
        },
        "min_post_cost_edge": {
            "value": overall_roi,
            "threshold": MIN_POST_COST_EDGE,
            "passed": overall_roi > MIN_POST_COST_EDGE,
            "note": "proxy: walk-forward overall_roi used as post-cost edge estimate",
        },
        "max_drawdown": {
            "value": max_dd,
            "threshold": MAX_DRAWDOWN_THRESHOLD,
            "passed": max_dd < MAX_DRAWDOWN_THRESHOLD,
        },
        "walk_forward_badge": {
            "value": badge,
            "required": QUALITY_BADGE_REQUIRED,
            "passed": badge in QUALITY_BADGE_REQUIRED,
        },
        "paper_stability_days": {
            "value": None,
            "threshold": 30,
            "passed": None,
            "note": "Tracked manually",
        },
    }

    # overall_passed: all automatable gates (exclude paper_stability_days)
    automatable = [k for k in gates if k != "paper_stability_days"]
    overall_passed = all(gates[k]["passed"] for k in automatable)

    return {"gates": gates, "overall_passed": overall_passed}


def generate_promotion_gate(sport: str) -> int:
    """Load reports, evaluate gates, write output. Returns exit code."""
    wf_path = DATA_DIR / f"walk_forward_{sport}_report.json"
    cal_path = CALIBRATION_REPORTS_DIR / f"{sport}_calibration.json"

    if not wf_path.exists():
        print(f"ERROR: Walk-forward report not found: {wf_path}", file=sys.stderr)
        return 1
    if not cal_path.exists():
        print(f"ERROR: Calibration report not found: {cal_path}", file=sys.stderr)
        return 1

    with open(wf_path) as f:
        wf_report = json.load(f)
    with open(cal_path) as f:
        cal_report = json.load(f)

    result = evaluate_gates(wf_report, cal_report)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sport": sport,
        "model_version": wf_report.get("generated_at", timestamp),
        "gates": result["gates"],
        "overall_passed": result["overall_passed"],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"promotion_gate_{sport}_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Promotion gate report: {out_path}")
    print(f"overall_passed: {output['overall_passed']}")
    for gate_name, gate in output["gates"].items():
        status = "PASS" if gate["passed"] else ("MANUAL" if gate["passed"] is None else "FAIL")
        print(f"  {gate_name}: {status} (value={gate['value']})")

    return 0 if output["overall_passed"] else 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate promotion gate report for a sport."
    )
    parser.add_argument("--sport", required=True, help="Sport to evaluate (e.g. nba)")
    args = parser.parse_args()
    return generate_promotion_gate(args.sport)


if __name__ == "__main__":
    sys.exit(main())
