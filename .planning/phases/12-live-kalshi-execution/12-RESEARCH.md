# Phase 12: Live Kalshi Execution - Research

**Researched:** 2026-03-17
**Domain:** Python async order execution, CLOB order lifecycle, settlement ledger event sourcing
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXEC-03 | Operator can enable live Kalshi CLOB order submission via `ENABLE_KALSHI_EXECUTION` env flag | `ShadowExecutionEngine` already reads this env var; Phase 12 adds KalshiClient branch inside the existing `process_intent` flow |
| EXEC-05 | System polls Kalshi order status after submission and records fills and cancellations in SettlementLedger | `KalshiClient.get_open_orders()` returns `KalshiOrder` with `status`; `SettlementLedger.append(LedgerEntry)` is the write path |
</phase_requirements>

---

## Summary

Phase 12 extends the already-implemented `ShadowExecutionEngine` with a live branch activated by `ENABLE_KALSHI_EXECUTION=true`. When the flag is set, `process_intent` calls `KalshiClient.create_order()` after the exposure guards pass, writes an order-submission `LedgerEntry` to `SettlementLedger`, then enters a poll loop calling `KalshiClient.get_open_orders()` until the order status is terminal (`"executed"` or `"canceled"`). Each terminal event produces a second `LedgerEntry` — `FILL` with fill quantity/price on execution, `ADJUSTMENT` (or a custom notes field) with reason on cancellation.

The critical constraint is that `KalshiClient` has no single-order fetch (`GET /portfolio/orders/{id}`) wired in the current implementation; the available polling mechanism is `get_open_orders(ticker=...)` filtered client-side by `order_id`. Phase 12 must either add a `get_order(order_id)` method to `KalshiClient` or poll via `get_open_orders`. Adding `get_order` is cleaner and mirrors the Kalshi API v2 endpoint `GET /trade-api/v2/portfolio/orders/{order_id}`.

The `SettlementLedger` from Phase 6 is append-only, takes `LedgerEntry` dataclasses with strict UTC-aware timestamp enforcement, and maps naturally to fill and cancellation events. No schema changes are needed — the existing `"FILL"`, `"ADJUSTMENT"`, and `"POSITION_OPENED"` event types cover all Phase 12 write operations. The `notes` field on `LedgerEntry` carries free-text cancellation reason.

**Primary recommendation:** Add `get_order(order_id)` to `KalshiClient`, introduce a `LiveOrderPoller` async helper in `execution_engine.py`, and extend `ShadowExecutionEngine` with an optional `KalshiClient` dependency injected at construction time — keeping shadow mode unchanged when the client is absent.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sharpedge-feeds` (KalshiClient) | workspace | CLOB order submission and status polling | Already the project's authenticated Kalshi transport; RSA-PSS signing implemented |
| `sharpedge-venue-adapters` (SettlementLedger, LedgerEntry) | workspace | Append-only write path for fills and cancellations | Phase 6 artifact; already Supabase-wired and tested |
| `asyncio` (stdlib) | 3.12+ | Poll loop sleep between status checks | No extra dep; matches async pattern throughout KalshiClient |
| `pytest-asyncio` | already in test infra | Async test support | `asyncio_mode = "auto"` already set in `pyproject.toml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock.AsyncMock` | stdlib | Mock `KalshiClient` in tests | Any test exercising the live path without real credentials |
| `uuid` (stdlib) | 3.12+ | Generate `position_lot_id` for linking submission + fill entries | Needed to correlate the two `LedgerEntry` rows for one order |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `get_open_orders()` filtered by order_id | Add `get_order(order_id)` | `get_open_orders` only returns status="resting" orders — a filled order disappears, making fill detection impossible without a dedicated single-order endpoint |
| Polling loop in `process_intent` synchronously | Background `asyncio.Task` | Synchronous blocking poll would stall the engine; background task is more correct but adds cancellation complexity — for v2.0, inline async poll with configurable max_attempts is simpler and sufficient |

**Installation:** No new packages. All dependencies are already declared in `packages/venue_adapters/pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

All changes stay within the existing package:

```
packages/venue_adapters/src/sharpedge_venue_adapters/
├── execution_engine.py       # Extend: add LiveOrderPoller, extend ShadowExecutionEngine
└── (no new files needed)

packages/data_feeds/src/sharpedge_feeds/
└── kalshi_client.py          # Extend: add get_order(order_id) method

packages/venue_adapters/tests/
├── test_shadow_execution_engine.py   # Existing — no changes needed
└── test_live_execution_engine.py     # New: RED stubs for EXEC-03 + EXEC-05 (Wave 0)
```

### Pattern 1: Flag-Branched Engine Construction

`ShadowExecutionEngine` gains an optional `kalshi_client: KalshiClient | None` parameter. Shadow mode = client is `None`. Live mode = client injected.

```python
# Conceptual — execution_engine.py extension
class ShadowExecutionEngine:
    def __init__(
        self,
        max_market_exposure: float,
        max_day_exposure: float,
        kalshi_client=None,           # None = shadow mode
        settlement_ledger=None,       # None = shadow mode (no SettlementLedger writes)
        poll_interval_seconds: float = 5.0,
        poll_max_attempts: int = 60,
    ) -> None: ...

    @classmethod
    def from_env(cls) -> "ShadowExecutionEngine":
        # Reads ENABLE_KALSHI_EXECUTION, KALSHI_API_KEY, KALSHI_PRIVATE_KEY_PATH
        # Returns engine with KalshiClient injected if flag is true
        ...
```

**When to use:** Always. Shadow mode stays the default; live mode requires explicit `ENABLE_KALSHI_EXECUTION=true` plus credentials.

### Pattern 2: LiveOrderPoller

A small async helper that drives the poll loop independently of the engine's guard logic:

```python
# Conceptual — internal to execution_engine.py
class LiveOrderPoller:
    """Polls Kalshi order status until terminal, then writes to SettlementLedger."""

    async def poll_until_terminal(
        self,
        order_id: str,
        ticker: str,
        position_lot_id: str,
        submitted_price_cents: int,
        contracts: int,
        settlement_ledger: SettlementLedger,
        kalshi_client: KalshiClient,
        interval_s: float,
        max_attempts: int,
    ) -> LedgerEntry | None:
        """Returns the final LedgerEntry written, or None if max_attempts exceeded."""
        ...
```

**When to use:** Called after a successful `create_order()` response.

### Pattern 3: Linking Submission and Fill via `position_lot_id`

Both the submission entry (`POSITION_OPENED`) and the fill entry (`FILL`) use the same `position_lot_id` UUID. This allows `SettlementLedger.replay(position_lot_id)` to compute net PnL across both rows.

```python
import uuid
lot_id = str(uuid.uuid4())

# On submission
ledger.append(LedgerEntry(
    entry_id=None,
    event_type="POSITION_OPENED",
    venue_id="kalshi",
    market_id=intent.market_id,
    position_lot_id=lot_id,
    amount_usdc=-stake_usd,       # debit: capital deployed
    fee_component=0.0,
    rebate_component=0.0,
    price_at_event=submitted_price_cents / 100.0,
    occurred_at=datetime.now(timezone.utc),
    recorded_at=datetime.now(timezone.utc),
    notes=f"order_id={kalshi_order.order_id}",
))

# On fill
ledger.append(LedgerEntry(
    entry_id=None,
    event_type="FILL",
    venue_id="kalshi",
    market_id=intent.market_id,
    position_lot_id=lot_id,
    amount_usdc=0.0,              # fill credit comes at settlement
    fee_component=0.0,
    rebate_component=0.0,
    price_at_event=fill_price_cents / 100.0,
    occurred_at=datetime.now(timezone.utc),
    recorded_at=datetime.now(timezone.utc),
    notes=f"order_id={kalshi_order.order_id} filled qty={fill_qty}",
))

# On cancellation
ledger.append(LedgerEntry(
    event_type="ADJUSTMENT",
    ...
    amount_usdc=+stake_usd,       # credit back: capital returned
    notes=f"order_id={order_id} canceled reason={reason}",
))
```

### Pattern 4: `get_order` Addition to KalshiClient

The Kalshi v2 API exposes `GET /trade-api/v2/portfolio/orders/{order_id}`. This must be added to `KalshiClient`:

```python
async def get_order(self, order_id: str) -> KalshiOrder | None:
    path = f"/trade-api/v2/portfolio/orders/{order_id}"
    response = await self._client.get(
        path, headers=self._auth_headers("GET", path)
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    return self._parse_order(data.get("order", {}))
```

**Why this matters:** `get_open_orders()` only returns orders with `status="resting"`. Once an order is filled (`"executed"`) or cancelled (`"canceled"`), it will not appear in `get_open_orders()`. Without `get_order()`, the poller cannot detect fills — it would just see the order disappear and have no way to distinguish fill from cancellation.

### Anti-Patterns to Avoid

- **Polling inside `process_intent` synchronously:** Blocks the event loop for potentially minutes. Use `await asyncio.sleep(interval_s)` in an async method.
- **Re-implementing the exposure commit for live path:** Live path must use the same `MarketExposureGuard.commit()` and `DayExposureGuard.commit()` calls already in place — do not duplicate.
- **Writing to `ShadowLedger` AND `SettlementLedger` in live mode:** In live mode, `ShadowLedger` should still receive its `ShadowLedgerEntry` (signal log) but the financial record goes only to `SettlementLedger`.
- **Hardcoding poll interval:** Always read from constructor param with env-var fallback so tests can set `poll_interval_seconds=0.0`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSA-PSS request signing | Custom signer | `KalshiClient._auth_headers()` | Already implemented; cryptography library handles edge cases |
| Append-only financial event store | Custom dict/file store | `SettlementLedger.append(LedgerEntry)` | Phase 6 artifact with Supabase persistence, UTC enforcement, and deterministic replay |
| Order status parsing | Custom status string logic | `KalshiOrder.status` from `_parse_order()` | Already normalizes API response to `"resting"/"canceled"/"executed"/"pending"` |
| Position lot correlation | Custom ID scheme | `uuid.uuid4()` as `position_lot_id` | Standard UUID links submission + fill entries for `replay_position_pnl()` |

---

## Common Pitfalls

### Pitfall 1: `get_open_orders` Does Not Return Filled/Cancelled Orders
**What goes wrong:** Poller calls `get_open_orders(ticker=...)` in a loop, order gets filled, order vanishes from the list, poller times out and writes no fill entry.
**Why it happens:** Kalshi's `GET /portfolio/orders?status=resting` only returns resting orders. Filled orders have `status="executed"` and are absent.
**How to avoid:** Add `get_order(order_id)` to `KalshiClient` and use it in the poll loop. Check `order.status` directly.
**Warning signs:** Tests where mock `get_open_orders` returns empty list after fill — poller should write `FILL` entry, not timeout.

### Pitfall 2: Naive Datetime in `LedgerEntry`
**What goes wrong:** `LedgerEntry.__post_init__` raises `ValueError` with "must be UTC-aware" if `occurred_at` or `recorded_at` is timezone-naive.
**Why it happens:** Forgetting `timezone.utc` when constructing `datetime.now()` or datetime literals.
**How to avoid:** Always use `datetime.now(timezone.utc)` — same pattern already used throughout Phase 11.

### Pitfall 3: Live Path Bypasses Exposure Guards
**What goes wrong:** Live `create_order()` is called before checking guards, or guards are checked but not committed, leading to over-exposure.
**Why it happens:** Temptation to short-circuit for the live path. The existing `process_intent` guard sequence must run first.
**How to avoid:** Live branch must be entered ONLY after both guards pass and both `commit()` calls are made — i.e., after the `ShadowLedgerEntry` is written in the current implementation. The `create_order()` call follows, not precedes, the guard commit.

### Pitfall 4: Poll Loop Runs in CI Against Real Kalshi
**What goes wrong:** Test accidentally imports real `KalshiClient` and polls live API, causing flaky/slow CI.
**Why it happens:** Missing mock injection in tests.
**How to avoid:** All tests for the live path inject `AsyncMock` for `KalshiClient`. Never read `KALSHI_API_KEY` from env in tests — always inject a mock client.

### Pitfall 5: `KalshiOrder.count` Is Contracts, Not USD
**What goes wrong:** Fill entry records `amount_usdc` as raw `count` (integer contracts), not dollar value.
**Why it happens:** `KalshiOrder.count` is number of contracts; `yes_price` is cents (0-99). USD stake = `(count * yes_price) / 100`.
**How to avoid:** `amount_usdc = (order.count * order.yes_price) / 100.0` for the fill entry.

### Pitfall 6: Missing `get_order` Returns `None` Permanently
**What goes wrong:** If `get_order` returns `None` (404), poller treats it as a not-found case forever, spinning until `max_attempts`.
**Why it happens:** Order ID is valid but briefly unavailable, or order was immediately rejected.
**How to avoid:** Distinguish `None` (not found / possibly still processing) from a terminal status. After a configurable number of consecutive `None` responses, log and write an `ADJUSTMENT` entry with `notes="order not found after submission"`.

---

## Code Examples

Verified patterns from existing codebase:

### Writing a FILL Entry to SettlementLedger
```python
# Source: packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py
from sharpedge_venue_adapters.ledger import LedgerEntry, SettlementLedger
from datetime import datetime, timezone

ledger = SettlementLedger()
entry = ledger.append(LedgerEntry(
    entry_id=None,
    event_type="FILL",
    venue_id="kalshi",
    market_id="KXBTC-25MAR31-T100000",
    position_lot_id="some-uuid",
    amount_usdc=0.0,
    fee_component=0.0,
    rebate_component=0.0,
    price_at_event=0.55,
    occurred_at=datetime.now(timezone.utc),
    recorded_at=datetime.now(timezone.utc),
    notes="order_id=abc123 filled qty=5",
))
# entry.entry_id is set (from in-memory counter or Supabase)
```

### Creating a Kalshi Order
```python
# Source: packages/data_feeds/src/sharpedge_feeds/kalshi_client.py
order: KalshiOrder = await client.create_order(
    ticker="KXBTC-25MAR31-T100000",
    action="buy",
    side="yes",
    order_type="limit",
    count=5,
    yes_price=55,   # 55 cents
)
# order.order_id, order.status ("resting" or "pending")
```

### Mocking KalshiClient in Tests
```python
# Source: pattern from conftest.py + unittest.mock.AsyncMock
from unittest.mock import AsyncMock, MagicMock
from sharpedge_feeds.kalshi_client import KalshiOrder
from datetime import datetime, timezone

mock_client = AsyncMock()
mock_client.create_order.return_value = KalshiOrder(
    order_id="test-order-123",
    ticker="KXBTC",
    action="buy",
    side="yes",
    type="limit",
    count=5,
    yes_price=55,
    no_price=45,
    status="resting",
    created_time=datetime.now(timezone.utc),
)
mock_client.get_order.return_value = KalshiOrder(
    order_id="test-order-123",
    ticker="KXBTC",
    action="buy",
    side="yes",
    type="limit",
    count=5,
    yes_price=55,
    no_price=45,
    status="executed",   # terminal state
    created_time=datetime.now(timezone.utc),
)
```

### KalshiOrder Status Terminal Check
```python
# Status values defined in KalshiOrder.status docstring:
# "resting"  — order is live in the CLOB, awaiting fill
# "pending"  — order submitted but not yet acknowledged
# "executed" — fully or partially filled (terminal for poll exit)
# "canceled" — order was cancelled (terminal for poll exit)

TERMINAL_STATUSES = {"executed", "canceled"}

def is_terminal(order: KalshiOrder) -> bool:
    return order.status in TERMINAL_STATUSES
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shadow-only engine in Phase 11 | Engine extended with live branch in Phase 12 | This phase | `KalshiClient` becomes a dependency of execution_engine |
| No `get_order` method on `KalshiClient` | Add `get_order(order_id)` | This phase | Enables single-order status poll — required for fill detection |
| `ShadowLedger` only | `ShadowLedger` + `SettlementLedger` in live mode | This phase | Financial events recorded with deterministic replay capability |

---

## Open Questions

1. **Fill quantity vs. partial fills**
   - What we know: `KalshiOrder.count` is the original order size; there is no `filled_count` field in the current `KalshiOrder` dataclass
   - What's unclear: Does the Kalshi API `GET /portfolio/orders/{id}` response include a `filled_count` or `remaining_count` field for partial fills?
   - Recommendation: Extend `KalshiOrder` with `filled_count: int = 0` and `remaining_count: int = 0` when adding `get_order()`. If the API returns these, use them; if not, treat `status="executed"` as full fill. For v2.0 scope (EXEC-05), full-fill tracking is sufficient — partial fill tracking is deferred.

2. **`from_env()` credentials loading for live mode**
   - What we know: `KalshiConfig` requires `api_key` (UUID) and `private_key_pem` (PEM string). The STATE.md todo notes "Verify live Kalshi CLOB order submission credentials before Phase 12 starts."
   - What's unclear: Env var names for these credentials are not standardized in the current codebase
   - Recommendation: Define `KALSHI_API_KEY` and `KALSHI_PRIVATE_KEY_PEM` as the standard env var names. `from_env()` on `ShadowExecutionEngine` reads these when `ENABLE_KALSHI_EXECUTION=true`.

3. **Cancellation reason field**
   - What we know: `KalshiClient.cancel_order()` returns `dict` with `"order"` details and `"reduced_by"` count; `KalshiOrder` has no `cancel_reason` field
   - What's unclear: Does the Kalshi API return a cancellation reason in the order object?
   - Recommendation: Use `notes` field on `LedgerEntry` for the reason string (e.g., `"canceled by operator"` vs. `"canceled by exchange"`). The success criterion says "reason field" — `notes` on `LedgerEntry` satisfies this without schema changes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (asyncio_mode = "auto") |
| Config file | `packages/venue_adapters/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py -x` |
| Full suite command | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-03 | `ENABLE_KALSHI_EXECUTION=true` triggers `create_order()` and writes order ID to SettlementLedger | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_live_mode_calls_create_order -x` | Wave 0 |
| EXEC-03 | Shadow mode unchanged — no `create_order()` call when flag absent | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_shadow_mode_unchanged -x` | Wave 0 |
| EXEC-05 | Poller detects `status="executed"` and writes FILL LedgerEntry with qty/price/timestamp | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_fill_event_recorded -x` | Wave 0 |
| EXEC-05 | Poller detects `status="canceled"` and writes ADJUSTMENT LedgerEntry with reason in notes | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_cancel_event_recorded -x` | Wave 0 |
| EXEC-03 | Exposure guards still enforced in live mode before `create_order()` is called | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_live_mode_exposure_guard_still_applied -x` | Wave 0 |
| EXEC-05 | `get_order` returns terminal status on first poll — FILL written, no unnecessary retries | unit | `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py::test_fill_on_first_poll -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/test_live_execution_engine.py -x`
- **Per wave merge:** `uv run --package sharpedge-venue-adapters pytest packages/venue_adapters/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/venue_adapters/tests/test_live_execution_engine.py` — covers EXEC-03 and EXEC-05 (new file, all RED stubs)
- [ ] `get_order(order_id)` method on `KalshiClient` — required for poll loop; must be added to `kalshi_client.py` before tests can exercise the fill detection path

---

## Sources

### Primary (HIGH confidence)
- `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` — `SettlementLedger`, `LedgerEntry` fields, event types, append API, UTC enforcement
- `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` — `ShadowExecutionEngine`, `ShadowLedger`, guard pattern, `from_env()` classmethod
- `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` — `KalshiOrder` fields, `create_order()` signature, `get_open_orders()` filter, `cancel_order()` return type, `KalshiOrder.status` values
- `packages/venue_adapters/pyproject.toml` — pytest config, asyncio_mode, package dependencies

### Secondary (MEDIUM confidence)
- Kalshi API docs pattern inferred from existing `kalshi_client.py` implementation: `GET /trade-api/v2/portfolio/orders/{order_id}` exists as standard REST endpoint (same path structure as `cancel_order` DELETE)
- `KalshiOrder.status` values `"resting"`, `"canceled"`, `"executed"`, `"pending"` — defined in `kalshi_client.py` docstring comment at line 103

### Tertiary (LOW confidence)
- Kalshi API partial fill fields (`filled_count`, `remaining_count`) — inferred from standard CLOB exchange patterns; not verified from live Kalshi API response schema

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed present in workspace
- Architecture: HIGH — `ShadowExecutionEngine` extension pattern is unambiguous; `SettlementLedger` interface fully inspected
- `get_order` necessity: HIGH — `get_open_orders` only returns resting orders, confirmed from `kalshi_client.py` line 295 (`params: {"status": "resting"}`)
- Partial fill fields: LOW — `KalshiOrder` dataclass has no `filled_count`; existence of this field in API response not verified

**Research date:** 2026-03-17
**Valid until:** 2026-04-16 (stable internal codebase; Kalshi API v2 is stable)
