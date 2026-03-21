from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import Projection
from sharpedge_shared.types import Sport


def upsert_projection(
    game_id: str,
    sport: Sport,
    home_team: str,
    away_team: str,
    projected_spread: float,
    projected_total: float,
    spread_confidence: float,
    total_confidence: float,
    game_time: str | None = None,
) -> Projection:
    """Insert or update a model projection for a game."""
    client = get_supabase_client()
    data = {
        "game_id": game_id,
        "sport": sport,
        "home_team": home_team,
        "away_team": away_team,
        "projected_spread": projected_spread,
        "projected_total": projected_total,
        "spread_confidence": spread_confidence,
        "total_confidence": total_confidence,
    }
    if game_time:
        data["game_time"] = game_time

    result = client.table("projections").upsert(data, on_conflict="game_id").execute()
    return Projection(**result.data[0])


def get_projection(game_id: str) -> Projection | None:
    """Get the projection for a specific game."""
    client = get_supabase_client()
    result = client.table("projections").select("*").eq("game_id", game_id).execute()
    if result.data:
        return Projection(**result.data[0])
    return None


def get_projections_by_sport(sport: Sport) -> list[Projection]:
    """Get all projections for a given sport."""
    client = get_supabase_client()
    result = client.table("projections").select("*").eq("sport", sport).order("game_time").execute()
    return [Projection(**row) for row in result.data]
