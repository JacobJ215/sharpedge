"""Integration tests for compose_alpha with calibrated confidence_mult — INT-01.

Tests verify:
  - compose_alpha (pure function) produces different output with confidence_mult=0.8 vs 1.0
  - retrain_scheduler imports from sharpedge_db.client (not sharpedge_feeds)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_compose_alpha_uses_calibrated_confidence_mult():
    """compose_alpha with confidence_mult=0.8 produces different alpha than mult=1.0."""
    from sharpedge_models.alpha import compose_alpha

    alpha_calibrated = compose_alpha(
        edge_score=0.6,
        regime_scale=1.0,
        survival_prob=0.9,
        confidence_mult=0.8,
    )
    alpha_default = compose_alpha(
        edge_score=0.6,
        regime_scale=1.0,
        survival_prob=0.9,
        confidence_mult=1.0,
    )

    assert alpha_calibrated.alpha != alpha_default.alpha, (
        f"confidence_mult=0.8 should produce different alpha than 1.0; "
        f"got calibrated={alpha_calibrated.alpha}, default={alpha_default.alpha}"
    )
    assert alpha_calibrated.confidence_mult == 0.8
    assert alpha_default.confidence_mult == 1.0


def test_retrain_scheduler_uses_correct_import():
    """retrain_scheduler imports from sharpedge_db.client (import fix confirmed)."""
    with patch("sharpedge_db.client.get_supabase_client", MagicMock()):
        try:
            from sharpedge_webhooks.jobs.retrain_scheduler import start_retrain_scheduler
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "INT-01 (scheduler import fix): retrain_scheduler.py still uses wrong import. "
                f"Original error: {exc}"
            ) from exc

    assert callable(start_retrain_scheduler), (
        "start_retrain_scheduler must be callable after import fix"
    )
