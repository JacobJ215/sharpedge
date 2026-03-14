---
phase: 02-agent-architecture
plan: 02
subsystem: agent-pipeline
tags: [langgraph, stategraph, tdd, parallel-nodes, llm-evaluator, wave-1]
dependency_graph:
  requires: [02-01 (sharpedge-agent-pipeline scaffold + RED stubs)]
  provides:
    - BettingAnalysisState TypedDict (parallel-safe with operator.add reducer)
    - build_analysis_graph() compiled 9-node StateGraph
    - validate_setup LLM node with SetupEvalResult structured output
    - 9 node implementations (route_intent, fetch_context, detect_regime, run_models, calculate_ev, validate_setup, compose_alpha, size_position, generate_report)
    - error_handler node
  affects: [02-03 (BettingCopilot uses ANALYSIS_GRAPH), 02-04 (alpha_ranker uses BettingAlpha)]
tech_stack:
  added:
    - langgraph StateGraph parallel fan-out pattern
    - ChatOpenAI.with_structured_output(SetupEvalResult)
    - Annotated[list[str], operator.add] reducer for parallel-safe state
  patterns:
    - LangGraph 1.1.x: recursion_limit in ainvoke config, not compile()
    - TDD red-green: tests written RED first, implementation brings GREEN
    - Parallel fan-out: 3 add_edge calls from fetch_context to independent nodes
    - Loop guard: retry_count >= 2 forces compose_alpha regardless of WARN verdict
key_files:
  created:
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/state.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/__init__.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/route_intent.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/fetch_context.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/detect_regime.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/run_models.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/calculate_ev.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/validate_setup.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/size_position.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/generate_report.py
  modified: []
decisions:
  - Node implementations call module-level functions (classify_regime, simulate_bankroll, compose_alpha, calculate_ev) instead of class instances — the Phase 1 APIs are functional, not OO; the plan's <interfaces> section described a wrapper pattern that was not implemented in Phase 1
  - OddsClient requires api_key at construction time — fetch_context reads ODDS_API_KEY from env; falls back to empty context if missing (offline-safe)
  - BettingAlpha.alpha_score field is actually named alpha (not alpha_score) — node implementations use the correct field name from the actual dataclass
  - quality_warnings key not included in total=False TypedDict to avoid mypy issues with Annotated reducers — state is total=False so all keys are Optional by default
metrics:
  duration: ~25 minutes
  completed: "2026-03-14"
  tasks_completed: 2
  files_created: 12
  files_modified: 0
---

# Phase 2 Plan 02: BettingAnalysisState + 9-Node LangGraph Graph Summary

**One-liner:** LangGraph 9-node StateGraph with Annotated parallel-safe state, ChatOpenAI structured-output evaluator, and retry-capped conditional routing — all 16 unit tests GREEN.

## What Was Built

Wave 1 of Phase 2 implements the complete analysis pipeline graph: state schema, graph topology, and all 9 node functions.

### Task 1: BettingAnalysisState + Graph Wiring (TDD)

**RED:** test_state.py and test_graph.py written with ImportError (no implementation yet).

**GREEN:** Implementation brings all tests to pass.

**state.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/state.py`):
- `BettingAnalysisState` TypedDict (total=False) with 16 typed keys
- `quality_warnings: Annotated[list[str], operator.add]` — parallel nodes can safely append without clobbering
- Forward references via `from __future__ import annotations`
- Imports `RegimeClassification`, `BettingAlpha`, `MonteCarloResult` from Phase 1 packages

**graph.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py`):
- `build_analysis_graph()` creates a `StateGraph(BettingAnalysisState)`, adds 9 named nodes + error_handler, wires all edges
- Parallel fan-out: 3 explicit `add_edge` calls from `fetch_context` to `detect_regime`, `run_models`, `calculate_ev`
- Fan-in: all 3 parallel nodes connect to `validate_setup`
- `add_conditional_edges("validate_setup", _route_after_validation, {...})` with 3-way routing
- `_route_after_validation`: PASS → compose_alpha, WARN+retry<2 → fetch_context, WARN+retry≥2 → compose_alpha (loop guard), REJECT → generate_report
- Compiled without `recursion_limit` (passed at `ainvoke()` call site instead)
- `ANALYSIS_GRAPH = build_analysis_graph()` module-level singleton

**nodes/__init__.py**: Exports all 10 callables (9 nodes + error_handler).

### Task 2: 9 Node Implementations (TDD)

**RED:** test_validate_setup.py already exists from 02-01 with ImportError stubs.

**GREEN:** All 9 node files implemented.

| Node | File | Key behavior |
|------|------|-------------|
| route_intent | route_intent.py | Keyword heuristic: "?" → copilot, "scan" → scan, else analyze |
| fetch_context | fetch_context.py | OddsClient.get_odds() once; offline fallback with neutral defaults |
| detect_regime | detect_regime.py | classify_regime(**regime_inputs); quality_warning if confidence < 0.5 |
| run_models | run_models.py | calculate_ev(model_prob, odds); optional analyze_zone() for spreads |
| calculate_ev | calculate_ev.py | simulate_bankroll(2000 paths, 500 bets); quality_warning if ruin > 5% |
| validate_setup | validate_setup.py | ChatOpenAI(gpt-4o-mini).with_structured_output(SetupEvalResult); WARN increments retry_count |
| compose_alpha | compose_alpha.py | compose_alpha(edge_score, regime_scale, survival_prob, 1.0) |
| size_position | size_position.py | Half-Kelly formula clamped to [0.005, 0.25] |
| generate_report | generate_report.py | Discord-embed string with all signals; appends quality_warnings |

## Verification Results

1. `uv run pytest tests/unit/agent_pipeline/test_graph.py tests/unit/agent_pipeline/test_state.py tests/unit/agent_pipeline/test_validate_setup.py -x -q` — **16 passed** ✓
2. `build_analysis_graph()` nodes: `['__start__', 'route_intent', 'fetch_context', 'detect_regime', 'run_models', 'calculate_ev', 'validate_setup', 'compose_alpha', 'size_position', 'generate_report', 'error_handler']` ✓
3. All node files: max 107 lines (validate_setup.py) — none exceed 499 lines ✓
4. `recursion_limit` appears only in comments in graph.py, NOT inside `compile()` call ✓

## Deviations from Plan

### Automatic Adaptations (No Plan Deviation)

**1. [Rule 1 - Bug] Phase 1 APIs are functional, not class-based**
- **Found during:** Task 2 — implementing detect_regime, run_models, calculate_ev, compose_alpha nodes
- **Issue:** Plan's `<interfaces>` section described `RegimeDetector().classify_regime()`, `MonteCarloSimulator().simulate()`, `AlphaComposer().compose_alpha()`, `EVCalculator().calculate()` as class instances. The actual Phase 1 code has module-level functions: `classify_regime()`, `simulate_bankroll()`, `compose_alpha()`, `calculate_ev()`.
- **Fix:** Node implementations call the actual module-level functions directly. The behavior is identical — no wrapper classes needed.
- **Files modified:** All 4 affected node files (detect_regime.py, run_models.py, calculate_ev.py, compose_alpha.py)
- **Commit:** 2b9957a

**2. [Rule 2 - Missing Input Validation] OddsClient requires api_key**
- **Found during:** Task 2 — implementing fetch_context.py
- **Issue:** `OddsClient.__init__` requires `api_key: str` parameter. Plan didn't specify where to get it.
- **Fix:** fetch_context reads `ODDS_API_KEY` from environment via `os.environ.get("ODDS_API_KEY", "")`. Falls back to offline context dict if OddsClient fails (network not available in tests).
- **Files modified:** fetch_context.py
- **Commit:** 2b9957a

**3. [Rule 1 - Bug] BettingAlpha field name is alpha, not alpha_score**
- **Found during:** Task 2 — implementing generate_report.py and compose_alpha.py
- **Issue:** Plan's generate_report behavior says "alpha badge" from `BettingAlpha.alpha_score` and `BettingAlpha.badge`. Actual dataclass fields are `BettingAlpha.alpha` (float) and `BettingAlpha.quality_badge` (str).
- **Fix:** Used the correct field names from the actual dataclass definition.
- **Files modified:** generate_report.py, compose_alpha.py
- **Commit:** 2b9957a

## Self-Check

Files created:

- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/state.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/graph.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/__init__.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/validate_setup.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/detect_regime.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/run_models.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/calculate_ev.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/route_intent.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/fetch_context.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/compose_alpha.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/size_position.py
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/nodes/generate_report.py

Commit 2b9957a confirmed in git log.

## Self-Check: PASSED
