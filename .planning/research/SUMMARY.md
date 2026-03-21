# Project Research Summary

**Project:** SharpEdge v3.0 — Launch & Distribution
**Domain:** Multi-platform sports analytics SaaS — web (Next.js 14) + mobile (Flutter) + Discord community + FastAPI backend; Whop monetization, Supabase auth, App Store distribution
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH
**Supersedes:** v2.0 SUMMARY.md (2026-03-13)

---

## Executive Summary

SharpEdge v3.0 is a distribution milestone, not a product milestone. The core quant engine, web app, Flutter mobile app, Discord bot, and FastAPI backend are all built (v2.0 complete through Phase 15). The v3.0 work is deploying everything to production, getting both mobile apps approved on the App Store and Play Store, standing up a monetized Discord community with proper tier gating, and building a marketing landing page. The primary technical blocker is a schema gap: `public.users` is missing a `supabase_auth_id` column, which means web and mobile JWT-based tier enforcement and immediate Whop→Supabase tier sync cannot function. Migration 008 adding this bridge column is the single dependency that gates the majority of auth and feature-gate work across web, mobile, and the webhook server. Everything else can be sequenced in parallel after that migration lands.

The recommended approach is three parallel execution tracks after the schema blocker is resolved: (1) auth bridge and deployment infrastructure (web on Vercel Pro, Python services on Railway, CI/CD for all), (2) Discord community setup with content seeding before the server goes public, and (3) App Store submission preparation. Mobile store submission should be staggered 2–4 weeks after web and Discord go live — this decouples the launch date from Apple's unpredictable review timeline, and gives the Discord community time to generate the track record content and activity that converts users who find the app organically on the App Store. The landing page is low-effort and should ship alongside the Discord launch.

The two highest-risk items for the entire v3.0 milestone are the iOS IAP bypass decision and the Whop→Discord role sync reliability. Apple will reject the iOS app under Guideline 3.1.1 if any payment UI or Whop links appear in the app — the correct fix is a read-only companion pattern (no pricing, no upgrade buttons, no external payment links; users subscribe on web and the tier flows through the JWT). Whop→Discord role sync fails silently in three documented failure modes; all three have clear mitigations that must be implemented before the first paid subscriber arrives, not after. Both of these decisions must be locked in during architecture and setup phases, before UI or store submission work begins.

---

## Key Findings

### Recommended Stack

The deployment stack for each component is well-defined and research-confirmed. Web goes on Vercel Pro — the Hobby plan explicitly prohibits commercial use and has stricter function limits; Pro is required from day one for a paying SaaS. Python services (FastAPI webhook server and the Discord bot) go on Railway as two separate services from the same repo. Railway's always-on process model is the correct choice for the Discord bot, which maintains a persistent WebSocket connection to Discord's gateway — Render's free tier would kill this connection after 15 minutes of inactivity. Mobile CI/CD uses Fastlane + GitHub Actions. This is a critical correction from any prior notes referencing EAS Build or Expo — EAS Build is an Expo-only product that does not apply to the Flutter codebase. iOS builds require a `macos-latest` GitHub Actions runner; Android builds run on `ubuntu-latest`; both jobs run in parallel. Sentry error tracking is added to all three platforms using one Sentry organization with three projects. UptimeRobot free tier monitors the health endpoints and posts alerts to a private Discord `#ops` channel.

**Core technologies:**
- Vercel Pro: Next.js 14 hosting — zero-config deploy on push to main, commercial use permitted, required for SaaS
- Railway: FastAPI webhook server + Discord bot — always-on process model, GitHub auto-deploy, two separate services
- Fastlane + GitHub Actions: Flutter mobile CI/CD — parallel iOS (macOS runner) and Android (ubuntu runner) jobs
- Fastlane match: iOS certificate management — encrypted private cert repo, avoids 2FA issues in CI
- Sentry (3 projects): Error tracking for web (`@sentry/nextjs ^8.x`), mobile (`sentry_flutter ^8.x` stable, not 9.x beta), Python services (`sentry-sdk ^2.x`)
- UptimeRobot (free): Health endpoint monitoring with Discord webhook alerts to private ops channel

**Version constraints to verify before building:**
- `sentry_flutter ^8.x` stable — 9.x is beta as of research date; do not pin beta in production
- `@supabase/ssr` required for Next.js middleware server-side session reading — existing `supabase.ts` uses basic `createClient` which does not support server-side session in middleware
- Flutter SDK must be >=3.24.0 to meet `sentry_flutter ^8.x` requirements — `pubspec.yaml` specifies `'>=3.10.0'`; verify installed SDK version before adding Sentry to mobile

See `.planning/research/STACK.md` for the full deployment architecture diagram, all alternatives considered, App Store compliance checklist, and library version compatibility table.

---

### Expected Features

The v3.0 feature set is about distribution infrastructure and conversion mechanics, not new quant capabilities. The quant engine is built. What is missing is the channel structure, content strategy, pricing setup, and store presence that converts traffic into paying subscribers.

**Must have at launch (P1 — revenue blocked without these):**
- Discord 3-tier channel structure (free visible to all, Mid and Premium gated) + Whop bot automated role assignment — without this, payment unlocks nothing
- Bot posting daily free-tier edges — minimum one post per day; empty server is the primary Discord failure mode
- `#track-record` channel with automated weekly model performance posts — sports bettors are scam-wary; transparent track record is the primary trust signal
- Migration 008 (`supabase_auth_id` column) + Custom Access Token Hook registered in Supabase — gates web middleware and mobile feature gating
- Landing page with single CTA, benefit-driven headline, pricing tiers, and 3 real performance data points
- App Store listing with 17+ age rating, live privacy policy URL, keyword-optimized title/subtitle, 6 captioned screenshots
- 3-email onboarding sequence (Day 0: welcome + today's free edge; Day 3: what Pro members saw this week; Day 7: early-adopter upgrade CTA)
- `/upgrade` bot command posting Whop checkout link inline — removes the friction of leaving Discord to find the payment page

**Should have within 30 days of launch (P2 — conversion impact):**
- Behavior-triggered upgrade prompt (user runs a bot command → DM with Whop checkout link fires within minutes) — requires event tracking in place first
- App Store preview video (15–30 seconds) — research-confirmed 10–30% conversion lift
- Custom App Store Product Pages for 2–3 keyword variants — multiplies keyword surface area
- Live model output embed on landing page — proves the engine is real before signup

**Defer to v3.1+ (confirmed anti-features for v3.0):**
- Referral/affiliate program — calibrate incentive amounts after 60 days of conversion data
- Admin dashboard for user management — Supabase and Whop dashboards are sufficient until ~200 users
- Content marketing/blog/newsletter — high ongoing time cost, slow SEO ROI; build-in-public on X is faster
- In-app community or social features — keep community in Discord where it belongs

**Critical freemium gate design decision:** Free tier must create desire without satisfying it. The free experience shows "Edge detected" with sport, market, and direction — but no line, no confidence interval, no Kelly sizing, no line movement alerts, and no historical performance data. All of those are Mid tier unlocks. The upgrade prompt fires at the moment of maximum friction: when the user sees the teaser and cannot get the detail. A free tier that includes Kelly sizing or multiple full edge recommendations will not convert above 2%.

**Pricing recommendation:** Mid tier at $39–$49/month (not $19–$29 — underpricing signals low confidence in the edge quality and fails the credibility test for serious bettors). Premium tier at $99–$149/month. One successful +EV edge play recovers the Mid tier monthly cost; the landing page should make this math explicit.

See `.planning/research/FEATURES.md` for the full prioritization matrix, MVP definition, competitor comparison (OddsJam has no Discord strategy — the gap is real), and onboarding sequence detail.

---

### Architecture Approach

The central architectural problem is a two-identity-system mismatch. The existing `public.users` table was built with `discord_id` as the primary user key because the product was Discord-first. Web and mobile users sign in via Supabase Auth (email/password), which creates a separate UUID in `auth.users`. These two identities are currently unlinked in the schema. Migration 008 resolves this by adding `supabase_auth_id UUID UNIQUE` to `public.users` as the bridge column, a trigger that auto-creates a `public.users` row when a Supabase Auth user signs up, RLS policies scoping reads and writes to the authenticated user's own row, and the Custom Access Token Hook Postgres function that injects the user's `tier` from `public.users` into every JWT at issue time.

Once the Custom Access Token Hook is registered, `tier` flows into `app_metadata.tier` in the JWT — Next.js middleware reads it from the session object with zero database calls, and Flutter reads it from `currentUser.appMetadata` with no additional network request. The Whop webhook handler also needs a new `push_tier_to_supabase_auth()` call after its existing `update_user_tier_in_db()` — this pushes the updated tier directly into `auth.users.app_metadata` via the Supabase Admin API, eliminating the ~1-hour JWT refresh delay that would otherwise follow a subscription event.

**Major components and their status:**

| Component | Status | Key Change Required |
|-----------|--------|---------------------|
| `public.users` (Supabase DB) | Exists — incomplete | Add `supabase_auth_id` column + trigger + RLS (migration 008) |
| Custom Access Token Hook (Postgres fn) | Does not exist | New — injects `tier` into every JWT |
| `apps/web/src/middleware.ts` | Does not exist | New — JWT-based route protection |
| `apps/web/src/lib/supabase.ts` | Exists — basic | Upgrade to `@supabase/ssr` for server-side session reading |
| `apps/web/src/app/auth/callback/route.ts` | Stub — incomplete | Add Discord identity extraction and account-link logic |
| `apps/webhook_server/routes/whop.py` | Exists — partial | Add `push_tier_to_supabase_auth()` after `update_user_tier_in_db` |
| `apps/mobile/lib/services/auth_service.dart` | Exists — partial | Add `currentTier` getter reading `app_metadata` |
| `apps/mobile/lib/providers/app_state.dart` | Exists — partial | Add `hasProAccess` / `hasSharpAccess` computed getters |
| `apps/bot/middleware/tier_check.py` | Exists — complete | No change required |

**Build order within the auth phase:** Migration 008 is the absolute blocker. After it lands, steps for registering the hook, upgrading `supabase.ts`, updating `auth/callback`, and adding `push_tier_to_supabase_auth` to the webhook handler are all parallelizable. Flutter tier reading (auth_service.dart + app_state.dart) can start after the hook is registered.

**Critical anti-pattern to avoid:** Do not store subscription tier in `user_metadata` (user-editable — any user can self-upgrade via `supabase.auth.updateUser()`). Use `app_metadata` only, which is writable only via service key, admin API, or a `SECURITY DEFINER` Postgres function.

See `.planning/research/ARCHITECTURE.md` for the full Postgres function SQL, Next.js middleware code, Flutter getter code, all data flow diagrams, account-linking sequence, and the build order table with parallelization notes.

---

### Critical Pitfalls

**1. iOS IAP bypass — highest risk, structural decision required before mobile UI build.**
If the iOS app contains any button labeled "Subscribe," "Upgrade," or "Unlock," or any URL pointing to Whop or a payment page, Apple rejects under Guideline 3.1.1. The entire v3.0 monetization routes through Whop (web-based). The correct resolution is the read-only companion pattern: iOS app displays data for existing subscribers, detects tier from the Supabase JWT on login, gates features accordingly, but never shows pricing or payment UI. Users subscribe on web; the tier propagates through the JWT. This is the pattern used by BettingPros and Action Network — both live on the App Store. This decision must be made before mobile UI is built; retrofitting it after build is expensive.

**2. App Store metadata rejection — gambling-adjacent language.**
Apple's human reviewers flag apps that describe themselves as betting tools rather than analytics tools. Every approved comparable (BettingPros, Rithmm, Pikkit, Action Network, OddsJam) uses the same formula: a disclaimer in the first 3 sentences of the description ("for entertainment and informational purposes only, no real-money wagering facilitated"), language emphasizing "analytics," "probability," "data" over "betting tips" or "find profitable bets," and screenshots showing probability charts rather than dollar amounts or sportsbook interfaces. App name and subtitle should avoid "betting," "wagers," or "odds" without a qualifying "Analytics" or "Insights" modifier. Age rating must be set to 17+ explicitly via the App Store Connect questionnaire.

**3. Whop→Discord role sync silent failures.**
The most common failure mode for Discord-first monetization: user pays, Whop fires the webhook, role is never assigned, user opens a support ticket or requests a refund. Three distinct silent failure modes: (a) Whop Bot role is not at the top of the server's role hierarchy — bot silently fails to assign any role below it; (b) user has not yet joined the Discord server at time of purchase — webhook fires, no member to assign to, Whop does not retry; (c) webhook endpoint returns 200 despite internal failure — event is lost. Mitigations: move the Whop Bot role to the top before any paid users exist, direct users to join Discord before completing purchase, add Sentry error tracking to the webhook handler so role assignment failures surface as alerts instead of silent 200s, enable the Whop bot event log channel in a private admin channel.

**4. Dead Discord server at launch — the empty room problem.**
A server with no activity when the first outsiders arrive creates a negative signal loop: new members see silence, post nothing, leave forever. The mitigation is content before community: post 7 days of daily bot-generated content before the first public invite goes out, recruit 10–20 seed members from personal network and beta testers briefed to be active the first week, wire the bot to post real SharpEdge output (top edges, line movement alerts, market regime) daily in a `#free-picks` channel. The server should look like it has been running for a week before the public ever sees it.

**5. Freemium gate calibration — the free tier gives too much.**
If free users can see Kelly sizing, multiple full edge recommendations, or line movement alerts, conversion stays below 2% indefinitely. Free tier shows one teaser edge per day with no detail. Mid tier unlocks full line, confidence interval, Kelly sizing, live odds, and movement alerts. The upgrade prompt fires at the moment of maximum friction. Feature gating must be enforced server-side at the Supabase RLS and API middleware layer — not just in the UI, where a free-tier JWT could call paid-tier endpoints directly.

---

## Implications for Roadmap

Phases continue from Phase 16 (last completed was Phase 15 in v2.0). The work falls into four parallel tracks with clear dependency constraints. Recommended sequence:

1. Auth bridge + deployment infrastructure (unblocks all subsequent auth and feature-gate work)
2. Discord community setup + content seeding (parallel to infra; critical path for launch credibility)
3. Landing page + onboarding sequence (parallel to infra; low effort, high conversion ROI)
4. Mobile store submission (staggered 2–4 weeks after web and Discord go live)

---

### Phase 16: Auth Bridge and Schema Migration

**Rationale:** Migration 008 and the Custom Access Token Hook are hard dependencies for every auth-related task across web, mobile, and the webhook server. This phase has no external blockers and can start immediately. Nothing in v3.0 auth works correctly until this is deployed.

**Delivers:** `supabase_auth_id` bridge column live in production Supabase, Custom Access Token Hook registered and verified emitting `tier` in all JWTs, `handle_new_auth_user` trigger auto-creating `public.users` rows for new Supabase signups, RLS policies on `public.users` scoping reads and writes to the authenticated user.

**Addresses:** Cross-platform auth consistency, immediate tier propagation on subscription events, web middleware prerequisite, mobile feature gate prerequisite.

**Avoids:** Two-identity inconsistency anti-pattern (ARCHITECTURE.md Anti-Pattern 3), ~1-hour JWT refresh delay after Whop subscription event.

**Research flag:** Standard patterns — Supabase Custom Access Token Hook is officially documented with working SQL examples at HIGH confidence. No additional research needed before planning this phase.

---

### Phase 17: Web Deployment and Feature Gating

**Rationale:** Depends on Phase 16 (JWT must contain `tier` before middleware can read it). Vercel project creation and environment variable setup have no schema dependency and can start immediately in parallel with Phase 16.

**Delivers:** Next.js web app live on Vercel Pro at production domain, `apps/web/src/middleware.ts` protecting paid routes using JWT tier claim with zero DB calls, `@supabase/ssr` upgrade complete across the web app, `auth/callback` route linking Discord OAuth identity to Supabase account, FastAPI webhook server and Discord bot running as separate services on Railway, GitHub Actions CI gates (test jobs blocking merge to main for both web and Python services).

**Uses:** Vercel Pro, Railway, `@supabase/ssr`, Sentry for Next.js and Python, UptimeRobot.

**Avoids:** Vercel Hobby plan (commercial use prohibited), Render for the Discord bot (sleep mode kills persistent WebSocket).

**Research flag:** Standard patterns — Vercel, Railway, and `@supabase/ssr` middleware are all well-documented. No additional research needed.

---

### Phase 18: Discord Community Setup and Content Seeding

**Rationale:** Channel structure and content seeding have no dependency on the schema migration and can start immediately. However, the server must not be made publicly visible until bot posting is confirmed working and at least 7 days of content is pre-seeded. This is the highest-ROI distribution work for the first paying subscribers.

**Delivers:** Discord server with 3-tier channel structure (free visible, Mid and Premium gated), Whop→Discord role assignment tested end-to-end with a real test subscription before any public users, Whop Bot role verified at the top of the server's role hierarchy, 7 days of pre-seeded bot-generated content in free channels, 10–20 seed members recruited and active before server goes public, `#track-record` channel with first automated model performance post, `/upgrade` bot command live, event log channel monitoring every role assignment, Sentry error tracking on the webhook handler confirming role assignment failures surface as alerts.

**Addresses features:** Discord tier structure, bot-automated daily edge posts, track record channel (trust signal), upgrade prompt, onboarding flow.

**Avoids:** Dead server at launch (Pitfall 4), Whop→Discord role sync failures (Pitfall 7).

**Research flag:** Verify Whop's current webhook retry behavior and idempotency guarantees in the Whop developer docs before finalizing the webhook handler — if Whop retries on timeout, the handler needs idempotency keys to prevent duplicate role assignments. This is a targeted verification task, not a full research phase.

---

### Phase 19: Marketing Landing Page and Onboarding Sequence

**Rationale:** No hard technical dependencies beyond a live production domain. Can be built and deployed in parallel with Phases 16–18. Should go live alongside or immediately before the Discord server opens to the public, so any traffic the launch generates has somewhere credible to land.

**Delivers:** Static landing page (SSG or static export) with single CTA ("Join Discord Free"), benefit-driven headline (outcome language, not feature language), three-column pricing tiers showing Mid at $39–$49 and Premium at $99–$149, three real model performance data points as social proof, mobile-responsive design under 3-second load, live privacy policy URL (required before App Store submission). Three-email onboarding sequence wired to fire via the Discord bot DM and/or email: Day 0 (welcome + today's free edge), Day 3 (what Pro members saw this week), Day 7 (early-adopter upgrade CTA with price anchor).

**Addresses features:** Landing page conversion, onboarding sequence, pricing credibility, social proof via model track record data.

**Avoids:** Hidden pricing (kills comparison shoppers), multiple competing CTAs in the hero (dilutes single conversion goal), vague "institutional-grade" headline copy that means nothing to a skeptical visitor.

**Research flag:** Standard patterns — landing page CRO is well-researched across multiple verified sources. No additional research needed. Do not A/B test at launch — insufficient traffic for statistical significance.

---

### Phase 20: Mobile App Store Submission (iOS + Android)

**Rationale:** Stagger this 2–4 weeks after Phases 17–19 go live. Reasons: Apple review takes 1–3 days per cycle and a first-time sports analytics app should budget 2 full cycles (up to 2 weeks); the Discord server will have real daily content and a working track record channel by the time App Store users arrive; mobile-specific failure modes (privacy manifest, credential mismatch, metadata language) need to be resolved without blocking the web and Discord launch. Staggering isolates launch date from Apple's timeline.

**Delivers:** iOS app live on App Store — 17+ rating, zero payment UI, read-only companion pattern confirmed, keyword-optimized metadata using approved-app formula, privacy manifest (`PrivacyInfo.xcprivacy`) configured before first build, App Store Connect metadata complete before first submission, TestFlight beta period completed before App Review submission. Android app live on Play Store via internal track promoted to production. Fastlane + GitHub Actions CI/CD pipeline with parallel iOS and Android jobs running on correct runner types. Push notifications tested on a physical device via EAS `preview` build profile before submission.

**Uses:** Fastlane, Fastlane match, GitHub Actions macOS runner, App Store Connect API Key, Google Play Service Account, `flutter_native_splash`, `package_info_plus`, `url_launcher`.

**Avoids:** IAP bypass rejection (read-only companion pattern — zero payment UI in iOS app); gambling-adjacent metadata rejection (approved-app description formula); privacy manifest rejection (configure before first build, not after first rejection); EAS credential mismatch (use EAS-managed credentials from day one, never manually create certificates in the Apple Developer portal); App Store Connect metadata gap (complete all required fields before first `eas submit`).

**Research flag:** This phase has the most novel failure modes and the most external dependencies. Recommend a `/gsd:research-phase` pass on: (a) current Apple App Review turnaround for sports analytics apps in 2026; (b) Google Play first-upload manual requirement (Play Console web UI vs API — affects CI/CD pipeline design); (c) whether any EAS-specific Fastlane behavior has changed for Flutter projects since Jan 2026 tutorials.

---

### Phase 21: Monitoring, Error Tracking, and Post-Launch Instrumentation

**Rationale:** Monitoring infrastructure should be operational before the first public user hits the system. Can be built in parallel with Phases 16–20. Becomes critical at the moment of public launch.

**Delivers:** Sentry configured across all three platforms (web, mobile, Python) with `production` and `staging` environment tags, UptimeRobot monitoring the FastAPI `/health` endpoint and the web domain with Discord webhook alerts to private `#ops` channel, Discord bot health check routed through FastAPI (bot pings a Redis key; FastAPI reads it), Sentry alerts on any exception in the webhook role-assignment handler so sync failures surface as alerts instead of silent 200s.

**Addresses:** Webhook event loss, role sync failure visibility, Discord bot downtime detection.

**Research flag:** Standard patterns — Sentry and UptimeRobot are fully documented. No additional research needed.

---

### Phase Ordering Rationale

- **Phase 16 first** because the `supabase_auth_id` column and Custom Access Token Hook are hard blockers for web middleware, mobile tier reading, and immediate Whop tier sync. No auth-related work in any subsequent phase is correct without this.
- **Phases 17, 18, 19 in parallel** after Phase 16 is deployed. Web deployment, Discord setup, and landing page have no interdependencies. All three should target the same public launch date.
- **Phase 20 staggered 2–4 weeks later** to decouple launch date from Apple's review timeline and to ensure the Discord community has visible activity and a track record when App Store users arrive.
- **Phase 21 parallel to all** — monitoring should be live before public launch.
- **Discord content seeding (Phase 18) must complete before any public promotion** — the empty room problem has no technical fix, only a sequencing fix.

---

### Research Flags

**Needs phase-specific research before writing the plan:**
- **Phase 20 (mobile submission):** Apple App Review current turnaround, Google Play first-upload manual requirement, any Fastlane/Flutter CI changes since Jan 2026 tutorials. Run `/gsd:research-phase` before Phase 20 planning.

**Targeted verification tasks (not full research-phase, but must resolve before implementation):**
- **Phase 18 (Whop webhook):** Confirm Whop webhook retry behavior and idempotency guarantees in Whop developer docs before finalizing the webhook handler design.
- **Phase 20 (Flutter SDK):** Verify installed Flutter SDK version is >=3.24.0 before adding `sentry_flutter` to `pubspec.yaml`.

**Standard patterns — skip research-phase:**
- Phase 16 (schema migration): Supabase Custom Access Token Hook is officially documented at HIGH confidence.
- Phase 17 (web deployment): Vercel Pro + Railway are standard, well-documented.
- Phase 19 (landing page): Landing page CRO patterns are thoroughly researched.
- Phase 21 (monitoring): Sentry and UptimeRobot are fully documented.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Web and Python deployment patterns confirmed via live docs. Flutter Fastlane CI/CD pattern confirmed by multiple Jan 2026 tutorials. Sentry version numbers from pub.dev and npm as of research date — verify `sentry_flutter` version before pinning. |
| Features | MEDIUM-HIGH | Quant engine features HIGH confidence from prior v2.0 research (retained). Launch and distribution features (Discord pricing benchmarks, onboarding sequence design, CRO patterns) MEDIUM confidence from web research conducted 2026-03-21 with cited sources. |
| Architecture | HIGH | Custom Access Token Hook verified against official Supabase docs. Existing webhook handler, tier check middleware, and mobile auth service inspected directly from codebase. The bridge column pattern and JWT injection are mechanically correct. |
| Pitfalls | MEDIUM-HIGH | iOS IAP bypass (Guideline 3.1.1) is HIGH confidence — explicit, actively enforced, no ambiguity. App Store metadata language risks MEDIUM — based on analysis of approved comparable apps, not Apple's internal review criteria. Whop role sync failure modes HIGH confidence from official Whop docs. Freemium conversion pitfalls HIGH confidence from a16z, Userpilot, OpenView research. |

**Overall confidence:** MEDIUM-HIGH

The main residual uncertainties are Apple's current App Review timeline, Google Play's first-upload requirement as of 2026, and Whop's current webhook retry/idempotency behavior. None of these block planning for Phases 16–19. They must be resolved before Phase 20 planning begins.

---

### Gaps to Address

**1. iOS app scope decision (founder decision, not a research gap):** The read-only companion pattern means iOS users never see pricing or payment UI. The exact feature set visible to a free-tier iOS user versus a paid-tier iOS user needs to be specified before mobile UI development begins in Phase 20. This gates Phase 20 scope definition.

**2. Pricing finalization (founder decision):** FEATURES.md cites $19–$29 for Mid tier based on Discord community benchmarks. PITFALLS.md argues $39–$49 based on perceived-value logic for serious bettors. The roadmapper should flag this as a decision point before Phase 19 (landing page) planning.

**3. Whop webhook idempotency:** Both PITFALLS.md and ARCHITECTURE.md note that Whop's webhook retry behavior needs verification. If Whop retries on timeout, the handler must use idempotency keys to prevent duplicate role assignments. Verify in Whop developer docs before Phase 18 implementation begins.

**4. Flutter SDK version:** `pubspec.yaml` specifies `flutter: '>=3.10.0'` but `sentry_flutter ^8.x` requires `>=3.24.0`. The actual installed Flutter SDK version must be verified in the CI environment before the Phase 20 CI/CD pipeline is written.

**5. Apple App Review timeline for 2026:** Research assumes 1–3 days per cycle based on historical data. Build a minimum 2-week buffer into Phase 20 timeline and treat approval date as unknown until the first review cycle completes.

**6. Google Play first-upload requirement:** PITFALLS.md flags that the first Android AAB upload must be done manually via the Play Console web UI, not via Fastlane or EAS Submit API. This is a one-time constraint that affects Phase 20 CI/CD pipeline sequencing. Verify this is still current in 2026 before writing the Phase 20 plan.

---

## Sources

### Primary (HIGH confidence)
- Supabase Custom Access Token Hook official docs — verified Postgres function pattern and dashboard registration flow
- Supabase JWT Claims Reference — `app_metadata` vs `user_metadata` security distinction
- Supabase User Management official docs — `handle_new_auth_user` trigger pattern
- Apple IAP Guideline 3.1.1 — IAP bypass rules, explicit and actively enforced
- Expo EAS GitHub issues (official repo) — ITMS-90748, provisioning mismatch patterns, privacy manifest tracking issue #27796
- Whop Discord integration official docs — role hierarchy requirement, webhook behavior, event log channel
- a16z freemium optimization research — free tier design principles
- Userpilot + OpenView Partners — freemium conversion rate benchmarks
- BettingPros, OddsJam, Action Network, Rithmm, Pikkit (live App Store listings) — approved comparable app metadata analysis

### Secondary (MEDIUM confidence)
- Vercel pricing page (March 2026) — Hobby vs Pro commercial use restriction
- Railway FastAPI deployment docs — Python/uv support confirmation
- Flutter iOS CI/CD with Fastlane + GitHub Actions tutorial (Jan 2026, AWS Plain English) — current Fastlane pattern for Flutter
- sentry_flutter on pub.dev — version 8.x stable, 9.x beta status confirmed
- Google Play gambling policy (support.google.com) — analytics apps approved without gambling license
- Fly.io vs Railway comparison (2026) — DX tradeoff analysis
- Sports betting Discord server surveys (Whop blog, BVCompany, Discortize) — pricing tier benchmarks
- Discord Community Onboarding official docs — built-in onboarding feature
- ASO guides (Togwe, Udonis) — app title/subtitle keyword weight, screenshot caption conversion value
- SaaS landing page CRO research (Grafit Agency, Genesys Growth, MADX) — single-CTA and pricing visibility patterns
- Discord community failure analysis (Daniela53 Substack, Influencers Time) — empty room problem pattern
- Unbounce research (cited in FEATURES.md) — testimonial conversion lift benchmarks

### Tertiary (LOW confidence — must verify during implementation)
- Apple App Review turnaround for sports analytics apps in 2026 — verify when Phase 20 cycle begins
- Whop webhook retry behavior and idempotency guarantees — verify in Whop developer docs before Phase 18
- Google Play first-upload manual requirement as of 2026 — verify in Play Console before Phase 20

---
*Research completed: 2026-03-21*
*Supersedes: .planning/research/SUMMARY.md (v2.0, 2026-03-13)*
*Ready for roadmap: yes*
