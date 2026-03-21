"""Tests for GET /api/v1/swarm/pipeline and GET /api/v1/swarm/calibration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MOCK_POSITIONS
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
