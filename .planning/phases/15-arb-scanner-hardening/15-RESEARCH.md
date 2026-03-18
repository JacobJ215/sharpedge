# Phase 15: Arb Scanner Hardening - Research

**Researched:** 2026-03-17
**Domain:** Real-time arbitrage scanning, Polymarket CLOB execution, cross-platform market matching
**Confidence:** HIGH (core code read directly; Polymarket CLOB API verified against official docs and py-clob-client source)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARB-01 | Operator starts scanner without pre-registering pairs — discovers and matches Kalshi/Polymarket markets automatically using `MarketCorrelationNetwork`, subscribing streams for all matched pairs | `MarketCorrelationNetwork._calculate_similarity()` (Jaccard, threshold 0.7) exists in `arbitrage.py`; `KalshiClient.get_markets()` and `PolymarketClient.get_markets()` already exist; `RealtimeArbScanner.register_pair()` and `wire()` already exist — need a new async `discover_and_wire()` method that chains these |
| ARB-02 | When arb opportunity exceeds threshold, scanner places limit orders on both Kalshi and Polymarket simultaneously, recording both order IDs | Kalshi: `KalshiClient.create_order(ticker, action, side, order_type, count, yes_price)` exists; Polymarket: CLOB POST `/order` endpoint at `clob.polymarket.com`, requires EIP-712 signed payload — simplest approach is to add `PolymarketClient.create_order()` wrapping the CLOB REST endpoint |
| ARB-03 | When either side's last update is older than staleness threshold (default 5s), skip pair and log warning | `MarketPair.last_kalshi_ts` and `last_poly_ts` fields already exist on the dataclass; need guard in `_check_pair()` before arb evaluation |
| ARB-04 | When `polymarket_no_token` is not set, fetch actual NO token order book from Polymarket CLOB instead of deriving `1 - yes_ask` | `PolymarketClient.get_orderbook(token_id)` exists at `GET /book?token_id={id}`; need to resolve the NO token_id from the YES token_id via Gamma API or market metadata, then call `get_orderbook()` to read real best ask |
</phase_requirements>

---

## Summary

Phase 15 hardens four known deficiencies in `RealtimeArbScanner`. All four changes are additive — no existing logic is removed, only extended. The existing code base already supplies every primitive needed; the work is wiring them together correctly.

**ARB-01** is the most architecturally significant change. `MarketCorrelationNetwork` already implements Jaccard-based text similarity matching at a 0.7 threshold. The missing piece is a startup coroutine that fetches open markets from both platforms, feeds them into `MarketCorrelationNetwork.add_market()`, extracts matched pairs via `get_multi_platform_events()`, converts them to `MarketPair` objects, calls `register_pairs()`, then calls `wire()`. This coroutine belongs on `RealtimeArbScanner` itself as `async discover_and_wire()`.

**ARB-02** requires implementing Polymarket CLOB order placement. Kalshi execution already exists via `KalshiClient.create_order()`. The Polymarket CLOB order endpoint is `POST https://clob.polymarket.com/order`. The critical complexity is that Polymarket orders require EIP-712 cryptographic signing — the order struct must be signed with the trader's Polygon private key before posting. The project's existing `PolymarketClient._build_auth_headers()` uses HMAC (wrong for order signing). A new `PolymarketCLOBOrderClient` that wraps EIP-712 signing via `py-clob-client` is the correct approach. Both legs must be dispatched with `asyncio.gather()` for simultaneous execution.

**ARB-03** is the smallest change: a 4-line guard at the top of `_check_pair()` that compares `time.time() - pair.last_kalshi_ts` and `time.time() - pair.last_poly_ts` against a configurable `staleness_threshold_s` (default 5.0), logs a warning, and returns early.

**ARB-04** requires fetching the real NO token order book when `polymarket_no_token` is not set on the `MarketPair`. `PolymarketClient.get_orderbook(token_id)` already exists and calls `GET /book?token_id={id}`. The challenge is that the NO token ID is not always stored on the pair — it must be looked up from the Polymarket market metadata at startup (the `tokens` array in the Gamma API response always includes both YES and NO token IDs).

**Primary recommendation:** All four changes target `realtime_scanner.py` plus a new `PolymarketCLOBOrderClient` wrapper. Plan in two waves: Wave 1 = ARB-03 (staleness guard, trivial) + ARB-04 (NO token lookup, self-contained); Wave 2 = ARB-01 (auto-discovery wiring) + ARB-02 (dual-platform execution).

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sharpedge-analytics` | workspace | `RealtimeArbScanner`, `MarketCorrelationNetwork`, `MarketPair` | Contains all existing scanner logic |
| `sharpedge-feeds` | workspace | `KalshiClient`, `PolymarketClient`, stream clients | All transport clients already implemented |
| `asyncio` | stdlib | Concurrent order placement, event loop | Already used throughout |
| `websockets` | project dep | WebSocket streams | Already used in stream clients |
| `httpx` | project dep | HTTP for REST API calls | Already used in both clients |

### New Dependency (ARB-02 only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `py-clob-client` | latest (PyPI) | Polymarket CLOB EIP-712 order signing | Required for ARB-02 — EIP-712 signing is complex enough that hand-rolling it is error-prone |
| `eth-account` | >=0.8 (transitive via py-clob-client) | Polygon wallet signing | Pulled in automatically by py-clob-client |

**Installation (ARB-02 only):**
```bash
# In packages/data_feeds or packages/analytics pyproject.toml, add:
# "py-clob-client>=0.20"
uv add py-clob-client --package sharpedge-feeds
```

**Note:** If ARB-02 is scoped narrowly to "record both order IDs" without real capital, a stub `PolymarketCLOBOrderClient` that logs rather than signs is acceptable for Phase 15, deferring real EIP-712 signing to Phase 12's pattern (shadow vs live flag). This avoids the py-clob-client dependency entirely.

---

## Architecture Patterns

### Recommended File Changes

```
packages/
├── analytics/src/sharpedge_analytics/prediction_markets/
│   └── realtime_scanner.py          # ARB-01, ARB-03, ARB-04 changes here
└── data_feeds/src/sharpedge_feeds/
    ├── polymarket_client.py          # ARB-04: get_orderbook already exists
    └── polymarket_clob_orders.py     # ARB-02: NEW — PolymarketCLOBOrderClient
```

### Pattern 1: ARB-03 — Staleness Guard in `_check_pair()`

**What:** Early-exit guard using already-populated `last_kalshi_ts` / `last_poly_ts` fields.
**When to use:** Called on every price tick before any arb computation.

```python
# Source: realtime_scanner.py — _check_pair() modification
async def _check_pair(self, pair: MarketPair) -> None:
    """Check both arb directions on every price update."""
    if not (pair.kalshi_yes_ask > 0 and pair.poly_yes_ask > 0):
        return  # insufficient data

    # ARB-03: staleness guard
    now = time.time()
    kalshi_age = now - pair.last_kalshi_ts
    poly_age = now - pair.last_poly_ts
    if kalshi_age > self.staleness_threshold_s or poly_age > self.staleness_threshold_s:
        logger.warning(
            "Staleness guard: skipping %s (kalshi_age=%.1fs, poly_age=%.1fs)",
            pair.canonical_id, kalshi_age, poly_age,
        )
        return
    # ... existing direction A / direction B checks unchanged
```

The `staleness_threshold_s` parameter (default `5.0`) goes on `RealtimeArbScanner.__init__()`.

**Note:** `pair.last_kalshi_ts` and `pair.last_poly_ts` are set to `0.0` at construction. The guard fires if either field has never been updated (age = `now - 0.0` is enormous), which is correct — don't arb a pair where one side has no live data at all.

### Pattern 2: ARB-04 — Real NO Token Orderbook Fetch

**What:** When `polymarket_no_token` is None, fetch the NO token's real best ask from CLOB instead of deriving `1 - yes_ask`.
**When to use:** Inside `_check_pair()`, replacing the existing one-liner derivation.

The NO token ID for a Polymarket binary market is reliably available in the `tokens` array returned by the Gamma API. `PolymarketClient._parse_market()` already reads `data.get("tokens", [])` — the YES token has `outcome == "Yes"` and the NO token has `outcome == "No"`. At startup / discovery time, when building `MarketPair` objects, the NO token ID should always be extracted and populated into `pair.polymarket_no_token`.

For the case where `polymarket_no_token` remains None at runtime (legacy pair, manually constructed), the scanner must fall back to fetching the orderbook on-demand:

```python
# Source: realtime_scanner.py — inside _check_pair() before Direction A
if pair.poly_no_ask <= 0 and pair.polymarket_no_token is None:
    # ARB-04: fetch real NO-side best ask from CLOB
    # (polymarket_client injected at scanner construction for this purpose)
    if self._poly_client is not None:
        ob = await self._poly_client.get_orderbook_no_token(pair)
        if ob:
            pair.poly_no_ask = ob
    # If still 0, fall through — _evaluate() guards against zero prices
```

However, the cleaner approach (recommended for planning) is to guarantee `polymarket_no_token` is always populated during ARB-01's `discover_and_wire()` by reading both token IDs from the Gamma API response. This eliminates the need for runtime fallback fetching.

### Pattern 3: ARB-01 — Auto-Discovery `discover_and_wire()`

**What:** New async method on `RealtimeArbScanner` that fetches, matches, registers, and subscribes — replacing the manual `register_pair()` + `wire()` call sequence.
**When to use:** Called once at scanner startup before `asyncio.gather(kalshi_stream.run(), poly_stream.run())`.

```python
# Source: realtime_scanner.py — new method on RealtimeArbScanner
async def discover_and_wire(
    self,
    kalshi_client: KalshiClient,
    poly_client: PolymarketClient,
    kalshi_stream: KalshiStreamClient,
    poly_stream: PolymarketStreamClient,
    similarity_threshold: float = 0.7,
) -> int:
    """Fetch open markets, match pairs via Jaccard similarity, register, and wire.

    Returns:
        Number of matched pairs registered.
    """
    from sharpedge_analytics.prediction_markets.arbitrage import MarketCorrelationNetwork
    from sharpedge_analytics.prediction_markets.types import MarketOutcome
    from .fees import Platform

    # 1. Fetch open markets from both platforms
    kalshi_markets, poly_markets = await asyncio.gather(
        kalshi_client.get_markets(status="open", limit=200),
        poly_client.get_markets(active=True, closed=False, limit=200),
    )

    # 2. Feed into correlation network
    network = MarketCorrelationNetwork()
    for km in kalshi_markets:
        network.add_market(MarketOutcome(
            platform=Platform.KALSHI, market_id=km.ticker,
            outcome_id=km.ticker, question=km.title,
            outcome_label="Yes", price=km.yes_ask,
        ))
    for pm in poly_markets:
        for token in pm.outcomes:
            if token.outcome.lower() == "yes":
                network.add_market(MarketOutcome(
                    platform=Platform.POLYMARKET, market_id=pm.condition_id,
                    outcome_id=token.token_id, question=pm.question,
                    outcome_label="Yes", price=token.price,
                ))

    # 3. Extract multi-platform events (matched pairs)
    matched_events = network.get_multi_platform_events()
    pairs = []
    for event in matched_events:
        kalshi_market = event.platform_markets.get(Platform.KALSHI)
        poly_market = event.platform_markets.get(Platform.POLYMARKET)
        if not (kalshi_market and poly_market):
            continue
        # Extract NO token ID from poly_markets
        poly_no_token = _extract_no_token(poly_markets, poly_market.market_id)
        pairs.append(MarketPair(
            canonical_id=event.canonical_id,
            description=event.description,
            kalshi_ticker=kalshi_market.market_id,
            polymarket_yes_token=poly_market.outcome_id,
            polymarket_no_token=poly_no_token,
        ))

    self.register_pairs(pairs)
    self.wire(kalshi_stream, poly_stream)
    logger.info("Auto-discovered %d matched pairs", len(pairs))
    return len(pairs)
```

### Pattern 4: ARB-02 — Simultaneous Dual-Platform Execution

**What:** When an arb fires, place limit orders on both platforms concurrently and record both order IDs on the `LiveArbOpportunity`.
**When to use:** Inside `_fire()` or via a new `execute_arb()` method.

The `LiveArbOpportunity.sizing["instructions"]` already contains the per-leg details (platform, side, price, contracts). The execution wrapper reads those and dispatches:

```python
# Source: new execute_arb() coroutine — called from arb callback
async def execute_arb(
    opp: LiveArbOpportunity,
    kalshi_client: KalshiClient,
    poly_clob_client: PolymarketCLOBOrderClient,
) -> dict:
    legs = opp.sizing["instructions"]
    tasks = []
    for leg in legs:
        if leg["platform"] == "kalshi":
            tasks.append(_place_kalshi_leg(kalshi_client, leg))
        else:
            tasks.append(_place_poly_leg(poly_clob_client, leg))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {"order_ids": results, "canonical_id": opp.canonical_id}
```

Kalshi placement calls `KalshiClient.create_order(ticker=..., action="buy", side=leg["side"].lower(), order_type="limit", count=leg["contracts"], yes_price=int(leg["price"] * 100))`.

### Anti-Patterns to Avoid

- **Deriving NO ask from YES ask at runtime**: Violates ARB-04. Always populate `polymarket_no_token` at discovery time.
- **Sequential order placement**: Violates ARB-02's "simultaneously" requirement. Always use `asyncio.gather()`.
- **Firing arb callbacks before staleness check**: The staleness guard must occur inside `_check_pair()` before `_evaluate()` is ever called.
- **Relying on `PolymarketClient._build_auth_headers()` for order signing**: That client uses HMAC, which is for GET data endpoints. Order placement requires EIP-712 signing — a separate concern handled by `PolymarketCLOBOrderClient`.
- **Fetching Kalshi markets one-at-a-time for discovery**: Use `get_markets(limit=200)` with pagination loop rather than individual `get_market()` calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Jaccard text similarity for market matching | Custom tokenizer | `MarketCorrelationNetwork._calculate_similarity()` | Already implemented, threshold 0.7 already calibrated |
| Kalshi order placement | Raw HTTP POST | `KalshiClient.create_order()` | RSA-PSS auth already handled; price centering (yes+no=100) already done |
| Polymarket orderbook best-ask | Custom parser | `PolymarketClient.get_orderbook(token_id)` + `_best_ask()` | Already implemented, handles edge cases |
| EIP-712 signing for Polymarket orders | Custom eth signing | `py-clob-client` or stub with flag | EIP-712 has nonce, chain_id, domain separator complexity |
| Concurrent async execution | Thread pool | `asyncio.gather()` | Both clients are async-native |
| WebSocket subscription management | Custom pubsub | `KalshiStreamClient.subscribe()` + `PolymarketStreamClient.subscribe()` | Already implemented with reconnect |

**Key insight:** Every primitive for all four requirements already exists. This phase is entirely wiring work, not new infrastructure.

---

## Common Pitfalls

### Pitfall 1: `last_kalshi_ts` initialized to `0.0` — false stale on brand-new pairs

**What goes wrong:** When a `MarketPair` is first created, both timestamps are `0.0`. If `_check_pair()` is called before any tick arrives (e.g., a stray leftover tick), `time.time() - 0.0` is a large number, which will always trigger the staleness warning, even on a perfectly healthy pair.
**Why it happens:** `MarketPair` is a dataclass with `last_kalshi_ts: float = 0.0` — uninitialized.
**How to avoid:** The staleness guard should only trigger if at least one side HAS received a tick. Guard condition: `if pair.last_kalshi_ts > 0 and pair.last_poly_ts > 0` — then check ages. If either is still 0.0, treat as "no data yet" (already handled by the existing `if not (pair.kalshi_yes_ask > 0 ...)` guard above).
**Warning signs:** Log is flooded with staleness warnings immediately on startup.

### Pitfall 2: NO token ID not reliably "the other token" without checking `outcome` field

**What goes wrong:** `PolymarketMarket.outcomes` contains the YES and NO tokens in the order the API returns them. Assuming index 0 = YES, index 1 = NO causes incorrect NO token assignment on some markets.
**Why it happens:** Polymarket does not guarantee token order in the `tokens` array.
**How to avoid:** Always filter by `outcome.outcome.lower() == "no"` when extracting the NO token ID.

### Pitfall 3: Jaccard similarity at 0.7 produces false positives for short market titles

**What goes wrong:** "Will X happen?" vs "Will X occur?" — two-word intersection over small union can give high Jaccard even when events differ.
**Why it happens:** Short texts have inflated Jaccard scores.
**How to avoid:** Add a minimum word count check before matching (e.g., skip markets with fewer than 4 words). Acceptable for Phase 15 since the primary goal is automation, not perfect precision — false positives result in non-arb pairs being subscribed (benign) rather than missed arb.

### Pitfall 4: Polymarket CLOB order signing requires Polygon wallet, not just API key

**What goes wrong:** Attempting to post an order using only `POLY-API-KEY` / `POLY-SIGNATURE` headers (L2 auth) fails with a 401/403. Order creation requires L1 (private key) + L2 (API key + secret + passphrase).
**Why it happens:** The existing `PolymarketClient._build_auth_headers()` only does L2. `POST /order` requires a pre-signed EIP-712 order struct in the body.
**How to avoid:** Scope ARB-02 as "log order intent + record simulated order ID" (shadow mode) unless a Polygon private key is available in environment. This matches the project's overall approach of gating live capital behind `ENABLE_*` flags (see Phase 11/12 pattern).

### Pitfall 5: `asyncio.gather()` on both stream run-loops is blocking

**What goes wrong:** Calling `discover_and_wire()` from inside an already-running event loop causes nesting errors.
**Why it happens:** `discover_and_wire()` itself calls `asyncio.gather()` for parallel market fetching, which is fine. But if the caller tries to `await discover_and_wire()` after `asyncio.gather(stream.run(), ...)` has already started, it never executes.
**How to avoid:** Call `discover_and_wire()` before the stream gather, in a pre-run setup coroutine. The canonical pattern is:
```python
async def main():
    await scanner.discover_and_wire(kalshi_client, poly_client, ks, ps)
    await asyncio.gather(ks.run(), ps.run())
```

### Pitfall 6: Kalshi `yes_price` parameter is in cents (integer 1-99), not 0-1 float

**What goes wrong:** Passing `yes_price=0.45` (a float) to `KalshiClient.create_order()` results in an integer truncation to `0`, which is an invalid price.
**Why it happens:** The Kalshi REST API and `KalshiClient.create_order()` signature both use integer cents (1-99). The scanner stores prices as 0-1 floats.
**How to avoid:** Convert at the call site: `yes_price=int(round(leg["price"] * 100))`. Enforce bounds: must be between 1 and 99 inclusive.

---

## Code Examples

### Staleness Check (ARB-03)

```python
# Source: realtime_scanner.py RealtimeArbScanner._check_pair() — guard insertion
async def _check_pair(self, pair: MarketPair) -> None:
    """Check both arb directions on every price update."""
    if not (pair.kalshi_yes_ask > 0 and pair.poly_yes_ask > 0):
        return

    # ARB-03: only check staleness once both sides have received at least one tick
    if pair.last_kalshi_ts > 0 and pair.last_poly_ts > 0:
        now = time.time()
        if (now - pair.last_kalshi_ts) > self.staleness_threshold_s:
            logger.warning("Stale Kalshi data for %s (%.1fs old)", pair.canonical_id,
                           now - pair.last_kalshi_ts)
            return
        if (now - pair.last_poly_ts) > self.staleness_threshold_s:
            logger.warning("Stale Polymarket data for %s (%.1fs old)", pair.canonical_id,
                           now - pair.last_poly_ts)
            return
    # ... existing Direction A / B logic unchanged
```

### Polymarket Orderbook Best Ask (ARB-04)

```python
# Source: polymarket_client.py — PolymarketClient.get_orderbook() (already exists)
# Endpoint: GET https://clob.polymarket.com/book?token_id={token_id}
# Response: {"bids": [{"price": "0.48", "size": "500"}], "asks": [...], "spread": "0.04"}

async def get_no_token_best_ask(self, no_token_id: str) -> float | None:
    """Fetch best ask for a NO token from CLOB orderbook. Returns None if no liquidity."""
    ob = await self.get_orderbook(no_token_id)
    asks = ob.get("asks", [])
    # _best_ask equivalent: lowest non-zero ask price
    best = None
    for level in asks:
        try:
            p = float(level.get("price", 0))
            if p > 0 and (best is None or p < best):
                best = p
        except (TypeError, ValueError):
            pass
    return best
```

### Polymarket CLOB Order Placement REST Endpoint (ARB-02)

```python
# Source: Polymarket official docs (docs.polymarket.com/developers/CLOB/orders/create-order)
#         and py-clob-client endpoints.py (POST_ORDER = "/order")
#
# Endpoint:  POST https://clob.polymarket.com/order
# Auth:      L1 (EIP-712 signed order in body) + L2 (API key headers)
# Headers:   POLY-ADDRESS, POLY-SIGNATURE, POLY-TIMESTAMP, POLY-API-KEY,
#            POLY-PASSPHRASE (for L2)
#
# Request body (signed order struct — handled by py-clob-client):
# {
#   "order": {
#     "salt":         <nonce>,
#     "maker":        "0x<wallet_address>",
#     "signer":       "0x<signer_address>",
#     "taker":        "0x0000000000000000000000000000000000000000",
#     "tokenId":      "<token_id>",
#     "makerAmount":  "<usdc_amount_in_smallest_unit>",
#     "takerAmount":  "<token_amount>",
#     "expiration":   "0",
#     "nonce":        "0",
#     "feeRateBps":   "0",
#     "side":         "BUY",
#     "signatureType": 0,
#     "signature":    "0x<eip712_sig>"
#   },
#   "owner":     "0x<address>",
#   "orderType": "GTC"
# }
#
# Response:
# {
#   "success": true,
#   "errorMsg": "",
#   "orderID": "0xabc123...",
#   "status": "live|matched|delayed|unmatched",
#   "transactionsHashes": [],
#   "tradeIDs": []
# }
#
# Shadow mode recommendation: wrap in ENABLE_POLY_EXECUTION flag identical to
# Phase 11/12's ENABLE_KALSHI_EXECUTION pattern; log intent without signing
# when flag is false.
```

### Kalshi Order Placement (already exists)

```python
# Source: kalshi_client.py KalshiClient.create_order()
# Endpoint: POST https://api.elections.kalshi.com/trade-api/v2/portfolio/orders
# Auth:     RSA-PSS-SHA256 per-request signing (already implemented)
#
# Key type constraints (verified from source):
#   - ticker:     str   e.g. "KXBTC-25MAR31-T100000"
#   - action:     "buy" | "sell"
#   - side:       "yes" | "no"
#   - order_type: "limit" | "market"
#   - count:      int (number of contracts)
#   - yes_price:  int (CENTS: 1-99)  ← float prices from scanner MUST be converted
#   - no_price:   int (CENTS: 1-99, auto-derived as 100-yes_price if omitted)
#
# Conversion: yes_price = int(round(leg_price_float * 100))
order = await kalshi_client.create_order(
    ticker=pair.kalshi_ticker,
    action="buy",
    side="yes",       # or "no"
    order_type="limit",
    count=leg["contracts"],
    yes_price=int(round(leg["price"] * 100)),
)
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Manual pair registration at startup | ARB-01: auto-discovery via `MarketCorrelationNetwork` | Enables zero-config scanner operation |
| NO price always derived as `1 - yes_ask` | ARB-04: real CLOB orderbook for independent NO token | Only needed when NO token trades separately |
| No staleness protection | ARB-03: configurable `staleness_threshold_s` (default 5s) | Prevents ghost arb on stale quotes |
| Arb detection only, no execution | ARB-02: dual-platform order placement via `asyncio.gather` | Records order IDs; recommends shadow mode flag |

**Regarding Polymarket execution auth:** The project's current `PolymarketClient._build_auth_headers()` uses HMAC-SHA256 (`POLY-API-KEY`, `POLY-TIMESTAMP`, `POLY-SIGNATURE`). The documentation confirms this is L2 auth, which is sufficient for reading data. Order placement requires L1 (EIP-712 signed order struct) plus L2 headers. This is a non-trivial addition. The REQUIREMENTS.md explicitly defers full Polymarket live execution to v3 (POLY-EXEC-01/02/03). ARB-02 should be implemented as a `shadow_execute_arb()` that logs intents without actually signing, consistent with the project's execution philosophy.

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — validation section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project-wide) |
| Config file | `pyproject.toml` (root or per-package) |
| Quick run command | `uv run pytest packages/analytics/tests/ -x -q` |
| Full suite command | `uv run pytest packages/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARB-01 | `discover_and_wire()` fetches markets, matches pairs, calls `register_pair()` and `wire()` | unit (mocked clients) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_discover_and_wire -x` | Wave 0 |
| ARB-01 | Auto-discovery produces correct `MarketPair.polymarket_no_token` from Gamma token array | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_extraction -x` | Wave 0 |
| ARB-02 | `asyncio.gather()` fires both order placements simultaneously | unit (mocked order clients) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_dual_order_placement -x` | Wave 0 |
| ARB-03 | `_check_pair()` returns early + logs warning when Kalshi data stale | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_kalshi -x` | Wave 0 |
| ARB-03 | `_check_pair()` returns early + logs warning when Poly data stale | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_poly -x` | Wave 0 |
| ARB-03 | `_check_pair()` does NOT fire staleness guard when both timestamps are 0.0 (uninitialized) | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_uninit -x` | Wave 0 |
| ARB-04 | `poly_no_ask` uses real orderbook ask when `polymarket_no_token` is None | unit (mocked get_orderbook) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_real_ask -x` | Wave 0 |
| ARB-04 | `poly_no_ask` uses `1 - yes_ask` derivation when NO token orderbook returns no liquidity | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_fallback -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/analytics/tests/test_realtime_scanner.py -x -q`
- **Per wave merge:** `uv run pytest packages/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/analytics/tests/test_realtime_scanner.py` — covers all ARB-01 through ARB-04 scenarios (does not exist yet)
- [ ] `packages/analytics/tests/__init__.py` — may be needed if tests/ dir doesn't exist
- [ ] `packages/data_feeds/src/sharpedge_feeds/polymarket_clob_orders.py` — stub module for ARB-02 (Wave 0 stub only)

---

## Open Questions

1. **Does Phase 15 ARB-02 require real Polymarket execution or shadow mode?**
   - What we know: `REQUIREMENTS.md` lists `POLY-EXEC-01` through `POLY-EXEC-03` as deferred to v3; ARB-02 success criterion says "places limit orders … and records both order IDs"
   - What's unclear: whether "records order IDs" means real order submission or shadow-mode logging
   - Recommendation: Implement as shadow mode with `ENABLE_POLY_EXECUTION` flag (same pattern as Phase 11/12). This satisfies "records order IDs" (shadow IDs) without requiring Polygon private key management.

2. **Kalshi market `title` vs `subtitle` for Jaccard matching quality**
   - What we know: `KalshiMarket.title` and `subtitle` both exist; `PolymarketMarket.question` is the full question text
   - What's unclear: whether `title` alone gives sufficient word overlap for reliable matching
   - Recommendation: Use `f"{km.title} {km.subtitle}"` as the full question text when constructing `MarketOutcome.question` for Kalshi markets.

3. **Pagination for large market catalogs**
   - What we know: `KalshiClient.get_markets()` has `cursor` pagination; `PolymarketClient.get_markets()` has `offset` pagination; both default to `limit=100`
   - What's unclear: How many open markets exist at any given time (100 may not be enough)
   - Recommendation: `discover_and_wire()` should loop with pagination until all markets are fetched; use `limit=200` per page to reduce round-trips.

---

## Sources

### Primary (HIGH confidence)

- Direct code read: `packages/analytics/src/sharpedge_analytics/prediction_markets/realtime_scanner.py` — `MarketPair`, `RealtimeArbScanner`, tick handlers, `_check_pair()`, `_evaluate()`
- Direct code read: `packages/analytics/src/sharpedge_analytics/prediction_markets/arbitrage.py` — `MarketCorrelationNetwork`, `_calculate_similarity()` (Jaccard at 0.7), `get_multi_platform_events()`
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` — `KalshiClient.create_order()` full signature and price-in-cents constraint
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/polymarket_client.py` — `PolymarketClient.get_orderbook()`, `_parse_market()` token array parsing
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/kalshi_stream.py` — `KalshiStreamClient`, `KalshiTick` fields
- Direct code read: `packages/data_feeds/src/sharpedge_feeds/polymarket_stream.py` — `PolymarketStreamClient`, `PolyTick` fields, `_best_ask()` helper
- Direct code read: `packages/analytics/src/sharpedge_analytics/prediction_markets/fees.py` — `Platform` enum values
- py-clob-client source (GitHub): `endpoints.py` — `POST_ORDER = "/order"`, `GET_ORDER_BOOK = "/book"`

### Secondary (MEDIUM confidence)

- Polymarket CLOB documentation (docs.polymarket.com/developers/CLOB/orders/create-order): Order payload fields (`tokenID`, `price`, `size`, `side`, expiration, nonce), response schema (`orderID`, `status`, `success`), `GTC`/`GTD`/`FOK`/`FAK` order types
- Polymarket L2 methods doc (docs.polymarket.com/developers/CLOB/clients/methods-l2): `createAndPostOrder()` signature, L1 + L2 auth requirement for order placement
- py-clob-client README/source (github.com/Polymarket/py-clob-client): Confirmed L1 auth (`assert_level_1_auth`) required for `create_order`; L2 required for `post_order`

### Tertiary (LOW confidence)

- None — all claims verified against code or official docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries read directly from source
- Architecture: HIGH — all extension points verified in existing code; patterns follow existing conventions
- Polymarket CLOB API: MEDIUM — verified against official docs and py-clob-client source, but EIP-712 signing flow not tested against live API
- Pitfalls: HIGH — derived from direct inspection of existing code (timestamp initialization, token ordering, price unit conversion)

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (Polymarket CLOB API is relatively stable; Kalshi API very stable)
