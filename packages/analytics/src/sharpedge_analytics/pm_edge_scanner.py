"""Prediction market edge scanner.

Detects alpha edges across Kalshi and Polymarket by comparing model probabilities
to live market prices. Applies regime-adjusted thresholds and liquidity filters,
then enriches qualifying edges with BettingAlpha scores.

Model probability assumption (Pitfall 3 from RESEARCH.md):
No PM-specific prediction model exists in Phase 3. When the caller does not
supply a model_prob for a given market, a fee-adjusted price is used as the
"model probability" — the fair value after standard PM fees (~3%). An edge
exists when the fee-adjusted price differs from the raw market price enough
to exceed the regime threshold. Callers can override this by passing model_probs.

Fee constant: KALSHI_FEE_RATE = 0.03, POLY_FEE_RATE = 0.03
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sharpedge_analytics.pm_regime import (
    PM_REGIME_SCALE,
    classify_pm_regime,
)
from sharpedge_models.alpha import compose_alpha

__all__ = ["PMEdge", "scan_pm_edges"]

log = logging.getLogger(__name__)

KALSHI_FEE_RATE = 0.03
POLY_FEE_RATE = 0.03

# Default volume floor in USD
DEFAULT_VOLUME_FLOOR = 500.0


@dataclass
class PMEdge:
    """A detected edge in a prediction market."""

    platform: str            # "kalshi" | "polymarket"
    market_id: str
    market_title: str
    market_prob: float       # mid_price (Kalshi) or yes_price (Polymarket)
    model_prob: float        # caller-supplied or fee-adjusted fallback
    edge_pct: float          # (model_prob - market_prob) * 100
    volume_24h: float        # USD (converted for Kalshi)
    close_time: datetime | None
    alpha_score: float       # BettingAlpha.alpha from compose_alpha()
    alpha_badge: str         # "PREMIUM" | "HIGH" | "MEDIUM" | "SPECULATIVE"
    regime: str              # PMRegimeState.value
    regime_threshold: float  # adjusted threshold used for this market


def _classify_for_market(
    close_time: datetime | None,
    hours_since_created: float,
    price_variance: float,
    volume_spike_ratio: float,
) -> object:
    """Compute hours_to_close and classify regime."""
    if close_time is not None:
        from datetime import timezone

        now = datetime.now(tz=timezone.utc)
        if close_time.tzinfo is None:
            from datetime import timezone as tz
            close_time = close_time.replace(tzinfo=tz.utc)
        delta_h = (close_time - now).total_seconds() / 3600.0
        hours_to_close = max(0.0, delta_h)
    else:
        # No close time available; assume mid-lifecycle (not closing soon)
        hours_to_close = 168.0  # 1 week default

    return classify_pm_regime(
        hours_to_close=hours_to_close,
        hours_since_created=hours_since_created,
        volume_spike_ratio=volume_spike_ratio,
        price_variance=price_variance,
    )


def scan_pm_edges(
    kalshi_markets: list,
    polymarket_markets: list,
    model_probs: dict[str, float],
    volume_floor: float = DEFAULT_VOLUME_FLOOR,
    hours_since_created: float = 200.0,
    # Deferred to Plan 03 (PM-04: cross-market correlation):
    active_bets: list | None = None,
    market_titles: dict[str, str] | None = None,
) -> list[PMEdge]:
    """Scan Kalshi and Polymarket markets for model-vs-market edges.

    Args:
        kalshi_markets: List of KalshiMarket objects.
        polymarket_markets: List of PolymarketMarket objects.
        model_probs: Dict mapping market_id → model probability. Markets not
            present in this dict use a fee-adjusted fallback.
        volume_floor: Minimum 24h volume in USD to include a market. Markets
            below this threshold are silently skipped (debug log only).
        hours_since_created: Default hours since market creation when not
            available from the market object (used for regime classification).

    Returns:
        List of PMEdge objects sorted by alpha_score descending.
    """
    results: list[PMEdge] = []

    # --- Kalshi markets ---
    for market in kalshi_markets:
        market_id: str = market.ticker
        market_prob: float = market.mid_price
        volume_contracts: int = market.volume_24h
        volume_usd = volume_contracts * market_prob

        if volume_usd < volume_floor:
            log.debug("skipping %s: low liquidity (%.0f USD)", market_id, volume_usd)
            continue

        model_prob = model_probs.get(market_id)
        if model_prob is None:
            # Fallback: fee-adjusted fair price
            model_prob = market_prob / (1.0 - KALSHI_FEE_RATE)
            model_prob = min(model_prob, 1.0)

        price_variance = getattr(market, "spread", 0.05)
        volume_spike_ratio = 1.0  # no historical baseline for Kalshi in Phase 3

        classification = _classify_for_market(
            close_time=market.close_time,
            hours_since_created=hours_since_created,
            price_variance=price_variance,
            volume_spike_ratio=volume_spike_ratio,
        )

        regime_threshold = classification.edge_threshold_pct
        edge_pct = (model_prob - market_prob) * 100.0

        if edge_pct <= regime_threshold:
            continue

        alpha_result = compose_alpha(
            edge_score=edge_pct / 100.0,
            regime_scale=PM_REGIME_SCALE[classification.regime],
            survival_prob=0.95,
            confidence_mult=1.0,
        )

        results.append(
            PMEdge(
                platform="kalshi",
                market_id=market_id,
                market_title=market.title,
                market_prob=market_prob,
                model_prob=model_prob,
                edge_pct=edge_pct,
                volume_24h=volume_usd,
                close_time=market.close_time,
                alpha_score=alpha_result.alpha,
                alpha_badge=alpha_result.quality_badge,
                regime=classification.regime.value,
                regime_threshold=regime_threshold,
            )
        )

    # --- Polymarket markets ---
    for market in polymarket_markets:
        market_id = market.condition_id
        market_prob = market.yes_price
        volume_usd = float(market.volume_24h)  # already in USD

        if volume_usd < volume_floor:
            log.debug("skipping %s: low liquidity (%.0f USD)", market_id, volume_usd)
            continue

        model_prob = model_probs.get(market_id)
        if model_prob is None:
            model_prob = market_prob / (1.0 - POLY_FEE_RATE)
            model_prob = min(model_prob, 1.0)

        price_variance = 0.05  # no spread available on Polymarket mock
        # Volume spike: if 24h vol is unusually large vs floor, treat as spike
        volume_spike_ratio = volume_usd / (5.0 * volume_floor) if volume_usd > 5.0 * volume_floor else 1.0

        close_time = getattr(market, "end_date", None)
        classification = _classify_for_market(
            close_time=close_time,
            hours_since_created=hours_since_created,
            price_variance=price_variance,
            volume_spike_ratio=volume_spike_ratio,
        )

        regime_threshold = classification.edge_threshold_pct
        edge_pct = (model_prob - market_prob) * 100.0

        if edge_pct <= regime_threshold:
            continue

        alpha_result = compose_alpha(
            edge_score=edge_pct / 100.0,
            regime_scale=PM_REGIME_SCALE[classification.regime],
            survival_prob=0.95,
            confidence_mult=1.0,
        )

        results.append(
            PMEdge(
                platform="polymarket",
                market_id=market_id,
                market_title=market.question,
                market_prob=market_prob,
                model_prob=model_prob,
                edge_pct=edge_pct,
                volume_24h=volume_usd,
                close_time=close_time,
                alpha_score=alpha_result.alpha,
                alpha_badge=alpha_result.quality_badge,
                regime=classification.regime.value,
                regime_threshold=regime_threshold,
            )
        )

    results.sort(key=lambda e: e.alpha_score, reverse=True)
    return results
