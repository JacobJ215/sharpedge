# Technology Stack

**Project:** SharpEdge v2 — Institutional-Grade Sports Betting Intelligence Platform
**Researched:** 2026-03-13
**Research mode:** Upgrade / Brownfield — existing Python monorepo
**Confidence note:** WebSearch and WebFetch were unavailable during this research session. All version numbers and recommendations derive from training knowledge (cutoff August 2025). Versions marked [VERIFY] should be confirmed against PyPI / npm before pinning in pyproject.toml.

---

## Recommended Stack

### Agent Orchestration Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| langgraph | 0.2.x [VERIFY] | StateGraph multi-agent orchestration | Graph-based routing with explicit state transitions; parallel node execution via Send API; built-in interrupt/resume for human-in-the-loop; replaces flat OpenAI Agents SDK setup. Designed for exactly this pattern: specialist nodes (EV, regime, Kelly, copilot) fanning out from a coordinator node. |
| langchain-openai | 0.1.x [VERIFY] | LangChain OpenAI integration for LangGraph nodes | LangGraph nodes are plain callables; langchain-openai provides the ChatOpenAI wrapper with structured output (`.with_structured_output()`) needed for typed node return values. |
| langgraph-checkpoint-postgres | 0.1.x [VERIFY] | Persistent checkpointing to Supabase/PostgreSQL | Enables conversation memory and state resumption across Discord sessions. Uses existing Supabase connection — no new infrastructure. |

**Why LangGraph over OpenAI Agents SDK:**
The existing 3-agent flat setup in `apps/bot/` cannot express the 9-node directed workflow described in PROJECT.md (alpha scoring, regime gate, Kelly sizing, copilot, LLM eval gate). LangGraph's StateGraph models exactly this as a DAG with conditional edges. The `Send` API allows fanning out to all 5 ensemble models in parallel, collecting results into `Annotated[list, operator.add]` state fields. OpenAI Agents SDK lacks graph-based routing and persistent checkpointing without custom plumbing. Confidence: HIGH (LangGraph is the dominant Python agent framework for complex multi-step workflows as of 2025).

**Why NOT LangChain Expression Language (LCEL) alone:**
LCEL chains are linear. This platform needs conditional branching (reject gate), parallel fan-out (ensemble models), and state accumulation (portfolio context). LCEL cannot express these without wrapping in LangGraph anyway.

---

### Quantitative / ML Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| numpy | 2.0+ | Monte Carlo simulation engine, array math | Vectorized path simulation: generate 10,000 bet sequences in one `np.random.choice` call. Already in codebase at 1.26+; upgrade to 2.0 for performance improvements and copy-on-write semantics. |
| scipy | 1.14+ | Statistical distributions, optimization | `scipy.stats.beta` for Bayesian EV confidence already used. Add `scipy.optimize.minimize_scalar` for optimal Kelly fraction, `scipy.special.expit` for logistic calibration. Already present — extend, don't replace. |
| hmmlearn | 0.3.x [VERIFY] | 7-state Hidden Markov Model for regime detection | Industry-standard Baum-Welch EM training for HMMs in Python. Scipy-dependent, well-maintained, scikit-learn compatible API. `GaussianHMM` and `GMMHMM` cover the betting market use case (7 states: sharp, public, steam, buyback, thin, locked, neutral). Simpler and more stable than pomegranate for this use case. |
| scikit-learn | 1.5+ | Ensemble models, Platt scaling calibration | `CalibratedClassifierCV(method='sigmoid')` implements Platt scaling — wrap existing gradient boosting models directly. `cross_val_predict` with `cv=TimeSeriesSplit` for out-of-sample calibration. Already present at 1.5+. |
| lightgbm | 4.x [VERIFY] | Upgraded gradient boosting (replace sklearn GBM) | Faster training, native categorical support, better handling of sparse features (injury/weather flags). Sklearn-compatible API — drop-in replacement for existing `GradientBoostingClassifier`. Only add if benchmark shows >10% gain. |

**hmmlearn vs pomegranate decision:**
pomegranate v1.x (2024 rewrite) introduced breaking API changes, dropped some HMM variants, and has more complex installation due to PyTorch dependency. hmmlearn 0.3.x is stable, well-documented, scikit-learn compatible, and has no heavy dependencies. For a 7-state Gaussian HMM over betting market features (line movement velocity, volume, sharp percentage), hmmlearn is the correct choice. Confidence: HIGH for hmmlearn selection, MEDIUM for version number.

**Monte Carlo pattern (numpy):**
```python
# Vectorized ruin simulation — 10k paths, 500 bets each
rng = np.random.default_rng(seed)
outcomes = rng.choice([win_pct, -loss_pct], size=(n_paths, n_bets), p=[edge_prob, 1-edge_prob])
bankroll_paths = initial_bankroll * np.cumprod(1 + outcomes * kelly_fraction, axis=1)
ruin_probability = np.mean(np.any(bankroll_paths <= 0.1 * initial_bankroll, axis=1))
```
Use `np.random.default_rng` (not `np.random.seed`) for reproducibility and performance. Confidence: HIGH.

**Platt scaling pattern:**
```python
from sklearn.calibration import CalibratedClassifierCV
calibrated = CalibratedClassifierCV(base_estimator=gbm, method='sigmoid', cv='prefit')
calibrated.fit(X_cal, y_cal)  # calibration holdout set only
```
Use `cv='prefit'` when the base model is already trained on historical data — avoids leaking test data into calibration. Confidence: HIGH.

---

### Caching Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| redis-py | 5.0+ | Real-time odds caching, rate limit throttling | Already in codebase (`packages/odds_client/cache.py`). Extend with: TTL-keyed odds snapshots (30s TTL for live lines, 5min for stale), rate limit token buckets per API key, pub/sub channel for line movement alerts. |
| redis (server) | 7.x [VERIFY] | In-memory data store | Redis 7 adds multi-part AOF persistence and improved memory efficiency. Use `maxmemory-policy allkeys-lru` for odds cache — evict oldest odds when memory limit hit. |

**Redis usage pattern for odds pipeline:**
```
Key schema:
  odds:{sport}:{event_id}:{book}  → JSON blob, TTL=30s
  line_move:{event_id}            → sorted set by timestamp, score=line_value
  rate_limit:{api_key}            → integer counter, TTL=window_seconds
  alpha:{event_id}                → composite alpha score, TTL=60s
```
Cache the computed alpha score (60s TTL) to avoid recomputing 9-node LangGraph workflow on every Discord mention. Invalidate on significant line movement. Confidence: HIGH for pattern, MEDIUM for exact TTL values.

---

### API Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.115+ | REST API for web + mobile clients | Already present. Add versioned router (`/v1/`), WebSocket endpoint for real-time alpha score streaming, JWT middleware for Whop token validation. |
| uvicorn | 0.30+ | ASGI server | Already present. Add `--workers 4` in production for CPU-bound model inference. |
| websockets | 12.x [VERIFY] | WebSocket protocol support | FastAPI's built-in WebSocket support is sufficient; no separate library needed unless load testing reveals gaps. |

---

### Web Dashboard

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | 14.2.x [VERIFY] | Web dashboard (8 pages) | App Router is stable and production-ready in 14.x. Server Components reduce client bundle size for the analytics-heavy dashboard pages. Route Handlers replace getServerSideProps for API proxying. Do NOT upgrade to Next.js 15 until the ecosystem (shadcn/ui, next-auth, Tanstack Query) catches up — 14 is the safe production choice as of early 2026. |
| TypeScript | 5.x | Type safety | Required. Shared types with Expo via a `packages/types/` workspace package. |
| Tailwind CSS | 3.4.x [VERIFY] | Utility-first styling | Standard for Next.js projects. Pairs with shadcn/ui. |
| shadcn/ui | latest | Component library | Built on Radix UI primitives; unstyled accessible components that compose well with Tailwind. Preferred over Chakra/MUI for bundle size and composability. |
| Recharts | 2.x [VERIFY] | Charts and visualizations | React-first charting library. Lighter than Chart.js for SSR. Use for: bankroll path distributions, win rate over time, regime state timeline. |
| Tanstack Query | 5.x [VERIFY] | Server state management | Replaces useEffect+fetch patterns. Handles stale-while-revalidate for odds data, WebSocket subscriptions for live alpha scores. |
| next-auth | 4.x [VERIFY] | Authentication | JWT session validation against Whop membership tokens. Use `CredentialsProvider` with Whop API token verification. |
| Zustand | 4.x [VERIFY] | Client state management | Minimal global state: user preferences, notification settings, active bets tracker. Lighter than Redux for this scope. |

**Why Next.js 14 over 15:**
Next.js 15 (released late 2024) changed caching defaults (fetch is no longer cached by default), modified the params type signature for dynamic routes to be async, and introduced breaking changes to how middleware interacts with the cache. The ecosystem — particularly shadcn/ui generators, next-auth v4, and common patterns for App Router — targets 14.x. The SharpEdge web dashboard does not need the specific improvements in 15 (React 19 concurrent features, improved dev server). Stay on 14.2.x LTS until the milestone after web launch. Confidence: MEDIUM (based on known 15.x breaking changes as of Aug 2025; verify current ecosystem compatibility).

---

### Mobile App

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Expo | SDK 51 [VERIFY] | React Native mobile app (iOS + Android) | Managed workflow eliminates native build complexity. EAS Build handles CI/CD. SDK 51 supports React Native 0.74 with the new architecture (Fabric/JSI) opt-in. |
| Expo Router | 3.x [VERIFY] | File-based navigation | Mirrors Next.js App Router conventions — the shared TypeScript dev knows one routing pattern. |
| Expo Notifications | latest | Push notifications for alpha alerts | Primary mobile value prop: push notification when high-alpha edge detected. Requires Expo push token registration and FCM/APNs config. |
| React Native | 0.74+ [VERIFY] | Cross-platform rendering | Bundled with Expo SDK 51. New Architecture is stable enough for production in SDK 51. |
| NativeWind | 4.x [VERIFY] | Tailwind CSS for React Native | Shares Tailwind class names with the Next.js app — designers work in one vocabulary. v4 uses CSS variables and works with Expo Router. |
| Tanstack Query | 5.x | Server state on mobile | Same library as web — shared query hooks via `packages/hooks/` workspace package. Eliminates data-fetching logic duplication. |
| Expo SecureStore | latest | Secure token storage | Store JWT/session tokens in the device keychain. Never use AsyncStorage for auth tokens. |

**Why NOT bare React Native workflow:**
The Discord bot + FastAPI + LangGraph backend is already complex. Expo managed workflow eliminates native Xcode/Gradle build management, which is not the team's core competency. EAS Build replaces local native builds. The only reason to eject is if a required native module isn't available in Expo — unlikely for this feature set (push notifications, HTTP, secure storage are all first-class Expo features). Confidence: HIGH.

**Why NOT Flutter:**
Python backend with TypeScript front-ends shares types via workspace packages. Flutter (Dart) breaks this shared-type advantage and doubles the language surface area. Confidence: HIGH.

---

### Shared TypeScript Infrastructure (Web + Mobile)

| Technology | Purpose | Why |
|------------|---------|-----|
| `packages/api-client/` (monorepo workspace package) | Shared typed API client | Single source of truth for endpoint types. Generated from FastAPI OpenAPI schema using `openapi-typescript`. Both Next.js and Expo import from this package. |
| `packages/hooks/` (monorepo workspace package) | Shared Tanstack Query hooks | `useAlphaScores()`, `useBankrollSimulation()`, `useRegimeState()` — identical business logic across web and mobile. |
| `packages/types/` (monorepo workspace package) | Shared TypeScript types | Mirror of Pydantic models from Python backend. Keep in sync manually or via openapi-typescript codegen. |
| openapi-typescript | 6.x [VERIFY] | Generate TypeScript types from FastAPI schema | Run against `/openapi.json` endpoint. Eliminates manual type duplication. |

**Monorepo structure for TypeScript packages:**
Use npm/pnpm workspaces (separate from the uv Python workspace) for the TypeScript side. The repo has two workspace roots: `pyproject.toml` (Python/uv) and `package.json` (TypeScript/pnpm). Keep them strictly separated at the root — no mixing.

---

### Database Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Supabase | 2.0+ | Primary PostgreSQL database | Already established with 5 migrations and domain-scoped query modules. Keep. Add: `bet_simulations` table for Monte Carlo result persistence, `regime_states` table for HMM state history, `alpha_scores` table for composite score audit trail. |
| asyncpg | 0.29+ [VERIFY] | Direct async PostgreSQL driver | Use alongside supabase-py for high-throughput writes (bulk simulation results, regime state updates). supabase-py's REST layer adds latency for bulk inserts. |
| supabase-py | 2.0+ | Supabase client for auth, realtime, storage | Keep for auth validation, realtime subscriptions (line movement events), and storage (backtesting report PDFs). |

---

### Deployment Infrastructure

| Technology | Purpose | Why |
|------------|---------|-----|
| Railway or Render | Python backend hosting | FastAPI + Discord bot as separate Railway services. Supports Redis add-on. More predictable pricing than AWS Lambda for always-on Discord bot. |
| Vercel | Next.js hosting | Native Next.js deployment; Edge Network for sub-100ms dashboard loads. |
| EAS (Expo Application Services) | Mobile app builds + OTA updates | Managed iOS/Android builds without local Xcode. OTA updates push odds algorithm improvements without App Store review. |
| Upstash Redis | Managed Redis | Serverless Redis with per-request pricing — better than provisioned Redis for variable load. HTTP REST API works from Edge functions. |
| Docker Compose | Local development | Already present (`docker-compose.yml` for Redis). Extend with PostgreSQL local mirror for offline development. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Agent framework | LangGraph | OpenAI Agents SDK (existing) | Flat 3-agent setup cannot express 9-node StateGraph with conditional edges and parallel fan-out |
| Agent framework | LangGraph | CrewAI | CrewAI is role-based, not graph-based; no persistent checkpointing; less control over exact execution flow |
| HMM library | hmmlearn | pomegranate | pomegranate v1.x added PyTorch dependency and breaking API changes in 2024 rewrite; hmmlearn is simpler, more stable, sklearn-compatible |
| HMM library | hmmlearn | statsmodels HMM | statsmodels HMM is less feature-complete than hmmlearn; no Gaussian mixture emissions |
| Gradient boosting | scikit-learn GBM (keep) | XGBoost | XGBoost is a valid upgrade but requires additional installation; LightGBM is faster for tabular sports data if an upgrade is warranted |
| Web framework | Next.js 14 | Next.js 15 | 15.x breaking changes in caching, params types, middleware; ecosystem not fully adapted as of early 2026 |
| Web framework | Next.js 14 | Remix | Smaller ecosystem, fewer pre-built UI components, less community tooling for dashboards |
| Mobile | Expo (managed) | Bare React Native | Expo eliminates native build complexity without trading away needed capabilities |
| Mobile | Expo | Flutter | Dart breaks shared TypeScript type strategy between web and mobile |
| Charts | Recharts | D3.js | D3 requires manual React reconciliation; Recharts is React-first |
| Charts | Recharts | Victory | Recharts has more active maintenance and larger community |
| State (web) | Zustand | Redux Toolkit | Redux is overkill for the limited global state in this dashboard; Zustand is 3x smaller bundle |
| Calibration | sklearn CalibratedClassifierCV | Manual isotonic regression | sklearn implementation is well-tested; manual isotonic regression only justified if sklearn sigmoid (Platt) underperforms on calibration curve |
| Redis | redis-py (existing) | aioredis | redis-py 5.0+ has native async support via `redis.asyncio`; aioredis is deprecated and merged into redis-py |

---

## Versions to Pin (pyproject.toml)

```toml
# Agent orchestration
langgraph = ">=0.2.0,<0.3"
langchain-openai = ">=0.1.0,<0.2"
langgraph-checkpoint-postgres = ">=0.1.0,<0.2"

# Existing — extend
numpy = ">=2.0.0,<3"
scipy = ">=1.14.0,<2"
scikit-learn = ">=1.5.0,<2"

# New additions
hmmlearn = ">=0.3.0,<0.4"
lightgbm = ">=4.0.0,<5"      # Only add if benchmarks justify

# Already present — keep
redis = ">=5.0.0,<6"
fastapi = ">=0.115.0,<0.116"
uvicorn = ">=0.30.0,<1"
supabase = ">=2.0.0,<3"
pydantic = ">=2.0.0,<3"
```

```json
// package.json (TypeScript workspace root)
{
  "dependencies": {
    "next": "14.2.x",
    "react": "18.x",
    "typescript": "5.x",
    "tailwindcss": "3.4.x",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.0.0",
    "recharts": "^2.0.0",
    "next-auth": "^4.0.0",
    "openapi-typescript": "^6.0.0"
  }
}
```

```json
// apps/mobile/package.json
{
  "dependencies": {
    "expo": "~51.0.0",
    "expo-router": "~3.0.0",
    "expo-notifications": "latest",
    "expo-secure-store": "latest",
    "nativewind": "^4.0.0",
    "@tanstack/react-query": "^5.0.0"
  }
}
```

All version constraints marked [VERIFY] above should be confirmed against PyPI / npm before final pinning. Knowledge cutoff is August 2025.

---

## What NOT to Use

| Library / Pattern | Reason |
|-------------------|--------|
| `aioredis` | Deprecated; merged into `redis-py >= 4.2`. Use `redis.asyncio` instead. |
| `openai-agents` (existing) | Replace with LangGraph for the 9-node orchestration workflow. Keep only if a simpler single-step tool call doesn't need graph routing. |
| LangChain chains (LCEL) without LangGraph | Cannot express conditional branching, parallel fan-out, or persistent state. |
| `pomegranate` | PyTorch dependency adds 2GB to the container; API unstable after v1 rewrite; hmmlearn covers all needed HMM variants. |
| `asyncio.sleep` polling in Discord bot | Replace with LangGraph's interrupt/resume pattern + Redis pub/sub for event-driven alerts. |
| `matplotlib` for web/mobile output | Matplotlib generates static PNGs — wrong for interactive web dashboards. Port visualizations to Recharts on the front-end. Keep matplotlib only for Discord embeds where a PNG is appropriate. |
| Manual probability calibration | Do not hand-roll Platt scaling — `sklearn.calibration.CalibratedClassifierCV(method='sigmoid')` is correct, tested, and handles edge cases. |
| `np.random.seed()` / `np.random.rand()` (legacy API) | Use `np.random.default_rng()` for reproducibility and thread safety in Monte Carlo simulations. |
| Next.js Pages Router | Do not add new pages in the Pages Router. Use App Router exclusively for all new web pages. |
| AsyncStorage for tokens (mobile) | Security vulnerability. Use `expo-secure-store` for all auth tokens. |

---

## Sources

**Note:** Web access was unavailable during this research session. All findings are from training knowledge (cutoff August 2025). Confidence levels reflect this limitation.

| Claim | Confidence | Basis |
|-------|------------|-------|
| LangGraph StateGraph for multi-agent orchestration | HIGH | Well-documented pattern, dominant framework for Python agent graphs as of 2025 |
| hmmlearn over pomegranate | HIGH | pomegranate v1 PyTorch dependency and API instability well-known in ML community |
| numpy 2.0 default_rng for Monte Carlo | HIGH | Documented numpy best practice since 1.17 |
| sklearn CalibratedClassifierCV Platt scaling | HIGH | Official sklearn API, stable since 0.20 |
| Next.js 14.2 over 15 | MEDIUM | Based on known 15.x breaking changes; verify current shadcn/ui and next-auth compatibility |
| Expo SDK 51 | MEDIUM | SDK 51 released May 2024; SDK 52/53 may be current — verify before starting mobile phase |
| LangGraph version 0.2.x | MEDIUM | Active development; minor version may be higher — verify on PyPI |
| langgraph-checkpoint-postgres | MEDIUM | Package exists but verify exact name and version on PyPI |
| Redis 7.x | MEDIUM | Current as of training cutoff; verify latest stable |
| lightgbm recommendation | LOW | Conditional upgrade — benchmark required before adopting |
