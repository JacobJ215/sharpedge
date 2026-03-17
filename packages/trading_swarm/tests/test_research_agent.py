"""Tests for Research Agent."""
import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest

from sharpedge_trading.agents.research_agent import (
    _apply_freshness,
    _build_narrative,
    _fetch_all_signals,
    _raw_to_score,
    research_one,
)
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import OpportunityEvent
from sharpedge_trading.signals.types import RawSignal


def _make_opportunity(**overrides) -> OpportunityEvent:
    base = dict(
        market_id="MKT-001",
        ticker="TICKER-001",
        category="economic",
        current_price=0.45,
        liquidity=1000.0,
        time_to_resolution=timedelta(hours=24),
        price_momentum=0.20,
        spread_ratio=2.5,
    )
    base.update(overrides)
    return OpportunityEvent(**base)


def _make_raw(age_seconds: float = 60.0, source: str = "rss_ap") -> RawSignal:
    return RawSignal(source=source, text="Test headline", age_seconds=age_seconds, confidence=0.9)


# --- _apply_freshness ---

def test_freshness_keeps_recent_signal():
    sig = _make_raw(age_seconds=60.0)
    result = _apply_freshness(sig, max_age_seconds=3600)
    assert result is not None
    assert result.confidence == 0.9  # no penalty


def test_freshness_discards_stale_signal():
    sig = _make_raw(age_seconds=7200.0)
    result = _apply_freshness(sig, max_age_seconds=3600)
    assert result is None


def test_freshness_applies_confidence_penalty_for_old_signal():
    # age > 1 hour but within max_age
    sig = _make_raw(age_seconds=5000.0)
    result = _apply_freshness(sig, max_age_seconds=10000)
    assert result is not None
    assert result.confidence == pytest.approx(0.9 * 0.5)


def test_freshness_no_penalty_for_signal_under_1_hour():
    sig = _make_raw(age_seconds=1800.0)  # 30 min
    result = _apply_freshness(sig, max_age_seconds=10000)
    assert result is not None
    assert result.confidence == 0.9


# --- _raw_to_score ---

def test_raw_to_score_neutral_sentiment():
    sig = _make_raw(age_seconds=60.0)
    score = _raw_to_score(sig)
    assert score.sentiment == 0.5
    assert score.confidence == 0.9
    assert score.age_seconds == 60.0
    assert score.source == "rss_ap"


# --- _build_narrative ---

def test_build_narrative_formats_signals():
    signals = [
        RawSignal(source="rss_ap", text="Markets rise", age_seconds=60, confidence=0.9),
        RawSignal(source="reddit", text="Bullish sentiment", age_seconds=120, confidence=0.6),
    ]
    narrative = _build_narrative(signals)
    assert "[rss_ap] Markets rise" in narrative
    assert "[reddit] Bullish sentiment" in narrative


def test_build_narrative_empty_returns_no_signals():
    narrative = _build_narrative([])
    assert "No signals" in narrative


def test_build_narrative_caps_at_20_items():
    signals = [RawSignal(source="rss_ap", text=f"Item {i}", age_seconds=60, confidence=0.9) for i in range(30)]
    narrative = _build_narrative(signals)
    assert "Item 20" not in narrative
    assert "Item 19" in narrative


# --- _fetch_all_signals ---

@pytest.mark.asyncio
async def test_fetch_all_signals_combines_sources():
    rss_signal = RawSignal(source="rss_ap", text="RSS headline", age_seconds=60, confidence=0.9)
    reddit_signal = RawSignal(source="reddit", text="Reddit post", age_seconds=120, confidence=0.6)

    with patch("sharpedge_trading.agents.research_agent.fetch_rss_signals", return_value=[rss_signal]):
        with patch("sharpedge_trading.agents.research_agent.fetch_reddit_signals", return_value=[reddit_signal]):
            with patch("sharpedge_trading.agents.research_agent.fetch_twitter_signals", return_value=[]):
                signals = await _fetch_all_signals("CPI")

    assert len(signals) == 2
    sources = {s.source for s in signals}
    assert "rss_ap" in sources
    assert "reddit" in sources


@pytest.mark.asyncio
async def test_fetch_all_signals_handles_source_failure():
    rss_signal = RawSignal(source="rss_ap", text="RSS headline", age_seconds=60, confidence=0.9)

    with patch("sharpedge_trading.agents.research_agent.fetch_rss_signals", return_value=[rss_signal]):
        with patch("sharpedge_trading.agents.research_agent.fetch_reddit_signals", side_effect=Exception("Reddit down")):
            with patch("sharpedge_trading.agents.research_agent.fetch_twitter_signals", return_value=[]):
                signals = await _fetch_all_signals("CPI")

    # Should still return rss signals despite Reddit failure
    assert len(signals) == 1
    assert signals[0].source == "rss_ap"


# --- research_one ---

@pytest.mark.asyncio
async def test_research_one_emits_research_event():
    bus = EventBus()
    opp = _make_opportunity()
    rss_signal = RawSignal(source="rss_ap", text="Markets rise", age_seconds=60, confidence=0.9)

    with patch("sharpedge_trading.agents.research_agent.fetch_rss_signals", return_value=[rss_signal]):
        with patch("sharpedge_trading.agents.research_agent.fetch_reddit_signals", return_value=[]):
            with patch("sharpedge_trading.agents.research_agent.fetch_twitter_signals", return_value=[]):
                await research_one(opp, bus)

    event = await bus.get_research()
    assert event.market_id == "MKT-001"
    assert event.opportunity is opp
    assert len(event.signal_scores) == 1
    assert "[rss_ap] Markets rise" in event.narrative


@pytest.mark.asyncio
async def test_research_one_filters_stale_signals():
    bus = EventBus()
    # time_to_resolution = 2h → max_age = 3600s
    opp = _make_opportunity(time_to_resolution=timedelta(hours=2))
    # Signal is 5 hours old → beyond max_age → discarded
    stale_signal = RawSignal(source="rss_ap", text="Old news", age_seconds=18001, confidence=0.9)

    with patch("sharpedge_trading.agents.research_agent.fetch_rss_signals", return_value=[stale_signal]):
        with patch("sharpedge_trading.agents.research_agent.fetch_reddit_signals", return_value=[]):
            with patch("sharpedge_trading.agents.research_agent.fetch_twitter_signals", return_value=[]):
                await research_one(opp, bus)

    event = await bus.get_research()
    assert len(event.signal_scores) == 0
    assert "No signals" in event.narrative
