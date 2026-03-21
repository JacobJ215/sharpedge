# Phase 13: Ablation Validation & Capital Gate - Research

**Researched:** 2026-03-20
**Domain:** Python capital gating, ablation backtesting, circuit breaker patterns
**Confidence:** HIGH

## Summary

Phase 13 adds two independent but connected guardrails before live Kalshi execution is allowed. First, an ablation script validates that trained PM models beat a fee-adjusted market-price fallback on historical resolved data. Second, a `CapitalGate` class enforces four conditions simultaneously at `ShadowExecutionEngine.from_env()` startup: model artifacts exist (GATE-01), paper-trading metrics pass (GATE-02), operator issued manual approval (GATE-03), and no live circuit breaker is active (GATE-04).

All code lives in `packages/venue_adapters`. The `ShadowExecutionEngine.from_env()` method is the sole injection point for `assert_ready()`. The `CircuitBreakerState` pattern from `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` provides the drawdown model for GATE-04. The `ShadowLedger` / `ShadowLedgerEntry.predicted_edge` field is the paper-trading data source for GATE-02. All five `.joblib` artifacts already exist in `data/models/pm/`.

**Primary recommendation:** Implement `CapitalGate` as a standalone class in a new `packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py` file; wire `assert_ready()` into `from_env()` with a three-line guard block; implement both scripts as `scripts/run_ablation.py` and `scripts/approve_live.py`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Hybrid `CapitalGate` class in `packages/venue_adapters` — `check()` returns a status report (usable from standalone script or CI), `assert_ready()` raises if any condition fails (called from `ShadowExecutionEngine.from_env()`)
- **D-02:** `assert_ready()` collects ALL failing conditions before raising — operator sees the full picture in one error, not whack-a-mole
- **D-03:** State backed by Supabase — query `shadow_ledger` table rows to compute paper-trading metrics
- **D-04:** Minimum 7 days of paper trading required
- **D-05:** Two metrics both required: positive-signal rate >= 55% AND mean predicted edge >= 1.5%
- **D-06:** Uses existing `ShadowLedgerEntry.predicted_edge` field — no new columns needed
- **D-07:** Fallback baseline = "always bet YES at current market price, fee-adjusted" — most meaningful comparison against market consensus
- **D-08:** Output: console table (human-readable) + `data/ablation_report.json` (machine-readable, gate reads this)
- **D-09:** Pass threshold: overall edge delta >= +1.5% AND every category edge delta >= 0.0% (no category allowed to be net-negative)
- **D-10:** Report shows per-category edge delta + overall delta, with PASS/FAIL per category and overall
- **D-11:** `scripts/approve_live.py` — standalone script, shows full gate status table before prompting, blocks if GATE-01 or GATE-02 not met
- **D-12:** Operator types their name at the prompt; script writes `data/live_approval.json` with: `approved_at` (ISO UTC), `approved_by` (operator name), `gate_snapshot` (all 4 condition states at approval time)
- **D-13:** `CapitalGate` reads `data/live_approval.json` to verify GATE-03 — file must exist and be valid JSON
- **D-14 (GATE-04):** Wires into existing `CircuitBreakerState` pattern from `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` — when daily realized loss exceeds the configured threshold, write a circuit-breaker log entry AND rename `data/live_approval.json` to `data/live_approval.json.disabled` (preserve audit trail)
- **D-15:** Drawdown threshold configurable via `CIRCUIT_BREAKER_DAILY_LOSS_PCT` env var (default matches existing `TradingConfig.daily_loss_limit`)

### Claude's Discretion

- Circuit breaker invalidation: rename `live_approval.json` to `live_approval.json.disabled` (not delete — preserves audit trail)
- `approve_live.py` should show the same table format as `check()` — operator sees identical output whether they call `check()` manually or run the approval script
- Ablation script runs on historical resolved PM data (already in Supabase `resolved_pm_markets`) — no live API calls needed

### Deferred Ideas (OUT OF SCOPE)

- Dashboard visualization of gate status — Phase 14
- Automatic re-approval via CI after drawdown recovery — out of scope for v2.0
- Per-category ablation thresholds configurable separately — current design uses one threshold for all categories
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ABLATE-01 | Operator can run an ablation backtest comparing fee-adjusted fallback vs trained-model edge on historical paper data | `scripts/run_ablation.py` reads `resolved_pm_markets` from Supabase; uses `PMResolutionPredictor` or loads `.joblib` directly; fee model: Kalshi charges ~5% per contract fill |
| ABLATE-02 | Ablation report shows edge delta (model vs fallback) per category and overall, with configurable pass/fail threshold | `data/ablation_report.json` written with per-category and overall delta; threshold from env var `ABLATION_THRESHOLD_PCT` (default 1.5%) |
| GATE-01 | System rejects `ENABLE_KALSHI_EXECUTION=true` unless trained `.joblib` artifacts exist for all 5 categories | `CapitalGate._check_model_artifacts()` verifies `data/models/pm/{category}.joblib` for crypto, economic, entertainment, political, weather |
| GATE-02 | System requires a configurable N-day paper-trading period with acceptable edge-to-fill ratio before live flag is honoured | `CapitalGate._check_paper_period()` queries Supabase `shadow_ledger` for rows in past N days; checks positive-signal rate and mean predicted_edge |
| GATE-03 | Operator completes a manual review step (CLI confirmation + timestamped log entry) before enabling live execution | `scripts/approve_live.py` writes `data/live_approval.json`; `CapitalGate._check_approval()` reads and validates it |
| GATE-04 | System auto-disables live execution if daily realized loss exceeds a configurable drawdown threshold | `CapitalGate.record_loss()` mirrors `risk_agent.record_loss()` pattern; renames `live_approval.json` to `live_approval.json.disabled` on breach |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `pathlib` | 3.12 stdlib | File-path operations for `.joblib` checks and JSON read/write | No deps, cross-platform, already used in project |
| Python stdlib `json` | 3.12 stdlib | Read/write `ablation_report.json`, `live_approval.json` | Already used everywhere in project |
| Python stdlib `dataclasses` | 3.12 stdlib | `GateStatus` return type from `check()` | Matches `CircuitBreakerState` pattern in codebase |
| `supabase-py` (existing) | project dep | Query `shadow_ledger` and `resolved_pm_markets` tables | Already in project via `sharpedge_db` package |
| `joblib` (existing) | project dep | Load `.joblib` model artifacts for GATE-01 presence check | Already used by training pipeline |
| `pytest` + `pytest-asyncio` | project dev dep | Unit tests; `asyncio_mode = "auto"` already configured | Already configured in `packages/venue_adapters/pyproject.toml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `os` | 3.12 stdlib | `os.environ.get()` for threshold env vars | Consistent with existing `from_env()` pattern |
| `tabulate` or manual f-string table | stdlib-compatible | Console table formatting for `approve_live.py` | Use f-strings to avoid adding a dep; tabulate only if already present |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Supabase query for GATE-02 | In-memory `ShadowLedger.entries` | In-memory ledger resets on restart; Supabase gives durable cross-process history — Supabase wins for GATE-02 |
| Rename `.disabled` for GATE-04 invalidation | Delete file | Rename preserves audit trail per D-14; delete cannot be undone |
| Single `gate.py` file | Separate `capital_gate.py` | Separate file keeps ledger.py and execution_engine.py under 500-line limit and groups gate logic cleanly |

**Installation:** No new packages required. All dependencies are already in the project.

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
packages/venue_adapters/
  src/sharpedge_venue_adapters/
    capital_gate.py          # NEW — CapitalGate class
  tests/
    test_capital_gate.py     # NEW — all GATE-01..04 + check()/assert_ready() tests

scripts/
  run_ablation.py            # NEW — ablation backtest script
  approve_live.py            # NEW — manual review script

data/
  ablation_report.json       # written by run_ablation.py
  live_approval.json         # written by approve_live.py
  live_approval.json.disabled  # renamed by GATE-04 on drawdown breach
```

### Pattern 1: Hybrid check()/assert_ready() on CapitalGate

**What:** `check()` returns a structured status object; `assert_ready()` calls `check()` and raises `CapitalGateError` if any condition failed, including all failure reasons.
**When to use:** Call `check()` from scripts and CI; call `assert_ready()` from `ShadowExecutionEngine.from_env()` — one point of enforcement.

```python
# packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_CATEGORIES = ("crypto", "economic", "entertainment", "political", "weather")
_MODELS_DIR = Path("data/models/pm")
_APPROVAL_PATH = Path("data/live_approval.json")
_APPROVAL_DISABLED_PATH = Path("data/live_approval.json.disabled")


class CapitalGateError(RuntimeError):
    """Raised by assert_ready() when one or more gate conditions fail."""


@dataclass
class GateCondition:
    name: str
    passed: bool
    reason: str


@dataclass
class GateStatus:
    conditions: list[GateCondition] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.conditions)

    @property
    def failures(self) -> list[GateCondition]:
        return [c for c in self.conditions if not c.passed]


class CapitalGate:
    """Enforces all four capital gate conditions before live execution."""

    def __init__(
        self,
        models_dir: Path = _MODELS_DIR,
        approval_path: Path = _APPROVAL_PATH,
        min_paper_days: int = 7,
        min_positive_rate: float = 0.55,
        min_mean_edge: float = 0.015,
        daily_loss_pct: Optional[float] = None,
    ) -> None:
        ...

    def check(self) -> GateStatus:
        """Returns full gate status without raising. Safe to call from CI/scripts."""
        ...

    def assert_ready(self) -> None:
        """Calls check(); raises CapitalGateError if any condition failed."""
        status = self.check()
        if not status.all_passed:
            reasons = "; ".join(f.reason for f in status.failures)
            raise CapitalGateError(f"Capital gate failed: {reasons}")

    def record_daily_loss(self, amount_usd: float, bankroll: float) -> bool:
        """Record realized loss. Returns True if circuit breaker triggered."""
        ...

    @classmethod
    def from_env(cls) -> "CapitalGate":
        """Construct with thresholds from environment variables."""
        ...
```

### Pattern 2: from_env() injection in ShadowExecutionEngine

**What:** Three-line guard at the top of the live branch in `from_env()`.
**When to use:** Only when `ENABLE_KALSHI_EXECUTION=true` — shadow mode bypasses the gate entirely.

```python
# In ShadowExecutionEngine.from_env(), inside the live mode branch:
if os.environ.get("ENABLE_KALSHI_EXECUTION", "").lower() == "true":
    from sharpedge_venue_adapters.capital_gate import CapitalGate
    CapitalGate.from_env().assert_ready()   # raises CapitalGateError on fail
    # ... existing KalshiClient + SettlementLedger wiring follows
```

### Pattern 3: CircuitBreakerState extension for GATE-04

**What:** GATE-04 mirrors the `daily_loss_reset_date` + threshold logic from `risk_agent.CircuitBreakerState`. Daily loss is tracked inside `CapitalGate` (not shared module state) because `CapitalGate` is the enforcement boundary.
**When to use:** Call `gate.record_daily_loss(amount, bankroll)` from any code path that settles a trade; on breach, approval file is renamed to `.disabled`.

```python
# Breach logic inside CapitalGate.record_daily_loss():
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
if today != self._loss_reset_date:
    self._daily_loss = 0.0
    self._loss_reset_date = today
self._daily_loss += amount_usd
threshold = self._daily_loss_pct  # from CIRCUIT_BREAKER_DAILY_LOSS_PCT env var
if self._daily_loss / bankroll > threshold:
    if self._approval_path.exists():
        self._approval_path.rename(self._approval_path.with_suffix(".json.disabled"))
    return True  # breaker tripped
return False
```

### Pattern 4: Ablation backtest structure

**What:** Load resolved markets from Supabase `resolved_pm_markets`, load `.joblib` models, compute model-predicted edge vs fallback edge per category, write `data/ablation_report.json`.
**When to use:** Run once after training completes; GATE-01 checks `.joblib` presence, not ablation result — ablation is a separate prerequisite for operator confidence.

```python
# Ablation report JSON schema (data/ablation_report.json)
{
  "generated_at": "2026-03-20T12:00:00+00:00",
  "threshold_pct": 1.5,
  "categories": {
    "crypto":        {"model_edge": 0.041, "fallback_edge": 0.022, "delta": 0.019, "passed": true},
    "economic":      {"model_edge": 0.038, "fallback_edge": 0.020, "delta": 0.018, "passed": true},
    "entertainment": {"model_edge": 0.029, "fallback_edge": 0.018, "delta": 0.011, "passed": true},
    "political":     {"model_edge": 0.043, "fallback_edge": 0.021, "delta": 0.022, "passed": true},
    "weather":       {"model_edge": 0.035, "fallback_edge": 0.019, "delta": 0.016, "passed": true}
  },
  "overall": {"model_edge": 0.037, "fallback_edge": 0.020, "delta": 0.017, "passed": true},
  "passed": true
}
```

### Pattern 5: live_approval.json schema

```json
{
  "approved_at": "2026-03-20T14:32:00+00:00",
  "approved_by": "operator-name",
  "gate_snapshot": {
    "gate_01_models": true,
    "gate_02_paper_period": true,
    "gate_03_approval": false,
    "gate_04_circuit_breaker": true
  }
}
```

### Anti-Patterns to Avoid

- **Importing CapitalGate at module level in execution_engine.py:** Import only inside the live-mode branch of `from_env()` to avoid circular imports and keep shadow-mode startup free of gate overhead.
- **Sharing `_breaker` module-level state with risk_agent.py:** GATE-04 tracks daily loss inside `CapitalGate` instance state, not the risk_agent's `_breaker` module global. The two subsystems run independently.
- **Checking GATE-03 approval before GATE-01/02:** The approval script (`approve_live.py`) must block if GATE-01 or GATE-02 not met (D-11). This is a UX guard in the script, not a gate ordering requirement.
- **Deleting live_approval.json on breach:** Rename to `.disabled` to preserve the audit trail. The operator can inspect who approved and when.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UTC midnight date reset for daily loss | Custom timer/scheduler | Same `strftime("%Y-%m-%d")` pattern as `DayExposureGuard._maybe_reset()` and `CircuitBreakerState` | Already battle-tested in this codebase; consistent behavior |
| Fee-adjusted fallback edge calculation | Custom fee model | Kalshi standard ~5% of contract value (0.05 fee coefficient) — encode as constant | Exact fee formula is public; hand-rolling risks errors |
| Supabase queries for shadow_ledger | Custom ORM or raw SQL builder | `supabase-py` `.table("shadow_ledger").select("*").gte("timestamp", cutoff)` | Already used in `SettlementLedger.append()` |
| JSON file locking | fcntl/threading locks | No concurrent writes needed — scripts are single-process CLI tools | YAGNI; approval and ablation scripts are run once by one operator |

**Key insight:** Every pattern needed here already exists in the codebase — the task is assembly and wiring, not invention.

---

## Common Pitfalls

### Pitfall 1: GATE-02 computes metrics over wrong time window
**What goes wrong:** Query returns rows without a `timestamp` >= filter, producing inflated paper history.
**Why it happens:** Forgetting to apply the N-day cutoff filter on Supabase query.
**How to avoid:** Compute `cutoff = datetime.now(UTC) - timedelta(days=min_paper_days)` and pass as `.gte("timestamp", cutoff.isoformat())`.
**Warning signs:** GATE-02 passes on a brand-new project with no history.

### Pitfall 2: assert_ready() raises only first failure
**What goes wrong:** Operator fixes one condition, runs again, hits the next — whack-a-mole UX.
**Why it happens:** Using early `raise` instead of collecting all failures (D-02).
**How to avoid:** Accumulate all `GateCondition(passed=False, ...)` results into `GateStatus.conditions` before raising. The `assert_ready()` method calls `check()` first, then raises with all failures joined.
**Warning signs:** Test `test_assert_ready_collects_all_failures` fails.

### Pitfall 3: GATE-04 records loss against wrong bankroll
**What goes wrong:** Percentage threshold comparison uses stale or zero bankroll, triggering or suppressing breaker incorrectly.
**Why it happens:** `bankroll` is not persisted — callers must pass current bankroll.
**How to avoid:** `record_daily_loss(amount_usd, bankroll)` requires the caller to provide current bankroll; document this contract clearly. Mirror the `get_bankroll()` call pattern from `risk_agent.py`.
**Warning signs:** Circuit breaker trips at $0 loss (bankroll=0.0 passed).

### Pitfall 4: Ablation fee model not applied to fallback
**What goes wrong:** Fallback edge appears larger than it should because fees aren't subtracted.
**Why it happens:** Fee adjustment is specified for the fallback but easy to skip for "always YES" logic.
**How to avoid:** Apply `fee_rate = 0.05` to both model and fallback edges: `net_edge = gross_edge * (1 - fee_rate)`.
**Warning signs:** Fallback shows positive expected value greater than model on crypto.

### Pitfall 5: live_approval.json GATE-03 check passes stale approval
**What goes wrong:** Operator approved before GATE-01 or GATE-02 was fixed; stale approval file lets bad state through.
**Why it happens:** `CapitalGate._check_approval()` reads the file without checking whether GATE-01/02 pass.
**How to avoid:** GATE-03 check in `check()` should ALSO fail if `gate_snapshot.gate_01_models` or `gate_snapshot.gate_02_paper_period` is False in the stored snapshot (the snapshot was taken at approval time, so if GATE-01 was False then, the approval is invalid).
**Warning signs:** `test_stale_approval_rejected` fails.

### Pitfall 6: ShadowExecutionEngine.from_env() CapitalGate import fails in shadow mode
**What goes wrong:** Import of `capital_gate` module raises because supabase is not configured, even in shadow mode.
**Why it happens:** Import placed at module top level rather than inside the `ENABLE_KALSHI_EXECUTION` branch.
**How to avoid:** Keep the import inside the live-mode `if` branch — shadow mode never touches `CapitalGate`.

---

## Code Examples

Verified patterns from existing codebase sources:

### Existing from_env() pattern (gate injection point)
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py line 254
if os.environ.get("ENABLE_KALSHI_EXECUTION", "").lower() == "true":
    from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig
    # ... existing live-mode wiring
```

### CircuitBreakerState daily reset pattern (GATE-04 model)
```python
# Source: packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py lines 42-44
now_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
if _breaker.daily_loss_reset_date != now_date:
    _breaker.daily_loss = 0.0
    _breaker.daily_loss_reset_date = now_date
```

### DayExposureGuard reset pattern (also GATE-04 model)
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py lines 189-192
def _maybe_reset(self) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != self._reset_date:
        self._day_stake = 0.0
        self._reset_date = today
```

### TradingConfig daily_loss_limit default
```python
# Source: packages/trading_swarm/src/sharpedge_trading/config.py
_DEFAULTS = { "daily_loss_limit": 0.10, ... }  # 10% of bankroll
# GATE-04 default: CIRCUIT_BREAKER_DAILY_LOSS_PCT = 0.10
```

### ShadowLedgerEntry fields (GATE-02 data source)
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py lines 124-133
@dataclass(frozen=True)
class ShadowLedgerEntry:
    entry_id: Optional[int]
    market_id: str
    predicted_edge: float       # fraction — GATE-02 averages this
    kelly_sized_amount: float
    timestamp: datetime         # UTC-aware — GATE-02 filters by this
    position_lot_id: str = ""
```

### Training report JSON structure (GATE-01 cross-check)
```json
// Source: data/models/pm/training_report.json (confirmed present)
[
  {"category": "crypto",        "badge": "high", "model_path": "data/models/pm/crypto.joblib"},
  {"category": "economic",      "badge": "high", "model_path": "data/models/pm/economic.joblib"},
  {"category": "entertainment", "badge": "high", "model_path": "data/models/pm/entertainment.joblib"},
  {"category": "political",     "badge": "high", "model_path": "data/models/pm/political.joblib"},
  {"category": "weather",       "badge": "high", "model_path": "data/models/pm/weather.joblib"}
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `check_circuit_breakers()` function with module-level state | Class-based gate with instance state | Phase 13 (new) | CapitalGate is testable without module-level state reset between tests |
| Single condition checked at startup | Collect-all-failures pattern | Phase 13 (D-02) | Operator sees all gate failures in one error message |

**Deprecated/outdated:**
- Module-level `_breaker` state from `risk_agent.py`: GATE-04 does NOT reuse this — it creates its own instance state inside `CapitalGate` to remain independently testable. The existing `_breaker` continues to serve the trading swarm; the two are parallel, not shared.

---

## Open Questions

1. **Supabase `shadow_ledger` table existence**
   - What we know: `ShadowLedger` class is in-memory (confirmed from `execution_engine.py`); CONTEXT.md D-03 says "State backed by Supabase — query `shadow_ledger` table"
   - What's unclear: The table may not yet exist in Supabase schema — Phase 11/12 used in-memory `ShadowLedger` only; Supabase persistence was flagged as "Phase 14 extension" in the `ShadowLedger` docstring
   - Recommendation: Wave 0 test for GATE-02 should mock the Supabase call. Implementation should gracefully return `GateCondition(passed=False, reason="no shadow_ledger data")` if Supabase is unavailable or table is empty. Do not block Phase 13 on schema migration.

2. **Ablation fallback fee rate precision**
   - What we know: Kalshi charges a fee on each trade; CONTEXT.md says "fee-adjusted market price YES bet"
   - What's unclear: Exact fee coefficient — 5% is the standard Kalshi fee but can vary by market type
   - Recommendation: Use `FEE_RATE = 0.05` as a named constant in `run_ablation.py`; make it overridable via `ABLATION_FEE_RATE` env var. Document the assumption explicitly in the script.

3. **approve_live.py — does it need to live in `scripts/` or a different location?**
   - What we know: `scripts/` already has `approve_live.py` referenced in CONTEXT.md; existing scripts like `train_pm_models.py` are in `scripts/`
   - What's unclear: No issue; `scripts/` is correct.
   - Recommendation: None needed — confirmed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `packages/venue_adapters/pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) |
| Quick run command | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py -x -q` |
| Full suite command | `python -m pytest packages/venue_adapters/tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | `check()` fails when any `.joblib` missing | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate01_fails_missing_artifact -x` | Wave 0 |
| GATE-01 | `check()` passes when all 5 `.joblib` present | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate01_passes_all_artifacts -x` | Wave 0 |
| GATE-02 | `check()` fails when < 7 days of paper history | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate02_fails_insufficient_days -x` | Wave 0 |
| GATE-02 | `check()` fails when positive-signal rate < 55% | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate02_fails_low_positive_rate -x` | Wave 0 |
| GATE-02 | `check()` fails when mean edge < 1.5% | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate02_fails_low_mean_edge -x` | Wave 0 |
| GATE-02 | `check()` passes when 7+ days AND rate >= 55% AND mean edge >= 1.5% | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate02_passes_valid_period -x` | Wave 0 |
| GATE-03 | `check()` fails when `live_approval.json` absent | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate03_fails_no_approval_file -x` | Wave 0 |
| GATE-03 | `check()` fails when approval file is invalid JSON | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate03_fails_invalid_json -x` | Wave 0 |
| GATE-03 | `check()` fails when approval snapshot shows prior gate failures | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate03_fails_stale_approval -x` | Wave 0 |
| GATE-03 | `check()` passes when valid approval file present with gate snapshot | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate03_passes_valid_approval -x` | Wave 0 |
| GATE-04 | `record_daily_loss()` returns False below threshold | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate04_no_breach_below_threshold -x` | Wave 0 |
| GATE-04 | `record_daily_loss()` returns True and renames approval file on breach | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate04_breach_invalidates_approval -x` | Wave 0 |
| GATE-04 | Daily loss resets at UTC midnight | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate04_daily_reset -x` | Wave 0 |
| GATE-04 | `check()` fails when approval file is `.disabled` | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_gate04_check_fails_after_breach -x` | Wave 0 |
| D-02 | `assert_ready()` collects all failing conditions before raising | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_assert_ready_collects_all_failures -x` | Wave 0 |
| D-01 | `assert_ready()` raises `CapitalGateError` (not generic RuntimeError) | unit | `python -m pytest packages/venue_adapters/tests/test_capital_gate.py::test_assert_ready_raises_capital_gate_error -x` | Wave 0 |
| ABLATE-01 | Ablation script computes model vs fallback edge per category | unit | `python -m pytest packages/venue_adapters/tests/test_ablation.py::test_ablation_computes_per_category_delta -x` | Wave 0 |
| ABLATE-02 | Ablation report passes when delta >= threshold and all categories >= 0.0% | unit | `python -m pytest packages/venue_adapters/tests/test_ablation.py::test_ablation_pass_threshold -x` | Wave 0 |
| ABLATE-02 | Ablation report fails when any category delta < 0.0% | unit | `python -m pytest packages/venue_adapters/tests/test_ablation.py::test_ablation_fail_negative_category -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest packages/venue_adapters/tests/test_capital_gate.py -x -q`
- **Per wave merge:** `python -m pytest packages/venue_adapters/tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/venue_adapters/tests/test_capital_gate.py` — covers GATE-01, GATE-02, GATE-03, GATE-04, assert_ready() contract
- [ ] `packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py` — must exist as stub (with `NotImplementedError` bodies) so Wave 0 tests can import without `ImportError`
- [ ] `packages/venue_adapters/tests/test_ablation.py` — covers ABLATE-01, ABLATE-02
- [ ] `scripts/run_ablation.py` — must exist as a stub so ablation tests can import its core logic functions (if any are unit-testable as functions)

Note: `scripts/approve_live.py` is an interactive CLI script; test coverage for it is integration/manual-only. Its core logic (writing `live_approval.json` with correct schema) can be tested via a helper function extracted and imported by `test_capital_gate.py`.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection: `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` — `from_env()` injection point confirmed, `ShadowLedgerEntry.predicted_edge` field confirmed
- Direct inspection: `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — `SettlementLedger`, `LedgerEntry` schema confirmed; `ShadowLedger` docstring confirms in-memory only (Supabase deferred)
- Direct inspection: `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` — `CircuitBreakerState`, `check_circuit_breakers()`, `daily_loss_limit` pattern confirmed
- Direct inspection: `packages/venue_adapters/pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` confirmed
- Direct inspection: `data/models/pm/` — all 5 `.joblib` + 5 `_calibration.joblib` confirmed present
- Direct inspection: `data/models/pm/training_report.json` — all 5 categories with `"badge": "high"` confirmed
- Direct inspection: `.planning/config.json` — `nyquist_validation: true` confirmed

### Secondary (MEDIUM confidence)
- `.planning/phases/13-ablation-validation-capital-gate/13-CONTEXT.md` — all D-01 through D-15 decisions; CONTEXT.md is authoritative for locked choices
- `.planning/STATE.md` — phase history and cross-phase decisions confirm ShadowLedger is in-memory; Supabase persistence deferred

### Tertiary (LOW confidence)
- Kalshi 5% fee rate — inferred from market knowledge; verify against current Kalshi fee schedule before finalizing `ABLATION_FEE_RATE` constant

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed present in project; no new packages needed
- Architecture: HIGH — injection point confirmed in source; CircuitBreakerState pattern confirmed in source; `check()/assert_ready()` split is a well-established Python pattern
- Pitfalls: HIGH for items derived from code inspection; MEDIUM for Supabase shadow_ledger table availability (open question)
- Validation architecture: HIGH — test framework config confirmed; test file paths follow existing `test_shadow_execution_engine.py` naming convention

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable domain; no fast-moving dependencies)
