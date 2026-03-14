"""LangGraph StateGraph factory for the 9-node BettingAnalysis pipeline.

Build the graph once at module import via ANALYSIS_GRAPH singleton.

IMPORTANT: Use config={'recursion_limit': 25} at ainvoke() time — NOT in compile().
Example:
    result = await ANALYSIS_GRAPH.ainvoke(state, config={"recursion_limit": 25})
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, START, END

from sharpedge_agent_pipeline.state import BettingAnalysisState
from sharpedge_agent_pipeline.nodes import (
    route_intent,
    fetch_context,
    detect_regime,
    run_models,
    calculate_ev,
    validate_setup,
    compose_alpha,
    size_position,
    generate_report,
    error_handler,
)


def _route_after_validation(
    state: dict,
) -> Literal["compose_alpha", "fetch_context", "generate_report"]:
    """Conditional router called after validate_setup.

    Logic:
    - PASS  → compose_alpha
    - WARN + retry_count < 2  → fetch_context (re-analyze)
    - WARN + retry_count >= 2 → compose_alpha  (loop guard — force forward)
    - REJECT → generate_report (skip composition)
    """
    verdict = state.get("eval_verdict", "PASS")
    retry_count = state.get("retry_count", 0)

    if verdict == "REJECT":
        return "generate_report"
    if verdict == "WARN" and retry_count < 2:
        return "fetch_context"
    # PASS or (WARN + retry_count >= 2)
    return "compose_alpha"


def build_analysis_graph() -> StateGraph:
    """Build and compile the 9-node BettingAnalysis StateGraph.

    Graph topology:
        START → route_intent → fetch_context
        fetch_context → detect_regime   (parallel)
        fetch_context → run_models      (parallel)
        fetch_context → calculate_ev    (parallel)
        detect_regime  → validate_setup (fan-in)
        run_models     → validate_setup (fan-in)
        calculate_ev   → validate_setup (fan-in)
        validate_setup → [compose_alpha | fetch_context | generate_report]
        compose_alpha → size_position → generate_report → END
        error_handler → END
    """
    builder = StateGraph(BettingAnalysisState)

    # --- Add all nodes ---
    builder.add_node("route_intent", route_intent)
    builder.add_node("fetch_context", fetch_context)
    builder.add_node("detect_regime", detect_regime)
    builder.add_node("run_models", run_models)
    builder.add_node("calculate_ev", calculate_ev)
    builder.add_node("validate_setup", validate_setup)
    builder.add_node("compose_alpha", compose_alpha)
    builder.add_node("size_position", size_position)
    builder.add_node("generate_report", generate_report)
    builder.add_node("error_handler", error_handler)

    # --- Entry point ---
    builder.add_edge(START, "route_intent")
    builder.add_edge("route_intent", "fetch_context")

    # --- Parallel fan-out from fetch_context ---
    builder.add_edge("fetch_context", "detect_regime")
    builder.add_edge("fetch_context", "run_models")
    builder.add_edge("fetch_context", "calculate_ev")

    # --- Fan-in: all 3 parallel nodes → validate_setup ---
    builder.add_edge("detect_regime", "validate_setup")
    builder.add_edge("run_models", "validate_setup")
    builder.add_edge("calculate_ev", "validate_setup")

    # --- Conditional routing after validation ---
    builder.add_conditional_edges(
        "validate_setup",
        _route_after_validation,
        {
            "compose_alpha": "compose_alpha",
            "fetch_context": "fetch_context",
            "generate_report": "generate_report",
        },
    )

    # --- Sequential tail ---
    builder.add_edge("compose_alpha", "size_position")
    builder.add_edge("size_position", "generate_report")
    builder.add_edge("generate_report", END)

    # --- Error handler ---
    builder.add_edge("error_handler", END)

    # Compile without recursion_limit (pass it in ainvoke config instead)
    return builder.compile()


# Module-level singleton — built once at import time
ANALYSIS_GRAPH = build_analysis_graph()
