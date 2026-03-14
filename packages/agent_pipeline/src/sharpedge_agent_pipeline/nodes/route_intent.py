"""route_intent node: classifies game_query into an intent category.

No LLM call — simple keyword heuristic. Under 60 lines.
"""
from __future__ import annotations


def route_intent(state: dict) -> dict:
    """Classify the game_query into intent: 'analyze' | 'copilot' | 'scan'.

    Heuristic rules (first match wins):
    - query contains '?' → copilot (question mode)
    - query contains 'scan' or 'all games' → scan (batch mode)
    - default → analyze (single-game deep analysis)

    Args:
        state: BettingAnalysisState with game_query set.

    Returns:
        Partial state dict with 'intent' key.
    """
    query = state.get("game_query", "").lower().strip()

    if "?" in query:
        intent = "copilot"
    elif "scan" in query or "all games" in query or "all " in query:
        intent = "scan"
    else:
        intent = "analyze"

    return {"intent": intent}
