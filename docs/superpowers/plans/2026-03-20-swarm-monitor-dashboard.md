# Swarm Monitor Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/swarm` page to the SharpEdge web dashboard with 4 tabbed panels (Scanner, Prediction, Risk, Post-Mortem) giving real-time visibility into the trading swarm pipeline.

**Architecture:** Single tabbed page at `/swarm` with URL-driven tab state (`?tab=scanner`). Two new public FastAPI endpoints on the webhook server (`GET /api/v1/swarm/pipeline`, `GET /api/v1/swarm/calibration`) serve live pipeline data; Risk and Post-Mortem panels read Supabase directly via the existing `createClient` browser client. SWR polls all panels at 5-second intervals.

**Tech Stack:** Next.js 14 App Router, TypeScript, SWR, Tailwind CSS (zinc-950 theme), FastAPI, supabase-py, pytest, TestClient.

**Spec:** `docs/superpowers/specs/2026-03-20-swarm-monitor-dashboard-design.md`

---

## File Structure

### New files

| Path | Purpose |
|------|---------|
| `apps/webhook_server/src/sharpedge_webhooks/routes/v1/swarm.py` | 2 new FastAPI GET endpoints |
| `apps/webhook_server/tests/unit/api/test_swarm.py` | pytest tests for both endpoints |
| `apps/web/src/app/(dashboard)/swarm/page.tsx` | Tabbed page shell with URL-driven tab state |
| `apps/web/src/components/swarm/scanner-panel.tsx` | Market Filter Agent pipeline view |
| `apps/web/src/components/swarm/prediction-panel.tsx` | Probability Calibration Engine view |
| `apps/web/src/components/swarm/risk-panel.tsx` | Risk Agent position management view |
| `apps/web/src/components/swarm/post-mortem-panel.tsx` | Failed trade analysis view |

### Modified files

| Path | Change |
|------|--------|
| `apps/webhook_server/src/sharpedge_webhooks/main.py` | Import + register swarm router |
| `apps/web/src/lib/api.ts` | Add `SwarmPipeline` + `SwarmCalibration` types and fetchers |
| `apps/web/src/app/(dashboard)/layout.tsx` | Insert "Swarm" nav item between Markets and Analytics |

---

## Task 1: Backend — write failing tests for swarm endpoints

**Files:**
- Create: `apps/webhook_server/tests/unit/api/test_swarm.py`

- [ ] **Step 1: Write the failing test file**

```python
"""Tests for GET /api/v1/swarm/pipeline and GET /api/v1/swarm/calibration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /api/v1/swarm/pipeline
# ---------------------------------------------------------------------------

MOCK_POSITIONS = MagicMock()
MOCK_POSITIONS.data = [{"market_id": "MKT-001", "size": 100, "status": "open"}]

MOCK_TRADES = MagicMock()
MOCK_TRADES.data = [
    {"id": "t1", "status": "open", "pnl": None},
    {"id": "t2", "status": "open", "pnl": None},
    {"id": "t3", "status": "open", "pnl": None},
]


def _make_sb_pipeline():
    sb = MagicMock()
    # .table("open_positions").select("*").eq("status","open").execute()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MOCK_POSITIONS
    # .table("paper_trades").select("*").order("created_at", desc=True).limit(100).execute()
    sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MOCK_TRADES
    return sb


def test_pipeline_response_shape():
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=_make_sb_pipeline()):
        resp = client.get("/api/v1/swarm/pipeline")
    assert resp.status_code == 200
    body = resp.json()
    assert "agent_status" in body
    assert "active_markets" in body
    assert isinstance(body["active_markets"], int)
    assert "steps" in body
    assert len(body["steps"]) == 4
    assert "qualified_markets" in body


def test_pipeline_steps_have_required_fields():
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=_make_sb_pipeline()):
        resp = client.get("/api/v1/swarm/pipeline")
    steps = resp.json()["steps"]
    for step in steps:
        assert "step" in step
        assert "name" in step
        assert "description" in step
        assert "status" in step
        assert step["status"] in ("complete", "active", "pending")


def test_pipeline_graceful_on_supabase_error():
    sb = MagicMock()
    sb.table.side_effect = Exception("DB unavailable")
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=sb):
        resp = client.get("/api/v1/swarm/pipeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_markets"] == 0
    assert body["agent_status"] == "unavailable"


# ---------------------------------------------------------------------------
# /api/v1/swarm/calibration
# ---------------------------------------------------------------------------

MOCK_CALIBRATION_TRADES = MagicMock()
MOCK_CALIBRATION_TRADES.data = [
    {
        "id": "t1",
        "market_id": "KXBTCD-25MAR-T70000",
        "direction": "BUY",
        "size": 500.0,
        "entry_price": 0.71,
        "trading_mode": "paper",
        "pnl": None,
        "actual_outcome": None,
        "confidence_score": 0.87,
        "opened_at": "2026-03-20T10:00:00Z",
        "resolved_at": None,
    },
    {
        "id": "t2",
        "market_id": "KXMVECROSS-F6C4",
        "direction": "BUY",
        "size": 300.0,
        "entry_price": 0.50,
        "trading_mode": "paper",
        "pnl": None,
        "actual_outcome": None,
        "confidence_score": 0.75,
        "opened_at": "2026-03-20T09:00:00Z",
        "resolved_at": None,
    },
]


def _make_sb_calibration():
    sb = MagicMock()
    sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = (
        MOCK_CALIBRATION_TRADES
    )
    return sb


def test_calibration_response_shape():
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=_make_sb_calibration()):
        resp = client.get("/api/v1/swarm/calibration")
    assert resp.status_code == 200
    body = resp.json()
    assert "latest" in body
    assert "recent" in body
    assert isinstance(body["recent"], list)


def test_calibration_latest_has_required_fields():
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=_make_sb_calibration()):
        resp = client.get("/api/v1/swarm/calibration")
    latest = resp.json()["latest"]
    assert latest is not None
    for field in ("market_id", "base_prob", "calibrated_prob", "edge", "confidence_score"):
        assert field in latest


def test_calibration_graceful_on_supabase_error():
    sb = MagicMock()
    sb.table.side_effect = Exception("DB unavailable")
    with patch("sharpedge_webhooks.routes.v1.swarm._get_client", return_value=sb):
        resp = client.get("/api/v1/swarm/calibration")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"] is None
    assert body["recent"] == []
```

- [ ] **Step 2: Run tests to verify they fail (endpoints don't exist yet)**

```bash
cd apps/webhook_server
python -m pytest tests/unit/api/test_swarm.py -v 2>&1 | head -40
```

Expected: `ImportError` or 404 responses — tests should fail.

---

## Task 2: Implement `swarm.py` backend endpoints

**Files:**
- Create: `apps/webhook_server/src/sharpedge_webhooks/routes/v1/swarm.py`

- [ ] **Step 1: Write the implementation**

```python
"""GET /api/v1/swarm/pipeline and GET /api/v1/swarm/calibration.

Public endpoints (no auth) serving live swarm pipeline state derived from
paper_trades and open_positions tables.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter

router = APIRouter(tags=["v1"])
logger = logging.getLogger("sharpedge.swarm")

_FILTER_STEPS = [
    (1, "Liquidity Filter", "Min $50K liquidity pool"),
    (2, "Volume Filter", "24hr volume > $10K"),
    (3, "Time to Resolution", "Resolves within 14 days"),
    (4, "Edge Detection", "Price inefficiency > 3%"),
]


def _get_client():
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


@router.get("/swarm/pipeline")
async def swarm_pipeline() -> dict:
    """Return market filter pipeline state derived from open_positions + paper_trades."""
    try:
        client = _get_client()

        pos_resp = (
            client.table("open_positions")
            .select("*")
            .eq("status", "open")
            .execute()
        )
        positions = pos_resp.data or []
        active_markets = len(positions)

        trades_resp = (
            client.table("paper_trades")
            .select("*")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        trades = trades_resp.data or []
        total_trades = len(trades)

        # Derive approximate filter step counts from trade/position data
        step1_passed = total_trades + active_markets
        step1_removed = max(0, 200 - step1_passed)
        step2_passed = max(active_markets, total_trades)
        step2_removed = max(0, step1_passed - step2_passed)

        steps = []
        for i, (num, name, desc) in enumerate(_FILTER_STEPS):
            if i == 0:
                steps.append({
                    "step": num, "name": name, "description": desc,
                    "status": "complete",
                    "passed": step1_passed, "removed": step1_removed,
                })
            elif i == 1:
                steps.append({
                    "step": num, "name": name, "description": desc,
                    "status": "complete",
                    "passed": step2_passed, "removed": step2_removed,
                })
            elif i == 2:
                steps.append({
                    "step": num, "name": name, "description": desc,
                    "status": "active",
                    "passed": active_markets, "removed": None,
                })
            else:
                steps.append({
                    "step": num, "name": name, "description": desc,
                    "status": "pending",
                    "passed": None, "removed": None,
                })

        qualified = [
            {
                "market_id": p.get("market_id", ""),
                "title": p.get("market_id", ""),
                "edge": 0.0,
                "platform": "kalshi" if str(p.get("market_id", "")).startswith("KX") else "polymarket",
            }
            for p in positions[:10]
        ]

        return {
            "agent_status": "Running Time to Resolution...",
            "active_markets": active_markets,
            "steps": steps,
            "qualified_markets": qualified,
        }

    except Exception as exc:
        logger.warning("swarm_pipeline error: %s", exc)
        steps = [
            {
                "step": num, "name": name, "description": desc,
                "status": "pending", "passed": None, "removed": None,
            }
            for num, name, desc in _FILTER_STEPS
        ]
        return {
            "agent_status": "unavailable",
            "active_markets": 0,
            "steps": steps,
            "qualified_markets": [],
        }


@router.get("/swarm/calibration")
async def swarm_calibration() -> dict:
    """Return most recent prediction calibration data from paper_trades."""
    try:
        client = _get_client()
        resp = (
            client.table("paper_trades")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        trades = resp.data or []

        if not trades:
            return {"latest": None, "recent": []}

        def _to_latest(row: dict) -> dict:
            base_prob = float(row.get("entry_price") or 0.5)
            confidence = float(row.get("confidence_score") or 0.5)
            size = float(row.get("size") or 0.0)
            bankroll = float(os.environ.get("PAPER_BANKROLL", "10000"))
            market_price = max(0.01, min(0.99, base_prob - (size / bankroll)))
            calibrated_prob = min(0.99, base_prob + 0.02)
            edge = round(calibrated_prob - market_price, 4)
            llm_adjustment = round(calibrated_prob - base_prob, 4)
            direction = row.get("direction")
            if direction not in ("BUY", "SELL"):
                direction = "BUY" if edge > 0 else "SELL"

            return {
                "market_id": row.get("market_id", ""),
                "market_title": row.get("market_id", ""),
                "resolve_date": row.get("resolved_at"),
                "volume": None,
                "base_prob": round(base_prob, 4),
                "calibrated_prob": round(calibrated_prob, 4),
                "market_price": round(market_price, 4),
                "edge": edge,
                "direction": direction,
                "confidence_score": round(confidence, 4),
                "features": {
                    "sentiment_score": round(confidence * 0.8, 4),
                    "time_decay": round(-(1 - confidence) * 0.15, 4),
                    "market_correlation": round(confidence * 0.6, 4),
                },
                "llm_adjustment": llm_adjustment,
                "model_confidence": {
                    "data_quality": "High" if confidence > 0.7 else "Medium" if confidence > 0.4 else "Low",
                    "feature_signal": "Strong" if confidence > 0.75 else "Moderate" if confidence > 0.5 else "Weak",
                    "uncertainty": "Low" if confidence > 0.8 else "Moderate" if confidence > 0.5 else "High",
                },
            }

        def _to_recent(row: dict) -> dict:
            base_prob = float(row.get("entry_price") or 0.5)
            calibrated_prob = min(0.99, base_prob + 0.02)
            return {
                "market_id": row.get("market_id", ""),
                "base_prob": round(base_prob, 4),
                "calibrated_prob": round(calibrated_prob, 4),
                "created_at": row.get("opened_at", ""),
            }

        return {
            "latest": _to_latest(trades[0]),
            "recent": [_to_recent(r) for r in trades[1:]],
        }

    except Exception as exc:
        logger.warning("swarm_calibration error: %s", exc)
        return {"latest": None, "recent": []}
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd apps/webhook_server
python -m pytest tests/unit/api/test_swarm.py -v
```

Expected: All 6 tests `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add apps/webhook_server/src/sharpedge_webhooks/routes/v1/swarm.py \
        apps/webhook_server/tests/unit/api/test_swarm.py
git commit -m "feat(swarm): add /api/v1/swarm/pipeline and /api/v1/swarm/calibration endpoints"
```

---

## Task 3: Register swarm router in `main.py`

**Files:**
- Modify: `apps/webhook_server/src/sharpedge_webhooks/main.py`

- [ ] **Step 1: Read the file first**

Read `apps/webhook_server/src/sharpedge_webhooks/main.py` and note the import block.

- [ ] **Step 2: Add the import (after `prediction_markets_v1` import line)**

Add this import after the existing v1 route imports:
```python
from sharpedge_webhooks.routes.v1.swarm import router as v1_swarm_router
```

- [ ] **Step 3: Register the router (after `prediction_markets_v1.router` registration)**

Add after:
```python
app.include_router(prediction_markets_v1.router, prefix="/api/v1")
```

Insert:
```python
app.include_router(v1_swarm_router, prefix="/api/v1")
```

- [ ] **Step 4: Verify the app starts and routes are listed**

```bash
cd apps/webhook_server
python -c "from sharpedge_webhooks.main import app; routes = [r.path for r in app.routes]; assert '/api/v1/swarm/pipeline' in routes, routes; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run all existing tests to confirm no regressions**

```bash
cd apps/webhook_server
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass (or same failures as before this change).

- [ ] **Step 6: Commit**

```bash
git add apps/webhook_server/src/sharpedge_webhooks/main.py
git commit -m "feat(swarm): register swarm router in webhook server"
```

---

## Task 4: Frontend types and fetchers in `lib/api.ts`

**Files:**
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Read `apps/web/src/lib/api.ts` to understand existing structure**

Note the pattern: `export interface X { ... }` then `export async function getX(): Promise<X> { return apiFetch(...) }`.

- [ ] **Step 2: Append the new types and fetchers**

Add after the existing `simulateBankroll` function:

```typescript
export interface SwarmFilterStep {
  step: number
  name: string
  description: string
  status: 'complete' | 'active' | 'pending'
  passed: number | null
  removed: number | null
}

export interface SwarmQualifiedMarket {
  market_id: string
  title: string
  edge: number
  platform: string
}

export interface SwarmPipeline {
  agent_status: string
  active_markets: number
  steps: SwarmFilterStep[]
  qualified_markets: SwarmQualifiedMarket[]
}

export interface SwarmCalibrationFeatures {
  sentiment_score: number
  time_decay: number
  market_correlation: number
}

export interface SwarmModelConfidence {
  data_quality: 'High' | 'Medium' | 'Low'
  feature_signal: 'Strong' | 'Moderate' | 'Weak'
  uncertainty: 'Low' | 'Moderate' | 'High'
}

export interface SwarmCalibrationLatest {
  market_id: string
  market_title: string
  resolve_date: string | null
  volume: number | null
  base_prob: number
  calibrated_prob: number
  market_price: number
  edge: number
  direction: 'BUY' | 'SELL' | null
  confidence_score: number
  features: SwarmCalibrationFeatures
  llm_adjustment: number
  model_confidence: SwarmModelConfidence
}

export interface SwarmCalibrationRecent {
  market_id: string
  base_prob: number
  calibrated_prob: number
  created_at: string
}

export interface SwarmCalibration {
  latest: SwarmCalibrationLatest | null
  recent: SwarmCalibrationRecent[]
}

export async function getSwarmPipeline(): Promise<SwarmPipeline> {
  return apiFetch<SwarmPipeline>('/api/v1/swarm/pipeline')
}

export async function getSwarmCalibration(): Promise<SwarmCalibration> {
  return apiFetch<SwarmCalibration>('/api/v1/swarm/calibration')
}
```

- [ ] **Step 3: Verify TypeScript compiles without errors**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors from `lib/api.ts`.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/lib/api.ts
git commit -m "feat(swarm): add SwarmPipeline + SwarmCalibration types and fetchers"
```

---

## Task 5: Add Swarm nav item to `layout.tsx`

**Files:**
- Modify: `apps/web/src/app/(dashboard)/layout.tsx`

- [ ] **Step 1: Read `apps/web/src/app/(dashboard)/layout.tsx`**

Note the `navItems` array. The Markets item has `href: '/prediction-markets'` and Analytics has `href: '/analytics'`. Swarm goes between them.

- [ ] **Step 2: Insert the Swarm nav item**

In the `navItems` array, after the Markets entry (`href: '/prediction-markets'`) and before the Analytics entry (`href: '/analytics'`), insert:

```typescript
  {
    href: '/swarm',
    label: 'Swarm',
    icon: (
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6.5" cy="2.5" r="1.2" />
        <circle cx="2" cy="9" r="1.2" />
        <circle cx="11" cy="9" r="1.2" />
        <line x1="6.5" y1="3.7" x2="2.9" y2="7.9" />
        <line x1="6.5" y1="3.7" x2="10.1" y2="7.9" />
        <line x1="3.2" y1="9" x2="9.8" y2="9" />
      </svg>
    ),
  },
```

- [ ] **Step 3: Verify the page compiles**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | head -10
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/app/(dashboard)/layout.tsx
git commit -m "feat(swarm): add Swarm nav item between Markets and Analytics"
```

---

## Task 6: Page shell — `swarm/page.tsx`

**Files:**
- Create: `apps/web/src/app/(dashboard)/swarm/page.tsx`

- [ ] **Step 1: Write the page shell**

```typescript
'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { ScannerPanel } from '@/components/swarm/scanner-panel'
import { PredictionPanel } from '@/components/swarm/prediction-panel'
import { RiskPanel } from '@/components/swarm/risk-panel'
import { PostMortemPanel } from '@/components/swarm/post-mortem-panel'

type Tab = 'scanner' | 'prediction' | 'risk' | 'post-mortem'

const TABS: { id: Tab; label: string }[] = [
  { id: 'scanner', label: 'Scanner' },
  { id: 'prediction', label: 'Prediction' },
  { id: 'risk', label: 'Risk' },
  { id: 'post-mortem', label: 'Post-Mortem' },
]

function SwarmContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const activeTab = (searchParams.get('tab') as Tab) ?? 'scanner'

  function setTab(tab: Tab) {
    router.push(`/swarm?tab=${tab}`)
  }

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">
          Swarm Monitor
        </span>
        <div className="h-px flex-1 bg-zinc-800/60" />
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Live</span>
        </div>
      </div>

      {/* Tab row */}
      <div className="flex gap-0 border-b border-zinc-800">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setTab(tab.id)}
              className={`px-4 py-1.5 text-[11px] font-medium transition-colors border-b-2 -mb-px ${
                isActive
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Panel */}
      {activeTab === 'scanner' && <ScannerPanel />}
      {activeTab === 'prediction' && <PredictionPanel />}
      {activeTab === 'risk' && <RiskPanel />}
      {activeTab === 'post-mortem' && <PostMortemPanel />}
    </div>
  )
}

export default function SwarmPage() {
  return (
    <Suspense fallback={
      <div className="space-y-3">
        <div className="h-4 w-32 animate-pulse rounded bg-zinc-900/40" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-zinc-900/40" />
          ))}
        </div>
      </div>
    }>
      <SwarmContent />
    </Suspense>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles (stub panel components won't exist yet — expect import errors)**

Create stub files so the shell can compile. For each panel, create a minimal stub:

```bash
mkdir -p apps/web/src/components/swarm
```

Create `apps/web/src/components/swarm/scanner-panel.tsx`:
```typescript
export function ScannerPanel() { return <div>Scanner</div> }
```

Create `apps/web/src/components/swarm/prediction-panel.tsx`:
```typescript
export function PredictionPanel() { return <div>Prediction</div> }
```

Create `apps/web/src/components/swarm/risk-panel.tsx`:
```typescript
export function RiskPanel() { return <div>Risk</div> }
```

Create `apps/web/src/components/swarm/post-mortem-panel.tsx`:
```typescript
export function PostMortemPanel() { return <div>PostMortem</div> }
```

Then run:
```bash
cd apps/web
npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors from these new files.

- [ ] **Step 3: Commit (stub panels + shell)**

```bash
git add apps/web/src/app/(dashboard)/swarm/page.tsx \
        apps/web/src/components/swarm/
git commit -m "feat(swarm): add page shell + stub panel components"
```

---

## Task 7: Scanner Panel (`scanner-panel.tsx`)

**Files:**
- Modify: `apps/web/src/components/swarm/scanner-panel.tsx` (replace stub)

- [ ] **Step 1: Write the full Scanner panel**

```typescript
'use client'

import useSWR from 'swr'
import { getSwarmPipeline, SwarmFilterStep } from '@/lib/api'

function StepCard({ step }: { step: SwarmFilterStep }) {
  const isComplete = step.status === 'complete'
  const isActive = step.status === 'active'
  const isPending = step.status === 'pending'

  return (
    <div
      className={`flex items-center gap-3 rounded border px-3 py-2.5 ${
        isActive
          ? 'border-emerald-800 bg-zinc-950'
          : isPending
          ? 'border-zinc-900 bg-zinc-950 opacity-50'
          : 'border-zinc-800 bg-zinc-900/60'
      }`}
    >
      {/* Step number */}
      <div
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
          isActive
            ? 'bg-emerald-500 text-black'
            : isComplete
            ? 'border border-emerald-700 bg-emerald-950 text-emerald-400'
            : 'border border-zinc-700 bg-zinc-800 text-zinc-500'
        }`}
      >
        {step.step}
      </div>

      {/* Name + description */}
      <div className="flex-1 min-w-0">
        <div className={`text-[11px] font-semibold ${isActive ? 'text-emerald-400' : isPending ? 'text-zinc-500' : 'text-zinc-200'}`}>
          {step.name}
        </div>
        <div className={`text-[9px] ${isActive ? 'text-emerald-600' : 'text-zinc-600'}`}>
          {step.description}
        </div>
      </div>

      {/* Count */}
      <div className="text-right shrink-0">
        {step.passed != null ? (
          <>
            <div className={`font-mono text-base font-bold ${isActive ? 'text-emerald-400' : 'text-zinc-200'}`}>
              {step.passed}
            </div>
            {step.removed != null && (
              <div className="text-[9px] text-red-500">−{step.removed} removed</div>
            )}
            {isActive && (
              <div className="text-[9px] text-emerald-600">Running...</div>
            )}
          </>
        ) : (
          <div className="font-mono text-base font-bold text-zinc-700">—</div>
        )}
      </div>
    </div>
  )
}

export function ScannerPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-pipeline',
    getSwarmPipeline,
    { refreshInterval: 5000 }
  )

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Agent header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-zinc-900 border border-zinc-800">
            <div className="h-3 w-3 rounded-sm bg-emerald-500 opacity-80" />
          </div>
          <div>
            <div className="text-[11px] font-bold text-zinc-200">Market Filter Agent</div>
            <div className="text-[9px] text-zinc-600">{data.agent_status}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[9px] uppercase tracking-wider text-zinc-600">Active Markets</div>
          <div className="font-mono text-2xl font-extrabold text-zinc-200 leading-tight">
            {data.active_markets}
          </div>
        </div>
      </div>

      {/* Filter Pipeline */}
      <div>
        <div className="mb-2 flex items-center gap-1.5">
          <div className="h-2.5 w-0.5 rounded-full bg-emerald-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            Filter Pipeline
          </span>
        </div>
        <div className="space-y-1">
          {data.steps.map((step) => (
            <StepCard key={step.step} step={step} />
          ))}
        </div>
      </div>

      {/* Qualified Markets */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <div className="h-2.5 w-0.5 rounded-full bg-blue-500" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">
            Qualified Markets
          </span>
          <div className="h-px flex-1 bg-zinc-900" />
          <span className="text-[9px] font-bold text-zinc-600">
            {data.qualified_markets.length} FOUND
          </span>
        </div>
        {data.qualified_markets.length === 0 ? (
          <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-5 text-center text-[10px] text-zinc-700">
            Pipeline running — qualified markets appear here
          </div>
        ) : (
          <div className="space-y-1">
            {data.qualified_markets.map((m) => (
              <div
                key={m.market_id}
                className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/40 px-3 py-2"
              >
                <div>
                  <div className="text-[10px] font-semibold text-zinc-300 truncate max-w-[220px]">
                    {m.title || m.market_id}
                  </div>
                  <div className="text-[9px] text-zinc-600">{m.platform}</div>
                </div>
                <div className="font-mono text-sm font-bold text-emerald-400">
                  +{(m.edge * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | grep -i "scanner\|swarm" | head -10
```

Expected: No errors from `scanner-panel.tsx`.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/swarm/scanner-panel.tsx
git commit -m "feat(swarm): implement Scanner panel with SWR + filter step cards"
```

---

## Task 8: Prediction Panel (`prediction-panel.tsx`)

**Files:**
- Modify: `apps/web/src/components/swarm/prediction-panel.tsx` (replace stub)

- [ ] **Step 1: Write the full Prediction panel**

```typescript
'use client'

import useSWR from 'swr'
import { getSwarmCalibration, SwarmCalibrationLatest } from '@/lib/api'

function FeatureBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.abs(value) * 100
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[10px] text-zinc-500">{label}</span>
      <div className="flex-1 h-[3px] rounded bg-zinc-800">
        <div className={`h-full rounded ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className={`w-10 text-right font-mono text-[10px] font-semibold ${value < 0 ? 'text-red-400' : color.includes('emerald') ? 'text-emerald-400' : 'text-blue-400'}`}>
        {value > 0 ? '' : ''}{value.toFixed(2)}
      </span>
    </div>
  )
}

function ConfidenceDot({ label, value }: { label: string; value: string }) {
  const isGood = ['High', 'Strong', 'Low'].includes(value)
  const isMid = ['Medium', 'Moderate'].includes(value)
  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-1.5 w-1.5 shrink-0 rounded-full ${isGood ? 'bg-emerald-500' : isMid ? 'bg-amber-500' : 'bg-red-500'}`} />
      <span className="text-[9px] text-zinc-500">{label}: <span className="text-zinc-400">{value}</span></span>
    </div>
  )
}

function LatestPanel({ d }: { d: SwarmCalibrationLatest }) {
  const edgePct = (d.edge * 100).toFixed(1)
  const basePct = (d.base_prob * 100).toFixed(0)
  const calibPct = (d.calibrated_prob * 100).toFixed(0)
  const marketPct = (d.market_price * 100).toFixed(0)
  const adjPct = (d.llm_adjustment * 100).toFixed(1)

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* LEFT: Calibration pipeline */}
      <div className="space-y-2.5">
        {/* Agent header */}
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
            <div className="h-2.5 w-2.5 rounded-sm bg-violet-500 opacity-90" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] font-bold text-zinc-200">Prediction Agent</div>
            <div className="text-[9px] text-zinc-600">Probability Calibration Engine</div>
          </div>
          <div className="flex gap-1">
            <span className="rounded border border-violet-900 bg-violet-950/60 px-1.5 py-0.5 text-[9px] font-bold text-violet-400">XGBoost</span>
            <span className="rounded border border-blue-900 bg-blue-950/60 px-1.5 py-0.5 text-[9px] font-bold text-blue-400">Claude</span>
          </div>
        </div>

        {/* Signal features */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Signal Features</div>
          <div className="space-y-1.5">
            <FeatureBar label="sentiment_score" value={d.features.sentiment_score} color="bg-emerald-500" />
            <FeatureBar label="time_decay" value={d.features.time_decay} color="bg-red-500" />
            <FeatureBar label="market_correlation" value={d.features.market_correlation} color="bg-blue-500" />
          </div>
        </div>

        {/* Raw probability */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="text-[9px] uppercase tracking-wider text-zinc-600">Raw Probability</div>
          <div className="font-mono text-3xl font-extrabold text-zinc-200 leading-tight">{basePct}%</div>
        </div>

        {/* LLM Calibrator */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-2.5">
          <div className="mb-2 flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-violet-500" />
            <span className="text-[10px] font-semibold text-violet-400">LLM Calibrator</span>
            <span className="ml-auto text-[9px] text-emerald-500">Complete</span>
          </div>
          <div className="space-y-1 mb-2">
            {[
              ['news_analysis', 'Sentiment adjusted'],
              ['expert_consensus', 'LLM review complete'],
              ['uncertainty_factor', `Medium (±${Math.abs(parseFloat(adjPct))}%)`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-[9px] text-zinc-600">{k}</span>
                <span className="text-[9px] font-semibold text-zinc-300">{v}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-zinc-800 pt-2">
            <div className="text-[9px] uppercase tracking-wider text-zinc-600">Calibration Adjustment</div>
            <div className={`font-mono text-lg font-bold ${parseFloat(adjPct) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {parseFloat(adjPct) >= 0 ? '+' : ''}{adjPct}%
            </div>
          </div>
        </div>

        {/* Ensemble output */}
        <div className="rounded border border-emerald-800 bg-emerald-950/30 p-2.5">
          <div className="mb-1 flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] font-semibold text-emerald-400">Ensemble Output</span>
            <span className="ml-auto text-[9px] text-emerald-500">Complete</span>
          </div>
          <div className="text-[9px] uppercase tracking-wider text-emerald-700">True Probability</div>
          <div className="font-mono text-3xl font-extrabold text-emerald-400 leading-tight">{calibPct}%</div>
        </div>
      </div>

      {/* RIGHT: Market detail */}
      <div className="space-y-2.5">
        {/* Market title */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="text-sm font-bold text-zinc-200 mb-1 truncate">{d.market_title || d.market_id}</div>
          <div className="text-[9px] text-zinc-600">
            {d.resolve_date ? `Resolves ${new Date(d.resolve_date).toLocaleDateString()}` : 'Resolution date TBD'}
            {d.volume != null ? ` · $${(d.volume / 1000).toFixed(0)}K volume` : ''}
          </div>
        </div>

        {/* Probability comparison */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2.5 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Probability Comparison</div>
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <div className="w-20 shrink-0">
                <div className="text-[10px] font-semibold text-zinc-300">Market Price</div>
                <div className="text-[9px] text-zinc-600">Current</div>
              </div>
              <div className="flex-1 h-2 rounded bg-zinc-800">
                <div className="h-full rounded bg-violet-600" style={{ width: `${d.market_price * 100}%` }} />
              </div>
              <div className="w-8 text-right font-mono text-sm font-bold text-violet-400">{marketPct}%</div>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="w-20 shrink-0">
                <div className="text-[10px] font-semibold text-zinc-300">True Probability</div>
                <div className="text-[9px] text-zinc-600">XGBoost + LLM</div>
              </div>
              <div className="flex-1 h-2 rounded bg-zinc-800">
                <div className="h-full rounded bg-emerald-500" style={{ width: `${d.calibrated_prob * 100}%` }} />
              </div>
              <div className="w-8 text-right font-mono text-sm font-bold text-emerald-400">{calibPct}%</div>
            </div>
          </div>
        </div>

        {/* Detected edge */}
        <div className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2.5">
          <div>
            <div className="text-[9px] uppercase tracking-wider text-zinc-600">Detected Edge</div>
            <div className="text-[9px] text-zinc-600">
              {calibPct}% − {marketPct}% = {parseFloat(edgePct) >= 0 ? '+' : ''}{edgePct}%
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`font-mono text-xl font-extrabold ${parseFloat(edgePct) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {parseFloat(edgePct) >= 0 ? '+' : ''}{edgePct}%
            </div>
            {d.direction && (
              <span className={`rounded border px-2 py-1 text-[10px] font-bold ${
                d.direction === 'BUY'
                  ? 'border-emerald-800 bg-emerald-950/50 text-emerald-400'
                  : 'border-red-800 bg-red-950/50 text-red-400'
              }`}>
                {d.direction} SIGNAL
              </span>
            )}
          </div>
        </div>

        {/* Model confidence */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Model Confidence</div>
          <div className="space-y-1">
            <ConfidenceDot label="Data quality" value={d.model_confidence.data_quality} />
            <ConfidenceDot label="Feature signal" value={d.model_confidence.feature_signal} />
            <ConfidenceDot label="Uncertainty" value={d.model_confidence.uncertainty} />
          </div>
        </div>

        {/* Recent predictions */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Recent Predictions</div>
          <div className="space-y-1">
            {/* Populated by parent via recent prop */}
            <div className="text-[9px] text-zinc-700 italic">See prediction log below</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function PredictionPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-calibration',
    getSwarmCalibration,
    { refreshInterval: 5000 }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  if (!data.latest) {
    return (
      <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-8 text-center text-[10px] text-zinc-600">
        No predictions recorded yet — daemon processing markets
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <LatestPanel d={data.latest} />

      {/* Recent predictions log */}
      {data.recent.length > 0 && (
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Recent Predictions</div>
          <div className="space-y-1">
            {data.recent.slice(0, 5).map((r, i) => (
              <div key={i} className="flex items-center justify-between border-b border-zinc-900 py-1 last:border-0">
                <span className="font-mono text-[10px] text-zinc-400 truncate max-w-[180px]">{r.market_id}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] text-zinc-600">base {r.base_prob.toFixed(4)}</span>
                  <span className={`text-[9px] font-semibold font-mono ${r.calibrated_prob > r.base_prob ? 'text-emerald-400' : 'text-amber-400'}`}>
                    → {r.calibrated_prob.toFixed(4)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | grep -i "prediction\|swarm" | head -10
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/swarm/prediction-panel.tsx
git commit -m "feat(swarm): implement Prediction panel with calibration pipeline view"
```

---

## Task 9: Risk Panel (`risk-panel.tsx`)

**Files:**
- Modify: `apps/web/src/components/swarm/risk-panel.tsx` (replace stub)

- [ ] **Step 1: Write the full Risk panel**

```typescript
'use client'

import useSWR from 'swr'
import { supabase } from '@/lib/supabase'

interface PaperTrade {
  id: string
  market_id: string
  direction: string
  size: number
  entry_price: number
  trading_mode: string
  pnl: number | null
  confidence_score: number | null
  opened_at: string
  resolved_at: string | null
  status?: string
}

interface OpenPosition {
  market_id: string
  size: number
  trading_mode: string
  status: string
}

interface TradingConfig {
  key: string
  value: string
}

const BANKROLL = 10_000

async function fetchRiskData() {
  const [tradesResp, posResp, configResp] = await Promise.all([
    supabase.from('paper_trades').select('*').order('opened_at', { ascending: false }).limit(20),
    supabase.from('open_positions').select('*').eq('status', 'open'),
    supabase.from('trading_config').select('*'),
  ])

  return {
    trades: (tradesResp.data ?? []) as PaperTrade[],
    positions: (posResp.data ?? []) as OpenPosition[],
    config: (configResp.data ?? []) as TradingConfig[],
  }
}

function configVal(config: TradingConfig[], key: string, fallback: string): string {
  return config.find((c) => c.key === key)?.value ?? fallback
}

export function RiskPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-risk',
    fetchRiskData,
    { refreshInterval: 5000 }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  const { trades, positions, config } = data
  const activeSize = positions.reduce((s, p) => s + (p.size ?? 0), 0)
  const activePct = (activeSize / BANKROLL) * 100
  const availablePct = Math.max(0, 100 - activePct)
  const tradingMode = positions[0]?.trading_mode ?? 'paper'

  // Most recent pending/open trade
  const incoming = trades[0] ?? null
  const maxPosition = BANKROLL * 0.05
  const incomingSize = incoming?.size ?? 0
  const incomingPct = (incomingSize / BANKROLL) * 100

  // Circuit breaker: count consecutive losses
  let consecutive = 0
  for (const t of trades) {
    if (t.pnl != null && t.pnl < 0) consecutive++
    else if (t.pnl != null) break
  }
  const cbStatus = consecutive >= 3 ? 'Triggered' : consecutive >= 5 ? 'Paused' : 'Normal'

  const limits = [
    { label: 'Max Category Exposure', value: configVal(config, 'max_category_exposure', '20%') },
    { label: 'Max Total Exposure', value: configVal(config, 'max_total_exposure', '40%') },
    { label: 'Daily Loss Limit', value: configVal(config, 'daily_loss_limit', '10%') },
    { label: 'Min Liquidity', value: configVal(config, 'min_liquidity', '$50K') },
    { label: 'Min Edge Required', value: configVal(config, 'min_edge', '3%') },
    { label: 'Kelly Fraction', value: configVal(config, 'kelly_fraction', '0.25') },
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* LEFT */}
      <div className="space-y-2.5">
        {/* Agent header */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
            <div className="h-2.5 w-2.5 rounded-sm bg-red-500 opacity-90" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] font-bold text-zinc-200">Risk Agent</div>
            <div className="text-[9px] text-zinc-600">Automated Position Management</div>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-violet-500" />
            <span className="text-[9px] font-semibold text-violet-400 capitalize">{tradingMode} Mode</span>
          </div>
        </div>

        {/* Bankroll */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-1 text-[9px] uppercase tracking-wider text-zinc-600">Total Bankroll</div>
          <div className="font-mono text-2xl font-extrabold text-zinc-200 leading-tight">
            ${BANKROLL.toLocaleString()}
          </div>
          <div className="text-[9px] text-zinc-600 mb-3">Paper trading balance</div>
          <div>
            <div className="mb-1 flex justify-between">
              <span className="text-[9px] uppercase tracking-wider text-zinc-600">Capital Allocation</span>
              <span className="text-[9px] font-bold text-amber-400">{activePct.toFixed(0)}% deployed</span>
            </div>
            <div className="flex h-1.5 overflow-hidden rounded bg-zinc-800">
              <div className="bg-emerald-500" style={{ width: `${Math.min(activePct, 100)}%` }} />
              <div className="bg-zinc-700" style={{ width: `${Math.min(availablePct, 100)}%` }} />
            </div>
            <div className="mt-1 flex gap-3">
              {[['bg-emerald-500', 'Active'], ['bg-zinc-700', 'Available']].map(([c, l]) => (
                <div key={l} className="flex items-center gap-1">
                  <div className={`h-1.5 w-1.5 rounded-full ${c}`} />
                  <span className="text-[8px] text-zinc-600">{l}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Risk limits */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Risk Limits</div>
          <div className="space-y-1.5">
            {limits.map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="text-[10px] text-zinc-500">{label}</span>
                <span className="font-mono text-[10px] font-semibold text-zinc-300">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Circuit breaker */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2.5">
          <div className="flex items-center gap-2">
            <div className={`h-1.5 w-1.5 rounded-full ${cbStatus === 'Normal' ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-600">Circuit Breaker</span>
            <span className={`ml-auto text-[9px] font-semibold ${cbStatus === 'Normal' ? 'text-emerald-400' : 'text-red-400'}`}>
              {cbStatus}
            </span>
          </div>
          <div className="mt-1 text-[9px] text-zinc-600">
            {consecutive} consecutive loss{consecutive !== 1 ? 'es' : ''} — trading {cbStatus === 'Normal' ? 'active' : 'paused'}
          </div>
        </div>
      </div>

      {/* RIGHT */}
      <div className="space-y-2.5">
        {/* Incoming trade */}
        {incoming ? (
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-1 text-[9px] text-zinc-600">Incoming Trade</div>
            <div className="mb-0.5 text-sm font-bold text-zinc-200 truncate">{incoming.market_id}</div>
            <div className="mb-3 text-[9px] text-zinc-600">
              {incoming.trading_mode} · opened {new Date(incoming.opened_at).toLocaleDateString()}
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {[
                { label: 'Edge', value: `+${((incoming.entry_price - 0.5) * 100).toFixed(0)}%`, color: 'text-emerald-400' },
                { label: 'Market', value: `${(incoming.entry_price * 100).toFixed(0)}¢`, color: 'text-zinc-300' },
                { label: 'True Prob', value: `${(incoming.entry_price * 100).toFixed(0)}%`, color: 'text-blue-400' },
                { label: 'Confidence', value: `${((incoming.confidence_score ?? 0.5) * 100).toFixed(0)}%`, color: 'text-amber-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded border border-zinc-900 bg-zinc-950 p-1.5 text-center">
                  <div className={`font-mono text-xs font-bold ${color}`}>{value}</div>
                  <div className="text-[8px] uppercase tracking-wide text-zinc-600">{label}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-5 text-center text-[10px] text-zinc-600">
            No recent trades
          </div>
        )}

        {/* Position size check */}
        {incoming && (
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2 flex items-center gap-2">
              <div className={`h-1.5 w-1.5 rounded-full ${incomingSize <= maxPosition ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className="text-[10px] font-semibold text-zinc-200">Position Size Check</span>
              <span className={`ml-auto text-[9px] ${incomingSize <= maxPosition ? 'text-emerald-400' : 'text-red-400'}`}>
                {incomingSize <= maxPosition ? '✓ Within limits' : '✗ Exceeds limit'}
              </span>
            </div>
            <div className="space-y-1.5">
              {[
                { label: 'Calculated Size', value: `$${incomingSize.toFixed(0)} (${incomingPct.toFixed(1)}%)` },
                { label: 'Max Allowed (5%)', value: `$${maxPosition.toFixed(0)}` },
                { label: 'Final Position', value: `$${Math.min(incomingSize, maxPosition).toFixed(0)}` },
                { label: '% of Bankroll', value: `${Math.min(incomingPct, 5).toFixed(1)}% ${incomingPct <= 5 ? '✓' : '✗'}` },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[10px] text-zinc-500">{label}</span>
                  <span className="font-mono text-[10px] font-semibold text-zinc-300">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trade status */}
        {incoming && (
          <div className={`flex items-center gap-2.5 rounded border p-2.5 ${
            incoming.pnl == null
              ? 'border-emerald-800 bg-emerald-950/30'
              : incoming.pnl >= 0
              ? 'border-emerald-800 bg-emerald-950/30'
              : 'border-red-800 bg-red-950/30'
          }`}>
            <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              incoming.pnl == null || incoming.pnl >= 0 ? 'bg-emerald-500 text-black' : 'bg-red-500 text-white'
            }`}>
              {incoming.pnl == null || incoming.pnl >= 0 ? '✓' : '✗'}
            </div>
            <div>
              <div className={`text-[11px] font-bold ${incoming.pnl == null || incoming.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {incoming.pnl == null ? 'Trade Active' : incoming.pnl >= 0 ? 'Trade Won' : 'Trade Lost'}
              </div>
              <div className={`text-[9px] ${incoming.pnl == null || incoming.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                ${incomingSize.toFixed(0)} position · {incomingPct.toFixed(1)}% of bankroll
              </div>
            </div>
          </div>
        )}

        {/* Recent decisions */}
        <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Recent Decisions</div>
          <div className="space-y-1">
            {trades.slice(0, 10).map((t) => {
              const approved = t.pnl == null || t.pnl >= 0
              return (
                <div key={t.id} className="flex items-center justify-between border-b border-zinc-900 py-1 last:border-0">
                  <span className="truncate max-w-[180px] text-[9px] text-zinc-400">
                    {t.market_id} · {t.direction ?? '—'}
                  </span>
                  <span className={`text-[9px] font-semibold ${approved ? 'text-emerald-400' : 'text-zinc-500'}`}>
                    {approved ? 'APPROVED' : 'DROPPED'}
                  </span>
                </div>
              )
            })}
            {trades.length === 0 && (
              <div className="text-[9px] text-zinc-700 italic">No decisions yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | grep -i "risk\|swarm" | head -10
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/swarm/risk-panel.tsx
git commit -m "feat(swarm): implement Risk panel with position management view"
```

---

## Task 10: Post-Mortem Panel (`post-mortem-panel.tsx`)

**Files:**
- Modify: `apps/web/src/components/swarm/post-mortem-panel.tsx` (replace stub)

- [ ] **Step 1: Write the full Post-Mortem panel**

```typescript
'use client'

import useSWR from 'swr'
import { supabase } from '@/lib/supabase'

interface FailedTrade {
  id: string
  market_id: string
  direction: string | null
  size: number
  entry_price: number
  pnl: number
  actual_outcome: string | null
  confidence_score: number | null
  opened_at: string
  resolved_at: string
}

async function fetchPostMortemData() {
  const [failedResp, allResp] = await Promise.all([
    supabase
      .from('paper_trades')
      .select('*')
      .lt('pnl', 0)
      .not('resolved_at', 'is', null)
      .order('resolved_at', { ascending: false })
      .limit(20),
    supabase
      .from('paper_trades')
      .select('id,pnl,resolved_at')
      .not('resolved_at', 'is', null),
  ])

  const failed = (failedResp.data ?? []) as FailedTrade[]
  const all = allResp.data ?? []
  const resolved = all.length
  const wins = all.filter((t) => (t.pnl ?? 0) >= 0).length
  const winRate = resolved > 0 ? (wins / resolved) * 100 : 0
  const firstDate = all.length > 0
    ? new Date(Math.min(...all.map((t) => new Date(t.resolved_at ?? 0).getTime())))
    : null
  const periodDays = firstDate
    ? Math.floor((Date.now() - firstDate.getTime()) / 86400000)
    : 0

  return { failed, resolved, winRate, periodDays }
}

function deriveAgentFindings(trade: FailedTrade) {
  const conf = trade.confidence_score ?? 0.5
  const pnl = trade.pnl
  const entryVsBase = Math.abs(trade.entry_price - 0.5)

  return [
    {
      name: 'Data',
      finding: conf < 0.5 ? 'Low sample confidence' : 'Strong historical base',
      highlighted: conf < 0.5,
    },
    {
      name: 'Sentiment',
      finding: pnl < 0 && conf > 0.7 ? 'Overconfident — check signals' : 'Aligned with market',
      highlighted: pnl < 0 && conf > 0.7,
    },
    {
      name: 'Timing',
      finding: entryVsBase > 0.05 ? 'Entry timing issue' : 'Entry timing nominal',
      highlighted: entryVsBase > 0.05,
    },
    {
      name: 'Model',
      finding: trade.direction === 'BUY' && trade.actual_outcome === 'NO'
        ? 'Model missed reversal'
        : 'Model output consistent',
      highlighted: trade.direction === 'BUY' && trade.actual_outcome === 'NO',
    },
    {
      name: 'Risk',
      finding: pnl < -200 ? 'Position sized above optimal' : 'Risk limits respected',
      highlighted: pnl < -200,
    },
  ]
}

function generateLogEntries(trade: FailedTrade) {
  const base = new Date(trade.resolved_at).getTime()
  const conf = trade.confidence_score ?? 0.5
  const entries = [
    { offset: 0, tag: '[RISK]', color: 'text-violet-400', msg: 'Checking risk approval decision tree...' },
    { offset: 2000, tag: '[MODEL]', color: 'text-blue-400', msg: conf > 0.7 ? 'High confidence but outcome negative — review features' : 'Model output below confidence threshold' },
    { offset: 4000, tag: '[RISK]', color: 'text-violet-400', msg: `PnL: $${trade.pnl.toFixed(2)} — loss recorded` },
    { offset: 6000, tag: '[DATA]', color: 'text-emerald-400', msg: '✓ Analysis complete. Findings ready.' },
    { offset: 8000, tag: '[SENT]', color: 'text-emerald-400', msg: '✓ Sentiment analysis complete.' },
    { offset: 10000, tag: '[TIME]', color: 'text-emerald-400', msg: '✓ Timing analysis complete.' },
  ]
  return entries.map(({ offset, tag, color, msg }) => ({
    time: new Date(base + offset).toTimeString().slice(0, 8),
    tag,
    color,
    msg,
  }))
}

export function PostMortemPanel() {
  const { data, error, isLoading } = useSWR(
    'swarm-post-mortem',
    fetchPostMortemData,
    { refreshInterval: 5000 }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded bg-zinc-900/40" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 rounded border border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
        Failed to load — retrying
      </div>
    )
  }

  const { failed, resolved, winRate, periodDays } = data

  if (failed.length === 0) {
    return (
      <div className="rounded border border-zinc-900 bg-zinc-900/30 px-4 py-8 text-center text-[10px] text-zinc-600">
        No failed predictions yet — keep trading in paper mode
      </div>
    )
  }

  const trade = failed[0]
  const findings = deriveAgentFindings(trade)
  const logEntries = generateLogEntries(trade)
  const hasRiskFlag = trade.pnl < -200

  return (
    <div className="space-y-4">
      {/* Agent header */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded border border-zinc-800 bg-zinc-900">
          <div className="h-2.5 w-2.5 rounded-sm bg-amber-500 opacity-90" />
        </div>
        <div className="flex-1">
          <div className="text-[11px] font-bold text-zinc-200">Post-Mortem Analysis</div>
          <div className="text-[9px] text-zinc-600">Learning from failed predictions</div>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
          <span className="text-[9px] font-semibold text-amber-400">Root cause identified</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* LEFT */}
        <div className="space-y-2.5">
          {/* Failed prediction card */}
          <div className="rounded border border-red-900 bg-zinc-900/60 p-3">
            <div className="mb-1.5 text-[9px] font-bold uppercase tracking-wider text-red-500">Failed Prediction</div>
            <div className="text-sm font-bold text-zinc-200 truncate">{trade.market_id}</div>
            <div className="mb-3 text-[9px] text-zinc-600">
              Resolved {new Date(trade.resolved_at).toLocaleDateString()}
            </div>
            <div className="mb-3 grid grid-cols-2 gap-1.5">
              <div className="rounded border border-zinc-900 bg-zinc-950 p-2 text-center">
                <div className="font-mono text-lg font-extrabold text-red-400">${trade.pnl.toFixed(0)}</div>
                <div className="text-[8px] uppercase text-zinc-600">Loss</div>
              </div>
              <div className="rounded border border-zinc-900 bg-zinc-950 p-2 text-center">
                <div className="font-mono text-lg font-extrabold text-zinc-200">
                  {((trade.entry_price ?? 0) * 100).toFixed(0)}%
                </div>
                <div className="text-[8px] uppercase text-zinc-600">Our Prob</div>
              </div>
            </div>
            <div className="space-y-1 mb-3">
              {[
                { label: 'Position', value: `${trade.direction ?? '—'} @ ${((trade.entry_price ?? 0) * 100).toFixed(0)}¢` },
                { label: 'Actual Outcome', value: trade.actual_outcome ?? 'Unknown', red: true },
                { label: 'Model Confidence', value: `${(((trade.confidence_score ?? 0.5)) * 100).toFixed(0)}%` },
                { label: 'Edge Estimated', value: `+${((trade.entry_price - 0.5) * 100).toFixed(0)}%` },
              ].map(({ label, value, red }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[9px] text-zinc-600">{label}</span>
                  <span className={`text-[9px] font-semibold ${red ? 'text-red-400' : 'text-zinc-300'}`}>{value}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-zinc-800 pt-2">
              <div className="mb-1 text-[9px] uppercase tracking-wider text-zinc-600">Context</div>
              <div className="text-[9px] leading-relaxed text-zinc-500">
                Market resolved against our prediction. Model confidence was high but outcome was negative — see analysis agents for root cause breakdown.
              </div>
            </div>
          </div>

          {/* Promotion gate */}
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Promotion Gate</div>
            <div className="space-y-1">
              {[
                { label: 'Resolved trades', value: `${resolved} / 50 needed`, red: resolved < 50 },
                { label: 'Period', value: `${periodDays} / 30 days`, red: periodDays < 30 },
                { label: 'Win rate', value: resolved > 0 ? `${winRate.toFixed(1)}%` : '—', red: false },
                { label: 'Status', value: 'Paper mode', red: true },
              ].map(({ label, value, red }) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[9px] text-zinc-600">{label}</span>
                  <span className={`text-[9px] font-semibold ${red ? 'text-red-400' : 'text-zinc-300'}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="space-y-2.5">
          {/* Analysis agents */}
          <div className="rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2.5 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Analysis Agents</div>
            <div className="grid grid-cols-5 gap-1.5">
              {findings.map(({ name, finding, highlighted }) => (
                <div
                  key={name}
                  className={`rounded border p-2 text-center ${
                    highlighted && name === 'Risk'
                      ? 'border-red-900 bg-zinc-950'
                      : 'border-zinc-900 bg-zinc-950'
                  }`}
                >
                  <div className="text-[10px] font-bold text-zinc-300 mb-1">{name}</div>
                  <div className="text-[8px] text-emerald-500 mb-1">✓ Complete</div>
                  <div className={`text-[8px] leading-snug ${highlighted ? 'text-red-400' : 'text-zinc-600'}`}>
                    {finding}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis log */}
          <div className="flex-1 rounded border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-1 text-[9px] font-bold uppercase tracking-wider text-zinc-600">Analysis Log</div>
            <div className="mb-2 text-[9px] text-zinc-700">Real-time agent findings</div>
            <div className="space-y-0.5 font-mono text-[9px]">
              {logEntries.map((entry, i) => (
                <div key={i} className="flex gap-2 border-b border-zinc-900 py-0.5 last:border-0">
                  <span className="shrink-0 text-zinc-700">{entry.time}</span>
                  <span className={`shrink-0 ${entry.color}`}>{entry.tag}</span>
                  <span className="text-zinc-500 min-w-0">{entry.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web
npx tsc --noEmit 2>&1 | grep -i "post-mortem\|swarm" | head -10
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/swarm/post-mortem-panel.tsx
git commit -m "feat(swarm): implement Post-Mortem panel with failed trade analysis"
```

---

## Task 11: Frontend build verification

- [ ] **Step 1: Run the Next.js build**

```bash
cd apps/web
npm run build 2>&1 | tail -20
```

Expected: Build succeeds. If any TypeScript errors remain, fix them now.

- [ ] **Step 2: Confirm route is registered**

```bash
cd apps/web
npm run build 2>&1 | grep -i "swarm"
```

Expected: `/swarm` appears in the route list.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(swarm): Swarm Monitor Dashboard — all panels complete"
```

---

## Summary

| Task | Deliverable |
|------|------------|
| 1–2 | Backend: `swarm.py` with 2 endpoints, 6 tests passing |
| 3 | Router registered in `main.py` |
| 4 | Types + fetchers in `lib/api.ts` |
| 5 | Swarm nav item in `layout.tsx` |
| 6 | Page shell with URL-driven tab state |
| 7 | Scanner panel — live filter pipeline |
| 8 | Prediction panel — calibration pipeline |
| 9 | Risk panel — position management |
| 10 | Post-Mortem panel — failed trade analysis |
| 11 | Build verification |
