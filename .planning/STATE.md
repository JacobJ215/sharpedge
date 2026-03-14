---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 03-prediction-market-intelligence 03-03-PLAN.md
last_updated: "2026-03-14T04:37:58.455Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# Project State: SharpEdge v2

**Last updated:** 2026-03-14
**Updated by:** executor (03-03-PLAN.md)

---

## Project Reference

**Core value:** Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

**Current focus:** Phase 4 — API Layer + Front-Ends (FastAPI + Next.js web + Expo mobile)

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | 4 — API Layer + Front-Ends |
| Plan | 00 — Not started |
| Status | Phase 3 Complete |
| Blocking issues | None |

**Progress:**

[██████████] 100%
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
| 1 — Quant Engine | Correct, thread-safe quant primitives (no framework dependency) | Complete (3 plans done) |
| 2 — Agent Architecture | LangGraph 9-node StateGraph + BettingCopilot | Complete (4 of 4 plans done) |
| 3 — Prediction Market Intelligence | PM edge scanner + cross-market correlation | Complete (3 of 3 plans done) |
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
| uv sync --all-packages required to install workspace packages into root venv | Standard uv workspace behavior; root venv doesn't auto-install workspace members |
| Phase 1 APIs are functional (module-level functions), not class-based | Plan referenced EVCalculator(), RegimeDetector(), etc. as classes — actual Phase 1 code uses classify_regime(), simulate_bankroll(), compose_alpha() module-level functions |
| OddsClient reads ODDS_API_KEY from env with offline fallback | api_key required at construction; nodes must not fail in offline/test environments |
| StructuredTool from @tool is not directly callable via (**kwargs) | Use .invoke(dict) — BaseTool removed __call__; tests updated accordingly |
| COPILOT_GRAPH singleton is None when OPENAI_API_KEY absent | Lazy build via _try_build_graph(); callers use build_copilot_graph() in production |
| trim_conversation accepts plain dicts (not BaseMessage) | MessagesState internal format and test compatibility; converts to BaseMessage indices for LLM call |
| rank_by_alpha accepts plain dicts and ValuePlay objects | isinstance branch: dict.get() for tests, getattr() for production ValuePlay objects |
| None-safe alpha sort fallback to 0.0 | Allows mixed None/float alpha_score lists without TypeError during sort |
| prediction_markets.py split into fees/types/arbitrage sub-package | 614 lines exceeds 500-line limit; backward-compat re-exports preserve callers; clear concern boundaries |
| RED stubs define PM-01/02/03/04 contracts before implementation | 19 failing tests (ImportError) lock interface contracts so Wave 1 won't drift |
| classify_pm_regime() uses price_variance parameter name (not price_variance_7d) | Tests are authoritative contracts in TDD; implementation matches test signature |
| scan_pm_edges() accepts active_bets/market_titles as no-op kwargs | Correlation logic deferred to Plan 03 (PM-04); interface forward-compatible without TypeError |
| compute_entity_correlation uses min-denominator formula | Single shared entity in short title yields > 0.5; matches partial-match test expectations |
| CorrelationWarning dataclass in pm_edge_scanner returns mixed list | scan_pm_edges returns list[PMEdge | CorrelationWarning] when active_bets supplied; satisfies PM-04 test contract |

### Known Issues

- `tools.py` (446 lines) is now within 500-line limit after PM stub replacement (was 576, reduced by replacing verbose stub)
- `value_scanner.py` (650+ lines) exceeds 500-line limit — full refactor deferred to Phase 4
- ~~PM edge scanner RED stubs~~ FIXED: pm_correlation.py implemented; scan_pm_edges full correlation logic implemented; copilot tool stub replaced

### Resolved Issues

- ~~`datetime.utcnow()` timezone-naive~~ FIXED: all 7 occurrences replaced
- ~~`visualizations.py` 896 lines~~ FIXED: split into 4-module sub-package
- ~~`backtesting.py` 4 stub methods~~ FIXED: in-memory dict implementations
- ~~Zero test infrastructure~~ FIXED: pytest setup + 7 test stub files
- ~~`monte_carlo.py` missing~~ FIXED: thread-safe np.random.default_rng, 2000 paths
- ~~`alpha.py` missing~~ FIXED: composite alpha with EDGE_SCORE_FLOOR, 4 badges
- ~~`regime.py` missing~~ FIXED: 4-state rule-based classifier with confidence
- ~~`key_numbers.py` zone detection missing~~ FIXED: ZoneAnalysis + analyze_zone()
- ~~`clv.py` missing~~ FIXED: calculate_clv() American odds CLV
- ~~`walk_forward.py` missing~~ FIXED: WindowResult, create_windows(), quality_badge_from_windows()
- ~~Alpha not wired into value_scanner~~ FIXED: enrich_with_alpha(), rank uses alpha_score

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
| Phase 02-agent-architecture P01 | 8 | 2 tasks | 11 files |
| Phase 02-agent-architecture P03 | 35 | 2 tasks | 4 files created + 4 modified |
| Phase 03-prediction-market-intelligence P01 | 265 | 2 tasks | 7 files |
| Phase 03-prediction-market-intelligence P02 | 10 | 2 tasks | 2 files |
| Phase 03-prediction-market-intelligence P03 | 15 | 2 tasks | 4 files |

## Session Continuity

**To resume:** Read ROADMAP.md for phase goals and success criteria. Read this file for current position and decisions.

**Stopped at:** Completed 03-prediction-market-intelligence 03-03-PLAN.md
**Next action:** Phase 4 — API Layer + Front-Ends (FastAPI + Next.js web + Expo mobile, RLS first)

---
*State initialized: 2026-03-13 by roadmapper*
