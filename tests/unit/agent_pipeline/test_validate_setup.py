"""Tests for AGENT-02: validate_setup LLM evaluator with mocked ChatOpenAI."""
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_agent_pipeline.nodes.validate_setup import validate_setup, SetupEvalResult


def _make_state(verdict: str, retry_count: int = 0) -> dict:
    """Build a minimal state dict for validate_setup."""
    return {
        "ev_result": {
            "ev_percentage": 5.0,
            "edge": 3.0,
            "implied_prob": 47.6,
            "model_prob": 52.0,
            "is_positive_ev": True,
            "prob_edge_positive": 0.72,
        },
        "regime_result": MagicMock(regime=MagicMock(value="SHARP_CONSENSUS"), confidence=0.8),
        "mc_result": MagicMock(ruin_probability=0.03, p50_bankroll=1.12),
        "retry_count": retry_count,
    }


@patch("sharpedge_agent_pipeline.nodes.validate_setup.ChatOpenAI")
def test_pass_verdict_returned(mock_llm_cls):
    """Mock LLM returns PASS → node returns eval_verdict='PASS'."""
    mock_evaluator = MagicMock()
    mock_evaluator.invoke.return_value = SetupEvalResult(
        verdict="PASS", reasoning="All signals aligned.", confidence=0.9
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_evaluator

    state = _make_state("PASS", retry_count=0)
    result = validate_setup(state)

    assert result["eval_verdict"] == "PASS"
    assert "reasoning" in result["eval_reasoning"] or isinstance(result["eval_reasoning"], str)


@patch("sharpedge_agent_pipeline.nodes.validate_setup.ChatOpenAI")
def test_reject_verdict_returned(mock_llm_cls):
    """Mock LLM returns REJECT → node returns eval_verdict='REJECT'."""
    mock_evaluator = MagicMock()
    mock_evaluator.invoke.return_value = SetupEvalResult(
        verdict="REJECT", reasoning="Ruin risk too high.", confidence=0.85
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_evaluator

    state = _make_state("REJECT", retry_count=0)
    result = validate_setup(state)

    assert result["eval_verdict"] == "REJECT"


@patch("sharpedge_agent_pipeline.nodes.validate_setup.ChatOpenAI")
def test_warn_increments_retry_count(mock_llm_cls):
    """WARN verdict increments retry_count by 1."""
    mock_evaluator = MagicMock()
    mock_evaluator.invoke.return_value = SetupEvalResult(
        verdict="WARN", reasoning="Edge is borderline.", confidence=0.6
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_evaluator

    state = _make_state("WARN", retry_count=1)
    result = validate_setup(state)

    assert result["eval_verdict"] == "WARN"
    assert result["retry_count"] == 2


@patch("sharpedge_agent_pipeline.nodes.validate_setup.ChatOpenAI")
def test_pass_does_not_increment_retry_count(mock_llm_cls):
    """PASS verdict does NOT increment retry_count."""
    mock_evaluator = MagicMock()
    mock_evaluator.invoke.return_value = SetupEvalResult(
        verdict="PASS", reasoning="Clean setup.", confidence=0.95
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_evaluator

    state = _make_state("PASS", retry_count=1)
    result = validate_setup(state)

    assert result["retry_count"] == 1


def test_setup_eval_result_model():
    """SetupEvalResult is a valid Pydantic model with verdict, reasoning, confidence."""
    r = SetupEvalResult(verdict="PASS", reasoning="ok", confidence=0.9)
    assert r.verdict == "PASS"
    assert r.reasoning == "ok"
    assert r.confidence == 0.9
