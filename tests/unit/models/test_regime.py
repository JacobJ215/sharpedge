"""Failing test stubs for QUANT-03: Regime classifier."""


def test_classify_steam_move():
    """Fast consensus line movement returns STEAM_MOVE."""
    from sharpedge_analytics.regime import classify_regime, RegimeState
    result = classify_regime(ticket_pct=0.50, handle_pct=0.55, line_move_pts=2.0,
                              move_velocity=0.8, book_alignment=0.85)
    assert result.regime == RegimeState.STEAM_MOVE
    assert result.confidence > 0.7


def test_classify_public_heavy():
    """High ticket%, low handle% returns PUBLIC_HEAVY."""
    from sharpedge_analytics.regime import classify_regime, RegimeState
    result = classify_regime(ticket_pct=0.70, handle_pct=0.45, line_move_pts=0.5,
                              move_velocity=0.1, book_alignment=0.4)
    assert result.regime == RegimeState.PUBLIC_HEAVY


def test_classify_settled_default():
    """Balanced market returns SETTLED."""
    from sharpedge_analytics.regime import classify_regime, RegimeState
    result = classify_regime(ticket_pct=0.50, handle_pct=0.50, line_move_pts=0.5,
                              move_velocity=0.1, book_alignment=0.5)
    assert result.regime == RegimeState.SETTLED


def test_regime_has_scale():
    """RegimeClassification exposes a scale field used by AlphaComposer."""
    from sharpedge_analytics.regime import classify_regime
    result = classify_regime(ticket_pct=0.50, handle_pct=0.50, line_move_pts=0.5,
                              move_velocity=0.1, book_alignment=0.5)
    assert 0.5 <= result.scale <= 1.5
