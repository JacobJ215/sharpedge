"""RED stubs: cross-venue dislocation detection. DISLO-01."""

from sharpedge_venue_adapters.dislocation import (  # ImportError until Wave 4
    DislocScore,
    compute_consensus,
    score_dislocation,
)
from sharpedge_venue_adapters.protocol import CanonicalQuote


def _make_quote(venue_id, mid, spread=0.04):
    return CanonicalQuote(
        venue_id=venue_id,
        market_id="TEST-001",
        outcome_id="yes",
        raw_bid=mid - spread / 2,
        raw_ask=mid + spread / 2,
        raw_format="probability",
        fair_prob=mid,
        mid_prob=mid,
        spread_prob=spread,
        maker_fee_rate=0.0,
        taker_fee_rate=0.07,
        timestamp_utc="2026-03-14T12:00:00+00:00",
    )


def test_consensus_inverse_spread_weighted():
    """Tighter-spread venue has more weight in consensus."""
    quotes = [
        _make_quote("kalshi", mid=0.60, spread=0.02),  # tight = high weight
        _make_quote("polymarket", mid=0.50, spread=0.10),  # wide = low weight
    ]
    consensus = compute_consensus(quotes)
    # Should be closer to 0.60 (kalshi has tighter spread)
    assert consensus > 0.55


def test_consensus_single_quote():
    quotes = [_make_quote("kalshi", mid=0.55, spread=0.04)]
    consensus = compute_consensus(quotes)
    assert abs(consensus - 0.55) < 0.01


def test_disloc_score_bps_calculation():
    quotes = [
        _make_quote("kalshi", mid=0.60, spread=0.02),
        _make_quote("polymarket", mid=0.50, spread=0.10),
    ]
    scores = score_dislocation(quotes)
    assert len(scores) == 2
    for s in scores:
        assert isinstance(s, DislocScore)
        assert s.disloc_bps >= 0


def test_stale_quote_flagged():
    """Quote with old timestamp must be flagged is_stale=True."""
    old_quote = CanonicalQuote(
        venue_id="odds_api",
        market_id="TEST-001",
        outcome_id="yes",
        raw_bid=0.48,
        raw_ask=0.52,
        raw_format="probability",
        fair_prob=0.50,
        mid_prob=0.50,
        spread_prob=0.04,
        maker_fee_rate=0.0,
        taker_fee_rate=0.0,
        timestamp_utc="2026-01-01T00:00:00+00:00",  # very old
    )
    scores = score_dislocation([old_quote], stale_threshold_seconds=300)
    stale_scores = [s for s in scores if s.is_stale]
    assert len(stale_scores) >= 1
