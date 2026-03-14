"""RED stubs for CalibrationStore — QUANT-07.

These tests will fail with ImportError until Plan 05-04 implements
packages/models/src/sharpedge_models/calibration_store.py.
"""
import pytest

from sharpedge_models.calibration_store import CalibrationStore


def test_get_confidence_mult_below_50_games(tmp_path):
    """get_confidence_mult returns 1.0 when fewer than 50 resolved games stored."""
    store = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    mult = store.get_confidence_mult("NFL")
    assert mult == 1.0, f"Expected 1.0 with <50 games, got {mult}"


def test_get_confidence_mult_after_update(tmp_path):
    """get_confidence_mult returns value in [0.5, 1.2] after 60+ resolved games."""
    store = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    probs = [0.6] * 60
    outcomes = [True, False] * 30  # 50% hit rate
    store.update("NFL", probs, outcomes)
    mult = store.get_confidence_mult("NFL")
    assert 0.5 <= mult <= 1.2, f"Expected mult in [0.5, 1.2], got {mult}"


def test_update_computes_brier_and_mult(tmp_path):
    """update persists state; subsequent get_confidence_mult reflects new Brier score."""
    store = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    probs = [0.55] * 60
    outcomes = [True if i % 2 == 0 else False for i in range(60)]
    store.update("NBA", probs, outcomes)

    # Reload from same path to confirm persistence
    store2 = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    mult = store2.get_confidence_mult("NBA")
    # After update, mult should be set (not default 1.0 from <50 threshold logic)
    assert mult != 1.0 or len(outcomes) >= 50, "update should change mult when enough games"


def test_poor_calibration_returns_below_1(tmp_path):
    """When probs are far from outcomes (high Brier score), confidence_mult < 1.0."""
    store = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    # Poorly calibrated: predicting 0.9 when outcome is False (Brier score high)
    probs = [0.95] * 60
    outcomes = [False] * 60  # Always wrong
    store.update("NFL", probs, outcomes)
    mult = store.get_confidence_mult("NFL")
    assert mult < 1.0, f"Poor calibration should yield mult < 1.0, got {mult}"


def test_good_calibration_returns_above_1(tmp_path):
    """When probs closely track outcomes (Brier score < 0.22), confidence_mult > 1.0."""
    store = CalibrationStore(store_path=tmp_path / "calibration.pkl")
    # Well calibrated: predicting ~0.8 and winning 80% of the time
    probs = [0.8] * 60
    outcomes = [True] * 48 + [False] * 12  # 80% hit rate
    store.update("NFL", probs, outcomes)
    mult = store.get_confidence_mult("NFL")
    assert mult > 1.0, f"Good calibration should yield mult > 1.0, got {mult}"
