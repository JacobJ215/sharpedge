---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-14T00:31:48.038Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 33
---

# Project State: SharpEdge v2

**Last updated:** 2026-03-14
**Updated by:** executor (01-01-PLAN.md)

---

## Project Reference

**Core value:** Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

**Current focus:** Phase 1 — Quant Engine (pure Python modules, no framework dependency)

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | 1 — Quant Engine |
| Plan | 01 — Technical Debt Clearance (complete) |
| Status | In progress |
| Blocking issues | None |

**Progress:**

[███░░░░░░░] 33%
Phase 1 [          ] 0%
Phase 2 [          ] 0%
Phase 3 [          ] 0%
Phase 4 [          ] 0%
Phase 5 [          ] 0%
```

---

## Phase Status

| Phase | Goal | Status |
|-------|------|--------|
| 1 — Quant Engine | Correct, thread-safe quant primitives (no framework dependency) | In progress (1 plan done) |
| 2 — Agent Architecture | LangGraph 9-node StateGraph + BettingCopilot | Not started |
| 3 — Prediction Market Intelligence | PM edge scanner + cross-market correlation | Not started |
| 4 — API Layer + Front-Ends | FastAPI + Next.js web + Expo mobile (RLS first) | Not started |
| 5 — Model Pipeline Upgrade | 5-model ensemble + rolling Platt calibration + walk-forward | Not started |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| BacktestEngine DB stubs use in-memory dict for Phase 1 | Supabase schema unknown; dict implementation unblocks WalkForwardBacktester |
| roc_auc_score from sklearn replaces O(n^2) concordant-pair loop | Correctness + performance; manual implementation had vectorized expression bug |
| visualizations.py split into 4-module sub-package | 896 lines exceeds 500-line limit; backward-compat re-exports preserve callers |
| Flutter mobile app excluded from Python uv workspace | No pyproject.toml in apps/mobile; different tech stack entirely |
| LangGraph replaces OpenAI Agents SDK | Graph-based routing, parallel specialist nodes, persistent checkpointing |
| Composite alpha score as primary ranking metric | Prevents optimizing EV alone; includes regime/survival/calibration factors |
| Monte Carlo as primary risk communication | "3.2% ruin over 500 bets" is more communicable than abstract Kelly fractions |
| HMM starts at 3–4 states, not 7 | Sports data is sparse; 7-state HMM requires 2000+ labeled observations |
| Keep existing ev_calculator.py — extend, not replace | Already has excellent Bayesian EV implementation |
| Supabase RLS before any user-scoped API route | Security non-negotiable; enable in Phase 4 before route wiring |

### Known Issues

- `tools.py` (576 lines) exceeds 500-line limit — needs splitting with backward-compatible re-exports (deferred to later plan)
- Monte Carlo uses `np.random.seed(42)` global RNG — not thread-safe for concurrent FastAPI requests (addressed in QUANT-02)
- 7 RED test stubs awaiting implementation: alpha, monte_carlo, regime, key_numbers, walk_forward, clv

### Resolved Issues (Plan 01-01)

- ~~`datetime.utcnow()` timezone-naive~~ FIXED: all 7 occurrences replaced
- ~~`visualizations.py` 896 lines~~ FIXED: split into 4-module sub-package
- ~~`backtesting.py` 4 stub methods~~ FIXED: in-memory dict implementations
- ~~Zero test infrastructure~~ FIXED: pytest setup + 7 test stub files

### Research Flags (Resolve Before Building)

- HMM training data audit: count seasons of betting data in Supabase per sport before committing to 3-state vs 7-state
- Version verification: LangGraph 0.2.x minor version, langgraph-checkpoint-postgres exact package name, Expo SDK current version — all marked [VERIFY] in STACK.md
- Kalshi/Polymarket API liquidity fields: verify bid-ask spread and open interest are available before Phase 3 design
- LangGraph `.astream_events()` event type names and `recursion_limit` parameter — verify against current docs before Phase 2

### Todos

- [ ] Resolve all [VERIFY] version tags in STACK.md before Phase 1 starts
- [ ] Audit Supabase for how many seasons of betting data exist per sport (HMM state count decision)
- [ ] Scan codebase for all `datetime.utcnow()` instances before Phase 1 plan is written
- [ ] Identify all callers of visualizations.py and tools.py before splitting (backward-compat re-export plan)

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete | 0/5 |
| Requirements delivered | 0/35 |
| Plans complete | 1/? |

---

## Session Continuity

**To resume:** Read ROADMAP.md for phase goals and success criteria. Read this file for current position and decisions.

**Stopped at:** Completed 01-01-PLAN.md (technical debt clearance)
**Next action:** Execute 01-02-PLAN.md (Wave 1 quant modules: alpha, monte_carlo, regime, walk_forward, clv, key_numbers)

---
*State initialized: 2026-03-13 by roadmapper*
