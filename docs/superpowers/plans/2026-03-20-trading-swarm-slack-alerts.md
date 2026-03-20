# Trading Swarm Slack Alerts — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Slack webhook alerting for four critical trading swarm events: circuit breaker triggered, auto-learning paused, promotion gate daily status, and promotion gate passed.

**Architecture:** A thin `alerts/slack.py` module inside `trading_swarm` fires a daemon thread per alert to POST to `SLACK_WEBHOOK_URL` without blocking the asyncio event loop. Four call sites are added to existing agents. A new `_run_gate_check` asyncio task runs daily.

**Tech Stack:** Python 3.12, `httpx` (already in pyproject.toml), `threading` (stdlib), `asyncio` (stdlib)

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Create | `packages/trading_swarm/src/sharpedge_trading/alerts/__init__.py` | Empty package init |
| Create | `packages/trading_swarm/src/sharpedge_trading/alerts/slack.py` | `send_alert()` — HTTP POST to Slack webhook in daemon thread |
| Modify | `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py:54-56` | Alert on circuit breaker (consecutive losses) |
| Modify | `packages/trading_swarm/src/sharpedge_trading/agents/post_mortem_agent.py:139-145` | Alert on auto-learning pause |
| Modify | `packages/trading_swarm/src/sharpedge_trading/daemon.py` | Add `_run_gate_check` task + wire into TaskGroup |
| Modify | `docker-compose.yml` | Add `SLACK_WEBHOOK_URL` env var |
| Create | `packages/trading_swarm/tests/test_slack_alerts.py` | Unit tests for `send_alert` |

---

## Task 1: Create `alerts/slack.py`

**Files:**
- Create: `packages/trading_swarm/src/sharpedge_trading/alerts/__init__.py`
- Create: `packages/trading_swarm/src/sharpedge_trading/alerts/slack.py`
- Test: `packages/trading_swarm/tests/test_slack_alerts.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/trading_swarm/tests/test_slack_alerts.py
"""Tests for slack alert module."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_trading.alerts.slack import send_alert


def test_send_alert_no_op_when_url_missing(monkeypatch):
    """send_alert is a silent no-op when SLACK_WEBHOOK_URL is not set."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    with patch("httpx.post") as mock_post:
        send_alert("test message")
        time.sleep(0.1)  # give daemon thread time to run
        mock_post.assert_not_called()


def test_send_alert_posts_to_webhook(monkeypatch):
    """send_alert POSTs JSON payload to SLACK_WEBHOOK_URL."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    posted_calls = []

    def fake_post(url, json, timeout):
        posted_calls.append((url, json, timeout))
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        return resp

    with patch("httpx.post", side_effect=fake_post):
        send_alert("hello world")
        # Wait for daemon thread
        for _ in range(20):
            if posted_calls:
                break
            time.sleep(0.05)

    assert len(posted_calls) == 1
    url, payload, timeout = posted_calls[0]
    assert url == "https://hooks.slack.com/test"
    assert payload == {"text": "hello world"}
    assert timeout == 5.0


def test_send_alert_silent_on_http_error(monkeypatch, caplog):
    """send_alert logs a warning but does not raise on HTTP error."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

    def raise_error(url, json, timeout):
        raise Exception("connection refused")

    with patch("httpx.post", side_effect=raise_error):
        send_alert("test")
        time.sleep(0.1)
    # No exception propagated — test passes if we reach here
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/revph/sharpedge
uv run --directory packages/trading_swarm pytest tests/test_slack_alerts.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'sharpedge_trading.alerts'`

- [ ] **Step 3: Create the empty package init**

```bash
mkdir -p packages/trading_swarm/src/sharpedge_trading/alerts
touch packages/trading_swarm/src/sharpedge_trading/alerts/__init__.py
```

- [ ] **Step 4: Write `alerts/slack.py`**

```python
# packages/trading_swarm/src/sharpedge_trading/alerts/slack.py
"""Slack Incoming Webhook alerter for critical trading swarm events.

Fires a daemon thread per alert so the asyncio event loop is never blocked.
If SLACK_WEBHOOK_URL is unset, all calls are silent no-ops.
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0


def send_alert(text: str) -> None:
    """Post `text` to the Slack webhook in a daemon thread.

    Returns immediately. Never raises.
    """
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        logger.debug("SLACK_WEBHOOK_URL not set — alert suppressed: %s", text[:60])
        return

    def _post() -> None:
        try:
            import httpx
            resp = httpx.post(url, json={"text": text}, timeout=_TIMEOUT)
            resp.raise_for_status()
            logger.debug("Slack alert sent: %s", text[:60])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack alert failed: %s", exc)

    t = threading.Thread(target=_post, daemon=True)
    t.start()
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run --directory packages/trading_swarm pytest tests/test_slack_alerts.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/alerts/ packages/trading_swarm/tests/test_slack_alerts.py
git commit -m "feat(alerts): add Slack webhook alerter module"
```

---

## Task 2: Add `SLACK_WEBHOOK_URL` to docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add env var to the trading-swarm service**

In `docker-compose.yml`, under the `trading-swarm` → `environment` block, add:

```yaml
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL:-}
```

The full environment block should look like:

```yaml
    environment:
      TRADING_MODE: ${TRADING_MODE:-paper}
      MODEL_DIR: /data/models/pm
      PAPER_BANKROLL: ${PAPER_BANKROLL:-10000}
      LIVE_BANKROLL: ${LIVE_BANKROLL:-2000}
      SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL:-}
```

- [ ] **Step 2: Verify docker-compose is valid**

```bash
docker compose config --quiet && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: pass SLACK_WEBHOOK_URL from .env to trading-swarm container"
```

---

## Task 3: Circuit breaker alert in `risk_agent.py`

**Files:**
- Modify: `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py:1-14` (add import)
- Modify: `packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py:54-56` (add alert call)
- Test: `packages/trading_swarm/tests/test_risk_agent.py` (add one test)

- [ ] **Step 1: Read the existing risk_agent test to understand patterns**

```bash
head -60 packages/trading_swarm/tests/test_risk_agent.py
```

- [ ] **Step 2: Write the failing test**

Add to `packages/trading_swarm/tests/test_risk_agent.py`:

```python
def test_circuit_breaker_sends_slack_alert(monkeypatch):
    """Circuit breaker fires a Slack alert when consecutive losses reach 5."""
    from sharpedge_trading.agents import risk_agent
    from sharpedge_trading.agents.risk_agent import _breaker, check_circuit_breakers
    from sharpedge_trading.config import TradingConfig

    # Reset state
    _breaker.consecutive_losses = 4
    _breaker.paused_until = None

    alerts_sent = []
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig()
    with patch("sharpedge_trading.agents.risk_agent.get_bankroll", return_value=10000.0):
        ok, reason = check_circuit_breakers(config)

    assert not ok
    assert "consecutive" in reason
    assert len(alerts_sent) == 1
    assert "CIRCUIT BREAKER" in alerts_sent[0]
```

Note: add `from unittest.mock import patch` at the top of the test file if not already present.

- [ ] **Step 3: Run to confirm failure**

```bash
uv run --directory packages/trading_swarm pytest tests/test_risk_agent.py::test_circuit_breaker_sends_slack_alert -v
```

Expected: FAIL — `AssertionError: assert 0 == 1` (no alerts sent yet)

- [ ] **Step 4: Add import and alert call to `risk_agent.py`**

At the top of `risk_agent.py`, after the existing imports, add:

```python
from sharpedge_trading.alerts.slack import send_alert
```

In `check_circuit_breakers`, change the consecutive losses block from:

```python
    if _breaker.consecutive_losses >= 5:
        _breaker.paused_until = datetime.now(tz=timezone.utc) + timedelta(hours=4)
        return False, f"5 consecutive losses — pausing 4 hours"
```

to:

```python
    if _breaker.consecutive_losses >= 5:
        _breaker.paused_until = datetime.now(tz=timezone.utc) + timedelta(hours=4)
        send_alert(
            f"CIRCUIT BREAKER triggered — trading halted after "
            f"{_breaker.consecutive_losses} consecutive losses. "
            f"Pausing until {_breaker.paused_until.strftime('%Y-%m-%d %H:%M UTC')}."
        )
        return False, f"5 consecutive losses — pausing 4 hours"
```

- [ ] **Step 5: Run test to confirm pass**

```bash
uv run --directory packages/trading_swarm pytest tests/test_risk_agent.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/risk_agent.py packages/trading_swarm/tests/test_risk_agent.py
git commit -m "feat(alerts): Slack alert on circuit breaker trigger"
```

---

## Task 4: Auto-learning pause alert in `post_mortem_agent.py`

**Files:**
- Modify: `packages/trading_swarm/src/sharpedge_trading/agents/post_mortem_agent.py`
- Test: `packages/trading_swarm/tests/test_post_mortem_agent.py` (add one test)

- [ ] **Step 1: Write the failing test**

Add to `packages/trading_swarm/tests/test_post_mortem_agent.py`:

```python
def test_auto_learning_pause_sends_slack_alert(monkeypatch):
    """Auto-learning pause fires a Slack alert after 5 consecutive adjustments."""
    import sharpedge_trading.agents.post_mortem_agent as pm

    # Reset module state
    pm._auto_adjustment_count = 4
    pm._auto_learning_paused = False
    pm._loss_counts = {"model_error": 3}  # triggers model_error path

    alerts_sent = []
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    # Mock supabase so _update_config doesn't fail
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr("sharpedge_trading.agents.post_mortem_agent._get_supabase_client", lambda: mock_client)

    from sharpedge_trading.config import TradingConfig
    pm._apply_learning_update({"model_error_score": 1.0, "sizing_error_score": 0.0}, TradingConfig())

    assert len(alerts_sent) == 1
    assert "Auto-learning paused" in alerts_sent[0]
```

Note: add `from unittest.mock import MagicMock` at the top of the test file if not already present.

- [ ] **Step 2: Run to confirm failure**

```bash
uv run --directory packages/trading_swarm pytest tests/test_post_mortem_agent.py::test_auto_learning_pause_sends_slack_alert -v
```

Expected: FAIL

- [ ] **Step 3: Add import and alert call to `post_mortem_agent.py`**

After existing imports, add:

```python
from sharpedge_trading.alerts.slack import send_alert
```

In `_apply_learning_update`, change the auto-learning pause block from:

```python
        if _auto_adjustment_count >= _MAX_AUTO_ADJUSTMENTS:
            _auto_learning_paused = True
            _update_config(client, "auto_learning_paused", 1.0)
            logger.warning(
                "Auto-learning paused after %d consecutive adjustments — manual review required",
                _MAX_AUTO_ADJUSTMENTS,
            )
```

to:

```python
        if _auto_adjustment_count >= _MAX_AUTO_ADJUSTMENTS:
            _auto_learning_paused = True
            _update_config(client, "auto_learning_paused", 1.0)
            logger.warning(
                "Auto-learning paused after %d consecutive adjustments — manual review required",
                _MAX_AUTO_ADJUSTMENTS,
            )
            send_alert(
                f"Auto-learning paused after {_MAX_AUTO_ADJUSTMENTS} consecutive adjustments "
                f"— manual review of trading config required."
            )
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
uv run --directory packages/trading_swarm pytest tests/test_post_mortem_agent.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/agents/post_mortem_agent.py packages/trading_swarm/tests/test_post_mortem_agent.py
git commit -m "feat(alerts): Slack alert on auto-learning pause"
```

---

## Task 5: Daily gate check task in `daemon.py`

**Files:**
- Modify: `packages/trading_swarm/src/sharpedge_trading/daemon.py`
- Test: `packages/trading_swarm/tests/test_daemon.py` (add tests)

- [ ] **Step 1: Write the failing tests**

Add to `packages/trading_swarm/tests/test_daemon.py`:

```python
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from sharpedge_trading.daemon import PromotionGateResult, _run_gate_check
from sharpedge_trading.config import TradingConfig


@pytest.mark.asyncio
async def test_gate_check_sends_passed_alert_on_first_pass(monkeypatch):
    """Gate check sends PASSED alert when gate passes for the first time."""
    import sharpedge_trading.daemon as daemon_mod

    # Reset module flag
    daemon_mod._gate_announced = False

    passed_result = PromotionGateResult(
        passed=True,
        checks={"min_trades": (True, "trades=60 (need ≥50)")},
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig()
    # Run one check cycle only (cancel after first sleep)
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(alerts_sent) == 1
    assert "PASSED" in alerts_sent[0]


@pytest.mark.asyncio
async def test_gate_check_suppresses_duplicate_passed_alert(monkeypatch):
    """Gate check does NOT re-send PASSED alert if gate already announced."""
    import sharpedge_trading.daemon as daemon_mod

    # Simulate gate already announced in this process
    daemon_mod._gate_announced = True

    passed_result = PromotionGateResult(
        passed=True,
        checks={"min_trades": (True, "trades=60 (need ≥50)")},
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig()
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(alerts_sent) == 0  # no duplicate alert


@pytest.mark.asyncio
async def test_gate_check_sends_status_when_not_passed(monkeypatch):
    """Gate check sends daily status when gate has not yet passed."""
    import sharpedge_trading.daemon as daemon_mod

    daemon_mod._gate_announced = False

    not_passed_result = PromotionGateResult(
        passed=False,
        checks={
            "min_trades": (False, "trades=12 (need ≥50)"),
            "min_period": (True, "period=35.0d (need ≥30)"),
        },
    )
    alerts_sent = []

    monkeypatch.setattr("sharpedge_trading.daemon.check_promotion_gate", lambda: not_passed_result)
    monkeypatch.setattr(
        "sharpedge_trading.alerts.slack.send_alert",
        lambda text: alerts_sent.append(text),
    )

    config = TradingConfig()
    task = asyncio.create_task(_run_gate_check(config))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(alerts_sent) == 1
    assert "1/2" in alerts_sent[0]  # 1 of 2 checks passing
    assert "[FAIL] min_trades" in alerts_sent[0]
    assert "[PASS] min_period" in alerts_sent[0]
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run --directory packages/trading_swarm pytest tests/test_daemon.py -k "gate_check" -v
```

Expected: FAIL — `cannot import name '_run_gate_check'`

- [ ] **Step 3: Add `_run_gate_check` and module-level flag to `daemon.py`**

After the existing imports, add:

```python
from sharpedge_trading.alerts.slack import send_alert
```

After the existing `_GATE_CHECK_INTERVAL = 86400` constant (add this), and after `class StartupError`, add the module-level flag and the new function:

```python
# Gate check state — resets on daemon restart (acceptable; see design spec)
_gate_announced: bool = False
_GATE_CHECK_INTERVAL: int = 86400  # 24 hours
```

Then add the `_run_gate_check` function before `run_daemon()`:

```python
async def _run_gate_check(config: TradingConfig) -> None:
    """Daily promotion gate check — alerts on status change."""
    global _gate_announced
    logger.info("Gate check agent started")
    while True:
        result = check_promotion_gate()
        n_pass = sum(1 for ok, _ in result.checks.values() if ok)
        n_total = len(result.checks)
        lines = [f"  [{'PASS' if ok else 'FAIL'}] {name}: {reason}"
                 for name, (ok, reason) in result.checks.items()]
        detail = "\n".join(lines)

        if result.passed:
            if not _gate_announced:
                send_alert(
                    f"PROMOTION GATE PASSED \u2705 \u2014 SharpEdge is ready for live trading.\n{detail}"
                )
                _gate_announced = True
                logger.info("Promotion gate PASSED \u2014 Slack alert sent")
            else:
                logger.info("Gate check: PASSED (alert already sent this session)")
        else:
            send_alert(
                f"Daily gate check: {n_pass}/{n_total} checks passing.\n{detail}"
            )
            logger.info("Gate check: %d/%d passing", n_pass, n_total)

        await asyncio.sleep(_GATE_CHECK_INTERVAL)
```

- [ ] **Step 4: Wire into the TaskGroup in `run_daemon()`**

In `run_daemon()`, inside the `async with asyncio.TaskGroup() as tg:` block, add:

```python
        tg.create_task(_run_gate_check(config), name="gate_check")
```

The full TaskGroup block should look like:

```python
    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_scan_agent(bus, config, kalshi_client), name="scan")
        tg.create_task(run_research_agent(bus), name="research")
        tg.create_task(run_prediction_agent(bus, config, calibrator), name="prediction")
        tg.create_task(run_portfolio_manager(bus, config), name="portfolio")
        tg.create_task(run_risk_agent(bus, config), name="risk")
        tg.create_task(_run_execution(bus, executor), name="execution")
        tg.create_task(run_monitor_agent(bus, kalshi_client), name="monitor")
        tg.create_task(run_post_mortem_agent(bus, config, get_bankroll()), name="post_mortem")
        tg.create_task(_run_gate_check(config), name="gate_check")
```

- [ ] **Step 5: Run all daemon tests**

```bash
uv run --directory packages/trading_swarm pytest tests/test_daemon.py -v
```

Expected: all pass

- [ ] **Step 6: Run full test suite to confirm no regressions**

```bash
uv run --directory packages/trading_swarm pytest tests/ -v --ignore=tests/contract
```

Expected: all pass (contract tests require real credentials, skip them)

- [ ] **Step 7: Commit**

```bash
git add packages/trading_swarm/src/sharpedge_trading/daemon.py packages/trading_swarm/tests/test_daemon.py
git commit -m "feat(alerts): daily promotion gate check with Slack alerts"
```

---

## Final verification

- [ ] **Rebuild Docker image and confirm startup**

```bash
docker compose build trading-swarm && docker compose up trading-swarm
```

Expected in logs within 10 seconds of startup:
- `Gate check agent started`
- `Daily gate check: X/8 passing` (Slack message appears in your channel)

- [ ] **Confirm SLACK_WEBHOOK_URL is reaching the container**

```bash
docker compose exec trading-swarm env | grep SLACK
```

Expected: `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`
