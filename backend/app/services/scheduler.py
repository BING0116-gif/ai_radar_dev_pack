"""Daily scheduler: triggers ``run_agent`` on a configurable schedule.

The scheduler's only job is *when* to run — it never decides tool order or
content. Jobs are rebuilt from Settings on every start (config is the source
of truth, so "restart restores the schedule" holds by construction). The
default jobstore is in-memory; for durable schedules, swap in a persistent
jobstore later.
"""

import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings

logger = logging.getLogger("app.services.scheduler")

JOB_ID = "daily-brief"


def build_scheduler(job_func: Callable | None = None) -> BackgroundScheduler:
    """Build (not started) a scheduler with the daily cron job from Settings.

    ``job_func`` defaults to the real run entry point and is injectable for
    tests/manual firing.
    """
    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_func or run_daily_brief,
        trigger=CronTrigger(hour=settings.SCHEDULER_DAILY_HOUR, minute=settings.SCHEDULER_DAILY_MINUTE),
        id=JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    return scheduler


def manual_fire(scheduler: BackgroundScheduler) -> None:
    """Trigger the daily job once, outside its cron time (for demos/manual runs)."""
    job = scheduler.get_job(JOB_ID)
    if job is None:
        raise LookupError(f"scheduled job '{JOB_ID}' not found")
    job.func()


def run_daily_brief() -> None:
    """Scheduler entry: run the demo user's daily brief in a fresh session."""
    from app.db import SessionLocal
    from app.services.runs import run_agent

    with SessionLocal() as db:
        from app.models import User

        user = db.query(User).order_by(User.id).first()
        if user is None:
            logger.warning("scheduled run skipped: no demo user")
            return
        summary = run_agent(db, user.id, reason="scheduled")
        logger.info("scheduled run summary=%s", summary)