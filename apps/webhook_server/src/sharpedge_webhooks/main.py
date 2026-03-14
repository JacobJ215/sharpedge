"""FastAPI webhook server for SharpEdge."""

import logging
import os
import sys

import uvicorn
from fastapi import FastAPI

from sharpedge_webhooks.config import WebhookConfig
from sharpedge_webhooks.routes.mobile import router as mobile_router
from sharpedge_webhooks.routes.v1.bankroll import router as v1_bankroll_router
from sharpedge_webhooks.routes.v1.copilot import router as v1_copilot_router
from sharpedge_webhooks.routes.v1.game_analysis import router as v1_game_analysis_router
from sharpedge_webhooks.routes.v1.portfolio import router as v1_portfolio_router
from sharpedge_webhooks.routes.v1.value_plays import router as v1_value_plays_router
from sharpedge_webhooks.routes.whop import router as whop_router

# Keep Stripe router for legacy/migration purposes
try:
    from sharpedge_webhooks.routes.stripe import router as stripe_router
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False

app = FastAPI(
    title="SharpEdge Webhooks",
    version="0.1.0",
    description="Webhook server for payment and subscription events",
)

# Primary: Whop webhooks
app.include_router(whop_router)

# Mobile API
app.include_router(mobile_router)

# v1 API routes
app.include_router(v1_value_plays_router, prefix="/api/v1")
app.include_router(v1_game_analysis_router, prefix="/api/v1")
app.include_router(v1_copilot_router, prefix="/api/v1")
app.include_router(v1_portfolio_router, prefix="/api/v1")
app.include_router(v1_bankroll_router, prefix="/api/v1")

# Legacy: Stripe webhooks (if still needed)
if HAS_STRIPE:
    app.include_router(stripe_router)


@app.get("/")
async def root() -> dict:
    return {
        "service": "sharpedge-webhooks",
        "version": "0.1.0",
        "endpoints": [
            "/webhooks/whop",
            "/health",
            "/api/value-plays",
            "/api/arbitrage",
            "/api/line-movements",
            "/api/bankroll",
            "/api/v1/value-plays",
            "/api/v1/games/{id}/analysis",
            "/api/v1/copilot/chat",
            "/api/v1/users/{id}/portfolio",
            "/api/v1/bankroll/simulate",
        ],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "sharpedge-webhooks"}


def run() -> None:
    """Entry point for the webhook server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("sharpedge.webhooks")

    config = WebhookConfig()  # type: ignore[call-arg]

    # Set env vars for downstream modules
    os.environ["SUPABASE_URL"] = config.supabase_url
    os.environ["SUPABASE_KEY"] = config.supabase_key
    os.environ["SUPABASE_SERVICE_KEY"] = config.supabase_service_key or config.supabase_key

    # Whop configuration
    os.environ["WHOP_API_KEY"] = config.whop_api_key
    os.environ["WHOP_WEBHOOK_SECRET"] = config.whop_webhook_secret
    os.environ["WHOP_PRO_PRODUCT_ID"] = config.whop_pro_product_id
    os.environ["WHOP_SHARP_PRODUCT_ID"] = config.whop_sharp_product_id

    # Discord configuration
    os.environ["DISCORD_BOT_TOKEN"] = config.discord_bot_token
    os.environ["DISCORD_GUILD_ID"] = config.discord_guild_id
    os.environ["PRO_ROLE_ID"] = config.pro_role_id
    os.environ["SHARP_ROLE_ID"] = config.sharp_role_id
    os.environ["FREE_ROLE_ID"] = config.free_role_id

    # Legacy Stripe (if configured)
    if config.stripe_secret_key:
        os.environ["STRIPE_SECRET_KEY"] = config.stripe_secret_key
        os.environ["STRIPE_WEBHOOK_SECRET"] = config.stripe_webhook_secret
        os.environ["STRIPE_PRO_PRICE_ID"] = config.stripe_pro_price_id
        os.environ["STRIPE_SHARP_PRICE_ID"] = config.stripe_sharp_price_id

    logger.info(f"Starting webhook server on port {config.webhook_port}")
    logger.info("Whop webhook endpoint: POST /webhooks/whop")

    uvicorn.run(app, host="0.0.0.0", port=config.webhook_port)


if __name__ == "__main__":
    run()
