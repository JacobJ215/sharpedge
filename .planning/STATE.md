# Project State: SharpEdge v2

**Last updated:** 2026-03-13
**Updated by:** roadmapper

---

## Project Reference

**Core value:** Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

**Current focus:** Phase 1 — Quant Engine (pure Python modules, no framework dependency)

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | 1 — Quant Engine |
| Plan | None started |
| Status | Not started |
| Blocking issues | None |

**Progress:**

```
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
| 1 — Quant Engine | Correct, thread-safe quant primitives (no framework dependency) | Not started |
| 2 — Agent Architecture | LangGraph 9-node StateGraph + BettingCopilot | Not started |
| 3 — Prediction Market Intelligence | PM edge scanner + cross-market correlation | Not started |
| 4 — API Layer + Front-Ends | FastAPI + Next.js web + Expo mobile (RLS first) | Not started |
| 5 — Model Pipeline Upgrade | 5-model ensemble + rolling Platt calibration + walk-forward | Not started |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph replaces OpenAI Agents SDK | Graph-based routing, parallel specialist nodes, persistent checkpointing |
| Composite alpha score as primary ranking metric | Prevents optimizing EV alone; includes regime/survival/calibration factors |
| Monte Carlo as primary risk communication | "3.2% ruin over 500 bets" is more communicable than abstract Kelly fractions |
| HMM starts at 3–4 states, not 7 | Sports data is sparse; 7-state HMM requires 2000+ labeled observations |
| Keep existing ev_calculator.py — extend, not replace | Already has excellent Bayesian EV implementation |
| Supabase RLS before any user-scoped API route | Security non-negotiable; enable in Phase 4 before route wiring |

### Known Issues (Pre-Phase 1)

- `datetime.utcnow()` used throughout packages/models/ — timezone-naive, must be fixed to `datetime.now(timezone.utc)`
- `visualizations.py` (896 lines) and `tools.py` (576 lines) exceed 500-line limit — need splitting with backward-compatible re-exports
- `backtesting.py` has 4 unimplemented stub methods — must be completed before walk-forward window logic
- Zero test coverage across all packages
- Monte Carlo uses `np.random.seed(42)` global RNG — not thread-safe for concurrent FastAPI requests

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
| Plans complete | 0/? |

---

## Session Continuity

**To resume:** Read ROADMAP.md for phase goals and success criteria. Read this file for current position and decisions. Run `/gsd:plan-phase 1` to begin Phase 1 planning.

**Next action:** `/gsd:plan-phase 1`

---
*State initialized: 2026-03-13 by roadmapper*
