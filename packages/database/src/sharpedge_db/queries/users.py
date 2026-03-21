"""Database queries for ``public.users``."""

from decimal import Decimal

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import User
from sharpedge_shared.constants import DEFAULT_UNIT_PERCENTAGE
from sharpedge_shared.types import Tier


def get_or_create_user(
    discord_id: str,
    discord_username: str | None = None,
) -> User:
    """Get an existing user or create a new one."""
    client = get_supabase_client()
    result = client.table("users").select("*").eq("discord_id", discord_id).execute()

    if result.data:
        return User(**result.data[0])

    new_user = {
        "discord_id": discord_id,
        "discord_username": discord_username,
        "tier": Tier.FREE,
        "bankroll": 0,
        "unit_size": 0,
    }
    result = client.table("users").insert(new_user).execute()
    return User(**result.data[0])


def get_user_by_discord_id(discord_id: str) -> User | None:
    """Get a user by their Discord ID."""
    client = get_supabase_client()
    result = client.table("users").select("*").eq("discord_id", discord_id).execute()
    if result.data:
        return User(**result.data[0])
    return None


def get_internal_user_id_by_supabase_auth(
    supabase_auth_id: str,
) -> str | None:
    """Return primary key of ``users`` for a Supabase Auth subject.

    Matches ``bets.user_id`` when logging wagers for that account.
    """
    client = get_supabase_client()
    result = (
        client.table("users")
        .select("id")
        .eq("supabase_auth_id", supabase_auth_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return str(row["id"])


def get_unit_size_for_user(internal_user_id: str) -> Decimal:
    """Dollar size of one unit for stake↔units math; ``0`` if unset."""
    client = get_supabase_client()
    result = client.table("users").select("unit_size").eq("id", internal_user_id).limit(1).execute()
    if not result.data:
        return Decimal("0")
    raw = result.data[0].get("unit_size")
    if raw is None:
        return Decimal("0")
    return Decimal(str(raw))


def update_user_tier(
    discord_id: str,
    tier: Tier,
    subscription_id: str | None = None,
) -> User:
    """Update a user's subscription tier."""
    client = get_supabase_client()
    update_data: dict = {"tier": tier}
    if subscription_id is not None:
        update_data["subscription_id"] = subscription_id

    result = client.table("users").update(update_data).eq("discord_id", discord_id).execute()
    return User(**result.data[0])


def update_bankroll(discord_id: str, bankroll: Decimal) -> User:
    """Update a user's bankroll and recalculate unit size."""
    unit_size = bankroll * Decimal(str(DEFAULT_UNIT_PERCENTAGE))
    client = get_supabase_client()
    result = (
        client.table("users")
        .update(
            {
                "bankroll": float(bankroll),
                "unit_size": float(unit_size),
            },
        )
        .eq("discord_id", discord_id)
        .execute()
    )
    return User(**result.data[0])
