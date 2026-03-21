# Technology Stack

**Project:** SharpEdge v3.0 — Launch & Distribution
**Domain:** Multi-platform sports analytics SaaS (web + mobile + Discord)
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH (web-verified for deployment stack; App Store compliance verified against live examples)

> This file extends and corrects the prior v2.0 STACK.md. The prior document assumed the mobile app was Expo/React Native. The actual codebase (`apps/mobile/pubspec.yaml`) uses Flutter/Dart. All mobile CI/CD recommendations below are Flutter-specific and supersede the Expo-based guidance in the previous file.

---

## Recommended Stack

### Web Deployment

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Vercel | Pro ($20/mo) | Next.js 14 hosting | Native Next.js support with zero-config deployment; automatic preview deployments on PRs; Edge Network for sub-100ms loads. **Must use Pro, not Hobby** — Hobby plan prohibits commercial use and has stricter rate limits on serverless functions. The webhook server (FastAPI) cannot run on Vercel; it goes on Railway. |
| GitHub Actions | - | CI/CD trigger for Vercel | Push to `main` triggers Vercel production deploy automatically via Vercel's GitHub integration. No custom workflow needed for web-only deploys. Add a test job (`npm test`) as a gate before merge. |

**Vercel Hobby vs Pro:** Hobby is non-commercial and limits serverless functions to 10s execution and 1M invocations/month. Pro adds $20 usage credit, 4GB RAM functions, 1TB bandwidth, and commercial use. For a paying SaaS, Pro is required on day one. MEDIUM confidence (based on Vercel pricing page, March 2026).

---

### Python Backend Deployment (FastAPI + Discord Bot)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Railway | - | Hosting for FastAPI webhook server + Discord bot | Two separate Railway services from the same repo. Railway detects `pyproject.toml` with uv and sets up correctly. Persistent process model is correct for the Discord bot (which must maintain a websocket connection to Discord — it cannot run serverless). $5/mo hobby plan; production services ~$20-40/mo at low traffic. Best DX of all Python hosting options. |
| Docker (Dockerfile per app) | - | Container packaging for Railway | Railway accepts Dockerfiles; add one per app (`apps/bot/Dockerfile`, `apps/webhook_server/Dockerfile`). Use `python:3.12-slim` base. uv is the package manager — install with `pip install uv` then `uv sync`. |
| GitHub Actions | - | CI for Python services | Add a workflow that runs `uv run pytest` + linting on PRs. Railway handles production deploy on merge to main via its GitHub integration (configure in Railway dashboard). No manual `flyctl` or deploy commands needed. |

**Why Railway over Fly.io:** Fly.io is cheaper (free tier: 3 shared VMs) and technically superior for multi-region, but it requires CLI knowledge (`flyctl deploy`, `fly.toml`, machine management). Railway's GitHub auto-deploy and web UI allow faster initial setup for a team focused on product. Fly.io is the correct choice when cost optimization becomes a priority post-launch. MEDIUM confidence (both platforms work; choice is DX tradeoff).

**Why not Render:** Render's free tier spins down after inactivity — fatal for a Discord bot that must stay connected. Railway's always-on model is correct. MEDIUM confidence.

---

### Mobile CI/CD — Flutter (iOS + Android)

> CRITICAL CORRECTION from prior STACK.md: The mobile app at `apps/mobile/` is Flutter (Dart), not Expo/React Native. EAS Build is an Expo product and does not apply. Use Fastlane + GitHub Actions for Flutter.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Fastlane | latest (Ruby gem) | iOS App Store + Android Play Store automation | Industry standard for mobile app deployment automation. Two lanes: `ios` (builds IPA, uploads to TestFlight via App Store Connect API) and `android` (builds AAB, uploads to Play Store internal track). Fastlane `match` handles iOS code signing certificates stored in a private Git repo. |
| Fastlane match | - | iOS code signing certificate management | Stores distribution certificates and provisioning profiles in an encrypted private GitHub repo. GitHub Actions pulls certificates during build without needing a local Mac. Required for automated iOS builds in CI. |
| GitHub Actions (macOS runner) | - | iOS build runner | iOS builds require macOS. Use `runs-on: macos-latest` for the iOS job. Android builds can run on `ubuntu-latest`. Parallelize both jobs in the same workflow for simultaneous submission. |
| App Store Connect API Key | - | Fastlane authentication to Apple | Generate a JSON key in App Store Connect > Users & Access > Keys. Store as GitHub Secret `APP_STORE_CONNECT_API_KEY_CONTENT`. Avoids Apple ID 2FA issues in CI. |
| Google Play Service Account | - | Fastlane authentication to Google Play | Create a service account in Google Cloud Console, grant it Google Play Developer API access, download the JSON key. Store as GitHub Secret `GOOGLE_PLAY_JSON_KEY`. |

**Fastlane workflow structure:**
```
apps/mobile/
  fastlane/
    Appfile          # Bundle ID, Apple ID, package name
    Fastfile         # lanes: ios_beta, ios_release, android_internal, android_release
    Matchfile        # match type: appstore, git_url: [private cert repo]
  android/
  ios/
  pubspec.yaml
```

**GitHub Actions workflow outline (parallel iOS + Android):**
```yaml
jobs:
  build-ios:
    runs-on: macos-latest
    steps:
      - flutter build ipa --release
      - fastlane ios_release  # uploads to TestFlight

  build-android:
    runs-on: ubuntu-latest
    steps:
      - flutter build appbundle --release
      - fastlane android_internal  # uploads to Play Store
```

MEDIUM confidence — multiple Jan 2026 tutorials confirm this pattern. macOS GitHub Actions runner cost is ~$0.08/min vs $0.008/min for Ubuntu; budget ~15-20 min per iOS build = ~$1.20 per release build. Acceptable for a small-volume release pipeline.

---

### Error Tracking — Sentry

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| @sentry/nextjs | ^8.x | Next.js web error + performance tracking | Wraps `next.config.mjs` with `withSentryConfig`. Covers client-side (browser), server-side (SSR/RSC), and edge runtime errors in one package. Run `npx @sentry/wizard@latest -i nextjs` to scaffold `instrumentation.ts`, `sentry.client.config.ts`, and `sentry.server.config.ts`. Requires Next.js 14+. |
| sentry_flutter | ^8.x (stable) | Flutter mobile error + performance tracking | Pub.dev package. Wraps `runApp` with `SentryFlutter.init()`. Captures crashes, Dart errors, ANRs (Android), and performance traces. Latest stable is ~8.x as of March 2026 (9.x in beta). Use ^8.x for stability. Compatible with Flutter >=3.24.0 and Dart >=3.5.0 which the project's pubspec.yaml meets (>=3.0.0 — verify exact Flutter version). |
| sentry-sdk (Python) | ^2.x | FastAPI + Discord bot error tracking | Add to both Python apps. FastAPI integration: `SentryAsgiMiddleware`. Discord bot: `sentry_sdk.init()` at startup. Captures unhandled exceptions in commands and background tasks. |

**Sentry installation:**
```bash
# Web
cd apps/web && npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs

# Python services
uv add sentry-sdk --group prod  # in apps/bot and apps/webhook_server
```

```yaml
# apps/mobile/pubspec.yaml addition
dependencies:
  sentry_flutter: ^8.0.0
```

ONE Sentry organization, THREE projects (web, mobile, bot). Use environment tags (`production`, `staging`) to separate signal from noise. MEDIUM confidence (version numbers from pub.dev and npm as of research date; the 9.x-beta version should be monitored).

---

### Uptime Monitoring

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| UptimeRobot | Free tier | Bot + webhook server downtime alerts | Free plan monitors up to 50 endpoints at 5-min intervals. Configure a Discord webhook alert to a private #ops channel. Catches bot outages faster than users reporting them. Free tier covers all three endpoints (web, API, health check). |

Add a `/health` endpoint to the FastAPI webhook server that returns 200. UptimeRobot monitors this URL. If the Discord bot dies, it cannot respond to its own health endpoint — route the bot's health check through the FastAPI service instead (the bot can ping a Redis key; FastAPI reads it).

---

### Supporting Libraries (New Additions for v3.0)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastlane-plugin-versioning | latest | Auto-increment build numbers from git tags | Avoids manual version bumps in pubspec.yaml before each release; reads from git tag |
| flutter_native_splash | ^2.4.0 | Native launch screen | Eliminates the white flash on app startup; configure in pubspec.yaml, run generator |
| package_info_plus | ^8.0.0 | Read app version at runtime | Display version number in app settings/about screen for support |
| url_launcher | ^6.3.0 | Open Whop subscription URL from mobile | Required for the "upgrade" CTA that opens the web subscription page |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Fastlane (local) | Test deployment lanes before CI | Install via `gem install fastlane`; run `fastlane ios_beta` locally to validate before pushing to CI |
| Flutter CLI | Build + test mobile | Already in project; ensure Flutter >=3.24.0 to meet sentry_flutter requirements |
| Vercel CLI | Preview deploy + env var management | `npx vercel env pull .env.local` syncs production env vars to local development |
| GitHub Environments | Separate staging vs production secrets | Create `staging` and `production` environments in GitHub repo settings; scope API keys per environment |

---

## Installation

```bash
# Web — Sentry
cd apps/web
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs

# Web — no other new npm dependencies required

# Python services — Sentry
cd apps/bot && uv add "sentry-sdk[fastapi]"
cd apps/webhook_server && uv add "sentry-sdk[fastapi]"

# Mobile — add to pubspec.yaml
# sentry_flutter: ^8.0.0
# flutter_native_splash: ^2.4.0
# package_info_plus: ^8.0.0
# url_launcher: ^6.3.0
# Then: flutter pub get

# Fastlane — run from apps/mobile/
gem install fastlane
fastlane init  # generates Appfile + Fastfile scaffolding
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Railway (Python hosting) | Fly.io | When cost matters more than DX; Fly.io free tier is better, CLI is more complex but documented well |
| Railway (Python hosting) | Render | Never for Discord bot — Render free tier sleeps, killing the persistent gateway connection |
| Railway (Python hosting) | AWS ECS/Fargate | When team has AWS expertise and needs fine-grained control; overkill for launch |
| Fastlane + GitHub Actions | Codemagic | Codemagic is Flutter-first CI/CD ($0 for 500 build minutes/month). Better default Flutter support, worse Git workflow integration. Valid alternative if GitHub Actions macOS costs become a concern. |
| Fastlane + GitHub Actions | Bitrise | Full-featured mobile CI/CD with macOS/Linux environments. More expensive ($90+/mo for teams), better built-in test reporting. Use if the team scales and needs dedicated mobile CI. |
| Vercel (Next.js) | Netlify | Netlify supports Next.js but with less feature parity than Vercel on App Router, RSC, and Edge functions. Acceptable but Vercel has zero-friction advantage. |
| Vercel (Next.js) | Cloudflare Pages | Cloudflare Pages has excellent edge performance and lower costs at scale. Switch is warranted post-launch if Vercel costs spike. |
| @sentry/nextjs | Datadog | Datadog is $15+/host/month for APM. Sentry's free tier (5K errors/month) is sufficient for launch; upgrade only if alert volume justifies cost. |
| UptimeRobot | BetterStack | BetterStack has better incident management, on-call schedules, and status pages. Use it when the product has SLA obligations. UptimeRobot is sufficient for v3.0. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| EAS Build (Expo) | EAS Build is the Expo Application Services build system and is only compatible with Expo/React Native projects. The SharpEdge mobile app is Flutter/Dart. | Fastlane + GitHub Actions |
| Vercel Hobby plan | Explicitly prohibits commercial use per Vercel's Fair Use Guidelines. Deploying a paid SaaS on Hobby violates ToS and can result in account suspension. | Vercel Pro ($20/mo) |
| Render free tier for Discord bot | Free tier suspends after 15 minutes of inactivity. Discord bot requires a persistent websocket — it will be killed constantly. | Railway or Fly.io (always-on) |
| Apple IAP for subscription in mobile app | Apple requires 30% commission on in-app purchases. Whop subscriptions are web-based external purchases — this is allowed as long as the app does not link to or prompt the external payment from within the app (Apple guideline 3.1.3). Add the subscription link behind a "Manage Subscription" button that opens a system browser, not an in-app WebView. | External web subscription via Whop |
| AsyncStorage for auth tokens (if any React Native code is ever added) | Not applicable to Flutter, but Flutter equivalent is shared_preferences — never store auth tokens there. | flutter_secure_storage |
| Sentry 9.x beta for Flutter | sentry_flutter 9.x is in beta as of research date. Pinning a beta in production introduces risk. | sentry_flutter ^8.x (stable) |

---

## App Store Compliance Checklist

This is the most operationally complex aspect of the v3.0 launch. Sports analytics apps without in-app wagering are routinely approved (BettingPros, OddsJam, Outlier, Oddschecker+ all live on App Store). The risk is in how the app is positioned.

### Apple App Store (iOS)

**Guideline 5.3 — Gambling:**
SharpEdge does NOT facilitate real-money wagering in the app. It provides odds data, EV calculations, and betting recommendations. This category (analytics/information) is approved: BettingPros, OddsJam, and Outlier are direct comparables currently live on App Store.

**Requirements to avoid rejection:**
- [ ] App does NOT allow users to place bets through the app
- [ ] App does NOT process deposits or withdrawals
- [ ] No links to sportsbook deposit pages from within the app (linking to a sportsbook's website for odds viewing is fine; linking to their signup/deposit flow is gray area — avoid)
- [ ] Age rating: Set to **17+** in App Store Connect > Rating (content references gambling/betting)
- [ ] Privacy policy URL: Required. Must disclose data collection (Supabase user data, Sentry crash data, analytics events)
- [ ] App Store description: Emphasize "analytics," "research," "data," "tools" — not "betting tips" or "guaranteed picks"
- [ ] No "guaranteed wins" language anywhere in metadata or screenshots
- [ ] In-App Purchases: None required; subscription is managed via Whop (external). Do NOT add an in-app purchase for the subscription — Apple requires 30% commission on digital goods sold in-app
- [ ] If the app ever shows Kalshi market positions (prediction market execution): Kalshi is a CFTC-regulated exchange, not a sportsbook. Frame this as "prediction market analytics" not "betting." This distinction likely matters for App Review.

**Required for submission:**
- Apple Developer Program account ($99/yr)
- App Store Connect app record created (bundle ID registered)
- Privacy policy URL (public URL, can be a simple page on the marketing site)
- App icon: 1024x1024px, no alpha channel, no rounded corners (Apple applies them)
- Screenshots: Required for 6.5" iPhone (iPhone 14 Pro Max size) and optionally iPad

### Google Play Store (Android)

Google Play is more permissive than Apple for analytics apps. Real-money gambling apps require a gambling license and country restrictions; analytics apps do not.

**Requirements:**
- [ ] Google Play Developer account ($25 one-time)
- [ ] Age rating: Complete the IARC rating questionnaire; select 18+ for content referencing gambling
- [ ] Privacy policy URL: Same URL as Apple; required
- [ ] Data safety section in Play Console: Declare what data is collected (Firebase, Supabase, Sentry) and whether it's shared with third parties
- [ ] Target API level: Android 14 (API 34) — required for new apps as of August 2024
- [ ] App signing: Use Play App Signing (Google manages the signing key); upload key goes to Fastlane

**Google's gambling policy distinction:**
Apps that provide "general information" about gambling (odds, tips, statistics) without facilitating transactions are approved without a gambling license. Apps that allow users to place bets, deposit funds, or receive winnings require a license. SharpEdge falls clearly in the information category.

### Both Stores

- [ ] Privacy policy must cover: data collected, how it's used, third-party SDKs (Sentry, Supabase, Firebase), user rights (GDPR/CCPA if serving EU/CA users)
- [ ] Terms of Service: Recommended (not technically required by stores but protects against chargebacks/disputes)
- [ ] Disclaimer text: "For informational and entertainment purposes only. Not financial or gambling advice." Include this in the app's About/Settings screen.

**Confidence on App Store compliance:** MEDIUM-HIGH. Direct comparable apps (OddsJam, BettingPros, Outlier) are live and approved. The risk is if App Review misclassifies the app as a gambling app — mitigation is positioning language in the description. No real-money transaction capability in the app is the hard boundary that keeps this out of guideline 5.3.4.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| @sentry/nextjs ^8.x | Next.js 14.2.x | `onRequestError` hook requires @sentry/nextjs >=8.28.0 and Next.js 15; for Next.js 14, use the standard `instrumentation.ts` pattern without `onRequestError` |
| sentry_flutter ^8.x | Flutter >=3.24.0, Dart >=3.5.0 | The project's pubspec.yaml has `flutter: '>=3.10.0'` — verify actual installed Flutter SDK version is >=3.24.0 before adding sentry_flutter |
| flutter_native_splash ^2.4.0 | Flutter 3.x | Compatible with current SDK range |
| fastlane (latest) | Xcode 15+ (macOS runner) | GitHub's `macos-latest` runner provides Xcode 15/16; verify Xcode version compatibility with project's iOS deployment target |
| supabase_flutter ^2.6.0 | Flutter >=3.0.0 | Already in pubspec.yaml — no change needed |
| firebase_core ^3.6.0 | Flutter >=3.10.0 | Already in pubspec.yaml; Firebase is used for push notifications (firebase_messaging) |

---

## Deployment Architecture Summary

```
GitHub (main branch push)
  ├── Vercel (automatic) → Next.js web app → Production domain
  ├── Railway (automatic) → FastAPI webhook server → api.yourdomain.com
  ├── Railway (automatic) → Discord bot → always-on process
  └── GitHub Actions (manual tag or workflow_dispatch)
        ├── iOS job (macos-latest) → Fastlane → TestFlight → App Store
        └── Android job (ubuntu-latest) → Fastlane → Play Store internal track → Play Store
```

Keep web and Python deploys on automatic merge-to-main. Keep mobile deploys as manual triggers (workflow_dispatch or git tag) — app store reviews take 1-3 days and you don't want every backend commit triggering a mobile release.

---

## Sources

- [Vercel Pricing — Hobby vs Pro](https://vercel.com/pricing) — confirmed commercial use restriction on Hobby; Pro pricing ($20/mo); MEDIUM confidence
- [Railway FastAPI deployment docs](https://docs.railway.com/guides/fastapi) — confirmed Python/uv support; MEDIUM confidence
- [Flutter iOS CI/CD: Automated TestFlight with Fastlane & GitHub Actions (Jan 2026)](https://aws.plainenglish.io/flutter-ios-ci-cd-automated-testflight-deployment-with-fastlane-github-actions-step-by-step-ac3b4b1c7ce0) — confirmed current pattern; MEDIUM confidence
- [sentry_flutter on pub.dev](https://pub.dev/packages/sentry_flutter) — version 8.x stable, 9.x beta; MEDIUM confidence
- [Sentry Next.js docs](https://docs.sentry.io/platforms/javascript/guides/nextjs/) — confirmed wizard setup, instrumentation.ts pattern; HIGH confidence
- [Apple App Store Review Guidelines (Guideline 5.3)](https://developer.apple.com/app-store/review/guidelines/) — gambling requires real-money wagering; analytics category not subject to 5.3.4; MEDIUM confidence (direct fetch was truncated — relied on community analysis and live App Store examples)
- [BettingPros on App Store](https://apps.apple.com/us/app/bettingpros-sports-betting/id1468109182) — live comparable app; confirmed analytics-only apps are approved; HIGH confidence
- [OddsJam on App Store](https://apps.apple.com/us/app/oddsjam-sharp-sports-betting/id6448072108) — live comparable; HIGH confidence
- [Google Play gambling policy](https://support.google.com/googleplay/android-developer/answer/9877032) — confirmed analytics apps don't require gambling license; MEDIUM confidence
- [UptimeRobot Discord integration](https://uptimerobot.com/integrations/discord-integration/) — free tier confirmed; HIGH confidence
- [Fly.io vs Railway comparison](https://thesoftwarescout.com/fly-io-vs-railway-2026-which-developer-platform-should-you-deploy-on/) — DX tradeoff analysis; MEDIUM confidence

---

*Stack research for: SharpEdge v3.0 Launch & Distribution*
*Researched: 2026-03-21*
*Supersedes: deployment and mobile sections of .planning/research/STACK.md (v2.0, 2026-03-13)*
