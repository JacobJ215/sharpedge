"""Bureau of Labor Statistics (BLS) API client stub — Phase 9 plan 01.

Full implementation in plan 02.
"""

from __future__ import annotations

import os

BLS_RELEASE_CALENDAR_URL = "https://www.bls.gov/schedule/news_release/"

_OFFLINE_ENV = "BLS_OFFLINE"


class BLSClient:
    """Fetches economic release schedule data from BLS.

    All methods raise NotImplementedError until plan 02.
    Set BLS_OFFLINE=true to get (30, False) defaults without network calls.
    """

    def __init__(self) -> None:
        self._offline = os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")

    def get_days_since_last_release(self, series: str) -> int:
        """Return days since most recent data release for the given series.

        Args:
            series: BLS series name, e.g. "CPI", "PPI", "NFP".

        Returns:
            Non-negative int.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")

    def get_is_release_imminent(self, series: str, threshold_days: int = 3) -> bool:
        """Return True if a release for series is within threshold_days.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")
