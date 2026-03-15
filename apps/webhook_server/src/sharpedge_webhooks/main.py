"""FastAPI webhook server for SharpEdge."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from sharpedge_webhooks.config import WebhookConfig
from sharpedge_webhooks.routes.mobile import router as mobile_router
from sharpedge_webhooks.routes.v1.bankroll import router as v1_bankroll_router
from sharpedge_webhooks.routes.v1.copilot import router as v1_copilot_router
from sharpedge_webhooks.routes.v1 import markets as markets_v1
from sharpedge_webhooks.routes.v1.game_analysis import router as v1_game_analysis_router
from sharpedge_webhooks.routes.v1.notifications import router as v1_notifications_router
from sharpedge_webhooks.routes.v1.portfolio import router as v1_portfolio_router
from sharpedge_webhooks.routes.v1.value_plays import router as v1_value_plays_router
from sharpedge_webhooks.routes.whop import router as whop_router

# Keep Stripe router for legacy/migration purposes
try:
    from sharpedge_webhooks.routes.stripe import router as stripe_router
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False

_logger = logging.getLogger("sharpedge.webhooks")

# Config is populated in run() before uvicorn starts; also available at module
# level so the lifespan can reference it without a circular import.
_config: WebhookConfig | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Start background jobs on startup; cancel them on shutdown."""
    tasks: list[asyncio.Task] = []

    if _config and _config.alert_enabled:
        from sharpedge_webhooks.jobs.result_watcher import run_result_watcher

        social_cfg = {
            "discord_bot_token": _config.discord_bot_token,
            "discord_channel_id": _config.win_announcements_channel_id,
            "instagram_account_id": _config.instagram_account_id,
            "instagram_access_token": _config.instagram_access_token,
            "instagram_account_handle": _config.instagram_account_handle,
            "supabase_url": _config.supabase_url,
            "supabase_service_key": _config.supabase_service_key or _config.supabase_key,
            "supabase_storage_bucket": _config.supabase_storage_bucket,
            "social_image_enabled": _config.social_image_enabled,
        }

        tasks.append(
            asyncio.create_task(
                run_result_watcher(social_cfg, poll_interval=_config.alert_poll_interval_seconds),
                name="result_watcher",
            )
        )
        _logger.info("result_watcher job started (poll interval %ds)", _config.alert_poll_interval_seconds)

        from sharpedge_webhooks.jobs.alert_poster import run_alert_poster

        alert_cfg = {**social_cfg,
            "min_ev_threshold": _config.alert_min_ev_threshold,
            "cooldown_minutes": _config.alert_cooldown_minutes,
            "value_alerts_channel_id": getattr(_config, 'value_alerts_channel_id', ''),
            "twitter_api_key": _config.twitter_api_key,
            "twitter_api_secret": _config.twitter_api_secret,
            "twitter_access_token": _config.twitter_access_token,
            "twitter_access_token_secret": _config.twitter_access_token_secret,
        }

        tasks.append(
            asyncio.create_task(
                run_alert_poster(alert_cfg, poll_interval=_config.alert_poll_interval_seconds),
                name="alert_poster",
            )
        )
        _logger.info("alert_poster job started")
    else:
        _logger.info("Social posting disabled (ALERT_ENABLED=false)")

    yield

    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _logger.info("Background jobs stopped")


app = FastAPI(
    title="SharpEdge Webhooks",
    version="0.1.0",
    description="Webhook server for payment and subscription events",
    lifespan=lifespan,
)

# Primary: Whop webhooks
app.include_router(whop_router)

# Mobile API
app.include_router(mobile_router)

# v1 API routes
app.include_router(v1_value_plays_router, prefix="/api/v1")
app.include_router(v1_game_analysis_router, prefix="/api/v1")
app.include_router(v1_copilot_router, prefix="/api/v1")
app.include_router(v1_notifications_router, prefix="/api/v1")
app.include_router(v1_portfolio_router, prefix="/api/v1")
app.include_router(v1_bankroll_router, prefix="/api/v1")
app.include_router(markets_v1.router, prefix="/api/v1")

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
    global _config
    _config = config

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
