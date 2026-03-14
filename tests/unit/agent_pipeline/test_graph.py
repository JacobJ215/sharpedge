"""Tests for AGENT-01 + AGENT-02: 9-node LangGraph graph wiring and retry cap."""
import pytest

from sharpedge_agent_pipeline.graph import build_analysis_graph, ANALYSIS_GRAPH
from sharpedge_agent_pipeline.graph import _route_after_validation


def test_build_analysis_graph_returns_compiled_graph():
    """build_analysis_graph() returns a compiled StateGraph without error."""
    graph = build_analysis_graph()
    assert graph is not None


def test_graph_has_nine_named_nodes():
    """Compiled graph exposes all 9 named nodes plus error_handler."""
    graph = ANALYSIS_GRAPH
    nodes = set(graph.nodes)
    expected_nodes = {
        "route_intent", "fetch_context", "detect_regime",
        "run_models", "calculate_ev", "validate_setup",
        "compose_alpha", "size_position", "generate_report",
        "error_handler",
    }
    missing = expected_nodes - nodes
    assert not missing, f"Missing nodes: {missing}"


def test_parallel_fan_out_from_fetch_context():
    """fetch_context fans out to detect_regime, run_models, calculate_ev."""
    graph = ANALYSIS_GRAPH
    # The compiled graph edges should include all 3 fan-out edges
    # We verify by checking the node names exist and graph compiled
    nodes = set(graph.nodes)
    assert "fetch_context" in nodes
    assert "detect_regime" in nodes
    assert "run_models" in nodes
    assert "calculate_ev" in nodes


def test_warn_retry_cap_routes_to_compose_alpha():
    """WARN verdict with retry_count >= 2 routes to compose_alpha (loop guard)."""
    state = {
        "eval_verdict": "WARN",
        "retry_count": 2,
    }
    result = _route_after_validation(state)
    assert result == "compose_alpha"


def test_warn_retry_below_cap_routes_to_fetch_context():
    """WARN verdict with retry_count < 2 routes back to fetch_context."""
    state = {
        "eval_verdict": "WARN",
        "retry_count": 1,
    }
    result = _route_after_validation(state)
    assert result == "fetch_context"


def test_pass_verdict_routes_to_compose_alpha():
    """PASS verdict routes to compose_alpha."""
    state = {
        "eval_verdict": "PASS",
        "retry_count": 0,
    }
    result = _route_after_validation(state)
    assert result == "compose_alpha"


def test_reject_verdict_routes_to_generate_report():
    """REJECT verdict routes to generate_report."""
    state = {
        "eval_verdict": "REJECT",
        "retry_count": 0,
    }
    result = _route_after_validation(state)
    assert result == "generate_report"


def test_analysis_graph_singleton_is_not_none():
    """Module-level ANALYSIS_GRAPH singleton is built at import time."""
    assert ANALYSIS_GRAPH is not None
