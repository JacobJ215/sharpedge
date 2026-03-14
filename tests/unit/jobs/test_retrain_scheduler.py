"""RED stub for retrain_scheduler — MODEL-01.

Fails with ImportError until Plan 05-05 creates
apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sharpedge_webhooks.jobs.retrain_scheduler import start_retrain_scheduler


def test_retrain_scheduler_starts():
    """start_retrain_scheduler() returns a running AsyncIOScheduler."""
    scheduler = start_retrain_scheduler()
    assert isinstance(scheduler, AsyncIOScheduler), (
        f"Expected AsyncIOScheduler, got {type(scheduler)}"
    )
    assert scheduler.running is True, (
        "start_retrain_scheduler() must call scheduler.start() before returning"
    )
    # Cleanup
    scheduler.shutdown(wait=False)
