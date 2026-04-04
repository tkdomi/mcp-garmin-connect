import logging
from datetime import date, timedelta
from typing import Optional

from mcp.types import Tool

from src.services import garmin, cache

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    Tool(
        name="get_activities",
        description=(
            "Returns a list of activities (type, duration, distance, HR, calories). "
            "Filter by sport type and/or time period. "
            "Use when the user asks about recent workouts, training history, or wants to browse activities."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Sport type filter: running, cycling, swimming, hiking, walking, strength.",
                    "enum": ["running", "cycling", "swimming", "hiking", "walking", "strength"],
                },
                "period": {
                    "type": "string",
                    "description": "Time period: today, yesterday, this_week, last_week, this_month, this_year. Omit for 10 most recent.",
                    "enum": ["today", "yesterday", "this_week", "last_week", "this_month", "this_year"],
                },
            },
        },
    ),
    Tool(
        name="get_activity",
        description=(
            "Returns full details of a single activity: splits, laps, cadence, power, "
            "HR zones, stride metrics, training effect. "
            "Use when the user asks about a specific workout in depth, or their last activity."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "Garmin activity ID (from get_activities). Omit to get the most recent activity.",
                }
            },
        },
    ),
    Tool(
        name="get_training_status",
        description=(
            "Returns training status (e.g. Productive, Maintaining, Detraining), "
            "training readiness score (0-100), and acute/chronic load ratio. "
            "Use when the user asks whether to train today, or about training readiness."
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
        name="get_vo2max",
        description=(
            "Returns VO2 max value and fitness age equivalent. "
            "Use when the user asks about aerobic fitness, VO2 max, or fitness age."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "sport": {
                    "type": "string",
                    "description": "Sport for VO2 max: running or cycling. Defaults to running.",
                    "enum": ["running", "cycling"],
                }
            },
        },
    ),
    Tool(
        name="get_training_load",
        description=(
            "Returns weekly training load broken down by intensity: aerobic low, aerobic high, anaerobic. "
            "Use when the user asks about training volume, load, or intensity distribution."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "description": "Monday of the week in YYYY-MM-DD format. Defaults to current week.",
                }
            },
        },
    ),
    Tool(
        name="get_race_predictions",
        description=(
            "Returns predicted race finish times for 5K, 10K, half marathon, and marathon. "
            "Use when the user asks about race predictions, goal paces, or running performance."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
]


async def handle(name: str, arguments: dict) -> Optional[dict]:
    if name == "get_activities":
        return await _get_activities(arguments.get("type"), arguments.get("period"))
    if name == "get_activity":
        return await _get_activity(arguments.get("activity_id"))
    if name == "get_training_status":
        return await _get_training_status(arguments.get("date"))
    if name == "get_vo2max":
        return await _get_vo2max(arguments.get("sport", "running"))
    if name == "get_training_load":
        return await _get_training_load(arguments.get("week_start"))
    if name == "get_race_predictions":
        return await _get_race_predictions()
    return None


def _resolve_period(period: str) -> tuple[str, str]:
    today = date.today()
    if period == "today":
        return today.isoformat(), today.isoformat()
    if period == "yesterday":
        d = today - timedelta(days=1)
        return d.isoformat(), d.isoformat()
    if period == "this_week":
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat(), today.isoformat()
    if period == "last_week":
        last_monday = today - timedelta(days=today.weekday() + 7)
        return last_monday.isoformat(), (last_monday + timedelta(days=6)).isoformat()
    if period == "this_month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if period == "this_year":
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    raise ValueError(f"Unknown period: {period}")


async def _get_activities(activity_type: Optional[str] = None, period: Optional[str] = None):
    start_date, end_date, limit = None, None, 10
    if period:
        start_date, end_date = _resolve_period(period)
        limit = 50
    try:
        data = await garmin.get_activities_list(
            activity_type=activity_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for activity list: {e}")
        raise


async def _get_activity(activity_id: Optional[int] = None):
    try:
        data = await garmin.get_activity(activity_id)
        if data.start_time:
            cache.set("activity", data.start_time[:10], data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for activity detail: {e}")
        if activity_id is None:
            stale = cache.get_stale("activity", date.today().isoformat())
            if stale:
                stale["stale"] = True
                return stale
        raise


async def _get_training_status(target_date: Optional[str] = None):
    if not target_date:
        target_date = date.today().isoformat()
    cached = cache.get("training_status", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_training_status(target_date)
        cache.set("training_status", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for training status, trying stale cache: {e}")
        stale = cache.get_stale("training_status", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_vo2max(sport: str = "running"):
    today = date.today().isoformat()
    cache_key = f"vo2max_{sport}"
    cached = cache.get(cache_key, today)
    if cached:
        return cached
    try:
        data = await garmin.get_vo2max(sport)
        cache.set(cache_key, today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for VO2 max, trying stale cache: {e}")
        stale = cache.get_stale(cache_key, today)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_training_load(week_start: Optional[str] = None):
    if not week_start:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
    cached = cache.get("training_load", week_start)
    if cached:
        return cached
    try:
        data = await garmin.get_training_load(week_start)
        cache.set("training_load", week_start, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for training load, trying stale cache: {e}")
        stale = cache.get_stale("training_load", week_start)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_race_predictions():
    today = date.today().isoformat()
    cached = cache.get("race_predictions", today)
    if cached:
        return cached
    try:
        data = await garmin.get_race_predictions()
        cache.set("race_predictions", today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for race predictions, trying stale cache: {e}")
        stale = cache.get_stale("race_predictions", today)
        if stale:
            stale["stale"] = True
            return stale
        raise
