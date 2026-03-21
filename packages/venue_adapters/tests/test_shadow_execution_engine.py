"""Failing test stubs for Phase 11 Shadow Execution Engine (Wave 0 — RED).

All 10 tests must FAIL until Plan 02 implements the engine. Zero syntax errors
and zero ImportErrors — only assertion or NotImplementedError failures.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sharpedge_venue_adapters.execution_engine import (
    DayExposureGuard,
    OrderIntent,
    ShadowExecutionEngine,
    ShadowLedgerEntry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def make_intent():
    """Factory for creating OrderIntent with sensible defaults."""

    def _factory(
        market_id: str = "MKTX",
        kelly_fraction: float = 0.1,
        bankroll: float = 1000.0,
    ) -> OrderIntent:
        return OrderIntent(
            market_id=market_id,
            predicted_edge=0.05,
            fair_prob=0.58,
            kelly_fraction=kelly_fraction,
            bankroll=bankroll,
            created_at=datetime.now(UTC),
        )

    return _factory


# ---------------------------------------------------------------------------
# Test 1 — shadow mode processes intent without calling real Kalshi API
# ---------------------------------------------------------------------------


async def test_shadow_mode_no_kalshi_calls(make_intent, monkeypatch):
    """process_intent returns a ShadowLedgerEntry without ENABLE_KALSHI_EXECUTION set."""
    monkeypatch.delenv("ENABLE_KALSHI_EXECUTION", raising=False)
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=2000.0)
    intent = make_intent(market_id="MKTX", kelly_fraction=0.1, bankroll=1000.0)
    result = await engine.process_intent(intent)
    assert isinstance(result, ShadowLedgerEntry)
    assert result.market_id == intent.market_id


# ---------------------------------------------------------------------------
# Test 2 — engine instantiates when ENABLE_KALSHI_EXECUTION absent
# ---------------------------------------------------------------------------


def test_shadow_mode_detection(monkeypatch):
    """ShadowExecutionEngine instantiates cleanly without ENABLE_KALSHI_EXECUTION."""
    monkeypatch.delenv("ENABLE_KALSHI_EXECUTION", raising=False)
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=2000.0)
    assert engine is not None


# ---------------------------------------------------------------------------
# Test 3 — ShadowLedgerEntry exposes required fields
# ---------------------------------------------------------------------------


def test_ledger_entry_fields():
    """ShadowLedgerEntry attributes are accessible and hold correct values."""
    entry = ShadowLedgerEntry(
        entry_id=1,
        market_id="MKTX",
        predicted_edge=0.07,
        kelly_sized_amount=42.0,
        timestamp=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
    )
    assert entry.market_id == "MKTX"
    assert entry.predicted_edge == pytest.approx(0.07)
    assert entry.kelly_sized_amount == pytest.approx(42.0)
    assert entry.timestamp == datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Test 4 — naive timestamp raises ValueError
# ---------------------------------------------------------------------------


def test_naive_timestamp_rejected():
    """ShadowLedgerEntry raises ValueError when timestamp has no tzinfo."""
    with pytest.raises(ValueError):
        ShadowLedgerEntry(
            entry_id=None,
            market_id="MKTX",
            predicted_edge=0.05,
            kelly_sized_amount=50.0,
            timestamp=datetime(2026, 3, 17, 12, 0, 0),  # no tzinfo
        )


# ---------------------------------------------------------------------------
# Test 5 — per-market limit rejects second intent exceeding cap
# ---------------------------------------------------------------------------


async def test_per_market_limit_rejection(make_intent):
    """Second intent that would breach per-market cap returns None."""
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=2000.0)
    # First intent: kelly_fraction=0.4, bankroll=1000 → stake=$400
    intent_1 = make_intent(market_id="MKTX", kelly_fraction=0.4, bankroll=1000.0)
    await engine.process_intent(intent_1)
    # Second intent: would add another $400 to MKTX → total $800 > $500 cap
    intent_2 = make_intent(market_id="MKTX", kelly_fraction=0.4, bankroll=1000.0)
    result = await engine.process_intent(intent_2)
    assert result is None


# ---------------------------------------------------------------------------
# Test 6 — rejected per-market intent does not add ledger entry
# ---------------------------------------------------------------------------


async def test_per_market_rejection_no_ledger_write(make_intent):
    """After per-market rejection, only the first accepted entry is in the ledger."""
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=2000.0)
    intent_1 = make_intent(market_id="MKTX", kelly_fraction=0.4, bankroll=1000.0)
    await engine.process_intent(intent_1)
    intent_2 = make_intent(market_id="MKTX", kelly_fraction=0.4, bankroll=1000.0)
    await engine.process_intent(intent_2)
    assert len(engine.shadow_ledger.entries) == 1


# ---------------------------------------------------------------------------
# Test 7 — per-day limit rejects intent that exceeds daily cap
# ---------------------------------------------------------------------------


async def test_per_day_limit_rejection(make_intent):
    """Intent that would push total day stake above daily cap returns None."""
    engine = ShadowExecutionEngine(max_market_exposure=2000.0, max_day_exposure=800.0)
    # Three intents: each $300; first two = $600 OK, third = $900 > $800
    intent_a = make_intent(market_id="MKT1", kelly_fraction=0.3, bankroll=1000.0)
    intent_b = make_intent(market_id="MKT2", kelly_fraction=0.3, bankroll=1000.0)
    intent_c = make_intent(market_id="MKT3", kelly_fraction=0.3, bankroll=1000.0)
    await engine.process_intent(intent_a)
    await engine.process_intent(intent_b)
    result = await engine.process_intent(intent_c)
    assert result is None


# ---------------------------------------------------------------------------
# Test 8 — rejected per-day intent does not add ledger entry
# ---------------------------------------------------------------------------


async def test_per_day_rejection_no_ledger_write(make_intent):
    """After per-day rejection, entry count does not increase."""
    engine = ShadowExecutionEngine(max_market_exposure=2000.0, max_day_exposure=800.0)
    intent_a = make_intent(market_id="MKT1", kelly_fraction=0.3, bankroll=1000.0)
    intent_b = make_intent(market_id="MKT2", kelly_fraction=0.3, bankroll=1000.0)
    intent_c = make_intent(market_id="MKT3", kelly_fraction=0.3, bankroll=1000.0)
    await engine.process_intent(intent_a)
    await engine.process_intent(intent_b)
    count_before = len(engine.shadow_ledger.entries)
    await engine.process_intent(intent_c)
    assert len(engine.shadow_ledger.entries) == count_before


# ---------------------------------------------------------------------------
# Test 9 — per-market cap boundary: exactly at cap accepted, $1 over rejected
# ---------------------------------------------------------------------------


async def test_per_market_cap_boundary(make_intent):
    """Intent exactly at the per-market cap is accepted; $1 over is rejected."""
    engine = ShadowExecutionEngine(max_market_exposure=500.0, max_day_exposure=5000.0)
    # Intent committing exactly $500: kelly_fraction=0.5, bankroll=1000
    intent_exact = make_intent(market_id="MKTX", kelly_fraction=0.5, bankroll=1000.0)
    result_exact = await engine.process_intent(intent_exact)
    assert isinstance(result_exact, ShadowLedgerEntry)
    # Intent adding $1 more to the same market
    intent_over = make_intent(market_id="MKTX", kelly_fraction=0.001, bankroll=1000.0)
    result_over = await engine.process_intent(intent_over)
    assert result_over is None


# ---------------------------------------------------------------------------
# Test 10 — DayExposureGuard resets stake at UTC midnight
# ---------------------------------------------------------------------------


def test_day_stake_resets_at_midnight():
    """DayExposureGuard resets cumulative day stake when UTC date changes."""
    guard = DayExposureGuard(max_day_exposure=1000.0)
    guard.commit(900.0)
    # Before midnight: $200 more would breach ($900 + $200 = $1100 > $1000)
    assert guard.would_breach(200.0) is True
    # Advance mock date by one day — guard should detect new UTC day and reset
    future_dt = datetime(2099, 1, 1, 0, 0, 1, tzinfo=UTC)
    with patch(
        "sharpedge_venue_adapters.execution_engine.datetime",
        wraps=datetime,
    ) as mock_dt:
        mock_dt.now.return_value = future_dt
        assert guard.would_breach(200.0) is False
