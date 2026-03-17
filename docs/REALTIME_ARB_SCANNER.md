# Real-Time Prediction Market Arbitrage Scanner

Cross-platform arbitrage detection for Kalshi and Polymarket using WebSocket streams
instead of periodic HTTP polling. Detects fee-adjusted probability gaps in sub-second
latency vs. the prior 2-minute polling loop.

---

## The Problem It Solves

Arbitrage windows in prediction markets during live events last **5–45 seconds**.
The previous scanner polled every 2 minutes — missing virtually every window.

This system replaces polling with persistent WebSocket connections to both platforms,
checking arb conditions on every price tick.

---

## Architecture

```
Kalshi WS (ticker channel)          Polymarket WS (book channel)
  yes_bid / yes_ask per tick          best_bid / best_ask per token
         │                                       │
         └─────────────┬─────────────────────────┘
                       ▼
              RealtimeArbScanner
              ┌─────────────────────────────────────────────┐
              │ on every tick for a registered MarketPair:  │
              │   1. check direction A (YES Kalshi/NO Poly)  │
              │   2. check direction B (YES Poly/NO Kalshi)  │
              │   3. apply actual Kalshi fee formula         │
              │   4. if net gap ≥ threshold → fire callback  │
              └─────────────────────────────────────────────┘
                       │
              LiveArbOpportunity
              ┌─────────────────────────────────────────────┐
              │ description, both platforms + prices,       │
              │ gross/net profit %, sizing instructions      │
              │ (amount + contracts per leg)                 │
              └─────────────────────────────────────────────┘
```

---

## Files

| File | Package | Purpose |
|------|---------|---------|
| `kalshi_stream.py` | `sharpedge-feeds` | Kalshi WebSocket client (`ticker` channel) |
| `polymarket_stream.py` | `sharpedge-feeds` | Polymarket CLOB WebSocket client (`book` channel) |
| `realtime_scanner.py` | `sharpedge-analytics` | Gap detection engine; wires both streams |

---

## Quick Start

### 1. Register market pairs

Pairs must be pre-matched: you need the Kalshi ticker and the Polymarket YES/NO token IDs
for the same underlying event.

```python
from sharpedge_analytics.prediction_markets.realtime_scanner import (
    RealtimeArbScanner, MarketPair
)

scanner = RealtimeArbScanner(
    min_gap_pct=2.0,     # minimum net profit % after fees
    bankroll=10_000.0,   # total bankroll for sizing
    max_bet_pct=0.05,    # max 5% of bankroll per arb
)

scanner.register_pair(MarketPair(
    canonical_id="chiefs_sb_lx",
    description="Chiefs win Super Bowl",
    kalshi_ticker="KXNFL-25-KC",
    polymarket_yes_token="0xabc123...",
    polymarket_no_token="0xdef456...",   # optional; derived as 1-yes if omitted
))
```

### 2. Register a callback

```python
@scanner.on_arb
async def handle_arb(opp):
    print(f"ARB {opp.net_profit_pct:.2f}% | {opp.description}")
    for leg in opp.sizing["instructions"]:
        print(
            f"  {leg['action']} {leg['side']} on {leg['platform']}"
            f" @ {leg['price']:.3f}  — ${leg['amount']:.2f} ({leg['contracts']} contracts)"
        )
    print(f"  Guaranteed profit: ${opp.sizing['guaranteed_profit']:.2f}")
```

### 3. Wire and run

```python
import asyncio
from sharpedge_feeds.kalshi_stream import KalshiStreamClient
from sharpedge_feeds.polymarket_stream import PolymarketStreamClient
from sharpedge_feeds.kalshi_client import KalshiConfig

kalshi_stream = KalshiStreamClient(KalshiConfig(
    api_key="your-api-key-uuid",
    private_key_pem=open("kalshi_key.pem").read(),
))
poly_stream = PolymarketStreamClient()

# Wire subscribes both streams to the registered tickers/tokens
# and attaches the internal tick handlers
scanner.wire(kalshi_stream, poly_stream)

await asyncio.gather(
    kalshi_stream.run(),
    poly_stream.run(),
)
```

---

## Fee Math

The scanner uses the **actual Kalshi probability-weighted formula**, not a fixed rate:

```
kalshi_fee = 0.07 × contracts × price × (1 − price)
```

This fee is highest at price = 0.50 (±3.5% effective) and approaches zero at the
extremes (0.01 or 0.99). Polymarket standard markets have zero trading fees.

Fee-adjusted effective price per contract:

```python
adj_price = raw_price + (fee / contracts)  # buying
```

Both directions are checked. An opportunity only fires if **net_total < 1.0** after
applying fees to both legs.

---

## MarketPair Fields

| Field | Type | Description |
|-------|------|-------------|
| `canonical_id` | `str` | Unique ID for this pair (used for cooldown tracking) |
| `description` | `str` | Human-readable event name |
| `kalshi_ticker` | `str` | Kalshi market ticker (e.g. `KXNFL-25-KC`) |
| `polymarket_yes_token` | `str` | Polymarket YES outcome token ID (hex) |
| `polymarket_no_token` | `str \| None` | Polymarket NO token ID; omit to derive as `1 − yes_ask` |

---

## LiveArbOpportunity Fields

| Field | Type | Description |
|-------|------|-------------|
| `canonical_id` | `str` | Pair identifier |
| `description` | `str` | Event name |
| `buy_yes_platform` | `str` | `"kalshi"` or `"polymarket"` |
| `buy_yes_price` | `float` | Raw YES ask price (0–1) |
| `buy_no_platform` | `str` | `"kalshi"` or `"polymarket"` |
| `buy_no_price` | `float` | Raw NO ask price (0–1) |
| `gross_profit_pct` | `float` | Profit % before fees |
| `net_profit_pct` | `float` | Profit % after platform fees |
| `sizing` | `dict` | Sizing instructions (see below) |
| `detected_at` | `datetime` | When the opportunity was detected |
| `estimated_window_seconds` | `int` | Default 30s; override in subclass |

### `sizing` dict

```python
{
    "total_stake": 500.00,          # dollars
    "guaranteed_profit": 11.23,     # dollars regardless of outcome
    "roi_pct": 2.25,
    "instructions": [
        {
            "platform": "kalshi",
            "action": "BUY",
            "side": "YES",
            "price": 0.48,
            "amount": 245.00,       # dollars
            "contracts": 510,
        },
        {
            "platform": "polymarket",
            "action": "BUY",
            "side": "NO",
            "price": 0.505,
            "amount": 255.00,
            "contracts": 504,
        },
    ],
}
```

---

## Bulk Pair Registration

Use `build_scanner_from_matched_markets()` when you have many pairs:

```python
from sharpedge_analytics.prediction_markets.realtime_scanner import (
    build_scanner_from_matched_markets
)

pairs = [
    ("Chiefs win SB",        "KXNFL-25-KC",   "0xabc...", "0xdef..."),
    ("Eagles win SB",        "KXNFL-25-PHI",  "0x123...", "0x456..."),
    ("Total points > 47.5",  "KXNFL-25-O47",  "0x789...", None),
]

scanner = build_scanner_from_matched_markets(
    pairs,
    min_gap_pct=2.0,
    bankroll=10_000.0,
)
```

---

## Matching Markets (Getting Pair IDs)

You still need to obtain the Kalshi ticker and Polymarket token IDs for each event.
Two options:

**Option A — Use the existing `MarketCorrelationNetwork` from a bulk fetch:**

```python
from sharpedge_feeds.kalshi_client import get_kalshi_client
from sharpedge_feeds.polymarket_client import get_polymarket_client
from sharpedge_analytics.prediction_markets import MarketCorrelationNetwork

kalshi = await get_kalshi_client(api_key="...")
poly   = await get_polymarket_client()

k_markets = await kalshi.get_markets(status="open")
p_markets = await poly.get_markets(active=True)

# Build MarketOutcome objects and add to correlation network
# (existing prediction_market_scanner.py already does this)
# Then extract matched pairs for registration
```

**Option B — Hard-code known pairs** for specific events (Super Bowl, election night, etc.)
where you know the tickers in advance. This is more reliable for time-sensitive events
where you want the scanner running before markets open.

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_gap_pct` | `2.0` | Minimum net profit % to trigger a callback |
| `bankroll` | `10_000.0` | Total capital for position sizing |
| `max_bet_pct` | `0.05` | Max fraction of bankroll per arb (5%) |
| `_fire_cooldown` | `1.0` | Seconds between callbacks for the same pair |

Adjust `_fire_cooldown` directly on the scanner instance if you want faster re-fires
during high-volatility windows:

```python
scanner._fire_cooldown = 0.25  # fire at most 4× per second per pair
```

---

## Reconnect Behavior

Both stream clients reconnect automatically on disconnect using exponential backoff:

```
attempt 1: wait 1s
attempt 2: wait 2s
attempt 3: wait 4s
...
max wait:  30s
```

On reconnect, the subscribe message is re-sent with all registered tickers/tokens.

---

## Limitations

1. **Market matching is manual** — pairs must be pre-registered. The existing
   `MarketCorrelationNetwork` (Jaccard similarity) can assist but may miss or
   misidentify markets with non-standard wording.

2. **Execution is not implemented** — the scanner detects and sizes opportunities
   but does not place orders. Kalshi order placement is in `KalshiClient.create_order()`.
   Polymarket order placement requires separate CLOB integration.

3. **Stale price staleness** — if only one stream updates and the other has not sent a
   tick recently, `_check_pair` runs on potentially stale data from the other side.
   The `last_kalshi_ts` / `last_poly_ts` fields on `MarketPair` can be used to add
   a staleness guard if needed.

4. **No_token derivation** — when `polymarket_no_token` is omitted, NO ask is derived
   as `1 − poly_yes_ask`. This is accurate for binary markets but incorrect for markets
   where the NO token trades independently with its own spread.
