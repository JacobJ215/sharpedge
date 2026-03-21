"""Startup/shutdown helpers for BettingCopilot Postgres checkpointer (optional)."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

_logger = logging.getLogger("sharpedge.webhooks")


async def start_background_jobs(app: FastAPI, config) -> list[asyncio.Task]:
    """Start optional alert / line-monitor tasks. Returns task handles."""
    tasks: list[asyncio.Task] = []
    if config is None:
        return tasks

    if config.alert_enabled:
        from sharpedge_webhooks.jobs.result_watcher import run_result_watcher

        social_cfg = {
            "discord_bot_token": config.discord_bot_token,
            "discord_channel_id": config.win_announcements_channel_id,
            "instagram_account_id": config.instagram_account_id,
            "instagram_access_token": config.instagram_access_token,
            "instagram_account_handle": config.instagram_account_handle,
            "supabase_url": config.supabase_url,
            "supabase_service_key": config.supabase_service_key or config.supabase_key,
            "supabase_storage_bucket": config.supabase_storage_bucket,
            "social_image_enabled": config.social_image_enabled,
        }

        tasks.append(
            asyncio.create_task(
                run_result_watcher(social_cfg, poll_interval=config.alert_poll_interval_seconds),
                name="result_watcher",
            )
        )
        _logger.info(
            "result_watcher job started (poll interval %ds)", config.alert_poll_interval_seconds
        )

        from sharpedge_webhooks.jobs.alert_poster import run_alert_poster

        alert_cfg = {
            **social_cfg,
            "min_ev_threshold": config.alert_min_ev_threshold,
            "cooldown_minutes": config.alert_cooldown_minutes,
            "value_alerts_channel_id": getattr(config, "value_alerts_channel_id", ""),
            "twitter_api_key": config.twitter_api_key,
            "twitter_api_secret": config.twitter_api_secret,
            "twitter_access_token": config.twitter_access_token,
            "twitter_access_token_secret": config.twitter_access_token_secret,
            "push_notifications_enabled": config.push_notifications_enabled,
            "firebase_service_account_json": config.firebase_service_account_json,
        }

        tasks.append(
            asyncio.create_task(
                run_alert_poster(alert_cfg, poll_interval=config.alert_poll_interval_seconds),
                name="alert_poster",
            )
        )
        _logger.info("alert_poster job started")
    else:
        _logger.info("Social posting disabled (ALERT_ENABLED=false)")

    if config.line_monitor_enabled:
        from sharpedge_webhooks.jobs.line_movement_monitor import run_line_movement_monitor

        line_monitor_cfg = {
            "odds_api_key": config.odds_api_key,
            "ev_threshold": config.line_monitor_ev_threshold,
        }
        tasks.append(
            asyncio.create_task(
                run_line_movement_monitor(
                    line_monitor_cfg,
                    poll_interval=config.line_monitor_interval_seconds,
                ),
                name="line_movement_monitor",
            )
        )
        _logger.info("line_movement_monitor started")

    return tasks


async def stop_background_tasks(tasks: list[asyncio.Task]) -> None:
    from contextlib import suppress

    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    _logger.info("Background jobs stopped")


@asynccontextmanager
async def copilot_postgres_scope(app: FastAPI) -> AsyncIterator[None]:
    """If COPILOT_DATABASE_URL or DATABASE_URL is set, hold AsyncPostgresSaver for app lifetime."""
    dsn = (os.environ.get("COPILOT_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        app.state.copilot_graph = None
        app.state.copilot_persist_threads = False
        yield
        return

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph
    except ImportError as e:
        _logger.warning("Copilot Postgres checkpointer unavailable (import): %s", e)
        app.state.copilot_graph = None
        app.state.copilot_persist_threads = False
        yield
        return

    try:
        async with AsyncPostgresSaver.from_conn_string(dsn) as checkpointer:
            await checkpointer.setup()
            app.state.copilot_graph = build_copilot_graph(checkpointer=checkpointer)
            app.state.copilot_persist_threads = True
            _logger.info("BettingCopilot Postgres checkpointer enabled")
            yield
    except Exception as e:
        _logger.warning("Copilot Postgres checkpointer failed: %s", e)
        app.state.copilot_graph = None
        app.state.copilot_persist_threads = False
        yield
