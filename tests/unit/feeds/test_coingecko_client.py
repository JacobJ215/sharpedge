"""RED stub tests for CoinGeckoClient — Phase 9 plan 01.

All fetch tests MUST fail with NotImplementedError (RED state).
Offline-mode tests verify the flag is detected (GREEN after plan 02 adds offline path).
"""

import os
import pytest

from sharpedge_feeds.coingecko_client import CoinGeckoClient, COINGECKO_BASE


# ---------------------------------------------------------------------------
# RED tests — raise NotImplementedError until plan 02
# ---------------------------------------------------------------------------

def test_get_price_returns_float():
    """get_price('bitcoin') should return float in (0, inf)."""
    client = CoinGeckoClient()
    with pytest.raises(NotImplementedError):
        result = client.get_price("bitcoin")
        # Plan 02 contract: result is float > 0
        assert isinstance(result, float)
        assert result > 0


def test_get_price_change_7d_returns_float():
    """get_price_change_7d('bitcoin') should return a float."""
    client = CoinGeckoClient()
    with pytest.raises(NotImplementedError):
        result = client.get_price_change_7d("bitcoin")
        assert isinstance(result, float)


def test_offline_mode_returns_defaults(monkeypatch):
    """COINGECKO_OFFLINE=true → returns (0.0, 0.0) without network call.

    This test is RED until plan 02 implements the offline branch.
    """
    monkeypatch.setenv("COINGECKO_OFFLINE", "true")
    client = CoinGeckoClient()
    # Offline branch not implemented yet — will raise NotImplementedError.
    with pytest.raises(NotImplementedError):
        price = client.get_price("bitcoin")
        change = client.get_price_change_7d("bitcoin")
        # Plan 02 contract: offline returns defaults, not raises.
        assert price == 0.0
        assert change == 0.0


# ---------------------------------------------------------------------------
# Importability / constant tests — GREEN
# ---------------------------------------------------------------------------

def test_module_level_base_url():
    assert COINGECKO_BASE == "https://api.coingecko.com/api/v3"


def test_client_instantiates():
    client = CoinGeckoClient()
    assert client is not None
