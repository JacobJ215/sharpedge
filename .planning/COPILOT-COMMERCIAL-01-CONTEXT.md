# Copilot commercial readiness — Phase 1 (Trust & correctness) CONTEXT

**Discuss-phase:** 2026-03-21  
**Scope:** `.planning/COPILOT-COMMERCIAL-ROADMAP.md` — **Phase 1 only**  
**Input:** User selected gray areas **1, 2, 3, 4** for discussion.

**Assumption:** Decisions below use **launch-oriented defaults** where specifics were not answered line-by-line. Legal/compliance should review **Area 1** before release; product may revise any item and update this file.

---

## Locked from prior roadmap (not reopened here)

- **Phase 2+:** Conversation persistence = LangGraph checkpointer on **webhook server** + **Postgres** (e.g. Supabase). Optional Next.js route = **pass-through only**, no authoritative chat state in Next.

---

## Area 1 — Responsible gambling & disclaimers

| Decision | Choice |
|----------|--------|
| **Placement** | **System prompt (required)** + **persistent one-line footer** on copilot UI (web + mobile), not only first message. |
| **Tone / content** | Short, plain language: **18+**; betting involves **risk of loss**; SharpEdge is **informational / analytical**, **not** financial, investment, or legal advice; users responsible for compliance with **local laws**. |
| **Problem gambling** | If user signals distress or asks for help: respond with **generic support framing** + suggest **national/local problem-gambling resources** (exact links/strings: **TODO legal/marketing** — e.g. NCPG for US audience). No commitment to automated “refuse all betting” unless legal requires later. |
| **Marketing alignment** | Disclaimers **may be stricter** than growth copy; copilot must not contradict disclaimers with “guaranteed” language. |

**Deferred (not Phase 1 scope):** Jurisdiction-specific packs (NJ, UK, etc.) → note for future phase if counsel requires.

---

## Area 2 — `compare_books` (real multi-book comparison)

| Decision | Choice |
|----------|--------|
| **v1 launch** | **(A) Real multi-book line comparison** when `ODDS_API_KEY` is set. Implement `compare_books` using **`OddsClient.get_line_comparison(game)`** after resolving a **`Game`** from The Odds API (`packages/odds_client`). Return structured spreads / totals / h2h per book with **best-line** flags already computed by the client. **No stub** that pretends to compare. |
| **Latency / I/O** | Accept **network latency** (client default **30s** HTTP timeout). Prefer **optional Redis** on `OddsClient(redis_url=...)` for cache hits on repeated sport-level fetches. Tool should **time-box** copilot-facing work if needed (e.g. fail soft with “try again”) — exact cap for planner. |
| **Identifier gap** | Tool arg `game_id` today must be aligned in implementation: either treat as **The Odds API event `id`**, or add **`sport` + natural-language resolution** via **`OddsClient.find_game`** when the id is internal SharpEdge — **planner chooses minimal path for Phase 1** (likely: document Odds API id + optional `find_game` fallback in same tool or follow-up). |
| **Missing key** | If `ODDS_API_KEY` unset: return clear **`unavailable_reason`** + short user-facing note (no fabricated books). |
| **Suggestion chips / copy** | **Keep** line-shopping / best-line style prompts **if** they match implemented behavior. **“Live arb”** still implies **cross-market or risk-free structures** — do not promise arb unless a dedicated arb tool exists; chips may say **“best spread across books”** or similar. |
| **Feature flag** | Optional **`COPILOT_COMPARE_BOOKS=0`** to disable in crisis; default **on** when key present. Tier-gating **Phase 7** optional. |

**Deferred:** Full **cross-exchange arb** parity with Discord scanners (multi-leg, Kalshi × books) → later roadmap phase; this CONTEXT covers **The Odds API** multi-book comparison only.

**Implementation pointer:** `OddsClient.get_odds(sport)` → locate `Game` by `id` or `find_game(query, sport)` → `get_line_comparison(game)` → serialize capped list of `FormattedLine` for the LLM (respect token limits).

---

## Area 3 — `analyze_game` output in copilot

| Decision | Choice |
|----------|--------|
| **Length** | Raise copilot-facing truncation from **~2000** to **~6000 characters** for v1 (balance context cost vs usefulness). |
| **Behavior** | System/tool guidance: lead with **short executive summary**; if content is truncated, **explicitly** tell the user to open **full Game Analysis** in the app (deep link or route path **TODO** in plan). |
| **Clients** | **Same** effective limit and behavior for **web and mobile**. |
| **Tiers** | **No** different report length by tier for v1; revisit in Phase 7 if cost requires it. |

**Deferred:** Pagination / `continue_analysis` tool — only if 6k proves insufficient after launch metrics.

---

## Area 4 — Dual “exposure” tools (`get_user_exposure` vs `get_exposure_status`)

| Decision | Choice |
|----------|--------|
| **Canonical user question** | **`get_user_exposure`** = **real** open/pending bet exposure from **SharpEdge DB** for the authenticated user. |
| **Synthetic venue book** | **`get_exposure_status`** is **not** user portfolio truth. **v1 production default:** omit from copilot tool list unless **`COPILOT_VENUE_EXPOSURE_SIM=1`** (dev/demo). When enabled, tool description **must** lead with **`[SIMULATION]`** and state it does **not** reflect logged bets. |
| **Naming** | If sim remains in any build, plan rename to something like **`get_venue_exposure_simulation`** in a follow-up PR to reduce model confusion (optional Phase 1 stretch). |
| **Future merge** | Single merged “exposure” tool that combines DB + venue sim → **explicit later phase**; not Phase 1. |

---

## code_context (for planner / implementer)

| Topic | Location |
|-------|-----------|
| Copilot graph | `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py` |
| Tools | `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`, `tools_extended.py`, `venue_tools.py` |
| SSE API | `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` |
| Web copilot UI + chips | `apps/web/src/components/copilot/chat-stream.tsx` |
| Mobile copilot | `apps/mobile/lib/screens/copilot_screen.dart` |
| Tool count test (drift) | `packages/agent_pipeline/tests/test_copilot_tools_count.py` |
| Odds API client (line comparison) | `packages/odds_client/src/sharpedge_odds/client.py` (`get_line_comparison`, `find_game`, `get_odds`) |

---

## Next steps (GSD)

1. **`/gsd-plan-phase`** (or manual PLAN.md) for **Copilot Commercial Phase 1** using this CONTEXT.  
2. **`/gsd-execute-phase`** in small PRs: system prompt + footer, `analyze_game` user_id + cap, **`compare_books` wired to `OddsClient` + id resolution**, exposure gating, tests, chip copy.  
3. **Legal pass** on Area 1 footer + prompt language before public launch.  
4. **Discuss-phase** again for **Phase 2** (checkpointing) when ready — separate CONTEXT file.

---

## Document history

- **2026-03-21:** Initial CONTEXT from discuss-phase; areas 1–4; defaults applied pending legal/product override.
- **2026-03-21:** Area 2 revised — **real multi-book comparison** via `OddsClient.get_line_comparison`, `ODDS_API_KEY`, accepted latency; identifier alignment and arb wording called out.
