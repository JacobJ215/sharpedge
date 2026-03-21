# BettingCopilot — commercial readiness roadmap

Phased PR plan for SharpEdge BettingCopilot: threading, trust, tooling, and scale.  
**Audience:** engineering + launch checklist.

---

## Architecture decision: where conversation state lives

**Chosen default: LangGraph checkpointing on the webhook server (FastAPI), backed by Postgres (e.g. Supabase Postgres).**

| Criterion | Checkpointing on webhook server | Thin Next.js BFF owns chat state |
|-----------|--------------------------------|----------------------------------|
| Single API for web + mobile | Yes — one `POST /api/v1/copilot/chat` | Risk of duplicating thread logic or forcing all clients through Next |
| Agent runtime | Graph stays next to OpenAI + tools | Next still proxies to Python unless agent is rewritten in TS |
| Audit / compliance | Central logs, `user_id`, `thread_id`, retention | Split unless BFF is pass-through only |
| Billing / rate limits | Fits existing v1 routes and auth patterns | Redundant if state is authoritative in Python |

**Optional later:** a **pass-through** Next route (`app/api/copilot/chat`) for same-origin/CORS or hiding the API hostname. It must **forward** `message`, `thread_id`, and `Authorization` — **not** store conversation state.

---

## Launch order (what to ship first)

1. **Phase 1** — Trust and correctness (reputational risk).
2. **Phase 2** — Server-side memory (defines the commercial chat product).
3. **Phase 3** — Natural language → `game_id` (largest sports UX win).
4. **Phases 4–7** — Can run in parallel tracks post-launch or as capacity allows.

---

## Phase 1 — Trust and correctness

**Goal:** No misleading tools; user context is consistent; tests match code.

| Work item | Notes |
|-----------|--------|
| System message | Persona, responsible gambling, “do not invent `game_id`”, when to call which tool |
| `analyze_game` + `user_id` | Read `user_id` from `RunnableConfig` (same pattern as portfolio tools) |
| `compare_books` | Implement real comparison via `OddsClient` + existing endpoints, **or** replace with honest limited tool + update UI copy/suggestion chips |
| `get_exposure_status` vs `get_user_exposure` | Clarify in tool docstrings; merge or gate synthetic `ExposureBook` behind env |
| Tests | Fix `test_copilot_tools_count` (and similar) to match current tool set (e.g. base + venue + extended) |
| `analyze_game` output | Raise truncation cap or add continuation/pagination if product needs full reports |

**Exit criteria:** Stub tools are not marketed as full features; portfolio and analysis see the same authenticated user.

---

## Phase 2 — Server-side memory (commercial core)

**Goal:** Multi-turn copilot with one backend source of truth for web and mobile.

| Work item | Notes |
|-----------|--------|
| `thread_id` / `session_id` | Client sends id; server loads checkpoint and appends the new user message |
| LangGraph checkpointer | Postgres-backed (Supabase-compatible); use recommended schema / package |
| AuthZ | Every read/write scoped by `user_id` + `thread_id` (RLS or explicit checks) |
| Retention | Policy: TTL, max threads per user, or export/delete for compliance |
| Clients | Next `chat-stream.tsx` + Flutter `copilot_screen.dart`: generate/persist UUID, send on each request |

**Exit criteria:** Same thread can resume after navigation (when client persists `thread_id`); mobile and web behave identically.

---

## Phase 3 — Resolve natural language → ids

**Goal:** Remove friction for line movement, sharp signals, projections, book comparison.

| Work item | Notes |
|-----------|--------|
| `search_games` / `resolve_game` | query + sport → `game_id`, teams, commence time |
| Data sources | Align with existing odds/DB feeds (bot `lines`, webhook v1 odds routes) |
| Optional | `list_upcoming_games` with filters |

**Exit criteria:** “Lakers tonight” works without pasting opaque ids.

---

## Phase 4 — Transparency and supportability

**Goal:** Users and support can see what the copilot used.

| Work item | Notes |
|-----------|--------|
| SSE (or parallel channel) | Tool start/end events: name + short summary (not full raw JSON) |
| UI | Tool chips or collapsible “Steps / sources” |

**Exit criteria:** Fewer “it hallucinated” reports; easier production debugging.

---

## Phase 5 — Prediction markets and trading depth

**Goal:** PM questions do not dead-end at “paste a ticker.”

| Work item | Notes |
|-----------|--------|
| Thin tool wrappers | Scan edges, correlation, regime — wrap `sharpedge_analytics`, cap row counts |
| Optional | User PM positions if persisted in DB |
| Writes | Order placement only with explicit **human-in-the-loop** confirmation |

**Exit criteria:** PM workflows comparable to sportsbook assistant depth for common intents.

---

## Phase 6 — Scale the brain (sub-agents / skills)

**Goal:** More capabilities without a flat list of dozens of tools.

| Work item | Notes |
|-----------|--------|
| Supervisor or intent router | Route to subgraphs: Sports, PM, Portfolio, AppGuide (product help + deep links, no fabricated data) |
| Skills | Pack = system addendum + **subset** of tools per turn |

**Exit criteria:** Safer routing; new features ship as skill/tool bundles.

---

## Phase 7 — Commercial hardening

**Goal:** Production operations and margin.

| Work item | Notes |
|-----------|--------|
| Rate limits | Per tier on `/copilot/chat` (align with subscription/tier middleware) |
| Logging + PII | What is stored in checkpoints; redaction policy |
| Cost controls | Max graph steps / recursion, token budget per thread |
| Feature flags | Gate experimental tools |

**Exit criteria:** Observable, controllable, tier-aware copilot at scale.

---

## Reference: current implementation touchpoints

- **Graph:** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py`
- **Tools:** `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`, `tools_extended.py`, `venue_tools.py`
- **API:** `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py`
- **Web UI:** `apps/web/src/components/copilot/chat-stream.tsx`
- **Mobile UI:** `apps/mobile/lib/screens/copilot_screen.dart`

---

## Document history

- **2026-03-21:** Initial roadmap (architecture decision + phased PRs).
