"""Tests for push_tier_to_supabase_auth in Whop webhook handler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_push_tier_to_supabase_auth_with_linked_account():
    """When supabase_auth_id exists, admin API update_user_by_id is called."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"supabase_auth_id": "uuid-123"}
    )
    mock_client.auth.admin.update_user_by_id = MagicMock()

    with patch("sharpedge_db.client.get_supabase_client", return_value=mock_client):
        from sharpedge_webhooks.routes.whop import push_tier_to_supabase_auth
        await push_tier_to_supabase_auth("discord-456", "pro")

    mock_client.auth.admin.update_user_by_id.assert_called_once_with(
        "uuid-123",
        {"app_metadata": {"tier": "pro"}}
    )


@pytest.mark.asyncio
async def test_push_tier_to_supabase_auth_discord_only_user():
    """When supabase_auth_id is NULL, admin API is NOT called."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"supabase_auth_id": None}
    )
    mock_client.auth.admin.update_user_by_id = MagicMock()

    with patch("sharpedge_db.client.get_supabase_client", return_value=mock_client):
        from sharpedge_webhooks.routes.whop import push_tier_to_supabase_auth
        await push_tier_to_supabase_auth("discord-456", "pro")

    mock_client.auth.admin.update_user_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_push_tier_to_supabase_auth_no_row():
    """When no public.users row exists for discord_id, admin API is NOT called."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=None
    )
    mock_client.auth.admin.update_user_by_id = MagicMock()

    with patch("sharpedge_db.client.get_supabase_client", return_value=mock_client):
        from sharpedge_webhooks.routes.whop import push_tier_to_supabase_auth
        await push_tier_to_supabase_auth("discord-456", "pro")

    mock_client.auth.admin.update_user_by_id.assert_not_called()
