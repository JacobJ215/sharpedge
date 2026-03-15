"""RED stub tests for BLSClient — Phase 9 plan 01.

All fetch tests MUST fail with NotImplementedError (RED state).
"""

import pytest

from sharpedge_feeds.bls_client import BLSClient, BLS_RELEASE_CALENDAR_URL


# ---------------------------------------------------------------------------
# RED tests — raise NotImplementedError until plan 02
# ---------------------------------------------------------------------------

def test_get_days_since_last_release_returns_int():
    """get_days_since_last_release('CPI') → int >= 0."""
    client = BLSClient()
    with pytest.raises(NotImplementedError):
        result = client.get_days_since_last_release("CPI")
        assert isinstance(result, int)
        assert result >= 0


def test_get_is_release_imminent_returns_bool():
    """get_is_release_imminent('CPI', threshold_days=3) → bool."""
    client = BLSClient()
    with pytest.raises(NotImplementedError):
        result = client.get_is_release_imminent("CPI", threshold_days=3)
        assert isinstance(result, bool)


def test_offline_mode_returns_defaults(monkeypatch):
    """BLS_OFFLINE=true → returns (30, False) without network call.

    RED until plan 02 implements the offline branch.
    """
    monkeypatch.setenv("BLS_OFFLINE", "true")
    client = BLSClient()
    with pytest.raises(NotImplementedError):
        days = client.get_days_since_last_release("CPI")
        imminent = client.get_is_release_imminent("CPI", threshold_days=3)
        assert days == 30
        assert imminent is False


# ---------------------------------------------------------------------------
# Importability / constant tests — GREEN
# ---------------------------------------------------------------------------

def test_module_level_calendar_url():
    assert BLS_RELEASE_CALENDAR_URL == "https://www.bls.gov/schedule/news_release/"


def test_client_instantiates():
    client = BLSClient()
    assert client is not None
