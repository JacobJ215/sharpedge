"""Node callables for the BettingAnalysis LangGraph pipeline.

Exports all 9 node functions plus error_handler.
Each node receives the full BettingAnalysisState dict and returns a partial
state dict with only the keys it writes.
"""

from sharpedge_agent_pipeline.nodes.calculate_ev import calculate_ev
from sharpedge_agent_pipeline.nodes.compose_alpha import compose_alpha
from sharpedge_agent_pipeline.nodes.detect_regime import detect_regime
from sharpedge_agent_pipeline.nodes.fetch_context import fetch_context
from sharpedge_agent_pipeline.nodes.generate_report import generate_report
from sharpedge_agent_pipeline.nodes.route_intent import route_intent
from sharpedge_agent_pipeline.nodes.run_models import run_models
from sharpedge_agent_pipeline.nodes.size_position import size_position
from sharpedge_agent_pipeline.nodes.validate_setup import validate_setup


def error_handler(state: dict) -> dict:
    """Catch-all error handler node. Returns minimal error state."""
    error_msg = state.get("error") or "Unknown error in analysis pipeline"
    return {
        "report": f"Analysis failed: {error_msg}",
        "error": error_msg,
    }


__all__ = [
    "calculate_ev",
    "compose_alpha",
    "detect_regime",
    "error_handler",
    "fetch_context",
    "generate_report",
    "route_intent",
    "run_models",
    "size_position",
    "validate_setup",
]
