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
MarketCorrelationNetwork ──────── discover_and_wire() ─── auto-registers matched pairs
(Jaccard similarity)                      │
                                          ▼
Kalshi WS (ticker channel)          Polymarket WS (book channel)
  yes_bid / yes_ask per tick          best_bid / best_ask per token
         │                                       │
         └─────────────┬─────────────────────────┘
                       ▼
              RealtimeArbScanner
              ┌─────────────────────────────────────────────┐
              │ on every tick for a registered MarketPair:  │
              │   0. staleness guard (>5s stale → skip)     │
              │   1. NO token pricing (stream → CLOB → 1-y) │
              │   2. check direction A (YES Kalshi/NO Poly)  │
              │   3. check direction B (YES Poly/NO Kalshi)  │
              │   4. apply actual Kalshi fee formula         │
              │   5. if net gap ≥ threshold → fire callback  │
              └─────────────────────────────────────────────┘
                       │
              LiveArbOpportunity
              ┌─────────────────────────────────────────────┐
              │ description, both platforms + prices,       │
              │ gross/net profit %, sizing instructions      │
              │ (amount + contracts per leg)                 │
              └─────────────────────────────────────────────┘
                       │
              shadow_execute_arb()
              ┌─────────────────────────────────────────────┐
              │ asyncio.gather(kalshi leg, poly leg)         │
              │ Kalshi: KalshiClient.create_order()         │
              │ Poly:   PolymarketCLOBOrderClient (shadow)  │
              └─────────────────────────────────────────────┘
```

---

## Files

| File | Package | Purpose |
|------|---------|---------|
| `kalshi_stream.py` | `sharpedge-feeds` | Kalshi WebSocket client (`ticker` channel) |
| `polymarket_stream.py` | `sharpedge-feeds` | Polymarket CLOB WebSocket client (`book` channel) |
| `polymarket_clob_orders.py` | `sharpedge-feeds` | Polymarket CLOB order placement client (shadow mode) |
| `realtime_scanner.py` | `sharpedge-analytics` | Gap detection engine; wires both streams |

---

## Quick Start

### 1. Auto-discover and register pairs

Use `discover_and_wire()` to automatically match markets across platforms using Jaccard
similarity — no manual pair registration needed:

```python
import asyncio
from sharpedge_analytics.prediction_markets.realtime_scanner import RealtimeArbScanner
from sharpedge_feeds.kalshi_stream import KalshiStreamClient
from sharpedge_feeds.polymarket_stream import PolymarketStreamClient
from sharpedge_feeds.kalshi_client import KalshiConfig

scanner = RealtimeArbScanner(min_gap_pct=2.0, bankroll=10_000.0)
kalshi_stream = KalshiStreamClient(KalshiConfig(api_key="...", private_key_pem="..."))
poly_stream = PolymarketStreamClient()

# Fetches open markets from both platforms, Jaccard-matches them,
# registers pairs, and calls scanner.wire() — all in one call.
await scanner.discover_and_wire(kalshi_stream, poly_stream)
```

Or register pairs manually when you know the tickers in advance:

```python
from sharpedge_analytics.prediction_markets.realtime_scanner import (
    RealtimeArbScanner, MarketPair
)

scanner = RealtimeArbScanner(
    min_gap_pct=2.0,          # minimum net profit % after fees
    bankroll=10_000.0,        # total bankroll for sizing
    max_bet_pct=0.05,         # max 5% of bankroll per arb
    staleness_threshold_s=5.0, # skip pairs with stale quotes older than 5s
)

scanner.register_pair(MarketPair(
    canonical_id="chiefs_sb_lx",
    description="Chiefs win Super Bowl",
    kalshi_ticker="KXNFL-25-KC",
    polymarket_yes_token="0xabc123...",
    polymarket_no_token="0xdef456...",   # optional; CLOB fallback used if omitted
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

### 4. Execute opportunities (shadow mode)

Use `shadow_execute_arb()` to fire both legs concurrently. Shadow mode is on by default —
set `ENABLE_POLY_EXECUTION=true` to enable live Polymarket orders once your CLOB integration
is fully configured.

```python
from sharpedge_analytics.prediction_markets.realtime_scanner import shadow_execute_arb
from sharpedge_feeds.kalshi_client import KalshiClient
from sharpedge_feeds.polymarket_clob_orders import PolymarketCLOBOrderClient

kalshi_client = KalshiClient(...)
poly_clob = PolymarketCLOBOrderClient()  # shadow mode by default

@scanner.on_arb
async def handle_arb(opp):
    result = await shadow_execute_arb(opp, kalshi_client, poly_clob)
    print(result["order_ids"])   # both leg order IDs
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
| `polymarket_no_token` | `str \| None` | Polymarket NO token ID; if omitted, CLOB is queried as fallback then `1 − yes_ask` |

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

### Automatic (recommended): `discover_and_wire()`

`discover_and_wire()` handles the full lifecycle — fetch open markets from both platforms
concurrently, match them via Jaccard similarity (`MarketCorrelationNetwork`), register all
matched pairs, and wire the streams. The NO token is extracted per outcome rather than derived:

```python
await scanner.discover_and_wire(kalshi_stream, poly_stream)
```

### Manual: hard-code known pairs

For time-sensitive events where you know the tickers in advance (Super Bowl, election night),
pre-registering pairs before markets open is more reliable than waiting for discovery:

```python
scanner.register_pair(MarketPair(
    canonical_id="sb_2026_chiefs",
    description="Chiefs win Super Bowl LX",
    kalshi_ticker="KXNFL-26-KC",
    polymarket_yes_token="0xabc...",
    polymarket_no_token="0xdef...",
))
```

### Manual: bulk from correlation network

```python
from sharpedge_analytics.prediction_markets import MarketCorrelationNetwork
# (prediction_market_scanner.py already builds the network from periodic fetches)
# Extract matched pairs, then scanner.register_pairs(pairs)
```

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_gap_pct` | `2.0` | Minimum net profit % to trigger a callback |
| `bankroll` | `10_000.0` | Total capital for position sizing |
| `max_bet_pct` | `0.05` | Max fraction of bankroll per arb (5%) |
| `staleness_threshold_s` | `5.0` | Skip pair if either side's last tick is older than this |
| `_fire_cooldown` | `1.0` | Seconds between callbacks for the same pair |

Adjust `_fire_cooldown` directly on the scanner instance if you want faster re-fires
during high-volatility windows:

```python
scanner._fire_cooldown = 0.25  # fire at most 4× per second per pair
```

Set `staleness_threshold_s=0` to disable the staleness guard entirely:

```python
scanner = RealtimeArbScanner(staleness_threshold_s=0)
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

## Known Limitations

1. **Auto-discovery match quality** — `discover_and_wire()` uses Jaccard similarity on
   market titles. Markets with non-standard or abbreviated wording may be missed or
   incorrectly matched. Verify matches for high-stakes events; use manual registration
   for known tickers.

2. **Polymarket live execution deferred** — `PolymarketCLOBOrderClient` ships in shadow
   mode by default (`ENABLE_POLY_EXECUTION` env var, default `false`). Shadow mode logs
   the order and returns a synthetic order ID without hitting the CLOB. Set
   `ENABLE_POLY_EXECUTION=true` once EIP-712 signing and wallet configuration are
   complete (tracked as POLY-EXEC-01).

3. **Staleness guard fires only after first tick** — pairs with `last_kalshi_ts=0.0`
   or `last_poly_ts=0.0` skip the staleness check (no data yet, not stale). The guard
   activates only once both sides have received at least one tick. This means the very
   first evaluation on a new pair uses whatever data arrived first.
