# Architecture Patterns

**Domain:** Multi-platform SaaS — web (Next.js 14) + mobile (Flutter) + Discord bot (discord.py) + FastAPI webhook server; Supabase Auth + Whop monetization
**Researched:** 2026-03-21
**Confidence:** HIGH (core patterns verified against Supabase official docs and existing codebase inspection)

---

## Note on Scope

This document covers two architectural concerns:

1. **v3.0 Launch Architecture** — Cross-platform auth, subscription gating, Whop↔Supabase↔Discord sync (primary focus for this milestone)
2. **v2.0 Agent Architecture** — LangGraph StateGraph and BettingCopilot (retained from previous research, unchanged)

---

## v3.0: Cross-Platform Auth and Subscription Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT TIER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  Next.js 14  │  │   Flutter    │  │     Discord Bot          │   │
│  │  (web app)   │  │  (mobile)    │  │  (discord.py / python)   │   │
│  │              │  │              │  │                          │   │
│  │ middleware.ts│  │ app_state    │  │  @require_tier           │   │
│  │ reads JWT    │  │ reads JWT    │  │  queries public.users    │   │
│  │ app_metadata │  │ app_metadata │  │  by discord_id           │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
└─────────┼────────────────┼───────────────────────┼─────────────────┘
          │ @supabase/ssr  │ supabase_flutter SDK  │ supabase-py
          │ (server+client)│ (AsyncStorage)        │ (service key)
          ▼                ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        AUTH & DATA TIER                              │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                         Supabase                               │  │
│  │                                                                │  │
│  │  auth.users                  public.users                      │  │
│  │  ─────────────               ────────────────────────────────  │  │
│  │  id (UUID) ──────────────→  supabase_auth_id (UUID, UNIQUE)   │  │
│  │  email                       discord_id (VARCHAR, UNIQUE)      │  │
│  │  app_metadata.tier           tier (free|pro|sharp)             │  │
│  │                              whop_membership_id               │  │
│  │                              bankroll, unit_size, bets...      │  │
│  │                                                                │  │
│  │  Custom Access Token Hook:                                     │  │
│  │    SELECT tier FROM public.users                               │  │
│  │    WHERE supabase_auth_id = event.user_id                      │  │
│  │    → inject into JWT app_metadata.tier                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
          ▲  HMAC-SHA256 signed webhooks
┌──────────────────────────────────────────────────────────────────────┐
│                      WEBHOOK / SYNC TIER                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  FastAPI Webhook Server  (apps/webhook_server)                  │ │
│  │                                                                 │ │
│  │  membership.went_valid:                                         │ │
│  │    1. upsert public.users (discord_id, tier, membership_id)    │ │
│  │    2. Discord REST: PUT guilds/{id}/members/{uid}/roles/{r}    │ │
│  │    3. Supabase Admin API: updateUserById app_metadata.tier     │ │
│  │                                                                 │ │
│  │  membership.went_invalid:                                       │ │
│  │    1. UPDATE public.users SET tier = 'free'                    │ │
│  │    2. Discord REST: DELETE role                                 │ │
│  │    3. Supabase Admin API: updateUserById app_metadata.tier     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
          ▲  HTTPS POST events
     ┌────┴────┐
     │  Whop   │  (subscription lifecycle events)
     └─────────┘
```

---

### The Central Problem: Two Identity Systems

The existing schema uses `discord_id` as the primary user identifier (keyed on `public.users.discord_id`). Web and mobile users sign in through Supabase Auth (email/password), which produces an `auth.users.id` UUID. These are separate identities.

**Current state (from codebase inspection):**
- `public.users` — has `discord_id` as unique key, no `supabase_auth_id` column
- Webhook handler (`routes/whop.py`) — updates `public.users` by `discord_id` only
- Bot `tier_check.py` — queries `public.users` by `discord_id` — correct, no change needed
- Web `supabase.ts` — thin `createClient` wrapper, no server-side session handling
- Mobile `auth_service.dart` — signs in via Supabase email/password, gets JWT but does not read tier claim

**The single most important schema change:** add `supabase_auth_id UUID UNIQUE` to `public.users`. This is the bridge column that connects the two identity systems.

---

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `public.users` (Supabase DB) | Single source of truth for subscription tier | Exists — needs `supabase_auth_id` column |
| Custom Access Token Hook (Postgres fn) | Injects `tier` into every JWT at issue time — eliminates per-request DB lookups | Does not exist — new Postgres function required |
| `apps/web/src/middleware.ts` | Decodes JWT, checks `app_metadata.tier`, redirects or blocks routes | Does not exist — new file |
| `apps/web/src/lib/supabase.ts` | Supabase client | Exists — needs `@supabase/ssr` upgrade for server-side |
| `apps/web/src/app/auth/callback/route.ts` | Exchange OAuth code, link Discord identity to Supabase account | Exists as stub — needs account-link logic |
| `apps/webhook_server/routes/whop.py` | Receive Whop events, update DB tier, fire Discord REST | Exists — needs `push_tier_to_supabase_auth` call added |
| `apps/mobile/lib/services/auth_service.dart` | Supabase Flutter email sign-in, biometrics | Exists — needs `currentTier` getter |
| `apps/mobile/lib/providers/app_state.dart` | App-level state provider | Exists — needs `hasProAccess` / `hasSharpAccess` computed fields |
| `apps/bot/middleware/tier_check.py` | Decorator: query DB by `discord_id`, enforce tier | Exists — no change required |

---

### Pattern 1: Supabase Auth JWT with Tier Claim (Web + Mobile)

**What:** A Postgres function registered as a Supabase Custom Access Token Hook injects the user's `tier` from `public.users` into the JWT at issue time. Web and mobile clients read `app_metadata.tier` from the decoded token without any additional DB call.

**Why `app_metadata` over alternatives:**
- `user_metadata` is user-editable — a user could call `supabase.auth.updateUser({ data: { tier: 'sharp' } })` to self-upgrade
- `app_metadata` is server-controlled only; writeable only via service key or `SECURITY DEFINER` Postgres function
- Tier in JWT eliminates a DB roundtrip on every page load, route check, and feature gate

**New Postgres function (migration 008):**
```sql
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

Registration: Supabase dashboard → Authentication → Hooks → Custom Access Token → set to `public.custom_access_token_hook`.

**Reading the claim in Next.js (server-side helper):**
```typescript
// apps/web/src/lib/auth.ts  (new file)
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function getUserTier(): Promise<'free' | 'pro' | 'sharp'> {
  const cookieStore = cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { get: (name) => cookieStore.get(name)?.value } }
  )
  const { data: { session } } = await supabase.auth.getSession()
  return (session?.user?.app_metadata?.tier ?? 'free') as 'free' | 'pro' | 'sharp'
}
```

**Reading the claim in Flutter (extend existing `auth_service.dart`):**
```dart
// New getter on existing AuthService class
String get currentTier {
  final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
  return (meta?['tier'] as String?) ?? 'free';
}
```

**Confidence:** HIGH — verified against [Supabase Custom Access Token Hook docs](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook)

---

### Pattern 2: Whop Webhook → Supabase → Discord Role Sync

**What:** Whop fires `membership.went_valid` / `membership.went_invalid` to the existing FastAPI handler. The handler updates `public.users`, calls Discord REST to add/remove roles, and now also calls the Supabase Admin API to push the new tier directly into `auth.users.app_metadata` — no waiting for JWT refresh.

**What already exists (codebase confirmed):**
- HMAC-SHA256 signature verification
- `update_user_tier_in_db` — updates by `discord_id`
- `add_discord_role` / `remove_discord_role` — Discord REST via `httpx`
- Tier hierarchy: Sharp includes Pro (Sharp subscribers get both roles)

**The gap:** The handler updates `public.users.tier` by `discord_id`, but the Supabase JWT will not reflect the new tier until the user's next token refresh (~1 hour default). For immediate reflection on web and mobile, the handler must also update `auth.users.app_metadata.tier` via the Supabase Admin API.

**New function to add to `routes/whop.py`:**
```python
async def push_tier_to_supabase_auth(supabase_auth_id: str, tier: str) -> None:
    """Push updated tier into Supabase auth.users app_metadata for immediate JWT reflection."""
    if not supabase_auth_id:
        return
    try:
        from supabase import create_client
        client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )
        client.auth.admin.update_user_by_id(
            supabase_auth_id,
            {"app_metadata": {"tier": tier}}
        )
    except Exception as e:
        logger.exception(f"Failed to push tier to Supabase auth: {e}")
```

This requires `supabase_auth_id` to be stored in `public.users` — supplied by migration 008.

**Note on lookup:** The webhook knows `discord_id`, not `supabase_auth_id`. The handler must do a DB lookup:
```python
result = client.table("users").select("supabase_auth_id").eq("discord_id", discord_id).single().execute()
supabase_auth_id = result.data.get("supabase_auth_id") if result.data else None
```

If `supabase_auth_id` is NULL (Discord-only user, no web account yet), skip the admin API call gracefully.

**Confidence:** HIGH — existing webhook handler inspected; Supabase admin API documented

---

### Pattern 3: Feature Gating Middleware

**Next.js (new file `apps/web/src/middleware.ts`):**
```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

const TIER_ORDER = { free: 0, pro: 1, sharp: 2 } as const

const ROUTE_REQUIREMENTS: Record<string, 'pro' | 'sharp'> = {
  '/dashboard/portfolio':   'pro',
  '/dashboard/value-plays': 'pro',
  '/dashboard/arb':         'sharp',
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const requiredTier = ROUTE_REQUIREMENTS[pathname]
  if (!requiredTier) return NextResponse.next()

  const response = NextResponse.next()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get:    (n)    => request.cookies.get(n)?.value,
        set:    (n, v) => response.cookies.set(n, v),
        remove: (n)    => response.cookies.delete(n),
      },
    }
  )
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  const userTier = (session.user.app_metadata?.tier ?? 'free') as keyof typeof TIER_ORDER
  const hasAccess = TIER_ORDER[userTier] >= TIER_ORDER[requiredTier]

  if (!hasAccess) {
    return NextResponse.redirect(new URL('/upgrade', request.url))
  }

  return response
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
```

**Flutter (extend existing `app_state.dart`):**
```dart
// Add to AppState class — reads from AuthService.currentTier (JWT, no API call)
bool get hasProAccess {
  final tier = authService.currentTier;
  return tier == 'pro' || tier == 'sharp';
}

bool get hasSharpAccess => authService.currentTier == 'sharp';
```

Gate UI in Flutter screens:
```dart
appState.hasProAccess
  ? const ValuePlaysScreen()
  : UpgradePromptWidget(requiredTier: 'pro')
```

**Discord bot:** The existing `@require_tier(Tier.PRO)` decorator in `tier_check.py` already works correctly. It queries `public.users` by `discord_id` using the service key. No change required.

**Confidence:** HIGH — Next.js middleware pattern verified; Flutter pattern from existing provider code

---

### Pattern 4: Discord Bot Subscription Verification

**How the bot checks tier:**
1. User runs `/value` slash command
2. `@require_tier(Tier.PRO)` decorator fires
3. `get_or_create_user(discord_id)` queries `public.users` by `discord_id`
4. Compares `user.tier` against `min_tier` using `_TIER_ORDER` dict
5. Blocks with upgrade embed or allows execution

This is already correct and complete. The Whop webhook keeps `public.users.tier` current; the bot reads from it.

**Fallback for delayed webhooks:** `subscription_service.py` already has `get_user_memberships(whop_api_key, discord_id)` which calls Whop API directly. Use this as a manual `/refresh-tier` command, not on every slash command invocation.

**Confidence:** HIGH — code inspected directly

---

### Schema Changes Required (Migration 008)

```sql
-- packages/database/src/sharpedge_db/migrations/008_auth_bridge.sql

-- 1. Bridge column: links Supabase Auth UUID to the existing discord_id-keyed row
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS supabase_auth_id UUID UNIQUE,
  ADD COLUMN IF NOT EXISTS whop_membership_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id
  ON public.users(supabase_auth_id);

-- 2. RLS: web/mobile users can read and update their own row
CREATE POLICY "User reads own record"
  ON public.users FOR SELECT
  USING (auth.uid() = supabase_auth_id);

CREATE POLICY "User updates own bankroll"
  ON public.users FOR UPDATE
  USING (auth.uid() = supabase_auth_id)
  WITH CHECK (auth.uid() = supabase_auth_id);

-- 3. Auto-create public.users row when a new Supabase Auth user signs up
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

-- 4. Custom Access Token Hook (see Pattern 1 above)
-- Register via Supabase Dashboard → Authentication → Hooks
```

---

### Account Linking: Web Signup → Discord Link

When a user creates a Supabase email account on web, they need to connect their Discord identity so Whop webhook updates (keyed on `discord_id`) flow to their Supabase JWT.

```
Step 1: User signs up on web (email/password)
  → Supabase creates auth.users row (UUID assigned)
  → Trigger handle_new_auth_user fires
  → INSERT public.users(supabase_auth_id=UUID, tier='free')
  → Custom Access Token Hook injects tier='free' into JWT

Step 2: User clicks "Connect Discord" in account settings
  → OAuth redirect to Discord
  → Discord redirects to /auth/callback?provider=discord&code=...
  → apps/web/src/app/auth/callback/route.ts exchanges code
  → extract discord_id from Supabase identity provider data
  → UPDATE public.users SET discord_id=$discord_id
      WHERE supabase_auth_id=$current_user_uuid

Step 3: User subscribes via Whop
  → Whop fires membership.went_valid with discord_id
  → Webhook: UPDATE public.users SET tier='pro' WHERE discord_id=$discord_id
  → Webhook: lookup supabase_auth_id from public.users
  → Webhook: Supabase Admin API update_user_by_id(app_metadata.tier='pro')
  → Web/mobile: next JWT refresh includes tier='pro'
  → Discord: role added via REST
```

**Note on users who subscribe before linking Discord:** If a user subscribes on Whop but has not connected their Discord account, the webhook fires with `discord_id` only. The tier is written to `public.users` by `discord_id`. The `supabase_auth_id` field remains NULL so `push_tier_to_supabase_auth` is skipped. When the user eventually connects Discord via web, the two rows must be merged (or prevented via email verification on Whop checkout). Simplest mitigation: require Discord OAuth connection before allowing subscription, or show a "Sync subscription" button that triggers a manual Whop API lookup.

---

### Data Flow Diagrams

**New Web User Signup:**
```
User fills email/password form
        ↓
supabase.auth.signUp(email, password)
        ↓
Supabase creates auth.users row (UUID)
        ↓
Trigger: handle_new_auth_user fires
        ↓
INSERT public.users(supabase_auth_id=UUID, tier='free')
        ↓
Custom Access Token Hook fires on JWT issue
        ↓
JWT app_metadata.tier = 'free'
        ↓
Next.js middleware reads tier from JWT (zero DB calls)
        ↓
Free-tier routes accessible; paid routes → /upgrade
```

**User Subscribes on Whop:**
```
User clicks Subscribe link (from bot /subscribe or web)
        ↓
Redirects to whop.com/{slug}/checkout/{product_id}?d={discord_id}
        ↓
User completes payment on Whop
        ↓
Whop fires membership.went_valid (HMAC-SHA256 signed)
        ↓
FastAPI webhook server verifies signature
        ↓
update_user_tier_in_db(discord_id, tier='pro')          [existing]
        ↓
add_discord_role(discord_id, PRO_ROLE_ID)               [existing]
        ↓
Lookup supabase_auth_id from public.users by discord_id [new DB query]
        ↓
push_tier_to_supabase_auth(supabase_auth_id, 'pro')     [new]
        ↓
Supabase Admin API: updateUserById app_metadata.tier='pro'
        ↓
User's next JWT refresh: tier='pro'
        ↓
Web middleware + Flutter feature gates unlock
```

**Discord Bot Command:**
```
User runs /value slash command
        ↓
@require_tier(Tier.PRO) fires
        ↓
get_or_create_user(discord_id) → SELECT public.users by discord_id
        ↓
user.tier == 'pro' or 'sharp'?
  YES → execute command
  NO  → send ephemeral upgrade embed (Whop checkout link)
```

---

### New vs Modified Components

| Component | Status | What Changes |
|-----------|--------|--------------|
| `packages/database/migrations/008_auth_bridge.sql` | **NEW** | `supabase_auth_id` column, RLS policies, `handle_new_auth_user` trigger |
| Supabase Custom Access Token Hook (Postgres fn in migration 008) | **NEW** | Injects `tier` into every JWT |
| `apps/web/src/middleware.ts` | **NEW** | JWT-based route protection for Next.js |
| `apps/web/src/lib/auth.ts` | **NEW** | `getUserTier()` and `getUserSession()` server helpers |
| `apps/web/src/lib/supabase.ts` | **MODIFY** | Upgrade from basic `createClient` to `@supabase/ssr` browser + server clients |
| `apps/web/src/app/auth/callback/route.ts` | **MODIFY** | Add Discord identity extraction and `discord_id` → `supabase_auth_id` link |
| `apps/webhook_server/routes/whop.py` | **MODIFY** | Add `push_tier_to_supabase_auth()` call after `update_user_tier_in_db` |
| `apps/mobile/lib/services/auth_service.dart` | **MODIFY** | Add `currentTier` getter reading `app_metadata` |
| `apps/mobile/lib/providers/app_state.dart` | **MODIFY** | Add `hasProAccess` and `hasSharpAccess` computed getters |
| `apps/bot/middleware/tier_check.py` | **NO CHANGE** | Already correct; queries `public.users` by `discord_id` |
| `apps/bot/services/subscription_service.py` | **NO CHANGE** | Whop API fallback available; use for `/refresh-tier` command only |

---

### Build Order

Dependencies drive this order. Each step explicitly unlocks subsequent steps.

| Step | Work | Justification | Parallelizable? |
|------|------|---------------|-----------------|
| 1 | Write and apply migration 008 | `supabase_auth_id` column is required by all subsequent steps | Blocks everything |
| 2 | Register Custom Access Token Hook in Supabase dashboard | Enables `tier` in JWT; web middleware and mobile gate both require it | After step 1 |
| 3 | Upgrade `apps/web/src/lib/supabase.ts` to `@supabase/ssr` | Required before Next.js middleware can read server-side sessions | After step 1; parallel with step 2 |
| 4 | Write `apps/web/src/middleware.ts` | Tier-based route protection; requires `@supabase/ssr` and JWT with tier claim | After steps 2 + 3 |
| 5 | Update `apps/web/src/app/auth/callback/route.ts` | Discord account linking; requires `supabase_auth_id` column | After step 1; parallel with 2–3 |
| 6 | Add `push_tier_to_supabase_auth` to `routes/whop.py` | Immediate tier propagation on subscription event; requires step 1 | After step 1; parallel with 2–5 |
| 7 | Extend `apps/mobile/lib/services/auth_service.dart` | `currentTier` getter; requires JWT to include `tier` claim (step 2) | After step 2 |
| 8 | Extend `apps/mobile/lib/providers/app_state.dart` | `hasProAccess` getters; requires step 7 | After step 7 |

Steps 2, 3, 5, 6 are parallelizable once step 1 is complete.
Steps 7–8 are parallelizable once step 2 is complete.

---

### Integration Points

**External Services:**

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Whop | Inbound HMAC-SHA256 webhook to FastAPI | Already working. Add `push_tier_to_supabase_auth` after DB update |
| Discord REST API | Direct HTTP from webhook server | Already working. Bot token + guild ID in env vars |
| Supabase Auth | JS `@supabase/ssr` (web), Flutter SDK (mobile), Python `supabase-py` (backend) | Hook registration required in dashboard after migration 008 |
| Supabase DB | Service key bypasses RLS (backend/bot), anon key + RLS (web/mobile) | Migration 008 adds column and RLS policies |

**Internal Boundaries:**

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Webhook server ↔ Supabase DB | `supabase-py` service key | Updates `tier` by `discord_id` (existing) + looks up `supabase_auth_id` (new) |
| Webhook server ↔ Discord | `httpx` REST, Bot token | Role add/remove already implemented |
| Webhook server ↔ Supabase Auth | `supabase-py` admin API | New: `update_user_by_id` to push tier into JWT metadata immediately |
| Next.js ↔ Supabase | `@supabase/ssr` server client in middleware | JWT tier read with no DB call |
| Flutter ↔ Supabase | `supabase_flutter` SDK | `currentUser.appMetadata` available after login |
| Discord bot ↔ Supabase DB | `supabase-py` service key, reads `public.users` by `discord_id` | No change |

---

### Anti-Patterns to Avoid

**Anti-Pattern 1: Querying DB on Every Request for Tier**
What people do: Check `public.users.tier` in every Next.js route handler or API call.
Why it's wrong: Adds DB latency to every page load; doesn't scale; defeats the JWT architecture.
Do this instead: Embed tier in JWT via Custom Access Token Hook. Read from `session.user.app_metadata.tier` — zero DB calls.

**Anti-Pattern 2: Using `user_metadata` for Tier**
What people do: Store subscription tier in `user_metadata` (user-editable) or call `updateUser()` from the client.
Why it's wrong: Any user can call `supabase.auth.updateUser({ data: { tier: 'sharp' } })` to self-upgrade.
Do this instead: Use `app_metadata` only. It is writable only via the service key, admin API, or a `SECURITY DEFINER` Postgres function.

**Anti-Pattern 3: Single Primary Key for Two Identity Systems**
What people do: Keep `discord_id` as the only user key and try to reconcile web users at query time with no bridge column.
Why it's wrong: Webhook updates (keyed on `discord_id`) and web JWT sessions (keyed on Supabase UUID) become permanently inconsistent.
Do this instead: Add `supabase_auth_id UUID UNIQUE` to `public.users`. Both columns coexist. `discord_id` can be NULL for email-only web users; `supabase_auth_id` can be NULL for Discord-only users until they create a web account.

**Anti-Pattern 4: Checking Whop API on Every Bot Command**
What people do: Call `validate_whop_membership()` (Whop REST API) inside the `@require_tier` decorator to confirm subscription is still active.
Why it's wrong: Each slash command fires an outbound HTTP call; bot availability couples to Whop API uptime; rate limits apply.
Do this instead: Trust `public.users.tier` as source of truth. Whop webhooks keep it current. Reserve direct Whop API calls for a `/refresh-tier` command.

**Anti-Pattern 5: Forgetting `detectSessionInUrl: false` on Mobile**
What people do: Initialize Supabase Flutter client without disabling URL-based session detection.
Why it's wrong: On mobile there is no URL to detect sessions from; leaving this enabled can cause unexpected behavior on deep links.
Do this instead: Set `detectSessionInUrl: false` in the Flutter Supabase client config alongside `persistSession: true` and `autoRefreshToken: true`.

---

### Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–1k users | Current synchronous webhook handler is fine. Supabase free tier limits (50k MAU auth) are not a concern. |
| 1k–10k users | Consider queuing Whop webhook processing with Redis + RQ if webhook handler becomes a bottleneck. Supabase Pro tier required. Bot DB queries can be cached in Redis with 5-minute TTL. |
| 10k+ users | Add Supabase read replicas for bot command queries. Horizontal FastAPI replicas. Rate-limit Discord API calls (10 role changes/second per guild per bot). |

**First bottleneck:** Discord REST calls in the webhook handler are synchronous within the async context. At high subscription volume (hundreds/hour), these should be queued or made fire-and-forget with retry. This is not a v3.0 concern.

---

## v2.0: Agent Architecture (Retained)

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONT-ENDS                                                         │
│  Discord Bot  │  Next.js Web (SSE streaming)  │  Flutter Mobile     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────────────┐
│  FastAPI REST Layer  (apps/api/)                                     │
│  /api/v1/copilot/chat  [SSE stream]                                  │
│  /api/v1/value-plays   /api/v1/games/:id/analysis                   │
│  /api/v1/bankroll/simulate  /api/v1/users/:id/portfolio             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Python calls
┌──────────────────────────▼──────────────────────────────────────────┐
│  AGENT LAYER  (packages/agents/)                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LangGraph StateGraph  (BettingAnalysisWorkflow)             │   │
│  │                                                              │   │
│  │  [route_intent] → [fetch_context] → [detect_regime]         │   │
│  │       ↓                                                      │   │
│  │  [run_models] → [calculate_ev] → [validate_setup]           │   │
│  │       ↓                  ↓             ↓ REJECT→END         │   │
│  │  [compose_alpha] → [size_position] → [generate_report]→END  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  BettingCopilot  (conversational — tool-calling loop)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ function calls
┌──────────────────────────▼──────────────────────────────────────────┐
│  QUANTITATIVE ENGINE  (packages/models/, packages/analytics/)       │
│  MonteCarloSimulator │ BettingRegimeDetector │ AlphaComposer        │
│  WalkForwardBacktester │ KeyNumberZoneDetector │ ev_calculator.py   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│  DATA LAYER                                                         │
│  Odds API (30+ books) │ Kalshi │ Polymarket │ ESPN │ Weather        │
│  Redis (hot cache)    │ Supabase (persistent store)                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Package / Module | Responsibility | Communicates With |
|-----------|-----------------|----------------|-------------------|
| `BettingAnalysisWorkflow` | `packages/agents/src/sharpedge_agents/workflow.py` | LangGraph StateGraph — routes bet analysis requests through 9 specialist nodes | Quant engine modules, data feed clients |
| `BettingCopilot` | `packages/agents/src/sharpedge_agents/copilot.py` | Stateful conversational agent using tool-call loop against CopilotSnapshot | All quant engine modules via tool wrappers |
| `BettingSetupEvaluator` | `packages/agents/src/sharpedge_agents/evaluator.py` | LLM gate (GPT-4o-mini) — validates each candidate alert before report node | Called from `validate_setup` graph node only |
| `MonteCarloSimulator` | `packages/models/src/sharpedge_models/monte_carlo.py` | Simulate 2000 bankroll paths; return ruin probability, percentile outcomes, max drawdown | Called by `size_position` node; exposed as copilot tool and `/bankroll/simulate` endpoint |
| `BettingRegimeDetector` | `packages/analytics/src/sharpedge_analytics/regime.py` | Classify betting market state into one of 7 regimes | Called by `detect_regime` node; output stored in `BettingAnalysisState.regime_state` |
| `AlphaComposer` | `packages/models/src/sharpedge_models/alpha.py` | Compute composite alpha = edge_prob × ev_score × regime_scale × survival_prob × confidence_mult | Called by `compose_alpha` node |
| `WalkForwardBacktester` | `packages/models/src/sharpedge_models/walk_forward.py` | Sliding-window out-of-sample validation; produces quality badge | Background job, not hot path |
| `KeyNumberZoneDetector` | `packages/analytics/src/sharpedge_analytics/key_numbers.py` | Detects proximity to NFL/NBA/MLB/NHL clustering numbers; adjusts alpha | Called within `calculate_ev` node |
| FastAPI layer | `apps/api/` | REST + SSE endpoints consumed by web and mobile | Agent layer, quant engine, Supabase, Redis |
| Discord Bot | `apps/bot/` | Slash commands + alert dispatch | FastAPI layer or direct agent layer calls |

### LangGraph Node Groupings by LLM Cost

| Tier | Nodes | LLM | Rationale |
|------|-------|-----|-----------|
| No LLM | `fetch_context`, `detect_regime`, `run_models`, `calculate_ev`, `compose_alpha`, `size_position` | None | Pure I/O or math |
| GPT-4o-mini | `route_intent`, `validate_setup` | GPT-4o-mini | Routing + gate — low-stakes classification |
| GPT-4o | `generate_report` | GPT-4o | Explanation quality matters |

### Anti-Patterns to Avoid (Agent Architecture)

**Anti-Pattern 1: Putting I/O Inside Quant Modules**
Quant modules must be pure functions. Nodes own I/O; quant modules receive plain Python dicts and return results.

**Anti-Pattern 2: Calling `analyze_game` for Every Game in Background Scan**
Run deterministic nodes first (no LLM); invoke LLM nodes only for games clearing the alpha threshold. Otherwise costs scale linearly with game count.

**Anti-Pattern 3: Storing Full CopilotSnapshot in Graph State**
Snapshot hydration is a Python object in the copilot class, not in the graph state. Large state inflates LangGraph checkpoint size.

---

## Sources

- [Supabase Custom Access Token Hook](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook) — HIGH confidence
- [Supabase JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields) — HIGH confidence
- [Supabase Custom Claims and RBAC](https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac) — HIGH confidence
- [Supabase User Management (triggers)](https://supabase.com/docs/guides/auth/managing-user-data) — HIGH confidence
- [Expo / Supabase Guide](https://docs.expo.dev/guides/using-supabase/) — HIGH confidence
- [Whop Discord Integration](https://docs.whop.com/memberships-and-access/access-discord-server/access-a-discord-server) — MEDIUM confidence (behavior confirmed by existing codebase)
- Existing codebase: `apps/webhook_server/routes/whop.py`, `apps/bot/middleware/tier_check.py`, `packages/database/migrations/001_initial_schema.sql`, `apps/mobile/lib/services/auth_service.dart` — HIGH confidence (direct inspection)

---

*Architecture research for: SharpEdge v3.0 — cross-platform auth, subscription gating, and Whop↔Supabase↔Discord sync*
*Researched: 2026-03-21*
