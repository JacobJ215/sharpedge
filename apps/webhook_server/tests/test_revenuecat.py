"""Tests for RevenueCat webhook handler."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    from sharpedge_webhooks.routes.revenuecat import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def test_revenuecat_initial_purchase_pushes_tier(client):
    """INITIAL_PURCHASE event updates tier to pro."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.auth.admin.update_user_by_id = MagicMock()

    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "test-secret"}):
        with patch("sharpedge_db.client.get_supabase_client", return_value=mock_sb):
            resp = client.post(
                "/webhooks/revenuecat",
                json={
                    "event": {
                        "type": "INITIAL_PURCHASE",
                        "app_user_id": "uuid-abc",
                        "product_id": "sharpedge_pro_monthly",
                    }
                },
                headers={"Authorization": "test-secret"},
            )

    assert resp.status_code == 200
    mock_sb.auth.admin.update_user_by_id.assert_called_once_with(
        "uuid-abc",
        {"app_metadata": {"tier": "pro"}}
    )


def test_revenuecat_expiration_sets_free(client):
    """EXPIRATION event sets tier to free."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.auth.admin.update_user_by_id = MagicMock()

    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "test-secret"}):
        with patch("sharpedge_db.client.get_supabase_client", return_value=mock_sb):
            resp = client.post(
                "/webhooks/revenuecat",
                json={
                    "event": {
                        "type": "EXPIRATION",
                        "app_user_id": "uuid-abc",
                        "product_id": "sharpedge_pro_monthly",
                    }
                },
                headers={"Authorization": "test-secret"},
            )

    assert resp.status_code == 200
    mock_sb.auth.admin.update_user_by_id.assert_called_once_with(
        "uuid-abc",
        {"app_metadata": {"tier": "free"}}
    )


def test_revenuecat_rejects_invalid_auth(client):
    """Invalid Authorization header returns 401."""
    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "real-secret"}):
        resp = client.post(
            "/webhooks/revenuecat",
            json={"event": {"type": "INITIAL_PURCHASE", "app_user_id": "x", "product_id": "y"}},
            headers={"Authorization": "wrong-secret"},
        )
    assert resp.status_code == 401


def test_revenuecat_no_app_user_id(client):
    """Missing app_user_id returns 200 with message."""
    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "s"}):
        resp = client.post(
            "/webhooks/revenuecat",
            json={"event": {"type": "INITIAL_PURCHASE", "app_user_id": "", "product_id": "x"}},
            headers={"Authorization": "s"},
        )
    assert resp.status_code == 200
    assert resp.json()["message"] == "No app_user_id"
