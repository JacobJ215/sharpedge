"""RED stubs: KalshiAdapter wrapping kalshi_client.py. VENUE-03."""
import pytest
from unittest.mock import AsyncMock, patch
from sharpedge_venue_adapters.adapters.kalshi import KalshiAdapter  # ImportError until Wave 2
from sharpedge_venue_adapters.protocol import VenueAdapter, VenueCapability


@pytest.fixture
def adapter():
    return KalshiAdapter(api_key=None)  # offline/test mode


def test_kalshi_adapter_satisfies_protocol(adapter):
    assert isinstance(adapter, VenueAdapter)


def test_kalshi_capabilities_read_only_false(adapter):
    """Kalshi supports execution (unlike sportsbooks)."""
    assert adapter.capabilities.execution_supported is True
    assert adapter.capabilities.read_only is False


def test_kalshi_venue_id(adapter):
    assert adapter.venue_id == "kalshi"


@pytest.mark.asyncio
async def test_list_markets_returns_canonical_markets(adapter):
    with patch.object(adapter, "_client") as mock_client:
        mock_client.get_markets = AsyncMock(return_value=[])
        markets = await adapter.list_markets()
        assert isinstance(markets, list)


@pytest.mark.asyncio
async def test_get_orderbook_returns_canonical_orderbook(adapter):
    with pytest.raises(NotImplementedError):
        raise NotImplementedError("getOrderBook stub — implement in Wave 2")


@pytest.mark.asyncio
async def test_get_settlement_state_maps_result_field(adapter):
    """Kalshi 'result' field: 'yes', 'no', or None -> SettlementState."""
    with pytest.raises(NotImplementedError):
        raise NotImplementedError("get_settlement_state stub — implement in Wave 2")
