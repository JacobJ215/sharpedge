"""Tests for promotion gate report structure — GATE-01.

Tests verify:
  - evaluate_gates: builds a dict with all 5 gate keys
  - Gate passes when all automatable criteria are met
  - Gate fails when max_drawdown exceeds threshold
"""
from __future__ import annotations

import importlib.util
import pathlib


def _load_generate_promotion_gate():
    root = pathlib.Path(__file__).parent.parent.parent.parent
    script_path = root / "scripts" / "generate_promotion_gate.py"
    spec = importlib.util.spec_from_file_location("generate_promotion_gate", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_wf_report(overall_roi=0.031, max_drawdown=0.14, badge="high"):
    return {
        "sport": "nba",
        "quality_badge": badge,
        "overall_roi": overall_roi,
        "max_drawdown": max_drawdown,
    }


def _make_cal_report(brier=0.21):
    return {
        "sport": "nba",
        "brier_score": brier,
        "confidence_mult": 0.95,
    }


def test_gate_report_has_required_fields():
    """evaluate_gates returns a dict with all 5 required gate keys."""
    mod = _load_generate_promotion_gate()
    result = mod.evaluate_gates(_make_wf_report(), _make_cal_report())

    assert "gates" in result, "Result must have 'gates' key"
    assert "overall_passed" in result, "Result must have 'overall_passed' key"

    required_gates = {
        "calibration_brier_score",
        "min_post_cost_edge",
        "max_drawdown",
        "walk_forward_badge",
        "paper_stability_days",
    }
    assert required_gates == set(result["gates"].keys()), (
        f"Missing gate keys: {required_gates - set(result['gates'].keys())}"
    )


def test_gate_passes_when_all_criteria_met():
    """overall_passed is True when brier<0.22, edge>0.02, drawdown<0.20, badge=high."""
    mod = _load_generate_promotion_gate()
    result = mod.evaluate_gates(
        _make_wf_report(overall_roi=0.031, max_drawdown=0.14, badge="high"),
        _make_cal_report(brier=0.21),
    )

    assert result["overall_passed"] is True, (
        f"All criteria met — expected overall_passed=True, got gates={result['gates']}"
    )
    for gate_name, gate in result["gates"].items():
        if gate_name == "paper_stability_days":
            assert gate["passed"] is None, "paper_stability_days must have passed=None"
            continue
        assert gate["passed"] is True, f"Gate '{gate_name}' should have passed"


def test_gate_fails_when_drawdown_exceeds_limit():
    """overall_passed is False when max_drawdown=0.25 exceeds 0.20 threshold."""
    mod = _load_generate_promotion_gate()
    result = mod.evaluate_gates(
        _make_wf_report(max_drawdown=0.25),
        _make_cal_report(brier=0.21),
    )

    assert result["overall_passed"] is False, (
        "max_drawdown=0.25 exceeds threshold 0.20 — expected overall_passed=False"
    )
    drawdown_gate = result["gates"]["max_drawdown"]
    assert drawdown_gate["passed"] is False, (
        f"max_drawdown gate should be failed, got: {drawdown_gate}"
    )
