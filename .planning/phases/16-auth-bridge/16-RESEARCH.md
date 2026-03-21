# Phase 16: Auth Bridge - Research

**Researched:** 2026-03-21
**Domain:** Supabase Auth schema migration, Custom Access Token Hook, Next.js SSR middleware, Flutter JWT claims, Whop webhook tier sync, RevenueCat IAP webhook
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can sign up with email on web app and a `public.users` row is created automatically, linked to their Supabase Auth UUID | Migration 008 `handle_new_auth_user` trigger + signup page — both documented with working code |
| AUTH-02 | User can log in to web app and mobile app with the same account | Same Supabase Auth UUID, `@supabase/ssr` on web, `supabase_flutter` on mobile — common JWT, no separate identity |
| AUTH-03 | Free-tier user sees limited features with clear upgrade prompt — not a blank page or error | Next.js middleware redirect to `/upgrade`, Flutter `hasProAccess` gate + `UpgradePromptWidget` |
| AUTH-04 | Paid subscription via Whop automatically unlocks full access on web + mobile within 30 seconds | Custom Access Token Hook + `push_tier_to_supabase_auth()` via Supabase Admin API after Whop webhook fires |
| AUTH-05 | User can view their current tier (Free / Mid / Premium) and a link to their Whop subscription management page from within the app | Tier display widget reading `app_metadata.tier` from JWT; Whop manage link is `https://whop.com/manage` |

</phase_requirements>

---

## Summary

Phase 16 resolves a structural identity gap: `public.users` was built with `discord_id` as the only user key (correct for the Discord-first v1 product), but web and mobile sign-in creates a separate Supabase Auth UUID in `auth.users`. These two identities are currently unlinked — there is no column connecting them. Everything in this phase flows from fixing that gap.

Migration 008 adds `supabase_auth_id UUID UNIQUE` to `public.users`, a trigger that auto-creates a `public.users` row when a Supabase Auth user signs up, RLS policies scoping web/mobile reads to the user's own row, and the Custom Access Token Hook Postgres function that injects `tier` from `public.users` into every JWT at issue time. Once the hook is registered in the Supabase dashboard, `app_metadata.tier` is available in every JWT — Next.js middleware reads it with zero DB calls, and Flutter reads it from `currentUser.appMetadata` with no additional network request.

The Whop webhook handler (`apps/webhook_server/src/sharpedge_webhooks/routes/whop.py`) already verifies HMAC-SHA256, updates `public.users.tier` by `discord_id`, and manages Discord role assignment. The only missing step is a `push_tier_to_supabase_auth()` call using the Supabase Admin API that pushes the new tier directly into `auth.users.app_metadata` — eliminating the ~1-hour JWT auto-refresh delay that would otherwise follow a subscription event. The web dashboard auth is currently client-side only (the `(dashboard)/layout.tsx` uses `onAuthStateChange`, there is no `middleware.ts`). The mobile `AuthService` signs in via email/password and reads `currentToken` but has no `currentTier` getter. Both gaps are straightforward additions once the hook is in place.

**Primary recommendation:** Apply migration 008 first (blocks everything). Register the Custom Access Token Hook in the Supabase dashboard. Then in parallel: add `@supabase/ssr`, write `middleware.ts`, add `push_tier_to_supabase_auth` to the webhook handler, add `currentTier` getter to `AuthService`, and add `hasProAccess` / `hasSharpAccess` to `AppState`. Add a `/auth/signup` page and a `/account` page (tier display + Whop manage link) as new Next.js routes.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@supabase/ssr` | ^0.5.x (latest stable) | Server-side Supabase session reading in Next.js middleware and RSC | Required for reading sessions in `middleware.ts` — basic `createClient` does not work in Edge runtime middleware |
| `@supabase/supabase-js` | ^2.45.0 (already installed) | Browser-side Supabase client (login, signup, auth state) | Already in project; no version change needed |
| `supabase_flutter` | ^2.6.0 (already installed) | Flutter Supabase SDK — email sign-in, JWT session, `currentUser.appMetadata` | Already in project; `appMetadata` access is stable since 2.x |
| `supabase-py` | (via sharpedge_db workspace dep) | Python Supabase client — service key; used for `update_user_by_id` Admin API call | Already in `sharpedge_db.client` singleton |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | ^0.27 (already installed) | Async HTTP client in webhook server | Already used for Discord REST calls; no new dependency |
| Next.js middleware | Built-in (Next.js 14.2.5) | Edge-runtime request interceptor for tier-based route protection | Required for zero-latency route gating without a DB call |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@supabase/ssr` middleware | Client-side auth check in `layout.tsx` (current approach) | Current approach causes a flash of protected content and a client-side redirect — not suitable for production feature gating |
| Custom Access Token Hook | DB lookup on every request | Hook is zero-cost at request time; DB lookup adds latency and does not scale |
| `app_metadata.tier` | `user_metadata.tier` | `user_metadata` is user-editable — any user could self-upgrade by calling `supabase.auth.updateUser()` |

**Installation (new package only):**
```bash
# In apps/web/
npm install @supabase/ssr
```

No new Python dependencies are needed — `supabase-py` is already available via `sharpedge_db`.

---

## Existing Codebase — Confirmed State

This section documents the confirmed state of every file touched by this phase. All findings are from direct codebase inspection (HIGH confidence).

### `public.users` schema (migration 001)

```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id VARCHAR(255) UNIQUE NOT NULL,   -- only user key
    discord_username VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'free',
    subscription_id VARCHAR(255),
    bankroll DECIMAL(12, 2) DEFAULT 0,
    unit_size DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Gap:** No `supabase_auth_id` column. No `whop_membership_id` column. No `email` column.

**RLS state:** RLS enabled on all tables. Only a service-role policy exists on `users` — no authenticated-user policies exist. Web/mobile users using the anon key cannot read their own row.

### `apps/web/src/lib/supabase.ts` — confirmed state

```typescript
import { createClient } from '@supabase/supabase-js'
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

**Gap:** Uses basic `createClient`. Does NOT use `@supabase/ssr`. This client cannot be used in `middleware.ts` (Edge runtime). Must be extended — a new `createServerClient` and `createBrowserClient` pattern is needed.

### `apps/web/src/app/(dashboard)/layout.tsx` — confirmed state

Auth check is client-side only via `supabase.auth.onAuthStateChange`. There is no `middleware.ts`. Dashboard routes are protected only in the browser — a direct URL navigation to `/portfolio` before React loads would show protected content.

**Gap:** No `middleware.ts` exists. No server-side route protection. No tier-based gating.

### `apps/web/src/app/auth/callback/route.ts` — confirmed state

```typescript
export async function GET(request: NextRequest) {
  const code = searchParams.get('code')
  if (code) { await supabase.auth.exchangeCodeForSession(code) }
  return NextResponse.redirect(`${origin}/`)
}
```

**Gap:** Exchanges auth codes but does not extract the Discord identity from the OAuth response. The Discord `discord_id` link logic is absent. This file uses the basic `supabase` import — needs upgrade to a server client for correct cookie handling.

### `apps/web/src/app/auth/login/page.tsx` — confirmed state

Email/password sign-in form exists and works. No signup page exists (no `/auth/signup` route). AUTH-01 requires a signup form — this is a new file.

### `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py` — confirmed state

- HMAC-SHA256 signature verification: EXISTS
- `update_user_tier_in_db(discord_id, tier)`: EXISTS — upserts by `discord_id`
- `add_discord_role` / `remove_discord_role`: EXISTS — Discord REST via `httpx`
- Sharp tier includes Pro (both roles added): EXISTS
- `log_payment`: EXISTS

**Gap:** No `push_tier_to_supabase_auth()` call. After `update_user_tier_in_db` succeeds, the code does not push the new tier into `auth.users.app_metadata`. The JWT will not reflect the new tier until the user's token auto-refreshes (~1 hour by default).

**Secondary gap:** `supabase` is not a dependency in `webhook_server/pyproject.toml`. The `sharpedge_db` workspace package provides `get_supabase_client()` which uses a service key — this is correct for admin operations. The admin `update_user_by_id` call must use the service key client, not the anon key.

### `apps/mobile/lib/services/auth_service.dart` — confirmed state

Has: `signInWithEmail`, `signOut`, `currentToken`, `currentUserId`, `isBiometricAvailable`, `authenticateWithBiometrics`, `isSignedIn`.

**Gap:** No `currentTier` getter. The `appMetadata` property on `currentUser` is available in `supabase_flutter ^2.6.0` — it just needs to be read.

### `apps/mobile/lib/providers/app_state.dart` — confirmed state

Has: `isAuthenticated`, `userId`, `authToken`, `setAuthenticated`, `clearAuth`, `refresh`.

**Gap:** No `hasProAccess`, `hasSharpAccess`, or `currentTier` computed getters. The tier is not read from the JWT anywhere in state management.

### `apps/mobile/pubspec.yaml` — confirmed state

`supabase_flutter: ^2.6.0` is already listed. `flutter: '>=3.10.0'` is the SDK constraint — the installed version must be verified before Phase 20 Sentry work, but `supabase_flutter ^2.6.0` has no SDK floor above 3.0.0, so this phase is unaffected.

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
packages/database/src/sharpedge_db/migrations/
└── 008_auth_bridge.sql               # new — schema migration

apps/web/src/
├── middleware.ts                      # new — tier-based route protection (Edge runtime)
├── lib/
│   ├── supabase.ts                   # modify — add SSR browser + server clients
│   └── auth.ts                       # new — getUserTier() / getUserSession() helpers
└── app/
    ├── auth/
    │   ├── callback/route.ts         # modify — add Discord identity link logic
    │   └── signup/page.tsx           # new — email/password registration form
    └── account/page.tsx              # new — tier display + Whop manage link (AUTH-05)

apps/webhook_server/src/sharpedge_webhooks/routes/
└── whop.py                           # modify — add push_tier_to_supabase_auth()

apps/mobile/lib/
├── services/auth_service.dart        # modify — add currentTier getter
└── providers/app_state.dart          # modify — add hasProAccess / hasSharpAccess
```

### Pattern 1: Supabase Custom Access Token Hook

**What:** A `SECURITY DEFINER` Postgres function registered in the Supabase dashboard injects `public.users.tier` into `app_metadata.tier` of every JWT at issue time.

**When to use:** Once — registered in the Supabase dashboard after migration 008 creates the `supabase_auth_id` bridge column.

**Full function (goes in migration 008):**
```sql
-- Source: https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
security definer
as $$
declare
  claims     jsonb;
  user_tier  text;
  auth_id    uuid;
begin
  auth_id := (event->>'user_id')::uuid;
  claims  := event->'claims';

  select tier into user_tier
  from public.users
  where supabase_auth_id = auth_id;

  user_tier := coalesce(user_tier, 'free');

  claims := jsonb_set(claims, '{app_metadata}',
    coalesce(claims->'app_metadata', '{}'));
  claims := jsonb_set(claims, '{app_metadata,tier}', to_jsonb(user_tier));

  return jsonb_set(event, '{claims}', claims);
end;
$$;

grant execute on function public.custom_access_token_hook
  to supabase_auth_admin;
```

**Dashboard registration:** Supabase Dashboard → Authentication → Hooks → Custom Access Token Hook → set to `public.custom_access_token_hook`. This step is a manual dashboard action — it cannot be done via SQL migration alone.

**Confidence:** HIGH — verified against Supabase Custom Access Token Hook official docs

---

### Pattern 2: Migration 008 — `supabase_auth_id` Bridge Column

**What:** Adds the bridge column, an index, user-scoped RLS policies, and the `handle_new_auth_user` trigger that auto-creates a `public.users` row for every new Supabase Auth signup.

**Full migration SQL:**
```sql
-- packages/database/src/sharpedge_db/migrations/008_auth_bridge.sql

-- 1. Bridge column
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS supabase_auth_id UUID UNIQUE,
  ADD COLUMN IF NOT EXISTS whop_membership_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id
  ON public.users(supabase_auth_id);

-- 2. RLS: authenticated web/mobile users read and update their own row
CREATE POLICY "User reads own record"
  ON public.users FOR SELECT
  USING (auth.uid() = supabase_auth_id);

CREATE POLICY "User updates own bankroll"
  ON public.users FOR UPDATE
  USING (auth.uid() = supabase_auth_id)
  WITH CHECK (auth.uid() = supabase_auth_id);

-- 3. Auto-create public.users row on new Supabase Auth signup
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (supabase_auth_id, tier)
  VALUES (NEW.id, 'free')
  ON CONFLICT (supabase_auth_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
```

**Note on `discord_id NOT NULL`:** The existing `discord_id` column is `NOT NULL`. New email-only web signups will NOT have a `discord_id`. The trigger inserts a row with `supabase_auth_id` and `tier` only. This will fail unless `discord_id` is made nullable. **Migration 008 must also include:**
```sql
ALTER TABLE public.users
  ALTER COLUMN discord_id DROP NOT NULL;
```

**Confidence:** HIGH — confirmed from direct inspection of migration 001 schema

---

### Pattern 3: `@supabase/ssr` Client Setup for Next.js

**What:** Replace the current single `createClient` export with a browser client and a server client factory. The server client reads cookies correctly in middleware and Route Handlers.

**New `apps/web/src/lib/supabase.ts`:**
```typescript
// Source: https://supabase.com/docs/guides/auth/server-side/nextjs
import { createBrowserClient } from '@supabase/ssr'

// For use in Client Components
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}
```

**New `apps/web/src/lib/supabase-server.ts`:**
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export function createServerSupabaseClient() {
  const cookieStore = cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get: (name) => cookieStore.get(name)?.value,
      },
    }
  )
}
```

**Existing consumer pages** (`login/page.tsx`, `callback/route.ts`, `(dashboard)/layout.tsx`) import `supabase` from `@/lib/supabase` as a named export. After the refactor, these imports must be updated to call `createClient()`. This is a mechanical find-and-replace with three files affected.

**Confidence:** HIGH — `@supabase/ssr` pattern verified against official Supabase Next.js guide

---

### Pattern 4: Next.js Middleware Tier Gate

**What:** `apps/web/src/middleware.ts` reads the tier from the JWT on every request to protected routes. Redirects unauthenticated users to `/auth/login` and free-tier users attempting paid routes to `/upgrade`.

```typescript
// apps/web/src/middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

const TIER_ORDER = { free: 0, pro: 1, sharp: 2 } as const
type Tier = keyof typeof TIER_ORDER

// Map route prefixes to minimum required tier
const ROUTE_MIN_TIER: Record<string, Tier> = {
  '/portfolio':          'pro',
  '/value-plays':        'pro',
  '/bankroll':           'pro',
  '/copilot':            'pro',
  '/prediction-markets': 'pro',
  '/analytics':          'pro',
  '/swarm':              'sharp',
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Find the most specific matching route prefix
  const requiredTier = Object.entries(ROUTE_MIN_TIER)
    .find(([prefix]) => pathname.startsWith(prefix))?.[1]

  if (!requiredTier) return NextResponse.next()

  const response = NextResponse.next({
    request: { headers: request.headers },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get:    (n)    => request.cookies.get(n)?.value,
        set:    (n, v, o) => response.cookies.set({ name: n, value: v, ...o }),
        remove: (n, o)    => response.cookies.set({ name: n, value: '', ...o }),
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  const userTier = (session.user.app_metadata?.tier ?? 'free') as Tier
  const hasAccess = TIER_ORDER[userTier] >= TIER_ORDER[requiredTier]

  if (!hasAccess) {
    return NextResponse.redirect(new URL('/upgrade', request.url))
  }

  return response
}

export const config = {
  matcher: [
    '/portfolio/:path*',
    '/value-plays/:path*',
    '/bankroll/:path*',
    '/copilot/:path*',
    '/prediction-markets/:path*',
    '/analytics/:path*',
    '/swarm/:path*',
    '/account/:path*',
  ],
}
```

**Note on `/upgrade`:** This route does not yet exist. The planner must include creating a minimal `/upgrade` page (static redirect to Whop checkout or an in-app upgrade prompt). Without this route, the middleware redirect resolves to a 404.

**Confidence:** HIGH — `@supabase/ssr` middleware pattern verified against official docs

---

### Pattern 5: `push_tier_to_supabase_auth()` in Whop Webhook Handler

**What:** After `update_user_tier_in_db` runs, look up `supabase_auth_id` from `public.users` by `discord_id` and push the new tier to `auth.users.app_metadata` via the Supabase Admin API. This forces the new tier into the next JWT refresh immediately rather than waiting ~1 hour.

```python
# Add to apps/webhook_server/src/sharpedge_webhooks/routes/whop.py

async def push_tier_to_supabase_auth(discord_id: str, tier: str) -> None:
    """Push updated tier into Supabase auth.users app_metadata for immediate JWT reflection."""
    try:
        from sharpedge_db.client import get_supabase_client
        client = get_supabase_client()  # uses service key — required for admin API

        # Look up supabase_auth_id from public.users by discord_id
        result = client.table("users").select("supabase_auth_id").eq(
            "discord_id", discord_id
        ).maybe_single().execute()

        if not result.data or not result.data.get("supabase_auth_id"):
            logger.info(
                f"No supabase_auth_id for discord_id={discord_id}; "
                "skipping auth metadata update (Discord-only user)"
            )
            return

        supabase_auth_id = result.data["supabase_auth_id"]
        client.auth.admin.update_user_by_id(
            supabase_auth_id,
            {"app_metadata": {"tier": tier}}
        )
        logger.info(f"Pushed tier={tier} to supabase auth for user {supabase_auth_id}")

    except Exception as e:
        logger.exception(f"Failed to push tier to Supabase auth: {e}")
```

**Call site** — in `whop_webhook()`, add immediately after each `update_user_tier_in_db` call:
```python
await update_user_tier_in_db(discord_id, tier)
await push_tier_to_supabase_auth(discord_id, tier)  # new
```

**Note on `supabase-py` Admin API:** `client.auth.admin.update_user_by_id` is available in `supabase-py >= 1.0`. The existing `sharpedge_db.client` uses the service key — the Admin API requires the service key, so no new client or credential is needed.

**Confidence:** HIGH — existing webhook handler inspected; Supabase Admin API documented

---

### Pattern 6: Flutter `currentTier` Getter and `hasProAccess` Computed State

**`auth_service.dart` addition:**
```dart
// Add to AuthService class
String get currentTier {
  final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
  return (meta?['tier'] as String?) ?? 'free';
}

bool get isSignedIn =>
    Supabase.instance.client.auth.currentSession != null;
```

**`app_state.dart` addition:**
```dart
// Add to AppState class (requires AuthService reference)
// AppState needs to hold a reference to AuthService or receive tier from it.
// Current pattern: authToken is stored in AppState.
// Simplest approach: derive tier from the Supabase SDK directly (no coupling change).

bool get hasProAccess {
  final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
  final tier = (meta?['tier'] as String?) ?? 'free';
  return tier == 'pro' || tier == 'sharp';
}

bool get hasSharpAccess {
  final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
  return (meta?['tier'] as String?) == 'sharp';
}

String get currentTier {
  final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
  return (meta?['tier'] as String?) ?? 'free';
}
```

**Gate pattern in Flutter screens:**
```dart
Consumer<AppState>(
  builder: (context, state, _) => state.hasProAccess
    ? const ValuePlaysScreen()
    : UpgradePromptWidget(
        message: 'Upgrade to Pro to see live value plays',
        whopLink: 'https://whop.com/sharpedge',
      ),
)
```

**Confidence:** HIGH — `supabase_flutter ^2.6.0` exposes `currentUser?.appMetadata` as `Map<String, dynamic>?`; confirmed via `supabase_flutter` package docs

---

### Pattern 7: Web Signup Page (AUTH-01)

No `/auth/signup` route exists. AUTH-01 requires email signup on web. The new page is a mirror of the existing `login/page.tsx` but calls `supabase.auth.signUp()` instead of `signInWithPassword`. The `handle_new_auth_user` trigger fires on the Supabase side and creates the `public.users` row automatically.

**Key points:**
- After `signUp()` succeeds, Supabase sends a confirmation email by default. The user must confirm before their session is established.
- The `auth/callback/route.ts` handles the confirmation link click. After migration 008, the callback route also needs to correctly set cookies via the server client pattern (not the current basic `supabase` import).
- The `/auth/signup` page must navigate to a "Check your email" intermediate state after the `signUp()` call.

---

### Pattern 8: Account / Tier Display Page (AUTH-05)

A `/account` page must be added to the web dashboard showing:
1. Current tier ("Free", "Pro", or "Sharp") — read from `session.user.app_metadata.tier`
2. A link to manage the Whop subscription at `https://whop.com/manage`

This page is a new Server Component (or Client Component with `useSession`) — no backend API call needed since tier is already in the JWT.

---

### Anti-Patterns to Avoid

- **`user_metadata` for tier:** `user_metadata` is user-editable. Any user can self-upgrade via `supabase.auth.updateUser({ data: { tier: 'sharp' } })`. Always use `app_metadata`, which is writable only via service key or `SECURITY DEFINER` function.
- **Querying `public.users` on every request for tier:** The Custom Access Token Hook embeds tier in the JWT. Middleware reads from `session.user.app_metadata.tier` with zero DB calls. Never add a DB query to the middleware hot path.
- **Checking Whop API on every bot command:** The bot's existing `@require_tier` reads `public.users.tier` which is kept current by webhooks. Direct Whop API calls should be reserved for a `/refresh-tier` command.
- **Importing the basic `supabase` client in `middleware.ts`:** The basic `createClient` does not work in the Edge runtime. Only `@supabase/ssr`'s `createServerClient` works in middleware.
- **Forgetting `detectSessionInUrl: false` on Flutter:** Mobile has no URL for session detection. The Flutter `Supabase.initialize()` call (in `main.dart`) should set `authOptions: FlutterAuthClientOptions(detectSessionInUrl: false)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT tier injection | Custom claim parsing or a separate user-data API endpoint per request | Supabase Custom Access Token Hook (Postgres function) | Official hook fires at JWT issue time — zero per-request overhead; survives token refresh automatically |
| Server-side session reading in Next.js middleware | Raw cookie parsing of the Supabase session cookie | `@supabase/ssr` `createServerClient` | Supabase's session cookie is chunked across multiple cookies; manual parsing breaks on large sessions |
| Immediate tier propagation after subscription | Polling the DB from the client | `push_tier_to_supabase_auth()` + Supabase Admin `update_user_by_id` | Admin API update forces the new `app_metadata` into the user record immediately; client gets it on next token refresh (~seconds via `autoRefreshToken`) |
| RLS user identity | Custom auth header + application-level authorization | `auth.uid() = supabase_auth_id` RLS policy | Supabase RLS uses the JWT `sub` claim automatically; no application code needed |

**Key insight:** Every piece of the auth stack in this phase has an official Supabase primitive. The only custom code is the thin glue that calls these primitives in the right sequence.

---

## Common Pitfalls

### Pitfall 1: `discord_id NOT NULL` Blocks the `handle_new_auth_user` Trigger

**What goes wrong:** The trigger inserts a row with only `supabase_auth_id` and `tier`. The `discord_id` column is `NOT NULL` (migration 001). The INSERT fails silently or raises an exception — no `public.users` row is created for new email-only signups.

**Why it happens:** Migration 001 defined `discord_id VARCHAR(255) UNIQUE NOT NULL` because the product was Discord-first. Email-only web signups do not have a `discord_id`.

**How to avoid:** Migration 008 must include `ALTER TABLE public.users ALTER COLUMN discord_id DROP NOT NULL;` before the trigger definition.

**Warning signs:** New user signs up on web, Supabase Auth row is created, but no `public.users` row appears. JWT tier claim is missing. Tier shows as `free` due to `coalesce` in the hook even after paying.

---

### Pitfall 2: `auth/callback/route.ts` Uses the Wrong Supabase Client

**What goes wrong:** The current `callback/route.ts` imports `supabase` from `@/lib/supabase` (the basic browser client). In a Route Handler, cookies are not available on this client — the session exchange via `exchangeCodeForSession` may succeed internally but fail to write the session cookie, leaving the user in a logged-out state after clicking the email confirmation link.

**Why it happens:** `@supabase/supabase-js` `createClient` does not handle server-side cookie writing. Only `@supabase/ssr`'s `createServerClient` does.

**How to avoid:** `callback/route.ts` must use `createServerClient` from `@supabase/ssr` and write cookies via the `set` option in the cookies adapter.

**Warning signs:** User clicks email confirmation link, is redirected to dashboard, but is immediately redirected back to login page.

---

### Pitfall 3: Custom Access Token Hook Requires Dashboard Registration — SQL Alone Is Not Enough

**What goes wrong:** The `custom_access_token_hook` function is deployed via SQL migration. The developer assumes the hook is active. But Supabase requires explicit registration in the Dashboard (Authentication → Hooks → Custom Access Token Hook). Without this step, the function exists in the database but is never called — JWTs have no `tier` claim.

**Why it happens:** Supabase hooks are a dashboard-registered feature, not auto-discovered from SQL function names.

**How to avoid:** The plan must include a manual verification step: after migration 008 is applied, register the hook in the Supabase dashboard and then test that a newly issued JWT (after sign-in) contains `app_metadata.tier`.

**Warning signs:** Migration applied, sign-in works, but `session.user.app_metadata.tier` is `undefined` in browser console.

---

### Pitfall 4: `push_tier_to_supabase_auth` Does Not Immediately Refresh Active Sessions

**What goes wrong:** `update_user_by_id` updates `auth.users.app_metadata` in Supabase. However, active JWT sessions are not invalidated — the user's current token still has the old tier until it expires and auto-refreshes.

**Why it happens:** Supabase JWTs are short-lived (default 1 hour), and `autoRefreshToken: true` refreshes them automatically in the background. The refresh happens when the token is about to expire or on the next page load, not immediately.

**How to avoid:** This is expected behavior — the 30-second success criterion in AUTH-04 refers to the tier appearing on the next page interaction after the webhook fires. The web client (`autoRefreshToken: true` is the default in `@supabase/ssr`) will pick up the new token within seconds on next use. Document this in the plan so the verifier knows what to check (refresh the page after Whop event fires, not before).

**Warning signs:** Tier does not update immediately in an already-open browser tab without any navigation — this is NOT a bug.

---

### Pitfall 5: RevenueCat IAP — New Webhook Endpoint Required (Not Yet Built)

**What goes wrong:** The additional context specifies "Option B IAP at $20/mo via RevenueCat" for mobile. The existing webhook handler handles only Whop events. RevenueCat fires separate webhook events (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`, `EXPIRATION`) to a different endpoint with a different payload schema and verification mechanism.

**Why it happens:** RevenueCat is a separate payment layer for Apple IAP / Google Play billing — Whop handles web checkout only.

**How to avoid:** A new `routes/revenuecat.py` webhook handler is required in `apps/webhook_server`. This was flagged in the additional context but is NOT in the existing codebase (confirmed). The planner must scope this as part of Phase 16 or explicitly defer it.

**RevenueCat webhook verification:** RevenueCat signs webhooks with an `Authorization` header containing a shared secret (set in RevenueCat dashboard). Verification is: `request.headers["Authorization"] == os.environ["REVENUECAT_WEBHOOK_SECRET"]`.

**RevenueCat tier mapping:** RevenueCat events include `product_id` (e.g., `sharpedge_pro_monthly`) and `entitlement_identifier`. Map to tier the same way as Whop: product ID → tier string. Then call `push_tier_to_supabase_auth` using the user's `supabase_auth_id`. RevenueCat events include `app_user_id` which can be set to the Supabase UUID at purchase time (see "RevenueCat User ID" section below).

**Confidence on RevenueCat:** MEDIUM — based on RevenueCat official webhook docs patterns; specific payload field names should be verified against the live RevenueCat dashboard before implementation.

---

### Pitfall 6: Account Linking Gap — Whop Webhook Knows `discord_id`, Not `supabase_auth_id`

**What goes wrong:** A user subscribes on Whop before connecting their Discord account to their Supabase web account. The webhook fires with `discord_id`. `push_tier_to_supabase_auth` does a lookup by `discord_id` to find `supabase_auth_id` — but `supabase_auth_id` is NULL (the user has not linked accounts yet). The tier is written to `public.users` by `discord_id` but does not propagate to the JWT.

**Why it happens:** Users may subscribe on Whop using their Discord account before they have created a web account. The Discord→Supabase link only happens when the user signs up on web and clicks "Connect Discord".

**How to avoid:** The `push_tier_to_supabase_auth` function must gracefully handle NULL `supabase_auth_id` — log an info-level message, skip the Admin API call, and return. The tier will be correct in `public.users` and will be picked up by the JWT hook as soon as the user signs into the web app and their trigger fires. No data loss occurs.

---

## RevenueCat Integration (Mobile IAP Tier Sync)

### User ID Strategy

RevenueCat requires a stable user ID to associate purchases with users. The correct approach for this codebase:

1. After Supabase sign-in in Flutter, call `Purchases.logIn(supabaseUserId)` using the Supabase Auth UUID as the RevenueCat App User ID
2. This links the Apple/Google purchase to the Supabase UUID
3. RevenueCat webhook events include `app_user_id` = Supabase UUID — the webhook handler can look up `supabase_auth_id` directly without a `discord_id` intermediary

**Flutter initialization pattern:**
```dart
// In auth flow after successful Supabase sign-in
final userId = Supabase.instance.client.auth.currentUser?.id;
if (userId != null) {
  await Purchases.logIn(userId);
}
```

### RevenueCat Webhook Event Mapping

| RevenueCat Event | Action |
|-----------------|--------|
| `INITIAL_PURCHASE` | Set tier to `pro` or `sharp` based on product ID |
| `RENEWAL` | Same as INITIAL_PURCHASE |
| `CANCELLATION` | Set tier to `free` |
| `EXPIRATION` | Set tier to `free` |
| `BILLING_ISSUE` | Log warning; tier stays active until EXPIRATION |

**Confidence:** MEDIUM — RevenueCat event names and payload structure from official RevenueCat webhook docs; verify specific `app_user_id` field name before implementation.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side auth check in layout | `middleware.ts` with `@supabase/ssr` server session | Supabase SSR package GA (2024) | Eliminates flash of protected content; protects at Edge layer before React renders |
| Manual cookie parsing for JWT | `@supabase/ssr` `createServerClient` handles chunked cookies | `@supabase/ssr` v0.3+ | Prevents session loss on large JWTs |
| Custom claims via `user_metadata` | `app_metadata` via Custom Access Token Hook | Supabase hooks GA (2024) | Prevents user self-upgrade; eliminates per-request DB lookups |
| Calling Whop API on every tier check | Webhook keeps `public.users.tier` current; JWT carries tier | v2.0 design (this codebase) | Eliminates external API dependency from every request hot path |

**Deprecated/outdated:**
- Basic `createClient` for server-side use: Works in Client Components but incorrect in middleware, Route Handlers, and Server Components. Replaced by `@supabase/ssr`.
- `supabase.auth.getUser()` in middleware: Use `getSession()` for performance (avoids a network call to Supabase Auth on every request); `getUser()` always hits the network.

---

## Open Questions

1. **RevenueCat scope: Phase 16 or Phase 20?**
   - What we know: Additional context says "Option B IAP at $20/mo via RevenueCat" is decided. No RevenueCat handler exists in the codebase.
   - What's unclear: Should the RevenueCat webhook endpoint be built in Phase 16 (alongside Whop) or deferred to Phase 20 (Mobile Submission)?
   - Recommendation: Scope it in Phase 16. It is a single new `routes/revenuecat.py` file plus registration of the endpoint URL in the RevenueCat dashboard. Deferring to Phase 20 means the first mobile IAP purchase will not propagate to the JWT — a broken experience at launch.

2. **`/upgrade` page content**
   - What we know: The middleware redirects to `/upgrade` for free-tier users hitting paid routes.
   - What's unclear: Should `/upgrade` be a full page with pricing info, or a minimal redirect to the Whop checkout URL?
   - Recommendation: A minimal page with tier overview and a CTA button linking to `https://whop.com/{slug}/checkout/{pro_product_id}` is sufficient for Phase 16. The full marketing landing page is Phase 19 scope.

3. **Discord OAuth "Connect Discord" flow**
   - What we know: `auth/callback/route.ts` exists as a stub. Discord identity linking is needed for Whop webhook tier sync to work for web users.
   - What's unclear: Is Discord OAuth connection mandatory at signup, or optional after signup? The simpler path is optional (prompt in the account page).
   - Recommendation: Optional — user signs up with email, gets free tier immediately. Account page prompts "Connect Discord to sync your Whop subscription." This avoids a mandatory OAuth step that increases signup friction.

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (web) — `vitest ^2.1.0` in `apps/web/package.json` |
| Framework | `flutter test` (mobile) — built-in SDK |
| Framework | `pytest` (Python webhook server) — used in existing test suites |
| Config file | `apps/web/vitest.config.*` (check if exists); otherwise inline in `package.json` |
| Quick run command (web) | `cd apps/web && npm test` |
| Quick run command (Python) | `cd apps/webhook_server && python -m pytest tests/ -x -q` |
| Quick run command (Flutter) | `cd apps/mobile && flutter test` |
| Full suite command | All three above in sequence |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | `handle_new_auth_user` trigger inserts a `public.users` row with `supabase_auth_id` and `tier='free'` on new Supabase Auth signup | integration (SQL) | Manual — run migration in Supabase SQL editor, insert into `auth.users`, verify row in `public.users` | Migration: Wave 0 gap |
| AUTH-01 | `/auth/signup` page calls `supabase.auth.signUp()` and shows "check your email" state | unit (Vitest + RTL) | `cd apps/web && npm test -- signup` | ❌ Wave 0 gap |
| AUTH-02 | Same Supabase session JWT is usable in web middleware and Flutter `currentToken` | integration (manual) | Sign in on web; copy token; verify same `sub` UUID in Flutter | Manual only |
| AUTH-03 | Free-tier user requesting `/portfolio` is redirected to `/upgrade` (not 404) | unit (Vitest middleware mock) | `cd apps/web && npm test -- middleware` | ❌ Wave 0 gap |
| AUTH-03 | `hasProAccess` returns `false` when `app_metadata.tier = 'free'` | unit (flutter test) | `cd apps/mobile && flutter test test/app_state_test.dart` | ❌ Wave 0 gap |
| AUTH-04 | `push_tier_to_supabase_auth` calls `auth.admin.update_user_by_id` with correct tier | unit (pytest mock) | `cd apps/webhook_server && python -m pytest tests/test_whop_tier_sync.py -x` | ❌ Wave 0 gap |
| AUTH-04 | `custom_access_token_hook` returns `app_metadata.tier` from `public.users` | integration (SQL function test) | Call function with test event JSON in Supabase SQL editor; verify output | Manual + SQL |
| AUTH-04 | Whop `membership.went_valid` event updates tier to `pro` in `public.users` | unit (pytest mock) | `cd apps/webhook_server && python -m pytest tests/test_whop.py -k test_membership_went_valid` | ❌ Wave 0 gap |
| AUTH-05 | `/account` page renders tier string and Whop manage link from JWT session | unit (Vitest + RTL) | `cd apps/web && npm test -- account` | ❌ Wave 0 gap |
| AUTH-05 | `currentTier` getter returns tier string from `app_metadata` | unit (flutter test) | `cd apps/mobile && flutter test test/auth_service_test.dart` | ❌ Wave 0 gap |

### Sampling Rate

- **Per task commit:** `cd apps/web && npm test` (Vitest fast suite) + `python -m pytest tests/ -x -q` (webhook server)
- **Per wave merge:** All three suites — web + Python + Flutter
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files for Phase 16 are new — no existing test infrastructure covers AUTH requirements:

- [ ] `apps/web/src/test/middleware.test.ts` — covers AUTH-03 middleware redirect logic
- [ ] `apps/web/src/test/signup.test.tsx` — covers AUTH-01 signup form behavior
- [ ] `apps/web/src/test/account.test.tsx` — covers AUTH-05 tier display
- [ ] `apps/webhook_server/tests/test_whop_tier_sync.py` — covers AUTH-04 `push_tier_to_supabase_auth` unit test
- [ ] `apps/mobile/test/auth_service_test.dart` — covers AUTH-04/05 `currentTier` getter
- [ ] `apps/mobile/test/app_state_test.dart` — covers AUTH-03 `hasProAccess` computed getter

---

## Sources

### Primary (HIGH confidence)

- Supabase Custom Access Token Hook official docs — `custom_access_token_hook` Postgres function signature, dashboard registration, `app_metadata` injection pattern
- Supabase `@supabase/ssr` Next.js guide — `createServerClient` + `createBrowserClient` setup, middleware cookie adapter pattern
- Supabase User Management docs — `handle_new_auth_user` trigger pattern (official example)
- Supabase JWT Claims Reference — `app_metadata` vs `user_metadata` writability distinction
- Direct codebase inspection (HIGH confidence):
  - `packages/database/src/sharpedge_db/migrations/001_initial_schema.sql` — confirmed `discord_id NOT NULL` constraint
  - `apps/webhook_server/src/sharpedge_webhooks/routes/whop.py` — confirmed existing event handling; confirmed missing `push_tier_to_supabase_auth`
  - `apps/web/src/lib/supabase.ts` — confirmed basic `createClient`; no `@supabase/ssr`
  - `apps/web/src/app/auth/callback/route.ts` — confirmed stub; no Discord identity link logic
  - `apps/web/src/app/(dashboard)/layout.tsx` — confirmed client-side auth only; no middleware
  - `apps/mobile/lib/services/auth_service.dart` — confirmed; no `currentTier` getter
  - `apps/mobile/lib/providers/app_state.dart` — confirmed; no `hasProAccess` computed state
  - `apps/mobile/pubspec.yaml` — confirmed `supabase_flutter: ^2.6.0`
  - `apps/web/package.json` — confirmed `@supabase/supabase-js: ^2.45.0`; no `@supabase/ssr`

### Secondary (MEDIUM confidence)

- RevenueCat webhook documentation — event names (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`), `app_user_id` field, Authorization header verification pattern
- `supabase_flutter` pub.dev package — `currentUser?.appMetadata` as `Map<String, dynamic>?` confirmed in 2.x
- Supabase Admin API Python reference — `client.auth.admin.update_user_by_id` method signature

### Tertiary (LOW confidence — verify during implementation)

- RevenueCat exact payload schema field names — verify against live RevenueCat dashboard webhook test tool before implementing `routes/revenuecat.py`
- `supabase-py` Admin API method exact signature — verify `update_user_by_id` parameter structure against current `supabase-py` version in workspace

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed except `@supabase/ssr`; exact versions confirmed from package files
- Architecture: HIGH — all patterns verified against official Supabase docs and direct codebase inspection
- Pitfalls: HIGH for `discord_id NOT NULL` (confirmed from migration 001), `callback/route.ts` client issue (confirmed), hook registration gap (official Supabase docs). MEDIUM for RevenueCat specifics.
- RevenueCat integration: MEDIUM — event names and authorization pattern from official docs; payload field names need verification

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (Supabase `@supabase/ssr` API is stable; 30-day window)
