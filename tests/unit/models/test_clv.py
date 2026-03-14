"""Failing test stubs for QUANT-06: Closing Line Value calculation."""
import pytest


def test_calculate_clv_positive():
    """Bet at -110 that closes at -120 has positive CLV (beat the close)."""
    from sharpedge_models.clv import calculate_clv
    clv = calculate_clv(bet_odds=-110, closing_line_odds=-120)
    assert clv > 0.0


def test_calculate_clv_negative():
    """Bet at -110 that closes at -105 has negative CLV (lost value)."""
    from sharpedge_models.clv import calculate_clv
    clv = calculate_clv(bet_odds=-110, closing_line_odds=-105)
    assert clv < 0.0


def test_calculate_clv_zero():
    """Bet at same odds as close has zero CLV."""
    from sharpedge_models.clv import calculate_clv
    clv = calculate_clv(bet_odds=-110, closing_line_odds=-110)
    assert clv == pytest.approx(0.0)
