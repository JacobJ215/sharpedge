"""Tests for slack alert module."""
from __future__ import annotations

import logging
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

    with caplog.at_level(logging.WARNING, logger="sharpedge_trading.alerts.slack"):
        with patch("httpx.post", side_effect=raise_error):
            send_alert("test")
            time.sleep(0.2)

    assert any("Slack alert failed" in r.message for r in caplog.records)
