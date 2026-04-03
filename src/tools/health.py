import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from mcp.types import Tool

from src.models.health import HealthSummary
from src.services import garmin, cache

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    Tool(
        name="get_sleep_data",
        description=(
            "Returns sleep quality, duration, sleep phases (deep/light/REM), "
            "HRV, and resting heart rate for a given date. "
            "Use when the user asks about sleep, recovery, or HRV."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Defaults to last night if not provided.",
                }
            },
        },
    ),
    Tool(
        name="get_body_battery",
        description=(
            "Returns the current Garmin Body Battery level (0-100) and today's charge/drain trend. "
            "Use when user asks about energy, fatigue, or readiness."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_daily_stats",
        description=(
            "Returns daily activity stats: steps, calories, active minutes, and average stress level. "
            "Use when the user asks about today's activity, steps, or stress."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Defaults to today.",
                }
            },
        },
    ),
    Tool(
        name="get_health_summary",
        description=(
            "Returns a multi-day health overview: average sleep score, HRV, steps, stress, "
            "resting heart rate, and activity count. Useful for trend analysis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of past days to include in the summary. Defaults to 7.",
                }
            },
        },
    ),
]


async def handle(name: str, arguments: dict) -> Optional[dict]:
    if name == "get_sleep_data":
        return await _get_sleep_data(arguments.get("date"))
    if name == "get_body_battery":
        return await _get_body_battery()
    if name == "get_daily_stats":
        return await _get_daily_stats(arguments.get("date"))
    if name == "get_health_summary":
        return await _get_health_summary(arguments.get("days", 7))
    return None


async def _get_sleep_data(target_date: Optional[str] = None):
    if not target_date:
        target_date = (date.today() - timedelta(days=1)).isoformat()
    cached = cache.get("sleep", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_sleep_data(target_date)
        cache.set("sleep", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for sleep, trying stale cache: {e}")
        stale = cache.get_stale("sleep", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_body_battery():
    today = date.today().isoformat()
    cached = cache.get("body_battery", today)
    if cached:
        return cached
    try:
        data = await garmin.get_body_battery()
        cache.set("body_battery", today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for body battery, trying stale cache: {e}")
        stale = cache.get_stale("body_battery", today)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_daily_stats(target_date: Optional[str] = None):
    if not target_date:
        target_date = date.today().isoformat()
    cached = cache.get("daily_stats", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_daily_stats(target_date)
        cache.set("daily_stats", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for daily stats, trying stale cache: {e}")
        stale = cache.get_stale("daily_stats", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_health_summary(days: int = 7):
    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(days)]
    sleep_results, stats_results = await asyncio.gather(
        asyncio.gather(*[_get_sleep_data(d) for d in dates], return_exceptions=True),
        asyncio.gather(*[_get_daily_stats(d) for d in dates], return_exceptions=True),
    )
    sleep_records = [r for r in sleep_results if isinstance(r, dict)]
    stats_records = [r for r in stats_results if isinstance(r, dict)]

    def avg(values):
        clean = [v for v in values if v is not None]
        return round(sum(clean) / len(clean), 1) if clean else None

    total_activities = len(cache.get_range("activity", dates[-1], dates[0]))
    summary = HealthSummary(
        days=days,
        avg_sleep_score=avg([r.get("sleep_score") for r in sleep_records]),
        avg_hrv=avg([r.get("hrv_last_night") for r in sleep_records]),
        avg_steps=avg([r.get("total_steps") for r in stats_records]),
        avg_stress=avg([r.get("avg_stress_level") for r in stats_records]),
        avg_resting_hr=avg([r.get("resting_heart_rate") for r in stats_records]),
        total_activities=total_activities,
    )
    return summary.model_dump()
