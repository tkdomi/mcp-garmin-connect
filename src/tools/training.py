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
]


async def handle(name: str, arguments: dict) -> Optional[dict]:
    if name == "get_activities":
        return await _get_activities(arguments.get("type"), arguments.get("period"))
    if name == "get_activity":
        return await _get_activity(arguments.get("activity_id"))
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
