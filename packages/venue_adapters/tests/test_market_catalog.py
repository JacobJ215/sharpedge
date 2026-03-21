"""RED stubs: MarketCatalog + MarketLifecycleState state machine. VENUE-02."""

import pytest
from sharpedge_venue_adapters.catalog import (  # ImportError until Wave 1
    InvalidTransitionError,
    MarketCatalog,
    MarketLifecycleState,
)


def test_lifecycle_states_exist():
    assert MarketLifecycleState.OPEN
    assert MarketLifecycleState.SUSPENDED
    assert MarketLifecycleState.CLOSED
    assert MarketLifecycleState.SETTLED
    assert MarketLifecycleState.CANCELLED


def test_open_can_transition_to_suspended():
    assert MarketLifecycleState.SUSPENDED in MarketLifecycleState.OPEN.valid_next()


def test_settled_is_terminal():
    assert len(MarketLifecycleState.SETTLED.valid_next()) == 0


def test_cancelled_is_terminal():
    assert len(MarketLifecycleState.CANCELLED.valid_next()) == 0


def test_invalid_transition_raises():
    with pytest.raises(InvalidTransitionError):
        MarketLifecycleState.SETTLED.transition_to(MarketLifecycleState.OPEN)


def test_market_catalog_upsert_and_get(mock_market_dict):
    catalog = MarketCatalog()
    catalog.upsert(mock_market_dict)
    result = catalog.get("kalshi", "KXBTCD-26MAR14")
    assert result is not None
    assert result["state"] == MarketLifecycleState.OPEN


def test_market_catalog_transition_state(mock_market_dict):
    catalog = MarketCatalog()
    catalog.upsert(mock_market_dict)
    catalog.transition("kalshi", "KXBTCD-26MAR14", MarketLifecycleState.CLOSED)
    result = catalog.get("kalshi", "KXBTCD-26MAR14")
    assert result["state"] == MarketLifecycleState.CLOSED
