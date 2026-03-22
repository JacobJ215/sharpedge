"""Soft router: ``COPILOT_ROUTER_FOCUS`` env → filtered tool list + system addendum.

Wave 1 does not add LangGraph subgraphs; it only restricts ``bind_tools`` and
injects a short focus line into the system prompt.
"""

from __future__ import annotations

import os

from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

# Env var read by :func:`resolve_tool_subset` when ``env_focus`` is ``None``.
COPILOT_ROUTER_FOCUS_ENV = "COPILOT_ROUTER_FOCUS"

_SPORTS_NAMES = frozenset(
    {
        "analyze_game",
        "search_value_plays",
        "check_line_movement",
        "get_sharp_indicators",
        "search_games",
        "resolve_game",
        "compare_books",
        "get_model_predictions",
        "get_injury_report",
    }
)

_PM_NAMES = frozenset(
    {
        "get_prediction_market_edge",
        "scan_top_pm_edges",
        "check_pm_correlation",
        "get_venue_dislocation",
    }
)

_PORTFOLIO_NAMES = frozenset(
    {
        "get_active_bets",
        "get_portfolio_stats",
        "estimate_bankroll_risk",
        "get_user_exposure",
        "compute_kelly",
    }
)

_FOCUS_ALLOWLISTS: dict[str, frozenset[str]] = {
    "sports": _SPORTS_NAMES,
    "pm": _PM_NAMES,
    "portfolio": _PORTFOLIO_NAMES,
}

_FOCUS_ALIASES = {
    "": "all",
    "all": "all",
    "*": "all",
    "default": "all",
}


def resolve_tool_subset(env_focus: str | None = None) -> tuple[list, str]:
    """Return ``(tools, system_addendum)`` for the given or env-configured focus.

    ``COPILOT_ROUTER_FOCUS`` values: ``all`` (default), ``sports``, ``pm``,
    ``portfolio``. Unknown values fall back to full ``COPILOT_TOOLS`` with no
    addendum (same as ``all``).

    Args:
        env_focus: If set, use this focus instead of reading
            ``os.environ[COPILOT_ROUTER_FOCUS_ENV]``.

    Returns:
        Filtered tool list (preserving order from ``COPILOT_TOOLS``) and a short
        system addendum (empty when focus is ``all`` or unrecognized).
    """
    raw = env_focus if env_focus is not None else os.environ.get(COPILOT_ROUTER_FOCUS_ENV, "all")
    focus = (raw or "all").strip().lower()
    focus = _FOCUS_ALIASES.get(focus, focus)

    if focus == "all" or focus not in _FOCUS_ALLOWLISTS:
        return list(COPILOT_TOOLS), ""

    allowed = _FOCUS_ALLOWLISTS[focus]
    tools = [t for t in COPILOT_TOOLS if getattr(t, "name", "") in allowed]
    names_sorted = ", ".join(sorted(allowed))
    addendum = (
        f"Session focus: **{focus}**. Available tools in this mode: {names_sorted}. "
        "Prefer these tools; if the user clearly needs another domain, say so briefly."
    )
    return tools, addendum
