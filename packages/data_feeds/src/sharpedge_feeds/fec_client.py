"""FEC (Federal Election Commission) API client stub — Phase 9 plan 01.

Full implementation in plan 02.
"""

from __future__ import annotations

import os

_OFFLINE_ENV = "FEC_OFFLINE"


class FECClient:
    """Fetches polling averages and election proximity from FEC / aggregator APIs.

    All methods raise NotImplementedError until plan 02.
    Set FEC_OFFLINE=true to get safe defaults without network calls.
    """

    def __init__(self) -> None:
        self._offline = os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")

    def get_polling_average(self, race_id: str) -> float:
        """Return polling average probability [0, 1] for the given race.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")

    def get_election_proximity_days(self, election_date_str: str) -> int:
        """Return days until election_date_str (ISO-8601 date string).

        Returns >= 0. Past election dates return 0.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")
