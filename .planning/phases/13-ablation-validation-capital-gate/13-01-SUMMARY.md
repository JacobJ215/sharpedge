---
phase: 13-ablation-validation-capital-gate
plan: "01"
subsystem: venue-adapters/capital-gate
tags: [tdd, red-phase, capital-gate, ablation, wave-0]
dependency_graph:
  requires: []
  provides:
    - capital_gate.py stub (CapitalGate, CapitalGateError, GateStatus, GateCondition, CATEGORIES)
    - ablation.py stub (compute_ablation_report)
    - 19 RED test stubs locking interface contracts for Plan 02
  affects:
    - packages/venue_adapters/tests/test_capital_gate.py
    - packages/venue_adapters/tests/test_ablation.py
tech_stack:
  added: []
  patterns:
    - TDD Wave 0 RED phase (NotImplementedError stubs with GREEN-form assertions)
    - CircuitBreakerState daily reset pattern (for GATE-04 test)
    - supabase create_client mock via unittest.mock.patch
key_files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/ablation.py
    - packages/venue_adapters/tests/test_capital_gate.py
    - packages/venue_adapters/tests/test_ablation.py
  modified: []
decisions:
  - "create_client imported via try/except in capital_gate.py stub so patch target sharpedge_venue_adapters.capital_gate.create_client resolves correctly for GATE-02 tests"
  - "assert_ready() implemented as real logic in stub (calls check(), raises on failures) — only check(), record_daily_loss(), from_env() raise NotImplementedError"
  - "model_prob field added to resolved_markets dicts in test_ablation to make delta computation intent clear in GREEN assertions"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-21"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
requirements_satisfied:
  - GATE-01
  - GATE-02
  - GATE-03
  - GATE-04
  - ABLATE-01
  - ABLATE-02
---

# Phase 13 Plan 01: CapitalGate RED Test Stubs Summary

**One-liner:** TDD Wave 0 — 19 RED test stubs locking CapitalGate + ablation interface contracts before Plan 02 implementation.

---

## What Was Built

Created four new files establishing the complete interface contract for the Phase 13 capital gate and ablation subsystems:

**`capital_gate.py`** — stub module exporting `CapitalGate`, `CapitalGateError`, `GateStatus`, `GateCondition`, and `CATEGORIES`. The `CapitalGate.__init__` stores all params (real), `assert_ready()` calls `check()` and raises `CapitalGateError` on failures (real), but `check()`, `record_daily_loss()`, and `from_env()` all `raise NotImplementedError`. Includes a conditional `create_client` import from supabase so the GATE-02 test mock patch target resolves correctly.

**`ablation.py`** — stub exporting `compute_ablation_report(resolved_markets, models_dir, fee_rate, threshold_pct)` which raises `NotImplementedError`.

**`test_capital_gate.py`** — 16 RED tests covering GATE-01 (model artifacts), GATE-02 (paper period), GATE-03 (manual approval), GATE-04 (daily loss circuit breaker), and the `assert_ready()` contract. Written in GREEN assertion form — Plan 02 implementation requires zero test changes.

**`test_ablation.py`** — 3 RED tests covering ABLATE-01 (per-category delta computation) and ABLATE-02 (pass/fail threshold logic). Written in GREEN assertion form.

---

## Verification Results

```
19 failed, 0 passed, 0 errors
```

All failures are `NotImplementedError`, not `ImportError`. Confirms interface is importable and contracts are locked.

---

## Deviations from Plan

### Auto-fixed Issues

None.

### Deliberate Micro-decisions

**1. create_client conditional import in stub**
- Found during: Task 1 (GATE-02 test design)
- Issue: Tests patch `sharpedge_venue_adapters.capital_gate.create_client`, but if the stub never imports `create_client`, the patch target would not exist at Plan 02 implementation time.
- Fix: Added `try/except ImportError` block importing `create_client` from supabase in the stub so the namespace is established.
- Files modified: `capital_gate.py`

**2. assert_ready() implemented in stub**
- Found during: Task 1 (assert_ready() behavior design)
- Issue: `assert_ready()` is specified to call `check()` and raise with all failures — this logic requires no new state, only delegation to `check()`. Implementing it in the stub means `test_assert_ready_raises_capital_gate_error` and `test_assert_ready_collects_all_failures` correctly fail because `check()` raises `NotImplementedError`, not because `assert_ready()` itself is a stub.
- Fix: Implemented `assert_ready()` as real delegation logic; kept `check()`, `record_daily_loss()`, `from_env()` as NotImplementedError stubs.
- Files modified: `capital_gate.py`

---

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `capital_gate.py` exists | FOUND |
| `ablation.py` exists | FOUND |
| `test_capital_gate.py` exists | FOUND |
| `test_ablation.py` exists | FOUND |
| Commit 2b3499e exists | FOUND |
| Commit fe9c0c4 exists | FOUND |
