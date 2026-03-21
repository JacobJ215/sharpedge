"""Whop webhook handlers for subscription management."""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/webhooks", tags=["whop"])
logger = logging.getLogger("sharpedge.webhooks.whop")

# Discord API base
DISCORD_API = "https://discord.com/api/v10"


def verify_whop_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Whop webhook signature.

    Whop uses HMAC-SHA256 for webhook verification.
    """
    if not signature or not secret:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def add_discord_role(user_id: str, role_id: str) -> bool:
    """Add a role to a Discord user via REST API."""
    guild_id = os.environ.get("DISCORD_GUILD_ID", "")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")

    if not guild_id or not bot_token:
        logger.error("Missing Discord configuration")
        return False

    url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}"

    async with httpx.AsyncClient() as client:
        response = await client.put(
            url,
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code in (200, 201, 204):
            logger.info(f"Added role {role_id} to user {user_id}")
            return True
        else:
            logger.error(f"Failed to add role: {response.status_code} {response.text}")
            return False


async def remove_discord_role(user_id: str, role_id: str) -> bool:
    """Remove a role from a Discord user via REST API."""
    guild_id = os.environ.get("DISCORD_GUILD_ID", "")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")

    if not guild_id or not bot_token:
        logger.error("Missing Discord configuration")
        return False

    url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}"

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers={
                "Authorization": f"Bot {bot_token}",
            },
        )

        if response.status_code in (200, 204):
            logger.info(f"Removed role {role_id} from user {user_id}")
            return True
        else:
            logger.error(f"Failed to remove role: {response.status_code} {response.text}")
            return False


def get_role_for_product(product_id: str) -> str | None:
    """Get Discord role ID for a Whop product."""
    pro_product = os.environ.get("WHOP_PRO_PRODUCT_ID", "")
    sharp_product = os.environ.get("WHOP_SHARP_PRODUCT_ID", "")
    pro_role = os.environ.get("PRO_ROLE_ID", "")
    sharp_role = os.environ.get("SHARP_ROLE_ID", "")

    if product_id == sharp_product:
        return sharp_role
    elif product_id == pro_product:
        return pro_role

    return None


def get_tier_for_product(product_id: str) -> str:
    """Get tier name for a Whop product."""
    pro_product = os.environ.get("WHOP_PRO_PRODUCT_ID", "")
    sharp_product = os.environ.get("WHOP_SHARP_PRODUCT_ID", "")

    if product_id == sharp_product:
        return "sharp"
    elif product_id == pro_product:
        return "pro"

    return "free"


async def update_user_tier_in_db(discord_id: str, tier: str) -> None:
    """Update user's tier in the database."""
    try:
        from sharpedge_db.client import get_supabase_client

        client = get_supabase_client()

        # Update or create user
        client.table("users").upsert({
            "discord_id": discord_id,
            "tier": tier,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="discord_id").execute()

        logger.info(f"Updated user {discord_id} to tier {tier}")

    except Exception as e:
        logger.exception(f"Failed to update user tier: {e}")


async def push_tier_to_supabase_auth(discord_id: str, tier: str) -> None:
    """Push updated tier into Supabase auth.users app_metadata for immediate JWT reflection.

    Looks up supabase_auth_id from public.users by discord_id, then calls
    the Supabase Admin API to update auth.users.app_metadata.tier.
    If supabase_auth_id is NULL (Discord-only user with no web account),
    logs info and returns gracefully.
    """
    try:
        from sharpedge_db.client import get_supabase_client
        client = get_supabase_client()

        result = client.table("users").select("supabase_auth_id").eq(
            "discord_id", discord_id
        ).maybe_single().execute()

        if not result.data or not result.data.get("supabase_auth_id"):
            logger.info(
                f"No supabase_auth_id for discord_id={discord_id}; "
                "skipping auth metadata update (Discord-only user)"
            )
            return

        supabase_auth_id = result.data["supabase_auth_id"]
        client.auth.admin.update_user_by_id(
            supabase_auth_id,
            {"app_metadata": {"tier": tier}}
        )
        logger.info(f"Pushed tier={tier} to supabase auth for user {supabase_auth_id}")

    except Exception as e:
        logger.exception(f"Failed to push tier to Supabase auth: {e}")


async def log_payment(
    discord_id: str,
    product_id: str,
    amount: float,
    currency: str,
    whop_membership_id: str,
    status: str = "succeeded",
) -> None:
    """Log payment to database for analytics."""
    try:
        from sharpedge_db.client import get_supabase_client

        client = get_supabase_client()

        client.table("payments").insert({
            "discord_id": discord_id,
            "product_id": product_id,
            "tier": get_tier_for_product(product_id),
            "amount": amount,
            "currency": currency,
            "whop_membership_id": whop_membership_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.info(f"Logged payment for user {discord_id}")

    except Exception as e:
        logger.exception(f"Failed to log payment: {e}")


@router.post("/whop")
async def whop_webhook(
    request: Request,
    x_whop_signature: str = Header(None, alias="X-Whop-Signature"),
):
    """Handle Whop webhook events.

    Events:
    - membership.went_valid: User subscribed or renewed
    - membership.went_invalid: User cancelled or payment failed
    - payment.succeeded: Payment completed
    - payment.failed: Payment failed
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    webhook_secret = os.environ.get("WHOP_WEBHOOK_SECRET", "")
    if webhook_secret and x_whop_signature:
        if not verify_whop_signature(body, x_whop_signature, webhook_secret):
            logger.warning("Invalid Whop webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("action") or payload.get("event")
    data = payload.get("data", {})

    logger.info(f"Received Whop webhook: {event_type}")

    # Extract common fields
    # Whop provides Discord user ID through their Discord integration
    discord_account = data.get("discord", {}) or {}
    discord_id = discord_account.get("id") or data.get("discord_id")

    # Get product/plan info
    product_id = data.get("product", {}).get("id") or data.get("plan", {}).get("id") or data.get("product_id", "")
    membership_id = data.get("id") or data.get("membership_id", "")

    if not discord_id:
        # Try to get from user object
        user = data.get("user", {})
        discord_id = user.get("discord", {}).get("id")

    if not discord_id:
        logger.warning(f"No Discord ID in webhook payload: {event_type}")
        # Return 200 to acknowledge receipt even without Discord ID
        return {"status": "ok", "message": "No Discord ID found"}

    # Handle events
    if event_type in ("membership.went_valid", "membership.created", "membership.renewed"):
        # User subscribed or renewed
        role_id = get_role_for_product(product_id)
        tier = get_tier_for_product(product_id)

        if role_id:
            # Add role
            await add_discord_role(discord_id, role_id)

            # If Sharp tier, also add Pro role (Sharp includes Pro)
            if tier == "sharp":
                pro_role = os.environ.get("PRO_ROLE_ID", "")
                if pro_role:
                    await add_discord_role(discord_id, pro_role)

        # Update database
        await update_user_tier_in_db(discord_id, tier)
        await push_tier_to_supabase_auth(discord_id, tier)

        logger.info(f"Subscription activated: {discord_id} -> {tier}")

    elif event_type in ("membership.went_invalid", "membership.cancelled", "membership.expired"):
        # User cancelled or subscription ended
        role_id = get_role_for_product(product_id)
        tier = get_tier_for_product(product_id)

        if role_id:
            # Remove role
            await remove_discord_role(discord_id, role_id)

            # If Sharp tier was removed, also remove Pro role
            if tier == "sharp":
                pro_role = os.environ.get("PRO_ROLE_ID", "")
                if pro_role:
                    await remove_discord_role(discord_id, pro_role)

        # Update database to free tier
        await update_user_tier_in_db(discord_id, "free")
        await push_tier_to_supabase_auth(discord_id, "free")

        logger.info(f"Subscription ended: {discord_id} -> free")

    elif event_type == "payment.succeeded":
        # Log successful payment
        amount = data.get("final_amount") or data.get("amount", 0)
        currency = data.get("currency", "usd")

        await log_payment(
            discord_id=discord_id,
            product_id=product_id,
            amount=amount / 100 if amount > 100 else amount,  # Convert cents if needed
            currency=currency,
            whop_membership_id=membership_id,
            status="succeeded",
        )

    elif event_type == "payment.failed":
        # Log failed payment
        amount = data.get("final_amount") or data.get("amount", 0)
        currency = data.get("currency", "usd")

        await log_payment(
            discord_id=discord_id,
            product_id=product_id,
            amount=amount / 100 if amount > 100 else amount,
            currency=currency,
            whop_membership_id=membership_id,
            status="failed",
        )

        logger.warning(f"Payment failed for user {discord_id}")

    else:
        logger.info(f"Unhandled Whop event: {event_type}")

    return {"status": "ok", "event": event_type}
