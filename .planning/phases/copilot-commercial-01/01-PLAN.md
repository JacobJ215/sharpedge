---
phase: copilot-commercial-01
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
  - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
  - packages/agent_pipeline/tests/test_copilot_tools_count.py
  - tests/unit/agent_pipeline/test_copilot_tools.py
  - apps/web/src/components/copilot/chat-stream.tsx
  - apps/mobile/lib/screens/copilot_screen.dart
  - apps/webhook_server/src/sharpedge_webhooks/config.py
autonomous: true
requirements:
  - COPILOT-COMMERCIAL-01-CONTEXT.md (Areas 1–4)
must_haves:
  truths:
    - "Every copilot LLM call is preceded by a fixed system message covering RG disclaimers, no guaranteed outcomes, and tool-use discipline (no invented game_id)."
    - "analyze_game receives authenticated user_id from RunnableConfig when available; report body cap is 6000 characters with guidance to open full Game Analysis in-app."
    - "compare_books returns real multi-book data from OddsClient.get_line_comparison when ODDS_API_KEY is set and COPILOT_COMPARE_BOOKS is not 0; otherwise returns explicit unavailable_reason without fabricated books."
    - "get_exposure_status is not registered in COPILOT_TOOLS unless COPILOT_VENUE_EXPOSURE_SIM=1; when registered, tool description starts with [SIMULATION]."
    - "Web and mobile copilot UIs show a persistent RG footer line consistent with CONTEXT Area 1."
    - "Suggestion chips do not promise live arb; line-shopping wording matches compare_books behavior."
  artifacts:
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py
      provides: COPILOT_SYSTEM_PROMPT constant (imported by agent)
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py
      provides: SystemMessage prepended in agent_node after trim
    - path: packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py
      provides: compare_books implementation, analyze_game user_id+cap, conditional COPILOT_TOOLS
---

<objective>
Execute **Copilot Commercial Phase 1** (Trust & correctness) per `.planning/COPILOT-COMMERCIAL-01-CONTEXT.md`: system prompt + client footers, `analyze_game` auth + truncation, real `compare_books` via `sharpedge_odds`, conditional venue exposure sim tool, chips/copy + tests.

**Out of scope:** LangGraph checkpointing / `thread_id` (Phase 2), `resolve_game` SharpEdge id map (Phase 3), SSE tool visibility (Phase 4).
</objective>

<execution_context>
@.planning/COPILOT-COMMERCIAL-ROADMAP.md
@.planning/COPILOT-COMMERCIAL-01-CONTEXT.md
@packages/odds_client/src/sharpedge_odds/client.py
@packages/odds_client/src/sharpedge_odds/models.py
</execution_context>

## Context summary

| Area | Deliverable |
|------|-------------|
| 1 | `COPILOT_SYSTEM_PROMPT` + web/mobile footer (18+, risk, not financial/legal advice; problem-gambling: generic framing + TODO link for NCPG/legal) |
| 2 | `compare_books` → `OddsClient`, optional `REDIS_URL`, `COPILOT_COMPARE_BOOKS=0` kill switch |
| 3 | `analyze_game`: `RunnableConfig` user_id, `[:6000]`, prompt line for full analysis at `/games/{id}` when id known |
| 4 | Build `COPILOT_TOOLS` so `get_exposure_status` excluded unless `COPILOT_VENUE_EXPOSURE_SIM=1`; strengthen docstrings |

---

## Task 1 — System prompt module

**Create** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/prompts.py`:

- Export `COPILOT_SYSTEM_PROMPT: str` covering:
  - SharpEdge role (analytical assistant; not financial/investment/legal advice).
  - **18+**; gambling risk; user responsible for **local laws**.
  - Do **not** invent `game_id` or book prices; use tools; ask clarifying questions.
  - For **truncated** analysis: tell user to open **full Game Analysis** in the app (web route pattern: **`/games/{game_id}`** when they have the id; otherwise “Lines or Game Analysis in the dashboard”).
  - **Problem gambling:** if user asks for help or expresses harm: supportive tone + suggest professional / national resources (**placeholder URL text** `TODO: legal` acceptable for merge if marketing replaces before prod).

**Keep under ~1–1.5k tokens**; no duplicate of entire tool list — high-level tool discipline only.

---

## Task 2 — Prepend system message in `agent_node`

**Edit** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`:

- Import `SystemMessage` from `langchain_core.messages` (or `langchain_core` pattern already used in repo).
- Import `COPILOT_SYSTEM_PROMPT` from `prompts.py`.
- In `agent_node`, after computing `trimmed_msgs`:
  - If the first message is **not** already a system message, **prepend** `SystemMessage(content=COPILOT_SYSTEM_PROMPT)`.
  - If trimming removed an older system message, ensure **exactly one** system prompt at the front (dedupe rule: always prepend fresh system content, or merge if multiple system msgs exist — prefer **single canonical** system at index 0).

**Tests:** extend or add unit test that mocked `llm.invoke` receives a message list whose first element is system content containing a known substring (e.g. `18+` or `not financial`).

---

## Task 3 — `analyze_game` user_id + cap

**Edit** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`:

- Add `config: RunnableConfig | None = None` to `analyze_game` signature (LangChain injects this).
- Resolve `user_id`: same pattern as `get_active_bets` — `config.configurable.get("user_id")` overrides empty arg.
- Change report truncation from `[:2000]` to **`[:6000]`**.
- Optionally add one line in tool docstring: direct user to full report in app when truncated.

**Tests:** `test_copilot_tools.py` or new test — mock graph invoke, assert `user_id` passed into state when configurable set.

---

## Task 4 — Real `compare_books`

**Edit** `compare_books` in `tools.py`:

**Environment:**

- `ODDS_API_KEY` — required for live data.
- `REDIS_URL` — optional; pass into `OddsClient(api_key, redis_url=...)` when set.
- `COPILOT_COMPARE_BOOKS` — if set to `0` / `false`, return `{ "unavailable_reason": "disabled", ... }` without calling API.

**Tool signature (Phase 1 resolution strategy):**

- **`game_id`** — The Odds API event id when known.
- **`sport`** — string default `NBA` (map to `sharpedge_shared.types.Sport` via existing `SPORT_KEYS` / same mapping as `OddsClient` uses — reuse `Sport` enum from shared or odds constants).
- **`game_query`** — optional; when non-empty, resolve game via **`OddsClient.find_game(game_query, sport_enum)`** instead of id match.

**Algorithm:**

1. If disabled or no API key → structured error, no fake `books`.
2. Instantiate `OddsClient`.
3. Resolve `Game`:
   - If `game_query`: `find_game(game_query, sport)`.
   - Else: `get_odds(sport)` and find `g` where `g.id == game_id`.
4. If no game → `{ "error": "...", "hint": "Pass game_query with team names or a valid Odds API event id." }`.
5. `comparison = client.get_line_comparison(game)`.
6. Serialize `LineComparison` to JSON-safe dict; **cap** rows per list (e.g. max **8** lines per market side) to control tokens; include `game_id`, teams, `commence_time`, and `best` flags from `FormattedLine`.

**Docstring:** State that `game_id` is **The Odds API** event id; for natural language use `game_query`.

**Tests:** mock `OddsClient` or httpx in `tests/unit/agent_pipeline/test_copilot_tools.py` — happy path + missing key + disabled flag.

---

## Task 5 — Conditional `get_exposure_status` + docstrings

**Edit** `tools.py` (or small helper next to `COPILOT_TOOLS`):

- Build tool list: start from base + extended + venue **dislocation** only by default.
- Append `get_exposure_status` **only if** `os.environ.get("COPILOT_VENUE_EXPOSURE_SIM", "").lower() in ("1", "true", "yes")`.
- Update `get_exposure_status` tool description to start with **`[SIMULATION]`** and state it does not reflect logged SharpEdge bets.
- Update `get_user_exposure` description to say it reflects **pending bets logged in SharpEdge** / DB.

**Note:** `get_venue_dislocation` remains available unless product decides otherwise (not gated in CONTEXT).

---

## Task 6 — Web UI footer + chips

**Edit** `apps/web/src/components/copilot/chat-stream.tsx`:

- Add persistent **footer** under the input (replace or augment the existing “Scoped to your portfolio…” line) with RG one-liner matching CONTEXT (18+, risk, not advice).
- Update **SUGGESTIONS** / **SUGGESTION_ICONS**: replace **“Any live arb opportunities?”** with e.g. **“Best line across books for a game?”** or **“Compare books on a game”** (aligned with `compare_books` + `game_query`).

---

## Task 7 — Mobile UI footer

**Edit** `apps/mobile/lib/screens/copilot_screen.dart`:

- Add the **same** one-line RG disclaimer near the input (match web meaning; Flutter styling consistent with existing copilot screen).

---

## Task 8 — Tests and drift

**Edit** `packages/agent_pipeline/tests/test_copilot_tools_count.py`:

- Replace fixed `12` with **assertion on expected tool names** (ordered or set equality) for default env, **or** document expected count **14** when sim off (10 base + 3 extended + 2 venue with only dislocation + compare — actually count: base 10 includes compare, extended 3, venue: dislocation always, exposure conditional).

**Explicit default-env expected tool names** (executor must verify after implementation):

- All current names **except** `get_exposure_status` when sim off.
- Include `compare_books`, `get_venue_dislocation`, extended trio, etc.

**Optional:** `apps/webhook_server` — document new env vars in `config.py` or existing settings module (no secrets).

---

## Verification checklist (before merge)

- [ ] `uv run pytest packages/agent_pipeline/tests/test_copilot_tools_count.py tests/unit/agent_pipeline/test_copilot_tools.py` (and any new tests) pass.
- [ ] With `ODDS_API_KEY` unset, `compare_books` returns clear unavailable state in a manual or unit test.
- [ ] With `COPILOT_VENUE_EXPOSURE_SIM` unset, `get_exposure_status` not in `COPILOT_TOOLS`.
- [ ] Web copilot page shows RG footer; chips do not say “live arb”.
- [ ] Legal/marketing ticket filed for **final** disclaimer URL copy (Area 1 TODO).

---

## Dependency / risk notes

- **Odds API quota:** `compare_books` may call `get_odds` (sport-wide) when resolving by id — cache via Redis recommended in staging/prod.
- **Latency:** Up to Odds API client timeout; copilot request may run longer — acceptable per CONTEXT; monitor p95 after deploy.
- **`Sport` mapping:** Invalid sport string → tool returns friendly error listing supported codes.

---

## Document history

- **2026-03-21:** Initial plan from `/gsd-plan-phase` Copilot Commercial Phase 1.
