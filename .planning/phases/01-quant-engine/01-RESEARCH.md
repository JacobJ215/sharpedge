# Phase 1: Quant Engine - Research

**Researched:** 2026-03-13
**Domain:** Pure-Python quantitative primitives — Monte Carlo simulation, regime detection, alpha composition, walk-forward backtesting, CLV tracking
**Confidence:** HIGH (existing codebase is the primary source; all key files read directly)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUANT-01 | System calculates composite alpha score (EV × regime_scale × survival_prob × confidence_mult) for every betting opportunity | `ev_calculator.py` already produces `prob_edge_positive` and `EVCalculation`; new `AlphaComposer` multiplies these with regime/survival/confidence factors |
| QUANT-02 | System simulates 2000 bankroll paths and returns ruin probability, P5/P50/P95 outcomes, and max drawdown distribution for a given bet | New `MonteCarloSimulator` in `packages/models/monte_carlo.py`; must use `np.random.default_rng()` per call — not global seed |
| QUANT-03 | System classifies current betting market into one of 7 regime states with confidence score | New `BettingRegimeDetector` in `packages/analytics/regime.py`; start with 3-4 states (decision locked); HMM state count gated on data audit |
| QUANT-04 | System detects when a spread/total is at or near a key number and returns historical cover rate, half-point value, and zone strength | `key_numbers.py` already has `analyze_key_numbers()` and per-sport frequency tables; needs `KeyNumberZoneDetector` wrapper that exposes cover rate, half-point value, and zone strength fields |
| QUANT-05 | System produces walk-forward backtest report with out-of-sample win rate, out-of-sample ROI, per-window results, and quality badge | New `WalkForwardBacktester` in `packages/models/walk_forward.py`; 4 DB stub methods in `backtesting.py` must be implemented first |
| QUANT-06 | System tracks CLV (closing line value) for each bet and updates user's CLV stats after game closes | `BacktestResult.closing_line` field already exists; `_update_outcome_db` stub must be implemented; new CLV stat aggregator needed |
</phase_requirements>

---

## Summary

Phase 1 is a pure-Python computation layer with no LangGraph or I/O dependencies. The goal is to build six quant primitives that all downstream phases will call as black-box functions. The existing codebase provides a strong foundation: `ev_calculator.py` has a complete Bayesian EV implementation with Beta-distribution uncertainty quantification, `key_numbers.py` has per-sport frequency tables for NFL/NBA/MLB/NHL/NCAAF, and `backtesting.py` has the calibration bin and Brier score machinery. The missing pieces are `MonteCarloSimulator`, `AlphaComposer`, `BettingRegimeDetector` (wrapper), `WalkForwardBacktester`, and CLV aggregation.

There are four pre-phase debt items that must be cleared before new code is written: the 4 unimplemented DB stubs in `backtesting.py`, the `datetime.utcnow()` occurrences in 3 model files (7 call sites), the `visualizations.py` module at 896 lines needing a split before callers break, and the global `np.random.seed()` pattern in the Monte Carlo path. None of these are new features — they are blocking correctness guarantees for what Phase 1 adds.

**Primary recommendation:** Build each quant primitive as a pure, stateless function or class that accepts plain Python data and returns a typed dataclass. No database calls, no Redis, no HTTP inside quant modules. Nodes in Phase 2's LangGraph graph are the I/O boundary; quant modules are the computation boundary.

---

## Standard Stack

### Core (already present — extend, do not replace)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.0+ | Monte Carlo path simulation, array math | Vectorized `rng.choice` across (n_paths, n_bets) shape; already in workspace |
| scipy | 1.14+ | Beta distribution for Bayesian EV, Wilson interval | `scipy.stats.beta` used throughout `ev_calculator.py`; already present |
| scikit-learn | 1.5+ | Calibration, model pipeline | `CalibratedClassifierCV` for Platt scaling in Phase 5; already present |
| pydantic | 2.0+ | Input validation at system boundaries | All public API inputs validated; already enforced project-wide |
| pytest | 8.0+ | Test framework | Configured in root `pyproject.toml`; `pytest-asyncio` and `pytest-mock` included |

### New Additions (Phase 1 only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hmmlearn | 0.3.x | Gaussian HMM for regime detection | Only if rule-based classifier proves insufficient after data audit; start with rules |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hmmlearn | pomegranate | pomegranate v1 added PyTorch dependency (2GB), breaking API changes; hmmlearn is stable and sklearn-compatible |
| hmmlearn | statsmodels HMM | Less feature-complete; no Gaussian mixture emissions |
| Rule-based regime | HMM from day one | Sparse betting data may not support HMM training; rules give a working baseline immediately |

**Installation (new dependency only):**
```bash
uv add hmmlearn --package sharpedge-analytics
```

---

## Architecture Patterns

### Recommended Module Layout (Phase 1 additions)

```
packages/models/src/sharpedge_models/
    ├── ev_calculator.py        # EXISTS — extend only (add alpha_score output to EVCalculation)
    ├── backtesting.py          # EXISTS — implement 4 DB stubs; fix datetime.utcnow()
    ├── monte_carlo.py          # NEW — MonteCarloSimulator
    ├── alpha.py                # NEW — AlphaComposer + BettingAlpha dataclass
    └── walk_forward.py         # NEW — WalkForwardBacktester

packages/analytics/src/sharpedge_analytics/
    ├── key_numbers.py          # EXISTS — add KeyNumberZoneDetector wrapper class
    ├── regime.py               # NEW — BettingRegimeDetector
    └── visualizations/         # SPLIT from visualizations.py (896 lines → sub-modules)
        ├── __init__.py         # Re-export everything currently exported (backward compat)
        ├── line_charts.py      # create_line_movement_chart, create_bankroll_chart
        ├── ev_charts.py        # create_ev_distribution_chart, create_clv_chart
        └── public_charts.py    # create_public_betting_chart
```

**File size constraint:** All files under 500 lines (project rule from CLAUDE.md). The split of `visualizations.py` must happen before any new analytics code is added, because callers in `research.py` use direct function imports that will continue to work via `__init__.py` re-exports.

### Pattern 1: Stateless Quant Module

Each Phase 1 module is a pure function or a stateless class whose methods are pure functions. No module-level mutable state, no database calls, no Redis.

```python
# packages/models/src/sharpedge_models/monte_carlo.py
# Source: pattern from .planning/research/STACK.md (HIGH confidence)

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class MonteCarloResult:
    ruin_probability: float
    p05_bankroll: float
    p50_bankroll: float
    p95_bankroll: float
    max_drawdown_p50: float
    n_paths: int
    n_bets: int


def simulate_bankroll(
    win_prob: float,
    win_pct: float,
    loss_pct: float,
    initial_bankroll: float = 1.0,
    n_paths: int = 2000,
    n_bets: int = 500,
    seed: int | None = None,   # None in production, fixed in tests
) -> MonteCarloResult:
    """Simulate bankroll paths. seed=None for production (non-reproducible)."""
    rng = np.random.default_rng(seed)  # Per-call instance, NOT np.random.seed()
    outcomes = rng.choice(
        [win_pct, -loss_pct],
        size=(n_paths, n_bets),
        p=[win_prob, 1 - win_prob],
    )
    paths = initial_bankroll * np.cumprod(1 + outcomes, axis=1)
    ruin_mask = np.any(paths <= 0.1 * initial_bankroll, axis=1)
    final = paths[:, -1]
    drawdowns = 1 - paths / np.maximum.accumulate(paths, axis=1)
    return MonteCarloResult(
        ruin_probability=float(np.mean(ruin_mask)),
        p05_bankroll=float(np.percentile(final, 5)),
        p50_bankroll=float(np.percentile(final, 50)),
        p95_bankroll=float(np.percentile(final, 95)),
        max_drawdown_p50=float(np.percentile(drawdowns.max(axis=1), 50)),
        n_paths=n_paths,
        n_bets=n_bets,
    )
```

### Pattern 2: Alpha Composition with Floor Guard

The multiplicative formula must have a minimum `edge_score` floor before multipliers are applied to prevent regime-boosted weak edges from appearing as PREMIUM.

```python
# packages/models/src/sharpedge_models/alpha.py
# Source: .planning/research/PITFALLS.md Pitfall 9 (HIGH confidence, project doc)

from dataclasses import dataclass
from typing import Literal

EDGE_SCORE_FLOOR = 0.05  # Below this, badge is forced to SPECULATIVE


@dataclass(frozen=True)
class BettingAlpha:
    alpha: float
    edge_score: float
    regime_scale: float
    survival_prob: float
    confidence_mult: float
    quality_badge: Literal["PREMIUM", "HIGH", "MEDIUM", "SPECULATIVE"]


def compose_alpha(
    edge_score: float,       # prob_edge_positive from ev_calculator
    regime_scale: float,     # 1.0-1.4 from BettingRegimeDetector
    survival_prob: float,    # 1 - ruin_probability from MonteCarloSimulator
    confidence_mult: float,  # calibration multiplier (1.0 until Phase 5)
) -> BettingAlpha:
    # Floor guard: weak edge cannot be promoted by multipliers
    if edge_score < EDGE_SCORE_FLOOR:
        return BettingAlpha(
            alpha=edge_score,
            edge_score=edge_score,
            regime_scale=regime_scale,
            survival_prob=survival_prob,
            confidence_mult=confidence_mult,
            quality_badge="SPECULATIVE",
        )

    alpha = edge_score * regime_scale * survival_prob * confidence_mult

    if alpha >= 0.15:
        badge = "PREMIUM"
    elif alpha >= 0.08:
        badge = "HIGH"
    elif alpha >= 0.03:
        badge = "MEDIUM"
    else:
        badge = "SPECULATIVE"

    return BettingAlpha(
        alpha=alpha,
        edge_score=edge_score,
        regime_scale=regime_scale,
        survival_prob=survival_prob,
        confidence_mult=confidence_mult,
        quality_badge=badge,
    )
```

### Pattern 3: Regime Detector — Rule-Based First

Start with a deterministic rule-based classifier using inputs already available in the codebase (ticket%, handle%, line movement velocity, book alignment). Add HMM only after data audit confirms sufficient observations per state.

```python
# packages/analytics/src/sharpedge_analytics/regime.py
# Source: .planning/research/PITFALLS.md Pitfall 4 (HIGH confidence)

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class RegimeState(str, Enum):
    SHARP_CONSENSUS = "SHARP_CONSENSUS"    # scale=1.3
    STEAM_MOVE = "STEAM_MOVE"             # scale=1.4
    PUBLIC_HEAVY = "PUBLIC_HEAVY"          # scale=0.8
    SETTLED = "SETTLED"                    # scale=1.0


REGIME_SCALE: dict[RegimeState, float] = {
    RegimeState.SHARP_CONSENSUS: 1.3,
    RegimeState.STEAM_MOVE: 1.4,
    RegimeState.PUBLIC_HEAVY: 0.8,
    RegimeState.SETTLED: 1.0,
}


@dataclass(frozen=True)
class RegimeClassification:
    regime: RegimeState
    confidence: float   # 0-1
    scale: float        # regime_scale for AlphaComposer


def classify_regime(
    ticket_pct: float,        # public ticket percentage (0-1)
    handle_pct: float,        # public handle percentage (0-1)
    line_move_pts: float,     # absolute line movement since open
    move_velocity: float,     # points per hour
    book_alignment: float,    # fraction of books moving same direction (0-1)
) -> RegimeClassification:
    """Rule-based regime classifier. HMM upgrade path available post-data-audit."""
    # Steam: fast, large, consensus move
    if move_velocity >= 0.5 and book_alignment >= 0.75:
        confidence = min(0.9, book_alignment)
        return RegimeClassification(RegimeState.STEAM_MOVE, confidence, REGIME_SCALE[RegimeState.STEAM_MOVE])

    # Public heavy: ticket% >> handle% suggests public one-way action
    if ticket_pct >= 0.65 and handle_pct <= 0.50:
        confidence = min(0.85, ticket_pct)
        return RegimeClassification(RegimeState.PUBLIC_HEAVY, confidence, REGIME_SCALE[RegimeState.PUBLIC_HEAVY])

    # Sharp consensus: handle% exceeds ticket% (sharp money on one side)
    if handle_pct >= 0.60 and handle_pct > ticket_pct + 0.15:
        confidence = min(0.85, handle_pct - ticket_pct + 0.5)
        return RegimeClassification(RegimeState.SHARP_CONSENSUS, confidence, REGIME_SCALE[RegimeState.SHARP_CONSENSUS])

    # Default: settled market
    return RegimeClassification(RegimeState.SETTLED, 0.6, REGIME_SCALE[RegimeState.SETTLED])
```

### Pattern 4: Walk-Forward Backtest with Non-Overlapping Windows

```python
# packages/models/src/sharpedge_models/walk_forward.py
# Source: .planning/research/PITFALLS.md Pitfall 8 (HIGH confidence, project doc)

from dataclasses import dataclass
from typing import Literal


@dataclass
class WindowResult:
    window_id: int
    train_ids: list[str]
    test_ids: list[str]
    out_of_sample_win_rate: float
    out_of_sample_roi: float
    n_bets: int


@dataclass
class BacktestReport:
    windows: list[WindowResult]
    overall_win_rate: float
    overall_roi: float
    quality_badge: Literal["low", "medium", "high", "excellent"]


def quality_badge_from_windows(windows: list[WindowResult]) -> str:
    """Quality badge requires >= 3 non-overlapping windows with positive ROI."""
    if len(windows) < 2:
        return "low"
    n_positive = sum(1 for w in windows if w.out_of_sample_roi > 0)
    if len(windows) >= 4 and n_positive >= 3:
        return "excellent"
    elif len(windows) >= 3 and n_positive >= 2:
        return "high"
    elif n_positive >= 1:
        return "medium"
    return "low"
```

### Pattern 5: Fix datetime.utcnow() Before Walking Forward

Seven call sites use `datetime.utcnow()` across `backtesting.py`, `arbitrage.py`, and `ml_inference.py`. This must be resolved before any window comparison logic is written, because timezone-naive datetimes mixed with timezone-aware comparisons produce incorrect window boundaries.

```python
# BEFORE (all 7 sites)
from datetime import datetime
timestamp = datetime.utcnow()

# AFTER
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)
```

### Anti-Patterns to Avoid

- **I/O inside quant modules:** `MonteCarloSimulator`, `AlphaComposer`, `BettingRegimeDetector` must not call Supabase or Redis. Data flows in as plain Python types; results flow out as dataclasses. Phase 2 graph nodes own I/O.
- **Global numpy RNG:** `np.random.seed(42)` is not thread-safe. Use `np.random.default_rng(seed)` with `seed=None` in production.
- **Overlapping walk-forward windows:** Training windows must be non-overlapping. Assert `len(set(train_ids) & set(test_ids)) == 0` per window in tests.
- **Skipping the edge floor:** Adding multipliers before checking `edge_score >= 0.05` will promote weak setups to HIGH/PREMIUM via regime boost.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Probability calibration | Custom sigmoid fitting | `sklearn.calibration.CalibratedClassifierCV(method='sigmoid')` | Handles edge cases at prob boundaries; tested against thousands of datasets |
| Wilson score intervals | Manual formula | Already implemented in `backtesting.py._wilson_score_interval()` | Correct formula already in codebase — call it, don't duplicate |
| Beta distribution CDF | Manual integration | `scipy.stats.beta.cdf()` | Numerically stable; already used in `ev_calculator.py` |
| AUC-ROC | Manual concordant pair count | `sklearn.metrics.roc_auc_score()` | The existing `_calculate_discrimination()` has a subtle bug (double loop via list comprehension); replace with sklearn |
| HMM training | Custom Baum-Welch EM | `hmmlearn.hmm.GaussianHMM` | Baum-Welch is numerically tricky; hmmlearn handles numerical underflow |

**Key insight:** The quant domain has decades of well-tested numerical implementations. The project's value is in the domain logic (regime scales, alpha thresholds, walk-forward design), not in reimplementing statistics primitives.

---

## Common Pitfalls

### Pitfall 1: Global numpy RNG Breaks Concurrent Requests
**What goes wrong:** `np.random.seed(42)` sets global process state. Two concurrent FastAPI requests calling `simulate_bankroll()` will contaminate each other's path distributions.
**Why it happens:** The FinnAI original used a deterministic seed for test reproducibility; the pattern was carried over.
**How to avoid:** Use `np.random.default_rng(seed=None)` in production. Only pass an explicit `seed` in test fixtures.
**Warning signs:** Two users simulating different `win_prob` values get identical variance.

### Pitfall 2: Backtesting Stubs Must Be Implemented First
**What goes wrong:** `_store_to_db`, `_update_outcome_db`, `_fetch_resolved_predictions`, `_count_predictions` all return `pass` or `[]`. Walk-forward windows computed from DB data will silently return empty lists, producing a "no data" report that looks like a valid result.
**Why it happens:** Stubs were placeholders left during initial build — 4 methods at lines 339–366 of `backtesting.py`.
**How to avoid:** Implement all 4 before any walk-forward window logic is written.
**Warning signs:** `BacktestReport` shows 0 windows but no error raised.

### Pitfall 3: Walk-Forward Window Overlap Inflates Out-of-Sample Metrics
**What goes wrong:** Rolling windows that reuse the same bets in multiple training sets make the model appear more consistent than it is.
**Why it happens:** Rolling window is the default; non-overlapping requires explicit design.
**How to avoid:** Use expanding train / fixed test windows (Season N train → Season N+1 test, then Seasons N+N+1 train → Season N+2 test). Assert zero overlap in tests.
**Warning signs:** Quality badge reads "excellent" for a strategy with flat or negative real-money results.

### Pitfall 4: HMM Starts at 7 States — Underfitting
**What goes wrong:** NFL has ~270 games/year. Some regimes (STEAM_MOVE, THIN_MARKET) occur infrequently. A 7-state HMM needs ~700–2000+ labeled observations to converge; sports data is far below this threshold.
**Why it happens:** REQUIREMENTS.md specifies 7 regime states (QUANT-03). The requirement text names 7 states, but the success criteria only require "minimum 3 states."
**How to avoid:** Start with 3–4 states. The requirement is satisfied with 3 states. Expand to 7 only after an audit of Supabase confirms sufficient observations per state.
**Warning signs:** After HMM training, `model.transmat_` has one or two rows with near-zero probability — degenerate convergence.

### Pitfall 5: Visualizations Split Breaks Bot Command Imports
**What goes wrong:** `research.py` imports 5 functions directly from `sharpedge_analytics.visualizations`. A naive split to sub-modules breaks all 5 imports.
**Why it happens:** Python import paths are not automatically forwarded.
**How to avoid:** Split to `visualizations/` subdirectory with `__init__.py` that re-exports all current public names. Verify with a quick `python -c "from sharpedge_analytics.visualizations import create_line_movement_chart"` smoke test before committing.
**Warning signs:** `ImportError` in the Discord bot after the split.

### Pitfall 6: Alpha Floor Not Enforced — Regime Boost Promotes Weak Edges
**What goes wrong:** `edge_score = 0.04` (SPECULATIVE) × `regime_scale = 1.4` × `survival_prob = 0.97` × `confidence_mult = 1.1` = `0.059` → would qualify as MEDIUM without a floor check.
**Why it happens:** Multiplicative formula without a floor.
**How to avoid:** Check `edge_score < EDGE_SCORE_FLOOR` before applying multipliers.
**Warning signs:** MEDIUM or HIGH alerts for bets where `prob_edge_positive < 0.60`.

---

## Code Examples

Verified from existing codebase and project research documents:

### Existing EV Calculator — What to Preserve
```python
# Source: packages/models/src/sharpedge_models/ev_calculator.py (read directly)
# prob_edge_positive is the output that becomes edge_score in AlphaComposer

ev_calc = calculate_ev(model_prob=0.58, odds=-110)
# ev_calc.prob_edge_positive -> float (0-1), e.g. 0.81
# ev_calc.confidence_level   -> ConfidenceLevel enum
# ev_calc.kelly_full          -> kelly fraction (already capped at 0.25)
```

### Key Number Detector — What to Wrap
```python
# Source: packages/analytics/src/sharpedge_analytics/key_numbers.py (read directly)
# analyze_key_numbers() is already implemented; needs a typed wrapper

from sharpedge_analytics.key_numbers import analyze_key_numbers, KeyNumberAnalysis

analysis: KeyNumberAnalysis = analyze_key_numbers(line=-3.0, sport="NFL")
# analysis.crosses_key      -> bool
# analysis.key_frequency    -> float (0.152 for NFL -3)
# analysis.value_adjustment -> float (15.2 for being on hook side)
# analysis.nearest_key      -> int
# analysis.distance_to_key  -> float
```

### BacktestEngine Stubs to Implement
```python
# Source: packages/models/src/sharpedge_models/backtesting.py lines 339–366 (read directly)
# These 4 methods need Supabase schema-based implementation:

def _store_to_db(self, result: BacktestResult) -> None:
    # INSERT INTO backtest_predictions (...) VALUES (...)
    pass  # TODO

def _update_outcome_db(self, prediction_id: str, won: bool, closing_line: float | None) -> None:
    # UPDATE backtest_predictions SET outcome=won, closing_line=closing_line WHERE prediction_id=...
    pass  # TODO — this is also the CLV update path (QUANT-06)

def _fetch_resolved_predictions(self, market_type: str, sport: str | None) -> list[BacktestResult]:
    # SELECT * FROM backtest_predictions WHERE outcome IS NOT NULL AND market_type=...
    return []  # TODO

def _count_predictions(self, market_type: str, sport: str | None) -> int:
    # SELECT COUNT(*) FROM backtest_predictions WHERE market_type=...
    return 0  # TODO
```

### CLV Calculation Pattern
```python
# Source: QUANT-06 requirement + existing BacktestResult.closing_line field
# CLV = opening_odds - closing_odds (in implied probability terms)

def calculate_clv(bet_odds: int, closing_line_odds: int) -> float:
    """Closing line value: positive means bet before line moved against you."""
    from sharpedge_models.ev_calculator import american_to_implied
    bet_prob = american_to_implied(bet_odds)
    closing_prob = american_to_implied(closing_line_odds)
    return closing_prob - bet_prob  # positive = beat the close
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `np.random.seed()` global state | `np.random.default_rng()` per-call Generator | numpy 1.17 (2019) | Thread-safe Monte Carlo |
| `datetime.utcnow()` (deprecated) | `datetime.now(timezone.utc)` | Python 3.12 deprecation warning | Correct timezone-aware comparisons |
| sklearn `base_estimator` param | sklearn `estimator` param | sklearn 1.2 | `CalibratedClassifierCV(estimator=..., cv='prefit')` — old name raises deprecation warning |

**Deprecated/outdated in codebase:**
- `datetime.utcnow()`: 7 call sites in `backtesting.py`, `arbitrage.py`, `ml_inference.py` — raises `DeprecationWarning` in Python 3.12, scheduled for removal in 3.14
- `_calculate_discrimination()` in `backtesting.py`: manual concordant pair counting via list comprehension is O(n²); replace with `sklearn.metrics.roc_auc_score`

---

## Open Questions

1. **HMM state count: 3 vs 7**
   - What we know: Decision is locked at "start with 3–4 states" (STATE.md Key Decisions)
   - What's unclear: How many seasons of data are in Supabase per sport — the HMM upgrade path to 7 states depends on this
   - Recommendation: Proceed with 4-state rule-based classifier; add a TODO comment in `regime.py` pointing to the data audit step as the unlock condition for HMM

2. **Supabase backtest_predictions table schema**
   - What we know: `BacktestResult` dataclass has the fields needed; `_store_to_db` stub exists
   - What's unclear: Whether the table already exists in migrations or needs to be created
   - Recommendation: Check existing Supabase migrations before writing new schema; if absent, add a migration as the first sub-task of implementing the stubs

3. **CLV stats storage: in-memory aggregation vs Supabase aggregate query**
   - What we know: QUANT-06 requires "running CLV average in portfolio stats"
   - What's unclear: Whether to compute rolling average at query time or maintain a materialized aggregate
   - Recommendation: Compute at query time for Phase 1 (simpler); add materialized view in Phase 4 when portfolio page performance matters

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.24+ and pytest-mock 3.14+ |
| Config file | `pyproject.toml` (root workspace) — no `pytest.ini` present |
| Quick run command | `uv run pytest packages/models/tests/ packages/analytics/tests/ -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUANT-01 | `compose_alpha()` returns PREMIUM for high edge_score + favorable regime | unit | `uv run pytest packages/models/tests/test_alpha.py -x` | Wave 0 |
| QUANT-01 | `compose_alpha()` forces SPECULATIVE when edge_score < 0.05 regardless of multipliers | unit | `uv run pytest packages/models/tests/test_alpha.py::test_edge_floor -x` | Wave 0 |
| QUANT-02 | `simulate_bankroll()` returns correct ruin_probability shape and value range | unit | `uv run pytest packages/models/tests/test_monte_carlo.py -x` | Wave 0 |
| QUANT-02 | Two concurrent calls with `seed=None` return different distributions | unit | `uv run pytest packages/models/tests/test_monte_carlo.py::test_thread_safety -x` | Wave 0 |
| QUANT-03 | `classify_regime()` returns STEAM_MOVE for fast consensus line movement | unit | `uv run pytest packages/analytics/tests/test_regime.py -x` | Wave 0 |
| QUANT-03 | `classify_regime()` returns PUBLIC_HEAVY when ticket% >> handle% | unit | `uv run pytest packages/analytics/tests/test_regime.py::test_public_heavy -x` | Wave 0 |
| QUANT-04 | `analyze_key_numbers(-3.0, "NFL")` returns `crosses_key=False`, `key_frequency=0.152` | unit | `uv run pytest packages/analytics/tests/test_key_numbers.py -x` | Wave 0 |
| QUANT-04 | `analyze_key_numbers(-2.5, "NFL")` returns `crosses_key=True` | unit | `uv run pytest packages/analytics/tests/test_key_numbers.py::test_hook_detection -x` | Wave 0 |
| QUANT-05 | Walk-forward windows have zero overlap between train and test IDs | unit | `uv run pytest packages/models/tests/test_walk_forward.py::test_no_overlap -x` | Wave 0 |
| QUANT-05 | Quality badge "low" when < 2 windows, "excellent" when >= 4 windows with 3+ positive ROI | unit | `uv run pytest packages/models/tests/test_walk_forward.py::test_quality_badge -x` | Wave 0 |
| QUANT-06 | `calculate_clv(bet_odds=-110, closing_line_odds=-120)` returns positive float | unit | `uv run pytest packages/models/tests/test_clv.py -x` | Wave 0 |
| QUANT-06 | `record_outcome()` persists `closing_line` for later CLV aggregation | unit | `uv run pytest packages/models/tests/test_backtesting.py::test_outcome_persistence -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/models/tests/ packages/analytics/tests/ -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (must be created before implementation starts)

- [ ] `packages/models/tests/__init__.py` — package marker
- [ ] `packages/models/tests/test_monte_carlo.py` — covers QUANT-02
- [ ] `packages/models/tests/test_alpha.py` — covers QUANT-01
- [ ] `packages/models/tests/test_walk_forward.py` — covers QUANT-05
- [ ] `packages/models/tests/test_clv.py` — covers QUANT-06
- [ ] `packages/models/tests/test_backtesting.py` — covers DB stub implementations
- [ ] `packages/analytics/tests/__init__.py` — package marker
- [ ] `packages/analytics/tests/test_regime.py` — covers QUANT-03
- [ ] `packages/analytics/tests/test_key_numbers.py` — covers QUANT-04 (wraps existing `key_numbers.py`)
- [ ] Framework install: already present — `pytest`, `pytest-asyncio`, `pytest-mock` in root `pyproject.toml` dev deps

---

## Sources

### Primary (HIGH confidence)

- `/Users/revph/sharpedge/packages/models/src/sharpedge_models/ev_calculator.py` — existing EV and Bayesian confidence implementation read directly
- `/Users/revph/sharpedge/packages/models/src/sharpedge_models/backtesting.py` — confirmed 4 stub methods at lines 339–366; confirmed 3 `datetime.utcnow()` call sites
- `/Users/revph/sharpedge/packages/models/src/sharpedge_models/ml_inference.py` — confirmed 2 `datetime.utcnow()` call sites; global `_model_manager` singleton pattern documented
- `/Users/revph/sharpedge/packages/analytics/src/sharpedge_analytics/key_numbers.py` — existing per-sport key number tables and `KeyNumberAnalysis` dataclass read directly
- `/Users/revph/sharpedge/packages/models/src/sharpedge_models/arbitrage.py` — confirmed 2 `datetime.utcnow()` call sites
- `/Users/revph/sharpedge/.planning/research/STACK.md` — Monte Carlo `np.random.default_rng()` pattern; hmmlearn selection rationale
- `/Users/revph/sharpedge/.planning/research/PITFALLS.md` — all 6 Phase 1 pitfalls documented with code examples
- `/Users/revph/sharpedge/.planning/research/ARCHITECTURE.md` — module placement, quant module independence principle, build order
- `/Users/revph/sharpedge/.planning/STATE.md` — locked decisions: HMM starts 3–4 states, keep ev_calculator, datetime fix required
- `/Users/revph/sharpedge/.planning/REQUIREMENTS.md` — QUANT-01 through QUANT-06 definitions
- `/Users/revph/sharpedge/pyproject.toml` — confirmed pytest/pytest-asyncio/pytest-mock in dev dependencies

### Secondary (MEDIUM confidence)

- numpy `default_rng` API: stable since numpy 1.17; MEDIUM because exact 2.0 API surface not verified against live docs
- hmmlearn 0.3.x: training knowledge through August 2025; verify on PyPI before adding to `pyproject.toml`
- `CalibratedClassifierCV(estimator=...)` parameter rename from `base_estimator`: sklearn 1.2+ change; MEDIUM confidence — verify against installed sklearn version

### Tertiary (LOW confidence)

- HMM minimum observation count heuristics (700–2000): derived from standard HMM sample complexity literature; not from an authoritative sklearn/hmmlearn source — treat as directional guidance, not a hard threshold

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries read from existing `pyproject.toml` and source files; no guessing
- Architecture: HIGH — module layout derived from existing source tree and project architecture documents
- Pitfalls: HIGH for Monte Carlo RNG, datetime deprecation, stub status, and visualizations split (all directly verified in source); MEDIUM for HMM state count heuristics
- Test infrastructure: HIGH — pytest config confirmed in root `pyproject.toml`; zero existing test files confirmed by `find` scan

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (90 days — stable Python numerical stack; re-verify hmmlearn version before adding)
