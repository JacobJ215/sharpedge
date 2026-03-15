"""GREEN tests for download_pm_historical script — Phase 9 plan 02.

Tests use mocking to avoid live API calls and verify the implemented
offline/fixture behaviour and DataFrame schema contracts.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd


# ---------------------------------------------------------------------------
# Helper: run async coroutine in sync test context
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Kalshi backfill tests
# ---------------------------------------------------------------------------

def test_backfill_kalshi_resolved_offline_returns_dataframe(tmp_path):
    """Offline mode (no KALSHI_API_KEY) returns 50-row fixture DataFrame."""
    from scripts.download_pm_historical import backfill_kalshi_resolved

    df = _run(backfill_kalshi_resolved(out_dir=tmp_path, offline=True))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50

    expected_cols = {"ticker", "result", "volume", "open_interest", "last_price",
                     "yes_bid", "yes_ask", "close_time", "event_ticker"}
    assert expected_cols.issubset(set(df.columns))


def test_backfill_kalshi_resolved_writes_parquet(tmp_path):
    """Offline mode writes kalshi_resolved.parquet to out_dir."""
    from scripts.download_pm_historical import backfill_kalshi_resolved

    _run(backfill_kalshi_resolved(out_dir=tmp_path, offline=True))
    assert (tmp_path / "kalshi_resolved.parquet").exists()


def test_backfill_kalshi_resolved_auto_offline_no_key(monkeypatch, tmp_path):
    """KALSHI_API_KEY absent → automatically uses fixture data (50 rows)."""
    monkeypatch.delenv("KALSHI_API_KEY", raising=False)
    from scripts.download_pm_historical import backfill_kalshi_resolved

    df = _run(backfill_kalshi_resolved(out_dir=tmp_path))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50


def test_backfill_kalshi_resolved_returns_dataframe():
    """Mock KalshiClient.get_markets → returns non-empty DataFrame."""
    import tempfile
    from scripts.download_pm_historical import backfill_kalshi_resolved

    mock_market = MagicMock()
    mock_market.ticker = "KXBTC-100K"
    mock_market.result = "yes"
    mock_market.volume = 5000.0
    mock_market.open_interest = 200.0
    mock_market.last_price = 0.6
    mock_market.yes_bid = 0.58
    mock_market.yes_ask = 0.62
    mock_market.close_time = "2024-12-01T00:00:00Z"
    mock_market.event_ticker = "KXBTC"
    mock_market.title = "Will BTC reach $100k?"

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        with patch(
            "sharpedge_feeds.kalshi_client.KalshiClient.get_markets",
            new=AsyncMock(return_value=[mock_market]),
        ), patch.dict("os.environ", {"KALSHI_API_KEY": "fake-key"}):
            df = _run(backfill_kalshi_resolved(out_dir=out_dir))

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {"ticker", "result", "volume", "open_interest", "last_price",
                     "yes_bid", "yes_ask", "close_time", "event_ticker"}
    assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# Polymarket backfill tests
# ---------------------------------------------------------------------------

def test_backfill_polymarket_resolved_offline_returns_dataframe(tmp_path):
    """--offline flag → returns synthetic 50-row DataFrame."""
    from scripts.download_pm_historical import backfill_polymarket_resolved

    df = _run(backfill_polymarket_resolved(out_dir=tmp_path, offline=True))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50

    expected_cols = {"condition_id", "question", "volume", "liquidity",
                     "end_date", "category", "resolved_yes"}
    assert expected_cols.issubset(set(df.columns))


def test_backfill_polymarket_resolved_writes_parquet(tmp_path):
    """Offline mode writes polymarket_resolved.parquet to out_dir."""
    from scripts.download_pm_historical import backfill_polymarket_resolved

    _run(backfill_polymarket_resolved(out_dir=tmp_path, offline=True))
    assert (tmp_path / "polymarket_resolved.parquet").exists()


def test_backfill_polymarket_resolved_returns_dataframe():
    """Mock PolymarketClient.get_markets → DataFrame with expected columns."""
    import tempfile
    from scripts.download_pm_historical import backfill_polymarket_resolved

    mock_outcome_yes = MagicMock()
    mock_outcome_yes.outcome = "Yes"
    mock_outcome_yes.winner = True
    mock_outcome_yes.price = 0.9

    mock_outcome_no = MagicMock()
    mock_outcome_no.outcome = "No"
    mock_outcome_no.winner = False
    mock_outcome_no.price = 0.1

    mock_market = MagicMock()
    mock_market.condition_id = "0xabc123"
    mock_market.question = "Will BTC reach $100k?"
    mock_market.volume = 10000.0
    mock_market.liquidity = 500.0
    mock_market.end_date = "2024-12-31"
    mock_market.category = "crypto"
    mock_market.closed = True
    mock_market.outcomes = [mock_outcome_yes, mock_outcome_no]

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        with patch(
            "sharpedge_feeds.polymarket_client.PolymarketClient.get_markets",
            new=AsyncMock(return_value=[mock_market]),
        ):
            df = _run(backfill_polymarket_resolved(out_dir=out_dir))

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {"condition_id", "question", "volume", "liquidity",
                     "end_date", "category", "resolved_yes"}
    assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# Outcome normalization tests
# ---------------------------------------------------------------------------

def test_normalize_polymarket_two_outcomes_yes_winner():
    """2-outcome market with 'Yes' winner → resolved_yes = 1."""
    from scripts.download_pm_historical import _normalize_polymarket_outcome

    yes_outcome = MagicMock(outcome="Yes", winner=True)
    no_outcome = MagicMock(outcome="No", winner=False)
    market = MagicMock(outcomes=[yes_outcome, no_outcome])
    assert _normalize_polymarket_outcome(market) == 1


def test_normalize_polymarket_two_outcomes_no_winner():
    """2-outcome market with 'No' winner → resolved_yes = 0."""
    from scripts.download_pm_historical import _normalize_polymarket_outcome

    yes_outcome = MagicMock(outcome="Yes", winner=False)
    no_outcome = MagicMock(outcome="No", winner=True)
    market = MagicMock(outcomes=[yes_outcome, no_outcome])
    assert _normalize_polymarket_outcome(market) == 0


def test_normalize_polymarket_multi_outcome_non_no_winner():
    """3+ outcomes with non-'No' winner → resolved_yes = 1."""
    from scripts.download_pm_historical import _normalize_polymarket_outcome

    opt_a = MagicMock(outcome="Biden", winner=True)
    opt_b = MagicMock(outcome="Trump", winner=False)
    opt_c = MagicMock(outcome="Other", winner=False)
    market = MagicMock(outcomes=[opt_a, opt_b, opt_c])
    assert _normalize_polymarket_outcome(market) == 1


def test_normalize_polymarket_no_winners_returns_zero():
    """No winners in outcomes → resolved_yes = 0."""
    from scripts.download_pm_historical import _normalize_polymarket_outcome

    opt_a = MagicMock(outcome="Yes", winner=None)
    opt_b = MagicMock(outcome="No", winner=None)
    market = MagicMock(outcomes=[opt_a, opt_b])
    assert _normalize_polymarket_outcome(market) == 0


# ---------------------------------------------------------------------------
# Fixture file content test
# ---------------------------------------------------------------------------

def test_offline_mode_returns_fixture_data(monkeypatch, tmp_path):
    """KALSHI_API_KEY absent → returns fixture DataFrame (50 rows)."""
    monkeypatch.delenv("KALSHI_API_KEY", raising=False)
    from scripts.download_pm_historical import backfill_kalshi_resolved

    df = _run(backfill_kalshi_resolved(out_dir=tmp_path))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50


def test_fixture_covers_all_five_category_prefixes():
    """Fixture JSON has all 5 KXPOL/KXFED/KXBTC/KXENT/KXWTH event_ticker prefixes."""
    import json
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "data/raw/prediction_markets/fixtures/kalshi_sample.json"
    )
    data = json.loads(fixture_path.read_text())
    prefixes = {row["event_ticker"] for row in data}
    assert {"KXPOL", "KXFED", "KXBTC", "KXENT", "KXWTH"}.issubset(prefixes)
