"""Tests for Prediction Agent."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_trading.agents.prediction_agent import (
    _build_features,
    _predict_rf,
    validate_models_at_startup,
    predict_one,
)
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import (
    OpportunityEvent,
    PredictionEvent,
    ResearchEvent,
)
from sharpedge_trading.signals.llm_calibrator import LLMCalibrator
from sharpedge_trading.events.types import SignalScore


def _make_config(**overrides) -> TradingConfig:
    return TradingConfig.from_dict({
        "confidence_threshold": "0.03",
        "kelly_fraction": "0.25",
        "max_category_exposure": "0.20",
        "max_total_exposure": "0.40",
        "daily_loss_limit": "0.10",
        "min_liquidity": "500",
        "min_edge": "0.03",
        **overrides,
    })


def _make_opportunity(**kwargs) -> OpportunityEvent:
    defaults = dict(
        market_id="MKT-001",
        ticker="TICKER-001",
        category="economic",
        current_price=0.40,  # kalshi price
        liquidity=1000.0,
        time_to_resolution=timedelta(hours=24),
        price_momentum=0.20,
        spread_ratio=2.5,
    )
    defaults.update(kwargs)
    return OpportunityEvent(**defaults)


def _make_signal_score(confidence: float = 0.8) -> SignalScore:
    return SignalScore(source="rss_ap", sentiment=0.5, confidence=confidence, age_seconds=60.0)


def _make_research_event(**kwargs) -> ResearchEvent:
    opp = kwargs.pop("opportunity", _make_opportunity())
    defaults = dict(
        market_id=opp.market_id,
        opportunity=opp,
        narrative="Markets showing bullish signals",
        signal_scores=[_make_signal_score()],
    )
    defaults.update(kwargs)
    return ResearchEvent(**defaults)


# --- _build_features ---

def test_build_features_returns_list_of_floats():
    event = _make_research_event()
    features = _build_features(event)
    assert isinstance(features, list)
    assert all(isinstance(f, float) for f in features)
    assert len(features) == 7


def test_build_features_empty_signals_uses_defaults():
    event = _make_research_event(signal_scores=[])
    features = _build_features(event)
    assert features[4] == 0.0  # signal count
    assert features[5] == 0.5  # default mean_confidence


# --- _predict_rf ---

def test_predict_rf_returns_yes_probability():
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.4, 0.6]]

    import numpy as np
    with patch("sharpedge_trading.agents.prediction_agent.np", np):
        prob = _predict_rf(mock_model, [0.4, 0.2, 2.5, 1000.0, 1, 0.8, 60.0])

    assert prob == pytest.approx(0.6)


# --- validate_models_at_startup ---

def test_validate_models_returns_false_when_missing(tmp_path):
    with patch("sharpedge_trading.agents.prediction_agent._MODEL_DIR", tmp_path):
        result = validate_models_at_startup()
    assert result is False


def test_validate_models_returns_true_when_all_present(tmp_path):
    from sharpedge_trading.agents.prediction_agent import _CATEGORIES
    for cat in _CATEGORIES:
        (tmp_path / f"{cat}.joblib").touch()
    with patch("sharpedge_trading.agents.prediction_agent._MODEL_DIR", tmp_path):
        result = validate_models_at_startup()
    assert result is True


# --- predict_one ---

@pytest.mark.asyncio
async def test_predict_one_emits_prediction_when_edge_sufficient():
    bus = EventBus()
    config = _make_config(min_edge="0.03", confidence_threshold="0.03")
    event = _make_research_event()  # kalshi_price=0.40, signal confidence=0.80

    # RF model returns 0.55 → calibrated stays ~0.55 → edge = |0.55-0.40| - 0.001 = 0.149
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.45, 0.55]]

    calibrator = MagicMock(spec=LLMCalibrator)
    calibrator.calibrate.return_value = 0.55

    import numpy as np
    with patch("sharpedge_trading.agents.prediction_agent._load_model", return_value=mock_model):
        with patch("sharpedge_trading.agents.prediction_agent.np", np):
            emitted = await predict_one(event, bus, config, calibrator)

    assert emitted is True
    pred = await bus.get_prediction()
    assert pred.market_id == "MKT-001"
    assert pred.edge > 0.03
    assert pred.calibrated_probability == pytest.approx(0.55)


@pytest.mark.asyncio
async def test_predict_one_skips_when_no_edge():
    bus = EventBus()
    config = _make_config(min_edge="0.03")
    event = _make_research_event()  # kalshi_price=0.40

    # RF returns 0.42 → calibrated 0.42 → edge = |0.42-0.40| - 0.001 = 0.019 < 0.03
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.58, 0.42]]

    calibrator = MagicMock(spec=LLMCalibrator)
    calibrator.calibrate.return_value = 0.42

    import numpy as np
    with patch("sharpedge_trading.agents.prediction_agent._load_model", return_value=mock_model):
        with patch("sharpedge_trading.agents.prediction_agent.np", np):
            emitted = await predict_one(event, bus, config, calibrator)

    assert emitted is False


@pytest.mark.asyncio
async def test_predict_one_falls_back_to_market_price_when_model_missing():
    bus = EventBus()
    config = _make_config(min_edge="0.03")
    # kalshi_price=0.40, model missing → base_prob=0.40
    # calibrator returns 0.40 → edge = 0 - 0.001 < 0 → no emission
    event = _make_research_event()

    calibrator = MagicMock(spec=LLMCalibrator)
    calibrator.calibrate.return_value = 0.40

    with patch("sharpedge_trading.agents.prediction_agent._load_model", return_value=None):
        emitted = await predict_one(event, bus, config, calibrator)

    assert emitted is False


@pytest.mark.asyncio
async def test_predict_one_emits_prediction_with_model_fallback_when_rf_fails():
    bus = EventBus()
    config = _make_config(min_edge="0.03", confidence_threshold="0.03")
    event = _make_research_event()

    # RF raises → falls back to kalshi_price=0.40
    # calibrator returns 0.55 → edge = 0.149 > 0.03 → emits
    mock_model = MagicMock()
    mock_model.predict_proba.side_effect = Exception("RF crash")

    calibrator = MagicMock(spec=LLMCalibrator)
    calibrator.calibrate.return_value = 0.55

    with patch("sharpedge_trading.agents.prediction_agent._load_model", return_value=mock_model):
        emitted = await predict_one(event, bus, config, calibrator)

    assert emitted is True
