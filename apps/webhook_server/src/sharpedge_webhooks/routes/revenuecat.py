"""RevenueCat webhook handler for mobile IAP subscription management.

RevenueCat fires webhook events for Apple IAP and Google Play billing.
This handler maps RevenueCat events to tier updates in public.users
and pushes the tier into auth.users.app_metadata via the Supabase Admin API.

Verification: RevenueCat sends a shared secret in the Authorization header.
User ID: RevenueCat app_user_id is set to the Supabase Auth UUID at purchase time
(Flutter calls Purchases.logIn(supabaseUserId) after sign-in).
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/webhooks", tags=["revenuecat"])
logger = logging.getLogger("sharpedge.webhooks.revenuecat")

# RevenueCat product ID -> tier mapping
REVENUECAT_TIER_MAP: dict[str, str] = {
    "sharpedge_pro_monthly": "pro",
    "sharpedge_pro_yearly": "pro",
    "sharpedge_sharp_monthly": "sharp",
    "sharpedge_sharp_yearly": "sharp",
}

# Events that activate a subscription
ACTIVATE_EVENTS = {
    "INITIAL_PURCHASE",
    "RENEWAL",
    "UNCANCELLATION",
    "NON_RENEWING_PURCHASE",
}

# Events that deactivate a subscription
DEACTIVATE_EVENTS = {
    "CANCELLATION",
    "EXPIRATION",
}


def verify_revenuecat_auth(authorization: str | None) -> bool:
    """Verify RevenueCat webhook authorization header."""
    secret = os.environ.get("REVENUECAT_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("REVENUECAT_WEBHOOK_SECRET not set; skipping verification")
        return True
    return authorization == secret


def get_tier_from_product_id(product_id: str) -> str:
    """Map RevenueCat product ID to tier string."""
    return REVENUECAT_TIER_MAP.get(product_id, "pro")


async def push_tier_by_supabase_auth_id(supabase_auth_id: str, tier: str) -> None:
    """Update tier in both public.users and auth.users.app_metadata."""
    try:
        from sharpedge_db.client import get_supabase_client
        client = get_supabase_client()

        # Update public.users tier
        client.table("users").update({
            "tier": tier,
        }).eq("supabase_auth_id", supabase_auth_id).execute()

        # Push to auth.users.app_metadata for immediate JWT reflection
        client.auth.admin.update_user_by_id(
            supabase_auth_id,
            {"app_metadata": {"tier": tier}}
        )
        logger.info(f"RevenueCat: pushed tier={tier} for user {supabase_auth_id}")

    except Exception as e:
        logger.exception(f"RevenueCat: failed to push tier: {e}")


@router.post("/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: str | None = Header(None),
):
    """Handle RevenueCat webhook events for mobile IAP subscriptions.

    Events:
    - INITIAL_PURCHASE / RENEWAL: User subscribed or renewed via IAP
    - CANCELLATION / EXPIRATION: Subscription ended
    - BILLING_ISSUE: Payment problem (logged only, tier stays active)
    """
    if not verify_revenuecat_auth(authorization):
        raise HTTPException(status_code=401, detail="Invalid authorization")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event", {})
    event_type = event.get("type", "")
    app_user_id = event.get("app_user_id", "")
    product_id = event.get("product_id", "")

    logger.info(f"RevenueCat webhook: type={event_type} user={app_user_id} product={product_id}")

    if not app_user_id:
        logger.warning("RevenueCat webhook: no app_user_id in event")
        return {"status": "ok", "message": "No app_user_id"}

    if event_type in ACTIVATE_EVENTS:
        tier = get_tier_from_product_id(product_id)
        await push_tier_by_supabase_auth_id(app_user_id, tier)
        logger.info(f"RevenueCat: activated {app_user_id} -> {tier}")

    elif event_type in DEACTIVATE_EVENTS:
        await push_tier_by_supabase_auth_id(app_user_id, "free")
        logger.info(f"RevenueCat: deactivated {app_user_id} -> free")

    elif event_type == "BILLING_ISSUE":
        logger.warning(f"RevenueCat: billing issue for {app_user_id}, tier stays active")

    else:
        logger.info(f"RevenueCat: unhandled event type {event_type}")

    return {"status": "ok", "event": event_type}
