"""Tests for Monitor Agent."""

from unittest.mock import MagicMock, patch

import pytest
from sharpedge_trading.agents.monitor_agent import (
    _fetch_open_positions,
    monitor_once,
)
from sharpedge_trading.events.bus import EventBus


def _mock_position(
    market_id: str = "MKT-001", size: float = 100.0, entry_price: float = 0.45
) -> dict:
    return {
        "id": "pos-001",
        "market_id": market_id,
        "size": size,
        "entry_price": entry_price,
        "trading_mode": "paper",
        "category": "economic",
    }


# --- _fetch_open_positions ---


def test_fetch_open_positions_returns_empty_on_exception():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception(
        "DB error"
    )
    result = _fetch_open_positions(mock_client)
    assert result == []


def test_fetch_open_positions_returns_data():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        _mock_position()
    ]
    result = _fetch_open_positions(mock_client)
    assert len(result) == 1
    assert result[0]["market_id"] == "MKT-001"


# --- monitor_once ---


@pytest.mark.asyncio
async def test_monitor_once_emits_resolution_on_settlement():
    bus = EventBus()
    mock_kalshi = MagicMock()

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        _mock_position()
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock()
    )

    # Kalshi market is finalized YES
    mock_kalshi.get_market.return_value = {"status": "finalized", "result": "yes"}

    with patch(
        "sharpedge_trading.agents.monitor_agent._get_supabase_client", return_value=mock_client
    ):
        count = await monitor_once(bus, mock_kalshi)

    assert count == 1
    event = await bus.get_resolution()
    assert event.market_id == "MKT-001"
    assert event.actual_outcome is True
    assert event.pnl > 0  # YES outcome with long position
    assert event.position_size == 100.0


@pytest.mark.asyncio
async def test_monitor_once_emits_resolution_with_negative_pnl_on_no_outcome():
    """NO outcome should produce negative P&L = -size * entry_price."""
    bus = EventBus()
    mock_kalshi = MagicMock()
    mock_kalshi.get_market.return_value = {"status": "finalized", "result": "no"}

    mock_client = MagicMock()
    pos = _mock_position(size=100.0, entry_price=0.45)
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        pos
    ]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock()
    )

    with patch(
        "sharpedge_trading.agents.monitor_agent._get_supabase_client", return_value=mock_client
    ):
        count = await monitor_once(bus, mock_kalshi)

    assert count == 1
    event = await bus.get_resolution()
    assert event.actual_outcome is False
    # NO outcome P&L = -size * entry_price = -100 * 0.45 = -45.0
    assert abs(event.pnl - (-45.0)) < 0.01
    assert event.position_size == 100.0  # verify position_size passed through


@pytest.mark.asyncio
async def test_monitor_once_skips_unsettled():
    bus = EventBus()
    mock_kalshi = MagicMock()
    mock_kalshi.get_market.return_value = {"status": "open", "result": ""}

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        _mock_position()
    ]

    with patch(
        "sharpedge_trading.agents.monitor_agent._get_supabase_client", return_value=mock_client
    ):
        count = await monitor_once(bus, mock_kalshi)

    assert count == 0


@pytest.mark.asyncio
async def test_monitor_once_returns_zero_without_supabase():
    bus = EventBus()
    mock_kalshi = MagicMock()
    with patch("sharpedge_trading.agents.monitor_agent._get_supabase_client", return_value=None):
        count = await monitor_once(bus, mock_kalshi)
    assert count == 0
