"""Portfolio correlation detection for PM vs sportsbook positions.

Uses token-overlap similarity to detect when a prediction market and an active
sportsbook bet share the same team, player, or event entity.

Formula: correlation = |shared_tokens| / max(|tokens_a|, |tokens_b|)

No NLP library required — token matching is sufficient for this use case.
"""

import re

__all__ = ["DEFAULT_STOPWORDS", "compute_entity_correlation", "detect_correlated_positions"]

DEFAULT_STOPWORDS: frozenset[str] = frozenset(
    {
        "will",
        "the",
        "be",
        "in",
        "at",
        "a",
        "an",
        "to",
        "of",
        "for",
        "on",
        "by",
        "is",
        "are",
        "was",
        "were",
        "and",
        "or",
        "not",
        "win",
        "vs",
        "per",
        "title",
        "championship",
        "game",
        "series",
    }
)


def _tokenize(text: str, stopwords: frozenset[str] | None = None) -> frozenset[str]:
    """Normalize text to a set of meaningful tokens."""
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS
    # Lowercase, strip punctuation, split on whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = {t for t in cleaned.split() if t and t not in stopwords}
    return frozenset(tokens)


def compute_entity_correlation(
    text_a: str,
    text_b: str,
    stopwords: frozenset[str] | None = None,
) -> float:
    """Token-overlap correlation between two market descriptions. Returns 0.0-1.0."""
    tokens_a = _tokenize(text_a, stopwords)
    tokens_b = _tokenize(text_b, stopwords)

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    shared = tokens_a & tokens_b
    # Use min denominator (Jaccard-like but entity-biased toward shorter set)
    # This ensures a single shared entity in a short title yields > 0.5
    return len(shared) / min(len(tokens_a), len(tokens_b))


def _get_field(obj: object, field: str) -> str:
    """Get a field from either a dict or an object with attributes."""
    if isinstance(obj, dict):
        return str(obj.get(field, "") or "")
    return str(getattr(obj, field, "") or "")


def detect_correlated_positions(
    pm_market_title: str,
    active_bets: list,
    threshold: float = 0.6,
) -> list:
    """Return active bets correlated with pm_market_title above threshold.

    Checks correlation against both 'selection' and 'game' fields of each bet.
    Returns highest-correlation match per bet if it exceeds threshold.

    Args:
        pm_market_title: Title of the prediction market.
        active_bets: List of bet objects (dicts or objects with selection/game attrs).
        threshold: Minimum correlation score to include a bet (default 0.6).
    """
    if not active_bets:
        return []

    correlated: list = []
    for bet in active_bets:
        selection = _get_field(bet, "selection")
        game = _get_field(bet, "game")

        corr_selection = compute_entity_correlation(pm_market_title, selection)
        corr_game = compute_entity_correlation(pm_market_title, game)
        max_corr = max(corr_selection, corr_game)

        if max_corr > threshold:
            correlated.append(bet)

    return correlated
