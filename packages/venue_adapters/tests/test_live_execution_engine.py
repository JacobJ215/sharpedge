"""RED test stubs for Phase 12 live execution (EXEC-03 + EXEC-05).

All 7 tests FAIL until Plan 02 implements:
  - ShadowExecutionEngine accepting kalshi_client + settlement_ledger params
  - process_intent becoming async (uniformly) with live-mode CLOB ordering
  - LiveOrderPoller for fill/cancel polling

Zero import errors, zero syntax errors — only TypeError/AttributeError/AssertionError failures.

NOTE: All process_intent calls use `await` even for shadow mode. Plan 02 makes
process_intent uniformly async so shadow tests can be updated then. The safest
approach for test stability is uniform async.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sharpedge_feeds.kalshi_client import KalshiOrder
from sharpedge_venue_adapters.ledger import LedgerEntry, SettlementLedger
from sharpedge_venue_adapters.execution_engine import (
    OrderIntent,
    ShadowLedgerEntry,
    ShadowExecutionEngine,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_intent():
    """Factory for creating OrderIntent with sensible defaults."""

    def _factory(
        market_id: str = "KXBTC",
        kelly_fraction: float = 0.1,
        bankroll: float = 1000.0,
    ) -> OrderIntent:
        return OrderIntent(
            market_id=market_id,
            predicted_edge=0.05,
            fair_prob=0.60,
            kelly_fraction=kelly_fraction,
            bankroll=bankroll,
            created_at=datetime.now(timezone.utc),
        )

    return _factory


def make_mock_client(status: str = "executed") -> AsyncMock:
    """Return an AsyncMock KalshiClient with create_order and get_order pre-wired."""
    mock_client = AsyncMock()
    _now = datetime.now(timezone.utc)
    _order_resting = KalshiOrder(
        order_id="test-order-123",
        ticker="KXBTC",
        action="buy",
        side="yes",
        type="limit",
        count=5,
        yes_price=55,
        no_price=45,
        status="resting",
        created_time=_now,
    )
    _order_final = KalshiOrder(
        order_id="test-order-123",
        ticker="KXBTC",
        action="buy",
        side="yes",
        type="limit",
        count=5,
        yes_price=55,
        no_price=45,
        status=status,
        created_time=_now,
    )
    mock_client.create_order.return_value = _order_resting
    mock_client.get_order.return_value = _order_final
    return mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_mode_calls_create_order(make_intent):
    """Engine with mock KalshiClient calls create_order() and writes POSITION_OPENED entry."""
    mock_client = make_mock_client(status="resting")
    ledger = SettlementLedger()

    # Plan 02 will extend ShadowExecutionEngine.__init__ to accept these params
    engine = ShadowExecutionEngine(
        max_market_exposure=500.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent()
    result = await engine.process_intent(intent)

    assert mock_client.create_order.called
    entries = ledger.get_position_entries(result.position_lot_id)
    opened = [e for e in entries if e.event_type == "POSITION_OPENED"]
    assert len(opened) == 1
    assert "test-order-123" in opened[0].notes


@pytest.mark.asyncio
async def test_shadow_mode_unchanged(make_intent):
    """Engine constructed without kalshi_client returns ShadowLedgerEntry as before."""
    mock_client = make_mock_client()
    # Shadow mode: no kalshi_client, no settlement_ledger
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=2000.0)
    intent = make_intent()
    # In Plan 02, process_intent will become uniformly async
    result = await engine.process_intent(intent)
    assert isinstance(result, ShadowLedgerEntry)
    # The standalone mock_client passed here was never injected, so never called
    mock_client.create_order.assert_not_called()


@pytest.mark.asyncio
async def test_live_mode_exposure_guard_still_applied(make_intent):
    """When per-market cap would be breached in live mode, create_order is NOT called."""
    mock_client = make_mock_client(status="resting")
    ledger = SettlementLedger()

    # max_market_exposure=50, stake=kelly*bankroll=0.1*1000=$100 > $50 cap
    engine = ShadowExecutionEngine(
        max_market_exposure=50.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent(kelly_fraction=0.1, bankroll=1000.0)
    result = await engine.process_intent(intent)

    assert result is None
    mock_client.create_order.assert_not_called()


@pytest.mark.asyncio
async def test_fill_event_recorded(make_intent):
    """Poller detects status='executed' and writes FILL LedgerEntry to SettlementLedger."""
    mock_client = make_mock_client(status="executed")
    ledger = SettlementLedger()

    engine = ShadowExecutionEngine(
        max_market_exposure=500.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent()
    result = await engine.process_intent(intent)

    entries = ledger.get_position_entries(result.position_lot_id)
    fill_entries = [e for e in entries if e.event_type == "FILL"]
    assert len(fill_entries) == 1
    fill = fill_entries[0]
    # yes_price=55 cents → 0.55 probability
    assert fill.price_at_event == pytest.approx(0.55)
    assert "filled qty=5" in fill.notes


@pytest.mark.asyncio
async def test_cancel_event_recorded(make_intent):
    """Poller detects status='canceled' and writes ADJUSTMENT LedgerEntry (capital returned)."""
    mock_client = make_mock_client(status="canceled")
    ledger = SettlementLedger()

    engine = ShadowExecutionEngine(
        max_market_exposure=500.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent()
    result = await engine.process_intent(intent)

    entries = ledger.get_position_entries(result.position_lot_id)
    adj_entries = [e for e in entries if e.event_type == "ADJUSTMENT"]
    assert len(adj_entries) == 1
    adj = adj_entries[0]
    # Capital returned → positive amount_usdc
    assert adj.amount_usdc > 0
    assert "canceled" in adj.notes


@pytest.mark.asyncio
async def test_fill_on_first_poll(make_intent):
    """If get_order returns 'executed' on first call, exactly one get_order call is made."""
    mock_client = make_mock_client(status="executed")
    ledger = SettlementLedger()

    engine = ShadowExecutionEngine(
        max_market_exposure=500.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent()
    result = await engine.process_intent(intent)

    assert mock_client.get_order.call_count == 1
    entries = ledger.get_position_entries(result.position_lot_id)
    fill_entries = [e for e in entries if e.event_type == "FILL"]
    assert len(fill_entries) == 1


@pytest.mark.asyncio
async def test_full_live_flow(make_intent):
    """Full flow: create_order + get_order='executed' → POSITION_OPENED + FILL in ledger sharing same position_lot_id."""
    mock_client = make_mock_client(status="executed")
    ledger = SettlementLedger()

    engine = ShadowExecutionEngine(
        max_market_exposure=500.0,
        max_day_exposure=2000.0,
        kalshi_client=mock_client,
        settlement_ledger=ledger,
        poll_interval_seconds=0.0,
    )
    intent = make_intent()
    result = await engine.process_intent(intent)

    entries = ledger.get_position_entries(result.position_lot_id)
    event_types = {e.event_type for e in entries}
    assert "POSITION_OPENED" in event_types
    assert "FILL" in event_types

    # All entries share the same position_lot_id
    lot_ids = {e.position_lot_id for e in entries}
    assert len(lot_ids) == 1
    assert lot_ids.pop() == result.position_lot_id
