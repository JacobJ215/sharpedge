"""Research Agent — fetches signals for each opportunity and emits ResearchEvents."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from sharpedge_trading.events.types import OpportunityEvent, ResearchEvent, SignalScore
from sharpedge_trading.signals.news_rss_client import fetch_rss_signals
from sharpedge_trading.signals.reddit_client import fetch_reddit_signals
from sharpedge_trading.signals.twitter_client import fetch_twitter_signals
from sharpedge_trading.signals.types import RawSignal

if TYPE_CHECKING:
    from sharpedge_trading.events.bus import EventBus

logger = logging.getLogger(__name__)

# Signal freshness: signals older than resolution_time / 2 are discarded
# Signals older than 1 hour (3600s) receive a 50% confidence penalty
_CONFIDENCE_PENALTY_AGE = 3600.0  # 1 hour
_CONFIDENCE_PENALTY_FACTOR = 0.5

# Bounded concurrency: cap parallel research tasks
_MAX_CONCURRENT_RESEARCH = 5


def _apply_freshness(signal: RawSignal, max_age_seconds: float) -> RawSignal | None:
    """Apply freshness rules. Returns None if signal should be discarded."""
    if signal.age_seconds > max_age_seconds:
        return None  # discard stale signal
    confidence = signal.confidence
    if signal.age_seconds > _CONFIDENCE_PENALTY_AGE:
        confidence *= _CONFIDENCE_PENALTY_FACTOR
    return RawSignal(
        source=signal.source,
        text=signal.text,
        age_seconds=signal.age_seconds,
        confidence=confidence,
    )


def _raw_to_score(signal: RawSignal) -> SignalScore:
    """Convert a RawSignal to a SignalScore with a neutral sentiment placeholder.

    Sentiment is set to 0.5 (neutral) at this stage — actual sentiment analysis
    is performed by the LLM calibrator in the Prediction Agent using the narrative.
    """
    return SignalScore(
        source=signal.source,
        sentiment=0.5,  # placeholder; updated by LLM in prediction step
        confidence=signal.confidence,
        age_seconds=signal.age_seconds,
    )


def _build_narrative(signals: list[RawSignal]) -> str:
    """Build a text narrative summary from signals for LLM consumption."""
    if not signals:
        return "No signals available."
    lines = [f"[{s.source}] {s.text}" for s in signals[:20]]  # cap at 20 items for context
    return "\n".join(lines)


async def _fetch_all_signals(query: str) -> list[RawSignal]:
    """Fetch from all sources in parallel, return combined list."""
    source_names = ["rss", "reddit", "twitter"]
    results = await asyncio.gather(
        fetch_rss_signals(query),
        fetch_reddit_signals(query),
        fetch_twitter_signals(query),
        return_exceptions=True,
    )
    signals: list[RawSignal] = []
    for name, batch in zip(source_names, results, strict=False):
        if isinstance(batch, Exception):
            logger.warning("Signal source %s failed: %s", name, batch)
            continue
        signals.extend(batch)
    return signals


async def research_one(opportunity: OpportunityEvent, bus: EventBus) -> None:
    """Research a single opportunity and emit a ResearchEvent."""
    query = opportunity.ticker or opportunity.market_id
    if not query:
        logger.warning("OpportunityEvent has no ticker or market_id — skipping research")
        return
    max_age = opportunity.time_to_resolution.total_seconds() / 2

    raw_signals = await _fetch_all_signals(query)

    # Apply freshness rules
    fresh_signals: list[RawSignal] = []
    for sig in raw_signals:
        filtered = _apply_freshness(sig, max_age)
        if filtered is not None:
            fresh_signals.append(filtered)

    narrative = _build_narrative(fresh_signals)
    signal_scores = [_raw_to_score(s) for s in fresh_signals]

    event = ResearchEvent(
        market_id=opportunity.market_id,
        opportunity=opportunity,
        narrative=narrative,
        signal_scores=signal_scores,
    )
    await bus.put_research(event)
    logger.info(
        "Research complete: %s — %d/%d signals fresh, narrative=%d chars",
        opportunity.market_id,
        len(fresh_signals),
        len(raw_signals),
        len(narrative),
    )


async def run_research_agent(bus: EventBus) -> None:
    """Main research agent loop — consumes OpportunityEvents, bounded concurrency."""
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_RESEARCH)
    logger.info("Research agent started (max_concurrent=%d)", _MAX_CONCURRENT_RESEARCH)

    tasks: set[asyncio.Task] = set()

    async def _bounded(opp: OpportunityEvent) -> None:
        async with semaphore:
            await research_one(opp, bus)

    while True:
        opp = await bus.get_opportunity()
        task = asyncio.create_task(_bounded(opp))
        tasks.add(task)

        def _on_done(t: asyncio.Task) -> None:
            tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                logger.error("Research task failed: %s", t.exception())

        task.add_done_callback(_on_done)
