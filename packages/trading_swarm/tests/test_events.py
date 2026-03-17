"""Tests for event types and async bus."""
import asyncio
from datetime import timedelta

import pytest

from sharpedge_trading.events.types import (
    ApprovedEvent,
    ExecutionEvent,
    OpportunityEvent,
    PredictionEvent,
    ResearchEvent,
    ResolutionEvent,
    SignalScore,
)
from sharpedge_trading.events.bus import EventBus


def _make_opportunity() -> OpportunityEvent:
    return OpportunityEvent(
        market_id="MKT-001",
        ticker="TICKER-001",
        category="economic",
        current_price=0.45,
        liquidity=1000.0,
        time_to_resolution=timedelta(hours=24),
        price_momentum=0.05,
        spread_ratio=1.2,
    )


def test_opportunity_event_has_required_fields():
    opp = _make_opportunity()
    assert opp.market_id == "MKT-001"
    assert opp.ticker == "TICKER-001"
    assert opp.category == "economic"
    assert opp.current_price == 0.45
    assert opp.liquidity == 1000.0
    assert opp.time_to_resolution == timedelta(hours=24)
    assert opp.price_momentum == 0.05
    assert opp.spread_ratio == 1.2
    assert opp.created_at is not None


def test_signal_score_has_age_seconds():
    sig = SignalScore(source="reddit", sentiment=0.6, confidence=0.8, age_seconds=300.0)
    assert sig.age_seconds == 300.0


def test_research_event_embeds_opportunity():
    opp = _make_opportunity()
    sig = SignalScore(source="reddit", sentiment=0.6, confidence=0.8, age_seconds=300.0)
    evt = ResearchEvent(
        market_id="MKT-001",
        opportunity=opp,
        narrative="Bullish signals",
        signal_scores=[sig],
    )
    assert evt.opportunity is opp
    assert evt.narrative == "Bullish signals"
    assert evt.signal_scores[0].age_seconds == 300.0


def test_prediction_event_embeds_research():
    opp = _make_opportunity()
    sig = SignalScore(source="rss", sentiment=0.5, confidence=0.7, age_seconds=60.0)
    research = ResearchEvent(market_id="MKT-001", opportunity=opp, narrative="neutral", signal_scores=[sig])
    pred = PredictionEvent(
        market_id="MKT-001",
        research=research,
        base_probability=0.55,
        calibrated_probability=0.58,
        edge=0.05,
        confidence_score=0.7,
    )
    assert pred.base_probability == 0.55
    assert pred.calibrated_probability == 0.58
    assert pred.research is research


def test_approved_event_has_market_id_and_created_at():
    opp = _make_opportunity()
    sig = SignalScore(source="rss", sentiment=0.5, confidence=0.7, age_seconds=60.0)
    research = ResearchEvent(market_id="MKT-001", opportunity=opp, narrative="n", signal_scores=[sig])
    pred = PredictionEvent(
        market_id="MKT-001", research=research,
        base_probability=0.55, calibrated_probability=0.58,
        edge=0.05, confidence_score=0.7,
    )
    approved = ApprovedEvent(market_id="MKT-001", prediction=pred)
    assert approved.market_id == "MKT-001"
    assert approved.created_at is not None


def test_execution_event_has_size_and_created_at():
    evt = ExecutionEvent(
        market_id="MKT-001", direction="yes", size=50.0,
        entry_price=0.45, trading_mode="paper",
    )
    assert evt.size == 50.0
    assert evt.created_at is not None


def test_resolution_event_has_actual_outcome_and_resolved_at():
    evt = ResolutionEvent(
        trade_id="trade-001", market_id="MKT-001",
        actual_outcome=True, pnl=25.0, trading_mode="paper",
    )
    assert evt.actual_outcome is True
    assert evt.resolved_at is not None


@pytest.mark.asyncio
async def test_bus_put_and_get():
    bus = EventBus()
    opp = _make_opportunity()
    await bus.put_opportunity(opp)
    result = await bus.get_opportunity()
    assert result.market_id == "MKT-001"
    assert result.ticker == "TICKER-001"


@pytest.mark.asyncio
async def test_bus_research_channel():
    bus = EventBus()
    opp = _make_opportunity()
    sig = SignalScore(source="rss", sentiment=0.5, confidence=0.7, age_seconds=60.0)
    evt = ResearchEvent(market_id="MKT-001", opportunity=opp, narrative="test", signal_scores=[sig])
    await bus.put_research(evt)
    result = await bus.get_research()
    assert result.market_id == "MKT-001"


@pytest.mark.asyncio
async def test_bus_prediction_channel():
    bus = EventBus()
    opp = _make_opportunity()
    sig = SignalScore(source="rss", sentiment=0.5, confidence=0.7, age_seconds=60.0)
    research = ResearchEvent(market_id="MKT-001", opportunity=opp, narrative="n", signal_scores=[sig])
    evt = PredictionEvent(
        market_id="MKT-001", research=research,
        base_probability=0.55, calibrated_probability=0.58,
        edge=0.05, confidence_score=0.7,
    )
    await bus.put_prediction(evt)
    result = await bus.get_prediction()
    assert result.market_id == "MKT-001"


@pytest.mark.asyncio
async def test_bus_approved_channel():
    bus = EventBus()
    opp = _make_opportunity()
    sig = SignalScore(source="rss", sentiment=0.5, confidence=0.7, age_seconds=60.0)
    research = ResearchEvent(market_id="MKT-001", opportunity=opp, narrative="n", signal_scores=[sig])
    pred = PredictionEvent(
        market_id="MKT-001", research=research,
        base_probability=0.55, calibrated_probability=0.58,
        edge=0.05, confidence_score=0.7,
    )
    evt = ApprovedEvent(market_id="MKT-001", prediction=pred)
    await bus.put_approved(evt)
    result = await bus.get_approved()
    assert result.market_id == "MKT-001"


@pytest.mark.asyncio
async def test_bus_execution_channel():
    bus = EventBus()
    evt = ExecutionEvent(
        market_id="MKT-001", direction="yes", size=50.0,
        entry_price=0.45, trading_mode="paper",
    )
    await bus.put_execution(evt)
    result = await bus.get_execution()
    assert result.market_id == "MKT-001"


@pytest.mark.asyncio
async def test_bus_resolution_channel():
    bus = EventBus()
    evt = ResolutionEvent(
        trade_id="trade-001", market_id="MKT-001",
        actual_outcome=True, pnl=25.0, trading_mode="paper",
    )
    await bus.put_resolution(evt)
    result = await bus.get_resolution()
    assert result.trade_id == "trade-001"
