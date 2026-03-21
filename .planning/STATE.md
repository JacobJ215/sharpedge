---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Live Execution
status: unknown
stopped_at: Completed 16-auth-bridge plan 03 (16-03-PLAN.md)
last_updated: "2026-03-21T18:10:54.741Z"
progress:
  total_phases: 15
  completed_phases: 14
  total_plans: 64
  completed_plans: 64
---

# Project State: SharpEdge v3.0

**Last updated:** 2026-03-21
**Updated by:** roadmapper agent

---

## Project Reference

**Core value:** Surface high-alpha betting edges — ranked by composite probability score (EV × regime × survival × confidence) — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

**Current focus:** Phase 16 — auth-bridge

---

## Current Position

Phase: 16 (auth-bridge) — EXECUTING
Plan: 3 of 3

## Phase Status (v3.0)

| Phase | Goal | Status |
|-------|------|--------|
| 16 — Auth Bridge | `supabase_auth_id` migration + Custom Access Token Hook + tier propagation from Whop | Complete (Plan 3/3) |
| 17 — Web Deployment | Vercel Pro + Railway + CI/CD pipeline + JWT-based feature gating | Not started |
| 18 — Discord Community | Channel structure + Whop role sync + bot commands + content seeding | Not started |
| 19 — Marketing & Onboarding | Landing page + pricing + new user onboarding + social media | Not started |
| 20 — Mobile Submission | iOS + Android App Store submission + Fastlane CI/CD + TestFlight | Not started |
| 21 — Monitoring | Sentry (web + mobile + Python) + UptimeRobot + user event tracking | Not started |

---

## Accumulated Context

### Key Decisions (v2.0 carry-forward affecting v3.0)

- Phase 9 complete — PMResolutionPredictor, PMFeatureAssembler, download/process/train scripts all exist as stubs; Phase 10 runs them against live APIs
- SettlementLedger exists from Phase 6 (SETTLE-01) — Phase 12 extends it with fill/cancel tracking
- ExposureBook from Phase 6 (RISK-01) — Phase 11 uses it for per-market/per-day limit enforcement
- Polymarket live execution deferred to v2.1 — execution engine targets Kalshi CLOB only in v2.0

### Phase 16 Plan 01 Decisions (auth-bridge execution)

- discord_id DROP NOT NULL placed before trigger creation so email-only signups do not fail on INSERT (discord_id has no default)
- is_operator column added as BOOLEAN DEFAULT FALSE NOT NULL; set manually for platform owner; injected into JWT app_metadata to gate execution/swarm routes without user exposure
- RevenueCat app_user_id is set to Supabase Auth UUID at purchase time (Flutter calls Purchases.logIn after sign-in) enabling direct supabase_auth_id tier push
- BILLING_ISSUE events log warning only — tier is not downgraded during billing resolution window
- Custom Access Token Hook must be registered in Supabase Dashboard after migration 008 is applied (not automated)

### Phase 16 Plan 03 Decisions (tier UI execution)

- UpgradePromptWidget defaults requiredTier to 'pro'; callers pass 'sharp' for sharp-only gated screens
- Web account page uses client-side getSession() for tier display — no SSR overhead needed for non-security display data
- iOS upgrade path links to external browser only (no in-app payment UI) for Apple Guideline 3.1.1 compliance
- url_launcher ^6.2.0 added to pubspec.yaml — was not previously a dependency (auto-fixed, deviation Rule 3)

### v3.0 Architecture Decisions (from research)

- Migration 008 (`supabase_auth_id` column) is the hard blocker for all auth work — Phase 16 must land before Phases 17–21 can use tier-based access
- iOS app must use read-only companion pattern: zero payment UI, zero Whop links, no upgrade buttons — users subscribe on web and tier flows through JWT (Apple Guideline 3.1.1 compliance)
- Do NOT store subscription tier in `user_metadata` (user-editable) — use `app_metadata` only, writable via service key, admin API, or SECURITY DEFINER Postgres function
- Whop Bot role must be placed at the top of Discord role hierarchy before any paid users exist — silent failure mode if bot role is below the role it is trying to assign
- Discord server must have 7 days of pre-seeded bot-generated content before public launch — empty server creates negative signal loop
- Vercel Hobby plan prohibits commercial use — Pro plan required from day one
- Railway (not Render) for Discord bot — Render free tier kills persistent WebSocket after 15 minutes
- Fastlane + GitHub Actions for Flutter CI/CD — EAS Build is Expo-only, does not apply to Flutter
- `sentry_flutter ^8.x` stable — 9.x is beta; do not pin beta in production
- `@supabase/ssr` required for Next.js middleware server-side session reading — basic `createClient` does not support server-side session in middleware
- Phase 20 staggered 2–4 weeks after Phases 17–19 go live — decouples launch date from Apple review timeline

### Open Decisions (require founder input before planning)

- Pricing finalization: Mid tier $39–$49/month vs $19–$29 (research recommends $39–$49 for perceived value with serious bettors); must be set before Phase 19 landing page planning
- iOS app free-tier feature set: exact features visible to free-tier iOS users vs paid-tier iOS users must be specified before Phase 20 scope definition

### Verification Tasks (before implementation, not full research)

- Phase 18: Confirm Whop webhook retry behavior and idempotency guarantees in Whop developer docs before finalizing webhook handler design
- Phase 20: Verify installed Flutter SDK version is >=3.24.0 before adding `sentry_flutter` to `pubspec.yaml`
- Phase 20: Verify Google Play first-upload manual requirement is still current in 2026 before writing CI/CD pipeline

### Research Flags

- Phase 20 requires `/gsd:research-phase` before planning: Apple App Review current turnaround for sports analytics apps in 2026, Google Play first-upload manual requirement, any Fastlane/Flutter CI changes since Jan 2026

### Todos

- [ ] Set pricing tiers (Mid and Premium) before Phase 19 plan is written
- [ ] Define iOS free-tier vs paid-tier feature set before Phase 20 plan is written
- [ ] Verify Whop webhook idempotency behavior before Phase 18 implementation begins
- [ ] Verify Flutter SDK >= 3.24.0 in CI environment before Phase 20 begins
- [ ] Run `/gsd:research-phase 20` before writing the Phase 20 plan

### Blockers

None.

---

## Session Continuity

**Last session:** 2026-03-21T18:10:54.738Z
**Stopped at:** Completed 16-auth-bridge plan 03 (16-03-PLAN.md)
**Resume file:** None

---
*State initialized: 2026-03-13 by roadmapper*
*Updated: 2026-03-15 — v2.0 milestone roadmap created; position reset to Phase 10*
*Updated: 2026-03-21 — v3.0 milestone roadmap created; position reset to Phase 16; total phases updated to 21*
