import logging
import asyncio
from datetime import date, timedelta

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.alerts import build_webhook_payload
from src.services import garmin, cache

logger = logging.getLogger(__name__)


async def sync_health_data():
    """Full daily sync: pull all health data from Garmin and store in Supabase cache."""
    logger.info("Starting daily health sync...")
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    sleep, stats, battery = None, None, None

    try:
        sleep = await garmin.get_sleep_data(today)
        cache.set("sleep", today, sleep.model_dump())
        logger.info(f"Sleep synced: score={sleep.sleep_score}, HRV={sleep.hrv_last_night}")
    except Exception as e:
        logger.error(f"Sleep sync failed: {e}")

    try:
        stats = await garmin.get_daily_stats(today)
        cache.set("daily_stats", today, stats.model_dump())
        logger.info(f"Daily stats synced: steps={stats.total_steps}, stress={stats.avg_stress_level}")
    except Exception as e:
        logger.error(f"Daily stats sync failed: {e}")

    try:
        battery = await garmin.get_body_battery()
        cache.set("body_battery", today, battery.model_dump())
        logger.info(f"Body Battery synced: {battery.current_level}%")
    except Exception as e:
        logger.error(f"Body Battery sync failed: {e}")

    try:
        activity = await garmin.get_activity()
        if activity.activity_id:
            cache.set("activity", activity.start_time[:10] if activity.start_time else today, activity.model_dump())
            logger.info(f"Activity synced: {activity.activity_type} / {activity.activity_name}")
    except Exception as e:
        logger.error(f"Activity sync failed: {e}")

    await send_webhook(sleep, stats, battery)
    logger.info("Daily health sync complete.")


async def send_webhook(sleep, stats, battery):
    """Send health data + alert triggers to n8n webhook."""
    if not settings.n8n_webhook_url:
        logger.debug("No n8n webhook configured, skipping.")
        return

    payload = build_webhook_payload(sleep, stats, battery)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                settings.n8n_webhook_url,
                json=payload.model_dump(),
                headers={"Authorization": f"Bearer {settings.n8n_bearer_token}"},
            )
            response.raise_for_status()
            logger.info(f"Webhook sent: {response.status_code}, triggers={payload.alert_triggers}")
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")


def start_scheduler() -> AsyncIOScheduler:
    """Initialize and start APScheduler for daily sync."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_health_data,
        trigger="cron",
        hour=settings.sync_hour,
        minute=settings.sync_minute,
        id="daily_health_sync",
        name="Daily Garmin health sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — daily sync at {settings.sync_hour:02d}:{settings.sync_minute:02d}")
    return scheduler
