"""Market consensus line calculations.

The consensus line represents the "true" market view by aggregating
odds across multiple sportsbooks. Weighted consensus gives more
weight to sharper books (Pinnacle, Circa).
"""

from dataclasses import dataclass
from statistics import median, mean, stdev


# Book sharpness weights (higher = sharper, more weight)
# Pinnacle is the gold standard for sharp odds
BOOK_WEIGHTS: dict[str, float] = {
    "pinnacle": 1.0,
    "circa": 0.95,
    "bookmaker": 0.9,
    "betcris": 0.85,
    "bet365": 0.8,
    "draftkings": 0.7,
    "fanduel": 0.7,
    "betmgm": 0.65,
    "caesars": 0.65,
    "pointsbet": 0.6,
    "betrivers": 0.6,
    "unibet": 0.55,
    "superbook": 0.7,
    "westgate": 0.75,
    "barstool": 0.5,
    "espnbet": 0.5,
    "hardrock": 0.5,
    "fliff": 0.4,
}

DEFAULT_WEIGHT = 0.5


@dataclass
class ConsensusResult:
    """Result of consensus calculation."""

    consensus_line: float  # The consensus (median/weighted) line
    mean_line: float  # Simple average across books
    median_line: float  # Median line
    min_line: float  # Minimum line (most favorable to one side)
    max_line: float  # Maximum line (most favorable to other side)
    spread_range: float  # max - min (market disagreement)
    books_count: int  # Number of books included
    weighted_consensus: float | None  # Weighted by book sharpness
    sharpest_book: str | None  # Book with highest weight
    sharpest_line: float | None  # Line from sharpest book


def get_book_weight(book_name: str) -> float:
    """Get the sharpness weight for a sportsbook."""
    normalized = book_name.lower().replace(" ", "").replace("_", "")
    return BOOK_WEIGHTS.get(normalized, DEFAULT_WEIGHT)


def calculate_consensus_line(lines: list[float]) -> ConsensusResult:
    """Calculate consensus line from multiple sportsbooks.

    Args:
        lines: List of lines from different sportsbooks

    Returns:
        ConsensusResult with median, mean, range, etc.
    """
    if not lines:
        raise ValueError("Cannot calculate consensus from empty list")

    if len(lines) == 1:
        return ConsensusResult(
            consensus_line=lines[0],
            mean_line=lines[0],
            median_line=lines[0],
            min_line=lines[0],
            max_line=lines[0],
            spread_range=0,
            books_count=1,
            weighted_consensus=None,
            sharpest_book=None,
            sharpest_line=None,
        )

    return ConsensusResult(
        consensus_line=median(lines),
        mean_line=round(mean(lines), 2),
        median_line=median(lines),
        min_line=min(lines),
        max_line=max(lines),
        spread_range=round(max(lines) - min(lines), 2),
        books_count=len(lines),
        weighted_consensus=None,
        sharpest_book=None,
        sharpest_line=None,
    )


def calculate_weighted_consensus(
    lines_by_book: dict[str, float]
) -> ConsensusResult:
    """Calculate weighted consensus giving more weight to sharper books.

    Args:
        lines_by_book: Dict mapping sportsbook name to line

    Returns:
        ConsensusResult with weighted consensus included
    """
    if not lines_by_book:
        raise ValueError("Cannot calculate consensus from empty dict")

    lines = list(lines_by_book.values())
    books = list(lines_by_book.keys())

    # Find sharpest book
    weighted_books = [(book, get_book_weight(book)) for book in books]
    weighted_books.sort(key=lambda x: x[1], reverse=True)
    sharpest_book, _ = weighted_books[0]
    sharpest_line = lines_by_book[sharpest_book]

    # Calculate weighted average
    total_weight = 0
    weighted_sum = 0
    for book, line in lines_by_book.items():
        weight = get_book_weight(book)
        weighted_sum += line * weight
        total_weight += weight

    weighted_consensus = round(weighted_sum / total_weight, 2) if total_weight > 0 else median(lines)

    # Get basic consensus
    result = calculate_consensus_line(lines)

    # Add weighted data
    return ConsensusResult(
        consensus_line=result.median_line,
        mean_line=result.mean_line,
        median_line=result.median_line,
        min_line=result.min_line,
        max_line=result.max_line,
        spread_range=result.spread_range,
        books_count=result.books_count,
        weighted_consensus=weighted_consensus,
        sharpest_book=sharpest_book,
        sharpest_line=sharpest_line,
    )


def line_vs_consensus(
    line: float, consensus: float, bet_type: str = "spread"
) -> dict[str, any]:
    """Compare a line against consensus.

    Args:
        line: The line to compare
        consensus: The consensus line
        bet_type: "spread" or "total"

    Returns:
        Dict with deviation info and interpretation
    """
    deviation = round(line - consensus, 2)

    if bet_type == "spread":
        if deviation < 0:
            interpretation = f"{abs(deviation)} pts better for favorite"
        elif deviation > 0:
            interpretation = f"{abs(deviation)} pts better for underdog"
        else:
            interpretation = "At consensus"
    else:  # total
        if deviation < 0:
            interpretation = f"{abs(deviation)} pts lower (favors under)"
        elif deviation > 0:
            interpretation = f"{abs(deviation)} pts higher (favors over)"
        else:
            interpretation = "At consensus"

    return {
        "line": line,
        "consensus": consensus,
        "deviation": deviation,
        "deviation_abs": abs(deviation),
        "interpretation": interpretation,
        "is_off_market": abs(deviation) >= 0.5,
    }


def calculate_market_agreement(lines: list[float]) -> float:
    """Calculate how much the market agrees (0-100 scale).

    Low agreement = opportunity (books disagree)
    High agreement = efficient market

    Returns:
        Agreement score 0-100 (100 = perfect agreement)
    """
    if len(lines) < 2:
        return 100.0

    line_range = max(lines) - min(lines)

    # Scale: 0 range = 100% agreement, 3+ range = 0% agreement
    if line_range >= 3:
        return 0.0

    return round((1 - line_range / 3) * 100, 1)
