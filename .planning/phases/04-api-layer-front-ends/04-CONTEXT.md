# Phase 4: API Layer + Front-Ends - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a REST/SSE API (FastAPI), a Next.js 14 web dashboard (6 pages), and wire backend enhancements into the existing Flutter mobile app (full MOB-01–05 scope). All user-scoped data gated by Supabase RLS before any route is wired. Creating new data intelligence or ML models is out of scope — this phase surfaces what Phases 1–3 built.

</domain>

<decisions>
## Implementation Decisions

### Mobile tech stack
- **Keep Flutter** — `apps/mobile/` is already a Flutter project; continue with it, do not switch to Expo
- Wire all Phase 1–3 backend enhancements into the existing Flutter app
- **Full scope**: all 5 mobile requirements (MOB-01 through MOB-05) in this phase
- Push notifications via **Firebase Cloud Messaging (FCM)** — `firebase_messaging` package, iOS APNs + Android FCM
- **Swipe-to-log flow (MOB-01)**: swipe right opens a bottom sheet pre-filled with recommended Kelly stake and book; user adjusts if needed, taps Confirm — minimal friction
- The Flutter app has its own Dart HTTP layer; no shared TypeScript client with web

### FastAPI app structure
- **Extend the existing webhook server** (`apps/webhook_server/`) with a new `/api/v1/` prefix — do NOT create a separate service
- Add `routes/v1/` directory inside `apps/webhook_server/`
- Old `/api/value-plays`, `/api/bankroll` etc. stay as-is for Flutter backward compat during transition; new `/api/v1/*` endpoints run alongside
- **SSE streaming** for copilot: `StreamingResponse` with `text/event-stream` content type — FastAPI yields LangGraph tokens as SSE events. No WebSocket.
- New `/api/v1/value-plays`: returns `alpha_score`, `alpha_badge` (PREMIUM/HIGH/MEDIUM/SPECULATIVE), `regime_state` alongside existing EV/odds fields; supports `min_alpha` filter parameter

### Auth & RLS pattern
- **Supabase JWT** as the auth mechanism — frontend authenticates with Supabase (email/password), gets JWT, sends as `Authorization: Bearer` header
- FastAPI verifies JWT via `supabase.auth.get_user(token)` and passes it through to queries — RLS activates automatically
- **Auth dependency pattern**: reusable `get_current_user` FastAPI `Depends()` injected into protected routes; raises HTTP 401 on invalid/missing token
- **RLS scope**: ALL tables in the schema (max security) — shared game data tables use `service_role` key for bot/job writes; user-scoped queries use user JWT
- Value plays and game analysis endpoints are public (no auth required); portfolio and bankroll endpoints require `get_current_user`

### Web dashboard
- **Location**: `apps/web/` — create from scratch with Next.js 14 App Router + TypeScript
- **UI stack**: Tailwind CSS + shadcn/ui for components, **Recharts** for all charts
- **Data freshness**: polling on key pages — value plays page auto-refreshes every 60 seconds via SWR/React Query; portfolio/bankroll refresh on demand; copilot page is live via SSE
- **Value plays page (WEB-02)**: shadcn `DataTable` with sortable columns — alpha badge as colored pill, regime state as small chip, EV%, book, game. Dense/scannable, trading terminal feel
- **Monte Carlo fan chart (WEB-04)**: Recharts `AreaChart` — three layers: shaded P5–P95 band (risk range), solid P50 line (expected path), P5 floor line (ruin scenario)
- Supabase client in Next.js for auth — user signs in with Supabase, JWT forwarded to FastAPI for protected endpoints

### Claude's Discretion
- Exact shadcn/ui component selection per page
- Recharts color palette and theme for charts
- CORS configuration for Next.js ↔ FastAPI communication
- Exact Supabase RLS policy SQL for each table
- Flutter screen layout details beyond the defined interactions
- FCM setup steps and Firebase project configuration details
- API error response format/schema

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/webhook_server/src/sharpedge_webhooks/main.py`: FastAPI app with Whop + mobile routers — extend with `routes/v1/` router in same app
- `apps/webhook_server/src/sharpedge_webhooks/routes/mobile.py`: Existing `/api/value-plays`, `/api/arbitrage`, `/api/line-movements`, `/api/bankroll` — keep as backward-compat; v1 replaces with alpha-enriched versions
- `apps/mobile/lib/`: Flutter app with `screens/`, `providers/`, `services/`, `models/`, `widgets/` — extend existing structure; update services layer to call `/api/v1/` endpoints
- `apps/mobile/pubspec.yaml`: Add `firebase_messaging`, `local_auth`, `flutter_local_notifications` dependencies
- Phase 2 `copilot_graph` (LangGraph): Existing BettingCopilot graph — wire into SSE endpoint via `.astream_events()`
- Phase 1/2 `rank_by_alpha()`, `compose_alpha()`: Use to enrich value plays responses before returning from API

### Established Patterns
- Functional module-level APIs (not class-based) — all Phase 1–3 code follows this; API layer wraps functions, not objects
- FastAPI `APIRouter` with prefix + tags — existing `mobile.py` uses this pattern; follow for `v1/` routes
- Flutter Provider state management — existing pattern in `providers/`; follow for new screens

### Integration Points
- `apps/webhook_server/` → add `routes/v1/__init__.py` + individual route files; register router in `main.py`
- Flutter `services/` layer → update HTTP base URL to `/api/v1/`; add auth token header injection
- Supabase schema → enable RLS on all tables (migrations); add policies for user JWT + service_role bypass
- Phase 2 LangGraph `build_copilot_graph()` → call from SSE endpoint handler

</code_context>

<specifics>
## Specific Ideas

- The web value plays page should feel like a trading terminal — dense, sortable, information-rich. Not card-heavy or marketing-y.
- Old `/api/value-plays` stays alive during Flutter transition (do not break existing Flutter app during Phase 4 development)
- FCM push notifications must fire before the Discord bot alert for PREMIUM/HIGH plays — value_scanner_job.py needs to call FCM trigger before the Discord embed dispatch

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-api-layer-front-ends*
*Context gathered: 2026-03-14*
