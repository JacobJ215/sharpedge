"""Line movement detection and classification.

Line movements reveal where money is flowing. Sharp bettors move lines
with their bets. Understanding movement types helps identify value.

Movement Types:
- Steam: Sharp, sudden move across multiple books
- RLM (Reverse Line Movement): Line moves opposite to public betting
- Buyback: Line moves back after initial sharp action
- Gradual: Slow drift from balanced action
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class MovementType(StrEnum):
    """Types of line movement."""

    STEAM = "steam"  # Sharp money, sudden move across books
    RLM = "rlm"  # Reverse line movement (opposite public)
    BUYBACK = "buyback"  # Line moves back after sharp action
    GRADUAL = "gradual"  # Slow drift from balanced action
    CORRECTION = "correction"  # Adjustment after news/injury
    OPENING = "opening"  # Initial market formation
    UNKNOWN = "unknown"


@dataclass
class LineMovementResult:
    """Result of line movement classification."""

    game_id: str
    bet_type: str  # "spread", "total", "moneyline"
    old_line: float
    new_line: float
    old_odds: int | None
    new_odds: int | None
    movement: float  # Magnitude of move
    direction: str  # "toward_favorite", "toward_underdog", "over", "under"
    movement_type: MovementType
    confidence: float  # 0-1 confidence in classification
    interpretation: str
    is_significant: bool
    timestamp: datetime


# Thresholds for movement classification
STEAM_MOVE_THRESHOLD = 1.0  # 1 point = likely steam
SIGNIFICANT_MOVE_THRESHOLD = 0.5  # 0.5 points = notable
STEAM_TIME_WINDOW = timedelta(minutes=30)  # Steam happens fast


def classify_line_movement(
    old_line: float,
    new_line: float,
    old_odds: int | None = None,
    new_odds: int | None = None,
    game_id: str = "",
    bet_type: str = "spread",
    time_elapsed: timedelta | None = None,
    public_on_side: str | None = None,  # Which side public is betting
    move_direction: str | None = None,  # Which direction line moved
) -> LineMovementResult:
    """Classify a line movement.

    Args:
        old_line: Previous line
        new_line: Current line
        old_odds: Previous odds (optional)
        new_odds: Current odds (optional)
        game_id: Identifier for the game
        bet_type: Type of bet (spread, total, moneyline)
        time_elapsed: How long the move took
        public_on_side: "home", "away", "over", "under" - where public is betting
        move_direction: "home", "away", "over", "under" - which way line moved

    Returns:
        LineMovementResult with classification
    """
    movement = abs(new_line - old_line)

    # Determine direction
    if bet_type == "spread":
        if new_line < old_line:
            direction = "toward_favorite"
        else:
            direction = "toward_underdog"
    else:  # total
        if new_line < old_line:
            direction = "under"
        else:
            direction = "over"

    # Classify the movement
    movement_type = MovementType.UNKNOWN
    confidence = 0.5
    interpretation = ""

    # Check for steam move (large, fast)
    if movement >= STEAM_MOVE_THRESHOLD:
        if time_elapsed and time_elapsed <= STEAM_TIME_WINDOW:
            movement_type = MovementType.STEAM
            confidence = 0.85
            interpretation = (
                f"Steam move detected: {movement:.1f} pt move in "
                f"{time_elapsed.total_seconds() / 60:.0f} minutes. "
                "Sharp money likely involved."
            )
        else:
            movement_type = MovementType.STEAM
            confidence = 0.7
            interpretation = (
                f"Large move ({movement:.1f} pts) suggests sharp action."
            )

    # Check for RLM (line moves opposite to public)
    elif public_on_side and move_direction:
        is_rlm = (
            (public_on_side in ["home", "over"] and move_direction in ["away", "under"])
            or (public_on_side in ["away", "under"] and move_direction in ["home", "over"])
        )
        if is_rlm:
            movement_type = MovementType.RLM
            confidence = 0.75
            interpretation = (
                f"Reverse line movement: public on {public_on_side} but "
                f"line moved {move_direction}. Sharp money opposing public."
            )

    # Check for significant but not steam
    elif movement >= SIGNIFICANT_MOVE_THRESHOLD:
        movement_type = MovementType.GRADUAL
        confidence = 0.6
        interpretation = (
            f"Notable {movement:.1f} pt move. Monitor for further action."
        )

    # Minor movement
    else:
        movement_type = MovementType.GRADUAL
        confidence = 0.5
        interpretation = "Minor line adjustment, likely balanced action."

    is_significant = movement >= SIGNIFICANT_MOVE_THRESHOLD

    return LineMovementResult(
        game_id=game_id,
        bet_type=bet_type,
        old_line=old_line,
        new_line=new_line,
        old_odds=old_odds,
        new_odds=new_odds,
        movement=round(movement, 2),
        direction=direction,
        movement_type=movement_type,
        confidence=round(confidence, 2),
        interpretation=interpretation,
        is_significant=is_significant,
        timestamp=datetime.now(),
    )


def detect_steam_move(
    movements: list[tuple[str, float, float, datetime]],
    threshold: float = STEAM_MOVE_THRESHOLD,
    time_window: timedelta = STEAM_TIME_WINDOW,
) -> bool:
    """Detect if a steam move occurred across multiple books.

    A true steam move shows similar movement across multiple books
    in a short time window.

    Args:
        movements: List of (book_name, old_line, new_line, timestamp)
        threshold: Minimum movement to consider
        time_window: Maximum time for coordinated move

    Returns:
        True if steam move detected
    """
    if len(movements) < 2:
        return False

    # Sort by timestamp
    sorted_moves = sorted(movements, key=lambda x: x[3])

    # Check if multiple books moved in same direction within window
    first_time = sorted_moves[0][3]
    last_time = sorted_moves[-1][3]

    if last_time - first_time > time_window:
        return False

    # Check if all moves are in same direction and large enough
    directions = []
    for _, old, new, _ in sorted_moves:
        if abs(new - old) >= threshold * 0.5:  # At least half threshold
            directions.append(1 if new > old else -1)

    # Steam = all same direction
    if not directions:
        return False

    return all(d == directions[0] for d in directions)


def detect_reverse_line_movement(
    public_percentage: float,
    line_direction: str,
    public_side: str,
) -> tuple[bool, str]:
    """Detect reverse line movement.

    RLM occurs when the line moves opposite to where the public is betting.

    Args:
        public_percentage: Percentage of bets on public side (0-100)
        line_direction: "home" or "away" / "over" or "under"
        public_side: Which side the public is on

    Returns:
        (is_rlm, explanation)
    """
    opposite_sides = {
        "home": "away",
        "away": "home",
        "over": "under",
        "under": "over",
    }

    is_rlm = line_direction == opposite_sides.get(public_side, "")

    if is_rlm and public_percentage >= 60:
        return True, (
            f"{public_percentage:.0f}% of tickets on {public_side}, "
            f"but line moved toward {line_direction}. "
            "Sharp money opposing the public."
        )
    elif is_rlm:
        return True, (
            f"Line moved opposite to public ({public_side}). "
            "Possible sharp action."
        )

    return False, ""


def calculate_movement_from_open(
    opening_line: float,
    current_line: float,
    bet_type: str = "spread",
) -> dict[str, any]:
    """Calculate total movement from opening line.

    Args:
        opening_line: Line when market opened
        current_line: Current line
        bet_type: "spread" or "total"

    Returns:
        Movement analysis from open
    """
    movement = current_line - opening_line
    abs_movement = abs(movement)

    if bet_type == "spread":
        if movement < 0:
            direction = "toward_favorite"
            interpretation = f"Favorite getting {abs_movement:.1f} more points of action"
        elif movement > 0:
            direction = "toward_underdog"
            interpretation = f"Underdog getting {abs_movement:.1f} more points of action"
        else:
            direction = "unchanged"
            interpretation = "Line unchanged from open"
    else:
        if movement < 0:
            direction = "down"
            interpretation = f"Total dropped {abs_movement:.1f} points"
        elif movement > 0:
            direction = "up"
            interpretation = f"Total climbed {abs_movement:.1f} points"
        else:
            direction = "unchanged"
            interpretation = "Total unchanged from open"

    significance = "major" if abs_movement >= 1.5 else "notable" if abs_movement >= 0.5 else "minor"

    return {
        "opening_line": opening_line,
        "current_line": current_line,
        "total_movement": round(movement, 2),
        "direction": direction,
        "significance": significance,
        "interpretation": interpretation,
    }


def track_movement_history(
    snapshots: list[tuple[datetime, float]],
) -> list[dict]:
    """Create a timeline of line movements.

    Args:
        snapshots: List of (timestamp, line) tuples

    Returns:
        List of movement events
    """
    if len(snapshots) < 2:
        return []

    sorted_snapshots = sorted(snapshots, key=lambda x: x[0])
    movements = []

    for i in range(1, len(sorted_snapshots)):
        prev_time, prev_line = sorted_snapshots[i - 1]
        curr_time, curr_line = sorted_snapshots[i]

        if prev_line != curr_line:
            movements.append({
                "from_time": prev_time,
                "to_time": curr_time,
                "from_line": prev_line,
                "to_line": curr_line,
                "movement": round(curr_line - prev_line, 2),
                "duration": curr_time - prev_time,
            })

    return movements
