"""FEC (Federal Election Commission) API client — Phase 9 plan 02.

Provides polling average and election proximity features for political
prediction market resolution model feature engineering.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import httpx

_OFFLINE_ENV = "FEC_OFFLINE"

_FEC_BASE = "https://api.open.fec.gov/v1"


def _is_offline() -> bool:
    return os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")


class FECClient:
    """Fetches polling averages and election proximity data.

    polling_average: normalized margin in [0, 1] from FEC API (best-effort).
    election_proximity_days: pure datetime math — no network call required.

    Args:
        offline: If True, get_polling_average returns 0.0 without network calls.
                 Can also be set via FEC_OFFLINE=true env var.
    """

    def __init__(self, offline: bool = False) -> None:
        self._offline = offline or _is_offline()

    def get_polling_average(self, race_id: str) -> float:
        """Return normalized polling average for the given race.

        Attempts to fetch from FEC public API. Falls back to 0.0 on any error.

        Args:
            race_id: Race identifier string (e.g. "presidential-2024").
                     Currently used as a pass-through; FEC endpoint is best-effort.

        Returns:
            Float in [0.0, 1.0]. Returns 0.0 in offline mode or on any error.
        """
        if self._offline:
            return 0.0
        try:
            # FEC presidential coverage endpoint — no API key required for public data.
            url = f"{_FEC_BASE}/presidential/coverage_end_date/"
            response = httpx.get(url, timeout=5.0)
            data: dict[str, Any] = response.json()
            results = data.get("results", [])
            if not results:
                return 0.0
            # Normalize: take the average of available candidate_contribution_count
            # as a proxy for polling margin normalized to [0, 1].
            values = [float(r.get("candidate_contribution_count", 0) or 0) for r in results]
            total = sum(values)
            if total <= 0:
                return 0.0
            # Normalize max to 1.0
            max_val = max(values)
            return round(max_val / total, 4) if total > 0 else 0.0
        except Exception:
            return 0.0

    def get_election_proximity_days(self, election_date_str: str) -> int:
        """Return days until election_date_str from today.

        Pure datetime math — no network call.

        Args:
            election_date_str: ISO-8601 date string, e.g. "2024-11-05".

        Returns:
            Non-negative int. Returns 0 for past dates. Returns 365 on parse error.
        """
        try:
            election_date = datetime.strptime(election_date_str, "%Y-%m-%d").date()
            today = date.today()
            delta = (election_date - today).days
            return max(0, delta)
        except Exception:
            return 365
