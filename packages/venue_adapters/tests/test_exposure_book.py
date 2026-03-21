"""RED stubs: ExposureBook + fractional Kelly with drawdown throttle. RISK-01."""

import pytest
from sharpedge_venue_adapters.exposure import (  # ImportError until Wave 5
    AllocationDecision,
    ExposureBook,
    apply_drawdown_throttle,
    compute_allocation,
)


def test_drawdown_throttle_at_zero():
    """No drawdown -> full multiplier (1.0)."""
    assert apply_drawdown_throttle(current_drawdown=0.0) == 1.0


def test_drawdown_throttle_at_threshold():
    """At threshold (0.10) -> still full (1.0)."""
    assert apply_drawdown_throttle(current_drawdown=0.10) == 1.0


def test_drawdown_throttle_at_max():
    """At max drawdown (0.25) -> quarter multiplier (0.25)."""
    assert apply_drawdown_throttle(current_drawdown=0.25) == pytest.approx(0.25, abs=0.01)


def test_drawdown_throttle_clamps_below_quarter():
    """Beyond max drawdown -> still at least 0.25 (floor)."""
    assert apply_drawdown_throttle(current_drawdown=0.50) >= 0.25


def test_exposure_book_initial_empty():
    book = ExposureBook()
    assert book.total_exposure() == 0.0
    assert book.venue_exposure("kalshi") == 0.0


def test_exposure_book_add_position():
    book = ExposureBook()
    book.add_position(venue_id="kalshi", market_id="KXBTCD-26MAR14", stake=100.0)
    assert book.total_exposure() == pytest.approx(100.0)
    assert book.venue_exposure("kalshi") == pytest.approx(100.0)


def test_venue_concentration_cap_enforced():
    """If kalshi already has 30% of bankroll and cap is 0.30, no more kalshi."""
    book = ExposureBook(bankroll=1000.0, venue_concentration_cap=0.30)
    book.add_position(venue_id="kalshi", market_id="M1", stake=300.0)
    decision = compute_allocation(
        book=book,
        venue_id="kalshi",
        market_id="M2",
        edge=0.05,
        fair_prob=0.55,
        current_drawdown=0.0,
    )
    assert decision.recommended_fraction == 0.0  # cap hit


def test_allocation_decision_fields():
    book = ExposureBook(bankroll=1000.0)
    decision = compute_allocation(
        book=book,
        venue_id="kalshi",
        market_id="KXBTCD-26MAR14",
        edge=0.05,
        fair_prob=0.55,
        current_drawdown=0.05,
    )
    assert isinstance(decision, AllocationDecision)
    assert 0.0 <= decision.recommended_fraction <= 1.0
    assert decision.kelly_half > 0
