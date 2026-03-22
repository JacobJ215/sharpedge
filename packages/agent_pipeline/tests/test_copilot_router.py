"""Soft router: COPILOT_ROUTER_FOCUS → tool subset + system addendum."""

from __future__ import annotations

from sharpedge_agent_pipeline.copilot.router import COPILOT_ROUTER_FOCUS_ENV, resolve_tool_subset
from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

_PM_EXPECTED = frozenset(
    {
        "get_prediction_market_edge",
        "scan_top_pm_edges",
        "check_pm_correlation",
        "get_venue_dislocation",
    }
)


def test_resolve_all_returns_full_tools_and_empty_addendum(monkeypatch) -> None:
    monkeypatch.delenv(COPILOT_ROUTER_FOCUS_ENV, raising=False)
    tools, addendum = resolve_tool_subset("all")
    assert len(tools) == len(COPILOT_TOOLS)
    assert addendum == ""


def test_resolve_pm_returns_strict_subset_and_addendum(monkeypatch) -> None:
    monkeypatch.delenv(COPILOT_ROUTER_FOCUS_ENV, raising=False)
    tools, addendum = resolve_tool_subset("pm")
    full_names = {t.name for t in COPILOT_TOOLS}
    got = {t.name for t in tools}
    assert got == _PM_EXPECTED & full_names
    assert len(got) < len(full_names)
    assert "pm" in addendum.lower()
    assert "Session focus" in addendum
