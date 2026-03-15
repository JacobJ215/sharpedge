"""GREEN tests for BLSClient — Phase 9 plan 02.

Static cadence logic tested without network calls (BLSClient never makes
live network requests — it uses a static dict for all series).
"""

import pytest

from sharpedge_feeds.bls_client import BLSClient, BLS_RELEASE_CALENDAR_URL, RELEASE_CADENCE_DAYS


# ---------------------------------------------------------------------------
# Offline-mode tests — GREEN
# ---------------------------------------------------------------------------

def test_get_days_since_last_release_offline_returns_30(monkeypatch):
    """BLS_OFFLINE=true → get_days_since_last_release returns 30."""
    monkeypatch.setenv("BLS_OFFLINE", "true")
    client = BLSClient()
    result = client.get_days_since_last_release("CPI")
    assert result == 30


def test_get_is_release_imminent_offline_returns_false(monkeypatch):
    """BLS_OFFLINE=true → get_is_release_imminent returns False."""
    monkeypatch.setenv("BLS_OFFLINE", "true")
    client = BLSClient()
    result = client.get_is_release_imminent("CPI", threshold_days=3)
    assert result is False


def test_offline_mode_returns_defaults(monkeypatch):
    """BLS_OFFLINE=true → both methods return (30, False)."""
    monkeypatch.setenv("BLS_OFFLINE", "true")
    client = BLSClient()
    days = client.get_days_since_last_release("CPI")
    imminent = client.get_is_release_imminent("CPI", threshold_days=3)
    assert days == 30
    assert imminent is False


def test_offline_mode_constructor_flag():
    """offline=True constructor flag → returns (30, False)."""
    client = BLSClient(offline=True)
    assert client.get_days_since_last_release("CPI") == 30
    assert client.get_is_release_imminent("CPI") is False


# ---------------------------------------------------------------------------
# Static cadence logic tests — GREEN (no network, no offline flag)
# ---------------------------------------------------------------------------

def test_get_days_since_last_release_returns_int():
    """get_days_since_last_release('CPI') returns non-negative int."""
    client = BLSClient()
    result = client.get_days_since_last_release("CPI")
    assert isinstance(result, int)
    assert result >= 0


def test_get_days_since_last_release_cpi_bounded():
    """CPI (monthly) result is within [0, 30]."""
    client = BLSClient()
    result = client.get_days_since_last_release("CPI")
    assert 0 <= result <= RELEASE_CADENCE_DAYS["CPI"]


def test_get_days_since_last_release_gdp_bounded():
    """GDP (quarterly) result is within [0, 90]."""
    client = BLSClient()
    result = client.get_days_since_last_release("GDP")
    assert 0 <= result <= RELEASE_CADENCE_DAYS["GDP"]


def test_unknown_series_returns_30():
    """Unknown series returns 30 (safe default)."""
    client = BLSClient()
    result = client.get_days_since_last_release("UNKNOWN_SERIES")
    assert result == 30


def test_get_is_release_imminent_returns_bool():
    """get_is_release_imminent returns a bool."""
    client = BLSClient()
    result = client.get_is_release_imminent("CPI", threshold_days=3)
    assert isinstance(result, bool)


def test_unknown_series_imminent_returns_false():
    """Unknown series → get_is_release_imminent returns False."""
    client = BLSClient()
    result = client.get_is_release_imminent("UNKNOWN_SERIES")
    assert result is False


# ---------------------------------------------------------------------------
# Importability / constant tests — GREEN
# ---------------------------------------------------------------------------

def test_module_level_calendar_url():
    assert BLS_RELEASE_CALENDAR_URL == "https://www.bls.gov/schedule/news_release/"


def test_release_cadence_dict_has_expected_keys():
    assert "CPI" in RELEASE_CADENCE_DAYS
    assert "PPI" in RELEASE_CADENCE_DAYS
    assert "NFP" in RELEASE_CADENCE_DAYS
    assert "GDP" in RELEASE_CADENCE_DAYS


def test_client_instantiates():
    client = BLSClient()
    assert client is not None
