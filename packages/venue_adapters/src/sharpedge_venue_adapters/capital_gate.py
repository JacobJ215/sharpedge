"""Capital gate — enforces all four gate conditions before live Kalshi execution.

Phase 13: Full CapitalGate implementation (Plan 02 — GREEN phase).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

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

logger = logging.getLogger(__name__)


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

    # ------------------------------------------------------------------
    # Private gate checks
    # ------------------------------------------------------------------

    def _check_model_artifacts(self) -> GateCondition:
        """GATE-01: All 5 .joblib artifacts must exist in models_dir."""
        missing = [cat for cat in CATEGORIES if not (self._models_dir / f"{cat}.joblib").exists()]
        if missing:
            return GateCondition(
                name="GATE-01",
                passed=False,
                reason=f"Missing .joblib artifacts: {', '.join(missing)}",
            )
        return GateCondition(
            name="GATE-01",
            passed=True,
            reason="All 5 model artifacts present",
        )

    def _check_paper_period(self) -> GateCondition:
        """GATE-02: Must have min_paper_days of shadow_ledger data meeting thresholds."""
        if create_client is None:
            return GateCondition(
                name="GATE-02",
                passed=False,
                reason="No shadow_ledger data available (Supabase not configured)",
            )

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")

        try:
            client = create_client(url, key)
            cutoff = (datetime.now(UTC) - timedelta(days=self._min_paper_days)).isoformat()
            result = (
                client.table("shadow_ledger")
                .select("predicted_edge,timestamp")
                .gte("timestamp", cutoff)
                .execute()
            )
            rows = result.data
        except Exception as exc:
            return GateCondition(
                name="GATE-02",
                passed=False,
                reason=f"No shadow_ledger data available (query error: {exc})",
            )

        if not rows:
            return GateCondition(
                name="GATE-02",
                passed=False,
                reason=f"No paper-trading data in last {self._min_paper_days} days",
            )

        # Count unique calendar days covered
        unique_days = {r["timestamp"][:10] for r in rows if r.get("timestamp")}
        if len(unique_days) < self._min_paper_days:
            return GateCondition(
                name="GATE-02",
                passed=False,
                reason=(
                    f"Paper-trading period too short: {len(unique_days)} days "
                    f"(need {self._min_paper_days})"
                ),
            )

        positive_rate = sum(1 for r in rows if r["predicted_edge"] > 0) / len(rows)
        mean_edge = sum(r["predicted_edge"] for r in rows) / len(rows)

        if positive_rate >= self._min_positive_rate and mean_edge >= self._min_mean_edge:
            return GateCondition(
                name="GATE-02",
                passed=True,
                reason=(
                    f"Paper metrics OK: positive_rate={positive_rate:.1%}, "
                    f"mean_edge={mean_edge:.3%}"
                ),
            )

        return GateCondition(
            name="GATE-02",
            passed=False,
            reason=(
                f"Paper metrics below threshold: "
                f"positive_rate={positive_rate:.1%} (need {self._min_positive_rate:.0%}), "
                f"mean_edge={mean_edge:.3%} (need {self._min_mean_edge:.3%})"
            ),
        )

    def _check_approval(self) -> GateCondition:
        """GATE-03: Valid live_approval.json must exist with passing gate snapshot."""
        if not self._approval_path.exists():
            return GateCondition(
                name="GATE-03",
                passed=False,
                reason=f"No approval file at {self._approval_path}",
            )

        try:
            data = json.loads(self._approval_path.read_text())
        except json.JSONDecodeError:
            return GateCondition(
                name="GATE-03",
                passed=False,
                reason="Invalid JSON in approval file",
            )

        snapshot = data.get("gate_snapshot", {})
        if not (
            snapshot.get("gate_01_models") is True and snapshot.get("gate_02_paper_period") is True
        ):
            return GateCondition(
                name="GATE-03",
                passed=False,
                reason="Stale approval: GATE-01 or GATE-02 was not met at approval time",
            )

        return GateCondition(
            name="GATE-03",
            passed=True,
            reason=(
                f"Approved by {data.get('approved_by', 'unknown')} "
                f"at {data.get('approved_at', 'unknown')}"
            ),
        )

    def _check_circuit_breaker(self) -> GateCondition:
        """GATE-04: Circuit breaker must not have been tripped (approval renamed to .disabled).

        Fails when:
          - The .disabled file exists (breaker was tripped and approval invalidated), OR
          - Neither approval nor .disabled file exists (no live approval has ever been granted)
        """
        disabled_path = self._approval_path.with_suffix(".json.disabled")
        if disabled_path.exists():
            return GateCondition(
                name="GATE-04",
                passed=False,
                reason="Circuit breaker tripped — approval invalidated",
            )
        if not self._approval_path.exists():
            return GateCondition(
                name="GATE-04",
                passed=False,
                reason="No approval file — live execution not authorized",
            )
        return GateCondition(
            name="GATE-04",
            passed=True,
            reason="No active circuit breaker",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> GateStatus:
        """Evaluate all four gate conditions. Returns GateStatus without raising."""
        conditions = [
            self._check_model_artifacts(),
            self._check_paper_period(),
            self._check_approval(),
            self._check_circuit_breaker(),
        ]
        return GateStatus(conditions=conditions)

    def assert_ready(self) -> None:
        """Call check(); raise CapitalGateError if any condition failed.

        Collects ALL failures before raising so the operator sees the full
        picture in one error (D-02).
        """
        status = self.check()
        if not status.all_passed:
            reasons = "; ".join(f"{f.name}: {f.reason}" for f in status.failures)
            raise CapitalGateError(f"Capital gate failed: {reasons}")

    def record_daily_loss(self, amount_usd: float, bankroll: float) -> bool:
        """Record realized loss in USD. Returns True if circuit breaker triggered.

        On breach: renames live_approval.json to live_approval.json.disabled
        to invalidate GATE-03 and preserve the audit trail (D-14).
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._loss_reset_date:
            self._daily_loss = 0.0
            self._loss_reset_date = today

        self._daily_loss += amount_usd

        if bankroll > 0 and self._daily_loss / bankroll > self._daily_loss_pct:
            if self._approval_path.exists():
                self._approval_path.rename(self._approval_path.with_suffix(".json.disabled"))
            logger.warning(
                "CIRCUIT BREAKER: daily loss %.2f exceeds %.0f%% of bankroll %.2f",
                self._daily_loss,
                self._daily_loss_pct * 100,
                bankroll,
            )
            return True

        return False

    @classmethod
    def from_env(cls) -> CapitalGate:
        """Construct CapitalGate with thresholds from environment variables.

        Reads:
          CAPITAL_GATE_MODELS_DIR          (default: data/models/pm)
          CAPITAL_GATE_APPROVAL_PATH       (default: data/live_approval.json)
          CAPITAL_GATE_MIN_PAPER_DAYS      (default: 7)
          CAPITAL_GATE_MIN_POSITIVE_RATE   (default: 0.55)
          CAPITAL_GATE_MIN_MEAN_EDGE       (default: 0.015)
          CIRCUIT_BREAKER_DAILY_LOSS_PCT   (default: 0.10)
        """
        return cls(
            models_dir=Path(os.environ.get("CAPITAL_GATE_MODELS_DIR", "data/models/pm")),
            approval_path=Path(
                os.environ.get("CAPITAL_GATE_APPROVAL_PATH", "data/live_approval.json")
            ),
            min_paper_days=int(os.environ.get("CAPITAL_GATE_MIN_PAPER_DAYS", "7")),
            min_positive_rate=float(os.environ.get("CAPITAL_GATE_MIN_POSITIVE_RATE", "0.55")),
            min_mean_edge=float(os.environ.get("CAPITAL_GATE_MIN_MEAN_EDGE", "0.015")),
            daily_loss_pct=float(os.environ.get("CIRCUIT_BREAKER_DAILY_LOSS_PCT", "0.10")),
        )
