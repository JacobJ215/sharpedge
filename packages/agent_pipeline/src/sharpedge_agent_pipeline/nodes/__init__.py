"""Node callables for the BettingAnalysis LangGraph pipeline.

Exports all 9 node functions plus error_handler.
Each node receives the full BettingAnalysisState dict and returns a partial
state dict with only the keys it writes.
"""
from sharpedge_agent_pipeline.nodes.route_intent import route_intent
from sharpedge_agent_pipeline.nodes.fetch_context import fetch_context
from sharpedge_agent_pipeline.nodes.detect_regime import detect_regime
from sharpedge_agent_pipeline.nodes.run_models import run_models
from sharpedge_agent_pipeline.nodes.calculate_ev import calculate_ev
from sharpedge_agent_pipeline.nodes.validate_setup import validate_setup
from sharpedge_agent_pipeline.nodes.compose_alpha import compose_alpha
from sharpedge_agent_pipeline.nodes.size_position import size_position
from sharpedge_agent_pipeline.nodes.generate_report import generate_report


def error_handler(state: dict) -> dict:
    """Catch-all error handler node. Returns minimal error state."""
    error_msg = state.get("error") or "Unknown error in analysis pipeline"
    return {
        "report": f"Analysis failed: {error_msg}",
        "error": error_msg,
    }


__all__ = [
    "route_intent",
    "fetch_context",
    "detect_regime",
    "run_models",
    "calculate_ev",
    "validate_setup",
    "compose_alpha",
    "size_position",
    "generate_report",
    "error_handler",
]
