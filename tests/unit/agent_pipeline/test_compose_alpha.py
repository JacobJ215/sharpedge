"""RED stub for compose_alpha CalibrationStore wiring — QUANT-07.

Tests that the compose_alpha node uses CalibrationStore.get_confidence_mult
instead of the hardcoded 1.0 placeholder from Phase 4.

Fails with ImportError until Plan 05-04 implements
packages/models/src/sharpedge_models/calibration_store.py
AND wires it into compose_alpha.py.
"""
import pytest
from unittest.mock import MagicMock, patch

from sharpedge_models.calibration_store import CalibrationStore
from sharpedge_agent_pipeline.nodes.compose_alpha import compose_alpha


def test_compose_alpha_uses_calibration_store():
    """When CalibrationStore.get_confidence_mult is mocked to 0.8,
    compose_alpha node produces a result with confidence_mult = 0.8 (not 1.0).

    This test locks the Phase 5 interface contract: compose_alpha must call
    CalibrationStore.get_confidence_mult() rather than using a hardcoded 1.0.
    """
    mock_store = MagicMock(spec=CalibrationStore)
    mock_store.get_confidence_mult.return_value = 0.8

    with patch(
        "sharpedge_agent_pipeline.nodes.compose_alpha.CalibrationStore",
        return_value=mock_store,
    ):
        state = {
            "ev_result": {"prob_edge_positive": 0.65},
            "regime_result": None,
            "mc_result": None,
            "sport": "NFL",
        }
        result = compose_alpha(state)

    alpha = result.get("alpha")
    assert alpha is not None, "compose_alpha returned None alpha"
    assert hasattr(alpha, "confidence_mult"), (
        "BettingAlpha must expose confidence_mult attribute"
    )
    assert alpha.confidence_mult == 0.8, (
        f"Expected confidence_mult=0.8 from CalibrationStore mock, got {alpha.confidence_mult}"
    )
