"""Format alert and win announcement content for each social platform."""

from __future__ import annotations

from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fmt_odds(odds: int | float) -> str:
    """Return American-odds string: +150 or -110."""
    odds = int(odds)
    return f"+{odds}" if odds >= 0 else str(odds)


def _sport_hashtags(play_or_bet: dict) -> str:
    """Return sport-specific hashtags based on the sport field."""
    sport = str(play_or_bet.get("sport", "")).upper()
    mapping: dict[str, str] = {
        "NFL": "#NFL #FootballBetting",
        "NBA": "#NBA #BasketballBetting",
        "MLB": "#MLB #BaseballBetting",
        "NHL": "#NHL #HockeyBetting",
        "NCAAF": "#NCAAF #CollegeFootball",
        "NCAAB": "#NCAAB #CollegeBasketball",
        "SOCCER": "#Soccer #SoccerBetting",
        "MMA": "#MMA #UFCBetting",
        "UFC": "#UFC #UFCBetting",
        "TENNIS": "#Tennis #TennisBetting",
        "GOLF": "#Golf #GolfBetting",
        "BOX": "#Boxing #BoxingBetting",
    }
    for key, tags in mapping.items():
        if key in sport:
            return tags
    return "#SportsBetting #Betting"


# ---------------------------------------------------------------------------
# Alert formatters
# ---------------------------------------------------------------------------


def format_alert_discord(play: dict) -> dict:
    """Return a discord embed dict for a value play alert."""
    game = play.get("game") or play.get("event", "Unknown Game")
    side = play.get("side") or play.get("team", "")
    market = play.get("bet_type") or play.get("market", "")
    book = play.get("sportsbook") or play.get("book", "")
    ev_raw = play.get("ev_percentage") or play.get("expected_value", 0)
    # ev_percentage is stored as a whole number (e.g. 4.2 = 4.2%); expected_value
    # from the mobile route is fractional (0.042). Normalise to a percentage float.
    ev = float(ev_raw) if float(ev_raw) > 1 else float(ev_raw) * 100
    confidence = play.get("confidence", "")
    odds_raw = play.get("market_odds") or play.get("book_odds") or play.get("our_odds") or 0

    fields = [
        {"name": "Game", "value": game, "inline": False},
        {"name": "Pick", "value": side, "inline": True},
        {"name": "Market", "value": market, "inline": True},
        {"name": "Book", "value": book, "inline": True},
        {"name": "EV", "value": f"+{ev:.1f}%", "inline": True},
        {"name": "Odds", "value": _fmt_odds(odds_raw), "inline": True},
        {"name": "Confidence", "value": str(confidence).capitalize(), "inline": True},
    ]

    return {
        "title": "Value Play Alert",
        "description": f"**{side}** ({market}) at **{book}**",
        "color": 0x00D4AA,
        "fields": fields,
        "footer": {"text": "SharpEdge \u2022 Value Alert"},
        "timestamp": datetime.now(UTC).isoformat(),
    }


def format_alert_twitter(play: dict) -> str:
    """Return tweet text for a value play alert. Max 250 chars."""
    game = play.get("game") or play.get("event", "Unknown Game")
    side = play.get("side") or play.get("team", "")
    market = play.get("bet_type") or play.get("market", "")
    book = play.get("sportsbook") or play.get("book", "")
    odds_raw = play.get("market_odds") or play.get("book_odds") or play.get("our_odds") or 0
    ev_raw = play.get("ev_percentage") or play.get("expected_value", 0)
    ev = float(ev_raw) if float(ev_raw) > 1 else float(ev_raw) * 100
    confidence = str(play.get("confidence", "")).capitalize()

    text = (
        f"\U0001f3af ALERT: {game}\n"
        f"{side} ({market})\n"
        f"{book} @ {_fmt_odds(odds_raw)}\n"
        f"+{ev:.1f}% EV | {confidence}\n"
        f"#SharpEdge #SportsBetting"
    )

    # Hard trim to 250 chars while keeping hashtags
    if len(text) > 250:
        tail = "\n#SharpEdge #SportsBetting"
        allowed = 250 - len(tail)
        text = text[:allowed].rstrip() + tail

    return text


def format_alert_instagram_caption(play: dict) -> str:
    """Return Instagram caption for a value play alert."""
    game = play.get("game") or play.get("event", "Unknown Game")
    side = play.get("side") or play.get("team", "")
    market = play.get("bet_type") or play.get("market", "")
    book = play.get("sportsbook") or play.get("book", "")
    odds_raw = play.get("market_odds") or play.get("book_odds") or play.get("our_odds") or 0
    ev_raw = play.get("ev_percentage") or play.get("expected_value", 0)
    ev = float(ev_raw) if float(ev_raw) > 1 else float(ev_raw) * 100
    confidence = str(play.get("confidence", "")).capitalize()
    sport_tags = _sport_hashtags(play)

    body = (
        f"\U0001f3af VALUE ALERT\n\n"
        f"Game: {game}\n"
        f"Pick: {side} ({market})\n"
        f"Book: {book} @ {_fmt_odds(odds_raw)}\n"
        f"Edge: +{ev:.1f}% EV | {confidence} confidence\n\n"
        f"Our models identified this line as mispriced. "
        f"Always bet within your bankroll. Track every play at sharpedge.ai\n\n"
        f"#SharpEdge #SportsBetting #SharpBetting #BettingPicks "
        f"#ValueBetting #EVBetting #SportsPicks #BettingAdvice "
        f"#BettingCommunity #ExpectedValue {sport_tags}"
    )
    return body


# ---------------------------------------------------------------------------
# Win announcement formatters
# ---------------------------------------------------------------------------


def format_win_discord(bet: dict, summary: dict, original_post_id: str | None = None) -> dict:
    """Return a discord embed dict for a win announcement."""
    game = bet.get("game") or bet.get("event", "Unknown Game")
    selection = bet.get("selection") or bet.get("side") or bet.get("team", "")
    odds_raw = bet.get("odds") or bet.get("book_odds") or 0
    profit = float(bet.get("profit") or 0)

    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    roi = float(summary.get("roi", 0))

    fields = [
        {"name": "Pick", "value": f"{selection} {_fmt_odds(odds_raw)}", "inline": True},
        {"name": "Profit", "value": f"+${profit:,.2f}", "inline": True},
        {"name": "Running ROI", "value": f"+{roi:.1f}%", "inline": True},
        {"name": "Season Record", "value": f"{wins}W-{losses}L", "inline": True},
    ]

    description = f"**{selection}** came through at {_fmt_odds(odds_raw)}"
    if original_post_id:
        description += f"\n\u2192 Original alert: {original_post_id}"

    return {
        "title": f"\U0001f3c6 WINNER \u2014 {game}",
        "description": description,
        "color": 0x00D4AA,
        "fields": fields,
        "footer": {"text": "SharpEdge \u2022 We called it"},
        "timestamp": datetime.now(UTC).isoformat(),
    }


def format_win_twitter(bet: dict, summary: dict) -> str:
    """Return tweet text for a win announcement. Max 250 chars."""
    selection = bet.get("selection") or bet.get("side") or bet.get("team", "")
    odds_raw = bet.get("odds") or bet.get("book_odds") or 0
    profit = float(bet.get("profit") or 0)

    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    roi = float(summary.get("roi", 0))

    text = (
        f"\U0001f3c6 WINNER!\n"
        f"{selection} \u2705\n"
        f"Odds: {_fmt_odds(odds_raw)} | Profit: +${profit:,.2f}\n"
        f"Season: {wins}W-{losses}L | ROI: +{roi:.1f}%\n"
        f"#SharpEdge"
    )

    if len(text) > 250:
        tail = "\n#SharpEdge"
        allowed = 250 - len(tail)
        text = text[:allowed].rstrip() + tail

    return text


def format_win_instagram_caption(bet: dict, summary: dict) -> str:
    """Return Instagram caption for a win announcement with hashtags."""
    game = bet.get("game") or bet.get("event", "Unknown Game")
    selection = bet.get("selection") or bet.get("side") or bet.get("team", "")
    odds_raw = bet.get("odds") or bet.get("book_odds") or 0
    profit = float(bet.get("profit") or 0)
    sport_tags = _sport_hashtags(bet)

    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    pushes = summary.get("pushes", 0)
    roi = float(summary.get("roi", 0))
    win_rate = float(summary.get("win_rate", 0))
    # win_rate may be fractional (0-1) or percentage (0-100)
    if win_rate <= 1.0:
        win_rate *= 100

    body = (
        f"\U0001f3c6 WINNER!\n\n"
        f"Game: {game}\n"
        f"Pick: {selection} @ {_fmt_odds(odds_raw)}\n"
        f"Profit: +${profit:,.2f}\n\n"
        f"Season Record: {wins}W-{losses}L{f'-{pushes}P' if pushes else ''}\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Season ROI: +{roi:.1f}%\n\n"
        f"Our process is built on expected value. "
        f"Follow for daily picks, line movement alerts, and arbitrage opportunities. "
        f"Track everything at sharpedge.ai\n\n"
        f"#SharpEdge #SportsBetting #SharpBetting #BettingPicks "
        f"#ValueBetting #EVBetting #SportsPicks #BettingWins "
        f"#BettingCommunity #WinningBets #BettingTips {sport_tags}"
    )
    return body
