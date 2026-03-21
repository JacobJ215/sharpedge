# Pitfalls Research

**Domain:** Sports analytics SaaS — App Store launch, Discord monetization, freemium conversion
**Project:** SharpEdge v3.0 Launch & Distribution
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH — App Store policy pitfalls drawn from verified approved app analysis (BettingPros, Action Network, Pikkit, Rithmm) plus official Apple guidelines; Expo pitfalls from EAS documentation and known GitHub issues; Whop/Discord pitfalls from official Whop docs plus community patterns; freemium pitfalls from a16z, Userpilot, and OpenView research.

---

## Critical Pitfalls

Mistakes that cause rejection, launch delay, or structural conversion failure.

---

### Pitfall 1: Apple App Store Rejection — Gambling-Adjacent App Metadata

**What goes wrong:**
Apple rejects sports betting analytics apps under Guideline 5.3 (Gambling) when the app name, description, or screenshots contain language that implies facilitation of wagering rather than analysis. The review team triggers on keywords in the app name/subtitle, the first sentence of the description, and screenshot overlays. Approved competitors (BettingPros, Action Network, Pikkit, Rithmm) all use a consistent formula: they exist on the App Store because they explicitly disclaim wagering and frame everything as informational.

**Why it happens:**
First-time founders write an honest description of what their platform does — "surface high-alpha betting edges," "identify betting edges," "arbitrage detection" — without realizing that App Review reads these phrases as facilitating gambling. Apple's human reviewers (not automated) are trained to flag anything that looks like a gambling tool. The app's actual behavior (no wagering, no money movement) is less visible to reviewers than its descriptive language.

**How to avoid:**
Use the proven approved-app formula. Frame everything as "sports analytics," "probability analysis," or "data-driven insights." Apply these rules to every metadata field:

- **App name/subtitle:** Avoid "betting," "wagers," "odds" in the name itself. Use "sports analytics," "edge detection," or "probability."
- **Description opening:** Must include a disclaimer in the first 3 sentences. Model after Rithmm: "[App] is for entertainment purposes only and does not involve real-money betting or prizes." Action Network: "Information is for news and entertainment purposes only."
- **Screenshots:** Do not show dollar amounts, "bet $X," or sportsbook account interfaces. Show probability charts, confidence intervals, team analytics.
- **Keywords field:** Do not use "gambling," "wager," "sportsbook," "bet slip" as keywords.
- **Age rating:** Set to 17+ (Frequent/Intense Simulated Gambling). Do not set lower — Apple reviewers will escalate if age rating looks inconsistent with content.
- **Privacy policy URL:** Must be present and live before submission. Apple hard-rejects without it.

**Warning signs:**
- Description uses "bet" as a verb ("helps you bet smarter") rather than a noun in an analytical context
- App name contains "Sharp," "Edge," or "Odds" without a qualifying "Analytics" or "Insights" suffix
- Screenshots show numeric probability outputs labeled "Win Probability: 73%" adjacent to visible sportsbook logos

**Phase to address:**
App Store listing phase (MOBILE-03). Write metadata before building the EAS production build. Submit to App Review with this language first, on the simplest possible build, before adding every feature.

---

### Pitfall 2: Apple App Store Rejection — In-App Purchase Bypass via External Payment

**What goes wrong:**
If the iOS app links to Whop's external subscription page, or displays a "Subscribe on Web" button, Apple will reject under Guideline 3.1.1 (Business: Payments). Apple requires that any digital goods or subscriptions sold to iOS users go through Apple IAP with Apple's 30% cut. Directing users to an external URL to subscribe is explicitly prohibited.

**Why it happens:**
The entire v3.0 monetization architecture routes through Whop (web-based checkout). This is correct for web and Discord users. But iOS users who discover the app and try to subscribe must not be shown an external payment link or told to "visit our website to subscribe."

**How to avoid:**
Three compliant patterns exist:

1. **Read-only app (safest):** The iOS app is a viewer-only companion — it displays data but cannot initiate a subscription. Users subscribe on web, and the app detects their Supabase tier on login. No payment UI in the app at all. This avoids IAP entirely. This is the pattern used by BettingPros and Action Network.

2. **IAP with Whop webhook sync:** Implement Apple IAP for iOS subscriptions. On successful IAP purchase, call the Whop API to activate the corresponding membership tier. Requires significant implementation effort and Apple's cut.

3. **Freemium only on iOS:** Free users see the app, paid features require web signup. The app never mentions pricing or subscription. Add a neutral CTA: "Access all features at sharpedge.io."

Recommendation: implement Pattern 1 for v3.0. iOS app is a free companion for existing subscribers only. No payment UI whatsoever. This ships faster and avoids IAP complexity entirely.

**Warning signs:**
- Any button in the iOS app labeled "Subscribe," "Upgrade," "Get Premium," or "Unlock"
- Any URL pointing to Whop or a payment page visible in the iOS app
- Pricing text anywhere in the iOS app

**Phase to address:**
Mobile app architecture decision (MOBILE-01). Decide before building the mobile app UI whether iOS is read-only or purchase-capable. Changing this after build is expensive.

---

### Pitfall 3: Apple App Store Rejection — Missing iOS Privacy Manifest

**What goes wrong:**
Since May 2024, Apple requires a `PrivacyInfo.xcprivacy` file in any iOS app that calls "required reason APIs" — this includes standard Expo SDK libraries that use UserDefaults, FileTimestamp, SystemBootTime, or DiskSpace APIs. Expo EAS Build does not automatically generate this file. Apps submitted without it receive a rejection email listing the specific APIs found. The rejection adds 1–2 weeks to the timeline.

**Why it happens:**
First-time founders follow the EAS Submit tutorial, which covers the basic submission flow but does not prominently feature the privacy manifest requirement. The rejection comes after the build has already been processed and uploaded, which takes hours. Discovering this after your first submission attempt wastes a full review cycle (typically 1–3 days per cycle).

**How to avoid:**
Configure the privacy manifest before the first production build:

1. Add `expo-privacy-manifest` to `app.json` plugins or create `ios/PrivacyInfo.xcprivacy` manually
2. After submitting to TestFlight (not full App Review), check email for Apple's pre-review notification about missing privacy manifest entries
3. Fix all entries before submitting to App Review proper

Expo's documentation at `docs.expo.dev/guides/apple-privacy/` lists the configuration options. Read it before the first build, not after the first rejection.

**Warning signs:**
- First EAS production build submitted directly to App Review without a TestFlight beta test period
- `app.json` has no `expo-privacy-manifest` plugin configured
- No `PrivacyInfo.xcprivacy` file in the iOS project

**Phase to address:**
EAS build configuration phase (MOBILE-01 through MOBILE-04). Add to the EAS setup checklist before first production build.

---

### Pitfall 4: Dead Discord Server at Launch — The Empty Room Problem

**What goes wrong:**
A Discord server with 0–10 members and empty channels creates a negative signal loop. The first real users to join see no activity, post nothing, and leave. The server reaches 50–100 members with total silence. The founder posts "gm" daily to no response. After 2–3 months, the server has members but no community. This is the most common outcome for founder-led Discord communities.

**Why it happens:**
The structural mistake is launching the server and the product simultaneously with no seeded content or engaged seed users. Discord engagement is social — it requires the appearance of activity to generate activity. The founder conflates "Discord server exists" with "Discord community exists."

**How to avoid:**
Do not make the Discord server publicly visible until it has a minimum viable activity level. The sequence that works:

1. **Pre-launch:** Recruit 10–20 seed members (beta testers, early signups, personal network) before the server is listed anywhere. Brief them: "I need you to be active this first week." Give them Moderator or Insider roles.
2. **Content before community:** Post 7 days of content in the server before the first public invite goes out. Each channel should have at least 5 messages. Create a daily cadence: one "pick of the day" post, one "line movement alert," one "question of the day." These can come from the bot.
3. **Onboarding flow:** New members must complete an onboarding step (#rules → react to get access). This filters for intent and prevents lurk-and-leave behavior.
4. **Bot as content engine:** Wire the Discord bot to post real SharpEdge output daily — top 3 edges, line movement alerts, market regime — into a #free-picks channel. This gives the server a reason to exist even when the founder is not posting.
5. **No gamification:** Do not add XP levels, points, or chat activity rewards. This produces fake engagement (people posting single emojis for points) that drives real conversations out.

**Warning signs:**
- Server launched on the same day as the web app, with no seed members
- All channels empty when first public link is posted
- Founder is the only one posting in the first week

**Phase to address:**
Discord setup phase (DISCORD-01 through DISCORD-05). Seed content and seed members before first public promotion. Bot should be posting daily picks before the server link goes live.

---

### Pitfall 5: Freemium Gate That Never Converts — The Free Tier Gives Too Much

**What goes wrong:**
Free users get enough SharpEdge value that they never feel the need to upgrade. They see daily picks, use the EV calculator, and track their performance — all for free. Conversion rate stays below 2% indefinitely. Revenue never reaches sustainability. The product serves its most engaged users for free while the founder subsidizes their infrastructure costs.

**Why it happens:**
First-time founders gate the wrong features. The instinct is to show off the product's best capabilities in the free tier to attract users, then hope they pay. This works for VC-backed companies that can afford months of zero conversion. For a first-time founder targeting revenue ASAP, a generous free tier is a slow death.

**How to avoid:**
Gate features at the "aha moment," not after it. The aha moment for SharpEdge is seeing the first high-confidence edge with Kelly sizing — the feeling of "I know exactly what to bet and how much." Structure the tiers so that:

- **Free tier shows enough to create desire, not enough to satisfy it:**
  - Daily top 1 edge (no detail — just sport, market, direction, and "edge detected")
  - EV calculator (limited to manual input, no pre-populated live odds)
  - No historical performance data
  - No Kelly sizing output
  - No line movement alerts

- **Mid tier (primary conversion target) unlocks the aha moment:**
  - Full edge details (exact line, book, confidence interval, Kelly size)
  - Live odds integration
  - Line movement alerts
  - Performance tracking

- **Premium tier** adds the quantitative engine depth (Monte Carlo, composite alpha, copilot).

The free tier should feel genuinely useful but obviously incomplete. The upgrade prompt should fire at the moment of maximum frustration: when a free user sees "Edge detected — upgrade to view details."

**Warning signs:**
- Free users are satisfied and active for more than 2 weeks with no upgrade prompt
- Free tier includes Kelly sizing output
- Free tier includes multiple full edge recommendations per day

**Phase to address:**
Auth and tier gate phase (AUTH-03, AUTH-04). Feature gating must be designed before the web app is built. Retrofitting gating after features are built is expensive and error-prone.

---

### Pitfall 6: Pricing That Is Too Low to Seem Credible

**What goes wrong:**
Sports betting analytics tools are priced based on their perceived alpha value, not their development cost. If a user makes $500+ on a well-sized edge play, a $9.99/month subscription feels irrelevant. But if the product is priced at $9.99, users assume the edges are low quality. The "institutional-grade probabilistic intelligence" positioning and a $9.99 price tag are contradictory signals.

**Why it happens:**
First-time founders price for accessibility ("I want everyone to afford this") rather than for perceived value. Underpricing destroys conversion because it signals low confidence in the product's value.

**How to avoid:**
Price at the level where users who see real value do not hesitate, and users who are uncommitted self-select out. For sports analytics targeting serious bettors:

- Mid tier: $39–$49/month (not $9.99–$19.99)
- Premium tier: $99–$149/month

A user who makes one correct call on a +$250 EV bet has already recovered the monthly cost of the mid tier. Positioning must make this math explicit on the landing page.

**Warning signs:**
- Landing page pricing below $29/month for the first paid tier
- Pricing based on "what feels affordable" rather than "what ROI does one successful edge provide"

**Phase to address:**
Marketing landing page phase (GROWTH-01). Pricing is a landing page decision, not a product decision. Set it before the page goes live, not after.

---

### Pitfall 7: Whop Discord Role Sync Fails Silently After Payment

**What goes wrong:**
A user pays via Whop. Their Whop membership is activated. Their Discord role is never assigned. They join the Discord server as a paid member and see only the free channels. They open a support ticket or, worse, request a refund. This is the highest-impact failure mode for a Discord-first monetization flow.

**Why it happens:**
The Whop-to-Discord role sync has three distinct failure modes, all silent by default:

1. **Bot role hierarchy:** The Whop Bot's role in the Discord server hierarchy must be positioned above every role it assigns. If it is not at the top, the bot silently fails to assign roles without any error in the Discord UI. Whop's documentation calls this out, but founders skip it during initial setup.

2. **Member not in server at time of purchase:** Whop fires the role-assignment webhook at the moment of purchase. If the user has not yet joined the Discord server, the webhook cannot assign a role to a non-member. The role is never assigned. Whop does not retry. The user must manually trigger re-sync or the founder must manually assign the role.

3. **Webhook delivery failure / no retry:** Whop's webhook system will retry on HTTP errors, but if the webhook server is down or the endpoint returns a success code despite failing internally, the event is lost. No role is assigned. No error is surfaced to the Whop dashboard by default.

**How to avoid:**
- **Before launch:** Move the Whop Bot role to the very top of the server role list. Test this before any paid users exist.
- **Onboarding flow:** After purchase, Whop's confirmation page should direct users to join the Discord server. Make this the first CTA after payment: "Step 1: Join our Discord server. Step 2: Your role will be assigned automatically." This forces the user to join before the webhook fires.
- **Event log channel:** Enable Whop's bot event log in a private admin channel. Every role assignment (and failure) is logged there. This is the only visibility into role sync status.
- **Manual re-sync command:** Build a `/resync` bot command that lets admins trigger a Whop membership check for a specific Discord user. This is the recovery path when role sync fails.
- **Webhook endpoint monitoring:** Add Sentry error tracking to the webhook handler. Any exception in role assignment should trigger an alert, not a silent 200 OK.

**Warning signs:**
- No event log channel configured in the Discord server
- Whop Bot role is not at the top of the server's role hierarchy
- No test of the purchase → role assignment flow with a real test subscription before launch

**Phase to address:**
Discord community setup (DISCORD-02) and webhook server deployment (DEPLOY-02). Test the full purchase → role assignment flow end-to-end in a staging environment before go-live.

---

### Pitfall 8: Expo EAS — First iOS Submission Fails Due to Missing Metadata in App Store Connect

**What goes wrong:**
EAS Build produces a valid `.ipa`. EAS Submit uploads it to App Store Connect successfully. But the submission cannot be sent for App Review because App Store Connect is missing required fields: privacy policy URL, age rating questionnaire, app category, content rights declaration, and export compliance. The build just sits in "Processing" or "Ready to Submit" with a list of validation errors. First-time founders spend hours discovering these are not EAS issues but App Store Connect configuration issues.

**Why it happens:**
EAS Build handles code signing and binary creation. EAS Submit handles uploading the binary. Neither tool configures App Store Connect metadata. The App Store Connect setup (create the app listing, fill all metadata fields, answer the questionnaire, set pricing) is a manual step that must happen before or alongside the first submission, not after.

**How to avoid:**
Complete all App Store Connect configuration before running `eas submit`:

1. Create the App Store listing in App Store Connect (different from the EAS project)
2. Set the bundle ID — must match exactly what is in `app.json`'s `ios.bundleIdentifier`
3. Answer the export compliance questionnaire (does the app use encryption? — yes, HTTPS; answer accordingly)
4. Set the age rating to 17+ via the content rating questionnaire
5. Add the privacy policy URL (must be a live URL, not localhost)
6. Set the primary category (Sports or Utilities — do not use "Games")
7. Add pricing (Free)
8. Add at minimum 1 screenshot per required device size (6.5" iPhone is required)

Then run `eas submit`. The first time through will still require TestFlight before App Review.

Additional EAS-specific gotcha: Google Play requires the first upload to be manual (via the Play Console web UI), not via EAS Submit API. Run the first Android upload via the Play Console, then EAS Submit works for subsequent builds.

**Warning signs:**
- First EAS submission attempted without visiting App Store Connect beforehand
- Bundle ID in `app.json` does not exactly match the bundle ID registered in App Store Connect
- Privacy policy URL is a placeholder or returns 404

**Phase to address:**
Mobile store setup (MOBILE-03) — this is a prerequisite before MOBILE-04 (app approval). Allocate a full day to App Store Connect configuration before any build submission.

---

### Pitfall 9: Expo EAS — iOS Build Credential Mismatch Blocks Production Build

**What goes wrong:**
EAS Build manages iOS code signing automatically (certificates and provisioning profiles). On the first production build (`--profile production`), EAS may fail with a provisioning profile mismatch if: (a) a distribution certificate was previously created manually in the Apple Developer portal, (b) the bundle ID was registered with capabilities that were later changed, or (c) the team has multiple Apple Developer accounts and EAS picks the wrong one.

**Why it happens:**
Apple's code signing system is stateful — certificates, profiles, and entitlements must match exactly. EAS abstracts most of this, but the abstraction breaks when there is existing state in the Apple Developer portal that conflicts with what EAS expects to create. The error messages from Apple are cryptic (e.g., ITMS-90748 with no further explanation).

**How to avoid:**
- Use EAS-managed credentials from day one. Do not create certificates manually in the Apple Developer portal if you intend to use EAS Build.
- Run `eas credentials` to inspect what EAS has registered before the first production build.
- If a mismatch exists, use `eas credentials --platform ios` to revoke and regenerate. This invalidates the old profile but creates a clean state.
- Ensure `eas.json` has the correct `production` profile with `"credentialsSource": "remote"`.
- If using push notifications (`expo-notifications`), the production provisioning profile must include the APNs entitlement. Verify via `eas credentials` before submitting.

**Warning signs:**
- Apple Developer portal has manually created distribution certificates from a previous project
- The error `No provisioning profiles matching` or `Invalid code signing` appears in EAS build logs
- First build attempt is directly to production, bypassing a `preview` or `staging` build profile test

**Phase to address:**
EAS configuration (MOBILE-01). Set up and validate EAS credentials before building the first production binary.

---

## Technical Debt Patterns

Shortcuts that seem reasonable for v3.0 launch but create compounding problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| iOS app is read-only / no IAP | Avoids Apple IAP complexity, ships faster | Limits iOS monetization; iOS users must convert on web | Acceptable for v3.0; revisit at v3.1 |
| Whop webhook server is a simple FastAPI app with no queue | Simpler deployment | Webhook events lost if server restarts during delivery | Never acceptable for production; add Redis queue or use Whop's retry logic |
| Free tier defined by hiding UI elements on frontend | Fast to implement | Features still callable via API; security theater | Never acceptable; gate at API layer (Supabase RLS + tier check) |
| Skip TestFlight beta period, submit directly to App Review | Saves 1–2 weeks | First App Review rejection adds 1–3 days per cycle; no beta feedback before public launch | Never for first submission |
| One Discord server for both free and paid users | No complexity in server management | Paid users share space with free users who see gated content; creates resentment | Acceptable only with strict channel permissions from day one |
| Launch all platforms simultaneously | Coordinated launch story | Each platform has its own failure modes; simultaneous launch means all fail together | Stagger: Discord + web first, mobile 2–4 weeks later |

---

## Integration Gotchas

Common mistakes when connecting to external services in the v3.0 stack.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Whop → Discord role sync | Not testing the full purchase-to-role flow before launch | Buy a test subscription with a test account; verify role appears in Discord within 60 seconds |
| Whop webhooks | Webhook endpoint returns 200 even when internal processing fails | Return 200 only after role assignment is confirmed; use idempotency keys on webhook events |
| Expo → Apple APNs | Testing push notifications in Expo Go (works) then assuming they work in production (they don't without entitlements) | Always test push notifications via EAS Build `preview` profile on a physical device |
| Supabase → mobile app | Using service role key in the mobile app (exposes admin access to all users) | Use Supabase `anon` key in mobile; enforce RLS; never ship service role key in a client app |
| EAS Submit → App Store Connect | Bundle ID in `app.json` does not match App Store Connect | Register the bundle ID in App Store Connect first; copy it exactly to `app.json` |
| Whop → Supabase tier sync | Whop membership tier not synced to Supabase `users.tier` column | Webhook handler must write tier to Supabase on every membership activation/deactivation event |

---

## Performance Traps

Patterns that work at launch scale but fail as the community grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Discord bot posting picks synchronously in response to user commands | Bot appears slow; commands time out at 3-second Discord limit | All long-running operations must use deferred responses (`interaction.response.defer()`) | Immediately if ML model inference takes > 2 seconds |
| Webhook handler processes Whop events synchronously | Role assignment blocks the HTTP response; timeouts cause Whop to retry; duplicate role assignments | Queue webhook events in Redis; process asynchronously; use idempotency keys | At first Whop retry (within 30 seconds of a slow response) |
| Mobile app fetches all user data on every screen load | App feels slow on mobile networks; API costs scale with screen views | Cache tier status and edge data locally; refresh on app foreground only | At ~100 active mobile users |
| Supabase free tier connection pooling | API timeouts during Discord bot command spikes | Use Supabase connection pooling (PgBouncer) from day one | At ~20 concurrent Discord users |

---

## Security Mistakes

Domain-specific security issues for a sports analytics SaaS with Discord and mobile components.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Supabase service role key in Expo mobile app | Any user can extract the key from the app binary and access all user data | Use `anon` key in mobile; enforce RLS on all tables |
| Whop webhook endpoint not validating HMAC signature | Attacker can forge webhook events, granting unauthorized roles | Validate Whop HMAC signature on every incoming webhook before processing |
| No rate limiting on `/api/v1/analyze` endpoint | Free users abuse the API to get paid-tier data by calling raw endpoints | Enforce tier check at API middleware layer, not just in the UI |
| Discord bot token in environment variable without rotation plan | Leaked token gives attacker full bot control | Store in secret manager; have a rotation runbook ready |
| Supabase RLS disabled on user-scoped tables | Any authenticated user can read any other user's picks history and performance data | Enable RLS before any user-scoped data goes into production tables |

---

## UX Pitfalls

Common user experience mistakes in Discord + mobile + SaaS simultaneous launches.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Upgrade prompt appears on first session before user understands the product | User closes the app; never returns | Show upgrade prompt only after user has seen at least one "edge detected" result |
| Different feature sets on web vs mobile with no explanation | Users confused about what they're paying for; churn | Document which features are on which platform; mobile companion framing sets correct expectations |
| Discord onboarding requires 5+ steps before user gets value | 60–80% drop-off before seeing any content | Gate on 1 step maximum (rules reaction); show free picks in the first channel they can access |
| Bot commands return walls of text with no formatting | Discord users ignore or mute the bot | Use Discord embeds with structured fields; color-code by confidence tier (green/yellow/red) |
| No clear path from Discord free member to web signup | Discord community grows but web signups stagnate | Every bot response that shows a gated feature includes a single CTA: "View full analysis at sharpedge.io" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete during development but are missing critical pieces for App Store approval and production launch.

- [ ] **iOS app submission:** Privacy policy URL is live (not localhost, not a Google Doc) — verify it resolves from a device on cellular, not just your dev machine
- [ ] **iOS age rating:** Set to 17+ via App Store Connect questionnaire, not estimated — the questionnaire answer must match the content
- [ ] **Discord role sync:** Whop Bot role is at the top of the server role hierarchy — verify in Server Settings → Roles, not just assumed
- [ ] **Whop webhook handler:** HMAC signature validation is implemented — check the handler code, not just that webhooks are received
- [ ] **Feature gates:** API endpoints enforce tier restrictions server-side — verify by calling the API directly with a free-tier JWT, not by testing the UI
- [ ] **Mobile app:** Push notifications tested on a physical device via EAS Build preview profile, not Expo Go — APNs entitlement must be in the production provisioning profile
- [ ] **EAS production build:** Bundle ID in `app.json` matches App Store Connect exactly — a one-character difference causes silent submission failure
- [ ] **App Store Connect:** All required metadata fields completed before first EAS submit — missing fields cause "cannot submit for review" errors post-upload
- [ ] **Supabase RLS:** Enabled on bets, users, and picks tables — test by querying user B's data while authenticated as user A
- [ ] **Whop → Supabase tier sync:** Deactivation webhook updates Supabase `users.tier` to free — test by cancelling a test subscription and verifying gated features disappear

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover efficiently.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| App Store rejection (metadata/gambling language) | LOW — 3–5 days | Update description/screenshots with compliant language; resubmit; average re-review is 1–3 days |
| App Store rejection (IAP bypass) | HIGH — 1–3 weeks | Remove all payment UI from iOS app; implement read-only companion pattern; resubmit |
| App Store rejection (privacy manifest) | LOW — 1–2 days | Add `PrivacyInfo.xcprivacy` entries per Apple's rejection email; rebuild via EAS; resubmit |
| Discord roles not assigned after payment | LOW — 1 hour | Manually assign roles via Discord; fix bot hierarchy; trigger Whop re-sync; add event log channel |
| Freemium never converts (>3 months with <2% conversion) | HIGH — ongoing | Tighten free tier gate (remove one key feature); add in-app upgrade prompt at the right moment; reassess pricing |
| EAS credential mismatch | MEDIUM — 4–8 hours | Run `eas credentials --platform ios`; revoke conflicting profile; regenerate; rebuild |
| Webhook events lost (role assignments missed) | MEDIUM — 2–4 hours | Add replay logic: query Whop memberships API on bot startup; reconcile against Discord roles; assign missing roles |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls before they occur.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| App Store rejection — gambling language | MOBILE-03 (App listing setup) | Use approved-app formula; have a non-founder read the description and classify it as "gambling tool" or "sports analytics tool" |
| App Store rejection — IAP bypass | MOBILE-01 (Mobile app architecture) | Confirm zero payment UI in iOS app; no Whop links visible to unauthenticated users |
| App Store rejection — privacy manifest | MOBILE-01 (EAS setup) | Run EAS build to TestFlight; wait for Apple's pre-review email; fix all listed APIs before App Review submission |
| Dead Discord server | DISCORD-01 to DISCORD-05 (Community setup) | Server has 14 days of daily bot-posted content and 10+ seed members before first public link |
| Freemium never converts | AUTH-03 to AUTH-04 (Tier gating) | Free-tier user cannot access Kelly sizing or full edge details via UI or direct API call |
| Pricing too low | GROWTH-01 (Landing page) | Mid tier at $39+/month; landing page includes ROI calculation showing one successful play covers subscription |
| Whop → Discord role sync failure | DISCORD-02 + DEPLOY-02 | Test purchase → role assignment with a real test subscription; event log channel shows assignment confirmed within 60 seconds |
| EAS submission — missing App Store Connect metadata | MOBILE-03 (before MOBILE-04) | All App Store Connect fields completed; first submission goes to TestFlight, not directly to App Review |
| EAS iOS credential mismatch | MOBILE-01 (EAS configuration) | `eas credentials --platform ios` shows clean state; `preview` profile build succeeds before `production` build attempted |
| Push notification entitlements missing | MOBILE-01 to MOBILE-02 | Push notifications tested on physical device via EAS `preview` build; not validated in Expo Go |

---

## Sources

- Apple App Store approved sports betting analytics apps analyzed: BettingPros (id1468109182), Rithmm (id1641010681), Pikkit (id1586567110), Action Network (id1083677479), Outlier (id6443885102) — MEDIUM confidence (observed app store listings; actual review correspondence not public)
- Apple App Review Guideline 5.3 (Gambling) — accessed via developer.apple.com (content truncated in fetch; supplemented by shopapper.com analysis) — MEDIUM confidence
- Apple IAP Guideline 3.1.1 — HIGH confidence (explicit, well-documented, actively enforced)
- Expo EAS documentation: docs.expo.dev/distribution/app-stores/, docs.expo.dev/guides/apple-privacy/ — HIGH confidence (official docs)
- Expo EAS GitHub issues: ITMS-90748 (issue #1659), provisioning mismatch (issue #1073), privacy manifest tracking (issue #27796) — HIGH confidence (official repo)
- Whop Discord integration docs: whop.com/blog/link-whop-to-discord/, whop.com/blog/webhooks-app-whop/ — HIGH confidence (official Whop docs)
- Freemium conversion research: a16z.com/how-to-optimize-your-free-tier-freemium/, userpilot.com/blog/freemium-conversion-rate/, openviewpartners.com/blog/freemium-pricing-guide/ — HIGH confidence (authoritative SaaS research)
- Discord community failure patterns: daniela53.substack.com/p/why-your-discord-server-is-dead-and, influencers-time.com/launch-a-branded-discord-community-strategy-and-success-guide/ — MEDIUM confidence (practitioner observation, not controlled research)
- Feature gating: demogo.com/2025/06/25/feature-gating-strategies-for-your-saas-freemium-model-to-boost-conversions/ — MEDIUM confidence

**Gaps requiring phase-specific validation:**
- Apple App Review response time for sports analytics apps in the current review queue (2026) — verify during MOBILE-04 phase
- Whop's current webhook retry behavior and idempotency guarantees — verify in Whop developer docs before DEPLOY-02
- Exact Google Play first-upload manual requirement — verify in Play Console before MOBILE-05

---
*Pitfalls research for: SharpEdge v3.0 Launch & Distribution*
*Researched: 2026-03-21*
