# Phase 11: Shadow Execution Engine - Research

**Researched:** 2026-03-17
**Domain:** Python execution engine, exposure limit enforcement, append-only ledger, shadow/paper trading mode
**Confidence:** HIGH

## Summary

Phase 11 builds an `execution_engine.py` module (new file, new package or standalone script) that sits between the signal pipeline and the existing executor layer. Its job is threefold: receive order intents from the PM edge scanner or risk agent, check per-market and per-day exposure limits before accepting each intent, and write every accepted signal to a `ShadowLedger` with the four required fields (market_id, predicted_edge, kelly_sized_amount, timestamp). No Kalshi API calls may be made in shadow mode.

All three upstream building blocks are fully implemented and tested. `ExposureBook` (in `packages/venue_adapters/src/sharpedge_venue_adapters/exposure.py`) tracks open positions and enforces venue concentration caps. `SettlementLedger` (in `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py`) is a battle-tested append-only ledger. Kelly sizing lives in `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` (`compute_kelly_size`) and also in `packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/size_position.py`. The `PaperExecutor` and `KalshiExecutor` already exist in `packages/trading_swarm/src/sharpedge_trading/execution/`; the execution engine in Phase 11 is a new layer above these that adds per-market and per-day limit enforcement before delegating to `PaperExecutor`.

Phase 11 does NOT extend `PaperExecutor`. The distinction is: `PaperExecutor` simulates fills (slippage model, bankroll deduction, Supabase write to `paper_trades`). Phase 11's `ShadowLedger` is a lighter, purpose-built record that captures prediction-market signals with their edge and Kelly amount, even before any fill simulation. The two can coexist: the engine checks limits, writes to `ShadowLedger`, then optionally delegates to `PaperExecutor` for fill simulation.

**Primary recommendation:** Add a new `execution_engine.py` in `packages/venue_adapters/src/sharpedge_venue_adapters/` (or a new `packages/execution_engine/` package). It wraps `ExposureBook` for per-market and per-day limit enforcement, defines a `ShadowLedger` dataclass with the four required fields, and exposes a synchronous `process_signal(intent) -> ShadowLedgerEntry | None` function. Keep it framework-free (no asyncio required at this layer) so it is trivially testable.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXEC-01 | Operator can run shadow-mode execution that logs order intents without submitting to Kalshi | `ShadowExecutionEngine` with `ENABLE_KALSHI_EXECUTION` absent/false — delegates to `ShadowLedger.append()` only, never to `KalshiExecutor`. Verified by asserting no `KalshiClient.create_order` calls. |
| EXEC-02 | Shadow mode records market_id, predicted edge, Kelly-sized amount, and timestamp per signal to a ledger | New `ShadowLedgerEntry` dataclass with those four fields; `ShadowLedger.append()` stores in-memory or Supabase. `SettlementLedger` pattern is the model. |
| EXEC-04 | System enforces per-market and per-day max-exposure limits before any order intent is created | `ExposureBook` enforces per-venue concentration. Phase 11 adds per-market cap (new `_market_positions` dict) and per-day cumulative cap (new `_day_stake` counter that resets at UTC midnight). Rejection must occur BEFORE the ledger entry is written. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses (stdlib) | 3.12 | `ShadowLedgerEntry`, `OrderIntent`, `ExposureConfig` | Already used throughout the codebase for all data contracts |
| `datetime` / `timezone.utc` (stdlib) | 3.12 | UTC-aware timestamps on all ledger entries | Project convention: `ValueError` on naive datetimes (see `LedgerEntry.__post_init__`) |
| `uuid` (stdlib) | 3.12 | `lot_id` / `entry_id` generation | Already used in `PaperExecutor` and `KalshiExecutor` |
| `os.environ` (stdlib) | 3.12 | `ENABLE_KALSHI_EXECUTION` flag, `SHADOW_MAX_MARKET_EXPOSURE`, `SHADOW_MAX_DAY_EXPOSURE` | Project convention for all feature flags (see `executor_factory.py`, `daemon.py`) |
| `sharpedge_venue_adapters` | workspace | `ExposureBook`, `compute_allocation`, `AllocationDecision` | Phase 6 RISK-01 deliverable — fully tested, handles Kelly + drawdown throttle |
| `sharpedge_trading` | workspace | `compute_kelly_size`, `TradingConfig` | Phase 6/8 deliverable — `compute_kelly_size` in `risk_agent.py` is the right Kelly function for Kalshi binary markets |
| pytest + pytest-asyncio | >=8.0 / >=0.24 | Test framework | Workspace-wide dev deps (root `pyproject.toml`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `supabase-py` | already in workspace | Optional persistence for `ShadowLedger` to Supabase | Only when `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are set; in-memory mode is the default for tests |
| `logging` (stdlib) | 3.12 | Structured log line per rejection and per acceptance | Project convention: every agent logs at INFO/WARNING |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `ShadowLedger` class | Reuse `SettlementLedger` with a `SHADOW_SIGNAL` event type | `SettlementLedger` requires `amount_usdc`, `fee_component`, `rebate_component`, `price_at_event` — all irrelevant for a pre-fill signal log. A dedicated `ShadowLedger` is cleaner and Phase 12 can extend `SettlementLedger` for fills. |
| `ExposureBook` for per-day limit | A separate daily counter | `ExposureBook` tracks per-venue, not per-day. The cleanest approach is to add a thin `DayExposureGuard` alongside `ExposureBook` rather than mutating Phase 6's tested class. |
| Adding to `venue_adapters` package | New `execution_engine` package | `venue_adapters` already exports exposure + ledger; adding `execution_engine.py` there keeps the dependency graph flat. A new package adds unnecessary indirection for a single new module. |

**Installation:** No new dependencies needed. Everything is already in the uv workspace.

---

## Architecture Patterns

### Recommended Project Structure

The execution engine belongs in `packages/venue_adapters/` since it depends on `ExposureBook` and `SettlementLedger`, both of which live there. Add one new file:

```
packages/venue_adapters/src/sharpedge_venue_adapters/
├── execution_engine.py        # NEW — ShadowLedger + ShadowExecutionEngine
├── exposure.py                # EXISTING — ExposureBook, compute_allocation
├── ledger.py                  # EXISTING — SettlementLedger
└── __init__.py                # update exports

packages/venue_adapters/tests/
├── test_shadow_execution_engine.py   # NEW — all three success criteria
└── ...                               # EXISTING
```

### Pattern 1: OrderIntent → Limit Check → ShadowLedger

**What:** The engine receives a structured `OrderIntent`, checks per-market and per-day exposure limits, rejects the intent if either limit would be breached, and writes a `ShadowLedgerEntry` only on acceptance.

**When to use:** For every PM edge signal that arrives in shadow mode (`ENABLE_KALSHI_EXECUTION` not set or `false`).

**Example:**
```python
# Source: derived from packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ShadowLedgerEntry:
    entry_id: int | None
    market_id: str
    predicted_edge: float      # model_prob - market_prob, as a fraction (e.g. 0.05)
    kelly_sized_amount: float  # dollar amount: bankroll * kelly_fraction
    timestamp: datetime        # UTC-aware

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("ShadowLedgerEntry.timestamp must be UTC-aware")

@dataclass(frozen=True)
class OrderIntent:
    market_id: str
    predicted_edge: float
    fair_prob: float
    kelly_fraction: float
    bankroll: float
    created_at: datetime       # UTC-aware
```

### Pattern 2: DayExposureGuard — Per-Day Stake Counter

**What:** A simple class that tracks total committed stake for the current UTC calendar day, resetting automatically when the date changes.

**When to use:** Every call to `ShadowExecutionEngine.process_intent()` queries the guard before writing the ledger entry.

**Example:**
```python
# Source: derived from packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py
# CircuitBreakerState uses the same UTC-date-reset pattern.
class DayExposureGuard:
    def __init__(self, max_day_exposure: float) -> None:
        self._max = max_day_exposure
        self._day_stake: float = 0.0
        self._reset_date: str = ""   # YYYY-MM-DD UTC

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._reset_date:
            self._day_stake = 0.0
            self._reset_date = today

    def would_breach(self, stake: float) -> bool:
        self._maybe_reset()
        return (self._day_stake + stake) > self._max

    def commit(self, stake: float) -> None:
        self._maybe_reset()
        self._day_stake += stake

    @property
    def day_stake(self) -> float:
        self._maybe_reset()
        return self._day_stake
```

### Pattern 3: Per-Market Exposure Cap

**What:** A dict `{market_id: total_committed_stake}` that prevents any single market from receiving more than `max_market_exposure` dollars.

**When to use:** Before `DayExposureGuard.would_breach()` check — per-market cap is the first gate.

**Example:**
```python
# Source: mirrors ExposureBook._positions dict pattern
class MarketExposureGuard:
    def __init__(self, max_market_exposure: float) -> None:
        self._max = max_market_exposure
        self._market_stake: dict[str, float] = {}

    def would_breach(self, market_id: str, stake: float) -> bool:
        current = self._market_stake.get(market_id, 0.0)
        return (current + stake) > self._max

    def commit(self, market_id: str, stake: float) -> None:
        self._market_stake[market_id] = self._market_stake.get(market_id, 0.0) + stake
```

### Pattern 4: ShadowExecutionEngine — Central Coordinator

**What:** Ties `MarketExposureGuard`, `DayExposureGuard`, and `ShadowLedger` together. Returns a `ShadowLedgerEntry` on acceptance, `None` on rejection with a logged reason.

**Example:**
```python
# Source: derived from executor_factory.py + risk_agent.py patterns
import os

class ShadowExecutionEngine:
    def __init__(
        self,
        max_market_exposure: float,
        max_day_exposure: float,
    ) -> None:
        self._market_guard = MarketExposureGuard(max_market_exposure)
        self._day_guard = DayExposureGuard(max_day_exposure)
        self._ledger = ShadowLedger()

    def process_intent(self, intent: OrderIntent) -> ShadowLedgerEntry | None:
        stake = intent.kelly_fraction * intent.bankroll
        # Gate 1: per-market
        if self._market_guard.would_breach(intent.market_id, stake):
            logger.warning("Per-market limit breach for %s — rejected", intent.market_id)
            return None
        # Gate 2: per-day
        if self._day_guard.would_breach(stake):
            logger.warning("Per-day limit breach — rejected (market=%s)", intent.market_id)
            return None
        # Accept: commit then write ledger
        self._market_guard.commit(intent.market_id, stake)
        self._day_guard.commit(stake)
        entry = self._ledger.append(ShadowLedgerEntry(
            entry_id=None,
            market_id=intent.market_id,
            predicted_edge=intent.predicted_edge,
            kelly_sized_amount=stake,
            timestamp=intent.created_at,
        ))
        return entry
```

### Anti-Patterns to Avoid

- **Writing the ledger entry before the limit check:** EXEC-04 explicitly requires rejection *before* the ledger entry is written. If the check happens after `ledger.append()`, the success criterion is violated.
- **Mutating `ExposureBook` in Phase 6:** `ExposureBook` does not track per-day exposure; adding it there breaks Phase 6's tested scope. Use `DayExposureGuard` as a parallel, independent guard.
- **Making `ShadowExecutionEngine.process_intent` async:** There is no I/O in the hot path (ledger is in-memory by default). Keep it synchronous so unit tests need no event loop.
- **Using `TRADING_MODE` env var to distinguish shadow vs live:** The existing `executor_factory.py` uses `TRADING_MODE=paper|live`. Phase 11 introduces `ENABLE_KALSHI_EXECUTION` (per EXEC-01/EXEC-03 split). Use the new flag for the shadow/live gate, not the old `TRADING_MODE`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Kelly sizing formula | Custom Kelly math | `risk_agent.compute_kelly_size(calibrated_prob, kalshi_price, bankroll, kelly_fraction)` | Already battle-tested, handles price floors/ceilings and fractional Kelly |
| Append-only ledger with Supabase persistence | Custom DB write | `SettlementLedger.append()` pattern (copy the `__init__` and `append` pattern for `ShadowLedger`) | Handles in-memory/Supabase duality, UTC enforcement, frozen dataclass |
| Venue concentration cap | Custom dict tracking | `ExposureBook.venue_utilization()` + `compute_allocation()` | Already handles drawdown throttle, correlation discount, cap enforcement |
| UTC-aware timestamp enforcement | Custom validation | `datetime.now(timezone.utc)` + `__post_init__` check (same as `LedgerEntry`) | Project-wide pattern, prevents timezone bugs that cause replay errors |
| Idempotency key | Custom hash | `f"{market_id}:{direction}:{created_at.isoformat()}"` (same as `_idempotency_key` in paper/kalshi executors) | Already in use, prevents duplicate ledger entries |

**Key insight:** The project has already solved the hard problems. Phase 11 is assembly and a thin new limit layer, not invention.

---

## Common Pitfalls

### Pitfall 1: Ledger Write Before Limit Check
**What goes wrong:** `ledger.append()` is called before `would_breach()` is checked, so a rejected intent still produces a ledger entry — violating Success Criterion 2 and 3.
**Why it happens:** Natural code ordering puts "record intent" first, then "check limits."
**How to avoid:** Both guards are checked with `return None` before any `ledger.append()` call. Unit tests must assert `len(ledger.entries) == 0` after a rejection.
**Warning signs:** Test for "reject before write" passes but test for "ledger count after rejection" is missing.

### Pitfall 2: Day Exposure Counter Not Resetting at Midnight
**What goes wrong:** If the date-reset logic uses local time or Python's `datetime.now()` without `timezone.utc`, the reset fires at local midnight instead of UTC midnight, causing limit inconsistencies.
**Why it happens:** `datetime.now()` returns local time on macOS/Linux unless `tz=timezone.utc` is passed.
**How to avoid:** Use `datetime.now(timezone.utc).strftime("%Y-%m-%d")` exactly as `CircuitBreakerState` in `risk_agent.py` does.
**Warning signs:** Tests that mock `datetime.now` fail or produce nondeterministic results.

### Pitfall 3: Kalshi API Call Guard Not Enforced
**What goes wrong:** `ShadowExecutionEngine` is integrated into the daemon but `KalshiExecutor.execute()` is still reachable via the existing event bus, so a shadow-mode signal reaches the live executor.
**Why it happens:** The daemon's `_run_execution` loop calls `executor.execute(event)` regardless of shadow mode.
**How to avoid:** `ShadowExecutionEngine` must not emit `ExecutionEvent` onto the bus in shadow mode; OR the daemon must not instantiate `KalshiExecutor` when `ENABLE_KALSHI_EXECUTION` is not set. The recommended approach: `ShadowExecutionEngine` writes to `ShadowLedger` and returns; it does NOT call `PaperExecutor.execute()` or `KalshiExecutor.execute()` in Phase 11.
**Warning signs:** Integration test passes but a Kalshi mock records calls when `ENABLE_KALSHI_EXECUTION` is unset.

### Pitfall 4: Per-Market Cap Based on Count, Not Dollars
**What goes wrong:** The per-market limit is implemented as "max N intents per market" rather than "max $X stake per market," producing a limit that can be trivially gamed by tiny intents.
**Why it happens:** Success Criterion 2 says "breach the per-market max-exposure limit" — "exposure" means dollar stake, not count.
**How to avoid:** `MarketExposureGuard` tracks cumulative stake (`float`), not intent count.
**Warning signs:** Test uses `size=0.01` and succeeds with 1000 intents on the same market.

### Pitfall 5: Frozen Dataclass for ShadowLedgerEntry Breaks Supabase Row
**What goes wrong:** `frozen=True` dataclass cannot be modified after construction; but if the Supabase insert returns a DB-assigned `entry_id`, the code tries to assign to the frozen field.
**Why it happens:** Same pattern as `LedgerEntry.entry_id` — solved in Phase 6 by constructing a new `LedgerEntry(entry_id=db_id, ...)` from the returned row.
**How to avoid:** Follow `SettlementLedger.append()` exactly: construct a new `ShadowLedgerEntry(entry_id=db_id, ...)` after the DB insert.

---

## Code Examples

### Shadow Ledger Entry Construction (verified pattern from ledger.py)
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py
now = datetime.now(timezone.utc)
entry = ShadowLedgerEntry(
    entry_id=None,
    market_id="KXBTCD-26MAR14",
    predicted_edge=0.047,       # 4.7% edge
    kelly_sized_amount=237.50,  # $237.50 = $10,000 bankroll * 0.025 kelly
    timestamp=now,
)
```

### Rejection Test Pattern
```python
# Verify ledger is NOT written when per-market limit is breached
engine = ShadowExecutionEngine(
    max_market_exposure=500.0,
    max_day_exposure=2000.0,
)
# First intent commits $400 to MKTX
intent_1 = OrderIntent(market_id="MKTX", kelly_fraction=0.04, bankroll=10_000.0, ...)
engine.process_intent(intent_1)  # accepted, ledger has 1 entry

# Second intent would push MKTX to $800 — over $500 cap
intent_2 = OrderIntent(market_id="MKTX", kelly_fraction=0.04, bankroll=10_000.0, ...)
result = engine.process_intent(intent_2)
assert result is None
assert len(engine.shadow_ledger.entries) == 1  # NOT written
```

### Kelly Sizing Delegation (from risk_agent.py)
```python
# Source: packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py
from sharpedge_trading.agents.risk_agent import compute_kelly_size
stake = compute_kelly_size(
    calibrated_prob=0.58,
    kalshi_price=0.51,
    bankroll=10_000.0,
    kelly_fraction=0.25,   # from TradingConfig.defaults()
)
# stake is clamped to [0.1%, 5%] of bankroll = [$10, $500]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TRADING_MODE=paper` controls shadow behaviour | `ENABLE_KALSHI_EXECUTION` is the live gate; shadow is the default | Phase 11 (new) | Cleaner separation: `TRADING_MODE` is about executor type; `ENABLE_KALSHI_EXECUTION` is the capital risk gate |
| `PaperExecutor` writes all shadow trades | `ShadowExecutionEngine` writes `ShadowLedger` entries pre-fill; `PaperExecutor` remains for fill simulation | Phase 11 (new) | Shadow ledger captures pre-decision signals; paper trades capture simulated fills — different semantic layers |
| Exposure limits in `ExposureBook` (venue-level cap only) | `ExposureBook` + `MarketExposureGuard` + `DayExposureGuard` | Phase 11 (new) | Three orthogonal limits: venue concentration, per-market dollar cap, per-day dollar cap |

---

## Open Questions

1. **Where does `max_market_exposure` and `max_day_exposure` come from?**
   - What we know: `TradingConfig` has `max_category_exposure` and `max_total_exposure` but not per-market or per-day limits specific to shadow mode.
   - What's unclear: Should these be new columns in the `trading_config` Supabase table, env vars, or constructor arguments with config-file defaults?
   - Recommendation: Use env vars (`SHADOW_MAX_MARKET_EXPOSURE`, `SHADOW_MAX_DAY_EXPOSURE`) with hardcoded defaults (e.g. `$500` per market, `$2000` per day) consistent with existing `TradingConfig._DEFAULTS`. This avoids a Supabase schema migration for Phase 11 and keeps the config story simple.

2. **Does Phase 11 need to wire into the existing daemon event bus?**
   - What we know: `run_daemon()` uses an `EventBus` → `_run_execution()` → `executor.execute()` chain. `ShadowExecutionEngine` is a new layer that could replace `_run_execution()` in shadow mode, or be invoked upstream of it.
   - What's unclear: The success criteria describe "start shadow mode and verify signals produce ledger entries" — this sounds like a CLI / script invocation, not necessarily the full daemon.
   - Recommendation: Phase 11 should provide `ShadowExecutionEngine` as a standalone, testable class. The daemon integration (wiring it into the event bus loop) is a follow-on task within Phase 11, but the core unit is self-contained. The planner can split this into Wave 0 (stubs + tests), Wave 1 (core engine), Wave 2 (daemon wiring).

3. **Should `ShadowLedger` persist to a new Supabase table?**
   - What we know: `SettlementLedger` optionally writes to `ledger_entries`. Phase 14 (DASH-02) will need to query shadow signals for the paper-trading summary page.
   - What's unclear: Is a new `shadow_ledger_entries` Supabase table needed in Phase 11, or can it be deferred to Phase 14?
   - Recommendation: For Phase 11, in-memory `ShadowLedger` is sufficient (mirrors how `SettlementLedger` works without Supabase). Add a `shadow_ledger_entries` DDL stub and Supabase write path as an optional wave in Phase 11, so Phase 14 has a table to query without a surprise migration.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24 |
| Config file | `packages/venue_adapters/pyproject.toml` — `[tool.pytest.ini_options] asyncio_mode = "auto"` |
| Quick run command | `cd /path/to/sharpedge && uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py -x` |
| Full suite command | `uv run pytest packages/venue_adapters/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | Shadow mode produces ledger entries and makes zero Kalshi API calls | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_shadow_mode_no_kalshi_calls -x` | Wave 0 |
| EXEC-01 | Operator can verify mode is "shadow" (no `ENABLE_KALSHI_EXECUTION` flag) | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_shadow_mode_detection -x` | Wave 0 |
| EXEC-02 | Accepted intent produces entry with market_id, predicted_edge, kelly_sized_amount, timestamp | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_ledger_entry_fields -x` | Wave 0 |
| EXEC-02 | ShadowLedgerEntry rejects naive (non-UTC) timestamp | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_naive_timestamp_rejected -x` | Wave 0 |
| EXEC-04 | Intent that breaches per-market cap is rejected before ledger write | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_per_market_limit_rejection -x` | Wave 0 |
| EXEC-04 | After per-market rejection, ledger entry count is unchanged | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_per_market_rejection_no_ledger_write -x` | Wave 0 |
| EXEC-04 | Intent that pushes cumulative day exposure over limit is rejected before ledger write | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_per_day_limit_rejection -x` | Wave 0 |
| EXEC-04 | After per-day rejection, ledger entry count is unchanged | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_per_day_rejection_no_ledger_write -x` | Wave 0 |
| EXEC-04 | Intents up to the per-market cap are accepted; the one that exceeds is not | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_per_market_cap_boundary -x` | Wave 0 |
| EXEC-04 | Day stake resets at UTC midnight (mocked) | unit | `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py::test_day_stake_resets_at_midnight -x` | Wave 0 |

**All tests are RED stubs in Wave 0** — they import from `sharpedge_venue_adapters.execution_engine` which does not yet exist. They fail with `ImportError` until Wave 1 implementations land.

### Sampling Rate
- **Per task commit:** `uv run pytest packages/venue_adapters/tests/test_shadow_execution_engine.py -x`
- **Per wave merge:** `uv run pytest packages/venue_adapters/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/venue_adapters/tests/test_shadow_execution_engine.py` — covers EXEC-01, EXEC-02, EXEC-04 (10 test stubs)
- [ ] `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` — stub module with `OrderIntent`, `ShadowLedgerEntry`, `ShadowLedger`, `MarketExposureGuard`, `DayExposureGuard`, `ShadowExecutionEngine` class skeletons (all methods raise `NotImplementedError`)
- [ ] Update `packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py` — export new symbols

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `packages/venue_adapters/src/sharpedge_venue_adapters/exposure.py` — ExposureBook interface, compute_allocation, AllocationDecision
- Direct code inspection: `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — SettlementLedger, LedgerEntry, append-only pattern, UTC enforcement
- Direct code inspection: `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py` — compute_kelly_size, CircuitBreakerState day-reset pattern
- Direct code inspection: `packages/trading_swarm/src/sharpedge_trading/execution/paper_executor.py` — PaperExecutor, idempotency key pattern
- Direct code inspection: `packages/trading_swarm/src/sharpedge_trading/execution/executor_factory.py` — TRADING_MODE env var pattern
- Direct code inspection: `packages/trading_swarm/src/sharpedge_trading/daemon.py` — run_daemon, event bus wiring, ENABLE_KALSHI_EXECUTION context

### Secondary (MEDIUM confidence)
- Direct code inspection: `packages/trading_swarm/src/sharpedge_trading/config.py` — TradingConfig defaults, bounds, _DEFAULTS dict (informs default values for new exposure limits)
- Direct code inspection: `packages/analytics/src/sharpedge_analytics/pm_edge_scanner.py` — PMEdge structure, signal fields (predicted_edge maps to edge_pct / 100.0)
- `.planning/STATE.md` accumulated context — confirms ExposureBook from Phase 6 (RISK-01), SettlementLedger from Phase 6 (SETTLE-01)

### Tertiary (LOW confidence)
- None — all findings are from first-party codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in the workspace, versions pinned
- Architecture: HIGH — directly derived from existing patterns in tested Phase 6 code
- Pitfalls: HIGH — derived from reading actual code paths and existing test files
- Validation: HIGH — test framework is configured, asyncio_mode=auto confirmed in pyproject.toml

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable internal codebase; 30-day validity)
