"""RED TDD stubs for compose_alpha with calibrated confidence_mult — INT-01.

Tests lock the integration contracts for:
  - compose_alpha node uses CalibrationStore.get_confidence_mult per sport
  - retrain_scheduler imports from sharpedge_db.client (not sharpedge_feeds)

The scheduler import test turns GREEN after the retrain_scheduler.py import fix.
Do NOT add pytest.skip() calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_compose_alpha_uses_calibrated_confidence_mult():
    """compose_alpha node must use CalibrationStore.get_confidence_mult when building alpha.

    Patches CalibrationStore.get_confidence_mult to return 0.8 and asserts the alpha
    node output reflects a non-default confidence_mult (i.e., != 1.0).

    RED: raises NotImplementedError until compose_alpha is wired to CalibrationStore
    and its output exposes the confidence_mult value used.
    """
    raise NotImplementedError(
        "INT-01: compose_alpha is not yet wired to use CalibrationStore.get_confidence_mult. "
        "Wave 4 must: (1) call store.get_confidence_mult(sport) inside compose_alpha node, "
        "(2) expose confidence_mult in the node output dict so tests can assert on it."
    )

    # Assertions that must pass post-implementation:
    # mock_store = MagicMock()
    # mock_store.get_confidence_mult.return_value = 0.8
    #
    # with patch(
    #     "sharpedge_agent_pipeline.nodes.compose_alpha.CalibrationStore",
    #     return_value=mock_store,
    # ):
    #     # Also reset singleton so patch takes effect
    #     with patch("sharpedge_agent_pipeline.nodes.compose_alpha._CAL_STORE", None):
    #         from sharpedge_agent_pipeline.nodes.compose_alpha import compose_alpha
    #
    #         state = {
    #             "sport": "nba",
    #             "ev_score": 0.6,
    #             "regime": "bull",
    #             "survival_prob": 0.85,
    #         }
    #         result = compose_alpha(state)
    #
    # assert "confidence_mult" in result, (
    #     "compose_alpha output must include 'confidence_mult' key"
    # )
    # assert result["confidence_mult"] != 1.0, (
    #     "confidence_mult should be 0.8 (from mocked CalibrationStore), not default 1.0"
    # )
    # mock_store.get_confidence_mult.assert_called_once_with("nba")


def test_retrain_scheduler_uses_correct_import():
    """retrain_scheduler must import get_supabase_client from sharpedge_db.client.

    This test turns GREEN after the import fix in retrain_scheduler.py (line 36).
    The fix changes: from sharpedge_feeds.supabase_client import get_supabase_client
    to:             from sharpedge_db.client import get_supabase_client
    """
    # Patch the corrected import path so no live DB connection is needed
    with patch("sharpedge_db.client.get_supabase_client", MagicMock()):
        try:
            from sharpedge_webhooks.jobs.retrain_scheduler import start_retrain_scheduler
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "INT-01 (scheduler import fix): retrain_scheduler.py still imports from "
                "the wrong module. Fix line 36: change "
                "'from sharpedge_feeds.supabase_client import get_supabase_client' "
                "to 'from sharpedge_db.client import get_supabase_client'. "
                f"Original error: {exc}"
            ) from exc

    # If import succeeded, the fix is in place — test passes
    assert callable(start_retrain_scheduler), (
        "start_retrain_scheduler must be a callable after import fix"
    )
