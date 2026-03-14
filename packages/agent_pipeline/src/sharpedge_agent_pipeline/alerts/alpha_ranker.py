"""Alpha-based ranking for value play alerts.

Sorts value plays by composite alpha score (highest first).
Plays with alpha_score=None fall to the end via 0.0 fallback.
"""

from __future__ import annotations

from typing import Any


def rank_by_alpha(plays: list[Any]) -> list[Any]:
    """Sort value plays by alpha_score descending.

    Args:
        plays: List of ValuePlay objects or dicts with an ``alpha_score`` attribute/key.
               Objects with ``alpha_score=None`` are treated as 0.0 and sort last.

    Returns:
        A new list sorted by alpha_score descending (original list is not mutated).
    """
    def _score(play: Any) -> float:
        if isinstance(play, dict):
            val = play.get("alpha_score")
        else:
            val = getattr(play, "alpha_score", None)
        return val if val is not None else 0.0

    return sorted(plays, key=_score, reverse=True)
