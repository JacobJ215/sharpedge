"""GREEN tests for CoinGeckoClient — Phase 9 plan 02.

All tests verify the implemented offline behaviour without live network calls.
Live price fetches use monkeypatching to avoid external API dependency in CI.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from sharpedge_feeds.coingecko_client import CoinGeckoClient, COINGECKO_BASE


# ---------------------------------------------------------------------------
# Offline-mode tests — GREEN (no network)
# ---------------------------------------------------------------------------

def test_get_price_offline_returns_zero(monkeypatch):
    """COINGECKO_OFFLINE=true → get_price returns 0.0 without network call."""
    monkeypatch.setenv("COINGECKO_OFFLINE", "true")
    client = CoinGeckoClient()
    result = client.get_price("bitcoin")
    assert isinstance(result, float)
    assert result == 0.0


def test_get_price_change_7d_offline_returns_zero(monkeypatch):
    """COINGECKO_OFFLINE=true → get_price_change_7d returns 0.0 without network call."""
    monkeypatch.setenv("COINGECKO_OFFLINE", "true")
    client = CoinGeckoClient()
    result = client.get_price_change_7d("bitcoin")
    assert isinstance(result, float)
    assert result == 0.0


def test_offline_mode_constructor_flag():
    """offline=True constructor flag → returns 0.0 without network call."""
    client = CoinGeckoClient(offline=True)
    assert client.get_price("bitcoin") == 0.0
    assert client.get_price_change_7d("bitcoin") == 0.0


def test_offline_mode_returns_defaults(monkeypatch):
    """COINGECKO_OFFLINE=true → both methods return 0.0."""
    monkeypatch.setenv("COINGECKO_OFFLINE", "true")
    client = CoinGeckoClient()
    price = client.get_price("bitcoin")
    change = client.get_price_change_7d("bitcoin")
    assert price == 0.0
    assert change == 0.0


# ---------------------------------------------------------------------------
# Mocked live-mode tests — GREEN (mocked httpx)
# ---------------------------------------------------------------------------

def test_get_price_returns_float():
    """get_price('bitcoin') returns float > 0 when API responds."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"bitcoin": {"usd": 95000.0}}
    with patch("httpx.get", return_value=mock_response):
        client = CoinGeckoClient()
        result = client.get_price("bitcoin")
    assert isinstance(result, float)
    assert result > 0


def test_get_price_change_7d_returns_float():
    """get_price_change_7d('bitcoin') returns a float."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"bitcoin": {"usd": 95000.0, "usd_7d_change": 3.5}}
    with patch("httpx.get", return_value=mock_response):
        client = CoinGeckoClient()
        result = client.get_price_change_7d("bitcoin")
    assert isinstance(result, float)


def test_get_price_returns_zero_on_http_error():
    """Network error → returns 0.0, does not raise."""
    import httpx as _httpx
    with patch("httpx.get", side_effect=_httpx.RequestError("timeout")):
        client = CoinGeckoClient()
        result = client.get_price("bitcoin")
    assert result == 0.0


def test_get_price_returns_zero_on_missing_key():
    """Malformed response (missing key) → returns 0.0, does not raise."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    with patch("httpx.get", return_value=mock_response):
        client = CoinGeckoClient()
        result = client.get_price("bitcoin")
    assert result == 0.0


# ---------------------------------------------------------------------------
# Importability / constant tests — GREEN
# ---------------------------------------------------------------------------

def test_module_level_base_url():
    assert COINGECKO_BASE == "https://api.coingecko.com/api/v3"


def test_client_instantiates():
    client = CoinGeckoClient()
    assert client is not None
