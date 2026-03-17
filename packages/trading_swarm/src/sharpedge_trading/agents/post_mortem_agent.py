"""Post-Mortem Agent — structured loss attribution and bounded learning updates."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sharpedge_trading.agents.risk_agent import record_loss, record_win
from sharpedge_trading.config import TradingConfig, load_config
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ResolutionEvent

logger = logging.getLogger(__name__)

# Attribution thresholds
_MODEL_ERROR_THRESHOLD = 0.30   # |predicted - outcome| > 0.30 → model error
_SIZING_ERROR_THRESHOLD = 0.03  # position > 3% of bankroll → sizing risk

# Bounded learning: adjustments per attribution type
_CONFIDENCE_THRESHOLD_DELTA = 0.005   # raise confidence_threshold
_SIGNAL_WEIGHT_DELTA = 0.10           # reduce offending source weight
_KELLY_FRACTION_DELTA = 0.02          # reduce kelly_fraction

# Max consecutive auto-adjustments before pausing auto-learning
_MAX_AUTO_ADJUSTMENTS = 5

# Module-level auto-learning state
_auto_adjustment_count = 0
_auto_learning_paused = False


def _get_supabase_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore[import]
        return create_client(url, key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to create Supabase client: %s", exc)
        return None


def _classify_attribution(
    event: ResolutionEvent,
    calibrated_prob: float,
    position_size_pct: float,
) -> dict[str, float]:
    """Classify loss into attribution dimensions. Returns scores (0-1)."""
    outcome = float(event.actual_outcome)  # 1.0 if YES, 0.0 if NO

    # Model error: predicted probability was very wrong
    model_error = 1.0 if abs(calibrated_prob - outcome) > _MODEL_ERROR_THRESHOLD else 0.0

    # Signal error: narrative contradicted outcome
    # Proxy: calibrated_prob was adjusted by LLM from base in wrong direction
    # (We can't reconstruct this without research log, so use correlation with model_error)
    signal_error = 0.5 * model_error  # simplified attribution

    # Sizing error: position was too large
    sizing_error = 1.0 if position_size_pct > 0.03 else 0.0

    # Variance: low-probability outcome that still happened
    variance = 1.0 if calibrated_prob < 0.35 and not event.actual_outcome else 0.0

    return {
        "model_error_score": model_error,
        "signal_error_score": signal_error,
        "sizing_error_score": sizing_error,
        "variance_score": variance,
    }


def _write_post_mortem(
    client,
    event: ResolutionEvent,
    attribution: dict[str, float],
    narrative: str,
) -> None:
    """Write post-mortem to Supabase."""
    try:
        row = {
            "trade_id": event.trade_id,
            **attribution,
            "llm_narrative": narrative,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        client.table("trade_post_mortems").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write post-mortem: %s", exc)


def _apply_learning_update(
    attribution: dict[str, float],
    config: TradingConfig,
) -> bool:
    """Apply bounded learning updates to config in Supabase. Returns True if updated."""
    global _auto_adjustment_count, _auto_learning_paused

    if _auto_learning_paused:
        logger.warning("Auto-learning paused — skipping adjustment (manual review required)")
        return False

    client = _get_supabase_client()
    if client is None:
        return False

    updated = False
    current_config = load_config()

    if attribution["model_error_score"] > 0:
        new_val = min(
            current_config.confidence_threshold + _CONFIDENCE_THRESHOLD_DELTA,
            0.10,  # hard upper bound
        )
        _update_config(client, "confidence_threshold", new_val)
        updated = True

    if attribution["sizing_error_score"] > 0:
        new_val = max(
            current_config.kelly_fraction - _KELLY_FRACTION_DELTA,
            0.10,  # hard lower bound
        )
        _update_config(client, "kelly_fraction", new_val)
        updated = True

    if updated:
        _auto_adjustment_count += 1
        logger.info("Auto-learning adjustment #%d applied", _auto_adjustment_count)
        if _auto_adjustment_count >= _MAX_AUTO_ADJUSTMENTS:
            _auto_learning_paused = True
            logger.warning(
                "Auto-learning paused after %d consecutive adjustments — manual review required",
                _MAX_AUTO_ADJUSTMENTS,
            )
    return updated


def _update_config(client, key: str, value: float) -> None:
    try:
        client.table("trading_config").upsert(
            {
                "key": key,
                "value": str(value),
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                "updated_by": "post_mortem_agent",
            },
            on_conflict="key",
        ).execute()
        logger.info("Config updated: %s → %.4f", key, value)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to update config %s: %s", key, exc)


async def process_resolution(
    event: ResolutionEvent,
    config: TradingConfig,
    bankroll: float,
) -> None:
    """Process a ResolutionEvent — record post-mortem for losses, update circuit breakers."""
    if event.pnl >= 0:
        record_win()
        logger.info("WIN: %s pnl=%.2f", event.market_id, event.pnl)
        return

    # Loss path
    record_loss(abs(event.pnl))

    # Estimate calibrated_prob from pnl (simplified — actual stored in research log)
    # Using pnl relationship: if yes and loss, calibrated_prob ≈ entry_price
    # We use a proxy of 0.5 (neutral) if we can't reconstruct
    calibrated_prob = 0.5
    position_size_pct = abs(event.pnl) / bankroll if bankroll > 0 else 0.0

    attribution = _classify_attribution(event, calibrated_prob, position_size_pct)
    narrative = (
        f"Loss of ${abs(event.pnl):.2f} on {event.market_id}. "
        f"Outcome={'YES' if event.actual_outcome else 'NO'}. "
        f"Attribution: model_error={attribution['model_error_score']:.2f}, "
        f"signal_error={attribution['signal_error_score']:.2f}, "
        f"sizing_error={attribution['sizing_error_score']:.2f}, "
        f"variance={attribution['variance_score']:.2f}"
    )
    logger.warning("LOSS: %s pnl=%.2f | %s", event.market_id, event.pnl, narrative)

    client = _get_supabase_client()
    if client:
        _write_post_mortem(client, event, attribution, narrative)

    _apply_learning_update(attribution, config)


async def run_post_mortem_agent(bus: EventBus, config: TradingConfig, bankroll: float) -> None:
    """Main post-mortem agent loop — processes every ResolutionEvent."""
    logger.info("Post-mortem agent started")
    while True:
        event = await bus.get_resolution()
        await process_resolution(event, config, bankroll)
