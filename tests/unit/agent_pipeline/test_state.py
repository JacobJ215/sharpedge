"""Tests for AGENT-01: BettingAnalysisState TypedDict with parallel-safe quality_warnings."""
import operator

import pytest

from sharpedge_agent_pipeline.state import BettingAnalysisState


def test_quality_warnings_accumulate():
    """Annotated[list[str], operator.add] merges two lists from parallel nodes."""
    import typing

    hints = typing.get_type_hints(BettingAnalysisState, include_extras=True)
    qw_type = hints["quality_warnings"]
    # Must be Annotated — get_args returns (list[str], operator.add)
    args = typing.get_args(qw_type)
    assert len(args) == 2, "quality_warnings must be Annotated with a reducer"
    assert args[1] is operator.add, "reducer must be operator.add"


def test_parallel_keys_distinct():
    """regime_result, ev_result, mc_result are separate TypedDict fields."""
    import typing

    hints = typing.get_type_hints(BettingAnalysisState, include_extras=True)
    assert "regime_result" in hints
    assert "ev_result" in hints
    assert "mc_result" in hints
    # All three must be distinct keys
    assert len({"regime_result", "ev_result", "mc_result"} & hints.keys()) == 3


def test_state_has_all_required_keys():
    """BettingAnalysisState has all 14 typed keys."""
    import typing

    hints = typing.get_type_hints(BettingAnalysisState, include_extras=True)
    required_keys = {
        "game_query", "sport", "user_id",
        "game_context", "regime_inputs",
        "regime_result", "ev_result", "mc_result",
        "eval_verdict", "eval_reasoning", "retry_count",
        "alpha", "kelly_fraction",
        "quality_warnings",
        "report", "error",
    }
    missing = required_keys - hints.keys()
    assert not missing, f"Missing keys: {missing}"
