---
phase: copilot-commercial-03
plan: 01
type: execute
wave: 1
depends_on:
  - copilot-commercial-02
files_modified:
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/game_resolve_logic.py
  - packages/agent_pipeline/tests/test_copilot_tools_count.py
  - packages/agent_pipeline/tests/test_copilot_game_resolve.py
  - tests/unit/agent_pipeline/test_copilot_tools.py
autonomous: true
requirements:
  - .planning/COPILOT-COMMERCIAL-ROADMAP.md (Phase 3)
  - .planning/phases/copilot-commercial-03/03-CONTEXT.md
must_haves:
  truths:
    - "Copilot exposes at least one tool that maps natural language + sport to candidate games with game_id, teams, and commence_time."
    - "Copilot exposes a tool (or clear dual-mode contract) to return a single best-matching game_id for follow-on tools (e.g. analyze_game, line tools)."
    - "When ODDS_API_KEY is missing, tools return structured errors without crashing the graph."
    - "System prompt instructs the model to resolve game_id via these tools before calling analysis tools when the user did not supply an id."
  artifacts:
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/game_resolve_logic.py
      provides: shared OddsClient fetch + normalize + caps for game listing / resolution
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
      provides: new @tool entries registered in COPILOT_TOOLS
---

<objective>
Implement **Copilot Commercial Phase 3 — natural language → `game_id`**: add odds-backed copilot tools so phrases like “Lakers tonight” yield a usable `game_id` for existing tools, aligned with `OddsClient` and webhook `odds_lines` behavior.
</objective>

<execution_context>
@.planning/phases/copilot-commercial-03/03-CONTEXT.md
@packages/odds_client/src/sharpedge_odds/client.py
@apps/webhook_server/src/sharpedge_webhooks/routes/v1/odds_lines.py
@packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/compare_books_logic.py
@packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
@packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
</execution_context>

## Wave 1 — Game resolution module + tools + prompt + tests

### Task 1 — `game_resolve_logic` helper module

<action>
Add `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/game_resolve_logic.py` that:

1. Reads API key from `os.environ.get("ODDS_API_KEY", "")` (and optionally the same fallbacks as `compare_books_logic` if documented there).
2. Exposes `search_games_impl(sport: str, query: str | None, *, limit: int = 10) -> dict` calling `OddsClient.get_odds` after parsing sport to `Sport`, building a list of dicts with keys at minimum: `game_id`, `home_team`, `away_team`, `commence_time` (ISO string), `sport`. If `query` is non-empty, filter client-side with case-insensitive substring match on team names or reuse `find_game` semantics where appropriate. Cap list length to `limit`.
3. Exposes `resolve_game_impl(sport: str, query: str) -> dict` that returns either `{"game": {...same fields...}}` or `{"game": null, "candidates": [...]}` when ambiguous (max 5 candidates) — pick one consistent contract and document in module docstring.
4. Uses `try/finally` or context manager to call `client.close()` if `OddsClient` provides `close()`.

Concrete defaults: `limit=10` for search; candidate cap `5` for ambiguity.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/compare_books_logic.py
- packages/odds_client/src/sharpedge_odds/client.py
- `sharpedge_shared.types.Sport` and `sharpedge_odds.constants.SPORT_KEYS` (same pattern as `compare_books_logic.py`)
</read_first>

<acceptance_criteria>
- `game_resolve_logic.py` exists under `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/`.
- File contains callable symbols `search_games_impl` and `resolve_game_impl` (exact names).
- `grep -n ODDS_API_KEY packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/game_resolve_logic.py` returns at least one match.
- `uv run pytest packages/agent_pipeline/tests/test_copilot_game_resolve.py` exits 0 after Task 4 adds tests (may be RED until Task 4 complete — executor runs Task 4 in same wave).
</acceptance_criteria>

---

### Task 2 — Register `search_games` and `resolve_game` tools

<action>
In `tools.py`:

1. Import and wrap `search_games_impl` / `resolve_game_impl` in two `@tool` functions with docstrings stating: use when user gives team names or “tonight” without `game_id`; always pass `sport` when known; max results bounded by impl.
2. Append both to `COPILOT_TOOLS` (and ensure `test_copilot_tools_count.py` expected count updated).

Do not import from `apps/bot` or `apps/webhook_server`.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
- packages/agent_pipeline/tests/test_copilot_tools_count.py
</read_first>

<acceptance_criteria>
- `grep -n "search_games" packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` matches at least one `@tool` definition.
- `grep -n "resolve_game" packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` matches at least one `@tool` definition.
- `COPILOT_TOOLS` includes both tools (verify with `grep -A200 "COPILOT_TOOLS" packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py | grep search_games` and same for `resolve_game`).
- `test_copilot_tools_count.py` expected integer reflects new tool count and passes.
</acceptance_criteria>

---

### Task 3 — System prompt update

<action>
In `prompts.py` (`COPILOT_SYSTEM_PROMPT`), add a short bullet block: when user refers to a game without `game_id`, call `search_games` / `resolve_game` before `analyze_game`, `get_line_movements`, or other tools that require `game_id`. Do not invent ids.
</action>

<read_first>
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
</read_first>

<acceptance_criteria>
- `grep -n "resolve_game\\|search_games" packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py` has at least one match.
- `grep -n "game_id" packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py` still contains guidance not to invent game_id (existing or strengthened).
</acceptance_criteria>

---

### Task 4 — Unit tests (mock OddsClient)

<action>
Add `packages/agent_pipeline/tests/test_copilot_game_resolve.py` that mocks `OddsClient` (or `game_resolve_logic` import of it) to return 2–3 fake games and asserts:

1. `search_games_impl` returns capped list with expected `game_id` keys.
2. `resolve_game_impl` returns a single game dict when `find_game` / filter would match one row.

Keep tests hermetic (no network).
</action>

<read_first>
- packages/agent_pipeline/tests/test_copilot_tools.py
- packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/game_resolve_logic.py
</read_first>

<acceptance_criteria>
- `packages/agent_pipeline/tests/test_copilot_game_resolve.py` exists.
- `cd /Users/revph/sharpedge && uv run pytest packages/agent_pipeline/tests/test_copilot_game_resolve.py -q` exits 0.
- `uv run pytest packages/agent_pipeline/tests/test_copilot_tools_count.py packages/agent_pipeline/tests/test_copilot_game_resolve.py -q` exits 0.
</acceptance_criteria>

---

## Verification (phase goal)

- Manual: with `ODDS_API_KEY` set in dev, ask copilot (or unit integration smoke) “NBA Lakers next game id” flow returns a real id shape — optional for executor; automated tests are mandatory above.

---

## Plan metadata

- **2026-03-21:** Plan created via `/gsd-plan-phase` Copilot Commercial Phase 3 (roadmap slug `copilot-commercial-03`; GSD `init plan-phase` does not enumerate this slug — directory is canonical).
