"""Bureau of Labor Statistics (BLS) client — Phase 9 plan 02.

Provides economic release proximity features for economic category prediction
market resolution model feature engineering.

Note: BLS release calendar is complex to parse. We use a static monthly/quarterly
cadence dict — sufficient accuracy for ML feature engineering at training time.
"""

from __future__ import annotations

import os
from datetime import date

BLS_RELEASE_CALENDAR_URL = "https://www.bls.gov/schedule/news_release/"

_OFFLINE_ENV = "BLS_OFFLINE"

# Static release cadence in days for key BLS economic series.
# Monthly series use 30 days; quarterly GDP uses 90 days.
RELEASE_CADENCE_DAYS: dict[str, int] = {
    "CPI": 30,
    "PPI": 30,
    "NFP": 30,
    "GDP": 90,
}

_DEFAULT_CADENCE = 30


def _is_offline() -> bool:
    return os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")


class BLSClient:
    """Provides approximate days-since-last-release for BLS economic series.

    Uses static cadence dict (RELEASE_CADENCE_DAYS) — no live BLS API calls
    required. The approximation is based on today's day-of-month relative to
    the known monthly/quarterly release cadence.

    Args:
        offline: If True, returns (30, False) without any computation.
                 Can also be set via BLS_OFFLINE=true env var.
    """

    def __init__(self, offline: bool = False) -> None:
        self._offline = offline or _is_offline()

    def get_days_since_last_release(self, series: str) -> int:
        """Return approximate days since most recent data release for series.

        Uses today's day-of-month / cadence to estimate position in the release cycle.

        Args:
            series: BLS series name — one of "CPI", "PPI", "NFP", "GDP".
                    Unknown series returns 30.

        Returns:
            Non-negative int. Returns 30 in offline mode or for unknown series.
        """
        if self._offline:
            return 30
        try:
            series_upper = series.upper()
            if series_upper not in RELEASE_CADENCE_DAYS:
                return 30
            cadence = RELEASE_CADENCE_DAYS[series_upper]
            today = date.today()
            # Approximate: day-of-month as proxy for days-since-last-monthly-release.
            # For quarterly (GDP): use day_of_year % cadence.
            if cadence == 90:
                day_of_year = today.timetuple().tm_yday
                return int(day_of_year % cadence)
            # Monthly: day of month approximates days since last release.
            return min(today.day, cadence)
        except Exception:
            return 30

    def get_is_release_imminent(self, series: str, threshold_days: int = 3) -> bool:
        """Return True if a release for series is within threshold_days of next release.

        Args:
            series: BLS series name — one of "CPI", "PPI", "NFP", "GDP".
            threshold_days: Window (in days) before next release to flag as imminent.

        Returns:
            bool. Returns False in offline mode or for unknown series.
        """
        if self._offline:
            return False
        try:
            series_upper = series.upper()
            if series_upper not in RELEASE_CADENCE_DAYS:
                return False
            cadence = RELEASE_CADENCE_DAYS[series_upper]
            days_since = self.get_days_since_last_release(series)
            days_until_next = cadence - days_since
            return days_until_next <= threshold_days
        except Exception:
            return False
