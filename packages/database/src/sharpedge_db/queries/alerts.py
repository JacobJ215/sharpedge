from datetime import datetime, timezone

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import Alert
from sharpedge_shared.types import AlertType


def record_alert(
    user_id: str,
    alert_type: AlertType,
    game_id: str | None = None,
    content: str | None = None,
) -> Alert:
    """Record an alert that was delivered to a user."""
    client = get_supabase_client()
    data: dict = {
        "user_id": user_id,
        "alert_type": alert_type,
    }
    if game_id:
        data["game_id"] = game_id
    if content:
        data["content"] = content

    result = client.table("alerts").insert(data).execute()
    return Alert(**result.data[0])


def get_alerts_count(
    user_id: str,
    alert_type: AlertType,
    since: datetime,
) -> int:
    """Count alerts delivered to a user since a given time."""
    client = get_supabase_client()
    result = (
        client.table("alerts")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("alert_type", alert_type)
        .gte("delivered_at", since.isoformat())
        .execute()
    )
    return result.count or 0
