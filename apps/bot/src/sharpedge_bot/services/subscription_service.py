"""Business logic for Whop subscription management."""

import logging
from typing import Any

import httpx

logger = logging.getLogger("sharpedge.services.subscription")


def get_whop_checkout_url(
    product_id: str,
    company_slug: str,
    discord_id: str | None = None,
) -> str:
    """Generate a Whop checkout URL for a product.

    Whop handles checkout natively - we just redirect to the product page.

    Args:
        product_id: Whop product ID (prod_xxxxx)
        company_slug: Your Whop company/store slug
        discord_id: Optional Discord ID for tracking (passed as query param)

    Returns:
        Checkout URL for the product
    """
    # Base Whop checkout URL
    base_url = f"https://whop.com/{company_slug}/checkout/{product_id}"

    # Add Discord ID as reference if provided
    if discord_id:
        base_url += f"?d={discord_id}"

    return base_url


def get_whop_product_url(company_slug: str, product_id: str = "") -> str:
    """Get URL to view products or a specific product on Whop.

    Args:
        company_slug: Your Whop company/store slug
        product_id: Optional specific product ID

    Returns:
        Product or store URL
    """
    if product_id:
        return f"https://whop.com/{company_slug}/checkout/{product_id}"
    return f"https://whop.com/{company_slug}"


async def validate_whop_membership(
    whop_api_key: str,
    membership_id: str,
) -> dict[str, Any] | None:
    """Validate a Whop membership via API.

    Args:
        whop_api_key: Your Whop API key
        membership_id: Membership ID to validate

    Returns:
        Membership data if valid, None otherwise
    """
    if not whop_api_key or not membership_id:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.whop.com/api/v2/memberships/{membership_id}",
                headers={
                    "Authorization": f"Bearer {whop_api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                return response.json()

    except Exception as e:
        logger.exception(f"Error validating Whop membership: {e}")

    return None


async def get_user_memberships(
    whop_api_key: str,
    discord_id: str,
) -> list[dict[str, Any]]:
    """Get all memberships for a Discord user.

    Args:
        whop_api_key: Your Whop API key
        discord_id: Discord user ID

    Returns:
        List of membership objects
    """
    if not whop_api_key or not discord_id:
        return []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.whop.com/api/v2/memberships",
                params={"discord_id": discord_id},
                headers={
                    "Authorization": f"Bearer {whop_api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

    except Exception as e:
        logger.exception(f"Error fetching user memberships: {e}")

    return []


def get_tier_from_membership(
    membership: dict[str, Any],
    pro_product_id: str,
    sharp_product_id: str,
) -> str:
    """Determine tier from a Whop membership object.

    Args:
        membership: Whop membership object
        pro_product_id: Product ID for Pro tier
        sharp_product_id: Product ID for Sharp tier

    Returns:
        Tier string: 'sharp', 'pro', or 'free'
    """
    if not membership:
        return "free"

    product_id = membership.get("product", {}).get("id", "")
    status = membership.get("status", "")

    # Only valid memberships grant tier
    if status not in ("active", "trialing", "completed"):
        return "free"

    if product_id == sharp_product_id:
        return "sharp"
    elif product_id == pro_product_id:
        return "pro"

    return "free"


# ===========================================
# LEGACY STRIPE FUNCTIONS (deprecated)
# ===========================================

def create_checkout_session(
    discord_id: str,
    discord_username: str,
    price_id: str,
    stripe_secret_key: str,
    success_url: str = "https://sharpedge.gg/success",
    cancel_url: str = "https://sharpedge.gg/cancel",
) -> str:
    """Create a Stripe Checkout session and return the URL.

    DEPRECATED: Use get_whop_checkout_url instead.
    """
    try:
        import stripe
    except ImportError:
        logger.error("Stripe not installed. Use Whop instead.")
        return ""

    stripe.api_key = stripe_secret_key

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "discord_id": discord_id,
            "discord_username": discord_username,
        },
        subscription_data={
            "metadata": {
                "discord_id": discord_id,
                "discord_username": discord_username,
            },
        },
    )

    logger.info("Checkout session created for %s: %s", discord_id, session.id)
    return session.url


def create_portal_session(
    customer_id: str,
    stripe_secret_key: str,
    return_url: str = "https://sharpedge.gg",
) -> str:
    """Create a Stripe Customer Portal session and return the URL.

    DEPRECATED: Use Whop customer portal instead.
    """
    try:
        import stripe
    except ImportError:
        logger.error("Stripe not installed. Use Whop instead.")
        return ""

    stripe.api_key = stripe_secret_key

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )

    return session.url
