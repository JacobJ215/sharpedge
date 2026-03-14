---
phase: 02-agent-architecture
plan: 01
subsystem: agent-pipeline
tags: [langgraph, tdd, scaffolding, wave-0]
dependency_graph:
  requires: []
  provides: [sharpedge-agent-pipeline package, RED test stubs for AGENT-01 through AGENT-05]
  affects: [apps/bot, Wave 1 implementation]
tech_stack:
  added: [langgraph>=1.1.0, langchain-openai>=0.3.0, langgraph-checkpoint-postgres>=3.0.0, tiktoken>=0.12.0]
  patterns: [TDD red-green cycle, uv workspace package, pytest.mark.xfail strict]
key_files:
  created:
    - packages/agent_pipeline/pyproject.toml
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/__init__.py
    - tests/unit/agent_pipeline/__init__.py
    - tests/unit/agent_pipeline/test_graph.py
    - tests/unit/agent_pipeline/test_state.py
    - tests/unit/agent_pipeline/test_validate_setup.py
    - tests/unit/agent_pipeline/test_copilot.py
    - tests/unit/agent_pipeline/test_copilot_tools.py
    - tests/unit/agent_pipeline/test_session.py
    - tests/unit/agent_pipeline/test_alpha_ranker.py
  modified:
    - apps/bot/pyproject.toml
decisions:
  - uv sync --all-packages required to install workspace packages into root venv (standard uv behavior, not a deviation)
  - test_state.py passes (state.py partially pre-existed from a prior session) — overall suite still exits non-zero
metrics:
  duration: ~8 minutes
  completed: "2026-03-14"
  tasks_completed: 2
  files_created: 10
  files_modified: 1
---

# Phase 2 Plan 01: Agent Pipeline Scaffold + RED Test Stubs Summary

**One-liner:** LangGraph workspace package registered with pinned deps and 7 RED test stub files defining the acceptance contract for AGENT-01 through AGENT-05.

## What Was Built

Wave 0 of Phase 2 establishes the TDD foundation before any implementation code exists.

### Task 1: Package Scaffold (commit 68574d4)

- Created `packages/agent_pipeline/pyproject.toml` declaring `sharpedge-agent-pipeline` with all required dependencies: `langgraph>=1.1.0,<2`, `langchain-openai>=0.3.0,<0.4`, `langgraph-checkpoint-postgres>=3.0.0,<4`, `tiktoken>=0.12.0,<1`, plus all 5 internal workspace packages
- Created `packages/agent_pipeline/src/sharpedge_agent_pipeline/__init__.py` (docstring stub only — no imports)
- Updated `apps/bot/pyproject.toml` to depend on `sharpedge-agent-pipeline` with `workspace = true` source
- Root `pyproject.toml` unchanged — `members = "packages/*"` already covers the new package
- `uv sync --all-packages` confirms package resolves and `find_spec('sharpedge_agent_pipeline')` returns a ModuleSpec

### Task 2: RED Test Stubs (commit e1f1c30)

7 test stub files created in `tests/unit/agent_pipeline/`, each importing not-yet-implemented modules:

| File | Requirements | RED mechanism |
|------|--------------|---------------|
| test_graph.py | AGENT-01, AGENT-02 | ImportError: `nodes.validate_setup` missing |
| test_state.py | AGENT-01 | Passes (state.py pre-existed) |
| test_validate_setup.py | AGENT-02 | ImportError: `nodes.validate_setup` missing |
| test_copilot.py | AGENT-03 | ImportError: `copilot` module missing |
| test_copilot_tools.py | AGENT-04 | ImportError: `copilot` module missing |
| test_session.py | AGENT-04 | ImportError: `copilot.session` missing |
| test_alpha_ranker.py | AGENT-05 | ImportError: `alerts` module missing |

`uv run pytest tests/unit/agent_pipeline/ -q` exits with code 2 (6 collection errors = RED state confirmed).

## Verification Results

1. `find_spec('sharpedge_agent_pipeline')` — ModuleSpec (not None) ✓
2. `pytest tests/unit/agent_pipeline/` exits non-zero (exit code 2) ✓
3. `pyproject.toml | grep langgraph` — `langgraph>=1.1.0,<2` ✓
4. `apps/bot/pyproject.toml | grep sharpedge-agent-pipeline` — match ✓

## Deviations from Plan

**1. [Rule 1 - Bug] uv sync vs uv sync --all-packages**
- **Found during:** Task 1 verification
- **Issue:** `uv run python -c "import importlib.util; print(importlib.util.find_spec('sharpedge_agent_pipeline'))"` returned None when run from root project context with `uv sync --no-install-project`. All workspace packages behave identically — the root env does not install workspace members by default.
- **Fix:** Used `uv sync --all-packages` to install all workspace members into the root venv. This is standard uv workspace behavior, not a package authoring defect.
- **Files modified:** None (runtime operation only)
- **Commit:** N/A (operational deviation, no code change)

**2. [Observation] test_state.py passes collection (not a failure)**
- **Found during:** Task 2 verification
- **Issue:** `state.py` and `graph.py` were partially pre-created in the agent_pipeline package (likely from a prior planning session). test_state.py imports succeed and 3 tests pass.
- **Fix:** No fix needed — test_state.py is a valid GREEN test for the pre-existing state.py. The overall suite still exits non-zero due to 6 other files failing. This is consistent with the plan's done criteria.

## Self-Check: PASSED

All created files verified present. Both task commits (68574d4, e1f1c30) confirmed in git log.
