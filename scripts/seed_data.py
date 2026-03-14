"""Seed development data for testing."""

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Ensure packages are importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "packages", "shared", "src"),
)
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "packages", "database", "src"
    ),
)

from sharpedge_db.client import get_supabase_client  # noqa: E402
from sharpedge_shared.types import (  # noqa: E402
    BetResult,
    BetType,
    Sport,
    Tier,
)


def seed() -> None:
    """Seed the database with test data."""
    try:
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
            if not result.data:
                print(
                    f"WARNING: Upsert may have failed for "
                    f"{user_data['discord_username']}"
                )
            else:
                print(
                    f"Seeded user: {user_data['discord_username']} "
                    f"({user_data['tier']})"
                )

        # Get Pro user ID for sample bets
        pro_user = (
            client.table("users")
            .select("id")
            .eq("discord_id", "222222222222222222")
            .execute()
        )
        if not pro_user.data:
            print("ERROR: Pro user not found after upsert — seed aborted.")
            sys.exit(1)

        pro_id = pro_user.data[0]["id"]
        now = datetime.now(timezone.utc)

        # Remove existing test bets before re-seeding to prevent duplicates.
        client.table("bets").delete().eq("user_id", pro_id).execute()

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
                "settled_at": (now - timedelta(days=4, hours=20)).isoformat(),
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
                "settled_at": (now - timedelta(days=3, hours=20)).isoformat(),
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
                "settled_at": (now - timedelta(days=2, hours=20)).isoformat(),
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

        # ── Value Plays ──────────────────────────────────────────────────
        # Clear existing seeded value plays first
        client.table("value_plays").delete().eq("sportsbook", "FanDuel").execute()
        client.table("value_plays").delete().eq("sportsbook", "DraftKings").execute()
        client.table("value_plays").delete().eq("sportsbook", "BetMGM").execute()
        client.table("value_plays").delete().eq("sportsbook", "Caesars").execute()
        client.table("value_plays").delete().eq("sportsbook", "PointsBet").execute()

        sample_value_plays = [
            {
                "game_id": "seed_nfl_001",
                "game": "Chiefs vs Raiders",
                "sport": Sport.NFL,
                "bet_type": BetType.SPREAD,
                "side": "Chiefs -3",
                "sportsbook": "FanDuel",
                "market_odds": -108,
                "implied_probability": 0.5192,
                "model_probability": 0.5510,
                "fair_odds": -115,
                "edge_percentage": 3.2,
                "ev_percentage": 5.8,
                "confidence": "high",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=6)).isoformat(),
            },
            {
                "game_id": "seed_nba_001",
                "game": "Lakers vs Celtics",
                "sport": Sport.NBA,
                "bet_type": BetType.TOTAL,
                "side": "Over 225.5",
                "sportsbook": "DraftKings",
                "market_odds": -105,
                "implied_probability": 0.5122,
                "model_probability": 0.5390,
                "fair_odds": -112,
                "edge_percentage": 2.8,
                "ev_percentage": 4.1,
                "confidence": "high",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=3)).isoformat(),
            },
            {
                "game_id": "seed_nfl_002",
                "game": "Packers vs Bears",
                "sport": Sport.NFL,
                "bet_type": BetType.MONEYLINE,
                "side": "Packers ML",
                "sportsbook": "BetMGM",
                "market_odds": 138,
                "implied_probability": 0.4202,
                "model_probability": 0.4440,
                "fair_odds": 125,
                "edge_percentage": 2.1,
                "ev_percentage": 3.6,
                "confidence": "medium",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=10)).isoformat(),
            },
            {
                "game_id": "seed_nba_002",
                "game": "Warriors vs Suns",
                "sport": Sport.NBA,
                "bet_type": BetType.SPREAD,
                "side": "Suns +5.5",
                "sportsbook": "Caesars",
                "market_odds": -106,
                "implied_probability": 0.5146,
                "model_probability": 0.5380,
                "fair_odds": -114,
                "edge_percentage": 2.4,
                "ev_percentage": 3.2,
                "confidence": "medium",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=5)).isoformat(),
            },
            {
                "game_id": "seed_nhl_001",
                "game": "Bruins vs Rangers",
                "sport": Sport.NHL,
                "bet_type": BetType.MONEYLINE,
                "side": "Rangers ML",
                "sportsbook": "PointsBet",
                "market_odds": 155,
                "implied_probability": 0.3922,
                "model_probability": 0.4120,
                "fair_odds": 140,
                "edge_percentage": 1.9,
                "ev_percentage": 2.8,
                "confidence": "medium",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=8)).isoformat(),
            },
            {
                "game_id": "seed_nfl_003",
                "game": "Cowboys vs Eagles",
                "sport": Sport.NFL,
                "bet_type": BetType.SPREAD,
                "side": "Eagles -2.5",
                "sportsbook": "FanDuel",
                "market_odds": -112,
                "implied_probability": 0.5283,
                "model_probability": 0.5450,
                "fair_odds": -120,
                "edge_percentage": 1.6,
                "ev_percentage": 2.4,
                "confidence": "low",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=12)).isoformat(),
            },
            {
                "game_id": "seed_nba_003",
                "game": "Bucks vs Heat",
                "sport": Sport.NBA,
                "bet_type": BetType.TOTAL,
                "side": "Under 218.5",
                "sportsbook": "DraftKings",
                "market_odds": -108,
                "implied_probability": 0.5192,
                "model_probability": 0.5330,
                "fair_odds": -115,
                "edge_percentage": 1.4,
                "ev_percentage": 2.1,
                "confidence": "low",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=4)).isoformat(),
            },
            {
                "game_id": "seed_mlb_001",
                "game": "Yankees vs Red Sox",
                "sport": Sport.MLB,
                "bet_type": BetType.MONEYLINE,
                "side": "Red Sox ML",
                "sportsbook": "BetMGM",
                "market_odds": 118,
                "implied_probability": 0.4587,
                "model_probability": 0.4780,
                "fair_odds": 108,
                "edge_percentage": 1.8,
                "ev_percentage": 2.9,
                "confidence": "medium",
                "is_active": True,
                "game_start_time": (now + timedelta(hours=7)).isoformat(),
            },
        ]

        for vp in sample_value_plays:
            client.table("value_plays").insert(vp).execute()
            print(f"Seeded value play: {vp['side']} @ {vp['sportsbook']} ({vp['ev_percentage']:.1f}% EV)")

        # ── Arbitrage Opportunities ──────────────────────────────────────
        client.table("arbitrage_opportunities").delete().eq("book_a", "FanDuel").execute()
        client.table("arbitrage_opportunities").delete().eq("book_a", "DraftKings").execute()

        sample_arbs = [
            {
                "game_id": "seed_nfl_arb_001",
                "game": "Chiefs vs Raiders",
                "sport": Sport.NFL,
                "bet_type": BetType.SPREAD,
                "book_a": "FanDuel",
                "side_a": "Chiefs -3",
                "odds_a": -105,
                "stake_a_percentage": 51.2,
                "book_b": "DraftKings",
                "side_b": "Raiders +3",
                "odds_b": -108,
                "stake_b_percentage": 48.8,
                "profit_percentage": 1.42,
                "total_implied": 0.9858,
                "is_active": True,
            },
            {
                "game_id": "seed_nba_arb_001",
                "game": "Lakers vs Celtics",
                "sport": Sport.NBA,
                "bet_type": BetType.MONEYLINE,
                "book_a": "BetMGM",
                "side_a": "Lakers ML",
                "odds_a": 165,
                "stake_a_percentage": 37.7,
                "book_b": "Caesars",
                "side_b": "Celtics ML",
                "odds_b": -140,
                "stake_b_percentage": 62.3,
                "profit_percentage": 2.18,
                "total_implied": 0.9782,
                "is_active": True,
            },
            {
                "game_id": "seed_nfl_arb_002",
                "game": "Cowboys vs Eagles",
                "sport": Sport.NFL,
                "bet_type": "total",
                "book_a": "FanDuel",
                "side_a": "Over 45.5",
                "odds_a": -104,
                "stake_a_percentage": 49.0,
                "book_b": "PointsBet",
                "side_b": "Under 45.5",
                "odds_b": -106,
                "stake_b_percentage": 51.0,
                "profit_percentage": 0.93,
                "total_implied": 0.9907,
                "is_active": True,
            },
            {
                "game_id": "seed_nba_arb_002",
                "game": "Warriors vs Suns",
                "sport": Sport.NBA,
                "bet_type": BetType.SPREAD,
                "book_a": "DraftKings",
                "side_a": "Warriors -5",
                "odds_a": -106,
                "stake_a_percentage": 48.5,
                "book_b": "BetMGM",
                "side_b": "Suns +5",
                "odds_b": -107,
                "stake_b_percentage": 51.5,
                "profit_percentage": 0.74,
                "total_implied": 0.9926,
                "is_active": True,
            },
        ]

        for arb in sample_arbs:
            client.table("arbitrage_opportunities").insert(arb).execute()
            print(f"Seeded arb: {arb['side_a']} vs {arb['side_b']} ({arb['profit_percentage']:.2f}% profit)")

        print("\nSeed complete!")

    except Exception as e:
        print(f"ERROR: Seed failed — {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed()
