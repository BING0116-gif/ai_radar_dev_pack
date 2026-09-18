"""Tests for the daily scheduler rebuild/manual fire (CARD-014)."""

from app.core.config import get_settings
from app.services.scheduler import build_scheduler, manual_fire


def _cron_values(scheduler):
    """Read hour/minute from the scheduler's cron trigger via its fields."""
    trigger = scheduler.get_job("daily-brief").trigger
    fields = {f.name: [str(e) for e in f.expressions] for f in trigger.fields}
    return fields["hour"][0], fields["minute"][0]


def test_job_built_from_config_and_manually_firable():
    fired = []

    def fake_job():
        fired.append("ran")

    scheduler = build_scheduler(job_func=fake_job)
    scheduler.start()
    try:
        assert scheduler.get_job("daily-brief") is not None
        hour, minute = _cron_values(scheduler)
        assert (hour, minute) == (
            str(get_settings().SCHEDULER_DAILY_HOUR),
            str(get_settings().SCHEDULER_DAILY_MINUTE),
        )
        manual_fire(scheduler)
        assert fired == ["ran"]
    finally:
        scheduler.shutdown(wait=False)


def test_scheduler_rebuilds_from_config_on_restart(monkeypatch):
    monkeypatch.setenv("SCHEDULER_DAILY_HOUR", "7")
    monkeypatch.setenv("SCHEDULER_DAILY_MINUTE", "30")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    get_settings.cache_clear()  # rebuild the singleton so it sees the new env
    scheduler = None
    try:
        scheduler = build_scheduler(job_func=lambda: None)
        scheduler.start()
        assert _cron_values(scheduler) == ("7", "30")
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        get_settings.cache_clear()


def test_scheduler_start_and_shutdown_ok():
    scheduler = build_scheduler(job_func=lambda: None)
    scheduler.start()
    assert scheduler.running is True
    scheduler.shutdown(wait=False)
    assert scheduler.running is False