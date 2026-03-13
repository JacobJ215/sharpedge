"""Value play scanner - finds +EV betting opportunities.

Scans odds across sportsbooks and compares to model projections
to identify positive expected value bets.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Confidence(StrEnum):
    """Confidence level for value plays."""

    HIGH = "HIGH"  # 5%+ edge
    MEDIUM = "MEDIUM"  # 2.5-5% edge
    LOW = "LOW"  # 1-2.5% edge


@dataclass
class ValuePlay:
    """A detected value betting opportunity."""

    game_id: str
    game: str  # "Chiefs vs Raiders"
    sport: str
    bet_type: str  # "spread", "total", "moneyline"
    side: str  # "Chiefs -3", "Over 45.5", "Raiders ML"
    sportsbook: str
    market_odds: int  # Current odds at sportsbook
    model_probability: float  # Our model's win probability
    implied_probability: float  # Market implied probability
    fair_odds: int  # No-vig fair odds
    edge_percentage: float  # Edge in percentage points
    ev_percentage: float  # Expected value as percentage
    confidence: Confidence
    expires_at: datetime | None  # Game start time
    detected_at: datetime
    notes: str


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def prob_to_american(prob: float) -> int:
    """Convert probability to American odds."""
    if prob <= 0 or prob >= 1:
        return 0
    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))
    else:
        return round(100 * (1 - prob) / prob)


def calculate_ev(model_prob: float, market_odds: int) -> float:
    """Calculate expected value of a bet.

    Args:
        model_prob: Model's probability of winning (0-1)
        market_odds: American odds offered

    Returns:
        EV as percentage of stake
    """
    if market_odds > 0:
        decimal_odds = (market_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(market_odds)) + 1

    ev = (model_prob * decimal_odds) - 1
    return ev * 100


def calculate_edge(model_prob: float, market_odds: int) -> float:
    """Calculate edge over the market.

    Args:
        model_prob: Model's probability (0-1)
        market_odds: American odds offered

    Returns:
        Edge in percentage points
    """
    implied = american_to_implied_prob(market_odds)
    return (model_prob - implied) * 100


def classify_confidence(edge: float) -> Confidence:
    """Classify confidence level based on edge."""
    if edge >= 5.0:
        return Confidence.HIGH
    elif edge >= 2.5:
        return Confidence.MEDIUM
    else:
        return Confidence.LOW


def scan_for_value(
    projections: list[dict],
    odds_by_book: dict[str, dict],
    min_ev: float = 1.0,
    min_edge: float = 1.0,
) -> list[ValuePlay]:
    """Scan for value plays across all games and books.

    Args:
        projections: List of model projections with structure:
            {
                "game_id": str,
                "game": str,
                "sport": str,
                "home_win_prob": float,
                "away_win_prob": float,
                "over_prob": float,  # optional
                "under_prob": float,  # optional
                "spread_home_prob": float,  # optional
                "spread_away_prob": float,  # optional
            }
        odds_by_book: Dict mapping book name to odds dict:
            {
                "fanduel": {
                    "game_id": {
                        "spread_home": -110,
                        "spread_away": -110,
                        "total_over": -110,
                        "total_under": -110,
                        "ml_home": -150,
                        "ml_away": +130,
                    }
                }
            }
        min_ev: Minimum EV percentage to include
        min_edge: Minimum edge percentage to include

    Returns:
        List of ValuePlay opportunities sorted by EV
    """
    value_plays = []
    now = datetime.now()

    for proj in projections:
        game_id = proj["game_id"]
        game = proj.get("game", "Unknown")
        sport = proj.get("sport", "")

        for book_name, book_odds in odds_by_book.items():
            game_odds = book_odds.get(game_id, {})
            if not game_odds:
                continue

            # Check each bet type
            checks = [
                ("spread", "home", proj.get("spread_home_prob"), game_odds.get("spread_home")),
                ("spread", "away", proj.get("spread_away_prob"), game_odds.get("spread_away")),
                ("total", "over", proj.get("over_prob"), game_odds.get("total_over")),
                ("total", "under", proj.get("under_prob"), game_odds.get("total_under")),
                ("moneyline", "home", proj.get("home_win_prob"), game_odds.get("ml_home")),
                ("moneyline", "away", proj.get("away_win_prob"), game_odds.get("ml_away")),
            ]

            for bet_type, side, model_prob, market_odds in checks:
                if model_prob is None or market_odds is None:
                    continue

                ev = calculate_ev(model_prob, market_odds)
                edge = calculate_edge(model_prob, market_odds)

                if ev >= min_ev and edge >= min_edge:
                    implied = american_to_implied_prob(market_odds)
                    fair_odds = prob_to_american(model_prob)

                    # Build side description
                    if bet_type == "spread":
                        side_desc = f"{proj.get('home_team', 'Home')} {game_odds.get('spread_line', '')}" if side == "home" else f"{proj.get('away_team', 'Away')} {game_odds.get('spread_line', '')}"
                    elif bet_type == "total":
                        side_desc = f"{'Over' if side == 'over' else 'Under'} {game_odds.get('total_line', '')}"
                    else:
                        side_desc = f"{proj.get('home_team' if side == 'home' else 'away_team', side.title())} ML"

                    value_plays.append(ValuePlay(
                        game_id=game_id,
                        game=game,
                        sport=sport,
                        bet_type=bet_type,
                        side=side_desc,
                        sportsbook=book_name,
                        market_odds=market_odds,
                        model_probability=round(model_prob, 4),
                        implied_probability=round(implied, 4),
                        fair_odds=fair_odds,
                        edge_percentage=round(edge, 2),
                        ev_percentage=round(ev, 2),
                        confidence=classify_confidence(edge),
                        expires_at=proj.get("game_time"),
                        detected_at=now,
                        notes="",
                    ))

    return value_plays


def rank_value_plays(plays: list[ValuePlay]) -> list[ValuePlay]:
    """Rank value plays by a composite score.

    Considers: EV, edge, confidence, and sportsbook quality.

    Args:
        plays: List of ValuePlay opportunities

    Returns:
        Sorted list with best plays first
    """
    def score(play: ValuePlay) -> float:
        # Base score is EV
        s = play.ev_percentage

        # Bonus for high confidence
        if play.confidence == Confidence.HIGH:
            s *= 1.2
        elif play.confidence == Confidence.MEDIUM:
            s *= 1.1

        # Slight bonus for reputable books (less likely to limit)
        reputable = ["fanduel", "draftkings", "betmgm", "caesars"]
        if play.sportsbook.lower() in reputable:
            s *= 1.05

        return s

    return sorted(plays, key=score, reverse=True)


def filter_value_plays(
    plays: list[ValuePlay],
    min_ev: float | None = None,
    min_edge: float | None = None,
    confidence: Confidence | None = None,
    sport: str | None = None,
    bet_type: str | None = None,
    sportsbook: str | None = None,
) -> list[ValuePlay]:
    """Filter value plays by criteria.

    Args:
        plays: List of ValuePlay to filter
        min_ev: Minimum EV percentage
        min_edge: Minimum edge percentage
        confidence: Required confidence level
        sport: Filter to specific sport
        bet_type: Filter to specific bet type
        sportsbook: Filter to specific sportsbook

    Returns:
        Filtered list of ValuePlay
    """
    result = plays

    if min_ev is not None:
        result = [p for p in result if p.ev_percentage >= min_ev]

    if min_edge is not None:
        result = [p for p in result if p.edge_percentage >= min_edge]

    if confidence is not None:
        result = [p for p in result if p.confidence == confidence]

    if sport is not None:
        result = [p for p in result if p.sport.upper() == sport.upper()]

    if bet_type is not None:
        result = [p for p in result if p.bet_type == bet_type]

    if sportsbook is not None:
        result = [p for p in result if p.sportsbook.lower() == sportsbook.lower()]

    return result


def summarize_value_plays(plays: list[ValuePlay]) -> dict:
    """Generate summary statistics for value plays.

    Args:
        plays: List of ValuePlay

    Returns:
        Summary dict
    """
    if not plays:
        return {
            "count": 0,
            "avg_ev": 0,
            "avg_edge": 0,
            "by_confidence": {},
            "by_sport": {},
            "by_book": {},
        }

    by_confidence = {}
    by_sport = {}
    by_book = {}

    for p in plays:
        by_confidence[p.confidence] = by_confidence.get(p.confidence, 0) + 1
        by_sport[p.sport] = by_sport.get(p.sport, 0) + 1
        by_book[p.sportsbook] = by_book.get(p.sportsbook, 0) + 1

    return {
        "count": len(plays),
        "avg_ev": round(sum(p.ev_percentage for p in plays) / len(plays), 2),
        "avg_edge": round(sum(p.edge_percentage for p in plays) / len(plays), 2),
        "max_ev": round(max(p.ev_percentage for p in plays), 2),
        "by_confidence": by_confidence,
        "by_sport": by_sport,
        "by_book": by_book,
        "high_confidence_count": by_confidence.get(Confidence.HIGH, 0),
    }


# ============================================
# NO-VIG BASED VALUE SCANNER (No ML Required)
# ============================================

# Sharp books whose odds are closest to "true" probability
SHARP_BOOKS = ["pinnacle", "circa", "bookmaker"]


def calculate_consensus_fair_prob(
    all_book_odds: dict[str, tuple[int, int]],
    sharp_weight: float = 2.0,
) -> tuple[float, float]:
    """Calculate consensus fair probability from multiple books.

    Uses weighted average of no-vig probabilities, with sharp books
    weighted more heavily.

    Args:
        all_book_odds: Dict of {book_name: (side1_odds, side2_odds)}
        sharp_weight: Multiplier for sharp book weights

    Returns:
        Tuple of (fair_prob_side1, fair_prob_side2)
    """
    if not all_book_odds:
        return 0.5, 0.5

    prob1_weighted_sum = 0.0
    prob2_weighted_sum = 0.0
    total_weight = 0.0

    for book, (odds1, odds2) in all_book_odds.items():
        # Calculate no-vig probabilities for this book
        implied1 = american_to_implied_prob(odds1)
        implied2 = american_to_implied_prob(odds2)
        total_implied = implied1 + implied2

        fair1 = implied1 / total_implied
        fair2 = implied2 / total_implied

        # Weight by book sharpness
        weight = sharp_weight if book.lower() in SHARP_BOOKS else 1.0

        prob1_weighted_sum += fair1 * weight
        prob2_weighted_sum += fair2 * weight
        total_weight += weight

    fair_prob1 = prob1_weighted_sum / total_weight
    fair_prob2 = prob2_weighted_sum / total_weight

    # Normalize to sum to 1
    total = fair_prob1 + fair_prob2
    return fair_prob1 / total, fair_prob2 / total


def scan_for_value_no_vig(
    games: list[dict],
    min_ev: float = 1.0,
    min_edge: float = 1.0,
) -> list[ValuePlay]:
    """Scan for value plays using no-vig consensus as fair probability.

    This function doesn't require ML projections. Instead, it:
    1. Calculates fair probability from consensus across all books
    2. Compares each book's odds to that consensus
    3. Flags books offering better odds than fair

    Args:
        games: List of game dicts with structure:
            {
                "id": str,
                "sport": str,
                "home_team": str,
                "away_team": str,
                "bookmakers": [
                    {
                        "key": str,
                        "markets": [
                            {
                                "key": "spreads"|"totals"|"h2h",
                                "outcomes": [
                                    {"name": str, "price": int, "point": float}
                                ]
                            }
                        ]
                    }
                ]
            }
        min_ev: Minimum EV percentage to include
        min_edge: Minimum edge percentage to include

    Returns:
        List of ValuePlay opportunities
    """
    value_plays = []
    now = datetime.now()

    for game in games:
        game_id = game.get("id", "")
        sport = game.get("sport_key", "")
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        game_desc = f"{away_team} @ {home_team}"
        game_time = game.get("commence_time")

        bookmakers = game.get("bookmakers", [])
        if len(bookmakers) < 2:
            continue  # Need multiple books for consensus

        # Process each market type
        for market_key in ["spreads", "totals", "h2h"]:
            # Collect odds across all books for this market
            book_odds: dict[str, dict] = {}

            for bookmaker in bookmakers:
                book_key = bookmaker.get("key", "")
                for market in bookmaker.get("markets", []):
                    if market.get("key") != market_key:
                        continue

                    outcomes = market.get("outcomes", [])
                    if not outcomes:
                        continue

                    book_odds[book_key] = {
                        "outcomes": outcomes,
                        "market": market,
                    }

            if len(book_odds) < 2:
                continue

            # Calculate consensus fair probability for this market
            value_plays.extend(
                _find_value_in_market(
                    game_id=game_id,
                    game_desc=game_desc,
                    sport=sport,
                    home_team=home_team,
                    away_team=away_team,
                    market_key=market_key,
                    book_odds=book_odds,
                    game_time=game_time,
                    min_ev=min_ev,
                    min_edge=min_edge,
                    detected_at=now,
                )
            )

    return value_plays


def _find_value_in_market(
    game_id: str,
    game_desc: str,
    sport: str,
    home_team: str,
    away_team: str,
    market_key: str,
    book_odds: dict[str, dict],
    game_time: str | None,
    min_ev: float,
    min_edge: float,
    detected_at: datetime,
) -> list[ValuePlay]:
    """Find value plays within a specific market."""
    value_plays = []

    # Build odds structure for consensus calculation
    if market_key == "spreads":
        # Find home and away spread odds
        side1_name = home_team
        side2_name = away_team
    elif market_key == "totals":
        side1_name = "Over"
        side2_name = "Under"
    else:  # h2h (moneyline)
        side1_name = home_team
        side2_name = away_team

    # Extract odds for each side from each book
    side1_odds_by_book: dict[str, int] = {}
    side2_odds_by_book: dict[str, int] = {}
    side1_info: dict[str, dict] = {}
    side2_info: dict[str, dict] = {}

    for book_key, book_data in book_odds.items():
        outcomes = book_data.get("outcomes", [])

        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price")
            point = outcome.get("point")

            if price is None:
                continue

            if name == side1_name or (market_key == "totals" and name == "Over"):
                side1_odds_by_book[book_key] = price
                side1_info[book_key] = {"price": price, "point": point}
            elif name == side2_name or (market_key == "totals" and name == "Under"):
                side2_odds_by_book[book_key] = price
                side2_info[book_key] = {"price": price, "point": point}

    # Need both sides for consensus
    if not side1_odds_by_book or not side2_odds_by_book:
        return []

    # Calculate consensus fair probability
    # Use books that have both sides
    consensus_books = set(side1_odds_by_book.keys()) & set(side2_odds_by_book.keys())
    if len(consensus_books) < 2:
        return []

    consensus_odds = {
        book: (side1_odds_by_book[book], side2_odds_by_book[book])
        for book in consensus_books
    }

    fair_prob1, fair_prob2 = calculate_consensus_fair_prob(consensus_odds)

    # Get line from first book that has it
    line = None
    for info in side1_info.values():
        if info.get("point") is not None:
            line = info["point"]
            break

    # Now check each book for value
    for book_key, price in side1_odds_by_book.items():
        ev = calculate_ev(fair_prob1, price)
        edge = calculate_edge(fair_prob1, price)

        if ev >= min_ev and edge >= min_edge:
            if market_key == "spreads":
                side_desc = f"{home_team} {line:+.1f}" if line else f"{home_team} spread"
            elif market_key == "totals":
                side_desc = f"Over {line}" if line else "Over"
            else:
                side_desc = f"{home_team} ML"

            value_plays.append(ValuePlay(
                game_id=game_id,
                game=game_desc,
                sport=sport,
                bet_type=market_key.replace("h2h", "moneyline"),
                side=side_desc,
                sportsbook=book_key,
                market_odds=price,
                model_probability=round(fair_prob1, 4),
                implied_probability=round(american_to_implied_prob(price), 4),
                fair_odds=prob_to_american(fair_prob1) if 0 < fair_prob1 < 1 else 0,
                edge_percentage=round(edge, 2),
                ev_percentage=round(ev, 2),
                confidence=classify_confidence(edge),
                expires_at=datetime.fromisoformat(game_time.replace("Z", "+00:00")) if game_time else None,
                detected_at=detected_at,
                notes="Based on no-vig consensus",
            ))

    for book_key, price in side2_odds_by_book.items():
        ev = calculate_ev(fair_prob2, price)
        edge = calculate_edge(fair_prob2, price)

        if ev >= min_ev and edge >= min_edge:
            if market_key == "spreads":
                side_desc = f"{away_team} {-line:+.1f}" if line else f"{away_team} spread"
            elif market_key == "totals":
                side_desc = f"Under {line}" if line else "Under"
            else:
                side_desc = f"{away_team} ML"

            value_plays.append(ValuePlay(
                game_id=game_id,
                game=game_desc,
                sport=sport,
                bet_type=market_key.replace("h2h", "moneyline"),
                side=side_desc,
                sportsbook=book_key,
                market_odds=price,
                model_probability=round(fair_prob2, 4),
                implied_probability=round(american_to_implied_prob(price), 4),
                fair_odds=prob_to_american(fair_prob2) if 0 < fair_prob2 < 1 else 0,
                edge_percentage=round(edge, 2),
                ev_percentage=round(ev, 2),
                confidence=classify_confidence(edge),
                expires_at=datetime.fromisoformat(game_time.replace("Z", "+00:00")) if game_time else None,
                detected_at=detected_at,
                notes="Based on no-vig consensus",
            ))

    return value_plays
