"""RED stubs for PM correlation detector — covers PM-04.

These tests will fail with ImportError until pm_correlation module is
created in Wave 1. All tests are pure/synchronous.
"""

from unittest.mock import MagicMock
from sharpedge_analytics.pm_correlation import (
    compute_entity_correlation,
    detect_correlated_positions,
)


def test_compute_entity_correlation_exact_match():
    """Identical texts have correlation == 1.0."""
    result = compute_entity_correlation(
        "Lakers NBA Finals",
        "Lakers NBA Finals",
    )
    assert result == 1.0


def test_compute_entity_correlation_partial_match():
    """Shared entity 'Celtics' → correlation > 0.5."""
    result = compute_entity_correlation(
        "Lakers vs Celtics",
        "Celtics win title",
    )
    assert result > 0.5


def test_compute_entity_correlation_no_match():
    """Different teams → correlation < 0.1."""
    result = compute_entity_correlation(
        "Lakers vs Celtics",
        "Chiefs vs Ravens",
    )
    assert result < 0.1


def test_detect_correlated_positions_returns_matches():
    """PM market title shares entity with one active bet → returns list with that bet."""
    active_bet = MagicMock()
    active_bet.selection = "Lakers NBA Finals"
    active_bet.game = "Lakers vs Celtics"
    active_bet.sport = "NBA"
    active_bet.sportsbook = "DraftKings"

    result = detect_correlated_positions(
        pm_market_title="Will the Lakers win the NBA Finals?",
        active_bets=[active_bet],
    )

    assert isinstance(result, list)
    assert len(result) > 0
    assert active_bet in result


def test_detect_correlated_positions_empty_when_below_threshold():
    """Correlation below 0.6 → returns empty list."""
    active_bet = MagicMock()
    active_bet.selection = "Chiefs win Super Bowl"
    active_bet.game = "Chiefs vs Ravens"
    active_bet.sport = "NFL"
    active_bet.sportsbook = "FanDuel"

    result = detect_correlated_positions(
        pm_market_title="Will the Lakers win the NBA Finals?",
        active_bets=[active_bet],
        threshold=0.6,
    )

    assert result == []


def test_stopwords_excluded_from_matching():
    """'will' and 'the' are stopwords; must not cause false correlation."""
    result = compute_entity_correlation(
        "Will the Lakers win?",
        "Will the Chiefs win?",
    )
    # Stopwords 'will', 'the', 'win' removed → only team names remain
    # Lakers != Chiefs → low correlation
    assert result < 0.3
