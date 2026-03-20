---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Live Execution
status: unknown
stopped_at: Completed 12-01-PLAN.md
last_updated: "2026-03-20T23:49:53.431Z"
progress:
  total_phases: 15
  completed_phases: 12
  total_plans: 61
  completed_plans: 60
---

# Project State: SharpEdge v2.0

**Last updated:** 2026-03-18
**Updated by:** execute-phase agent

---

## Project Reference

**Core value:** Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

**Current focus:** Phase 12 — live-kalshi-execution

---

## Current Position

Phase: 12 (live-kalshi-execution) — EXECUTING
Plan: 2 of 2

## Phase Status (v2.0)

| Phase | Goal | Status |
|-------|------|--------|
| 10 — Training Pipeline Validation | Per-category .joblib artifacts validated against live APIs | Complete (3/3 plans done) |
| 11 — Shadow Execution Engine | execution_engine.py + ShadowLedger with exposure limits | In progress (2/3 plans done) |
| 12 — Live Kalshi Execution | CLOB order submission + fill/cancel tracking in SettlementLedger | Not started |
| 13 — Ablation Validation & Capital Gate | Ablation report + 4-condition capital gate before live orders flow | Not started |
| 14 — Dashboard Execution Pages | Execution status + paper-trading summary in web dashboard | Not started |

---

## Accumulated Context

### Key Decisions (v1.0 carry-forward affecting v2.0)

- Phase 9 complete — PMResolutionPredictor, PMFeatureAssembler, download/process/train scripts all exist as stubs; Phase 10 runs them against live APIs
- SettlementLedger exists from Phase 6 (SETTLE-01) — Phase 12 extends it with fill/cancel tracking
- ExposureBook from Phase 6 (RISK-01) — Phase 11 uses it for per-market/per-day limit enforcement
- Polymarket live execution deferred to v2.1 — execution engine targets Kalshi CLOB only in v2.0

### Phase 10 Plan 01 Decisions

- Single `resolved_pm_markets` table with `source` column + UNIQUE(market_id, source) idempotency key — not separate per-platform tables
- `resolved_yes` as INTEGER NOT NULL (0 or 1) to match both Kalshi result=="yes" normalization and Polymarket's native field
- Wave 0 tests written as regular failing tests (not xfail) so CI fails loudly until Plans 02/03 implementations land

### Phase 10 Plan 02 Decisions

- Kalshi preflight implemented as `await client.get_markets(limit=1)` inside the async function — avoids event-loop nesting that a synchronous wrapper would cause
- `process_pm_historical.py` calls `sharpedge_db.client.get_supabase_client()` via module attribute access so Wave 0 test mock at `sharpedge_db.client.get_supabase_client` takes effect correctly
- Offline/parquet path preserved in both scripts — zero test file changes required

### Phase 10 Plan 03 Decisions

- `calibration_score` added to training report via `brier_score_loss` computed on OOF arrays already produced by `_run_walk_forward()` — no additional data pass needed
- Guard condition `len(oof_probs) == len(oof_actuals)` and try/except prevent ValueError on edge cases
- `quality_below_minimum` skip entries include `calibration_score: None` to maintain consistent JSON schema
- `scripts/__init__.py` added to make scripts/ importable as Python package for unit tests

### Phase 11 Plan 01 Decisions

- 3 stub-contract tests intentionally pass (instantiation, field access, UTC guard) — UTC guard IS fully implemented in stub by design; 7 tests fail on NotImplementedError covering actual engine logic
- Tests written in final GREEN assertion form so Plan 02 implementation requires zero test changes
- `test_day_stake_resets_at_midnight` patches `sharpedge_venue_adapters.execution_engine.datetime` so Plan 02 can use `datetime.now()` internally without test file modifications

### Phase 11 Plan 02 Decisions

- `process_intent` checks market guard before day guard — reject-before-write enforced for both (EXEC-04)
- `DayExposureGuard._maybe_reset` compares UTC date strings — matches CircuitBreakerState pattern in risk_agent
- `from_env()` classmethod with fallback defaults means shadow mode works with zero env configuration (EXEC-01)
- Stale hardcoded date `2026-03-18` in `test_day_stake_resets_at_midnight` updated to `2099-01-01` — Rule 1 auto-fix; date had passed by test run time

### Phase 15 Plan 01 Decisions

- ARB-02 RED uses try/except import guard with `_SHADOW_EXECUTE_AVAILABLE` flag and explicit `pytest.fail()` so test counts as FAILED (not ERROR) — keeps the 8 FAILED count accurate
- `test_staleness_guard_uninit` fails via AssertionError on missing `staleness_threshold_s` attribute — tests the ARB-03 constructor contract directly without needing a running event loop
- `@pytest.mark.asyncio` used per-test rather than `asyncio_mode=auto` globally to avoid unintended side effects on other packages in the workspace

### Phase 15 Plan 02 Decisions

- Scanner calls `get_orderbook()` directly on `_poly_client` in `_check_pair()` (not via `get_no_token_best_ask()`) so test mocks on `get_orderbook` propagate correctly through AsyncMock objects — `get_no_token_best_ask()` added to PolymarketClient for external callers
- `test_staleness_guard_uninit` RED-phase `pytest.raises(AssertionError)` wrapper replaced with direct positive assertions (Rule 1 auto-fix) — the wrapper prevented GREEN pass since `hasattr` returns True after implementation
- `pair.poly_no_ask` persisted when CLOB ask found; left at `0.0` on empty orderbook (no persistence) — matches `test_no_token_fallback` assertion that `poly_no_ask == 0.0` after empty asks response

### Phase 15 Plan 03 Decisions

- NO token extracted by `outcome.lower() == "no"` filter in `discover_and_wire()` — never by index — avoids breakage when outcome list order varies
- `self._poly_client` assigned after `asyncio.gather()` fetch so ARB-04 CLOB fallback in `_check_pair()` works for pairs registered via `discover_and_wire()`
- Live Polymarket EIP-712 signing raises `NotImplementedError` in `PolymarketCLOBOrderClient` — deferred to POLY-EXEC-01 (v3); shadow mode is the v2.0 production path
- `shadow_execute_arb()` reads `leg.get("ticker") or leg.get("token_id") or opp.canonical_id` so unit test mocks (which omit explicit market ids) still pass while production callers embed real ids in leg dicts

### Phase 12 Plan 01 Decisions

- All process_intent test calls use `await` uniformly (even shadow mode) — Plan 02 makes process_intent always async; this ensures zero test file changes post-implementation
- RED test failures are `TypeError` (unexpected kwargs `kalshi_client`, `settlement_ledger`, `poll_interval_seconds`), not `ImportError` — confirms all imports from sharpedge_feeds and sharpedge_venue_adapters resolve correctly
- `get_order(order_id)` follows get_market() pattern exactly: `_auth_headers("GET", path)` + `_parse_order(data["order"])` — returns None on 404, raises on other HTTP errors
- `make_mock_client(status)` fixture pattern pre-wires `create_order.return_value=KalshiOrder(status="resting")` and `get_order.return_value=KalshiOrder(status=param)` for clean isolated test setup

### Todos

- [ ] Verify live Kalshi CLOB order submission credentials before Phase 12 starts
- [x] Confirm .joblib artifact directory convention before Phase 10 starts — confirmed: data/models/pm/{category}.joblib

### Blockers

None.

---

## Session Continuity

**Last session:** 2026-03-20T23:49:53.428Z
**Stopped at:** Completed 12-01-PLAN.md
**Resume file:** None

---
*State initialized: 2026-03-13 by roadmapper*
*Updated: 2026-03-15 — v2.0 milestone roadmap created; position reset to Phase 10*
