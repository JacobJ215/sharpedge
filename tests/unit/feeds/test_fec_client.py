"""GREEN tests for FECClient — Phase 9 plan 02.

Offline mode and proximity math tested without network calls.
Live polling average tests use mocked httpx.
"""

import pytest
from unittest.mock import MagicMock, patch

from sharpedge_feeds.fec_client import FECClient


# ---------------------------------------------------------------------------
# Offline-mode tests — GREEN (no network)
# ---------------------------------------------------------------------------

def test_get_polling_average_offline_returns_zero(monkeypatch):
    """FEC_OFFLINE=true → get_polling_average returns 0.0."""
    monkeypatch.setenv("FEC_OFFLINE", "true")
    client = FECClient()
    result = client.get_polling_average("presidential-2024")
    assert isinstance(result, float)
    assert result == 0.0


def test_get_polling_average_constructor_offline():
    """offline=True constructor flag → returns 0.0."""
    client = FECClient(offline=True)
    result = client.get_polling_average("presidential-2024")
    assert result == 0.0


def test_offline_mode_returns_defaults(monkeypatch):
    """FEC_OFFLINE=true → both methods return safe defaults."""
    monkeypatch.setenv("FEC_OFFLINE", "true")
    client = FECClient()
    avg = client.get_polling_average("presidential-2024")
    days = client.get_election_proximity_days("2024-11-05")
    assert avg == 0.0
    assert isinstance(days, int)
    assert days >= 0


# ---------------------------------------------------------------------------
# Election proximity tests — pure math (no network)
# ---------------------------------------------------------------------------

def test_get_election_proximity_days_returns_int():
    """get_election_proximity_days returns a non-negative int."""
    client = FECClient()
    result = client.get_election_proximity_days("2024-11-05")
    assert isinstance(result, int)
    assert result >= 0


def test_election_proximity_past_date_returns_zero():
    """Past election date → returns 0 (not negative)."""
    client = FECClient()
    result = client.get_election_proximity_days("2020-11-03")
    assert result == 0


def test_election_proximity_future_date_positive():
    """Far future election date → returns positive int."""
    client = FECClient()
    result = client.get_election_proximity_days("2040-01-01")
    assert result > 0


def test_election_proximity_invalid_date_returns_365():
    """Unparseable date string → returns 365 (safe default)."""
    client = FECClient()
    result = client.get_election_proximity_days("not-a-date")
    assert result == 365


# ---------------------------------------------------------------------------
# Mocked live-mode test
# ---------------------------------------------------------------------------

def test_get_polling_average_returns_float():
    """get_polling_average returns float in [0, 1] when API responds."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"candidate_contribution_count": 80},
            {"candidate_contribution_count": 20},
        ]
    }
    with patch("httpx.get", return_value=mock_response):
        client = FECClient()
        result = client.get_polling_average("presidential-2024")
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_get_polling_average_returns_zero_on_error():
    """Network error → returns 0.0, does not raise."""
    import httpx as _httpx
    with patch("httpx.get", side_effect=_httpx.RequestError("timeout")):
        client = FECClient()
        result = client.get_polling_average("presidential-2024")
    assert result == 0.0


# ---------------------------------------------------------------------------
# Importability tests — GREEN
# ---------------------------------------------------------------------------

def test_client_instantiates():
    client = FECClient()
    assert client is not None
