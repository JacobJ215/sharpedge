"""RED TDD stubs for promotion gate report structure — GATE-01.

Tests lock the interface contracts for:
  - generate_promotion_gate: returns a dict matching the gate report JSON schema
  - Gate passes when all criteria are met (brier<0.22, edge>0.02, drawdown<0.20, badge in high/excellent)
  - Gate fails when max_drawdown exceeds threshold (>0.20)

These tests must remain FAILING (RED) until the generate_promotion_gate script is implemented.
Do NOT add pytest.skip() calls.
"""
from __future__ import annotations

import pytest


def _build_gate_report(
    *,
    brier: float = 0.21,
    edge: float = 0.031,
    drawdown: float = 0.14,
    badge: str = "high",
) -> dict:
    """Helper: build a gate report dict matching the expected JSON schema."""
    return {
        "generated_at": "2026-03-15T00:00:00Z",
        "sport": "nba",
        "model_version": "test_v1",
        "gates": {
            "calibration_brier_score": {
                "value": brier,
                "threshold": 0.25,
                "passed": brier < 0.25,
            },
            "min_post_cost_edge": {
                "value": edge,
                "threshold": 0.02,
                "passed": edge > 0.02,
            },
            "max_drawdown": {
                "value": drawdown,
                "threshold": 0.20,
                "passed": drawdown < 0.20,
            },
            "walk_forward_badge": {
                "value": badge,
                "required": ["high", "excellent"],
                "passed": badge in ("high", "excellent"),
            },
            "paper_stability_days": {
                "value": None,
                "threshold": 30,
                "passed": None,
                "note": "Tracked manually",
            },
        },
        "overall_passed": all([
            brier < 0.25,
            edge > 0.02,
            drawdown < 0.20,
            badge in ("high", "excellent"),
        ]),
    }


def test_gate_report_has_required_fields():
    """Promotion gate report JSON must have all 5 gate keys plus top-level metadata.

    RED: raises ImportError until scripts/generate_promotion_gate.py is implemented.
    """
    try:
        from scripts.generate_promotion_gate import generate_promotion_gate  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "GATE-01: scripts/generate_promotion_gate.py does not exist yet. "
            "Wave 4 must implement generate_promotion_gate() returning a report "
            "dict with all 5 gate keys. Original error: " + str(exc)
        ) from exc

    raise NotImplementedError(
        "GATE-01: generate_promotion_gate not yet implemented. "
        "Report must contain: generated_at, sport, model_version, gates, overall_passed."
    )

    # Assertions that must pass post-implementation:
    # report = generate_promotion_gate(sport="nba", model_version="test_v1")
    # assert "generated_at" in report
    # assert "sport" in report
    # assert "model_version" in report
    # assert "gates" in report
    # assert "overall_passed" in report
    # required_gates = {
    #     "calibration_brier_score", "min_post_cost_edge",
    #     "max_drawdown", "walk_forward_badge", "paper_stability_days"
    # }
    # assert required_gates == set(report["gates"].keys()), (
    #     f"Missing gate keys: {required_gates - set(report['gates'].keys())}"
    # )


def test_gate_passes_when_all_criteria_met():
    """overall_passed must be True when brier<0.22, edge>0.02, drawdown<0.20, badge=high.

    RED: raises NotImplementedError until generate_promotion_gate is implemented
    and all gate checks are wired.
    """
    raise NotImplementedError(
        "GATE-01: gate pass logic not yet implemented. "
        "When brier=0.21 (<0.22 threshold), edge=0.031 (>0.02 threshold), "
        "drawdown=0.14 (<0.20 threshold), badge='high' — overall_passed must be True."
    )

    # Assertions that must pass post-implementation:
    # from scripts.generate_promotion_gate import generate_promotion_gate
    # report = generate_promotion_gate(
    #     sport="nba",
    #     model_version="test_v1",
    #     brier_score=0.21,
    #     post_cost_edge=0.031,
    #     max_drawdown=0.14,
    #     walk_forward_badge="high",
    # )
    # assert report["overall_passed"] is True, (
    #     "All gate criteria met — overall_passed should be True"
    # )
    # for gate_name, gate in report["gates"].items():
    #     if gate_name == "paper_stability_days":
    #         continue  # manually tracked
    #     assert gate["passed"] is True, f"Gate '{gate_name}' should have passed"


def test_gate_fails_when_drawdown_exceeds_limit():
    """overall_passed must be False when max_drawdown=0.25 exceeds 0.20 threshold.

    RED: raises NotImplementedError until generate_promotion_gate is implemented.
    """
    raise NotImplementedError(
        "GATE-01: gate fail logic not yet implemented. "
        "When max_drawdown=0.25 (> 0.20 threshold), overall_passed must be False "
        "and max_drawdown gate must show passed=False."
    )

    # Assertions that must pass post-implementation:
    # from scripts.generate_promotion_gate import generate_promotion_gate
    # report = generate_promotion_gate(
    #     sport="nba",
    #     model_version="test_v1",
    #     brier_score=0.21,
    #     post_cost_edge=0.031,
    #     max_drawdown=0.25,  # Exceeds 0.20 threshold
    #     walk_forward_badge="high",
    # )
    # assert report["overall_passed"] is False, (
    #     "max_drawdown=0.25 exceeds threshold 0.20 — overall_passed should be False"
    # )
    # drawdown_gate = report["gates"]["max_drawdown"]
    # assert drawdown_gate["passed"] is False, (
    #     f"max_drawdown gate should be failed, got: {drawdown_gate}"
    # )
