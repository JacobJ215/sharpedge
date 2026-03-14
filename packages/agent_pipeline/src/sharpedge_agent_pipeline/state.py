"""BettingAnalysisState TypedDict for the 9-node LangGraph pipeline.

This module defines the shared state that flows through the analysis graph.
quality_warnings uses Annotated[list[str], operator.add] so parallel nodes
can safely append warnings without clobbering each other's output.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from sharpedge_analytics.regime import RegimeClassification
from sharpedge_models.alpha import BettingAlpha
from sharpedge_models.monte_carlo import MonteCarloResult


class BettingAnalysisState(TypedDict, total=False):
    """Shared state for the BettingAnalysis LangGraph StateGraph.

    Keys are grouped by the node that writes them:
      - Inputs (provided at ainvoke): game_query, sport, user_id
      - fetch_context: game_context, regime_inputs
      - Parallel fan-out:
          detect_regime  → regime_result
          run_models     → ev_result
          calculate_ev   → mc_result
      - validate_setup: eval_verdict, eval_reasoning, retry_count
      - compose_alpha: alpha
      - size_position: kelly_fraction
      - generate_report / error_handler: report, error
      - Any node: quality_warnings (reducer = operator.add for parallel safety)
    """

    # --- Inputs ---
    game_query: str
    sport: str
    user_id: str

    # --- fetch_context outputs ---
    game_context: dict
    regime_inputs: dict

    # --- Parallel fan-out outputs (distinct keys — no collision) ---
    regime_result: RegimeClassification | None
    ev_result: dict | None
    mc_result: MonteCarloResult | None

    # --- validate_setup outputs ---
    eval_verdict: str
    eval_reasoning: str
    retry_count: int

    # --- compose_alpha / size_position outputs ---
    alpha: BettingAlpha | None
    kelly_fraction: float | None

    # --- Multi-writer accumulator (parallel-safe via operator.add) ---
    quality_warnings: Annotated[list[str], operator.add]

    # --- Terminal outputs ---
    report: str
    error: str | None
