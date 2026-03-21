# Requirements: SharpEdge v3.0

**Defined:** 2026-03-21
**Core Value:** Surface high-alpha betting edges — ranked by composite probability score — before anyone else sees them, with bankroll risk quantified so users bet the right size every time.

## v3.0 Requirements

### Deployment

- [ ] **DEPLOY-01**: Web app is accessible at a live production domain
- [ ] **DEPLOY-02**: Backend webhook server is deployed and receiving Whop/Stripe webhooks
- [ ] **DEPLOY-03**: Discord bot is running in production (not local)
- [ ] **DEPLOY-04**: CI/CD pipeline deploys web app on merge to main

### Auth & Accounts

- [ ] **AUTH-01**: User can sign up with email on web app
- [ ] **AUTH-02**: User can log in to web app and mobile app with the same account
- [ ] **AUTH-03**: Free tier user sees limited features with clear upgrade prompt
- [ ] **AUTH-04**: Paid subscription via Whop automatically unlocks full access on web + mobile
- [ ] **AUTH-05**: User can view their current tier and manage subscription from within the app

### Discord Community

- [ ] **DISCORD-01**: Discord server has channel structure for free vs paid tiers
- [ ] **DISCORD-02**: Subscribing via Whop automatically assigns the correct Discord role
- [ ] **DISCORD-03**: Bot commands are restricted by role (free users see limited commands)
- [ ] **DISCORD-04**: New member onboarding flow guides free users toward subscribing
- [ ] **DISCORD-05**: Server has rules, FAQ, and getting-started resources

### Mobile & App Stores

- [ ] **MOBILE-01**: iOS app works end-to-end (core screens functional, no crashes)
- [ ] **MOBILE-02**: Android app works end-to-end
- [ ] **MOBILE-03**: App Store listing exists with screenshots, description, and privacy policy
- [ ] **MOBILE-04**: App approved and live on Apple App Store
- [ ] **MOBILE-05**: App approved and live on Google Play Store

### Growth Funnel

- [ ] **GROWTH-01**: Marketing landing page clearly communicates value and pricing tiers
- [ ] **GROWTH-02**: Landing page converts visitor to free signup or Discord join
- [ ] **GROWTH-03**: New user onboarding shows key features within first session
- [ ] **GROWTH-04**: Social media profile (X/Twitter at minimum) exists with content strategy

### Platform Monitoring

- [ ] **MONITOR-01**: Error tracking (Sentry) active for web and mobile
- [ ] **MONITOR-02**: Bot downtime triggers an alert
- [ ] **MONITOR-03**: Key user events are tracked (signup, upgrade, feature usage)

## Future Requirements (v3.1+)

- Referral / affiliate program
- In-app push notification campaigns
- Admin dashboard for user management
- Polymarket live execution (deferred from v2.0)
- Blog / content marketing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time user chat | Not core to platform value |
| Referral system | Post-launch; need baseline first |
| Admin dashboard | Can manage via Supabase + Whop dashboards initially |
| Paid ads | User wants organic/social-first growth |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | TBD | Pending |
| DEPLOY-02 | TBD | Pending |
| DEPLOY-03 | TBD | Pending |
| DEPLOY-04 | TBD | Pending |
| AUTH-01 | TBD | Pending |
| AUTH-02 | TBD | Pending |
| AUTH-03 | TBD | Pending |
| AUTH-04 | TBD | Pending |
| AUTH-05 | TBD | Pending |
| DISCORD-01 | TBD | Pending |
| DISCORD-02 | TBD | Pending |
| DISCORD-03 | TBD | Pending |
| DISCORD-04 | TBD | Pending |
| DISCORD-05 | TBD | Pending |
| MOBILE-01 | TBD | Pending |
| MOBILE-02 | TBD | Pending |
| MOBILE-03 | TBD | Pending |
| MOBILE-04 | TBD | Pending |
| MOBILE-05 | TBD | Pending |
| GROWTH-01 | TBD | Pending |
| GROWTH-02 | TBD | Pending |
| GROWTH-03 | TBD | Pending |
| GROWTH-04 | TBD | Pending |
| MONITOR-01 | TBD | Pending |
| MONITOR-02 | TBD | Pending |
| MONITOR-03 | TBD | Pending |

**Coverage:**
- v3.0 requirements: 26 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 26 ⚠️

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
