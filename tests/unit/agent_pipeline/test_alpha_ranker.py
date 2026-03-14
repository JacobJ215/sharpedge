"""Tests for AGENT-05: rank_by_alpha sorts plays by composite alpha score."""
import pytest

from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
def test_rank_by_alpha_descending():
    """rank_by_alpha returns plays sorted highest alpha_score first."""
    plays = [
        {"game": "Game A", "alpha_score": 0.45},
        {"game": "Game B", "alpha_score": 0.72},
        {"game": "Game C", "alpha_score": 0.31},
    ]
    result = rank_by_alpha(plays)
    scores = [p["alpha_score"] for p in result]
    assert scores == sorted(scores, reverse=True), "Plays must be sorted highest alpha first"


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
def test_none_alpha_last():
    """Plays with alpha_score=None sort after plays with positive alpha_score."""
    plays = [
        {"game": "Game A", "alpha_score": None},
        {"game": "Game B", "alpha_score": 0.55},
        {"game": "Game C", "alpha_score": 0.20},
        {"game": "Game D", "alpha_score": None},
    ]
    result = rank_by_alpha(plays)
    # All None-alpha plays must come after scored plays
    has_score = [p for p in result if p["alpha_score"] is not None]
    no_score = [p for p in result if p["alpha_score"] is None]
    assert result[: len(has_score)] == has_score, "Scored plays must precede None-alpha plays"
    assert result[len(has_score) :] == no_score, "None-alpha plays must be at the end"
