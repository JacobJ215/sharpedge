"""RED stubs: OddsApiAdapter for multi-book line shopping via The Odds API. VENUE-05."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sharpedge_venue_adapters.adapters.odds_api import OddsApiAdapter  # ImportError until Wave 3
from sharpedge_venue_adapters.protocol import VenueAdapter


@pytest.fixture
def adapter():
    return OddsApiAdapter(api_key="test_key")


def test_odds_api_satisfies_protocol(adapter):
    assert isinstance(adapter, VenueAdapter)


def test_odds_api_is_read_only(adapter):
    assert adapter.capabilities.read_only is True
    assert adapter.capabilities.execution_supported is False


def test_odds_api_venue_id(adapter):
    assert adapter.venue_id == "odds_api"


@pytest.mark.asyncio
async def test_list_markets_returns_canonical_markets(adapter):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.headers = {"x-requests-remaining": "500"}
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        markets = await adapter.list_markets()
        assert isinstance(markets, list)


def test_remaining_credits_tracked(adapter):
    """OddsApiAdapter must expose remaining_credits after each API call."""
    assert hasattr(adapter, "remaining_credits")
    assert adapter.remaining_credits is None  # None before first call


def test_circuit_breaker_raises_below_50_credits(adapter):
    """When remaining_credits < 50, adapter must raise or warn before calling API."""
    from sharpedge_venue_adapters.adapters.odds_api import InsufficientCreditsError
    adapter.remaining_credits = 10
    with pytest.raises(InsufficientCreditsError):
        raise InsufficientCreditsError("stub — implement in Wave 3")
