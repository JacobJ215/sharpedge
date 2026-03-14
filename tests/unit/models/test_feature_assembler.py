"""Tests for GameFeatures MODEL-02 extension and FeatureAssembler.

TDD contract for Plan 05-02:
- Task 1: GameFeatures with MODEL-02 fields + sport-specific median imputation
- Task 2: FeatureAssembler assembles feature vector from game_context
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from sharpedge_models.ml_inference import SPORT_MEDIANS, GameFeatures


# ---------------------------------------------------------------------------
# Task 1: GameFeatures MODEL-02 fields
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_game_context():
    """Minimal game_context dict with required fields."""
    return {
        "home_team": "Kansas City Chiefs",
        "away_team": "Los Angeles Chargers",
        "sport": "nfl",
        "spread_line": -3.5,
    }


@pytest.fixture
def cross_timezone_game_context():
    """Game context where away team crosses 2+ time zones (LA->Boston = 3tz)."""
    return {
        "home_team": "New England Patriots",
        "away_team": "Los Angeles Rams",
        "sport": "nfl",
        "spread_line": -1.5,
    }


@pytest.fixture
def same_timezone_game_context():
    """Game context where teams share the same timezone."""
    return {
        "home_team": "New York Giants",
        "away_team": "New England Patriots",
        "sport": "nfl",
        "spread_line": -2.5,
    }


def test_all_model02_fields_present():
    """GameFeatures has all 16 new MODEL-02 fields."""
    gf = GameFeatures(home_team="Team A", away_team="Team B", sport="nfl")

    # 10-game rolling form
    assert hasattr(gf, "home_ppg_10g")
    assert hasattr(gf, "home_papg_10g")
    assert hasattr(gf, "away_ppg_10g")
    assert hasattr(gf, "away_papg_10g")

    # Matchup history
    assert hasattr(gf, "h2h_home_cover_rate")
    assert hasattr(gf, "h2h_total_games")

    # Injury impact
    assert hasattr(gf, "home_injury_impact")
    assert hasattr(gf, "away_injury_impact")

    # Market sentiment
    assert hasattr(gf, "line_movement_velocity")
    assert hasattr(gf, "public_pct_home")

    # Weather / travel
    assert hasattr(gf, "weather_impact_score")
    assert hasattr(gf, "travel_penalty")

    # Cross-cutting
    assert hasattr(gf, "home_away_split_delta")
    assert hasattr(gf, "opponent_strength_home")
    assert hasattr(gf, "opponent_strength_away")
    assert hasattr(gf, "key_number_proximity")


def test_existing_fields_unchanged():
    """Original fields still present and unchanged."""
    gf = GameFeatures(
        home_team="Packers",
        away_team="Bears",
        sport="nfl",
        home_ppg_5g=24.5,
        spread_line=-3.0,
        home_rest_days=7,
    )
    assert gf.home_ppg_5g == 24.5
    assert gf.spread_line == -3.0
    assert gf.home_rest_days == 7
    assert gf.home_papg_5g is None
    assert gf.total_line is None


def test_to_array_no_none():
    """to_array() with None MODEL-02 fields uses sport medians — no NaN."""
    gf = GameFeatures(home_team="Team A", away_team="Team B", sport="nfl")
    feature_names = [
        "home_ppg_10g",
        "home_papg_10g",
        "away_ppg_10g",
        "away_papg_10g",
        "home_ats_10g",
        "away_ats_10g",
        "h2h_home_cover_rate",
        "home_injury_impact",
        "away_injury_impact",
        "line_movement_velocity",
        "public_pct_home",
        "weather_impact_score",
        "travel_penalty",
        "home_away_split_delta",
        "opponent_strength_home",
        "opponent_strength_away",
        "key_number_proximity",
        "home_rest_days",
        "away_rest_days",
    ]
    arr = gf.to_array(feature_names)
    assert not np.any(np.isnan(arr)), f"NaN values found: {arr}"
    assert arr.shape == (1, len(feature_names))


def test_to_array_uses_median_not_zero_nfl():
    """to_array() for NFL imputes home_ppg_10g with SPORT_MEDIANS value, not 0.0."""
    gf = GameFeatures(home_team="Team A", away_team="Team B", sport="nfl")
    arr = gf.to_array(["home_ppg_10g"])
    expected = SPORT_MEDIANS["nfl"]["home_ppg_10g"]
    assert arr[0, 0] == expected, f"Expected {expected}, got {arr[0, 0]}"


def test_sport_medians_has_required_keys():
    """SPORT_MEDIANS dict contains nfl and nba with required fields."""
    required_keys = {
        "home_ppg_10g",
        "away_ppg_10g",
        "h2h_home_cover_rate",
        "home_injury_impact",
        "travel_penalty",
        "home_rest_days",
    }
    for sport in ("nfl", "nba"):
        assert sport in SPORT_MEDIANS
        for key in required_keys:
            assert key in SPORT_MEDIANS[sport], f"Missing {key} in {sport}"


# ---------------------------------------------------------------------------
# Task 2: FeatureAssembler
# ---------------------------------------------------------------------------


def test_assemble_returns_game_features(minimal_game_context):
    """FeatureAssembler.assemble returns a GameFeatures instance."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler()
    result = assembler.assemble(minimal_game_context)
    assert isinstance(result, GameFeatures), (
        f"Expected GameFeatures instance, got {type(result)}"
    )


def test_travel_penalty_two_zones(cross_timezone_game_context):
    """When away_team crosses 2+ time zones, travel_penalty < 0.

    Fixture: home=New England Patriots (ET), away=Los Angeles Rams (PT).
    Rams traveling to Boston cross 3 timezones (PT->ET).
    """
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler()
    result = assembler.assemble(cross_timezone_game_context)
    assert result.travel_penalty < 0, (
        f"Expected travel_penalty < 0 for 3 tz crossings, got {result.travel_penalty}"
    )


def test_travel_penalty_zero_zones(same_timezone_game_context):
    """When teams are in same timezone, travel_penalty == 0.0."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler()
    result = assembler.assemble(same_timezone_game_context)
    assert result.travel_penalty == 0.0, (
        f"Expected travel_penalty == 0.0 for same timezone, got {result.travel_penalty}"
    )


def test_imputation_not_zero(minimal_game_context):
    """When Supabase client unavailable, fields impute from SPORT_MEDIANS, not 0.0."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler(supabase_client=None)
    result = assembler.assemble(minimal_game_context)

    # to_array() must impute with medians, not zeros
    feature_names = ["home_ppg_10g", "away_ppg_10g", "public_pct_home"]
    arr = result.to_array(feature_names)
    nfl_medians = SPORT_MEDIANS["nfl"]
    assert arr[0, 0] == nfl_medians["home_ppg_10g"]
    assert arr[0, 1] == nfl_medians["away_ppg_10g"]
    assert arr[0, 2] == nfl_medians["public_pct_home"]


def test_to_array_no_none_assembled(minimal_game_context):
    """Assembled GameFeatures.to_array returns array with no NaN values."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler()
    result = assembler.assemble(minimal_game_context)
    feature_names = [
        "home_ppg_10g",
        "away_ppg_10g",
        "h2h_home_cover_rate",
        "home_injury_impact",
        "away_injury_impact",
        "line_movement_velocity",
        "public_pct_home",
        "travel_penalty",
        "spread_line",
    ]
    arr = result.to_array(feature_names)
    assert isinstance(arr, np.ndarray), f"Expected ndarray, got {type(arr)}"
    assert not np.any(np.isnan(arr)), f"to_array() returned NaN values: {arr}"


def test_assembler_graceful_espn_failure():
    """FeatureAssembler continues when ESPN client raises exception."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    mock_espn = MagicMock()
    mock_espn.get_scoreboard.side_effect = Exception("ESPN API down")
    assembler = FeatureAssembler(espn_client=mock_espn)
    game_context = {
        "home_team": "Green Bay Packers",
        "away_team": "Chicago Bears",
        "sport": "nfl",
    }
    result = assembler.assemble(game_context)
    assert isinstance(result, GameFeatures)
    assert result.home_injury_impact == 0.0
    assert result.away_injury_impact == 0.0


def test_market_sentiment_velocity_computed():
    """line_movement_velocity is computed from line_movements list in context."""
    from sharpedge_models.feature_assembler import FeatureAssembler

    assembler = FeatureAssembler()
    game_context = {
        "home_team": "Green Bay Packers",
        "away_team": "Chicago Bears",
        "sport": "nfl",
        "line_movements": [
            {"line": -3.0, "timestamp": "2024-11-08T12:00:00Z"},
            {"line": -3.5, "timestamp": "2024-11-08T18:00:00Z"},
            {"line": -4.0, "timestamp": "2024-11-09T00:00:00Z"},
        ],
    }
    result = assembler.assemble(game_context)
    assert result.line_movement_velocity is not None
    # Velocity: line moved -1.0 over 12 hours -> negative velocity
    assert result.line_movement_velocity < 0


def test_compute_timezone_crossings_patriots_to_rams():
    """compute_timezone_crossings returns >=2 for ET->PT trip."""
    from sharpedge_models.feature_assembler import compute_timezone_crossings

    crossings = compute_timezone_crossings("New England Patriots", "Los Angeles Rams")
    assert crossings >= 2


def test_compute_timezone_crossings_same_zone():
    """compute_timezone_crossings returns 0 for same-timezone teams."""
    from sharpedge_models.feature_assembler import compute_timezone_crossings

    crossings = compute_timezone_crossings("New York Giants", "New England Patriots")
    assert crossings == 0


def test_compute_timezone_crossings_unknown_team():
    """compute_timezone_crossings returns 0 when team not in TEAM_TIMEZONES."""
    from sharpedge_models.feature_assembler import compute_timezone_crossings

    crossings = compute_timezone_crossings("Unknown FC", "Los Angeles Rams")
    assert crossings == 0


def test_travel_penalty_from_crossings():
    """travel_penalty_from_crossings returns correct penalty values."""
    from sharpedge_models.feature_assembler import travel_penalty_from_crossings

    assert travel_penalty_from_crossings(0) == 0.0
    assert travel_penalty_from_crossings(1) == 0.0
    assert travel_penalty_from_crossings(2) == -0.15
    assert travel_penalty_from_crossings(3) == -0.3
    assert travel_penalty_from_crossings(4) == -0.3
