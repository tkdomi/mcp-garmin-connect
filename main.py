import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from src.config import settings
from src.garmin_client import GarminClient
from src.cache import CacheService
from src.scheduler import start_scheduler, sync_health_data
from src.models import HealthSummary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

garmin = GarminClient()
cache = CacheService()

# ─── MCP Server ──────────────────────────────────────────────────────────────

mcp = Server("garmin-mcp")


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
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
            name="get_last_activity",
            description=(
                "Returns details of the most recent recorded physical activity: "
                "type, name, duration, distance, average/max heart rate, and calories. "
                "Use when user asks about their last workout or run."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_health_summary",
            description=(
                "Returns a multi-day health overview: average sleep score, HRV, steps, stress, "
                "resting heart rate, and activity count. Useful for trend analysis and correlating "
                "health data with other domains (finances, mood, language learning)."
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


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"Tool called: {name} | args: {arguments}")

    try:
        if name == "get_sleep_data":
            result = await _get_sleep_data(arguments.get("date"))

        elif name == "get_body_battery":
            result = await _get_body_battery()

        elif name == "get_daily_stats":
            result = await _get_daily_stats(arguments.get("date"))

        elif name == "get_last_activity":
            result = await _get_last_activity()

        elif name == "get_health_summary":
            result = await _get_health_summary(arguments.get("days", 7))

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error(f"Tool error ({name}): {e}")
        return [TextContent(type="text", text=f"Error fetching data: {str(e)}")]


# ─── Tool implementations ────────────────────────────────────────────────────

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


async def _get_last_activity():
    today = date.today().isoformat()
    cached = cache.get("activity", today)
    if cached:
        return cached

    try:
        data = await garmin.get_last_activity()
        if data.start_time:
            cache.set("activity", data.start_time[:10], data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for activity: {e}")
        raise


async def _get_health_summary(days: int = 7):
    from_date = (date.today() - timedelta(days=days)).isoformat()
    to_date = date.today().isoformat()

    sleep_records = cache.get_range("sleep", from_date, to_date)
    stats_records = cache.get_range("daily_stats", from_date, to_date)

    def avg(values):
        clean = [v for v in values if v is not None]
        return round(sum(clean) / len(clean), 1) if clean else None

    summary = HealthSummary(
        days=days,
        avg_sleep_score=avg([r["raw_data"].get("sleep_score") for r in sleep_records]),
        avg_hrv=avg([r["raw_data"].get("hrv_last_night") for r in sleep_records]),
        avg_steps=avg([r["raw_data"].get("total_steps") for r in stats_records]),
        avg_stress=avg([r["raw_data"].get("avg_stress_level") for r in stats_records]),
        avg_resting_hr=avg([r["raw_data"].get("resting_heart_rate") for r in sleep_records]),
        total_activities=len(cache.get_range("activity", from_date, to_date)),
    )
    return summary.model_dump()


# ─── REST endpoints (health check + manual sync) ─────────────────────────────

async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "garmin-mcp"})


async def manual_sync(request: Request):
    asyncio.create_task(sync_health_data())
    return JSONResponse({"status": "sync_started"})


# ─── App startup ─────────────────────────────────────────────────────────────

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(
            streams[0], streams[1], mcp.create_initialization_options()
        )


app = Starlette(
    routes=[
        Route("/health", health_check),
        Route("/sync", manual_sync, methods=["POST"]),
        Route("/sse", handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
    on_startup=[lambda: start_scheduler()],
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.mcp_port,
        log_level="info",
    )
