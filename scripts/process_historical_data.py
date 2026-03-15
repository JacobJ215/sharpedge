#!/usr/bin/env python3
"""Process historical betting data for ML model training.

This script processes raw historical data and creates clean datasets
suitable for training spread and totals prediction models.

Features engineered:
- Team performance metrics (rolling averages)
- Rest days and schedule factors
- Home/away splits
- Historical ATS (against the spread) performance
- Weather indicators (where available)
- Line movement patterns

Output:
- data/processed/nfl_training.parquet
- data/processed/nba_training.parquet
- data/processed/feature_metadata.json
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# Directories
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def load_nfl_data() -> pd.DataFrame | None:
    """Load NFL betting data from Kaggle dataset."""
    nfl_dir = RAW_DIR / "nfl_betting"

    # Try different possible file names
    possible_files = [
        "spreadspoke_scores.csv",
        "nfl_scores.csv",
        "scores.csv",
        "nfl_betting_data.csv",
    ]

    for filename in possible_files:
        filepath = nfl_dir / filename
        if filepath.exists():
            print(f"Loading NFL data from {filepath}")
            df = pd.read_csv(filepath)
            print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
            return df

    # Check for any CSV files
    csv_files = list(nfl_dir.glob("*.csv"))
    if csv_files:
        print(f"Loading NFL data from {csv_files[0]}")
        df = pd.read_csv(csv_files[0])
        print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
        return df

    print("  NFL data not found")
    return None


def load_nba_data() -> pd.DataFrame | None:
    """Load NBA betting data from Kaggle dataset."""
    nba_dir = RAW_DIR / "nba_betting"

    csv_files = list(nba_dir.glob("*.csv"))
    if csv_files:
        # Load all CSV files and concatenate, skipping auxiliary files that
        # lack betting columns (e.g. metadata CSVs) to prevent schema mismatches.
        dfs = []
        for f in csv_files:
            print(f"Loading NBA data from {f.name}")
            df = pd.read_csv(f)
            cols_lower = {c.lower() for c in df.columns}
            has_betting = any(
                kw in col
                for col in cols_lower
                for kw in ("spread", "score", "total", "over_under")
            )
            if not has_betting:
                print(f"  Skipping {f.name}: no betting columns detected")
                continue
            dfs.append(df)

        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            print(f"  Loaded {len(combined)} total rows")
            return combined

    print("  NBA data not found")
    return None


def _parse_espn_scoreboard(json_path: Path) -> pd.DataFrame | None:
    """Parse ESPN scoreboard JSON into a flat DataFrame.

    ESPN scoreboard JSON structure:
    {"events": [{"date": "...", "competitions": [{"competitors": [
        {"homeAway": "home", "team": {"name": "..."}, "score": "..."},
        {"homeAway": "away", ...}
    ]}]}]}

    Returns None if file missing, parse fails, or no events found.
    """
    if not json_path.exists():
        return None
    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  JSON parse error for {json_path.name}: {e}")
        return None

    events = data.get("events", [])
    if not events:
        print(f"  No events found in {json_path.name}")
        return None

    rows = []
    for event in events:
        date_str = event.get("date", datetime.now().isoformat())
        for comp in event.get("competitions", []):
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            rows.append({
                "game_date": pd.to_datetime(date_str, utc=True, errors="coerce"),
                "home_team": home.get("team", {}).get("name", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "home_score": pd.to_numeric(home.get("score", None), errors="coerce"),
                "away_score": pd.to_numeric(away.get("score", None), errors="coerce"),
                "home_covered": None,
                "went_over": None,
            })

    if not rows:
        return None
    df = pd.DataFrame(rows)
    # Convert UTC-aware timestamps to naive (tz-convert first to handle tz-aware series)
    df["game_date"] = df["game_date"].dt.tz_convert(None)
    return df


def load_ncaab_data() -> pd.DataFrame | None:
    """Load NCAAB data from ESPN scoreboard JSON (current-week only)."""
    json_path = RAW_DIR / "espn" / "ncaab_scoreboard.json"
    df = _parse_espn_scoreboard(json_path)
    if df is None:
        print("  NCAAB ESPN data not found — skipping")
    return df


def load_mlb_data() -> pd.DataFrame | None:
    """Load MLB data from ESPN scoreboard JSON (current-week only)."""
    json_path = RAW_DIR / "espn" / "mlb_scoreboard.json"
    df = _parse_espn_scoreboard(json_path)
    if df is None:
        print("  MLB ESPN data not found — skipping")
    return df


def load_nhl_data() -> pd.DataFrame | None:
    """Load NHL data from ESPN scoreboard JSON (current-week only)."""
    json_path = RAW_DIR / "espn" / "nhl_scoreboard.json"
    df = _parse_espn_scoreboard(json_path)
    if df is None:
        print("  NHL ESPN data not found — skipping")
    return df


def zero_fill_domain_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add zero-filled columns for any DOMAIN_FEATURES entries missing from df.

    Prevents ValueError in _train_ensemble_for_sport() when ensemble columns
    derived from FeatureAssembler (live inference) are absent in historical data.
    """
    try:
        from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES
    except ImportError:
        return df  # graceful skip if models package not installed
    all_domain_cols = [col for cols in DOMAIN_FEATURES.values() for col in cols]
    for col in all_domain_cols:
        if col not in df.columns:
            df[col] = 0.0
    return df


def _finalize_processed_df(processed: pd.DataFrame, sport: str) -> pd.DataFrame:
    """Drop missing rows, sort by date, add season column."""
    required_cols = ["game_date", "home_team", "away_team", "home_score", "away_score"]
    missing_required = [c for c in required_cols if c not in processed.columns]
    if missing_required:
        print(f"  WARNING: Required columns not mapped: {missing_required} — rows missing these will be dropped")
    available_required = [c for c in required_cols if c in processed.columns]
    processed = processed.dropna(subset=available_required)
    if "game_date" in processed.columns:
        processed = processed.sort_values("game_date").reset_index(drop=True)
        processed["season"] = processed["game_date"].apply(
            lambda d: d.year if d.month >= 9 else d.year - 1 if pd.notna(d) else None
        )
    print(f"  Processed {len(processed)} games")
    return processed


def process_nfl_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process NFL data and engineer features.

    Expected columns (from spreadspoke dataset):
    - schedule_date, schedule_season, schedule_week
    - team_home, team_away
    - score_home, score_away
    - spread_favorite, spread_odds (or similar)
    - over_under_line
    """
    print("\nProcessing NFL data...")

    # Standardize column names (handle variations)
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    cols = df.columns.tolist()

    # Identify key columns by heuristic substring matching
    date_col = next((c for c in cols if "date" in c), None)
    home_team_col = next((c for c in cols if "home" in c and "team" in c), None)
    away_team_col = next((c for c in cols if "away" in c and "team" in c), None)
    home_score_col = next((c for c in cols if "home" in c and "score" in c), None)
    away_score_col = next((c for c in cols if "away" in c and "score" in c), None)
    spread_col = next((c for c in cols if "spread" in c and "line" not in c), None)
    total_col = next((c for c in cols if "over" in c or "total" in c), None)

    print(f"  Cols: date={date_col}, home={home_team_col}, away={away_team_col}, "
          f"h_score={home_score_col}, a_score={away_score_col}, spread={spread_col}, total={total_col}")

    # Create standardized dataframe
    processed = pd.DataFrame()

    if date_col:
        processed["game_date"] = pd.to_datetime(df[date_col], errors="coerce")

    if home_team_col and away_team_col:
        processed["home_team"] = df[home_team_col].astype(str)
        processed["away_team"] = df[away_team_col].astype(str)

    if home_score_col and away_score_col:
        processed["home_score"] = pd.to_numeric(df[home_score_col], errors="coerce")
        processed["away_score"] = pd.to_numeric(df[away_score_col], errors="coerce")
        processed["total_points"] = processed["home_score"] + processed["away_score"]
        processed["point_diff"] = processed["home_score"] - processed["away_score"]

    if spread_col:
        raw_spread = pd.to_numeric(df[spread_col], errors="coerce")
        # Normalize to home-team perspective: spreadspoke spread_favorite is always
        # from the favorite's side. Negate when away team is favorite.
        fav_col = next(
            (c for c in df.columns if "favorite" in c and "team" in c and "spread" not in c), None
        )
        if fav_col and home_team_col:
            home_is_fav = df[fav_col].str.strip().str.upper() == df[home_team_col].str.strip().str.upper()
            processed["spread_line"] = np.where(home_is_fav, raw_spread, -raw_spread)
        else:
            processed["spread_line"] = raw_spread

    if total_col:
        processed["total_line"] = pd.to_numeric(df[total_col], errors="coerce")

    # Calculate outcomes (spread_line normalized: negative = home favored)
    if "spread_line" in processed.columns and "point_diff" in processed.columns:
        delta = processed["point_diff"] + processed["spread_line"]
        processed["spread_result"] = np.where(delta > 0, "cover", np.where(delta < 0, "miss", "push"))
        processed["home_covered"] = processed["spread_result"] == "cover"
    if "total_line" in processed.columns and "total_points" in processed.columns:
        processed["total_result"] = np.where(
            processed["total_points"] > processed["total_line"], "over",
            np.where(processed["total_points"] < processed["total_line"], "under", "push"),
        )
        processed["went_over"] = processed["total_result"] == "over"

    return _finalize_processed_df(processed, "nfl")


def process_nba_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process NBA/ESPN-sourced data and engineer features.

    Reused by NCAAB, MLB, and NHL ESPN loaders (same heuristic column detection).
    """
    print("\nProcessing data...")

    # Standardize column names
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    cols = df.columns.tolist()

    # Prefer bare "home"/"away" names (Kaggle NBA) before heuristic matching
    date_col = next((c for c in cols if "date" in c), None)
    home_team_col = "home" if "home" in cols else next((c for c in cols if "home" in c and "team" in c), None)
    away_team_col = (
        "away" if "away" in cols
        else "visitor" if "visitor" in cols
        else next((c for c in cols if ("away" in c or "visitor" in c) and "team" in c), None)
    )
    home_score_col = next((c for c in cols if "home" in c and "score" in c), None)
    away_score_col = next((c for c in cols if ("away" in c or "visitor" in c) and "score" in c), None)
    spread_col = next((c for c in cols if "spread" in c and "line" not in c), None)
    total_col = next((c for c in cols if "over" in c or "total" in c), None)

    print(f"  Cols: date={date_col}, home={home_team_col}, away={away_team_col}, "
          f"h_score={home_score_col}, a_score={away_score_col}, spread={spread_col}, total={total_col}")

    processed = pd.DataFrame()

    if date_col:
        processed["game_date"] = pd.to_datetime(df[date_col], errors="coerce")

    if home_team_col and away_team_col:
        processed["home_team"] = df[home_team_col].astype(str)
        processed["away_team"] = df[away_team_col].astype(str)

    if home_score_col and away_score_col:
        processed["home_score"] = pd.to_numeric(df[home_score_col], errors="coerce")
        processed["away_score"] = pd.to_numeric(df[away_score_col], errors="coerce")
        processed["total_points"] = processed["home_score"] + processed["away_score"]
        processed["point_diff"] = processed["home_score"] - processed["away_score"]
    if spread_col:
        processed["spread_line"] = pd.to_numeric(df[spread_col], errors="coerce")
    if total_col:
        processed["total_line"] = pd.to_numeric(df[total_col], errors="coerce")

    # Calculate outcomes
    if "spread_line" in processed.columns and "point_diff" in processed.columns:
        delta = processed["point_diff"] + processed["spread_line"]
        processed["spread_result"] = np.where(delta > 0, "cover", np.where(delta < 0, "miss", "push"))
        processed["home_covered"] = processed["spread_result"] == "cover"
    if "total_line" in processed.columns and "total_points" in processed.columns:
        processed["total_result"] = np.where(
            processed["total_points"] > processed["total_line"], "over",
            np.where(processed["total_points"] < processed["total_line"], "under", "push"),
        )
        processed["went_over"] = processed["total_result"] == "over"

    return _finalize_processed_df(processed, "nba")


def engineer_rolling_features(
    df: pd.DataFrame, windows: list[int] = [3, 5, 10]
) -> pd.DataFrame:
    """Add rolling average features for each team."""
    print("\nEngineering rolling features...")

    if "home_team" not in df.columns or "home_score" not in df.columns:
        print("  Skipping - required columns not available")
        return df

    # Calculate rolling averages for each team
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    print(f"  Processing {len(teams)} teams...")

    for window in windows:
        roll = lambda x, w=window: x.rolling(w, min_periods=1).mean().shift(1)
        df[f"home_ppg_{window}g"] = df.groupby("home_team")["home_score"].transform(roll)
        df[f"home_papg_{window}g"] = df.groupby("home_team")["away_score"].transform(roll)
        df[f"away_ppg_{window}g"] = df.groupby("away_team")["away_score"].transform(roll)
        df[f"away_papg_{window}g"] = df.groupby("away_team")["home_score"].transform(roll)

    print(f"  Added {len(windows) * 4} rolling features")
    return df


def engineer_ats_features(
    df: pd.DataFrame, windows: list[int] = [5, 10, 20]
) -> pd.DataFrame:
    """Add ATS (against the spread) performance features."""
    print("\nEngineering ATS features...")

    if "home_covered" not in df.columns:
        print("  Skipping - spread results not available")
        return df

    # Compute away_covered_temp once outside the loop to avoid repeated
    # create/drop side-effects on the DataFrame reference.
    df["away_covered_temp"] = ~df["home_covered"]
    for window in windows:
        roll = lambda x, w=window: x.rolling(w, min_periods=1).mean().shift(1)
        df[f"home_ats_{window}g"] = df.groupby("home_team")["home_covered"].transform(roll)
        df[f"away_ats_{window}g"] = df.groupby("away_team")["away_covered_temp"].transform(roll)
    df.drop("away_covered_temp", axis=1, inplace=True)

    print(f"  Added {len(windows) * 2} ATS features")
    return df


def save_processed_data(df: pd.DataFrame, name: str) -> None:
    """Save processed data to parquet format."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / f"{name}_training.parquet"

    df.to_parquet(output_path, index=False)
    print(f"\nSaved {len(df)} rows to {output_path}")

    # Also save CSV for inspection
    csv_path = PROCESSED_DIR / f"{name}_training.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV copy to {csv_path}")


def save_feature_metadata(features: dict) -> None:
    """Save feature metadata for model training."""
    metadata_path = PROCESSED_DIR / "feature_metadata.json"

    with open(metadata_path, "w") as f:
        json.dump(features, f, indent=2)

    print(f"\nSaved feature metadata to {metadata_path}")


def main():
    """Main processing function."""
    print("=" * 60)
    print("SharpEdge Historical Data Processor")
    print("=" * 60)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed_any = False

    # Process NFL data
    nfl_df = load_nfl_data()
    if nfl_df is not None:
        nfl_processed = process_nfl_data(nfl_df)
        if len(nfl_processed) > 0:
            nfl_processed = engineer_rolling_features(nfl_processed)
            nfl_processed = engineer_ats_features(nfl_processed)
            nfl_processed = zero_fill_domain_features(nfl_processed)
            save_processed_data(nfl_processed, "nfl")
            processed_any = True

    # Process NBA data
    nba_df = load_nba_data()
    if nba_df is not None:
        nba_processed = process_nba_data(nba_df)
        if len(nba_processed) > 0:
            nba_processed = engineer_rolling_features(nba_processed)
            nba_processed = engineer_ats_features(nba_processed)
            nba_processed = zero_fill_domain_features(nba_processed)
            save_processed_data(nba_processed, "nba")
            processed_any = True

    # ESPN-sourced sports (NCAAB, MLB, NHL) — current-week scoreboard data
    for sport_name, loader in [
        ("ncaab", load_ncaab_data),
        ("mlb", load_mlb_data),
        ("nhl", load_nhl_data),
    ]:
        try:
            sport_df = loader()
            if sport_df is None:
                print(f"  Skipping {sport_name}: no data")
                continue
            sport_df = process_nba_data(sport_df)  # reuse generic column detection
            if len(sport_df) == 0:
                print(f"  Skipping {sport_name}: no valid rows after processing")
                continue
            sport_df = engineer_rolling_features(sport_df)
            sport_df = engineer_ats_features(sport_df)
            sport_df = zero_fill_domain_features(sport_df)
            save_processed_data(sport_df, sport_name)
            processed_any = True
        except Exception as e:
            print(f"  Error processing {sport_name}: {e} — skipping")

    # Save feature metadata
    feature_metadata = {
        "rolling_windows": [3, 5, 10],
        "ats_windows": [5, 10, 20],
        "target_columns": {"spread": "home_covered", "total": "went_over"},
        "feature_groups": {
            "rolling_offense": ["home_ppg_*", "away_ppg_*"],
            "rolling_defense": ["home_papg_*", "away_papg_*"],
            "ats_performance": ["home_ats_*", "away_ats_*"],
        },
        "processed_at": datetime.now().isoformat(),
    }
    save_feature_metadata(feature_metadata)

    print("\n" + "=" * 60)
    if processed_any:
        print("Processing complete!")
        print("Next step: Run 'python scripts/train_models.py'")
    else:
        print("No data processed. Please download data first:")
        print("  python scripts/download_historical_data.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
