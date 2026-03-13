"""Constants for The Odds API integration."""

from sharpedge_shared.types import Sport

BASE_URL = "https://api.the-odds-api.com/v4"

# Maps our Sport enum to The Odds API sport keys
SPORT_KEYS: dict[Sport, str] = {
    Sport.NFL: "americanfootball_nfl",
    Sport.NBA: "basketball_nba",
    Sport.MLB: "baseball_mlb",
    Sport.NHL: "icehockey_nhl",
    Sport.NCAAF: "americanfootball_ncaaf",
    Sport.NCAAB: "basketball_ncaab",
}

# Maps API bookmaker keys to display names
BOOKMAKER_DISPLAY_NAMES: dict[str, str] = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM",
    "caesars": "Caesars",
    "pointsbet": "PointsBet",
    "bet365": "Bet365",
    "bovada": "Bovada",
    "williamhill_us": "William Hill",
    "unibet_us": "Unibet",
    "betrivers": "BetRivers",
    "superbook": "SuperBook",
    "barstool": "ESPN BET",
    "espnbet": "ESPN BET",
    "hard_rock": "Hard Rock",
    "fliff": "Fliff",
}

MARKETS = ["h2h", "spreads", "totals"]
REGIONS = ["us", "us2"]

# Cache TTLs in seconds
ODDS_CACHE_TTL = 300   # 5 minutes
SCORES_CACHE_TTL = 60  # 1 minute
