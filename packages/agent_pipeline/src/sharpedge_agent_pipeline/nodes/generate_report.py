"""generate_report node: formats final Discord-embed-compatible analysis report.

No LLM, no network. Under 100 lines.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("sharpedge.agent.generate_report")


def generate_report(state: dict) -> dict:
    """Format a Discord-embed-compatible analysis report string.

    Includes: verdict, alpha badge, EV%, kelly %, regime, Monte Carlo summary.
    Handles both REJECT path (no alpha/kelly) and PASS/WARN path.

    Args:
        state: Full BettingAnalysisState.

    Returns:
        Partial state dict with report (str).
    """
    eval_verdict: str = state.get("eval_verdict", "UNKNOWN")
    eval_reasoning: str = state.get("eval_reasoning", "")

    ev_result: dict = state.get("ev_result") or {}
    regime_result = state.get("regime_result")
    mc_result = state.get("mc_result")
    alpha = state.get("alpha")
    kelly_fraction: float | None = state.get("kelly_fraction")

    # --- Header ---
    game_query: str = state.get("game_query", "Unknown game")
    sport: str = state.get("sport", "")
    lines = [
        f"**SharpEdge Analysis** | {sport} | {game_query}",
        f"**Verdict:** {eval_verdict}",
        "",
    ]

    # --- Alpha badge ---
    if alpha is not None:
        badge = getattr(alpha, "quality_badge", "N/A")
        alpha_score = getattr(alpha, "alpha", 0.0)
        lines.append(f"**Alpha:** {alpha_score:.4f} [{badge}]")
    else:
        lines.append("**Alpha:** N/A (setup rejected or not computed)")

    # --- EV signals ---
    if ev_result:
        ev_pct = ev_result.get("ev_percentage", 0.0)
        edge = ev_result.get("edge", 0.0)
        model_prob = ev_result.get("model_prob", 0.0)
        implied_prob = ev_result.get("implied_prob", 0.0)
        lines.append(f"**EV:** {ev_pct:+.2f}% | Edge: {edge:+.2f}%")
        lines.append(f"**Model prob:** {model_prob:.1f}% vs Implied: {implied_prob:.1f}%")

    # --- Kelly fraction ---
    if kelly_fraction is not None:
        lines.append(f"**Kelly (half):** {kelly_fraction:.1%} of bankroll")

    # --- Regime ---
    if regime_result is not None:
        regime_name = getattr(regime_result.regime, "value", str(regime_result.regime))
        confidence = getattr(regime_result, "confidence", 0.0)
        lines.append(f"**Regime:** {regime_name} (confidence {confidence:.0%})")

    # --- Monte Carlo ---
    if mc_result is not None:
        ruin = getattr(mc_result, "ruin_probability", 0.0)
        p50 = getattr(mc_result, "p50_bankroll", 1.0)
        p05 = getattr(mc_result, "p05_bankroll", 1.0)
        p95 = getattr(mc_result, "p95_bankroll", 1.0)
        lines.append(
            f"**MC (500 bets / 2000 paths):** "
            f"Ruin {ruin:.1%} | P50 {p50:.3f} | P5-P95 [{p05:.3f}–{p95:.3f}]"
        )

    # --- Reasoning ---
    if eval_reasoning:
        lines.append(f"\n**Evaluator:** {eval_reasoning}")

    # --- Quality warnings ---
    warnings: list[str] = state.get("quality_warnings") or []
    if warnings:
        lines.append("\n**Warnings:**")
        for w in warnings:
            lines.append(f"  ⚠ {w}")

    report = "\n".join(lines)
    return {"report": report}
