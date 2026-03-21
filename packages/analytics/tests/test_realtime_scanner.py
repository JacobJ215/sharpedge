"""Phase 15 RED test suite for RealtimeArbScanner hardening.

All 8 tests must FAIL (ImportError, AttributeError, or assertion failure) —
no PASSED tests are acceptable in this RED wave.

Requirements covered:
  ARB-01: auto-discovery via discover_and_wire()
  ARB-02: simultaneous dual-platform order placement via shadow_execute_arb()
  ARB-03: staleness guard in _check_pair()
  ARB-04: real NO-token orderbook fetch when polymarket_no_token is None
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

# Production imports — some will raise ImportError in RED phase (intentional)
from sharpedge_analytics.prediction_markets.realtime_scanner import (
    LiveArbOpportunity,
    MarketPair,
    RealtimeArbScanner,
)

# ARB-02: shadow_execute_arb does not exist yet — ImportError is the RED state
try:
    from sharpedge_analytics.prediction_markets.realtime_scanner import (
        shadow_execute_arb,  # noqa: F401
    )

    _SHADOW_EXECUTE_AVAILABLE = True
except ImportError:
    _SHADOW_EXECUTE_AVAILABLE = False

# ARB-04: PolymarketCLOBOrderClient does not exist yet — ImportError is the RED state
try:
    from sharpedge_feeds.polymarket_clob_orders import PolymarketCLOBOrderClient  # noqa: F401

    _CLOB_CLIENT_AVAILABLE = True
except ImportError:
    _CLOB_CLIENT_AVAILABLE = False

from sharpedge_feeds.kalshi_client import KalshiClient, KalshiMarket
from sharpedge_feeds.polymarket_client import (
    PolymarketClient,
    PolymarketMarket,
    PolymarketOutcome,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_scanner(**kwargs) -> RealtimeArbScanner:
    """Create a RealtimeArbScanner with ARB-03 staleness_threshold_s parameter."""
    defaults = dict(staleness_threshold_s=5.0, min_gap_pct=2.0, bankroll=10_000.0)
    defaults.update(kwargs)
    return RealtimeArbScanner(**defaults)


def _make_pair(
    kalshi_ts: float = 0.0,
    poly_ts: float = 0.0,
    kalshi_yes_ask: float = 0.45,
    poly_yes_ask: float = 0.50,
    poly_no_ask: float = 0.0,
    polymarket_no_token: str | None = None,
) -> MarketPair:
    """Create a MarketPair with given timestamps and prices."""
    return MarketPair(
        canonical_id="test_pair",
        description="Test market pair",
        kalshi_ticker="KXTEST-25-X",
        polymarket_yes_token="0xyes_token",
        polymarket_no_token=polymarket_no_token,
        kalshi_yes_ask=kalshi_yes_ask,
        poly_yes_ask=poly_yes_ask,
        poly_no_ask=poly_no_ask,
        last_kalshi_ts=kalshi_ts,
        last_poly_ts=poly_ts,
    )


# ── ARB-03: Staleness Guard ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_staleness_guard_kalshi(caplog):
    """ARB-03: stale Kalshi side (10s old) suppresses arb callback.

    When last_kalshi_ts is 10 seconds old and last_poly_ts is current,
    _check_pair() must log a staleness warning and NOT fire any arb callback.
    """
    scanner = _make_scanner()
    fired = []

    @scanner.on_arb
    async def capture(opp):
        fired.append(opp)

    now = time.time()
    pair = _make_pair(
        kalshi_ts=now - 10.0,  # stale: 10s old
        poly_ts=now,  # fresh
        kalshi_yes_ask=0.45,
        poly_yes_ask=0.50,
    )
    scanner.register_pair(pair)

    import logging

    with caplog.at_level(logging.WARNING):
        await scanner._check_pair(pair)

    assert len(fired) == 0, "Arb callback must NOT fire when Kalshi data is stale"
    assert any("stale" in record.message.lower() for record in caplog.records), (
        "Expected a staleness warning log entry"
    )


@pytest.mark.asyncio
async def test_staleness_guard_poly(caplog):
    """ARB-03: stale Poly side (10s old) suppresses arb callback.

    When last_poly_ts is 10 seconds old and last_kalshi_ts is current,
    _check_pair() must log a staleness warning and NOT fire any arb callback.
    """
    scanner = _make_scanner()
    fired = []

    @scanner.on_arb
    async def capture(opp):
        fired.append(opp)

    now = time.time()
    pair = _make_pair(
        kalshi_ts=now,  # fresh
        poly_ts=now - 10.0,  # stale: 10s old
        kalshi_yes_ask=0.45,
        poly_yes_ask=0.50,
    )
    scanner.register_pair(pair)

    import logging

    with caplog.at_level(logging.WARNING):
        await scanner._check_pair(pair)

    assert len(fired) == 0, "Arb callback must NOT fire when Poly data is stale"
    assert any("stale" in record.message.lower() for record in caplog.records), (
        "Expected a staleness warning log entry"
    )


@pytest.mark.asyncio
async def test_staleness_guard_uninit():
    """ARB-03: timestamps=0.0 (uninitialized pair) must NOT trigger staleness guard.

    Both last_kalshi_ts=0.0 and last_poly_ts=0.0 means the pair has never
    received a tick. The staleness guard must treat this as 'no data yet'
    (handled by the existing price>0 guard) rather than 'infinitely stale'.

    With prices insufficient to trigger a callback (gap < min_gap_pct),
    no callback fires — but the reason must be the price guard, not staleness.
    This test verifies staleness guard does NOT produce a warning on an
    uninitialised pair.
    """
    scanner = _make_scanner()
    import logging

    # Both timestamps 0.0, prices too close to fire arb (gap < 2%)
    pair = _make_pair(
        kalshi_ts=0.0,
        poly_ts=0.0,
        kalshi_yes_ask=0.49,
        poly_yes_ask=0.50,
    )
    scanner.register_pair(pair)


    # Verify the ARB-03 constructor contract
    assert hasattr(scanner, "staleness_threshold_s"), (
        "RealtimeArbScanner must have staleness_threshold_s attribute (ARB-03)"
    )

    # Run _check_pair with uninitialized timestamps — staleness guard must NOT fire
    import io

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.WARNING)
    scanner_logger = logging.getLogger("sharpedge_analytics.prediction_markets.realtime_scanner")
    scanner_logger.addHandler(handler)
    try:
        await scanner._check_pair(pair)
    finally:
        scanner_logger.removeHandler(handler)

    log_output = log_stream.getvalue()
    assert "stale" not in log_output.lower(), (
        f"Staleness guard must NOT fire for uninitialised pair (ts=0.0), got: {log_output}"
    )


# ── ARB-04: NO Token Real Orderbook ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_token_real_ask():
    """ARB-04: when polymarket_no_token is None, scanner fetches real NO ask from CLOB.

    After _check_pair(), pair.poly_no_ask must reflect the real best ask
    returned by get_orderbook (0.47), NOT the derived 1 - yes_ask (0.50).
    """
    scanner = _make_scanner()

    # Mock poly_client injected on scanner
    mock_poly_client = AsyncMock()
    mock_poly_client.get_orderbook = AsyncMock(
        return_value={"asks": [{"price": "0.47", "size": "200"}], "bids": []}
    )

    # ARB-04 requires scanner to have a _poly_client attribute for on-demand fetch
    scanner._poly_client = mock_poly_client  # type: ignore[attr-defined]

    pair = _make_pair(
        kalshi_ts=time.time(),
        poly_ts=time.time(),
        kalshi_yes_ask=0.45,
        poly_yes_ask=0.50,
        poly_no_ask=0.0,
        polymarket_no_token=None,  # triggers on-demand fetch
    )
    scanner.register_pair(pair)

    await scanner._check_pair(pair)

    assert pair.poly_no_ask == pytest.approx(0.47, abs=1e-6), (
        f"Expected poly_no_ask=0.47 from real CLOB orderbook, got {pair.poly_no_ask}"
    )


@pytest.mark.asyncio
async def test_no_token_fallback():
    """ARB-04: when NO token orderbook returns no liquidity, fall back to 1 - yes_ask.

    If get_orderbook returns asks=[], pair.poly_no_ask must remain derived
    as 1 - poly_yes_ask (the existing fallback path).
    """
    scanner = _make_scanner()

    mock_poly_client = AsyncMock()
    mock_poly_client.get_orderbook = AsyncMock(
        return_value={"asks": [], "bids": []}  # no liquidity
    )
    scanner._poly_client = mock_poly_client  # type: ignore[attr-defined]

    pair = _make_pair(
        kalshi_ts=time.time(),
        poly_ts=time.time(),
        kalshi_yes_ask=0.45,
        poly_yes_ask=0.50,
        poly_no_ask=0.0,
        polymarket_no_token=None,
    )
    scanner.register_pair(pair)

    await scanner._check_pair(pair)

    # Fallback: pair.poly_no_ask should still be 0.0 (not updated) or
    # the scanner derives it inline as 1 - yes_ask without persisting.
    # Either way, it must NOT be 0.47 (that would mean bad caching from prior test).
    # We verify get_orderbook was called (ARB-04 attempted) and no ask was persisted.
    mock_poly_client.get_orderbook.assert_called_once()
    assert pair.poly_no_ask == pytest.approx(0.0, abs=1e-6), (
        "poly_no_ask must remain 0.0 (unpersisted) when orderbook has no liquidity"
    )


# ── ARB-01: Auto-Discovery ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_and_wire():
    """ARB-01: discover_and_wire() fetches markets, matches pairs, registers and wires.

    mock kalshi_client.get_markets() returns one KalshiMarket.
    mock poly_client.get_markets() returns one PolymarketMarket with matching
    question and both YES/NO tokens.
    After awaiting scanner.discover_and_wire(...), register_pair must have been
    called once and wire must have been called once.
    """
    scanner = _make_scanner()

    # Patch register_pair and wire on the scanner instance
    scanner.register_pair = MagicMock(wraps=scanner.register_pair)
    scanner.wire = MagicMock(wraps=scanner.wire)

    # Mock KalshiClient
    mock_kalshi = AsyncMock(spec=KalshiClient)
    mock_kalshi_market = MagicMock(spec=KalshiMarket)
    mock_kalshi_market.ticker = "KXTEST-25"
    mock_kalshi_market.title = "Will the Fed cut rates in 2025"
    mock_kalshi_market.subtitle = ""
    mock_kalshi_market.yes_ask = 0.45
    mock_kalshi.get_markets = AsyncMock(return_value=[mock_kalshi_market])

    # Mock PolymarketClient
    mock_poly = AsyncMock(spec=PolymarketClient)
    mock_poly_outcome_yes = MagicMock(spec=PolymarketOutcome)
    mock_poly_outcome_yes.outcome = "Yes"
    mock_poly_outcome_yes.token_id = "0xyes_token_abc"
    mock_poly_outcome_yes.price = 0.50
    mock_poly_outcome_no = MagicMock(spec=PolymarketOutcome)
    mock_poly_outcome_no.outcome = "No"
    mock_poly_outcome_no.token_id = "0xno_token_def"
    mock_poly_outcome_no.price = 0.50
    mock_poly_market = MagicMock(spec=PolymarketMarket)
    mock_poly_market.condition_id = "0xcondition_123"
    mock_poly_market.question = "Will the Fed cut rates in 2025?"
    mock_poly_market.outcomes = [mock_poly_outcome_yes, mock_poly_outcome_no]
    mock_poly.get_markets = AsyncMock(return_value=[mock_poly_market])

    # Mock stream clients
    mock_kalshi_stream = MagicMock()
    mock_kalshi_stream.subscribe = MagicMock()
    mock_kalshi_stream.on_tick = MagicMock()
    mock_poly_stream = MagicMock()
    mock_poly_stream.subscribe = MagicMock()
    mock_poly_stream.on_tick = MagicMock()

    # This will fail with AttributeError if discover_and_wire() doesn't exist (RED)
    await scanner.discover_and_wire(
        mock_kalshi,
        mock_poly,
        mock_kalshi_stream,
        mock_poly_stream,
    )

    assert scanner.register_pair.call_count == 1, (
        f"register_pair must be called exactly once, got {scanner.register_pair.call_count}"
    )
    assert scanner.wire.call_count == 1, (
        f"wire must be called exactly once, got {scanner.wire.call_count}"
    )


@pytest.mark.asyncio
async def test_no_token_extraction():
    """ARB-01: auto-discovery populates MarketPair.polymarket_no_token from NO token outcome.

    The registered MarketPair must have polymarket_no_token set to the NO
    token_id from poly market's outcomes array — not the YES token_id.
    """
    scanner = _make_scanner()

    registered_pairs: list[MarketPair] = []
    original_register = scanner.register_pair

    def capture_register(pair: MarketPair) -> None:
        registered_pairs.append(pair)
        original_register(pair)

    scanner.register_pair = capture_register  # type: ignore[method-assign]

    mock_kalshi = AsyncMock(spec=KalshiClient)
    mock_kalshi_market = MagicMock(spec=KalshiMarket)
    mock_kalshi_market.ticker = "KXTEST-25"
    mock_kalshi_market.title = "Will the Fed cut rates in 2025"
    mock_kalshi_market.subtitle = ""
    mock_kalshi_market.yes_ask = 0.45
    mock_kalshi.get_markets = AsyncMock(return_value=[mock_kalshi_market])

    mock_poly = AsyncMock(spec=PolymarketClient)
    mock_poly_outcome_yes = MagicMock(spec=PolymarketOutcome)
    mock_poly_outcome_yes.outcome = "Yes"
    mock_poly_outcome_yes.token_id = "0xyes_token_abc"
    mock_poly_outcome_yes.price = 0.50
    mock_poly_outcome_no = MagicMock(spec=PolymarketOutcome)
    mock_poly_outcome_no.outcome = "No"
    mock_poly_outcome_no.token_id = "0xno_token_def"
    mock_poly_outcome_no.price = 0.50
    mock_poly_market = MagicMock(spec=PolymarketMarket)
    mock_poly_market.condition_id = "0xcondition_123"
    mock_poly_market.question = "Will the Fed cut rates in 2025?"
    mock_poly_market.outcomes = [mock_poly_outcome_yes, mock_poly_outcome_no]
    mock_poly.get_markets = AsyncMock(return_value=[mock_poly_market])

    mock_kalshi_stream = MagicMock()
    mock_kalshi_stream.subscribe = MagicMock()
    mock_kalshi_stream.on_tick = MagicMock()
    mock_poly_stream = MagicMock()
    mock_poly_stream.subscribe = MagicMock()
    mock_poly_stream.on_tick = MagicMock()

    await scanner.discover_and_wire(
        mock_kalshi,
        mock_poly,
        mock_kalshi_stream,
        mock_poly_stream,
    )

    assert len(registered_pairs) == 1, f"Expected 1 registered pair, got {len(registered_pairs)}"
    pair = registered_pairs[0]
    assert pair.polymarket_no_token == "0xno_token_def", (
        f"Expected polymarket_no_token='0xno_token_def' (the NO token), "
        f"got '{pair.polymarket_no_token}'"
    )
    assert pair.polymarket_yes_token == "0xyes_token_abc", (
        f"Expected polymarket_yes_token='0xyes_token_abc', got '{pair.polymarket_yes_token}'"
    )


# ── ARB-02: Dual Order Placement ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dual_order_placement():
    """ARB-02: shadow_execute_arb() places orders on both platforms concurrently.

    Calling shadow_execute_arb(opp, kalshi_client, poly_clob_client) must:
    - call kalshi_client.create_order (Kalshi leg)
    - call poly_clob_client.place_order (Poly leg)
    - return a dict with both order IDs recorded

    This test will FAIL (ImportError → skip) in RED phase because
    shadow_execute_arb does not yet exist.
    """
    if not _SHADOW_EXECUTE_AVAILABLE:
        pytest.fail(
            "shadow_execute_arb not importable from realtime_scanner "
            "(expected in RED phase — this IS the RED failure)"
        )

    # Build a minimal LiveArbOpportunity
    from datetime import datetime

    from sharpedge_analytics.prediction_markets.realtime_scanner import shadow_execute_arb

    opp = LiveArbOpportunity(
        canonical_id="test_pair",
        description="Test ARB",
        buy_yes_platform="kalshi",
        buy_yes_price=0.45,
        buy_no_platform="polymarket",
        buy_no_price=0.50,
        gross_profit_pct=5.0,
        net_profit_pct=3.5,
        sizing={
            "total_stake": 500.0,
            "guaranteed_profit": 17.5,
            "roi_pct": 3.5,
            "instructions": [
                {
                    "platform": "kalshi",
                    "action": "BUY",
                    "side": "YES",
                    "price": 0.45,
                    "amount": 225.0,
                    "contracts": 500,
                },
                {
                    "platform": "polymarket",
                    "action": "BUY",
                    "side": "NO",
                    "price": 0.50,
                    "amount": 275.0,
                    "contracts": 550,
                },
            ],
        },
        detected_at=datetime.now(),
    )

    mock_kalshi_client = AsyncMock()
    mock_kalshi_client.create_order = AsyncMock(return_value=MagicMock(order_id="KALSHI-ORDER-001"))

    mock_poly_clob_client = AsyncMock()
    mock_poly_clob_client.place_order = AsyncMock(
        return_value={"orderID": "POLY-ORDER-001", "success": True}
    )

    result = await shadow_execute_arb(opp, mock_kalshi_client, mock_poly_clob_client)

    mock_kalshi_client.create_order.assert_called_once()
    mock_poly_clob_client.place_order.assert_called_once()

    assert "order_ids" in result, f"Result must contain 'order_ids' key, got: {result}"
    assert len(result["order_ids"]) == 2, (
        f"Expected 2 order IDs (one per leg), got {len(result['order_ids'])}"
    )
