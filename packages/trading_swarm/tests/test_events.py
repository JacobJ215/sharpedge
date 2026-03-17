import asyncio
import pytest
from sharpedge_trading.events.types import OpportunityEvent, ResearchEvent, PredictionEvent
from sharpedge_trading.events.bus import EventBus


def test_opportunity_event_has_required_fields():
    e = OpportunityEvent(
        market_id="BTCUSD-24",
        category="crypto",
        kalshi_price=0.45,
        liquidity=1200.0,
        time_to_resolution_hours=48.0
    )
    assert e.market_id == "BTCUSD-24"
    assert e.category == "crypto"


@pytest.mark.asyncio
async def test_bus_put_and_get():
    bus = EventBus()
    e = OpportunityEvent(
        market_id="X",
        category="economic",
        kalshi_price=0.3,
        liquidity=500.0,
        time_to_resolution_hours=24.0
    )
    await bus.put_opportunity(e)
    result = await asyncio.wait_for(bus.get_opportunity(), timeout=1.0)
    assert result.market_id == "X"
