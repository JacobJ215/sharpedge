"""RED stubs for PM edge scanner — covers PM-01 and PM-02.

These tests will fail with ImportError until pm_edge_scanner module is
created in Wave 1. All tests are pure/synchronous (no asyncio needed).
"""

from unittest.mock import MagicMock
from sharpedge_analytics.pm_edge_scanner import scan_pm_edges, PMEdge


def _make_kalshi_market(ticker: str, yes_bid: float, yes_ask: float, volume: int = 10_000):
    """Helper: build a mock KalshiMarket."""
    m = MagicMock()
    m.ticker = ticker
    m.yes_bid = yes_bid
    m.yes_ask = yes_ask
    m.mid_price = (yes_bid + yes_ask) / 2
    m.volume_24h = volume
    m.spread = yes_ask - yes_bid
    m.close_time = None
    m.title = f"Kalshi market {ticker}"
    return m


def _make_poly_market(condition_id: str, yes_price: float, volume: float = 20_000.0):
    """Helper: build a mock PolymarketMarket."""
    m = MagicMock()
    m.condition_id = condition_id
    m.yes_price = yes_price
    m.volume_24h = volume
    m.liquidity = volume * 0.1
    m.question = f"Polymarket market {condition_id}"
    m.end_date = None
    return m


def test_scan_pm_edges_kalshi_returns_edges_above_threshold():
    """scan_pm_edges returns PMEdge list for Kalshi with edge_pct > 0."""
    model_probs = {"KAL-001": 0.80}
    markets = [_make_kalshi_market("KAL-001", yes_bid=0.62, yes_ask=0.64)]

    result = scan_pm_edges(
        kalshi_markets=markets,
        polymarket_markets=[],
        model_probs=model_probs,
    )

    assert isinstance(result, list)
    assert len(result) > 0
    edge = result[0]
    assert isinstance(edge, PMEdge)
    assert edge.edge_pct > 0
    assert edge.platform == "kalshi"


def test_scan_pm_edges_polymarket_returns_edges_above_threshold():
    """scan_pm_edges returns PMEdge list for Polymarket with edge_pct > 0."""
    model_probs = {"POLY-001": 0.75}
    markets = [_make_poly_market("POLY-001", yes_price=0.55)]

    result = scan_pm_edges(
        kalshi_markets=[],
        polymarket_markets=markets,
        model_probs=model_probs,
    )

    assert isinstance(result, list)
    assert len(result) > 0
    edge = result[0]
    assert isinstance(edge, PMEdge)
    assert edge.edge_pct > 0
    assert edge.platform == "polymarket"


def test_volume_floor_filters_low_liquidity():
    """Markets with volume_24h below 500 are excluded from results."""
    model_probs = {"KAL-LOW": 0.80}
    markets = [_make_kalshi_market("KAL-LOW", yes_bid=0.50, yes_ask=0.52, volume=100)]

    result = scan_pm_edges(
        kalshi_markets=markets,
        polymarket_markets=[],
        model_probs=model_probs,
        volume_floor=500,
    )

    assert result == []


def test_pm_edge_has_alpha_score():
    """Returned PMEdge objects have alpha_score (not None) and alpha_badge set."""
    model_probs = {"KAL-002": 0.85}
    markets = [_make_kalshi_market("KAL-002", yes_bid=0.60, yes_ask=0.62)]

    result = scan_pm_edges(
        kalshi_markets=markets,
        polymarket_markets=[],
        model_probs=model_probs,
    )

    assert len(result) > 0
    edge = result[0]
    assert edge.alpha_score is not None
    assert isinstance(edge.alpha_score, float)
    assert edge.alpha_badge is not None
    assert isinstance(edge.alpha_badge, str)
    assert len(edge.alpha_badge) > 0


def test_correlation_warning_order():
    """A correlated PM edge appears after a correlation warning entry in the list."""
    # Create a PM market that shares an entity with one active bet
    # The function should return a list where a correlation warning entry
    # precedes the PM edge entry (used for ordering by value_scanner_job)
    model_probs = {"KAL-CORR": 0.80}
    markets = [_make_kalshi_market("KAL-CORR", yes_bid=0.58, yes_ask=0.60)]

    active_bet = MagicMock()
    active_bet.selection = "Lakers win"
    active_bet.game = "Lakers vs Celtics"
    active_bet.sport = "NBA"
    active_bet.sportsbook = "DraftKings"

    result = scan_pm_edges(
        kalshi_markets=markets,
        polymarket_markets=[],
        model_probs=model_probs,
        active_bets=[active_bet],
        market_titles={"KAL-CORR": "Will the Lakers win the NBA Finals?"},
    )

    # Find index of any correlation warning entry and any PMEdge entry
    warning_indices = [
        i for i, item in enumerate(result)
        if hasattr(item, "warning_type") and item.warning_type == "correlation"
    ]
    edge_indices = [
        i for i, item in enumerate(result)
        if isinstance(item, PMEdge)
    ]

    assert len(warning_indices) > 0, "Expected at least one correlation warning"
    assert len(edge_indices) > 0, "Expected at least one PMEdge"
    assert warning_indices[0] < edge_indices[0], (
        "Correlation warning must precede its correlated PMEdge"
    )
