---
phase: 13-ablation-validation-capital-gate
verified: 2026-03-20T12:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 13: Ablation Validation & Capital Gate Verification Report

**Phase Goal:** Prove the model adds edge beyond fees and lock live execution behind operator-approved capital controls.
**Verified:** 2026-03-20
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All GATE and ABLATE test files exist and import without ImportError | VERIFIED | 19 tests collected, 0 import errors |
| 2 | CapitalGate.check() returns pass/fail for all 4 conditions in one call | VERIFIED | `check()` calls 4 private methods, returns `GateStatus` with `conditions` list |
| 3 | assert_ready() collects ALL failures before raising CapitalGateError | VERIFIED | `test_assert_ready_collects_all_failures` — GATE-01 through GATE-04 all appear in error message |
| 4 | GATE-01 rejects when any of the 5 .joblib artifacts is missing | VERIFIED | `test_gate01_fails_missing_artifact` passes; checks each of 5 CATEGORIES |
| 5 | GATE-02 rejects when paper-trading period is <7 days or metrics below thresholds | VERIFIED | 3 failure cases tested (days, positive_rate, mean_edge) and 1 pass case |
| 6 | GATE-03 rejects when live_approval.json is absent, invalid, or stale | VERIFIED | 3 failure cases (missing, invalid JSON, stale snapshot) + pass case tested |
| 7 | GATE-04 circuit breaker renames live_approval.json to .disabled on drawdown breach | VERIFIED | `test_gate04_breach_invalidates_approval` — `.disabled` file created, original removed |
| 8 | from_env() in ShadowExecutionEngine calls assert_ready() only in live mode | VERIFIED | Import and call are inside `ENABLE_KALSHI_EXECUTION == "true"` block (execution_engine.py lines 255-256) |
| 9 | Operator can run ablation backtest with per-category + overall edge delta report | VERIFIED | `compute_ablation_report()` implemented; `scripts/run_ablation.py` CLI exists and wired |
| 10 | Ablation report shows PASS/FAIL with configurable threshold | VERIFIED | `result["passed"]` and per-category `passed` verified by all 3 ablation tests |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Details |
|----------|-----------|--------------|--------|---------|
| `packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py` | 120 | 347 | VERIFIED | Exports CapitalGate, CapitalGateError, GateStatus, GateCondition, CATEGORIES; no NotImplementedError |
| `packages/venue_adapters/src/sharpedge_venue_adapters/ablation.py` | 50 | 135 | VERIFIED | Exports compute_ablation_report; no NotImplementedError |
| `packages/venue_adapters/tests/test_capital_gate.py` | 100 | 358 | VERIFIED | 16 test functions; all pass |
| `packages/venue_adapters/tests/test_ablation.py` | 40 | 121 | VERIFIED | 3 test functions; all pass |
| `scripts/approve_live.py` | 40 | 64 | VERIFIED | Operator approval CLI with sys.exit guards |
| `scripts/run_ablation.py` | 40 | 91 | VERIFIED | Supabase fetch + console table + JSON output |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_capital_gate.py` | `capital_gate.py` | `from sharpedge_venue_adapters.capital_gate import CapitalGate, CapitalGateError, GateStatus, GateCondition, CATEGORIES` | WIRED | Import resolves; 19 tests confirm no ImportError |
| `test_ablation.py` | `ablation.py` | `from sharpedge_venue_adapters.ablation import compute_ablation_report` | WIRED | Import resolves; 3 tests confirm no ImportError |
| `execution_engine.py` | `capital_gate.py` | `from sharpedge_venue_adapters.capital_gate import CapitalGate` inside live-mode if-block | WIRED | Lines 255-256 inside `ENABLE_KALSHI_EXECUTION == "true"` block only; shadow mode untouched |
| `capital_gate.py` | `data/live_approval.json` | `_approval_path` read in `_check_approval()` | WIRED | `self._approval_path.exists()` and `self._approval_path.read_text()` |
| `approve_live.py` | `capital_gate.py` | `from sharpedge_venue_adapters.capital_gate import CapitalGate` | WIRED | Line 13; `CapitalGate.from_env().check()` called in main() |
| `run_ablation.py` | `ablation.py` | `from sharpedge_venue_adapters.ablation import compute_ablation_report` | WIRED | Line 21; called in main() |
| `ablation.py` | `data/models/pm/*.joblib` | `joblib.load()` for each category model | WIRED | `model_path = models_dir / f"{cat}.joblib"` + `joblib.load(model_path)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ABLATE-01 | 13-01, 13-03 | Operator can run ablation backtest comparing fee-adjusted fallback vs trained-model edge | SATISFIED | `scripts/run_ablation.py` fetches from Supabase, invokes `compute_ablation_report()`, writes JSON; 3 tests pass |
| ABLATE-02 | 13-01, 13-03 | Ablation report shows edge delta per category and overall, with configurable pass/fail threshold | SATISFIED | Report dict contains `categories[cat]["delta"]`, `overall["delta"]`, `passed`; threshold via env var `ABLATION_THRESHOLD_PCT` |
| GATE-01 | 13-01, 13-02 | System rejects `ENABLE_KALSHI_EXECUTION=true` unless all 5 `.joblib` artifacts exist | SATISFIED | `_check_model_artifacts()` checks all 5 CATEGORIES; `assert_ready()` raises CapitalGateError on failure; wired in `execution_engine.py` |
| GATE-02 | 13-01, 13-02 | System requires N-day paper-trading period with acceptable edge metrics | SATISFIED | `_check_paper_period()` queries Supabase shadow_ledger; checks unique day count, positive_rate >= 55%, mean_edge >= 1.5% |
| GATE-03 | 13-01, 13-02 | Operator completes manual review CLI step before enabling live execution | SATISFIED | `scripts/approve_live.py` blocks on GATE-01/02 failure, prompts operator name, writes timestamped `live_approval.json` with gate_snapshot |
| GATE-04 | 13-01, 13-02 | System auto-disables live execution if daily realized loss exceeds drawdown threshold | SATISFIED | `record_daily_loss()` renames `live_approval.json` to `.disabled` on breach; UTC midnight reset implemented; circuit breaker check in `_check_circuit_breaker()` |

All 6 requirements mapped to phase 13 in REQUIREMENTS.md traceability table are satisfied. No orphaned requirements.

---

### Anti-Patterns Found

None. Scan across all 4 implementation files returned 0 matches for: TODO, FIXME, XXX, HACK, PLACEHOLDER, return null, return {}, return [].

---

### Human Verification Required

#### 1. Operator approval workflow (interactive CLI)

**Test:** With SUPABASE_URL/SUPABASE_SERVICE_KEY set and model artifacts in `data/models/pm/`, run `python scripts/approve_live.py` and follow the prompts.
**Expected:** Gate status table is printed; if GATE-01 and GATE-02 pass, operator is prompted for their name; `data/live_approval.json` is written with correct schema (`approved_by`, `approved_at`, `gate_snapshot`).
**Why human:** CLI reads stdin interactively; cannot be verified without a live Supabase connection and the 5 `.joblib` files present.

#### 2. Circuit breaker triggers on real loss stream

**Test:** With a configured gate, call `record_daily_loss()` with cumulative amounts until the threshold is exceeded; verify `live_approval.json` is renamed to `.disabled` and subsequent `assert_ready()` raises CapitalGateError.
**Expected:** `data/live_approval.json.disabled` exists; `assert_ready()` raises `CapitalGateError` listing `GATE-03` and `GATE-04` failures.
**Why human:** Integration with a running `ShadowExecutionEngine` and real filesystem state outside of tmp_path is needed to confirm the full live path.

#### 3. Ablation script against real Supabase data

**Test:** With `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and trained models present, run `python scripts/run_ablation.py`.
**Expected:** Console table shows per-category model_edge, fallback_edge, delta, and PASS/FAIL columns; `data/ablation_report.json` is written with correct JSON schema.
**Why human:** Requires a live Supabase instance with data in `resolved_pm_markets`; cannot be verified in the test environment.

---

### Gaps Summary

No gaps. All 10 observable truths are verified. All 6 artifacts meet existence and substantive thresholds. All 7 key links are wired. All 6 requirement IDs are satisfied. No anti-patterns detected. The full 19-test suite passes (19/19) against the real implementations.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
