import logging
from datetime import date
from typing import Optional

from mcp.types import Tool

from src.services import garmin, cache

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    Tool(
        name="get_user_profile",
        description=(
            "Returns user profile: display name, full name, birth date, gender, weight, height. "
            "Use when the user asks about their profile or account details."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_personal_records",
        description=(
            "Returns personal records (PRs) across all sports: fastest 5K, longest run, etc. "
            "Use when the user asks about their best performances or personal bests."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_fitness_age",
        description=(
            "Returns Garmin fitness age, chronological age, and potential fitness age. "
            "Use when the user asks about fitness age or overall fitness level."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_weight_history",
        description=(
            "Returns weight history with average, min, max over a date range. "
            "Use when the user asks about weight trends, body composition, or BMI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of past days to include. Defaults to 30.",
                }
            },
        },
    ),
]


async def handle(name: str, arguments: dict) -> Optional[dict]:
    if name == "get_user_profile":
        return await _get_user_profile()
    if name == "get_personal_records":
        return await _get_personal_records()
    if name == "get_fitness_age":
        return await _get_fitness_age()
    if name == "get_weight_history":
        return await _get_weight_history(arguments.get("days", 30))
    return None


async def _get_user_profile():
    today = date.today().isoformat()
    cached = cache.get("user_profile", today)
    if cached:
        return cached
    try:
        data = await garmin.get_user_profile()
        cache.set("user_profile", today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for user profile, trying stale cache: {e}")
        stale = cache.get_stale("user_profile", today)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_personal_records():
    today = date.today().isoformat()
    cached = cache.get("personal_records", today)
    if cached:
        return cached
    try:
        data = await garmin.get_personal_records()
        cache.set("personal_records", today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for personal records, trying stale cache: {e}")
        stale = cache.get_stale("personal_records", today)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_fitness_age():
    today = date.today().isoformat()
    cached = cache.get("fitness_age", today)
    if cached:
        return cached
    try:
        data = await garmin.get_fitness_age()
        cache.set("fitness_age", today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for fitness age, trying stale cache: {e}")
        stale = cache.get_stale("fitness_age", today)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_weight_history(days: int = 30):
    today = date.today().isoformat()
    cache_key = f"weight_history_{days}d"
    cached = cache.get(cache_key, today)
    if cached:
        return cached
    try:
        data = await garmin.get_weight_history(days)
        cache.set(cache_key, today, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for weight history, trying stale cache: {e}")
        stale = cache.get_stale(cache_key, today)
        if stale:
            stale["stale"] = True
            return stale
        raise
