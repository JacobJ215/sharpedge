---
phase: 2
slug: agent-architecture
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 + pytest-mock 3.14 |
| **Config file** | `pyproject.toml` (root — already configured) |
| **Quick run command** | `uv run pytest tests/unit/agent_pipeline/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q --ignore=tests/integration` |
| **Estimated runtime** | ~12 seconds (unit only, LLM mocked) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/agent_pipeline/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q --ignore=tests/integration`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| pkg-setup | 01 | 0 | AGENT-01 | unit | `uv run pytest tests/unit/agent_pipeline/ -x -q` | ❌ W0 | ⬜ pending |
| state-schema | 01 | 1 | AGENT-01 | unit | `uv run pytest tests/unit/agent_pipeline/test_state.py -x -q` | ❌ W0 | ⬜ pending |
| graph-wiring | 01 | 1 | AGENT-01 | unit | `uv run pytest tests/unit/agent_pipeline/test_graph.py -x -q` | ❌ W0 | ⬜ pending |
| parallel-nodes | 01 | 1 | AGENT-01 | unit | `uv run pytest tests/unit/agent_pipeline/test_graph.py::test_parallel_writes_no_collision -x -q` | ❌ W0 | ⬜ pending |
| validate-setup | 02 | 2 | AGENT-02 | unit | `uv run pytest tests/unit/agent_pipeline/test_validate_setup.py -x -q` | ❌ W0 | ⬜ pending |
| warn-retry-cap | 02 | 2 | AGENT-02 | unit | `uv run pytest tests/unit/agent_pipeline/test_graph.py::test_warn_retry_cap -x -q` | ❌ W0 | ⬜ pending |
| copilot-agent | 02 | 2 | AGENT-03 | unit | `uv run pytest tests/unit/agent_pipeline/test_copilot.py -x -q` | ❌ W0 | ⬜ pending |
| copilot-tools | 02 | 2 | AGENT-04 | unit | `uv run pytest tests/unit/agent_pipeline/test_copilot_tools.py -x -q` | ❌ W0 | ⬜ pending |
| trim-messages | 02 | 2 | AGENT-04 | unit | `uv run pytest tests/unit/agent_pipeline/test_session.py -x -q` | ❌ W0 | ⬜ pending |
| alpha-ranker | 02 | 3 | AGENT-05 | unit | `uv run pytest tests/unit/agent_pipeline/test_alpha_ranker.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/agent_pipeline/` — new package directory + `pyproject.toml`
- [ ] `packages/agent_pipeline/src/sharpedge_agent_pipeline/__init__.py`
- [ ] `tests/unit/agent_pipeline/__init__.py`
- [ ] `tests/unit/agent_pipeline/test_state.py` — stubs for AGENT-01 parallel state safety
- [ ] `tests/unit/agent_pipeline/test_graph.py` — stubs for AGENT-01 graph routing + AGENT-02 retry cap
- [ ] `tests/unit/agent_pipeline/test_validate_setup.py` — stubs for AGENT-02 (mocked LLM)
- [ ] `tests/unit/agent_pipeline/test_copilot.py` — stubs for AGENT-03 (mocked tools)
- [ ] `tests/unit/agent_pipeline/test_copilot_tools.py` — stubs for AGENT-04 (mocked DB)
- [ ] `tests/unit/agent_pipeline/test_session.py` — stubs for AGENT-04 trim_messages
- [ ] `tests/unit/agent_pipeline/test_alpha_ranker.py` — stubs for AGENT-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full graph ainvoke end-to-end with real Odds API | AGENT-01 | Requires live API keys + real game data | Run `graph.ainvoke({game_query: "Chiefs vs Raiders"})` locally, verify 9-node traversal in LangSmith trace |
| BettingCopilot multi-turn conversation quality | AGENT-03 | LLM response quality is subjective | Start `/copilot` session, ask 10+ questions, verify responses reference actual portfolio context |
| LLM evaluator verdict accuracy | AGENT-02 | PASS/WARN/REJECT quality depends on prompt | Test with known low-EV, medium-EV, and high-EV setups; verify verdicts are consistent with intent |
| langgraph-checkpoint-postgres connection to Supabase | AGENT-03 | Requires live Supabase credentials | Run integration test: `uv run pytest tests/integration/test_checkpoint_connection.py` (skip in CI) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-13
