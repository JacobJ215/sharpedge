"""run_models node: runs EV calculation and optional key number zone detection.

Calls EVCalculation functions from sharpedge_models.ev_calculator and
analyze_zone from sharpedge_analytics.key_numbers. No LLM, no network.
Under 80 lines.
"""

from __future__ import annotations

import logging

from sharpedge_models.ev_calculator import EVCalculation, calculate_ev

logger = logging.getLogger("sharpedge.agent.run_models")


def run_models(state: dict) -> dict:
    """Run EV calculation and optional key number zone detection.

    Uses game_context set by fetch_context. Calls calculate_ev() with
    model_prob and home_odds. Optionally enriches with key number zone
    analysis if spread_line is present.

    Args:
        state: BettingAnalysisState with game_context set.

    Returns:
        Partial state dict with ev_result dict.
    """
    game_context: dict = state.get("game_context") or {}

    sport: str = game_context.get("sport", "nfl").lower()
    try:
        from sharpedge_models.feature_assembler import FeatureAssembler
        from sharpedge_models.ml_inference import get_model_manager

        mgr = get_model_manager()
        if mgr.is_loaded:
            features = FeatureAssembler().assemble(game_context)
            ensemble_result = mgr.predict_ensemble(sport, features)
            if ensemble_result:
                model_prob: float = ensemble_result["meta_prob"]
            else:
                model_prob = game_context.get("model_prob", 0.52)
        else:
            model_prob = game_context.get("model_prob", 0.52)
    except Exception as exc:
        logger.warning("predict_ensemble failed, using fallback: %s", exc)
        model_prob = game_context.get("model_prob", 0.52)
    odds: int = game_context.get("home_odds", -110)

    try:
        calc: EVCalculation = calculate_ev(
            model_prob=model_prob,
            odds=odds,
        )
    except Exception as exc:
        logger.warning("calculate_ev failed: %s", exc)
        return {
            "ev_result": None,
            "quality_warnings": [f"run_models EV calculation failed: {exc}"],
        }

    ev_result: dict = {
        "ev_percentage": calc.ev_percentage,
        "edge": calc.edge,
        "implied_prob": calc.implied_prob,
        "model_prob": calc.model_prob,
        "is_positive_ev": calc.is_positive_ev,
        "prob_edge_positive": calc.prob_edge_positive,
        "kelly_full": calc.kelly_full,
        "kelly_half": calc.kelly_half,
        "confidence_level": calc.confidence_level.value,
        "odds": odds,
    }

    # Optional: key number zone detection for spreads/totals
    spread_line = game_context.get("spread_line")
    if spread_line is not None:
        try:
            from sharpedge_analytics.key_numbers import analyze_zone

            sport = game_context.get("sport", "NFL")
            zone = analyze_zone(float(spread_line), sport=str(sport))
            ev_result["zone_strength"] = zone.zone_strength
            ev_result["crosses_key"] = zone.crosses_key
            ev_result["half_point_value"] = zone.half_point_value
        except Exception as exc:
            logger.warning("Key number zone detection failed: %s", exc)

    return {"ev_result": ev_result}
