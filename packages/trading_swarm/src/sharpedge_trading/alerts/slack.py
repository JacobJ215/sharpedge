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
