"""Weekly retrain scheduler — MODEL-01.

Schedules a weekly cron job (Sunday 02:00 UTC) that retrains the ensemble
model using resolved game data from Supabase.

Requires: uv add apscheduler --package apps/webhook_server

Usage:
    from sharpedge_webhooks.jobs.retrain_scheduler import start_retrain_scheduler
    scheduler = start_retrain_scheduler()
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("sharpedge.jobs.retrain_scheduler")

_scheduler: AsyncIOScheduler | None = None


def _sync_retrain() -> None:
    """Synchronous retrain function — runs in a thread executor.

    Loads training data from Supabase (best-effort) and calls train_ensemble.
    Any failure is logged and does not crash the scheduler.
    """
    try:
        from sharpedge_models.ensemble_trainer import train_ensemble

        logger.info("Starting weekly ensemble retrain")
        # Load resolved game data from Supabase (best-effort; offline-safe)
        try:
            from sharpedge_db.client import get_supabase_client

            client = get_supabase_client()
            response = client.table("resolved_games").select("*").execute()
            records = response.data or []
            logger.info("Loaded %d resolved games for retraining", len(records))
        except Exception as db_exc:
            logger.warning("Supabase unavailable, retraining with empty data: %s", db_exc)
            records = []

        train_ensemble(records)
        logger.info("Weekly ensemble retrain complete")
    except Exception as exc:
        logger.error("Weekly retrain failed: %s", exc, exc_info=True)


async def weekly_retrain_job() -> None:
    """Async cron job — offloads CPU-bound retraining to thread executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_retrain)


def start_retrain_scheduler() -> AsyncIOScheduler:
    """Create, configure, and start the APScheduler AsyncIOScheduler.

    Registers the weekly_retrain_job as a cron job (every Sunday at 02:00 UTC).

    Returns:
        A running AsyncIOScheduler instance.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        weekly_retrain_job,
        trigger="cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        id="weekly_retrain",
        replace_existing=True,
    )
    # Ensure an event loop exists before starting AsyncIOScheduler
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    scheduler._eventloop = loop
    scheduler.start()
    return scheduler
