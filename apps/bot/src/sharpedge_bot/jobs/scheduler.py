"""Background job scheduler using APScheduler."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("sharpedge.jobs")

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the singleton scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler(bot: object) -> None:
    """Start the background job scheduler with all jobs registered.

    Jobs are staggered to avoid all running at the same time:
    - Opening lines: every 30 min
    - Odds monitor: every 5 min (minute 0, 5, 10...)
    - Consensus: every 5 min (minute 1, 6, 11...)
    - Value scanner: every 5 min (minute 2, 7, 12...)
    - Arb scanner: every 5 min (minute 3, 8, 13...)
    - Alert dispatcher: every 5 min (minute 4, 9, 14...)
    - Prediction market scanner: every 2 min (fast for short-lived arbs)
    """
    scheduler = get_scheduler()

    # Import all job modules
    from sharpedge_bot.jobs.alert_dispatcher import dispatch_alerts
    from sharpedge_bot.jobs.arbitrage_scanner import scan_for_arbitrage_opportunities
    from sharpedge_bot.jobs.consensus_calc import calculate_consensus
    from sharpedge_bot.jobs.odds_monitor import monitor_odds
    from sharpedge_bot.jobs.opening_lines import capture_opening_lines
    from sharpedge_bot.jobs.prediction_market_scanner import scan_prediction_market_arbitrage
    from sharpedge_bot.jobs.value_scanner_job import scan_for_value_plays

    # ============================================
    # OPENING LINES - Capture first odds for games
    # Runs every 30 minutes
    # ============================================
    scheduler.add_job(
        capture_opening_lines,
        "interval",
        minutes=30,
        args=[bot],
        id="opening_lines",
        replace_existing=True,
    )

    # ============================================
    # ODDS MONITOR - Track line changes
    # Runs every 5 minutes at :00, :05, :10...
    # ============================================
    scheduler.add_job(
        monitor_odds,
        "cron",
        minute="*/5",
        second=0,
        args=[bot],
        id="odds_monitor",
        replace_existing=True,
    )

    # ============================================
    # CONSENSUS CALCULATOR - Aggregate market lines
    # Runs every 5 minutes at :01, :06, :11...
    # ============================================
    scheduler.add_job(
        calculate_consensus,
        "cron",
        minute="1,6,11,16,21,26,31,36,41,46,51,56",
        second=0,
        args=[bot],
        id="consensus_calc",
        replace_existing=True,
    )

    # ============================================
    # VALUE SCANNER - Find +EV opportunities
    # Runs every 5 minutes at :02, :07, :12...
    # ============================================
    scheduler.add_job(
        scan_for_value_plays,
        "cron",
        minute="2,7,12,17,22,27,32,37,42,47,52,57",
        second=0,
        args=[bot],
        id="value_scanner",
        replace_existing=True,
    )

    # ============================================
    # ARBITRAGE SCANNER - Find arb opportunities
    # Runs every 5 minutes at :03, :08, :13...
    # ============================================
    scheduler.add_job(
        scan_for_arbitrage_opportunities,
        "cron",
        minute="3,8,13,18,23,28,33,38,43,48,53,58",
        second=0,
        args=[bot],
        id="arb_scanner",
        replace_existing=True,
    )

    # ============================================
    # ALERT DISPATCHER - Send notifications
    # Runs every 5 minutes at :04, :09, :14...
    # ============================================
    scheduler.add_job(
        dispatch_alerts,
        "cron",
        minute="4,9,14,19,24,29,34,39,44,49,54,59",
        second=0,
        args=[bot],
        id="alert_dispatcher",
        replace_existing=True,
    )

    # ============================================
    # PREDICTION MARKET SCANNER - Cross-platform arbs
    # Runs every 2 minutes for short-lived opportunities
    # Kalshi/Polymarket arbs last 5-45 seconds during peak
    # ============================================
    scheduler.add_job(
        scan_prediction_market_arbitrage,
        "interval",
        minutes=2,
        args=[bot],
        id="pm_arb_scanner",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Background scheduler started with %d jobs: %s",
        len(scheduler.get_jobs()),
        ", ".join(job.id for job in scheduler.get_jobs()),
    )


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
