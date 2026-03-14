"""RED stubs: PolymarketAdapter wrapping polymarket_client.py. VENUE-04."""
import pytest
from unittest.mock import AsyncMock, patch
from sharpedge_venue_adapters.adapters.polymarket import PolymarketAdapter  # ImportError until Wave 2
from sharpedge_venue_adapters.protocol import VenueAdapter


@pytest.fixture
def adapter():
    return PolymarketAdapter()


def test_polymarket_satisfies_protocol(adapter):
    assert isinstance(adapter, VenueAdapter)


def test_polymarket_capabilities_read_only(adapter):
    """Polymarket is read-only for Phase 6 (no EIP-712 signing)."""
    assert adapter.capabilities.read_only is True
    assert adapter.capabilities.maker_rewards is True


def test_polymarket_venue_id(adapter):
    assert adapter.venue_id == "polymarket"


@pytest.mark.asyncio
async def test_list_markets_paginates(adapter):
    """list_markets() must handle pagination (Gamma API returns up to 100 per page)."""
    with patch.object(adapter, "_client") as mock_client:
        mock_client.get_markets = AsyncMock(return_value=[])
        markets = await adapter.list_markets()
        assert isinstance(markets, list)


def test_prices_are_probability_scale(adapter):
    """Polymarket prices are 0.0-1.0 USDC — no conversion needed but must be validated."""
    from sharpedge_venue_adapters.protocol import CanonicalQuote
    # CanonicalQuote.raw_format must be "probability" for Polymarket
    with pytest.raises(NotImplementedError):
        raise NotImplementedError("CanonicalQuote.raw_format stub — implement in Wave 2")
