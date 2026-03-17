# Phase 8: Frontend Polish & Full Backend Wiring - Research

**Researched:** 2026-03-14
**Domain:** Full-stack wiring — Next.js 14 App Router auth, Flutter API surface, FCM push, Supabase RLS, BettingCopilot tool coverage, Phase 6 UI widgets
**Confidence:** HIGH — all findings based on direct codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Wire real Supabase JWT from auth session into ALL API calls — remove all placeholder `""` token references
- Complete `apps/web/src/app/auth/` — login page, callback handler, session management
- Verify RLS enforced on all user-scoped routes (portfolio, bets, bankroll)
- Mobile: Supabase auth with biometric (Face ID / fingerprint) gating account access
- Add venue dislocation widget to web prediction markets page (`/markets`)
- Add exposure / Kelly utilization widget to web bankroll page (`/bankroll`)
- Wire `get_venue_dislocation` and `get_exposure_status` copilot tools into frontend chat UX
- Both widgets must show real data from Phase 6 venue_adapters package (no stubs)
- All 6 FastAPI endpoints tested with real Supabase RLS (not test bypass / service_role)
- `apps/webhook_server/src/sharpedge_webhooks/jobs/` scanners running in production mode (not dry-run)
- Phase 6 `packages/venue_adapters/` wired into webhook_server for live Kalshi/Polymarket data
- `SnapshotStore` persistence verified with real Supabase connection
- `LedgerEntry` writing to real `ledger_entries` table (not test DB)
- `ApiService` base URL points to deployed webhook_server (not localhost)
- Verified on physical device (iOS + Android) — biometric auth requires real device
- Offline degradation: app usable without network (cached last feed)
- Wire `apps/mobile/lib/screens/arbitrage_screen.dart` to real PM correlation endpoint
- Wire `apps/mobile/lib/screens/line_movement_screen.dart` to real scanner
- Complete FCM push notification registration flow (token registration on login)
- Push notification fires BEFORE Discord alert for PREMIUM/HIGH alpha plays
- Test push delivery on both iOS (APNs) and Android (FCM direct)
- All 12 BettingCopilot tools exercised from both web and mobile chat (not just unit-tested)
- Includes Phase 6 tools: `get_venue_dislocation`, `get_exposure_status`
- Streaming SSE verified working from Flutter (not just web)
- Session context (10+ turns) validated without hitting context limit
- End-to-end test: login → view plays → ask copilot → log bet → see portfolio update

### Claude's Discretion
- Order of wiring within a plan (can wire web + mobile in same plan or separate)
- Whether to use Playwright or Cypress for e2e web tests
- Test fixture strategy for Supabase RLS verification (service_role vs. user JWT in test)
- Exactly how offline caching is implemented in Flutter (Hive, SharedPreferences, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Prediction market resolution models (Kalshi/Polymarket standalone ML) → Phase 9+
- Expansion beyond sports (political, economic, entertainment markets) → Phase 9+
- Native desktop app → not planned
- Admin dashboard → not planned for this milestone
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIRE-01 | Real Supabase JWT wired into all API calls; web auth pages complete (login, callback, session); RLS enforced on all user-scoped routes | Web `supabase.ts` uses `@supabase/supabase-js` v2; portfolio page already uses `supabase.auth.getSession()`; only missing: login page, callback route, auth guard on dashboard layout |
| WIRE-02 | Phase 6 venue dislocation widget on `/markets`; exposure/Kelly widget on `/bankroll`; both tools wired into copilot chat UX | `get_venue_dislocation` and `get_exposure_status` in `COPILOT_TOOLS` list; no web widget exists yet; need new API endpoints to surface dislocation/exposure data to frontend |
| WIRE-03 | All 6 FastAPI endpoints tested with real RLS; scanners in production mode; Phase 6 venue_adapters wired into webhook_server; SnapshotStore and LedgerEntry writing to real Supabase | Both SnapshotStore and LedgerStore use dual-mode (in-memory ↔ Supabase via env vars); currently no production env validation; RLS tests use mock supabase (service_role bypass) |
| WIRE-04 | Flutter ApiService base URL points to deployed server; PM correlation endpoint wired to arbitrage screen; line movement scanner wired to line_movement screen; offline caching | `ApiService._baseUrl` is `String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000')` — needs deploy-time override; both screens use `AppState.refresh()` which calls old `/api/arbitrage` and `/api/line-movements` stub routes |
| WIRE-05 | FCM token registration on login; FCM fires before Discord for PREMIUM/HIGH; verified on iOS + Android | FCM infrastructure fully implemented: `value_scanner_job.py` calls `send_fcm_notifications_for_play()` BEFORE appending to `_pending_value_alerts`; `NotificationService.registerToken()` called in `_ShellState.initState()`; only gap: no real PM correlation or line movement endpoints behind arbitrage/line_movement screens |
| WIRE-06 | All 12 tools exercised end-to-end from web and mobile chat; SSE verified from Flutter; 10+ turn sessions; full e2e journey | 12 tools confirmed assembled: 10 base tools + 2 VENUE_TOOLS via list concatenation; SSE streaming works in both `chat-stream.tsx` and `copilot_screen.dart`; copilot endpoint is public (no auth token passed) — needs auth header for context-aware tools |
</phase_requirements>

---

## Summary

Phase 8 is a wiring and integration phase, not a build phase. The backend is complete and battle-tested across Phases 1–7. The frontend surfaces (Next.js web, Flutter mobile) are partially wired, with several critical gaps that prevent calling this production-ready.

**Web auth gap:** The dashboard has no login page or auth callback. `apps/web/src/app/auth/` contains only a `set-password/` page (used for invite flows) — there is no `login/page.tsx` and no `callback/route.ts`. The dashboard layout has no auth guard; an unauthenticated user can see the dashboard skeleton (with failed data loads). The portfolio page correctly reads `supabase.auth.getSession()` but that requires the user to have an active session, which cannot happen without a login page.

**Flutter data source gap:** `AppState.refresh()` calls `_api.getValuePlays()`, `getArbitrageOpportunities()`, and `getLineMovements()`, all of which hit old stub routes (`/api/value-plays`, `/api/arbitrage`, `/api/line-movements`) rather than the v1 production endpoints. The `ArbitrageScreen` and `LineMovementScreen` therefore read stale/mock data. A new `GET /api/v1/prediction-markets/correlation` endpoint needs to back `ArbitrageScreen`, and `GET /api/v1/line-movement` needs to back `LineMovementScreen`.

**Phase 6 UI widgets missing:** The venue dislocation widget and exposure/Kelly utilization widget are tools in the LangGraph copilot (`get_venue_dislocation`, `get_exposure_status`) but have no corresponding UI widgets on `/markets` and `/bankroll`. New FastAPI endpoints need to expose dislocation and exposure data outside the copilot context.

**Primary recommendation:** Wire in four plan waves: (1) web auth + RLS hardening, (2) Phase 6 API endpoints + web widgets, (3) Flutter API migration + offline cache, (4) end-to-end validation sweep.

---

## Current Codebase State (Audit Findings)

### What Is Already Done (Do Not Rebuild)

| Component | File | Status |
|-----------|------|--------|
| Web Supabase client | `apps/web/src/lib/supabase.ts` | Done — `createClient` with anon key |
| Web portfolio auth | `apps/web/src/app/(dashboard)/page.tsx` | Done — `supabase.auth.getSession()` + `onAuthStateChange` |
| Web api.ts | `apps/web/src/lib/api.ts` | Done — all v1 endpoints with `Authorization: Bearer ${token}` |
| FastAPI deps.py | `apps/webhook_server/src/sharpedge_webhooks/routes/v1/deps.py` | Done — `get_current_user` via `client.auth.get_user(token)` |
| FastAPI notifications | `apps/webhook_server/src/sharpedge_webhooks/routes/v1/notifications.py` | Done — `POST /api/v1/users/{id}/device-token` with RLS check |
| Flutter AuthService | `apps/mobile/lib/services/auth_service.dart` | Done — Supabase signIn + biometrics + session token |
| Flutter NotificationService | `apps/mobile/lib/services/notification_service.dart` | Done — FCM init, iOS permissions, `registerToken()` |
| Flutter main.dart _Shell | `apps/mobile/lib/main.dart` | Done — FCM `registerToken` in `_ShellState.initState()` |
| Flutter LoginScreen | `apps/mobile/lib/screens/login_screen.dart` | Done — email+password → biometric gate → `AppState.setAuthenticated()` |
| Flutter CopilotScreen SSE | `apps/mobile/lib/screens/copilot_screen.dart` | Done — SSE via `http.Request` streaming |
| FCM before Discord | `apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py` | Done — `send_fcm_notifications_for_play(play)` called before `_pending_value_alerts.append(play)` |
| COPILOT_TOOLS (12 tools) | `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` | Done — 10 base + VENUE_TOOLS; `COPILOT_TOOLS` list confirmed at line 438–449 |
| SnapshotStore dual-mode | `packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py` | Done — in-memory fallback + Supabase when `SUPABASE_URL`+`SUPABASE_SERVICE_ROLE_KEY` set |
| LedgerStore dual-mode | `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` | Done — same dual-mode pattern |

### What Is Missing (Must Build in Phase 8)

| Gap | Location | Impact |
|-----|----------|--------|
| Web login page | `apps/web/src/app/auth/login/page.tsx` | WIRE-01 — no way to authenticate on web |
| Web auth callback route | `apps/web/src/app/auth/callback/route.ts` | WIRE-01 — Supabase SSR callback handler |
| Web dashboard auth guard | `apps/web/src/app/(dashboard)/layout.tsx` | WIRE-01 — unauth users see dashboard |
| Venue dislocation API endpoint | New `GET /api/v1/markets/dislocation` | WIRE-02 — widget needs data source |
| Exposure status API endpoint | New `GET /api/v1/bankroll/exposure` | WIRE-02 — widget needs data source |
| Web venue dislocation widget | New component on `/prediction-markets` | WIRE-02 |
| Web exposure/Kelly widget | New component on `/bankroll` | WIRE-02 |
| Flutter v1 endpoint migration | `AppState.refresh()` → v1 routes | WIRE-04 — screens use `/api/arbitrage` stub |
| PM correlation endpoint | New `GET /api/v1/prediction-markets/correlation` | WIRE-04 — ArbitrageScreen source |
| Line movement endpoint | New `GET /api/v1/line-movement` | WIRE-04 — LineMovementScreen source |
| Flutter offline cache | SharedPreferences or Hive | WIRE-04 — "last feed" requirement |
| Supabase RLS prod verification | Integration tests with real JWT | WIRE-03 — current tests mock supabase |
| Copilot auth token forwarding | `chat-stream.tsx` + `copilot_screen.dart` | WIRE-06 — tools like `get_active_bets` need user context |

---

## Standard Stack

### Core Technologies (All Pre-Existing — Do Not Change)

| Technology | Version | Location |
|------------|---------|----------|
| Next.js | 14.2.5 | `apps/web/` |
| `@supabase/supabase-js` | ^2.45.0 | `apps/web/package.json` |
| Flutter | SDK (latest stable) | `apps/mobile/` |
| `supabase_flutter` | ^2.6.0 | `apps/mobile/pubspec.yaml` |
| `firebase_messaging` | ^15.1.0 | `apps/mobile/pubspec.yaml` |
| `local_auth` | ^2.3.0 | `apps/mobile/pubspec.yaml` |
| FastAPI + Python | (existing) | `apps/webhook_server/` |
| Vitest + jsdom | (existing) | `apps/web/vitest.config.ts` |

### Supabase SSR Pattern for Next.js 14 App Router

The current web app uses `@supabase/supabase-js` directly (client-side only). For the login page and callback route in App Router, the SSR-compatible approach uses the same `supabase-js` client but handles session exchange in the Route Handler.

**Auth flow for Next.js App Router (non-SSR, browser-only — consistent with current project pattern):**

```
1. Login page: supabase.auth.signInWithPassword({ email, password })
2. On success: router.push('/') → dashboard
3. Session is stored in Supabase's browser localStorage by default
4. Callback route: handles email confirmation / magic links
5. Dashboard layout guard: supabase.auth.getSession() → redirect to /auth/login if null
```

The project already uses `@supabase/supabase-js` v2 (not `@supabase/ssr`), which is fine for client-side auth. Adding `@supabase/ssr` is NOT required given the current project choice to use browser-side auth.

**Confirmed pattern from `apps/web/src/app/(dashboard)/page.tsx`:**
```typescript
// Existing working pattern — replicate for auth guard
supabase.auth.getSession().then(({ data: { session } }) => {
  setToken(session?.access_token ?? '')
})
const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
  setToken(session?.access_token ?? '')
})
```

### Flutter API Migration Pattern

`ApiService._baseUrl` is compile-time injected via `String.fromEnvironment`:
```dart
static const String _baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
```

Build for production with:
```bash
flutter build ios --dart-define=API_BASE_URL=https://your-server.com
flutter build apk --dart-define=API_BASE_URL=https://your-server.com
```

Old stub routes that need migration:
- `_api.getValuePlays()` → `/api/value-plays` (stub) → should use `getValuePlaysV1()` → `/api/v1/value-plays`
- `_api.getArbitrageOpportunities()` → `/api/arbitrage` (stub) → needs new `GET /api/v1/prediction-markets/correlation`
- `_api.getLineMovements()` → `/api/line-movements` (stub) → needs new `GET /api/v1/line-movement`
- `_api.getBankroll()` → `/api/bankroll` (stub) → can stay for bankroll screen or migrate to v1

### Flutter Offline Caching Options

Both options are acceptable (Claude's discretion):

| Option | Package | When to Use |
|--------|---------|-------------|
| SharedPreferences | `shared_preferences` (already common) | Simple JSON cache for value plays + portfolio |
| Hive | `hive_flutter` | Type-safe, faster for larger datasets |

**Recommended for this project:** SharedPreferences — simple, no schema migrations, adequate for "last feed" requirement (cache List<ValuePlay> as JSON string).

---

## Architecture Patterns

### Web Auth Pages Pattern

```
apps/web/src/app/
├── auth/
│   ├── login/
│   │   └── page.tsx          ← NEW: email+password form, supabase.auth.signInWithPassword
│   ├── callback/
│   │   └── route.ts          ← NEW: handles Supabase email confirmation redirect
│   └── set-password/
│       └── page.tsx          ← EXISTS: invite flow handler
└── (dashboard)/
    ├── layout.tsx             ← MODIFY: add auth guard (redirect to /auth/login)
    └── ...
```

**Login page pattern (consistent with existing portfolio auth):**
```typescript
// apps/web/src/app/auth/login/page.tsx
'use client'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

// On submit: supabase.auth.signInWithPassword({ email, password })
// On success: router.push('/')
// Token stored automatically by supabase-js in sessionStorage/localStorage
```

**Auth guard in dashboard layout:**
```typescript
// apps/web/src/app/(dashboard)/layout.tsx — add to existing layout
// Check supabase.auth.getSession() on mount; if null, router.push('/auth/login')
// Skeleton while checking (avoids flash)
```

**Callback route handler:**
```typescript
// apps/web/src/app/auth/callback/route.ts
import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: Request) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  if (code) {
    await supabase.auth.exchangeCodeForSession(code)
  }
  return NextResponse.redirect(new URL('/', request.url))
}
```

### New FastAPI Endpoints for Phase 6 Widgets

Two new endpoints are needed to expose Phase 6 data outside the copilot context:

```python
# GET /api/v1/markets/dislocation?market_id=X&venue_ids=kalshi,polymarket
# Returns: { consensus_prob, scores: [{venue_id, mid_prob, disloc_bps, is_stale}] }
# Source: call get_venue_dislocation tool logic directly (not via copilot)

# GET /api/v1/bankroll/exposure
# Returns: { total_exposure, bankroll, venues: [{venue_id, exposure, utilization_pct}] }
# Source: ExposureBook singleton from venue_adapters.exposure
```

These are thin wrappers around the same logic that powers the copilot tools. The copilot tool code in `venue_tools.py` can be imported directly.

### Flutter AppState v1 Migration Pattern

```dart
// Current (stub routes):
Future.wait([
  _api.getValuePlays(),       // /api/value-plays
  _api.getArbitrageOpportunities(),   // /api/arbitrage
  _api.getLineMovements(),    // /api/line-movements
  _api.getBankroll(),         // /api/bankroll
])

// Target (v1 routes with auth):
Future.wait([
  _api.getValuePlaysV1(token: _authToken),    // /api/v1/value-plays
  _api.getPmCorrelation(token: _authToken),   // /api/v1/prediction-markets/correlation
  _api.getLineMovement(token: _authToken),    // /api/v1/line-movement
  _api.simulateBankroll(...),                 // /api/v1/bankroll/simulate (already v1)
])
```

AppState needs `_authToken` passed into `refresh()` to forward JWT.

### Supabase RLS Real-Token Test Pattern

Current RLS tests mock Supabase entirely. The WIRE-03 requirement asks for real RLS verification. Acceptable test fixture strategies (Claude's discretion):

**Strategy A — pytest with real Supabase test project:**
```python
# conftest.py — create a real test user JWT via Supabase REST API
import httpx
@pytest.fixture
def user_jwt():
    r = httpx.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                   json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                   headers={"apikey": SUPABASE_ANON_KEY})
    return r.json()["access_token"]
```

**Strategy B — service_role + explicit RLS assertions:**
Use service_role to insert rows for user A, then verify user B's JWT cannot read them. This is documented as acceptable in the Supabase testing guide.

**Recommendation (Claude's discretion):** Strategy B — service_role fixtures with cross-user isolation assertions. Faster in CI, no real user account management required.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Supabase session management | Custom JWT store/refresh | `supabase.auth.getSession()` + `onAuthStateChange()` | Handles token refresh, persistence, multi-tab sync automatically |
| FCM send loop | Custom HTTP to FCM v1 API | `firebase_admin.messaging.send()` (already in value_scanner_job.py) | Handles APNs bridging, token validation, error codes |
| SSE streaming parse | Manual EventSource / custom buffer | Existing `fetch().body.getReader()` pattern in chat-stream.tsx | Already handles backpressure, line-splitting; EventSource can't POST |
| Offline cache | Custom file serialization | SharedPreferences with `jsonEncode()` | `shared_preferences` handles async, thread-safe writes; already a standard Flutter dep |
| RLS enforcement | Custom row filtering in FastAPI | Supabase RLS policies in SQL + JWT-scoped queries | Supabase enforces at DB level regardless of API bugs |
| Biometric auth | Custom platform channel | `local_auth` package (already in pubspec.yaml) | Platform-specific Face ID/fingerprint, handles fallback to PIN |

---

## Common Pitfalls

### Pitfall 1: Dashboard Layout Auth Guard Causes Flash of Unauthenticated Content
**What goes wrong:** Layout renders children before session check resolves, causing a flash of the dashboard.
**Why it happens:** `getSession()` is async; layout renders synchronously first.
**How to avoid:** Render a loading state (skeleton or null) while session check is pending.
**Warning signs:** Users see dashboard content for <500ms before redirect.

### Pitfall 2: Flutter `ApiService._baseUrl` Is Compile-Time Constant
**What goes wrong:** Changing the default URL at runtime has no effect.
**Why it happens:** `String.fromEnvironment` is resolved at compile time, not runtime.
**How to avoid:** Must pass `--dart-define=API_BASE_URL=...` at build time. No environment file approach.
**Warning signs:** App always hits localhost despite config changes.

### Pitfall 3: Copilot Tools Need Auth Token for User-Context Tools
**What goes wrong:** `get_active_bets` returns empty or wrong data because no user JWT is passed to the copilot endpoint.
**Why it happens:** `POST /api/v1/copilot/chat` is a public endpoint (no `CurrentUser` dependency); the tools inside query Supabase with the service_role key which bypasses RLS, or return demo data.
**How to avoid:** Pass `Authorization` header from both `chat-stream.tsx` and `copilot_screen.dart`; add optional auth to copilot endpoint to thread user context into tool calls.
**Warning signs:** `get_active_bets` returns the same data regardless of which user is logged in.

### Pitfall 4: `@supabase/ssr` vs `@supabase/supabase-js` Mismatch
**What goes wrong:** The Supabase SSR docs recommend `@supabase/ssr` for Next.js App Router, but the project uses `@supabase/supabase-js` v2 directly.
**Why it happens:** Two valid approaches; mixing them causes duplicate sessions or middleware conflicts.
**How to avoid:** Stay with `@supabase/supabase-js` (existing project choice). Do not add `@supabase/ssr`. The existing pattern in `page.tsx` works correctly for client-side auth.
**Warning signs:** Two separate session stores, or auth cookie conflicts.

### Pitfall 5: ExposureBook Singleton Loses State on Server Restart
**What goes wrong:** The `_EXPOSURE_BOOK` module-level singleton in `venue_tools.py` initializes with `bankroll` from env but has no positions loaded from Supabase.
**Why it happens:** The singleton is in-memory only; `add_position()` calls don't persist.
**How to avoid:** For the `/api/v1/bankroll/exposure` endpoint, either: (a) query ledger_entries to reconstruct current positions on each request, or (b) document that the widget shows the live in-memory state which is only accurate within a single server process lifetime.
**Warning signs:** Exposure shows 0 across all venues after every deploy.

### Pitfall 6: Flutter ArbitrageScreen and LineMovementScreen Read from AppState Without Auth Token
**What goes wrong:** Screens read `state.arbitrage` and `state.lineMovements` from `AppState`, which are populated by `AppState.refresh()`. But `refresh()` currently uses unauthenticated stub routes.
**Why it happens:** `AppState` was designed before v1 auth endpoints existed.
**How to avoid:** Pass `authToken` into `AppState.refresh()` or have `AppState` read it from `AuthService.currentToken`.
**Warning signs:** Arbitrage and line movement screens always show empty state or error after migrating to v1 endpoints that require auth.

### Pitfall 7: SnapshotStore / LedgerStore in-memory in CI
**What goes wrong:** WIRE-03 verification shows SnapshotStore and LedgerStore "working with Supabase" but they silently fall back to in-memory if env vars absent.
**Why it happens:** The dual-mode pattern is designed for graceful fallback; same code path used in tests.
**How to avoid:** Integration test must assert `_supabase is not None` by requiring env vars, or use a Supabase test project with real credentials.
**Warning signs:** All WIRE-03 tests pass in CI but SnapshotStore is actually writing to dict, not Postgres.

---

## Code Examples

### Web Login Page (verified against existing supabase.ts)
```typescript
// Source: pattern from apps/web/src/app/(dashboard)/page.tsx supabase.auth.getSession()
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      router.push('/')
    }
  }
  // ... form JSX
}
```

### Web Dashboard Auth Guard
```typescript
// Source: pattern from apps/web/src/app/(dashboard)/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) router.replace('/auth/login')
      else setChecking(false)
    })
  }, [router])

  if (checking) return <div className="min-h-screen bg-zinc-950" /> // skeleton
  return <>{children}</>
}
```

### New FastAPI Exposure Endpoint
```python
# Source: mirrors existing pattern in apps/webhook_server/src/sharpedge_webhooks/routes/v1/bankroll.py
from fastapi import APIRouter
router = APIRouter(tags=["v1"])

@router.get("/bankroll/exposure")
async def get_exposure() -> dict:
    """Get current ExposureBook state. Public read endpoint."""
    from sharpedge_agent_pipeline.copilot.venue_tools import get_exposure_status
    return get_exposure_status.invoke({"venue_id": ""})
```

### Flutter AppState refresh with auth token
```dart
// Source: existing pattern in apps/mobile/lib/providers/app_state.dart
Future<void> refresh() async {
  loading = true;
  error = null;
  notifyListeners();
  try {
    // Use authToken if available for v1 endpoints
    final token = _authToken;
    final results = await Future.wait([
      _api.getValuePlaysV1(token: token),
      _api.getPmCorrelation(token: token),
      _api.getLineMovement(token: token),
    ]);
    valuePlays = results[0] as List<ValuePlayV1>;
    // ...
  } catch (e) {
    error = e.toString();
  } finally {
    loading = false;
    notifyListeners();
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `apps/web/src/app/(dashboard)/page.tsx` had empty string token placeholder | Token now sourced from `supabase.auth.getSession()` (already done in Phase 4) | Portfolio page correctly passes real JWT |
| `@supabase/auth-helpers-nextjs` (deprecated) | `@supabase/supabase-js` v2 direct (project choice) | No middleware required for client-side auth |
| Flutter `ApiService` all stub routes | Has both old stub methods AND v1 methods; old methods still called from `AppState.refresh()` | Must migrate refresh() to v1 methods |
| FCM token registered on Discord alert | FCM registered in `_ShellState.initState()` via `addPostFrameCallback` | Already correct per Phase 4 design |
| Discord fired before FCM | FCM `send_fcm_notifications_for_play()` called first, then `_pending_value_alerts.append()` | Already correct in value_scanner_job.py |

---

## Open Questions

1. **ExposureBook singleton persistence across requests**
   - What we know: `_EXPOSURE_BOOK` is module-level in `venue_tools.py`; starts empty each process restart
   - What's unclear: Should `/api/v1/bankroll/exposure` reconstruct from `ledger_entries` or serve live in-memory state?
   - Recommendation: Serve in-memory state with a note in UI ("reflects current session positions"); full ledger reconstruction is Phase 9 scope

2. **Session context in copilot — how to pass user token**
   - What we know: `POST /api/v1/copilot/chat` is public; tools query Supabase with service_role or return mock data
   - What's unclear: Should the copilot endpoint add an optional `Authorization` header and thread user_id into tool calls?
   - Recommendation: Add optional `CurrentUser` to copilot endpoint; if present, inject user_id into tool state; tools that need user data (get_active_bets, get_portfolio_stats) then use it

3. **PM correlation endpoint contract for ArbitrageScreen**
   - What we know: `ArbitrageScreen` shows `List<ArbitrageOpportunity>` (event, market, profitPercent, legs)
   - What's unclear: The PM correlation scanner returns `CorrelationWarning` objects, not arbitrage legs
   - Recommendation: The screen should be repurposed to show PM correlation warnings, or a new PM arbitrage endpoint created; the `ArbitrageOpportunity` model maps reasonably to cross-venue dislocation opportunities

4. **Supabase RLS test environment**
   - What we know: Current tests mock Supabase entirely; WIRE-03 requires real RLS verification
   - What's unclear: Is there a Supabase test project already configured?
   - Recommendation: If no test project, use service_role + cross-user isolation assertion pattern (Strategy B above); document the approach in test file headers

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (web) | Vitest + @testing-library/react (jsdom) |
| Config file (web) | `apps/web/vitest.config.ts` |
| Quick run (web) | `cd apps/web && npm test` |
| Full suite (web) | `cd apps/web && npm test -- --run` |
| Framework (Python) | pytest (existing across webhook_server + venue_adapters) |
| Quick run (Python) | `cd apps/webhook_server && python -m pytest tests/ -x -q` |
| Full suite (Python) | `uv run pytest apps/webhook_server/tests/ packages/venue_adapters/tests/ -q` |
| Framework (Flutter) | `flutter test` |
| Quick run (Flutter) | `cd apps/mobile && flutter test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIRE-01 | Web login page renders and calls `signInWithPassword` | unit | `cd apps/web && npm test -- src/test/auth.test.tsx` | ❌ Wave 0 |
| WIRE-01 | Dashboard layout redirects unauthenticated user | unit | `cd apps/web && npm test -- src/test/auth-guard.test.tsx` | ❌ Wave 0 |
| WIRE-01 | FastAPI `get_current_user` rejects cross-user portfolio access | unit | `cd apps/webhook_server && python -m pytest tests/unit/api/test_rls.py -x` | ✅ (partial — mock only) |
| WIRE-01 | FastAPI `get_current_user` rejects missing/invalid JWT | unit | `cd apps/webhook_server && python -m pytest tests/unit/api/test_rls.py -x` | ✅ |
| WIRE-02 | Venue dislocation widget renders with real data shape | unit | `cd apps/web && npm test -- src/test/venue-dislocation.test.tsx` | ❌ Wave 0 |
| WIRE-02 | Exposure widget renders utilization bars | unit | `cd apps/web && npm test -- src/test/exposure-widget.test.tsx` | ❌ Wave 0 |
| WIRE-02 | `GET /api/v1/markets/dislocation` returns correct schema | unit | `cd apps/webhook_server && python -m pytest tests/unit/api/test_dislocation_endpoint.py -x` | ❌ Wave 0 |
| WIRE-02 | `GET /api/v1/bankroll/exposure` returns correct schema | unit | `cd apps/webhook_server && python -m pytest tests/unit/api/test_exposure_endpoint.py -x` | ❌ Wave 0 |
| WIRE-03 | SnapshotStore writes to Supabase when env vars present | integration | `uv run pytest packages/venue_adapters/tests/test_snapshot_store.py -k supabase -x` | ❌ Wave 0 |
| WIRE-03 | LedgerStore writes to `ledger_entries` table | integration | `uv run pytest packages/venue_adapters/tests/test_settlement_ledger.py -k supabase -x` | ❌ Wave 0 |
| WIRE-04 | Flutter `ApiService.getValuePlaysV1()` used in AppState.refresh | unit | `cd apps/mobile && flutter test test/app_state_test.dart` | ❌ Wave 0 |
| WIRE-04 | Flutter offline cache: last feed shown when network fails | unit | `cd apps/mobile && flutter test test/offline_cache_test.dart` | ❌ Wave 0 |
| WIRE-04 | `GET /api/v1/prediction-markets/correlation` returns ArbitrageOpportunity schema | unit | `cd apps/webhook_server && python -m pytest tests/unit/api/test_pm_correlation_endpoint.py -x` | ❌ Wave 0 |
| WIRE-05 | FCM `send_fcm_notifications_for_play` called before Discord dispatch | unit | `cd apps/bot && python -m pytest tests/ -k fcm_before_discord -x` | ❌ Wave 0 |
| WIRE-06 | All 12 tools in COPILOT_TOOLS list | unit | `uv run pytest packages/agent_pipeline/tests/ -k copilot_tools_count -x` | ❌ Wave 0 |
| WIRE-06 | Copilot SSE streams from Flutter (CopilotScreen) | manual | Physical device verification | N/A |
| WIRE-06 | 10+ turn conversation stays within context window | unit | `uv run pytest packages/agent_pipeline/tests/ -k trim_conversation -x` | ✅ (existing) |

### Sampling Rate
- **Per task commit:** Run the specific test file for the changed component
- **Per wave merge:** Full suite for modified package (`npm test --run` for web; `uv run pytest` for Python)
- **Phase gate:** All test files listed above must be green before `/gsd:verify-work`

### Wave 0 Gaps (Files to Create Before Implementation)
- [ ] `apps/web/src/test/auth.test.tsx` — covers WIRE-01 login page
- [ ] `apps/web/src/test/auth-guard.test.tsx` — covers WIRE-01 dashboard guard
- [ ] `apps/web/src/test/venue-dislocation.test.tsx` — covers WIRE-02 dislocation widget
- [ ] `apps/web/src/test/exposure-widget.test.tsx` — covers WIRE-02 exposure widget
- [ ] `apps/webhook_server/tests/unit/api/test_dislocation_endpoint.py` — covers WIRE-02
- [ ] `apps/webhook_server/tests/unit/api/test_exposure_endpoint.py` — covers WIRE-02
- [ ] `apps/webhook_server/tests/unit/api/test_pm_correlation_endpoint.py` — covers WIRE-04
- [ ] `packages/venue_adapters/tests/test_snapshot_store.py` — add supabase-mode tests (covers WIRE-03)
- [ ] `apps/mobile/test/app_state_test.dart` — covers WIRE-04 AppState v1 migration
- [ ] `apps/mobile/test/offline_cache_test.dart` — covers WIRE-04 offline degradation
- [ ] `apps/bot/tests/test_fcm_ordering.py` — covers WIRE-05 FCM-before-Discord
- [ ] `packages/agent_pipeline/tests/test_copilot_tools_count.py` — covers WIRE-06 12-tool assertion

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `apps/web/src/lib/supabase.ts` — Supabase client setup; `@supabase/supabase-js` v2.45.0
- `apps/web/src/app/(dashboard)/page.tsx` — confirmed working auth pattern with `getSession()` + `onAuthStateChange`
- `apps/web/src/lib/api.ts` — all v1 API calls with `Authorization: Bearer ${token}`
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/deps.py` — FastAPI `get_current_user` dependency
- `apps/webhook_server/src/sharpedge_webhooks/routes/v1/notifications.py` — FCM device token registration endpoint
- `apps/bot/src/sharpedge_bot/jobs/value_scanner_job.py` — FCM fires before Discord; confirmed at lines 334–337
- `apps/mobile/lib/main.dart` — FCM `registerToken` in `_ShellState.initState()` at lines 141–151
- `apps/mobile/lib/services/api_service.dart` — `_baseUrl` is `String.fromEnvironment`; old stub routes still called from `AppState`
- `apps/mobile/lib/providers/app_state.dart` — `refresh()` calls old stub routes
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` — `COPILOT_TOOLS = [...] + VENUE_TOOLS` at lines 438–449
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/venue_tools.py` — `get_venue_dislocation`, `get_exposure_status`, `VENUE_TOOLS`
- `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — LedgerStore dual-mode confirmed
- `packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py` — SnapshotStore dual-mode confirmed
- `.planning/config.json` — `nyquist_validation: true` confirmed

### Secondary (MEDIUM confidence — inferred from existing patterns)
- SharedPreferences recommendation for Flutter offline cache — standard Flutter ecosystem choice; consistent with project simplicity preference
- Strategy B (service_role + cross-user isolation) for RLS testing — established Supabase testing pattern

### Tertiary (LOW confidence)
- None — all claims verified directly from codebase

---

## Metadata

**Confidence breakdown:**
- Current codebase state: HIGH — every file directly inspected
- Missing components inventory: HIGH — confirmed absent via `find` + file reads
- Standard stack: HIGH — versions read from package.json and pubspec.yaml
- Architecture patterns: HIGH — derived from existing working code in same project
- Pitfalls: HIGH — identified from actual code anti-patterns found during audit

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack; no fast-moving dependencies)
