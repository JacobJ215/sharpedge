# Swarm Monitor Dashboard Design

**Date:** 2026-03-20
**Status:** Approved — ready for implementation planning

---

## Goal

Add a "Swarm Monitor" section to the SharpEdge web dashboard that gives real-time transparency into the trading swarm pipeline: market scanning, probability calibration, position management, and post-mortem analysis. Enterprise-ready, matching existing frontend style.

## Architecture

**Approach:** Single tabbed page + 2 new lightweight API endpoints.

**Routing:** New `/swarm` page in the Next.js dashboard. Tab state managed via URL query param `?tab=scanner` (default). Tab options: `scanner` | `prediction` | `risk` | `post-mortem`.

**Data refresh:** SWR with `refreshInterval: 5000` (5-second polling) on all panels.

**Data sources (hybrid):**
- Scanner → `GET /api/v1/swarm/pipeline` (new webhook server endpoint)
- Prediction → `GET /api/v1/swarm/calibration` (new webhook server endpoint)
- Risk → Supabase `paper_trades` + `open_positions` direct read
- Post-Mortem → Supabase `paper_trades` where `pnl < 0` and `resolved_at IS NOT NULL`

**Visual style:** Matches existing frontend — `bg-zinc-950`, `border-zinc-800`, emerald (`#10b981`) primary accent, small-caps labels (`text-[9px]` / `text-[10px]`), `font-mono` for numbers, thin `border` separators, animated pulse for live indicators.

---

## File Structure

### New files

| Path | Purpose |
|------|---------|
| `apps/web/src/app/(dashboard)/swarm/page.tsx` | Tabbed page shell with URL-driven tab state |
| `apps/web/src/components/swarm/scanner-panel.tsx` | Market Filter Agent pipeline view |
| `apps/web/src/components/swarm/prediction-panel.tsx` | Probability Calibration Engine view |
| `apps/web/src/components/swarm/risk-panel.tsx` | Risk Agent position management view |
| `apps/web/src/components/swarm/post-mortem-panel.tsx` | Failed trade analysis view |
| `apps/webhook_server/src/sharpedge_webhooks/routes/v1/swarm.py` | 2 new FastAPI endpoints |

### Modified files

| Path | Change |
|------|--------|
| `apps/web/src/app/(dashboard)/layout.tsx` | Add "Swarm" nav item with robot/swarm icon |
| `apps/webhook_server/src/sharpedge_webhooks/routes/v1/__init__.py` | Register swarm router |

---

## Nav Item

Inserted between "Markets" and "Analytics" in the sidebar. Label: `Swarm`. Icon: grid/hexagon SVG consistent with existing nav icon style. Active state: emerald text + dot indicator (same pattern as all nav items).

---

## Page Shell (`swarm/page.tsx`)

- Header row: "Swarm Monitor" label + horizontal rule + animated live dot
- Tab row: 4 tabs (Scanner | Prediction | Risk | Post-Mortem), active tab underlined with `border-b-2 border-emerald-500`
- Tab state: read/write `?tab=` URL search param via `useSearchParams` + `useRouter`
- Loading skeleton: 3 pulse bars while SWR loads
- Each tab renders its panel component; only active tab fetches data (SWR key is null when tab inactive)

---

## Scanner Panel (`scanner-panel.tsx`)

**Data source:** `GET /api/v1/swarm/pipeline` → 5s SWR

**API response shape:**
```ts
{
  agent_status: string          // e.g. "Running Time to Resolution..."
  active_markets: number        // count passing all complete filters
  steps: Array<{
    step: number                // 1–4
    name: string                // "Liquidity Filter"
    description: string         // "Min $50K liquidity pool"
    status: "complete" | "active" | "pending"
    passed: number | null       // null if pending
    removed: number | null      // null if pending/active
  }>
  qualified_markets: Array<{
    market_id: string
    title: string
    edge: number
    platform: string
  }>
}
```

**Layout:**
- Agent header: icon box + "Market Filter Agent" + subtitle + active markets count (large mono)
- Section label: "Filter Pipeline"
- 4 filter step cards stacked vertically:
  - Complete step: numbered circle (emerald outline), name, description, passed count, removed count (red)
  - Active step: filled emerald circle, emerald text, "Running..." label
  - Pending step: grey circle, dimmed (opacity-50)
- Section label: "Qualified Markets" + count badge
- Empty state or list of qualified markets with edge %

**Backend endpoint logic (`swarm.py`):**
Reads `paper_trades` (count of open paper trades), `open_positions` to derive approximate filter step counts. Returns hardcoded step names/descriptions with derived counts. Falls back gracefully to zeros on any Supabase error.

---

## Prediction Panel (`prediction-panel.tsx`)

**Data source:** `GET /api/v1/swarm/calibration` → 5s SWR

**API response shape:**
```ts
{
  latest: {
    market_id: string
    market_title: string          // derived from market_id if no title stored
    resolve_date: string | null
    volume: number | null
    base_prob: number             // from paper_trades entry_price pre-calibration
    calibrated_prob: number       // from paper_trades entry_price
    market_price: number          // from paper_trades entry_price (market implied)
    edge: number                  // calibrated_prob - market_price
    direction: "BUY" | "SELL" | null
    confidence_score: number
    features: {
      sentiment_score: number
      time_decay: number
      market_correlation: number
    }
    llm_adjustment: number        // calibrated - base
    model_confidence: {
      data_quality: "High" | "Medium" | "Low"
      feature_signal: "Strong" | "Moderate" | "Weak"
      uncertainty: "Low" | "Moderate" | "High"
    }
  } | null
  recent: Array<{
    market_id: string
    base_prob: number
    calibrated_prob: number
    created_at: string
  }>
}
```

**Layout (two-column):**

Left column:
- Agent header: purple icon + "Prediction Agent" + "Probability Calibration Engine" + model badges (XGBoost, Claude)
- Signal features card: 3 rows (sentiment_score, time_decay, market_correlation) each with label, mini progress bar, and value
- Raw probability card: large mono percentage
- LLM Calibrator card: status dot + "Complete", news_analysis / expert_consensus / uncertainty_factor rows, calibration adjustment value
- Ensemble output card: emerald border, "True Probability" large mono

Right column:
- Market detail card: title, resolve date + volume
- Probability comparison card: two bar rows (Market Price purple, True Probability emerald) with percentages
- Detected edge card: edge % large + BUY/SELL signal badge
- Model confidence card: 3 dot indicators (data quality, feature signal, uncertainty)
- Recent predictions log: last 5 predictions as rows (market_id truncated, base → calibrated)

**Empty state:** "No predictions recorded yet — daemon processing markets" when `latest` is null.

---

## Risk Panel (`risk-panel.tsx`)

**Data source:** Supabase `paper_trades` + `open_positions` + `trading_config` — direct client reads at 5s SWR interval.

**Layout (two-column):**

Left column:
- Agent header: red icon + "Risk Agent" + "Automated Position Management" + mode badge (Paper/Live)
- Bankroll card: total from `PAPER_BANKROLL` env (or sum from open positions), capital allocation bar (active/pending/available proportions), legend
- Risk limits card: table of 6 limits pulled from `trading_config` Supabase table (max_category_exposure, max_total_exposure, daily_loss_limit, min_liquidity, min_edge, kelly_fraction)
- Circuit breaker card: consecutive loss count from `paper_trades` (last N trades), status (Normal / Triggered / Paused)

Right column:
- Incoming trade card: most recent `paper_trades` row where `status = 'pending'` or most recently opened — shows market_id, direction, edge stats (4-up badge grid: Edge / Market / True Prob / Confidence)
- Position size check card: calculated size, max allowed (5% bankroll), final position, % of bankroll with pass/fail indicator
- Trade status card: approved (emerald) or dropped (red) based on trade status
- Recent decisions list: last 10 `paper_trades` rows showing market_id + direction + APPROVED/DROPPED status

---

## Post-Mortem Panel (`post-mortem-panel.tsx`)

**Data source:** Supabase `paper_trades` where `pnl < 0` and `resolved_at IS NOT NULL`, ordered by `resolved_at DESC`.

**Layout (two-column):**

Left column:
- Agent header: amber icon + "Post-Mortem Analysis" + "Learning from failed predictions" + root cause status badge
- Failed prediction card (red border): trade title (from market_id), loss amount, our probability, position details (direction + entry price), actual outcome, model confidence, edge estimated, context paragraph (from `narrative` field if available)
- Promotion gate card: 4 key gate metrics (resolved count / 50 needed, period days / 30, win rate, live status) — links visual progress toward gate criteria

Right column:
- Analysis agents grid (5 cards: Data / Sentiment / Timing / Model / Risk): each shows name, "✓ Complete" status, and a key finding derived from the trade data. Risk card highlighted in red if a risk flag was present.
- Analysis log: scrollable timestamped log of analysis messages. Entries derived from `paper_trades` metadata fields. Color-coded by agent tag: `[DATA]` emerald, `[MODEL]` blue, `[SENT]` amber, `[RISK]` violet, `[TIME]` zinc.

**Empty state:** "No failed predictions yet — keep trading in paper mode" when no negative PnL trades exist.

---

## Backend Endpoints (`swarm.py`)

### `GET /api/v1/swarm/pipeline`

Auth: none (same pattern as existing prediction-markets endpoints).

Logic:
1. Connect to Supabase with `SUPABASE_SERVICE_KEY`
2. Query `open_positions` count → `active_markets`
3. Query `paper_trades` counts to derive step approximations
4. Return step array with hardcoded names/descriptions, derived counts
5. On any exception: return zeros with `status: "unavailable"`

### `GET /api/v1/swarm/calibration`

Auth: none.

Logic:
1. Query last 10 `paper_trades` rows ordered by `created_at DESC`
2. Map most recent row to `latest` shape
3. Derive `base_prob`, `calibrated_prob` from trade fields
4. Derive `features` from available fields (fallback to 0.0 if missing)
5. Map remaining rows to `recent` array
6. On any exception: return `{ latest: null, recent: [] }`

---

## Error Handling

- All SWR fetches: on error, show inline "Failed to load — retrying" message with retry dot animation
- All panels: graceful empty states for zero data
- Backend endpoints: always return 200 with empty/zero data on Supabase failure (never 500)
- Tab switching: instant (no loading flash — SWR caches previous data)

---

## Testing

- Unit tests for each panel component (mock SWR data, assert key elements render)
- Unit tests for `swarm.py` endpoints (mock Supabase client, assert response shape)
- Integration: nav item links to `/swarm`, tab switching changes URL, panels render without errors

---

## Out of Scope

- WebSocket / SSE real-time push (polling is sufficient for paper mode)
- Mobile app swarm monitor (web-only for this phase)
- Historical replay / time-scrubbing of pipeline state
- User-configurable refresh interval
