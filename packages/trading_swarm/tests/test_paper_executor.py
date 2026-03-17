"""Tests for PaperExecutor."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sharpedge_trading.execution.paper_executor import PaperExecutor, _compute_slippage, _idempotency_key
from sharpedge_trading.events.types import ExecutionEvent


def _make_event(**kwargs) -> ExecutionEvent:
    defaults = dict(
        market_id="MKT-001",
        direction="yes",
        size=100.0,
        entry_price=0.45,
        trading_mode="paper",
    )
    defaults.update(kwargs)
    return ExecutionEvent(**defaults)


# --- slippage model ---

def test_compute_slippage_positive():
    slippage = _compute_slippage(size=100.0, entry_price=0.45, market_volume=2000.0)
    assert slippage > 0.0


def test_compute_slippage_increases_with_size():
    small = _compute_slippage(size=10.0, entry_price=0.45, market_volume=2000.0)
    large = _compute_slippage(size=500.0, entry_price=0.45, market_volume=2000.0)
    assert large > small


# --- idempotency key ---

def test_idempotency_key_is_deterministic():
    event = _make_event()
    assert _idempotency_key(event) == _idempotency_key(event)


def test_idempotency_key_differs_by_direction():
    yes = _make_event(direction="yes")
    no = _make_event(direction="no")
    assert _idempotency_key(yes) != _idempotency_key(no)


# --- PaperExecutor ---

@pytest.mark.asyncio
async def test_paper_execute_returns_trade_id():
    executor = PaperExecutor(supabase_url="", supabase_key="")
    event = _make_event()
    with patch.object(executor, "_write_trade", new_callable=AsyncMock):
        trade_id = await executor.execute(event)
    assert trade_id is not None
    assert len(trade_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_paper_execute_idempotent():
    executor = PaperExecutor(supabase_url="", supabase_key="")
    event = _make_event()
    with patch.object(executor, "_write_trade", new_callable=AsyncMock):
        first = await executor.execute(event)
        second = await executor.execute(event)
    assert first is not None
    assert second is None  # duplicate suppressed


@pytest.mark.asyncio
async def test_paper_execute_fill_price_includes_slippage():
    executor = PaperExecutor(supabase_url="", supabase_key="")
    event = _make_event(direction="yes", entry_price=0.45)
    written_trades = []

    async def capture_trade(trade: dict) -> None:
        written_trades.append(trade)

    with patch.object(executor, "_write_trade", side_effect=capture_trade):
        await executor.execute(event)

    assert written_trades
    fill_price = written_trades[0]["entry_price"]
    assert fill_price > 0.45  # YES fill should be above entry (slippage)


@pytest.mark.asyncio
async def test_paper_execute_direction_no_has_lower_fill():
    executor = PaperExecutor(supabase_url="", supabase_key="")
    event = _make_event(direction="no", entry_price=0.55)
    written_trades = []

    async def capture_trade(trade: dict) -> None:
        written_trades.append(trade)

    with patch.object(executor, "_write_trade", side_effect=capture_trade):
        await executor.execute(event)

    fill_price = written_trades[0]["entry_price"]
    assert fill_price < 0.55  # NO fill should be below entry (slippage)
