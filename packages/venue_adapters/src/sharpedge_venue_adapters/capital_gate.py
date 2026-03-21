"""Capital gate — enforces all four gate conditions before live Kalshi execution.

Phase 13: CapitalGate stub module (Wave 0 — RED phase). All method bodies raise
NotImplementedError. Plan 02 replaces them with real implementations.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from supabase import create_client  # type: ignore[import]
except ImportError:  # pragma: no cover — supabase optional at import time
    create_client = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

CATEGORIES = ("crypto", "economic", "entertainment", "political", "weather")
_DEFAULT_MODELS_DIR = Path("data/models/pm")
_DEFAULT_APPROVAL_PATH = Path("data/live_approval.json")


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class CapitalGateError(RuntimeError):
    """Raised by assert_ready() when one or more gate conditions fail."""


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass
class GateCondition:
    """Result of evaluating a single capital gate condition."""

    name: str
    passed: bool
    reason: str


@dataclass
class GateStatus:
    """Aggregate result of all capital gate conditions."""

    conditions: list[GateCondition] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.conditions)

    @property
    def failures(self) -> list[GateCondition]:
        return [c for c in self.conditions if not c.passed]


# ---------------------------------------------------------------------------
# CapitalGate
# ---------------------------------------------------------------------------


class CapitalGate:
    """Enforces all four capital gate conditions before live execution.

    Conditions:
      GATE-01: All 5 .joblib model artifacts exist in models_dir.
      GATE-02: At least min_paper_days of shadow-ledger history with
               acceptable positive_signal_rate and mean_edge.
      GATE-03: Operator has written a valid live_approval.json.
      GATE-04: Daily realized loss has not exceeded daily_loss_pct threshold.
    """

    def __init__(
        self,
        models_dir: Path = _DEFAULT_MODELS_DIR,
        approval_path: Path = _DEFAULT_APPROVAL_PATH,
        min_paper_days: int = 7,
        min_positive_rate: float = 0.55,
        min_mean_edge: float = 0.015,
        daily_loss_pct: float = 0.10,
    ) -> None:
        self._models_dir = models_dir
        self._approval_path = approval_path
        self._min_paper_days = min_paper_days
        self._min_positive_rate = min_positive_rate
        self._min_mean_edge = min_mean_edge
        self._daily_loss_pct = daily_loss_pct
        # GATE-04 internal state (mirrors CircuitBreakerState pattern)
        self._daily_loss: float = 0.0
        self._loss_reset_date: str = ""

    def check(self) -> GateStatus:
        """Evaluate all four gate conditions. Returns GateStatus without raising."""
        raise NotImplementedError

    def assert_ready(self) -> None:
        """Call check(); raise CapitalGateError if any condition failed.

        Collects ALL failures before raising so the operator sees the full
        picture in one error (D-02).
        """
        status = self.check()
        if not status.all_passed:
            reasons = "; ".join(f.reason for f in status.failures)
            raise CapitalGateError(f"Capital gate failed: {reasons}")

    def record_daily_loss(self, amount_usd: float, bankroll: float) -> bool:
        """Record realized loss in USD. Returns True if circuit breaker triggered.

        On breach: renames live_approval.json to live_approval.json.disabled
        to invalidate GATE-03 and preserve the audit trail (D-14).
        """
        raise NotImplementedError

    @classmethod
    def from_env(cls) -> "CapitalGate":
        """Construct CapitalGate with thresholds from environment variables.

        Reads:
          CAPITAL_MODELS_DIR           (default: data/models/pm)
          CAPITAL_APPROVAL_PATH        (default: data/live_approval.json)
          CAPITAL_MIN_PAPER_DAYS       (default: 7)
          CAPITAL_MIN_POSITIVE_RATE    (default: 0.55)
          CAPITAL_MIN_MEAN_EDGE        (default: 0.015)
          CIRCUIT_BREAKER_DAILY_LOSS_PCT (default: 0.10)
        """
        raise NotImplementedError
