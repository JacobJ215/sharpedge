"""Queries for the injuries table (player availability)."""

from __future__ import annotations

import re
from typing import Any

from sharpedge_db.client import get_supabase_client

_MAX_ROWS = 150
_NOTABLE_STATUS = frozenset(
    {"OUT", "DOUBTFUL", "QUESTIONABLE", "PROBABLE", "IR"},
)


def teams_from_game_label(game: str) -> list[str]:
    """Split labels like 'Lakers vs Warriors' into two team strings."""
    if not game or not str(game).strip():
        return []
    s = str(game).strip()
    parts = re.split(
        r"\s+vs\.?\s+|\s+@\s+|\s+at\s+|\s+—\s+",
        s,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    if len(parts) != 2:
        return []
    return [parts[0].strip(), parts[1].strip()]


def _team_overlap(game_team: str, injury_team: str) -> bool:
    a = game_team.casefold().strip()
    b = injury_team.casefold().strip()
    if not a or not b:
        return False
    return a in b or b in a


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    ir = row.get("impact_rating")
    return {
        "team": row.get("team"),
        "player_name": row.get("player_name"),
        "position": row.get("position"),
        "status": row.get("status"),
        "injury_type": row.get("injury_type"),
        "is_key_player": bool(row.get("is_key_player")),
        "impact_rating": float(ir) if ir is not None else None,
    }


def get_injuries_for_game_label(
    game_label: str,
    sport: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return injury rows for teams inferred from a value-play game label."""
    teams = teams_from_game_label(game_label)
    if not teams:
        return []
    sport_key = sport.strip().upper() if sport else ""
    if not sport_key:
        return []

    client = get_supabase_client()
    cols = (
        "team, player_name, position, status, injury_type, "
        "is_key_player, impact_rating"
    )
    res = (
        client.table("injuries")
        .select(cols)
        .eq("sport", sport_key)
        .limit(_MAX_ROWS)
        .execute()
    )
    raw = res.data or []
    matched: list[dict[str, Any]] = []
    for row in raw:
        st = str(row.get("status") or "").strip().upper()
        if st not in _NOTABLE_STATUS:
            continue
        db_team = str(row.get("team") or "")
        if not any(_team_overlap(g, db_team) for g in teams):
            continue
        matched.append(row)

    def _sort_key(r: dict[str, Any]) -> tuple[bool, float]:
        kp = bool(r.get("is_key_player"))
        ir = r.get("impact_rating")
        ir_f = float(ir) if ir is not None else 0.0
        return (not kp, -ir_f)

    matched.sort(key=_sort_key)
    return [_serialize(r) for r in matched[:limit]]
