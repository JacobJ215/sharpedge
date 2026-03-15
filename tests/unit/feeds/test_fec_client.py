"""RED stub tests for FECClient — Phase 9 plan 01.

All fetch tests MUST fail with NotImplementedError (RED state).
"""

import pytest

from sharpedge_feeds.fec_client import FECClient


# ---------------------------------------------------------------------------
# RED tests — raise NotImplementedError until plan 02
# ---------------------------------------------------------------------------

def test_get_polling_average_returns_float():
    """get_polling_average('presidential-2024') → float in [0, 1]."""
    client = FECClient()
    with pytest.raises(NotImplementedError):
        result = client.get_polling_average("presidential-2024")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


def test_get_election_proximity_days_returns_int():
    """get_election_proximity_days('2024-11-05') → int >= 0."""
    client = FECClient()
    with pytest.raises(NotImplementedError):
        result = client.get_election_proximity_days("2024-11-05")
        assert isinstance(result, int)
        assert result >= 0


def test_offline_mode_returns_defaults(monkeypatch):
    """FEC_OFFLINE=true → returns (0.0, 365) without network call.

    RED until plan 02 implements the offline branch.
    """
    monkeypatch.setenv("FEC_OFFLINE", "true")
    client = FECClient()
    with pytest.raises(NotImplementedError):
        avg = client.get_polling_average("presidential-2024")
        days = client.get_election_proximity_days("2024-11-05")
        assert avg == 0.0
        assert days == 365


# ---------------------------------------------------------------------------
# Importability tests — GREEN
# ---------------------------------------------------------------------------

def test_client_instantiates():
    client = FECClient()
    assert client is not None
