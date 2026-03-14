"""Tests for BacktestEngine: datetime timezone-awareness and stub implementations."""
import pytest
from datetime import timezone

from sharpedge_models.backtesting import BacktestEngine, BacktestResult


def test_record_prediction_timezone_aware():
    """record_prediction() stores BacktestResult with timezone-aware timestamp."""
    engine = BacktestEngine()
    engine.record_prediction(
        prediction_id="pred_tz",
        market_type="spread",
        sport="NFL",
        predicted_prob=0.55,
        predicted_edge=3.0,
        odds=-110,
    )
    result = engine._memory_store[0]
    assert result.timestamp.tzinfo is not None
    assert result.timestamp.tzinfo == timezone.utc


def test_store_to_db_stores_in_dict():
    """_store_to_db() stores result in self._predictions dict keyed by prediction_id."""
    engine = BacktestEngine(db_client="fake_db")
    result = BacktestResult(
        prediction_id="pred_001",
        timestamp=__import__("datetime").datetime.now(timezone.utc),
        market_type="spread",
        sport="NFL",
        predicted_probability=0.58,
        predicted_edge=3.2,
        odds=-110,
        outcome=None,
        closing_line=None,
    )
    engine._store_to_db(result)
    assert "pred_001" in engine._predictions
    assert engine._predictions["pred_001"] is result


def test_fetch_resolved_predictions_returns_resolved():
    """_fetch_resolved_predictions() returns BacktestResults where outcome is not None."""
    engine = BacktestEngine(db_client="fake_db")
    from datetime import datetime

    pending = BacktestResult(
        prediction_id="p1",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="NFL",
        predicted_probability=0.55,
        predicted_edge=2.0,
        odds=-110,
        outcome=None,
        closing_line=None,
    )
    resolved_win = BacktestResult(
        prediction_id="p2",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="NFL",
        predicted_probability=0.60,
        predicted_edge=4.0,
        odds=-110,
        outcome=True,
        closing_line=-3.5,
    )
    resolved_nba = BacktestResult(
        prediction_id="p3",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="NBA",
        predicted_probability=0.52,
        predicted_edge=1.5,
        odds=-108,
        outcome=False,
        closing_line=-2.0,
    )
    engine._store_to_db(pending)
    engine._store_to_db(resolved_win)
    engine._store_to_db(resolved_nba)

    results = engine._fetch_resolved_predictions("spread", "NFL")
    assert len(results) == 1
    assert results[0].prediction_id == "p2"

    all_spread = engine._fetch_resolved_predictions("spread", None)
    assert len(all_spread) == 2


def test_count_predictions_returns_correct_count():
    """_count_predictions() returns correct int count matching stored results."""
    engine = BacktestEngine(db_client="fake_db")
    from datetime import datetime

    for i in range(3):
        engine._store_to_db(BacktestResult(
            prediction_id=f"nfl_{i}",
            timestamp=datetime.now(timezone.utc),
            market_type="spread",
            sport="NFL",
            predicted_probability=0.55,
            predicted_edge=2.0,
            odds=-110,
            outcome=None,
            closing_line=None,
        ))
    for i in range(2):
        engine._store_to_db(BacktestResult(
            prediction_id=f"nba_{i}",
            timestamp=datetime.now(timezone.utc),
            market_type="total",
            sport="NBA",
            predicted_probability=0.55,
            predicted_edge=2.0,
            odds=-110,
            outcome=None,
            closing_line=None,
        ))

    assert engine._count_predictions("spread", "NFL") == 3
    assert engine._count_predictions("total", "NBA") == 2
    assert engine._count_predictions("spread", None) == 3
    assert engine._count_predictions("total", None) == 2


def test_update_outcome_db_updates_result():
    """_update_outcome_db() sets outcome and closing_line on the stored result."""
    engine = BacktestEngine(db_client="fake_db")
    from datetime import datetime

    result = BacktestResult(
        prediction_id="upd_001",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="NFL",
        predicted_probability=0.55,
        predicted_edge=2.0,
        odds=-110,
        outcome=None,
        closing_line=None,
    )
    engine._store_to_db(result)
    engine._update_outcome_db("upd_001", won=True, closing_line=-3.5)

    updated = engine._predictions["upd_001"]
    assert updated.outcome is True
    assert updated.closing_line == -3.5
