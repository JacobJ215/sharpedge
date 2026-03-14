---
phase: 02-agent-architecture
plan: 04
subsystem: agent-pipeline
tags: [alpha-ranking, value-alerts, discord, tdd, wave-3, agent-05]
dependency_graph:
  requires: [02-03 (BettingCopilot ReAct graph), 01-03 (enrich_with_alpha in sharpedge_analytics)]
  provides:
    - alerts/alpha_ranker.py: rank_by_alpha() — sorts ValuePlay list by alpha_score descending, None-safe
    - alerts/__init__.py: re-exports rank_by_alpha
    - value_scanner_job.py: alert dispatch now sorted by alpha_score, not ev_percentage
  affects: [Phase 3 PM intelligence (value play pipeline established)]
tech_stack:
  added:
    - sharpedge_agent_pipeline.alerts.alpha_ranker (new module, <30 lines)
  patterns:
    - None-safe sort via fallback: key=lambda p: val if val is not None else 0.0, reverse=True
    - Thin adapter module pattern: alpha_ranker.py has zero external dependencies beyond typing
    - Dict + object dual API: rank_by_alpha accepts both dicts and ValuePlay objects via getattr/dict.get
key_files:
  created:
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/__init__.py
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/alpha_ranker.py
  modified:
    - apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py (add 2 imports, replace sort, add assertion)
    - tests/unit/agent_pipeline/test_alpha_ranker.py (remove xfail markers, add 2 missing test cases)
decisions:
  - rank_by_alpha accepts both plain dicts and ValuePlay objects for test compatibility (tests use dicts, production uses ValuePlay)
  - None-safe fallback to 0.0 allows mixed lists without raising TypeError during sort
  - rank_value_plays import kept for backward compat (other callers may exist) but not used for alert sort
metrics:
  duration: ~10 minutes
  completed: "2026-03-13"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 2 Plan 04: Alpha-Ranked Alert Dispatch Summary

**One-liner:** Thin alpha_ranker module with rank_by_alpha() wired into value_scanner_job.py so Discord value play alerts arrive sorted by composite alpha score, completing AGENT-05 and all 57 unit tests GREEN.

## What Was Built

Wave 3 (final) of Phase 2 delivers the missing link between enrich_with_alpha() (Phase 1, Plan 3) and Discord alert dispatch. Value play alerts now surface in alpha score order rather than discovery order.

### Task 1: rank_by_alpha Implementation + value_scanner_job.py Update (TDD)

**alpha_ranker.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/alpha_ranker.py`, 27 lines):
- `rank_by_alpha(plays: list[Any]) -> list[Any]` — returns a new sorted list, never mutates input
- Sort key: `val if val is not None else 0.0` with `reverse=True` — None-alpha plays sort last
- Accepts both plain dicts (for tests) and ValuePlay objects (for production) via `isinstance(play, dict)` branch
- Zero external dependencies beyond `__future__` and `typing`

**alerts/__init__.py** (`packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/__init__.py`):
- Re-exports `rank_by_alpha` as public API for the alerts sub-package

**value_scanner_job.py edits** (targeted, 3 lines changed):
- Added import: `enrich_with_alpha` from `sharpedge_analytics`
- Added import: `rank_by_alpha` from `sharpedge_agent_pipeline.alerts.alpha_ranker`
- Replaced `ranked_plays = rank_value_plays(all_value_plays)` with:
  - `enriched = enrich_with_alpha(all_value_plays)`
  - `ranked_plays = rank_by_alpha(enriched)`
  - assertion: `assert all(p.alpha_score is not None for p in ranked_plays[:20] if ranked_plays)`
- `rank_value_plays` import retained for backward compat (not used in alert sort path)

**test_alpha_ranker.py updates:**
- Removed `xfail(strict=True)` markers from `test_rank_by_alpha_descending` and `test_none_alpha_last`
- Added `test_empty_list`: rank_by_alpha([]) returns []
- Added `test_does_not_mutate`: original list order unchanged after call

### Task 2: Full Unit Suite Regression Check (Auto-approved in auto mode)

- 57 unit tests passed, 0 failures, 1 warning (pre-existing RuntimeWarning in monte_carlo.py, out of scope)
- All Phase 2 tests GREEN: test_alpha_ranker, test_copilot, test_copilot_tools, test_session, plus Phase 1 analytics/models tests

## Verification Results

1. `uv run pytest tests/unit/agent_pipeline/test_alpha_ranker.py -x -q` — **4 passed** (GREEN)
2. `uv run pytest tests/ -q --ignore=tests/integration` — **57 passed, 0 failures**
3. `grep "rank_by_alpha" value_scanner_job.py` — match found (import + usage)
4. `grep "rank_value_plays" value_scanner_job.py` — import present, NOT in sort path
5. `from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha; print('ok')` — **ok**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] test_alpha_ranker.py missing test_empty_list and test_does_not_mutate**
- **Found during:** Task 1 — plan's behavior spec listed 4 required tests but test file only contained 2
- **Issue:** Two required test cases (test_empty_list, test_does_not_mutate) were absent
- **Fix:** Added both test cases to test_alpha_ranker.py
- **Files modified:** `tests/unit/agent_pipeline/test_alpha_ranker.py`
- **Commit:** 646e0ab

**2. [Rule 2 - Missing functionality] Test file had xfail markers instead of live assertions**
- **Found during:** Task 1 — existing tests marked `xfail(strict=True, reason="Wave 1 not yet implemented")`
- **Issue:** With xfail strict, passing tests would become XPASS failures (wrong outcome)
- **Fix:** Removed xfail markers so tests run as live assertions
- **Files modified:** `tests/unit/agent_pipeline/test_alpha_ranker.py`
- **Commit:** 646e0ab

## Self-Check

Files created:
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/__init__.py — FOUND
- [x] packages/agent_pipeline/src/sharpedge_agent_pipeline/alerts/alpha_ranker.py — FOUND
- [x] .planning/phases/02-agent-architecture/02-04-SUMMARY.md — FOUND

Files modified:
- [x] apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py — FOUND (rank_by_alpha present)
- [x] tests/unit/agent_pipeline/test_alpha_ranker.py — FOUND (4 tests, no xfail)

Commits:
- [x] 646e0ab — feat(02-04): implement rank_by_alpha and wire alpha-ranked alert dispatch

## Self-Check: PASSED
