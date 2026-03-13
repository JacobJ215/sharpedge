"""Seed development data for testing."""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure packages are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "shared", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "database", "src"))

from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import BetResult, BetType, Sport, Tier


def seed() -> None:
    """Seed the database with test data."""
    client = get_supabase_client()

    # Create test users
    users = [
        {
            "discord_id": "111111111111111111",
            "discord_username": "TestUser_Free",
            "tier": Tier.FREE,
            "bankroll": 0,
            "unit_size": 0,
        },
        {
            "discord_id": "222222222222222222",
            "discord_username": "TestUser_Pro",
            "tier": Tier.PRO,
            "bankroll": 5000,
            "unit_size": 50,
        },
        {
            "discord_id": "333333333333333333",
            "discord_username": "TestUser_Sharp",
            "tier": Tier.SHARP,
            "bankroll": 10000,
            "unit_size": 100,
        },
    ]

    for user_data in users:
        result = (
            client.table("users")
            .upsert(user_data, on_conflict="discord_id")
            .execute()
        )
        print(f"Seeded user: {user_data['discord_username']} ({user_data['tier']})")

    # Get Pro user ID for sample bets
    pro_user = (
        client.table("users")
        .select("id")
        .eq("discord_id", "222222222222222222")
        .execute()
    )
    if not pro_user.data:
        print("Pro user not found, skipping bets.")
        return

    pro_id = pro_user.data[0]["id"]
    now = datetime.now(timezone.utc)

    # Create sample bets
    sample_bets = [
        {
            "user_id": pro_id,
            "sport": Sport.NFL,
            "game": "Chiefs vs Raiders",
            "bet_type": BetType.SPREAD,
            "selection": "Chiefs -3",
            "odds": -110,
            "units": 2.0,
            "stake": 100.0,
            "potential_win": 90.91,
            "result": BetResult.WIN,
            "profit": 90.91,
            "sportsbook": "FanDuel",
            "created_at": (now - timedelta(days=5)).isoformat(),
            "settled_at": (now - timedelta(days=5)).isoformat(),
        },
        {
            "user_id": pro_id,
            "sport": Sport.NFL,
            "game": "Packers vs Bears",
            "bet_type": BetType.SPREAD,
            "selection": "Packers -3.5",
            "odds": -105,
            "units": 1.5,
            "stake": 75.0,
            "potential_win": 71.43,
            "result": BetResult.LOSS,
            "profit": -75.0,
            "sportsbook": "DraftKings",
            "created_at": (now - timedelta(days=4)).isoformat(),
            "settled_at": (now - timedelta(days=4)).isoformat(),
        },
        {
            "user_id": pro_id,
            "sport": Sport.NBA,
            "game": "Lakers vs Celtics",
            "bet_type": BetType.TOTAL,
            "selection": "Over 215.5",
            "odds": -110,
            "units": 1.0,
            "stake": 50.0,
            "potential_win": 45.45,
            "result": BetResult.WIN,
            "profit": 45.45,
            "sportsbook": "BetMGM",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "settled_at": (now - timedelta(days=3)).isoformat(),
        },
        {
            "user_id": pro_id,
            "sport": Sport.NBA,
            "game": "Warriors vs Suns",
            "bet_type": BetType.MONEYLINE,
            "selection": "Warriors ML",
            "odds": 150,
            "units": 1.0,
            "stake": 50.0,
            "potential_win": 75.0,
            "result": BetResult.PENDING,
            "sportsbook": "Caesars",
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
    ]

    for bet_data in sample_bets:
        client.table("bets").insert(bet_data).execute()
        print(f"Seeded bet: {bet_data['selection']} ({bet_data['result']})")

    print("\nSeed complete!")


if __name__ == "__main__":
    seed()
