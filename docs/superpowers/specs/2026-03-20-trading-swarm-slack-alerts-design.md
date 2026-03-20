# Trading Swarm Slack Alerts — Design Spec

## Goal

Surface critical trading swarm events to a Slack channel so the operator knows when the system requires attention or reaches the live-trading promotion threshold — without requiring manual log inspection.

## Scope

Critical events only (not per-trade noise):
1. Promotion gate **passed** — system is ready to switch to live trading
2. Promotion gate **daily status** — progress update while still in paper mode
3. Circuit breaker triggered — consecutive-loss limit hit, trading halted
4. Auto-learning paused — post-mortem agent exhausted auto-adjustments, manual review needed

## Architecture

A single thin module `alerts/slack.py` inside the `trading_swarm` package. No new services, no new packages, no network dependencies beyond `httpx` (already present).

```
packages/trading_swarm/src/sharpedge_trading/
  alerts/
    __init__.py      (empty)
    slack.py         (send_alert function)
```

The module is called directly at the four trigger points in existing agents. It is opt-in: if `SLACK_WEBHOOK_URL` is not set, all calls are silent no-ops logged at DEBUG level.

## Components

### `alerts/slack.py`

```python
def send_alert(text: str) -> None
```

- Reads `SLACK_WEBHOOK_URL` from environment at call time (not at import)
- If unset or empty: logs at DEBUG level and returns immediately
- POSTs `{"text": text}` as JSON to the webhook URL via `httpx` (sync, short timeout ~5s)
- On any HTTP or network error: logs a WARNING and returns (never raises)
- Runs in a thread executor so it does not block the asyncio event loop when called from async contexts

### Trigger points

| Location | File | Event | Message format |
|---|---|---|---|
| Daily gate check task | `daemon.py` | Gate passed | `"PROMOTION GATE PASSED ✅ — SharpEdge is ready for live trading.\n<check details>"` |
| Daily gate check task | `daemon.py` | Gate not yet passed | `"Daily gate check: X/8 checks passing.\n  [PASS] min_trades: trades=12 (need ≥50)\n  [FAIL] ..."` — one line per check with `[PASS]`/`[FAIL]` prefix and the reason string from `PromotionGateResult.checks` |
| Circuit breaker | `risk_agent.py` | Consecutive loss limit hit | `"CIRCUIT BREAKER triggered — trading halted after N consecutive losses."` |
| Auto-learning pause | `post_mortem_agent.py` | 5 consecutive auto-adjustments | `"Auto-learning paused after 5 adjustments — manual review of trading config required."` |

### Daily gate check task

A new `asyncio` task added to `run_daemon()` alongside the existing agents:

```python
tg.create_task(_run_gate_check(config), name="gate_check")
```

Signature: `async def _run_gate_check(config: TradingConfig) -> None`

`_run_gate_check` runs `check_promotion_gate()` once per 24 hours (`asyncio.sleep(86400)`). On each check:
- If gate **passes**: sends the "PASSED" alert once, sets a module-level `_gate_announced` flag, then suppresses further "PASSED" alerts on subsequent checks
- If gate **not yet passed**: sends the daily status summary

**Daemon restart behavior**: `_gate_announced` is module-level and resets on restart. If the gate was previously passed and the daemon restarts, the first check will detect the gate is still passing (Supabase data is unchanged) and fire the alert again. This is acceptable — a duplicate "PASSED" alert on restart is a low-cost false positive. The implementer must not suppress it via external persistence to keep the implementation simple.

## Configuration

One new env var:

| Var | Required | Default | Purpose |
|---|---|---|---|
| `SLACK_WEBHOOK_URL` | No | `""` | Incoming webhook URL from Slack app. Empty = alerts disabled. |

Added to `docker-compose.yml` as an optional env var with an empty default so existing deployments are unaffected.

## Error Handling

- Missing `SLACK_WEBHOOK_URL`: silent no-op (DEBUG log only)
- Network timeout or HTTP error: WARNING log, execution continues normally
- Slack rate limits (HTTP 429): logged as WARNING, no retry (non-critical path)
- Never raises an exception that could affect the trading pipeline

## Testing

- Unit test for `send_alert`: mock `httpx.post`, assert payload shape and that missing URL is a no-op
- Unit test for daily gate check loop: mock `check_promotion_gate()`, assert alert fires on first pass and not on subsequent passes
- No integration test against real Slack (webhook URL is a secret)

## Out of Scope

- Per-trade alerts
- Email or push notification channels (can be added to `alerts/` later)
- Alert deduplication / rate limiting beyond what Slack's API enforces
- Alert history persistence in Supabase
