"""The Odds API multi-book line comparison for BettingCopilot (no @tool — called from tools.py)."""

from __future__ import annotations

import os
from typing import Any

from sharpedge_odds.client import OddsClient
from sharpedge_odds.constants import SPORT_KEYS
from sharpedge_odds.models import FormattedLine, LineComparison
from sharpedge_shared.errors import ExternalAPIError
from sharpedge_shared.types import Sport

_MAX_LINES_PER_SIDE = 8


def _sport_from_string(sport: str) -> Sport | None:
    key = (sport or "").strip().upper()
    if not key:
        return None
    try:
        s = Sport[key]
    except KeyError:
        return None
    if s not in SPORT_KEYS:
        return None
    return s


def _line_to_dict(fl: FormattedLine) -> dict[str, Any]:
    return {
        "sportsbook": fl.sportsbook,
        "sportsbook_display": fl.sportsbook_display,
        "side": fl.side,
        "line": fl.line,
        "odds": fl.odds,
        "is_best": fl.is_best,
    }


def _cap_side(lines: list[FormattedLine]) -> list[dict[str, Any]]:
    return [_line_to_dict(fl) for fl in lines[:_MAX_LINES_PER_SIDE]]


def comparison_to_dict(comp: LineComparison) -> dict[str, Any]:
    ct = comp.commence_time
    commence = ct.isoformat() if ct is not None else None
    return {
        "game_id": comp.game_id,
        "home_team": comp.home_team,
        "away_team": comp.away_team,
        "commence_time": commence,
        "spread_home": _cap_side(comp.spread_home),
        "spread_away": _cap_side(comp.spread_away),
        "total_over": _cap_side(comp.total_over),
        "total_under": _cap_side(comp.total_under),
        "moneyline_home": _cap_side(comp.moneyline_home),
        "moneyline_away": _cap_side(comp.moneyline_away),
    }


def run_compare_books(
    game_id: str = "",
    sport: str = "NBA",
    game_query: str = "",
) -> dict[str, Any]:
    """Return multi-book comparison dict or structured error / unavailable_reason."""
    flag = (os.environ.get("COPILOT_COMPARE_BOOKS") or "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return {
            "unavailable_reason": "disabled",
            "note": "Book comparison is disabled (COPILOT_COMPARE_BOOKS).",
            "books": [],
        }

    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        return {
            "unavailable_reason": "missing_api_key",
            "note": "ODDS_API_KEY is not set — book comparison is unavailable.",
            "books": [],
        }

    sport_enum = _sport_from_string(sport)
    if sport_enum is None:
        supported = ", ".join(sorted(s.name for s in SPORT_KEYS))
        return {
            "error": f"Unsupported sport '{sport}'. Use one of: {supported}",
            "books": [],
        }

    gq = (game_query or "").strip()
    gid = (game_id or "").strip()
    if not gq and not gid:
        return {
            "error": "Provide game_query (team names) and sport, or the Odds API event id as game_id.",
            "hint": "Example game_query: 'Lakers Celtics' with sport NBA.",
            "books": [],
        }

    redis_url = (os.environ.get("REDIS_URL") or "").strip()
    client = OddsClient(api_key=api_key, redis_url=redis_url)

    try:
        game = None
        if gq:
            game = client.find_game(gq, sport_enum)
            if game is None:
                return {
                    "error": f"No game matched query '{gq}' for sport {sport_enum.name}.",
                    "hint": "Try different team spellings or pass the Odds API event id as game_id.",
                    "books": [],
                }
        else:
            games = client.get_odds(sport_enum)
            game = next((g for g in games if g.id == gid), None)
            if game is None:
                return {
                    "error": f"No game with Odds API id '{gid}' in current {sport_enum.name} slate.",
                    "hint": "Use game_query with team names, or verify the event id from The Odds API.",
                    "books": [],
                }

        comparison = client.get_line_comparison(game)
        payload = comparison_to_dict(comparison)
        payload["note"] = "Lines from The Odds API; is_best flags are per side within each market."
        return payload
    except ExternalAPIError as e:
        return {"error": str(e), "books": []}
    except Exception as e:
        return {"error": str(e), "books": []}
    finally:
        try:
            client.close()
        except Exception:
            pass
