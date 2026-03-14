"""validate_setup node: LLM-powered bet setup quality evaluator.

Uses ChatOpenAI.with_structured_output(SetupEvalResult) to classify the
analysis signals as PASS / WARN / REJECT. This is the ONLY node that
calls an LLM. Under 100 lines.
"""
from __future__ import annotations

import logging
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("sharpedge.agent.validate_setup")


class SetupEvalResult(BaseModel):
    """Structured output from the validate_setup LLM evaluator."""

    verdict: Literal["PASS", "WARN", "REJECT"] = Field(
        description="PASS if bet setup is high quality, WARN if borderline, REJECT if invalid."
    )
    reasoning: str = Field(
        description="One to three sentence explanation of the verdict."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Evaluator confidence in this verdict (0.0–1.0)."
    )


_SYSTEM_PROMPT = """You are a sports betting quality evaluator. Given quantitative signals
from an analysis pipeline, decide whether the bet setup is ready to proceed.

Verdict rules:
- PASS: EV > 0, edge > 2%, ruin probability < 5%, regime is not PUBLIC_HEAVY
- WARN: borderline EV (0–2% edge) or ruin probability 5–10%
- REJECT: negative EV, ruin probability > 10%, or critically weak signals

Be concise and decisive. Return valid JSON only."""


def validate_setup(state: dict) -> dict:
    """Evaluate the bet setup using an LLM with structured output.

    Reads ev_result, regime_result, and mc_result from state. Calls
    ChatOpenAI(gpt-4o-mini) via with_structured_output(SetupEvalResult).

    Args:
        state: BettingAnalysisState with ev_result, regime_result, mc_result.

    Returns:
        Partial state dict with eval_verdict, eval_reasoning, retry_count.
    """
    ev_result: dict = state.get("ev_result") or {}
    regime_result = state.get("regime_result")
    mc_result = state.get("mc_result")
    current_retry: int = state.get("retry_count", 0)

    # Build signal summary for LLM
    regime_str = "UNKNOWN"
    regime_confidence = 0.0
    if regime_result is not None:
        regime_str = getattr(regime_result.regime, "value", str(regime_result.regime))
        regime_confidence = getattr(regime_result, "confidence", 0.0)

    ruin_prob = 0.0
    p50_bankroll = 1.0
    if mc_result is not None:
        ruin_prob = getattr(mc_result, "ruin_probability", 0.0)
        p50_bankroll = getattr(mc_result, "p50_bankroll", 1.0)

    user_message = (
        f"EV%: {ev_result.get('ev_percentage', 0):.2f}%, "
        f"Edge: {ev_result.get('edge', 0):.2f}%, "
        f"Model prob: {ev_result.get('model_prob', 50):.1f}%, "
        f"Prob edge positive: {ev_result.get('prob_edge_positive', 0):.2f}, "
        f"Regime: {regime_str} (confidence {regime_confidence:.2f}), "
        f"Ruin probability: {ruin_prob:.1%}, "
        f"P50 bankroll: {p50_bankroll:.3f}"
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    evaluator = llm.with_structured_output(SetupEvalResult)

    try:
        result: SetupEvalResult = evaluator.invoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ])
    except Exception as exc:
        logger.warning("validate_setup LLM call failed: %s — defaulting to WARN", exc)
        result = SetupEvalResult(
            verdict="WARN",
            reasoning=f"LLM evaluation failed ({exc}); defaulting to cautious WARN.",
            confidence=0.3,
        )

    # Increment retry_count only on WARN
    new_retry = current_retry + (1 if result.verdict == "WARN" else 0)

    return {
        "eval_verdict": result.verdict,
        "eval_reasoning": result.reasoning,
        "retry_count": new_retry,
    }
