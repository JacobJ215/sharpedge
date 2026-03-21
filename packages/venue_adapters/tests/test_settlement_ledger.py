"""RED stubs: append-only LedgerEntry + deterministic replay. SETTLE-01."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from sharpedge_venue_adapters.ledger import (  # ImportError until Wave 5
    LedgerEntry,
    replay_position_pnl,
)


def _make_entry(event_type: str, amount: float, position_lot_id: str = "LOT-001") -> LedgerEntry:
    return LedgerEntry(
        entry_id=None,
        event_type=event_type,
        venue_id="kalshi",
        market_id="KXBTCD-26MAR14",
        position_lot_id=position_lot_id,
        amount_usdc=amount,
        fee_component=0.0,
        rebate_component=0.0,
        price_at_event=0.52,
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )


def test_ledger_entry_is_frozen():
    entry = _make_entry("FILL", -100.0)
    with pytest.raises(FrozenInstanceError):
        entry.amount_usdc = 0.0  # frozen dataclass


def test_ledger_entry_event_types():
    for et in [
        "FILL",
        "FEE",
        "REBATE",
        "SETTLEMENT",
        "ADJUSTMENT",
        "POSITION_OPENED",
        "POSITION_CLOSED",
    ]:
        e = _make_entry(et, 0.0)
        assert e.event_type == et


def test_replay_position_pnl_single_fill_and_settlement():
    """FILL -100 + SETTLEMENT +200 -> PnL = +100."""
    entries = [
        _make_entry("FILL", -100.0),
        _make_entry("SETTLEMENT", 200.0),
    ]
    pnl = replay_position_pnl(entries, position_lot_id="LOT-001")
    assert pnl == pytest.approx(100.0)


def test_replay_pnl_with_fee_deduction():
    """FILL -100 + FEE -7 + SETTLEMENT +200 -> PnL = +93."""
    entries = [
        _make_entry("FILL", -100.0),
        _make_entry("FEE", -7.0),
        _make_entry("SETTLEMENT", 200.0),
    ]
    pnl = replay_position_pnl(entries, position_lot_id="LOT-001")
    assert pnl == pytest.approx(93.0)


def test_replay_is_deterministic():
    """Replaying the same entries always produces the same PnL."""
    entries = [
        _make_entry("FILL", -50.0),
        _make_entry("FEE", -3.50),
        _make_entry("SETTLEMENT", 100.0),
    ]
    result1 = replay_position_pnl(entries, position_lot_id="LOT-001")
    result2 = replay_position_pnl(entries, position_lot_id="LOT-001")
    assert result1 == result2


def test_ledger_timestamps_must_be_utc_aware():
    """Naive datetime in occurred_at must raise ValueError."""
    import datetime as dt

    with pytest.raises(ValueError):
        LedgerEntry(
            entry_id=None,
            event_type="FILL",
            venue_id="kalshi",
            market_id="TEST",
            position_lot_id="LOT-001",
            amount_usdc=-100.0,
            fee_component=0.0,
            rebate_component=0.0,
            price_at_event=0.52,
            occurred_at=dt.datetime(2026, 3, 14, 12, 0, 0),  # naive — no timezone
            recorded_at=datetime.now(dt.UTC),
        )
