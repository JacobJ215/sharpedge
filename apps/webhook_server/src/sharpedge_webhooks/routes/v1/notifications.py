"""POST /api/v1/users/{user_id}/device-token — FCM device token registration."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from supabase import create_client

if TYPE_CHECKING:
    from sharpedge_webhooks.routes.v1.deps import CurrentUser

router = APIRouter(tags=["v1"])


class DeviceTokenRequest(BaseModel):
    fcm_token: str
    platform: str  # 'ios' | 'android'


@router.post("/users/{user_id}/device-token", status_code=201)
async def register_device_token(
    user_id: str,
    request: DeviceTokenRequest,
    current_user: CurrentUser,
) -> dict:
    """Register or update FCM device token for push notifications.

    Requires valid Supabase JWT. User can only register their own tokens.
    """
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot register token for another user",
        )
    if request.platform not in ("ios", "android"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="platform must be 'ios' or 'android'",
        )

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
    client.table("user_device_tokens").upsert(
        {
            "user_id": user_id,
            "fcm_token": request.fcm_token,
            "platform": request.platform,
        },
        on_conflict="user_id,fcm_token",
    ).execute()
    return {"registered": True}
