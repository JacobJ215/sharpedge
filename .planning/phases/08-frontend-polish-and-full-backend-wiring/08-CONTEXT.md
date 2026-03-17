# Phase 8: Frontend Polish & Full Backend Wiring - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning
**Source:** PRD Express Path (docs/NEXT_PHASES_BRIEF.md)

<domain>
## Phase Boundary

Phase 8 makes every user-facing surface production-ready. Zero placeholder endpoints, zero mock data, zero test bypasses. Every screen in the web dashboard (Next.js) and mobile app (Flutter) reads from real production APIs with real Supabase JWT auth. Phase 6 venue dislocation and exposure widgets are wired into the UI. All 12 BettingCopilot tools are exercised end-to-end from both surfaces. FCM push notifications fire before Discord for PREMIUM/HIGH alpha alerts.

This phase does not add new backend capabilities — it wires existing Phase 1–7 capabilities fully into the user-facing layer.

</domain>

<decisions>
## Implementation Decisions

### Authentication (WIRE-01)
- Wire real Supabase JWT from auth session into ALL API calls — remove all placeholder `""` token references
- Complete `apps/web/src/app/auth/` — login page, callback handler, session management
- Verify RLS enforced on all user-scoped routes (portfolio, bets, bankroll)
- Mobile: Supabase auth with biometric (Face ID / fingerprint) gating account access

### Phase 6 UI Widgets (WIRE-02)
- Add venue dislocation widget to web prediction markets page (`/markets`)
- Add exposure / Kelly utilization widget to web bankroll page (`/bankroll`)
- Wire `get_venue_dislocation` and `get_exposure_status` copilot tools into frontend chat UX
- Both widgets must show real data from Phase 6 venue_adapters package (no stubs)

### FastAPI + Supabase RLS Verification (WIRE-03)
- All 6 FastAPI endpoints tested with real Supabase RLS (not test bypass / service_role)
- `apps/webhook_server/src/sharpedge_webhooks/jobs/` scanners running in production mode (not dry-run)
- Phase 6 `packages/venue_adapters/` wired into webhook_server for live Kalshi/Polymarket data
- `SnapshotStore` persistence verified with real Supabase connection
- `LedgerEntry` writing to real `ledger_entries` table (not test DB)

### Flutter End-to-End (WIRE-04)
- `ApiService` base URL points to deployed webhook_server (not localhost)
- Verified on physical device (iOS + Android) — biometric auth requires real device
- Offline degradation: app usable without network (cached last feed)
- Wire `apps/mobile/lib/screens/arbitrage_screen.dart` to real PM correlation endpoint
- Wire `apps/mobile/lib/screens/line_movement_screen.dart` to real scanner

### FCM Push Notifications (WIRE-05)
- Complete FCM push notification registration flow (token registration on login)
- Push notification fires BEFORE Discord alert for PREMIUM/HIGH alpha plays
- Test push delivery on both iOS (APNs) and Android (FCM direct)

### BettingCopilot Full Coverage (WIRE-06)
- All 12 BettingCopilot tools exercised from both web and mobile chat (not just unit-tested)
- Includes Phase 6 tools: `get_venue_dislocation`, `get_exposure_status`
- Streaming SSE verified working from Flutter (not just web)
- Session context (10+ turns) validated without hitting context limit
- End-to-end test: login → view plays → ask copilot → log bet → see portfolio update

### Pages to Complete
| Page | Route | Backend Endpoint | Requirement |
|------|-------|-----------------|-------------|
| Portfolio Overview | `/` | `GET /api/v1/users/{id}/portfolio` | WIRE-01 |
| Value Plays | `/plays` | `GET /api/v1/value-plays` | WIRE-01 |
| Game Detail | `/games/{id}` | `GET /api/v1/games/{id}/analysis` | WIRE-01 |
| Bankroll | `/bankroll` | `POST /api/v1/bankroll/simulate` + exposure widget | WIRE-02 |
| BettingCopilot | `/copilot` | SSE streaming + all 12 tools | WIRE-06 |
| Prediction Markets | `/markets` | PM edge scanner + venue dislocation widget | WIRE-02 |

### Claude's Discretion
- Order of wiring within a plan (can wire web + mobile in same plan or separate)
- Whether to use Playwright or Cypress for e2e web tests
- Test fixture strategy for Supabase RLS verification (service_role vs. user JWT in test)
- Exactly how offline caching is implemented in Flutter (Hive, SharedPreferences, etc.)

</decisions>

<specifics>
## Specific References from PRD

**Phase 6 copilot tools to wire:**
- `get_venue_dislocation` — cross-venue price dislocation score + venue breakdown
- `get_exposure_status` — current Kelly exposure utilization + fractional Kelly recommendation

**Push notification timing requirement:**
- FCM must fire BEFORE Discord alert (current order: Discord fires immediately on value_scanner_job result)
- Requires `value_scanner_job` to call FCM token registration endpoint and dispatch before Discord webhook

**Flutter screens requiring real wiring:**
- `apps/mobile/lib/screens/arbitrage_screen.dart` → real PM correlation endpoint
- `apps/mobile/lib/screens/line_movement_screen.dart` → real line movement scanner

**Auth pages (Next.js) to complete:**
- `apps/web/src/app/auth/login/page.tsx`
- `apps/web/src/app/auth/callback/route.ts`
- Token stored in session (not localStorage) — follows Supabase SSR pattern

</specifics>

<deferred>
## Deferred Ideas

- Prediction market resolution models (Kalshi/Polymarket standalone ML) → Phase 9+
- Expansion beyond sports (political, economic, entertainment markets) → Phase 9+
- Native desktop app → not planned
- Admin dashboard → not planned for this milestone

</deferred>

---

*Phase: 08-frontend-polish-and-full-backend-wiring*
*Context gathered: 2026-03-14 via PRD Express Path (docs/NEXT_PHASES_BRIEF.md)*
