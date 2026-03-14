"""Cross-venue dislocation detection: consensus pricing and deviation scoring.

Consensus is computed as inverse-spread-weighted mean of venue mid prices.
Venues with tighter spreads (higher liquidity) receive more weight.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

from sharpedge_venue_adapters.protocol import CanonicalQuote


@dataclass(frozen=True)
class DislocScore:
    """Per-venue dislocation score relative to cross-venue consensus."""
    market_id: str
    venue_id: str
    venue_mid_prob: float       # this venue's current mid price (probability)
    consensus_prob: float       # inverse-spread-weighted consensus across all venues
    disloc_bps: float           # |venue_mid - consensus| * 10000
    is_stale: bool              # True if quote age > stale_threshold_seconds
    stale_threshold_seconds: int = 300


def _parse_utc(timestamp_utc: str) -> datetime:
    """Parse ISO-8601 timestamp with timezone to aware datetime."""
    ts = timestamp_utc.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def _is_quote_stale(quote: CanonicalQuote, stale_threshold_seconds: int) -> bool:
    """Return True if quote is older than stale_threshold_seconds."""
    try:
        quote_time = _parse_utc(quote.timestamp_utc)
        age_seconds = (datetime.now(timezone.utc) - quote_time).total_seconds()
        return age_seconds > stale_threshold_seconds
    except (ValueError, TypeError):
        return True  # unparseable timestamp treated as stale


def compute_consensus(
    quotes: list[CanonicalQuote],
    stale_threshold_seconds: int = 300,
) -> float:
    """Compute inverse-spread-weighted consensus probability.

    Tighter spread (higher liquidity) -> higher weight.
    Stale quotes are excluded from weighted calculation.
    Falls back to simple mean if all quotes are stale or zero-spread.

    Args:
        quotes: list of CanonicalQuote from multiple venues, same market
        stale_threshold_seconds: age in seconds beyond which a quote is stale

    Returns:
        float: consensus probability in [0, 1]
    """
    if not quotes:
        raise ValueError("quotes must not be empty")

    # Separate fresh from stale
    fresh = [q for q in quotes if not _is_quote_stale(q, stale_threshold_seconds)]
    pool = fresh if fresh else quotes  # fallback to all if all stale

    # Inverse-spread weighting (skip zero-spread quotes to avoid inf weight)
    eligible = [q for q in pool if q.spread_prob > 1e-6]
    if eligible:
        weights = [1.0 / q.spread_prob for q in eligible]
        total_w = sum(weights)
        return sum(q.mid_prob * w / total_w for q, w in zip(eligible, weights))

    # Fallback: simple mean
    return sum(q.mid_prob for q in pool) / len(pool)


def score_dislocation(
    quotes: list[CanonicalQuote],
    stale_threshold_seconds: int = 300,
) -> list[DislocScore]:
    """Score each venue's quote relative to cross-venue consensus.

    Args:
        quotes: CanonicalQuote list for a single market across multiple venues
        stale_threshold_seconds: stale detection threshold per-venue default

    Returns:
        list[DislocScore] — one per input quote, ordered identically
    """
    if not quotes:
        return []

    consensus = compute_consensus(quotes, stale_threshold_seconds)

    scores: list[DislocScore] = []
    for q in quotes:
        stale = _is_quote_stale(q, stale_threshold_seconds)
        disloc_bps = abs(q.mid_prob - consensus) * 10_000.0
        scores.append(DislocScore(
            market_id=q.market_id,
            venue_id=q.venue_id,
            venue_mid_prob=q.mid_prob,
            consensus_prob=consensus,
            disloc_bps=round(disloc_bps, 2),
            is_stale=stale,
            stale_threshold_seconds=stale_threshold_seconds,
        ))

    return scores
