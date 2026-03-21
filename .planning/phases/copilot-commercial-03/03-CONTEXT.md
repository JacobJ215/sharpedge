# Copilot Commercial Phase 3 — Context

**Gathered:** 2026-03-21  
**Status:** Ready for planning  
**Source:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` Phase 3 + codebase alignment

---

## Phase boundary

Deliver **natural language → sportsbook `game_id`** (and human-readable game context) inside BettingCopilot so users never paste opaque IDs for line movement, projections, book comparison, and analysis tools.

---

## Implementation decisions

### Locked

- **Tools:** Add copilot `@tool` functions `search_games` and `resolve_game` (names may be adjusted to match existing naming conventions) with **query string + sport** → list or single match.
- **Data source:** Reuse **`sharpedge_odds.OddsClient`** (`get_odds`, `find_game`) — same stack as `compare_books` / `apps/webhook_server/.../odds_lines.py` (`_pick_game` pattern). No new HTTP surface required for MVP.
- **Caps:** Return **JSON-serializable dicts**, max **~10 games** for search; clear empty/error shapes consistent with `tools.py`.
- **Env:** **`ODDS_API_KEY`** (or pipeline/bot parity); fail soft with `{"error": ...}` when unset, matching other odds-backed tools.
- **Optional stretch:** `list_upcoming_games` with sport + time window — only if it fits one plan wave without scope creep.

### Claude's discretion

- Exact tool names and parameter names (`sport` enum vs string) — mirror `Sport` / webhook validation where practical.
- Whether `resolve_game` returns confidence / alternates when ambiguous vs asking a follow-up in prose only.
- Unit vs integration tests: prefer **`unittest.mock` on OddsClient** in `packages/agent_pipeline/tests/`.

---

## Canonical references

- `.planning/COPILOT-COMMERCIAL-ROADMAP.md` — Phase 3 exit criteria (“Lakers tonight” without opaque ids).
- `packages/odds_client/src/sharpedge_odds/client.py` — `get_odds`, `find_game`, `close`.
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/odds_lines.py` — `_pick_game`, `_game_summary`.
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/compare_books_logic.py` — env + OddsClient usage pattern.
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py` — when to call which tool.
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` — `COPILOT_TOOLS` assembly.

---

*Phase: copilot-commercial-03*
