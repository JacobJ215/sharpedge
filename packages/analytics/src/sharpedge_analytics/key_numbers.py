"""Key number analysis for sports betting.

Key numbers are the most common margins of victory. In the NFL,
games decided by exactly 3 or 7 points occur ~25% of the time.
Crossing a key number significantly changes the value of a bet.
"""

from dataclasses import dataclass


# NFL key numbers with historical frequency (approximate)
KEY_NUMBERS_NFL: dict[int, float] = {
    3: 0.152,   # ~15.2% of games decided by exactly 3
    7: 0.092,   # ~9.2% decided by exactly 7
    6: 0.055,   # ~5.5%
    10: 0.051,  # ~5.1%
    4: 0.046,   # ~4.6%
    14: 0.042,  # ~4.2%
    1: 0.039,   # ~3.9%
    17: 0.036,  # ~3.6%
    13: 0.034,  # ~3.4%
    2: 0.032,   # ~3.2%
}

# College football - similar but slightly different distribution
KEY_NUMBERS_NCAAF: dict[int, float] = {
    3: 0.140,
    7: 0.088,
    14: 0.052,
    10: 0.048,
    6: 0.045,
    4: 0.042,
    17: 0.040,
    21: 0.038,
    1: 0.035,
    2: 0.030,
}

# NBA key numbers (less impactful than NFL)
KEY_NUMBERS_NBA: dict[int, float] = {
    1: 0.045,
    2: 0.044,
    3: 0.043,
    4: 0.042,
    5: 0.041,
    6: 0.040,
    7: 0.039,
    8: 0.038,
    9: 0.035,
    10: 0.034,
}

# MLB run lines
KEY_NUMBERS_MLB: dict[int, float] = {
    1: 0.280,  # 1-run games are very common
    2: 0.180,
    3: 0.130,
    4: 0.095,
    5: 0.070,
}

# NHL puck lines
KEY_NUMBERS_NHL: dict[int, float] = {
    1: 0.240,  # 1-goal games very common
    2: 0.200,
    3: 0.150,
    4: 0.100,
}

SPORT_KEY_NUMBERS: dict[str, dict[int, float]] = {
    "NFL": KEY_NUMBERS_NFL,
    "NCAAF": KEY_NUMBERS_NCAAF,
    "NBA": KEY_NUMBERS_NBA,
    "NCAAB": KEY_NUMBERS_NBA,  # Use NBA as proxy
    "MLB": KEY_NUMBERS_MLB,
    "NHL": KEY_NUMBERS_NHL,
}


@dataclass
class KeyNumberAnalysis:
    """Analysis of key number impact."""

    current_line: float
    nearest_key: int
    distance_to_key: float
    key_frequency: float  # How often games land on this key number
    crosses_key: bool  # Does moving 0.5 pts cross a key number?
    value_adjustment: float  # Estimated value of crossing the key number


def is_key_number(margin: int, sport: str = "NFL") -> bool:
    """Check if a margin is a key number for the sport."""
    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)
    return abs(margin) in key_numbers


def get_key_number_value(margin: int, sport: str = "NFL") -> float:
    """Get the historical frequency of games landing on this margin."""
    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)
    return key_numbers.get(abs(margin), 0)


def analyze_key_numbers(
    line: float, sport: str = "NFL"
) -> KeyNumberAnalysis:
    """Analyze a line's relationship to key numbers.

    Args:
        line: The spread line (e.g., -3, -2.5, +7.5)
        sport: Sport for key number lookup

    Returns:
        KeyNumberAnalysis with value assessment
    """
    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)

    abs_line = abs(line)
    floor_line = int(abs_line)
    ceil_line = floor_line + 1

    # Find nearest key numbers
    nearest_keys = sorted(
        key_numbers.keys(),
        key=lambda k: abs(k - abs_line)
    )
    nearest_key = nearest_keys[0] if nearest_keys else 3

    distance = abs(abs_line - nearest_key)
    frequency = key_numbers.get(nearest_key, 0)

    # Check if moving 0.5 points (buying a half-point) crosses a key number.
    # A line already sitting exactly on a key number is NOT considered "crossing" —
    # the hook effect applies to lines just shy of the key (e.g. -2.5 hooks at -3).
    lower = abs_line
    upper = abs_line + 0.5
    crosses_key = any(lower < k <= upper for k in key_numbers.keys())

    # Value adjustment: if you're on the wrong side of a key number,
    # that's valuable. If you're getting +3 instead of +2.5, that's huge in NFL.
    value_adjustment = 0
    if sport.upper() in ["NFL", "NCAAF"]:
        # Being on the "hook" side of 3 or 7 is very valuable
        if 2.5 <= abs_line <= 3:
            value_adjustment = frequency * 100  # ~15% swing
        elif 3 < abs_line <= 3.5:
            value_adjustment = -frequency * 100
        elif 6.5 <= abs_line <= 7:
            value_adjustment = frequency * 100
        elif 7 < abs_line <= 7.5:
            value_adjustment = -frequency * 100

    return KeyNumberAnalysis(
        current_line=line,
        nearest_key=nearest_key,
        distance_to_key=round(distance, 2),
        key_frequency=frequency,
        crosses_key=crosses_key,
        value_adjustment=round(value_adjustment, 2),
    )


def compare_lines_key_numbers(
    line_a: float, line_b: float, sport: str = "NFL"
) -> dict[str, any]:
    """Compare two lines in terms of key number value.

    Useful for comparing alternate lines or shopping between books.

    Args:
        line_a: First line
        line_b: Second line
        sport: Sport for analysis

    Returns:
        Comparison showing which line is better and why
    """
    analysis_a = analyze_key_numbers(line_a, sport)
    analysis_b = analyze_key_numbers(line_b, sport)

    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)

    # Count key numbers crossed between the two lines
    low = min(abs(line_a), abs(line_b))
    high = max(abs(line_a), abs(line_b))

    keys_between = [k for k in key_numbers.keys() if low < k <= high]
    total_freq_crossed = sum(key_numbers.get(k, 0) for k in keys_between)

    # Determine which line is better (getting more points is better)
    if abs(line_a) > abs(line_b):
        better_line = line_a
        worse_line = line_b
    else:
        better_line = line_b
        worse_line = line_a

    return {
        "line_a": line_a,
        "line_b": line_b,
        "analysis_a": analysis_a,
        "analysis_b": analysis_b,
        "keys_crossed": keys_between,
        "frequency_impact": round(total_freq_crossed * 100, 1),
        "better_line": better_line,
        "difference_matters": total_freq_crossed > 0.05,  # >5% impact
        "explanation": _explain_key_number_diff(line_a, line_b, keys_between, sport),
    }


def _explain_key_number_diff(
    line_a: float, line_b: float, keys_crossed: list[int], sport: str
) -> str:
    """Generate human-readable explanation of key number impact."""
    if not keys_crossed:
        return "No key numbers crossed between these lines."

    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)

    explanations = []
    for key in keys_crossed:
        freq = key_numbers.get(key, 0)
        explanations.append(f"{key} ({freq*100:.1f}% of games)")

    return f"Crosses key number(s): {', '.join(explanations)}"


@dataclass
class ZoneAnalysis:
    """Extended key number zone analysis for QUANT-04."""

    current_line: float
    nearest_key: int
    distance_to_key: float
    crosses_key: bool
    cover_rate: float       # historical frequency of games landing on this key (same as key_frequency)
    half_point_value: float  # estimated value of buying/selling 0.5 pts here (same as value_adjustment)
    zone_strength: float    # normalized 0-1 strength of this zone vs max key in sport


def analyze_zone(line: float, sport: str = "NFL") -> ZoneAnalysis:
    """Return ZoneAnalysis with cover_rate, half_point_value, and zone_strength.

    Args:
        line: The spread line (e.g., -3, -2.5, +7.5)
        sport: Sport for key number lookup

    Returns:
        ZoneAnalysis with full zone strength assessment
    """
    analysis = analyze_key_numbers(line, sport)
    key_numbers = SPORT_KEY_NUMBERS.get(sport.upper(), KEY_NUMBERS_NFL)
    max_frequency = max(key_numbers.values()) if key_numbers else 1.0
    zone_strength = analysis.key_frequency / max_frequency if max_frequency > 0 else 0.0
    return ZoneAnalysis(
        current_line=analysis.current_line,
        nearest_key=analysis.nearest_key,
        distance_to_key=analysis.distance_to_key,
        crosses_key=analysis.crosses_key,
        cover_rate=analysis.key_frequency,
        half_point_value=analysis.value_adjustment,
        zone_strength=zone_strength,
    )


def get_teaser_value(
    original_line: float,
    teased_line: float,
    sport: str = "NFL",
) -> dict[str, any]:
    """Calculate the value of a teaser through key numbers.

    Teasers add points to spreads. Value comes from crossing key numbers.

    Args:
        original_line: Starting spread
        teased_line: Spread after teaser points added
        sport: Sport for analysis

    Returns:
        Analysis of teaser value
    """
    comparison = compare_lines_key_numbers(original_line, teased_line, sport)

    # Standard teaser odds adjustment
    # A 6-point teaser that doesn't cross key numbers is -EV
    # But crossing 3 or 7 can make it +EV

    key_value = comparison["frequency_impact"]

    # Rough threshold: need ~15% key number crossing to justify teaser odds
    is_valuable = key_value >= 12

    return {
        "original_line": original_line,
        "teased_line": teased_line,
        "points_added": abs(teased_line) - abs(original_line),
        "keys_crossed": comparison["keys_crossed"],
        "key_value_percentage": key_value,
        "is_valuable_teaser": is_valuable,
        "recommendation": (
            "Good teaser - crosses significant key numbers"
            if is_valuable
            else "Poor teaser - doesn't cross enough key numbers"
        ),
    }
