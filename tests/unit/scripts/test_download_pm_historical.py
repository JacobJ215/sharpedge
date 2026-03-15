"""Contract stub tests for download_pm_historical script — Phase 9 plan 01.

The script does not exist yet (implemented in plan 02/04).
Tests use pytest.mark.xfail to document the interface contract without
requiring the script to exist. All assertions are RED / xfail stubs.
"""

import pytest


# ---------------------------------------------------------------------------
# xfail RED stubs — document the download_pm_historical contract
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="plan 02/04 implementation pending — script not yet created")
def test_backfill_kalshi_resolved_returns_dataframe():
    """Mock KalshiClient.get_markets → returns non-empty DataFrame.

    Expected columns: [ticker, result, volume, open_interest, last_price,
                        yes_bid, yes_ask, close_time, event_ticker]
    """
    from unittest.mock import MagicMock, patch
    import pandas as pd

    # Import will fail until plan 02 creates the script as a module.
    from scripts.download_pm_historical import backfill_kalshi_resolved  # noqa: F401

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

    with patch("sharpedge_feeds.kalshi_client.KalshiClient.get_markets", return_value=[mock_market]):
        df = backfill_kalshi_resolved()

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {"ticker", "result", "volume", "open_interest", "last_price",
                     "yes_bid", "yes_ask", "close_time", "event_ticker"}
    assert expected_cols.issubset(set(df.columns))


@pytest.mark.xfail(reason="plan 02/04 implementation pending — script not yet created")
def test_backfill_polymarket_resolved_returns_dataframe():
    """Mock PolymarketClient.get_markets → DataFrame with expected columns.

    Expected columns: [condition_id, question, volume, liquidity,
                        end_date, category, resolved_yes]
    """
    from unittest.mock import MagicMock, patch
    import pandas as pd

    from scripts.download_pm_historical import backfill_polymarket_resolved  # noqa: F401

    mock_market = MagicMock()
    mock_market.condition_id = "0xabc123"
    mock_market.question = "Will BTC reach $100k?"
    mock_market.volume = 10000.0
    mock_market.liquidity = 500.0
    mock_market.end_date = "2024-12-31"
    mock_market.category = "crypto"
    mock_market.closed = True

    with patch("sharpedge_feeds.polymarket_client.PolymarketClient.get_markets", return_value=[mock_market]):
        df = backfill_polymarket_resolved()

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {"condition_id", "question", "volume", "liquidity",
                     "end_date", "category", "resolved_yes"}
    assert expected_cols.issubset(set(df.columns))


@pytest.mark.xfail(reason="plan 02/04 implementation pending — script not yet created")
def test_offline_mode_returns_fixture_data(monkeypatch):
    """KALSHI_API_KEY absent → returns fixture DataFrame (50 rows)."""
    import pandas as pd

    monkeypatch.delenv("KALSHI_API_KEY", raising=False)

    from scripts.download_pm_historical import backfill_kalshi_resolved  # noqa: F401

    df = backfill_kalshi_resolved()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
