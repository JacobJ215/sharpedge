#!/usr/bin/env python3
"""Download historical betting data from Kaggle and other sources.

This script downloads freely available historical sports betting data
for training ML models.

Data Sources:
- Kaggle NFL scores and betting data (tobycrabtree)
- Kaggle NBA betting data 2007-2025 (cviaxmiwnptr)
- ESPN API for recent game results

Usage:
    python scripts/download_historical_data.py

Requirements:
    - kaggle CLI configured with API credentials
    - Or manual download from Kaggle website
"""

from pathlib import Path
import subprocess
import urllib.request
import json

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Kaggle datasets
KAGGLE_DATASETS = [
    {
        "name": "NFL Scores and Betting Data",
        "dataset": "tobycrabtree/nfl-scores-and-betting-data",
        "output_dir": "nfl_betting",
        "url": (
            "https://www.kaggle.com/datasets/tobycrabtree/"
            "nfl-scores-and-betting-data"
        ),
    },
    {
        "name": "NBA Betting Data 2007-2025",
        "dataset": "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024",
        "output_dir": "nba_betting",
        "url": (
            "https://www.kaggle.com/datasets/cviaxmiwnptr/"
            "nba-betting-data-october-2007-to-june-2024"
        ),
    },
]

# ESPN API endpoints (free, no auth required)
ESPN_ENDPOINTS = {
    "nfl_scoreboard": (
        "https://site.api.espn.com/apis/site/v2/sports/"
        "football/nfl/scoreboard"
    ),
    "nba_scoreboard": (
        "https://site.api.espn.com/apis/site/v2/sports/"
        "basketball/nba/scoreboard"
    ),
    "mlb_scoreboard": (
        "https://site.api.espn.com/apis/site/v2/sports/"
        "baseball/mlb/scoreboard"
    ),
    "nhl_scoreboard": (
        "https://site.api.espn.com/apis/site/v2/sports/"
        "hockey/nhl/scoreboard"
    ),
}


def check_kaggle_cli() -> bool:
    """Check if Kaggle CLI is installed and configured."""
    try:
        result = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def download_kaggle_dataset(dataset: str, output_dir: Path) -> bool:
    """Download a Kaggle dataset using the CLI."""
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "kaggle",
                "datasets",
                "download",
                "-d",
                dataset,
                "-p",
                str(output_dir),
                "--unzip",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"  Downloaded successfully to {output_dir}")
            return True
        else:
            print(f"  Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Error downloading: {e}")
        return False


def fetch_espn_data(endpoint_name: str, url: str, output_dir: Path) -> bool:
    """Fetch data from ESPN API."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{endpoint_name}.json"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  Saved {endpoint_name} to {output_file}")
        return True
    except Exception as e:
        print(f"  Error fetching {endpoint_name}: {e}")
        return False


def print_manual_download_instructions():
    """Print instructions for manual Kaggle download."""
    print("\n" + "=" * 60)
    print("MANUAL DOWNLOAD INSTRUCTIONS")
    print("=" * 60)
    print("\nKaggle CLI not configured. Please download manually:\n")

    for ds in KAGGLE_DATASETS:
        output_dir = RAW_DIR / ds["output_dir"]
        print(f"1. {ds['name']}")
        print(f"   URL: {ds['url']}")
        print(f"   Download and extract to: {output_dir}")
        print()

    print("After downloading, run this script again to process the data.")
    print("=" * 60 + "\n")


def main():
    """Main download function."""
    print("=" * 60)
    print("SharpEdge Historical Data Downloader")
    print("=" * 60)

    # Create directories
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Check for Kaggle CLI
    has_kaggle = check_kaggle_cli()

    if has_kaggle:
        print("\nKaggle CLI detected. Downloading datasets...\n")
        for ds in KAGGLE_DATASETS:
            print(f"Downloading: {ds['name']}")
            output_dir = RAW_DIR / ds["output_dir"]
            download_kaggle_dataset(ds["dataset"], output_dir)
    else:
        print_manual_download_instructions()

    # Fetch ESPN data (always available)
    print("\nFetching ESPN API data...\n")
    espn_dir = RAW_DIR / "espn"
    for name, url in ESPN_ENDPOINTS.items():
        print(f"Fetching: {name}")
        fetch_espn_data(name, url, espn_dir)

    # Check what data we have
    print("\n" + "=" * 60)
    print("DATA INVENTORY")
    print("=" * 60)

    for ds in KAGGLE_DATASETS:
        output_dir = RAW_DIR / ds["output_dir"]
        if output_dir.exists() and any(output_dir.iterdir()):
            files = list(output_dir.glob("*"))
            print(f"\n{ds['name']}: {len(files)} files")
            for f in files[:5]:
                size = f.stat().st_size / 1024
                print(f"  - {f.name} ({size:.1f} KB)")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
        else:
            print(f"\n{ds['name']}: NOT DOWNLOADED")

    print("\n" + "=" * 60)
    print("Next step: Run 'python scripts/process_historical_data.py'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
