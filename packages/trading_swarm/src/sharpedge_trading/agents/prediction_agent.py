"""Prediction Agent — RF model + LLM calibration → PredictionEvent if edge > threshold."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import numpy as np

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import PredictionEvent, ResearchEvent
from sharpedge_trading.signals.llm_calibrator import LLMCalibrator

logger = logging.getLogger(__name__)

_KALSHI_FEE = 0.001  # 0.1% transaction fee
_CATEGORIES = ("political", "economic", "crypto", "entertainment", "weather")
_MODEL_DIR = Path(os.environ.get("MODEL_DIR", "data/models/pm"))


def _model_path(category: str) -> Path:
    return _MODEL_DIR / f"{category}.joblib"


def _load_model(category: str) -> object | None:
    """Load joblib model for category. Returns None if missing, logs WARNING."""
    path = _model_path(category)
    if not path.exists():
        logger.warning("Model file missing for category %s: %s", category, path)
        return None
    try:
        import joblib  # deferred
        return joblib.load(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load model for %s: %s", category, exc)
        return None


def _build_features(event: ResearchEvent) -> list[float]:
    """Build a minimal feature vector from the research event.

    Uses market price, signal count, mean confidence, and mean age.
    This is a simplified feature vector — the full Phase 9 feature engineering
    pipeline would be wired in here in production.
    """
    opp = event.opportunity
    scores = event.signal_scores
    mean_confidence = sum(s.confidence for s in scores) / len(scores) if scores else 0.5
    mean_age = sum(s.age_seconds for s in scores) / len(scores) if scores else 0.0
    return [
        opp.current_price,
        opp.price_momentum,
        opp.spread_ratio,
        opp.liquidity,
        float(len(scores)),
        mean_confidence,
        mean_age,
    ]


def _predict_rf(model: object, features: list[float]) -> float:
    """Run RF model. Returns probability of YES resolution."""
    arr = np.array([features])
    proba = model.predict_proba(arr)[0]  # type: ignore[union-attr]
    # Assume class order: [NO, YES] or [0, 1]
    return float(proba[1]) if len(proba) > 1 else float(proba[0])


def validate_models_at_startup() -> bool:
    """Check all category models exist. Returns False if any are missing."""
    all_present = True
    for cat in _CATEGORIES:
        path = _model_path(cat)
        if not path.exists():
            logger.warning("STARTUP: Missing model for category %s at %s", cat, path)
            all_present = False
    return all_present


async def predict_one(
    event: ResearchEvent,
    bus: EventBus,
    config: TradingConfig,
    calibrator: LLMCalibrator,
) -> bool:
    """Process one ResearchEvent. Returns True if PredictionEvent was emitted."""
    category = event.opportunity.category
    kalshi_price = event.opportunity.current_price

    # Load RF model (or fall back to market implied probability)
    model = _load_model(category)
    if model is None:
        base_prob = kalshi_price
        logger.info("Using market implied probability for %s (model missing)", event.market_id)
    else:
        features = _build_features(event)
        try:
            base_prob = _predict_rf(model, features)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RF prediction failed for %s: %s — using market price", event.market_id, exc)
            base_prob = kalshi_price

    # LLM calibration — run in executor to avoid blocking the asyncio event loop
    loop = asyncio.get_running_loop()
    calibrated_prob = await loop.run_in_executor(
        None, calibrator.calibrate, base_prob, event.narrative
    )

    # Edge calculation
    edge = abs(calibrated_prob - kalshi_price) - _KALSHI_FEE

    # Confidence score: mean of signal scores (proxy)
    scores = event.signal_scores
    confidence = sum(s.confidence for s in scores) / len(scores) if scores else 0.0

    # Gate: emit only if edge > threshold and confidence above threshold
    if edge <= config.min_edge or confidence < config.confidence_threshold:
        logger.debug(
            "No edge for %s: edge=%.4f (threshold=%.4f), confidence=%.4f",
            event.market_id, edge, config.min_edge, confidence,
        )
        return False

    prediction = PredictionEvent(
        market_id=event.market_id,
        research=event,
        base_probability=base_prob,
        calibrated_probability=calibrated_prob,
        edge=edge,
        confidence_score=confidence,
    )
    await bus.put_prediction(prediction)
    logger.info(
        "Prediction: %s | base=%.4f calibrated=%.4f edge=%.4f confidence=%.4f",
        event.market_id, base_prob, calibrated_prob, edge, confidence,
    )
    return True


async def run_prediction_agent(
    bus: EventBus,
    config: TradingConfig,
    calibrator: LLMCalibrator,
) -> None:
    """Main prediction agent loop."""
    logger.info("Prediction agent started")
    while True:
        event = await bus.get_research()
        await predict_one(event, bus, config, calibrator)
