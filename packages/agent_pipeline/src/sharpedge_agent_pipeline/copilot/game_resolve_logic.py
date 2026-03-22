"""Odds API game listing and resolution for BettingCopilot (no @tool — called from tools.py)."""

from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Any

from sharpedge_odds.client import OddsClient
from sharpedge_odds.constants import SPORT_KEYS
from sharpedge_odds.models import Game
from sharpedge_shared.errors import ExternalAPIError

from sharpedge_agent_pipeline.copilot.compare_books_logic import _sport_from_string


def _game_to_dict(game: Game, sport_code: str) -> dict[str, Any]:
    return {
        "game_id": game.id,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "commence_time": game.commence_time.isoformat(),
        "sport": sport_code,
        "sport_title": game.sport_title,
    }


def _normalize_query(q: str) -> str:
    return q.lower().replace("-", " ").replace("vs", " ").strip()


def _score_game_query(game: Game, query_normalized: str) -> float:
    game_str = f"{game.home_team} {game.away_team}".lower()
    score = SequenceMatcher(None, query_normalized, game_str).ratio()
    for team in (game.home_team, game.away_team):
        score = max(score, SequenceMatcher(None, query_normalized, team.lower()).ratio())
    return score


def search_games_impl(
    sport: str,
    query: str | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """List upcoming games for a sport; optional case-insensitive substring filter on team names."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        return {
            "error": "ODDS_API_KEY is not set — game search is unavailable.",
            "games": [],
            "count": 0,
        }

    sport_enum = _sport_from_string(sport)
    if sport_enum is None:
        supported = ", ".join(sorted(s.name for s in SPORT_KEYS))
        return {
            "error": f"Unsupported sport '{sport}'. Use one of: {supported}",
            "games": [],
            "count": 0,
        }

    redis_url = (os.environ.get("REDIS_URL") or "").strip()
    client = OddsClient(api_key=api_key, redis_url=redis_url)
    try:
        games = client.get_odds(sport_enum)
    except ExternalAPIError as e:
        return {"error": str(e), "games": [], "count": 0}
    except Exception as e:
        return {"error": str(e), "games": [], "count": 0}
    finally:
        try:
            client.close()
        except Exception:
            pass

    q = (query or "").strip()
    if q:
        ql = q.lower()
        games = [
            g
            for g in games
            if ql in g.home_team.lower()
            or ql in g.away_team.lower()
            or ql in f"{g.away_team} {g.home_team}".lower()
        ]

    games = sorted(games, key=lambda g: g.commence_time)[: max(1, min(limit, 25))]

    out = [_game_to_dict(g, sport_enum.name) for g in games]
    return {"games": out, "count": len(out)}


def resolve_game_impl(sport: str, query: str) -> dict[str, Any]:
    """Resolve natural language to a single game when possible; else return ranked candidates.

    Uses OddsClient.find_game first (fuzzy). If no match, scores all games in the sport
    and returns either one clear winner or up to 5 ambiguous candidates.
    """
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        return {
            "error": "ODDS_API_KEY is not set — game resolution is unavailable.",
            "game": None,
            "candidates": [],
        }

    sport_enum = _sport_from_string(sport)
    if sport_enum is None:
        supported = ", ".join(sorted(s.name for s in SPORT_KEYS))
        return {
            "error": f"Unsupported sport '{sport}'. Use one of: {supported}",
            "game": None,
            "candidates": [],
        }

    q_raw = (query or "").strip()
    if not q_raw:
        return {
            "error": "query is required (e.g. team names or 'Lakers').",
            "game": None,
            "candidates": [],
        }

    redis_url = (os.environ.get("REDIS_URL") or "").strip()
    client = OddsClient(api_key=api_key, redis_url=redis_url)
    try:
        game = client.find_game(q_raw, sport_enum)
        if game is not None:
            return {
                "game": _game_to_dict(game, sport_enum.name),
                "candidates": [],
                "ambiguous": False,
            }

        games = client.get_odds(sport_enum)
        qn = _normalize_query(q_raw)
        scored = sorted(
            ((g, _score_game_query(g, qn)) for g in games),
            key=lambda x: -x[1],
        )
        strong = [(g, s) for g, s in scored if s >= 0.35][:5]
        if not strong:
            return {
                "game": None,
                "candidates": [],
                "error": f"No game matched query {q_raw!r} for {sport_enum.name}.",
            }

        if len(strong) == 1:
            g, _ = strong[0]
            return {
                "game": _game_to_dict(g, sport_enum.name),
                "candidates": [],
                "ambiguous": False,
            }

        best_s, second_s = strong[0][1], strong[1][1]
        if best_s >= 0.5 and (best_s - second_s) >= 0.08:
            return {
                "game": _game_to_dict(strong[0][0], sport_enum.name),
                "candidates": [],
                "ambiguous": False,
            }

        cand = [_game_to_dict(g, sport_enum.name) for g, _ in strong]
        return {
            "game": None,
            "candidates": cand,
            "ambiguous": True,
            "note": "Multiple games matched; ask the user to pick a game_id or narrow the query.",
        }
    except ExternalAPIError as e:
        return {"error": str(e), "game": None, "candidates": []}
    except Exception as e:
        return {"error": str(e), "game": None, "candidates": []}
    finally:
        try:
            client.close()
        except Exception:
            pass
