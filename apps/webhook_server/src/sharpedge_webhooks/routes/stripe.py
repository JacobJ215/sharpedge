"""Stripe webhook handler for subscription events."""

import logging
import os

import httpx
import stripe
from fastapi import APIRouter, HTTPException, Request

from sharpedge_db.queries.users import get_user_by_discord_id, update_user_tier
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.webhooks.stripe")

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    webhook_secret = os.environ["STRIPE_WEBHOOK_SECRET"]
    pro_price_id = os.environ["STRIPE_PRO_PRICE_ID"]
    sharp_price_id = os.environ["STRIPE_SHARP_PRICE_ID"]

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe event: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, pro_price_id, sharp_price_id)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, pro_price_id, sharp_price_id)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)

    return {"status": "ok"}


async def _handle_checkout_completed(
    session: dict, pro_price_id: str, sharp_price_id: str
) -> None:
    """New subscription created via checkout."""
    discord_id = session.get("metadata", {}).get("discord_id")
    subscription_id = session.get("subscription")

    if not discord_id:
        logger.warning("Checkout session missing discord_id metadata.")
        return

    # Determine tier from line items
    tier = await _determine_tier_from_subscription(subscription_id, pro_price_id, sharp_price_id)

    # Update user in database
    update_user_tier(discord_id, tier, subscription_id)
    logger.info("User %s upgraded to %s (sub: %s)", discord_id, tier, subscription_id)

    # Sync Discord role
    await _sync_discord_role(discord_id, tier, action="add")


async def _handle_subscription_updated(
    subscription: dict, pro_price_id: str, sharp_price_id: str
) -> None:
    """Subscription plan changed (upgrade/downgrade)."""
    discord_id = subscription.get("metadata", {}).get("discord_id")
    if not discord_id:
        return

    sub_id = subscription["id"]
    tier = _tier_from_items(subscription.get("items", {}).get("data", []), pro_price_id, sharp_price_id)

    update_user_tier(discord_id, tier, sub_id)
    logger.info("User %s subscription updated to %s.", discord_id, tier)

    # Remove old role, add new
    await _sync_discord_role(discord_id, tier, action="add")


async def _handle_subscription_deleted(subscription: dict) -> None:
    """Subscription cancelled."""
    discord_id = subscription.get("metadata", {}).get("discord_id")
    if not discord_id:
        return

    # Downgrade to free
    update_user_tier(discord_id, Tier.FREE, None)
    logger.info("User %s subscription cancelled, downgraded to free.", discord_id)

    await _sync_discord_role(discord_id, Tier.FREE, action="remove")


async def _handle_payment_failed(invoice: dict) -> None:
    """Payment failed — log warning."""
    customer = invoice.get("customer")
    logger.warning("Payment failed for customer %s.", customer)


async def _determine_tier_from_subscription(
    subscription_id: str, pro_price_id: str, sharp_price_id: str
) -> Tier:
    """Look up the subscription to determine tier."""
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    sub = stripe.Subscription.retrieve(subscription_id)
    items = sub.get("items", {}).get("data", [])
    return _tier_from_items(items, pro_price_id, sharp_price_id)


def _tier_from_items(items: list, pro_price_id: str, sharp_price_id: str) -> Tier:
    """Determine tier from subscription items."""
    for item in items:
        price_id = item.get("price", {}).get("id", "")
        if price_id == sharp_price_id:
            return Tier.SHARP
        if price_id == pro_price_id:
            return Tier.PRO
    return Tier.FREE


async def _sync_discord_role(discord_id: str, tier: Tier, action: str = "add") -> None:
    """Add or remove Discord roles via the REST API."""
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    guild_id = os.environ.get("DISCORD_GUILD_ID", "")
    pro_role_id = os.environ.get("PRO_ROLE_ID", "")
    sharp_role_id = os.environ.get("SHARP_ROLE_ID", "")

    if not all([bot_token, guild_id]):
        logger.warning("Discord config missing, skipping role sync.")
        return

    headers = {"Authorization": f"Bot {bot_token}"}
    base = f"https://discord.com/api/v10/guilds/{guild_id}/members/{discord_id}/roles"

    async with httpx.AsyncClient() as client:
        if action == "remove" or tier == Tier.FREE:
            # Remove both Pro and Sharp roles
            for role_id in [pro_role_id, sharp_role_id]:
                if role_id:
                    await client.delete(f"{base}/{role_id}", headers=headers)
        elif tier == Tier.PRO and pro_role_id:
            await client.put(f"{base}/{pro_role_id}", headers=headers)
            if sharp_role_id:
                await client.delete(f"{base}/{sharp_role_id}", headers=headers)
        elif tier == Tier.SHARP and sharp_role_id:
            await client.put(f"{base}/{sharp_role_id}", headers=headers)
            if pro_role_id:
                await client.delete(f"{base}/{pro_role_id}", headers=headers)
