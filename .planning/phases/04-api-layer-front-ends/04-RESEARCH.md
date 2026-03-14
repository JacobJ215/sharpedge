# Phase 4: API Layer + Front-Ends - Research

**Researched:** 2026-03-14
**Domain:** FastAPI SSE, Supabase RLS, Next.js 14 App Router, Flutter FCM/biometrics
**Confidence:** HIGH (core patterns), MEDIUM (RLS SQL specifics), HIGH (Flutter packages)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Mobile tech stack:**
- Keep Flutter — `apps/mobile/` is already a Flutter project; continue with it, do not switch to Expo
- Wire all Phase 1–3 backend enhancements into the existing Flutter app
- Full scope: all 5 mobile requirements (MOB-01 through MOB-05) in this phase
- Push notifications via Firebase Cloud Messaging (FCM) — `firebase_messaging` package, iOS APNs + Android FCM
- Swipe-to-log flow (MOB-01): swipe right opens a bottom sheet pre-filled with recommended Kelly stake and book; user adjusts if needed, taps Confirm — minimal friction
- The Flutter app has its own Dart HTTP layer; no shared TypeScript client with web

**FastAPI app structure:**
- Extend the existing webhook server (`apps/webhook_server/`) with a new `/api/v1/` prefix — do NOT create a separate service
- Add `routes/v1/` directory inside `apps/webhook_server/`
- Old `/api/value-plays`, `/api/bankroll` etc. stay as-is for Flutter backward compat during transition; new `/api/v1/*` endpoints run alongside
- SSE streaming for copilot: `StreamingResponse` with `text/event-stream` content type — FastAPI yields LangGraph tokens as SSE events. No WebSocket.
- New `/api/v1/value-plays`: returns `alpha_score`, `alpha_badge` (PREMIUM/HIGH/MEDIUM/SPECULATIVE), `regime_state` alongside existing EV/odds fields; supports `min_alpha` filter parameter

**Auth & RLS pattern:**
- Supabase JWT as the auth mechanism — frontend authenticates with Supabase (email/password), gets JWT, sends as `Authorization: Bearer` header
- FastAPI verifies JWT via `supabase.auth.get_user(token)` and passes it through to queries — RLS activates automatically
- Auth dependency pattern: reusable `get_current_user` FastAPI `Depends()` injected into protected routes; raises HTTP 401 on invalid/missing token
- RLS scope: ALL tables in the schema (max security) — shared game data tables use `service_role` key for bot/job writes; user-scoped queries use user JWT
- Value plays and game analysis endpoints are public (no auth required); portfolio and bankroll endpoints require `get_current_user`

**Web dashboard:**
- Location: `apps/web/` — create from scratch with Next.js 14 App Router + TypeScript
- UI stack: Tailwind CSS + shadcn/ui for components, Recharts for all charts
- Data freshness: polling on key pages — value plays page auto-refreshes every 60 seconds via SWR/React Query; portfolio/bankroll refresh on demand; copilot page is live via SSE
- Value plays page (WEB-02): shadcn `DataTable` with sortable columns — alpha badge as colored pill, regime state as small chip, EV%, book, game. Dense/scannable, trading terminal feel
- Monte Carlo fan chart (WEB-04): Recharts `AreaChart` — three layers: shaded P5–P95 band (risk range), solid P50 line (expected path), P5 floor line (ruin scenario)
- Supabase client in Next.js for auth — user signs in with Supabase, JWT forwarded to FastAPI for protected endpoints

### Claude's Discretion
- Exact shadcn/ui component selection per page
- Recharts color palette and theme for charts
- CORS configuration for Next.js ↔ FastAPI communication
- Exact Supabase RLS policy SQL for each table
- Flutter screen layout details beyond the defined interactions
- FCM setup steps and Firebase project configuration details
- API error response format/schema

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| API-01 | FastAPI GET /api/v1/value-plays with min_alpha filter, alpha-ranked | `enrich_with_alpha()` + `rank_by_alpha()` already exist; new route reads from `value_plays` table ordered by `alpha_score` desc |
| API-02 | FastAPI GET /api/v1/games/:id/analysis returning full analysis state | `BettingAnalysisState` from Phase 2 graph is the response model; fetch from Supabase or run graph on demand |
| API-03 | FastAPI POST /api/v1/copilot/chat SSE streaming BettingCopilot responses | `build_copilot_graph()` + `astream_events()` → `StreamingResponse(text/event-stream)` |
| API-04 | FastAPI GET /api/v1/users/:id/portfolio returning ROI, win rate, CLV, drawdown, active bets | `get_performance_summary()`, `get_clv_summary()`, `get_pending_bets()` already exist in `sharpedge_db.queries.bets` |
| API-05 | FastAPI POST /api/v1/bankroll/simulate returning Monte Carlo result | `simulate_bankroll()` in `sharpedge_models.monte_carlo` — wrap as JSON endpoint |
| API-06 | Supabase RLS enabled for all user-scoped tables before any API route is wired | SQL `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY ... USING (auth.uid() = user_id)` |
| WEB-01 | Dashboard page: ROI curve, win rate, CLV trend, bankroll curve, active bets | Recharts LineChart for ROI/CLV, Recharts AreaChart for bankroll; SWR polls /api/v1/users/:id/portfolio |
| WEB-02 | Value plays page: live alpha-ranked with regime indicator and alpha badge | shadcn DataTable + TanStack Table sorting; `refreshInterval: 60000` in SWR |
| WEB-03 | Game detail page: model prediction, EV breakdown, regime state, key number proximity | GET /api/v1/games/:id/analysis → render BettingAnalysisState fields |
| WEB-04 | Bankroll page: Monte Carlo fan chart (P5/P50/P95), Kelly calculator, exposure limits | Recharts AreaChart with 3 Area layers (P5–P95 band, P50 line, P5 floor) |
| WEB-05 | Copilot page: streaming chat interface with BettingCopilot | SSE EventSource → React state accumulation; shadcn Input + ScrollArea |
| WEB-06 | Prediction markets page: Kalshi/Polymarket edge dashboard with regime classification | GET /api/v1/value-plays with PM filter; PM regime chip per row |
| MOB-01 | Feed screen: live alpha-ranked value plays with swipe-right to log bet | Flutter DismissibleWidget + BottomSheet; GET /api/v1/value-plays |
| MOB-02 | Copilot screen: BettingCopilot chat interface | Dart HTTP SSE client; POST /api/v1/copilot/chat |
| MOB-03 | Portfolio screen: bet tracker and performance stats | GET /api/v1/users/:id/portfolio |
| MOB-04 | Push notifications: PREMIUM/HIGH alpha alerts before Discord fires | firebase-admin python `send_each_for_multicast()` in value_scanner_job.py BEFORE Discord dispatch |
| MOB-05 | App uses biometric auth (Face ID / fingerprint) | `local_auth` ^2.1.6 Flutter package; `authenticateWithBiometrics()` at app launch |
</phase_requirements>

---

## Summary

Phase 4 surfaces Phase 1–3 intelligence through three delivery channels: a REST/SSE FastAPI layer added to the existing webhook server, a greenfield Next.js 14 web dashboard, and backend-enhanced Flutter mobile app. The critical sequencing constraint is Supabase RLS enablement (API-06) before any user-scoped route is wired — this is a one-time schema migration that must be Wave 0.

The existing codebase provides most of the data layer: `get_performance_summary()`, `get_clv_summary()`, `get_pending_bets()`, `simulate_bankroll()`, `enrich_with_alpha()`, and `rank_by_alpha()` are all implemented and tested. The LangGraph `build_copilot_graph()` is compiled and ready. The primary implementation work is: (1) writing FastAPI route handlers that wire these functions together behind JWT auth, (2) the Next.js 14 App Router scaffolding with Supabase SSR auth and SWR data fetching, and (3) Flutter service layer updates with FCM and biometric auth.

The key technical gotcha is supabase-py RLS activation: the service_role singleton client in `sharpedge_db/client.py` bypasses RLS by design. User-scoped API routes must create a per-request client using the user JWT — not reuse the global service_role client — for RLS policies to activate.

**Primary recommendation:** Wave 0 = RLS migration + FCM token storage table + Next.js scaffold. Wave 1 = public FastAPI v1 routes (value-plays, games, bankroll). Wave 2 = protected routes (portfolio) + Flutter service updates. Wave 3 = SSE copilot + web/mobile copilot screens.

---

## Standard Stack

### Core (FastAPI — backend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | already installed | APIRouter with prefix/tags | existing pattern in mobile.py |
| uvicorn | already installed | ASGI server | existing; StreamingResponse requires ASGI |
| supabase-py | already installed | Supabase client + auth.get_user() | existing singleton in sharpedge_db/client.py |
| python-jose or PyJWT | verify against existing requirements | JWT decode if doing local verify | fallback if supabase.auth.get_user() is too slow |
| firebase-admin | ^6.x (PyPI: firebase-admin) | send FCM push notifications from Python | official Google SDK; HTTP v1 API |

### Core (Next.js — web)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 14.x | App Router, Server Components, Route Handlers | locked decision |
| @supabase/ssr | ^0.5.x | SSR-safe Supabase client with cookie handling | official package; replaces deprecated @supabase/auth-helpers |
| @supabase/supabase-js | ^2.x | Browser Supabase client | paired with @supabase/ssr |
| swr | ^2.x | Client-side polling with refreshInterval | locked decision; `refreshInterval: 60000` for value plays |
| recharts | ^2.x | AreaChart, LineChart for all dashboards | locked decision |
| @tanstack/react-table | ^8.x | Powers shadcn DataTable sorting | shadcn's table component requires it |
| shadcn/ui | CLI-based | DataTable, Card, Badge, Input, ScrollArea | locked decision |
| tailwindcss | ^3.x | utility CSS | locked; paired with shadcn |

### Core (Flutter — mobile)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| firebase_messaging | ^15.x | FCM push notifications (foreground + background) | locked decision; iOS APNs bridge |
| flutter_local_notifications | ^17.x | Foreground notification display on iOS | FCM foreground on iOS requires this |
| local_auth | ^2.1.6 | Face ID / fingerprint biometric auth | locked for MOB-05 |
| flutter_secure_storage | ^9.x | Store user JWT securely after biometric gate | companion to local_auth pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | ^0.27 | Async HTTP client from FastAPI to Supabase if needed | if supabase-py sync client causes issues in async context |
| pydantic | ^2.x | Request/response models on v1 routes | already in FastAPI ecosystem |
| python-dotenv | already likely installed | env var loading | already used in config.py |

**Installation (FastAPI additions):**
```bash
pip install firebase-admin
```

**Installation (Next.js):**
```bash
npx create-next-app@14 apps/web --typescript --tailwind --app
cd apps/web
npx shadcn@latest init
npm install @supabase/ssr @supabase/supabase-js swr recharts @tanstack/react-table
npx shadcn@latest add table badge card input scroll-area
```

**Installation (Flutter additions to pubspec.yaml):**
```yaml
dependencies:
  firebase_core: ^3.x
  firebase_messaging: ^15.x
  flutter_local_notifications: ^17.x
  local_auth: ^2.1.6
  flutter_secure_storage: ^9.x
```

---

## Architecture Patterns

### FastAPI v1 Route Structure
```
apps/webhook_server/src/sharpedge_webhooks/
├── routes/
│   ├── mobile.py          # existing — keep as-is (backward compat)
│   ├── whop.py            # existing
│   └── v1/
│       ├── __init__.py    # exports router = APIRouter(prefix="/api/v1", tags=["v1"])
│       ├── deps.py        # get_current_user Depends(); per-request user client
│       ├── value_plays.py # GET /api/v1/value-plays
│       ├── games.py       # GET /api/v1/games/{game_id}/analysis
│       ├── copilot.py     # POST /api/v1/copilot/chat (SSE)
│       ├── portfolio.py   # GET /api/v1/users/{user_id}/portfolio
│       └── bankroll.py    # POST /api/v1/bankroll/simulate
```

### Next.js 14 App Structure
```
apps/web/
├── app/
│   ├── layout.tsx             # root layout with Supabase provider
│   ├── middleware.ts           # session refresh via @supabase/ssr
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx         # protected layout; redirect if no session
│   │   ├── page.tsx           # WEB-01: portfolio overview
│   │   ├── plays/page.tsx     # WEB-02: value plays DataTable
│   │   ├── games/[id]/page.tsx # WEB-03: game detail
│   │   ├── bankroll/page.tsx  # WEB-04: Monte Carlo fan chart
│   │   ├── copilot/page.tsx   # WEB-05: SSE chat
│   │   └── markets/page.tsx   # WEB-06: PM dashboard
│   └── api/
│       └── auth/callback/route.ts  # Supabase OAuth callback
├── lib/
│   ├── supabase/
│   │   ├── client.ts          # createBrowserClient()
│   │   └── server.ts          # createServerClient() with cookie helpers
│   └── api.ts                 # fetch wrappers that inject Bearer token
└── components/
    ├── value-plays-table.tsx  # "use client" + SWR + shadcn DataTable
    ├── monte-carlo-chart.tsx  # "use client" + Recharts AreaChart
    └── copilot-chat.tsx       # "use client" + EventSource SSE
```

### Flutter App Extension Pattern
```
apps/mobile/lib/
├── main.dart
├── models/          # existing — add AlphaPlay, PortfolioStats models
├── providers/       # existing — add PlayProvider, PortfolioProvider, CopilotProvider
├── screens/
│   ├── feed_screen.dart      # MOB-01: existing or new; alpha plays + swipe
│   ├── copilot_screen.dart   # MOB-02: SSE chat with copilot
│   ├── portfolio_screen.dart # MOB-03: stats + bet history
│   └── ...
├── services/
│   ├── api_service.dart      # update base URL to /api/v1, inject auth token
│   ├── fcm_service.dart      # new: init firebase_messaging, request perms
│   └── biometric_service.dart # new: local_auth wrapper
└── widgets/
    └── bet_log_bottom_sheet.dart  # new: MOB-01 swipe-right bottom sheet
```

---

### Pattern 1: FastAPI Auth Dependency (get_current_user)

**What:** Reusable FastAPI dependency that validates the Bearer JWT via Supabase and returns the authenticated user object. All protected routes inject this.

**Critical:** Do NOT reuse the global `get_supabase_client()` (service_role) for user-scoped queries. Create a per-request client with the user JWT so PostgREST activates RLS.

```python
# apps/webhook_server/src/sharpedge_webhooks/routes/v1/deps.py
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate JWT and return user dict. Raises 401 on failure."""
    token = credentials.credentials
    # Use anon key client to validate token — service_role bypasses RLS
    url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_KEY"]  # anon/public key
    client: Client = create_client(url, anon_key)
    try:
        response = client.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"user": response.user, "jwt": token}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")

def get_user_client(current_user: dict = Depends(get_current_user)) -> Client:
    """Return a Supabase client authenticated as the current user (activates RLS)."""
    url = os.environ["SUPABASE_URL"]
    anon_key = os.environ["SUPABASE_KEY"]
    client = create_client(url, anon_key)
    # Set the session so PostgREST uses user JWT → RLS activates
    client.auth.set_session(current_user["jwt"], "")
    return client
```

### Pattern 2: FastAPI SSE with LangGraph astream_events()

**What:** POST /api/v1/copilot/chat streams BettingCopilot responses as SSE. `astream_events(version="v2")` yields typed event dicts; filter for `on_chat_model_stream` to get token chunks.

**Critical:** The endpoint handler must be `async def`. SSE requires `StreamingResponse` with `media_type="text/event-stream"`. Each message must end with `\n\n`.

```python
# apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph

router = APIRouter()

class CopilotRequest(BaseModel):
    message: str
    user_id: str

async def _event_generator(message: str):
    """Yield SSE-formatted tokens from LangGraph astream_events."""
    graph = build_copilot_graph()
    input_state = {"messages": [{"role": "user", "content": message}]}
    async for event in graph.astream_events(input_state, version="v2"):
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", {})
            content = getattr(chunk, "content", "") or ""
            if content:
                payload = json.dumps({"token": content})
                yield f"data: {payload}\n\n"
    yield "data: {\"done\": true}\n\n"

@router.post("/copilot/chat")
async def copilot_chat(request: CopilotRequest):
    return StreamingResponse(
        _event_generator(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
```

### Pattern 3: Supabase RLS SQL Migrations

**What:** Enable RLS on each table and create user-scoped policies. Service_role key (already in `SUPABASE_SERVICE_KEY` env var) bypasses RLS automatically for bot/job writes.

```sql
-- Enable RLS on all user-scoped tables
ALTER TABLE bets ENABLE ROW LEVEL SECURITY;
ALTER TABLE bankroll_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
-- (shared game tables like value_plays, games stay readable by all — public policy)

-- User-scoped SELECT: user sees only their rows
CREATE POLICY "user_read_own_bets"
ON bets FOR SELECT
USING ((SELECT auth.uid()) = user_id);

-- User-scoped INSERT: user can insert their own bets
CREATE POLICY "user_insert_own_bets"
ON bets FOR INSERT
WITH CHECK ((SELECT auth.uid()) = user_id);

-- Service role bypasses RLS automatically — no policy needed for bot writes
-- Bot uses SUPABASE_SERVICE_KEY which activates the service_role Postgres role
```

**Note:** `value_plays` is a shared table written by the bot (service_role) and read publicly. Enable RLS with a public SELECT policy:
```sql
ALTER TABLE value_plays ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_value_plays"
ON value_plays FOR SELECT USING (true);
-- Bot INSERT uses service_role — bypasses RLS automatically
```

### Pattern 4: Next.js Supabase SSR Auth + JWT Forwarding

**What:** `@supabase/ssr` provides `createServerClient` (Server Components, Route Handlers) and `createBrowserClient` (Client Components). Middleware refreshes sessions. JWT is extracted from the Supabase session to forward to FastAPI.

```typescript
// apps/web/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request })
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options))
        },
      },
    }
  )
  await supabase.auth.getUser()  // refreshes session
  return response
}
```

```typescript
// apps/web/lib/api.ts — forward user JWT to FastAPI protected routes
export async function apiFetch(path: string, options?: RequestInit) {
  // Call from a Server Component or Route Handler with the session
  const { createServerClient } = await import('@supabase/ssr')
  // ... create client with cookies
  const { data: { session } } = await supabase.auth.getSession()
  const jwt = session?.access_token
  return fetch(`${process.env.FASTAPI_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
      ...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
      'Content-Type': 'application/json',
    },
  })
}
```

### Pattern 5: SWR Polling for Value Plays (60s)

**What:** Client Component wraps the value plays DataTable in SWR with 60-second refresh interval. The fetcher hits the FastAPI v1 endpoint directly (public, no auth required for value plays).

```typescript
// apps/web/components/value-plays-table.tsx
'use client'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export function ValuePlaysTable() {
  const { data, error, isLoading } = useSWR(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/value-plays`,
    fetcher,
    { refreshInterval: 60_000 }
  )
  // render shadcn DataTable with TanStack sorting
}
```

### Pattern 6: Recharts Monte Carlo Fan Chart (WEB-04)

**What:** Three `<Area>` components on the same `<AreaChart>`. The P5–P95 band uses a semi-transparent fill between P5 and P95; P50 is a solid line; P5 floor uses a dashed stroke.

**Approach:** Structure data as `{ time: number, p5: number, p50: number, p95: number }[]`. Use `stackId` carefully — do NOT stack these three; they share the same Y axis domain but are separate areas overlaid.

```typescript
// apps/web/components/monte-carlo-chart.tsx
'use client'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function MonteCarloFanChart({ data }: { data: PathPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <XAxis dataKey="bet" />
        <YAxis />
        <Tooltip />
        {/* P5–P95 shaded band — semi-transparent fill */}
        <Area type="monotone" dataKey="p95" stroke="none" fill="#3b82f6" fillOpacity={0.15} />
        {/* P5 floor — dashed stroke, no fill */}
        <Area type="monotone" dataKey="p5" stroke="#ef4444" strokeDasharray="4 4"
              fill="white" fillOpacity={1} />
        {/* P50 median — solid line */}
        <Area type="monotone" dataKey="p50" stroke="#3b82f6" strokeWidth={2} fill="none" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
```

**Note:** To achieve the band effect (fill between P5 and P95), the standard Recharts approach is to render P95 with a fill and then "erase" from below P5 by rendering P5 with `fill="white"` (opaque background). This requires knowing the chart background color. An alternative is using D3 directly for the area band, but that defeats the locked Recharts decision.

### Pattern 7: FCM Trigger from value_scanner_job.py

**What:** Before dispatching Discord alert, send FCM push to registered device tokens for PREMIUM/HIGH alpha plays. Uses `firebase-admin` Python SDK with HTTP v1 API.

```python
# In value_scanner_job.py — before Discord dispatch
import firebase_admin
from firebase_admin import credentials, messaging

def _init_fcm() -> bool:
    """Initialize Firebase Admin SDK once."""
    if not firebase_admin._apps:
        cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
        if not cred_path:
            return False
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return True

async def send_fcm_alert(play: ValuePlay, device_tokens: list[str]) -> None:
    """Send FCM push for PREMIUM/HIGH alpha plays."""
    if not _init_fcm() or not device_tokens:
        return
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=f"{play.alpha_badge} Alert: {play.game}",
            body=f"{play.side} @ {play.sportsbook} | EV: {play.ev_percentage:.1f}%",
        ),
        data={"alpha_badge": play.alpha_badge, "game_id": play.game_id},
        tokens=device_tokens,
    )
    messaging.send_each_for_multicast(message)
```

Device tokens must be stored in Supabase (e.g., `user_device_tokens` table) when the Flutter app registers via `FirebaseMessaging.instance.getToken()`.

### Pattern 8: Flutter Biometric Auth (MOB-05)

**What:** `local_auth` wraps Face ID / fingerprint. Called at app launch before showing any screen. JWT stored in `flutter_secure_storage` (persists across restarts, gated by biometric on retrieval).

```dart
// apps/mobile/lib/services/biometric_service.dart
import 'package:local_auth/local_auth.dart';

class BiometricService {
  final LocalAuthentication _auth = LocalAuthentication();

  Future<bool> authenticate() async {
    final canCheck = await _auth.canCheckBiometrics;
    if (!canCheck) return true; // fallback: allow if no biometrics enrolled
    return _auth.authenticate(
      localizedReason: 'Authenticate to access SharpEdge',
      options: const AuthenticationOptions(biometricOnly: false, stickyAuth: true),
    );
  }
}
```

**iOS config required:** Add `NSFaceIDUsageDescription` to `ios/Runner/Info.plist`.
**Android config required:** `minSdkVersion 23` in `android/app/build.gradle`, add `USE_BIOMETRIC` permission.

### Pattern 9: Flutter SSE for Copilot (MOB-02)

**What:** Dart's `http` package doesn't support SSE natively. Use `http.Client().send()` with a `StreamedResponse` to read SSE lines incrementally. The `copilot_screen.dart` accumulates tokens into a state string.

```dart
// apps/mobile/lib/services/api_service.dart (SSE portion)
Stream<String> streamCopilotResponse(String message, String jwt) async* {
  final client = http.Client();
  final request = http.Request(
    'POST',
    Uri.parse('$_baseUrl/api/v1/copilot/chat'),
  );
  request.headers['Authorization'] = 'Bearer $jwt';
  request.headers['Content-Type'] = 'application/json';
  request.body = jsonEncode({'message': message, 'user_id': _userId});

  final response = await client.send(request);
  await for (final chunk in response.stream.transform(utf8.decoder)) {
    for (final line in chunk.split('\n')) {
      if (line.startsWith('data: ')) {
        final data = jsonDecode(line.substring(6));
        if (data['done'] != true && data['token'] != null) {
          yield data['token'] as String;
        }
      }
    }
  }
  client.close();
}
```

### Anti-Patterns to Avoid

- **Reusing service_role client for user queries:** The singleton `get_supabase_client()` uses `SUPABASE_SERVICE_KEY` which bypasses RLS. Never use it for user-scoped reads — create a per-request client with the user JWT.
- **Synchronous supabase-py calls in async FastAPI endpoints:** `supabase-py` v1/v2 uses sync httpx under the hood. Wrap in `asyncio.to_thread()` or use `httpx.AsyncClient` directly to avoid blocking the event loop.
- **Using `supabase.auth.getSession()` in Next.js Server Components:** Only use `supabase.auth.getUser()` in server context — getSession() is not safe server-side per official docs.
- **Building the copilot graph per SSE request:** `build_copilot_graph()` compiles a StateGraph — do this once at startup or lazily cache it, not on every request.
- **Stacking P5/P50/P95 in Recharts with `stackId`:** Stacking adds values cumulatively (wrong for percentile bands). Overlay instead.
- **FCM after Discord in value_scanner_job.py:** The requirement (MOB-04) is FCM fires BEFORE Discord. The current job's queue-and-dispatch flow must be changed to send FCM inline before queuing the Discord embed.
- **Flutter `DismissibleWidget` as swipe-to-log:** `Dismissible` removes the item from the list on swipe. For bet-logging, swipe should open a BottomSheet without removing the play. Use `GestureDetector` with horizontal drag detection + `showModalBottomSheet()` instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE keep-alive / reconnect | Custom ping loop | `X-Accel-Buffering: no` header + client EventSource auto-reconnect | Browser EventSource reconnects automatically on disconnect |
| JWT validation | Manual JOSE decode | `supabase.auth.get_user(token)` | validates against Supabase's key, handles rotation |
| Biometric auth | Native iOS/Android code | `local_auth` ^2.1.6 | abstracts Face ID + fingerprint across both platforms |
| FCM HTTP v1 calls | Raw HTTP requests | `firebase-admin` Python SDK | handles OAuth2 token refresh for HTTP v1 API |
| DataTable sorting | Custom sort logic | TanStack Table `getSortedRowModel()` via shadcn DataTable | battle-tested; handles multi-column sort, edge cases |
| Supabase session cookies | Manual cookie management | `@supabase/ssr` createServerClient | handles cookie serialization, expiry, refresh automatically |
| Monte Carlo paths data | Per-request simulation on every page load | Cache `simulate_bankroll()` result in Supabase (keyed by params hash) | 2000-path simulation is CPU-bound; not suitable for real-time |

**Key insight:** The data layer (DB queries, quant functions) is already implemented in Phases 1–3. The API layer is primarily plumbing — connecting existing functions to HTTP endpoints. The only genuinely new computation is the per-request user auth check.

---

## Common Pitfalls

### Pitfall 1: supabase-py RLS not activating in FastAPI
**What goes wrong:** Routes hit the service_role client (bypasses RLS) instead of a user JWT client. Users can read other users' portfolio data.
**Why it happens:** The global `get_supabase_client()` in `sharpedge_db/client.py` uses `SUPABASE_SERVICE_KEY` — designed for bot writes.
**How to avoid:** `deps.py` creates a fresh client with `create_client(url, anon_key)` and calls `client.auth.set_session(jwt, "")` to activate the user context. Never pass `get_supabase_client()` to user-scoped queries.
**Warning signs:** Portfolio endpoint returns data for all users, not just the authenticated one.

### Pitfall 2: supabase-py sync calls blocking FastAPI event loop
**What goes wrong:** FastAPI endpoint becomes slow under concurrent SSE streams because sync DB calls block the async event loop.
**Why it happens:** `supabase-py` uses synchronous `httpx` under the hood; calling it directly in `async def` blocks.
**How to avoid:** Wrap DB calls in `await asyncio.to_thread(db_function, ...)` within async endpoint handlers.
**Warning signs:** SSE streams become sluggish when > 2 concurrent users.

### Pitfall 3: Next.js middleware missing from SSR auth flow
**What goes wrong:** Session expires but user still sees protected pages (or gets 401 on FastAPI calls with stale JWT).
**Why it happens:** Without middleware, Server Components call `getUser()` with an expired token and get no user.
**How to avoid:** `middleware.ts` at root calls `supabase.auth.getUser()` on every request — this refreshes the token and writes fresh cookies before any Server Component runs.
**Warning signs:** Users get logged out unexpectedly after 1 hour (JWT default expiry).

### Pitfall 4: FCM fires after Discord instead of before
**What goes wrong:** MOB-04 requirement fails — Discord alert reaches users before push notification.
**Why it happens:** Current `value_scanner_job.py` queues plays to `_pending_value_alerts` for later dispatch; FCM trigger is not in that flow yet.
**How to avoid:** FCM send must happen synchronously (or with `await`) inside `scan_for_value_plays()` before the Discord embed is dispatched by `alert_dispatcher.py`. Fetch device tokens from `user_device_tokens` table at scan time.
**Warning signs:** Manual test: monitor Discord channel vs phone — if Discord arrives first, FCM is in wrong position.

### Pitfall 5: Flutter swipe-to-log using Dismissible removes the play
**What goes wrong:** Swiping right dismisses the card from the list before user taps Confirm; user loses the pre-filled data if they cancel.
**Why it happens:** `Dismissible` is designed for delete-on-swipe, not action-on-swipe.
**How to avoid:** Use `GestureDetector` with `onHorizontalDragEnd` detecting rightward velocity, then `showModalBottomSheet()`. The play card stays in the list; only Confirm on the sheet logs the bet.
**Warning signs:** QA test: swipe right and tap Cancel — if card disappears, wrong widget.

### Pitfall 6: Recharts fan chart fill overlap wrong color
**What goes wrong:** P5 "floor" area covers the P50 line or the shaded band looks like a solid block.
**Why it happens:** `fill="white"` assumes chart background is white — dark mode breaks this. Also, rendering order matters for z-index in SVG.
**How to avoid:** Render order: P95 area first (background), P5 area second (erase from below), P50 line last (on top). For dark mode, use `fill="hsl(var(--background))"` (Tailwind CSS variable) instead of hardcoded white.
**Warning signs:** Fan chart looks correct in light mode, breaks in dark mode.

### Pitfall 7: `build_copilot_graph()` called per SSE request
**What goes wrong:** Each POST /copilot/chat compiles the StateGraph, binding tools and creating LLM client — 200–500ms overhead per request.
**Why it happens:** `COPILOT_GRAPH` singleton is `None` when `OPENAI_API_KEY` not set at import time, so developers call `build_copilot_graph()` in the route handler.
**How to avoid:** Build graph once at FastAPI startup using a `@app.on_event("startup")` handler (or lifespan context) and store in app state. In the SSE route, retrieve from `request.app.state.copilot_graph`.
**Warning signs:** /copilot/chat has > 500ms latency on first token.

---

## Code Examples

### FastAPI v1 route registration (main.py extension)
```python
# Source: existing apps/webhook_server/src/sharpedge_webhooks/main.py pattern
from sharpedge_webhooks.routes.v1 import router as v1_router
app.include_router(v1_router)
```

### Supabase RLS — enable and policy (verified pattern from official docs)
```sql
-- Source: https://supabase.com/docs/guides/database/postgres/row-level-security
ALTER TABLE bets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_read_own_bets" ON bets
  FOR SELECT USING ((SELECT auth.uid()) = user_id);
```

### FastAPI copilot graph startup (lifespan pattern)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph
    app.state.copilot_graph = build_copilot_graph()
    yield
    # cleanup if needed

app = FastAPI(lifespan=lifespan, ...)
```

### ValuePlay API response shape (v1 — enriched vs legacy)
```python
# Legacy /api/value-plays (mobile.py) — stays unchanged
{
  "id": "...", "event": "...", "market": "...",
  "expected_value": 0.045, "book": "fanduel", ...
}

# New /api/v1/value-plays — alpha-enriched
{
  "id": "...", "game": "...", "bet_type": "...",
  "ev_percentage": 4.5,
  "alpha_score": 0.12,            # NEW: from enrich_with_alpha()
  "alpha_badge": "HIGH",          # NEW: PREMIUM/HIGH/MEDIUM/SPECULATIVE
  "regime_state": "SHARP_CONSENSUS",  # NEW: from classify_regime()
  "book": "fanduel",
  "sport": "NFL", "side": "Chiefs -3"
}
```

### simulate_bankroll() function signature (existing — for API-05)
```python
# Source: packages/models/src/sharpedge_models/monte_carlo.py
def simulate_bankroll(
    win_prob: float,
    win_pct: float,       # fraction gained per win (e.g. 0.09 for +9%)
    loss_pct: float,      # fraction lost per loss (e.g. 0.10 for -10%)
    initial_bankroll: float = 1.0,
    n_paths: int = 2000,
    n_bets: int = 500,
    seed: int | None = None,
) -> MonteCarloResult:
    # returns: ruin_probability, p05_bankroll, p50_bankroll, p95_bankroll,
    #          max_drawdown_p50, n_paths, n_bets
```

### get_performance_summary() signature (existing — for API-04)
```python
# Source: packages/database/src/sharpedge_db/queries/bets.py
def get_performance_summary(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PerformanceSummary:
    # returns: total_bets, wins, losses, pushes, win_rate, units_won, roi, avg_odds
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@supabase/auth-helpers` (Next.js) | `@supabase/ssr` | 2024 | auth-helpers is deprecated; ssr package is the official replacement |
| FCM legacy HTTP API | FCM HTTP v1 API via firebase-admin SDK | 2024 | legacy API deprecated; Admin SDK uses v1 automatically |
| `supabase.auth.getSession()` in Server Components | `supabase.auth.getUser()` | 2024 | getSession is not safe server-side; getUser validates server-to-server |
| LangGraph `astream()` | LangGraph `astream_events(version="v2")` | LangGraph 0.2+ | v2 provides structured event types; simpler to filter for LLM token chunks |
| Flutter `firebase_messaging` v7/v8 | `firebase_messaging` v15.x with `firebase_core` | 2023–2024 | FlutterFire unified API; `onBackgroundMessage` now handled as top-level function |

**Deprecated/outdated:**
- `@supabase/auth-helpers`: replaced by `@supabase/ssr`; do not use
- FCM legacy API (`https://fcm.googleapis.com/fcm/send`): use `firebase-admin` which calls v1 API
- LangGraph `astream()`: yields state dicts, not token events; use `astream_events(version="v2")` for SSE

---

## Open Questions

1. **value_plays table schema — does it have alpha_score/alpha_badge columns?**
   - What we know: `value_scanner_job.py` stores plays without alpha columns (the INSERT in the job stores `ev_percentage`, `confidence`, etc. but not `alpha_score` or `alpha_badge`)
   - What's unclear: Whether a schema migration in Phase 4 Wave 0 is needed to add these columns, or whether enrichment happens at query time in the API layer
   - Recommendation: Add `alpha_score FLOAT` and `alpha_badge TEXT` columns in a Wave 0 migration; enrich and store at scan time in `value_scanner_job.py` (update the INSERT); then the v1 API just reads from DB.

2. **user_device_tokens table — does it exist?**
   - What we know: FCM requires storing device tokens per user; no `user_device_tokens` table is visible in the codebase
   - What's unclear: Whether Supabase schema already has this table
   - Recommendation: Wave 0 migration creates `user_device_tokens (id, user_id, token, platform, created_at)` with RLS policy allowing users to upsert their own token.

3. **games table / game analysis persistence**
   - What we know: API-02 requires GET /api/v1/games/:id/analysis returning full analysis state; the 9-node LangGraph graph produces `BettingAnalysisState`
   - What's unclear: Whether game analysis results are persisted in Supabase or computed on demand per request
   - Recommendation: Run `graph.invoke()` on demand for Phase 4 (acceptable latency for a detail page); caching in Phase 5.

4. **CORS configuration for Next.js ↔ FastAPI**
   - What we know: Left to Claude's discretion per CONTEXT.md
   - Recommendation: Add `fastapi.middleware.cors.CORSMiddleware` to the FastAPI app with `allow_origins=[NEXT_PUBLIC_APP_URL]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. In development, allow `localhost:3000`.

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing: `tests/` directory, `pyproject.toml` per package) |
| Flutter test framework | flutter_test (built-in) |
| Jest/Vitest for Next.js | Not yet configured — Wave 0 gap |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` (per package) |
| Quick run command (Python) | `cd /path/to/sharpedge && uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |
| Flutter test command | `cd apps/mobile && flutter test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | GET /api/v1/value-plays returns alpha_score, alpha_badge, min_alpha filter | unit (FastAPI TestClient) | `pytest tests/unit/webhooks/test_v1_value_plays.py -x` | Wave 0 |
| API-02 | GET /api/v1/games/:id/analysis returns BettingAnalysisState fields | unit (TestClient + mock graph) | `pytest tests/unit/webhooks/test_v1_games.py -x` | Wave 0 |
| API-03 | POST /api/v1/copilot/chat streams SSE events | integration (async TestClient) | `pytest tests/unit/webhooks/test_v1_copilot.py -x` | Wave 0 |
| API-04 | GET /api/v1/users/:id/portfolio returns stats (401 without JWT) | unit (TestClient + mock DB) | `pytest tests/unit/webhooks/test_v1_portfolio.py -x` | Wave 0 |
| API-05 | POST /api/v1/bankroll/simulate returns MC result | unit (TestClient) | `pytest tests/unit/webhooks/test_v1_bankroll.py -x` | Wave 0 |
| API-06 | RLS enabled: user A cannot read user B's bets | integration (Supabase real or local) | manual-only (requires live DB) | manual |
| WEB-01–WEB-06 | Pages render without error, correct data shape | smoke (Jest/Playwright) | Wave 0 gap | Wave 0 |
| MOB-01–MOB-05 | Flutter screens/services | unit (flutter_test) | `flutter test` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/webhooks/ -x -q` (API route unit tests only)
- **Per wave merge:** `uv run pytest tests/ -v && flutter test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/webhooks/__init__.py` — new test directory for v1 routes
- [ ] `tests/unit/webhooks/test_v1_value_plays.py` — covers API-01
- [ ] `tests/unit/webhooks/test_v1_games.py` — covers API-02
- [ ] `tests/unit/webhooks/test_v1_copilot.py` — covers API-03
- [ ] `tests/unit/webhooks/test_v1_portfolio.py` — covers API-04
- [ ] `tests/unit/webhooks/test_v1_bankroll.py` — covers API-05
- [ ] `apps/web/` — Next.js project scaffold (does not exist yet)
- [ ] `apps/mobile/test/` — Flutter test files for new services (biometric_service, fcm_service, api_service SSE)
- [ ] Schema migration SQL for: RLS policies, `alpha_score`/`alpha_badge` columns on `value_plays`, `user_device_tokens` table
- [ ] FastAPI webhook_server `pyproject.toml`: add `firebase-admin` dependency

---

## Sources

### Primary (HIGH confidence)
- Supabase official docs — Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase official docs — Next.js SSR setup: https://supabase.com/docs/guides/auth/server-side/nextjs
- shadcn/ui official docs — DataTable: https://ui.shadcn.com/docs/components/radix/data-table
- SWR official docs — Revalidation/refreshInterval: https://swr.vercel.app/docs/revalidation
- Firebase official docs — FCM Flutter get started: https://firebase.google.com/docs/cloud-messaging/flutter/get-started
- firebase-admin Python SDK docs: https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging
- pub.dev local_auth package: https://pub.dev/packages/local_auth
- Codebase: `packages/models/src/sharpedge_models/alpha.py` — `compose_alpha()` signature confirmed
- Codebase: `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py` — `build_copilot_graph()` confirmed
- Codebase: `packages/models/src/sharpedge_models/monte_carlo.py` — `simulate_bankroll()` signature confirmed
- Codebase: `packages/database/src/sharpedge_db/queries/bets.py` — `get_performance_summary()` confirmed
- Codebase: `packages/database/src/sharpedge_db/client.py` — service_role singleton confirmed
- Codebase: `apps/webhook_server/src/sharpedge_webhooks/routes/mobile.py` — existing route patterns confirmed

### Secondary (MEDIUM confidence)
- FastAPI StreamingResponse + LangGraph astream_events pattern: https://www.softgrade.org/sse-with-fastapi-react-langgraph/ (cross-verified with FastAPI and LangGraph official docs)
- supabase-py per-request JWT client pattern: https://github.com/orgs/supabase/discussions/33811
- Recharts AreaChart stacked area examples: https://recharts.github.io/en-US/examples/StackedAreaChart/

### Tertiary (LOW confidence — flag for validation)
- Recharts "erase" trick for fan chart (P5 area with fill="white"): pattern inferred from Recharts SVG rendering model; validate visually in dark mode
- supabase-py `client.auth.set_session(jwt, "")` activates RLS: pattern from community discussions; verify with a real Supabase instance during Wave 0 RLS testing

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are official, published, actively maintained; versions verified via pub.dev and npm
- Architecture: HIGH — FastAPI APIRouter pattern confirmed from existing mobile.py; LangGraph graph structure confirmed from agent.py; Flutter structure confirmed from pubspec.yaml
- RLS SQL: HIGH — SQL verified from official Supabase docs; service_role bypass behavior confirmed
- supabase-py per-request JWT pattern: MEDIUM — documented in community discussions but not in official supabase-py docs; needs real DB test
- Recharts fan chart: MEDIUM — standard AreaChart API is high confidence; "white fill erase" trick for the band needs visual validation

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable ecosystem; @supabase/ssr and firebase-admin change infrequently)
