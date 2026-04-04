# Garmin MCP Tools Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand from 6 to 18 MCP tools by adding training metrics, detailed health, weight/body composition, and user profile data — while refactoring into a modular `src/tools/` and `src/models/` package structure.

**Architecture:** Existing flat `src/models.py` splits into `src/models/{health,training,profile,alerts}.py`; existing 6 tools migrate from `main.py` to `src/tools/{health,training}.py`; 12 new tools added across `src/tools/{health,training,profile}.py`; `main.py` becomes a ~30-line bootstrap. Shared singletons (`GarminClient`, `CacheService`) live in `src/services.py`.

**Tech Stack:** Python 3.11+, mcp SDK (Server + Tool + TextContent), garth, pydantic v2, pytest + pytest-asyncio, unittest.mock

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/services.py` | Singleton `garmin` + `cache` shared across tools |
| Create | `src/models/__init__.py` | Re-export all models (backward compat) |
| Create | `src/models/health.py` | SleepData, BodyBatteryEntry/Data, DailyStats, HealthSummary, StressData, HeartRateData, SpO2RespirationData, HydrationData |
| Create | `src/models/training.py` | HRZone, LapData, ActivitySummary, ActivityData, ActivityList, TrainingStatus, VO2MaxData, VO2MaxHistory, TrainingLoad, RacePredictions |
| Create | `src/models/profile.py` | UserProfile, PersonalRecord, PersonalRecords, WeightEntry, WeightHistory, FitnessAge |
| Create | `src/models/alerts.py` | WebhookPayload |
| Delete | `src/models.py` | Replaced by package |
| Create | `src/tools/__init__.py` | `ALL_TOOLS` list + `dispatch(name, args)` router |
| Create | `src/tools/health.py` | 8 health tools: sleep, body_battery, daily_stats, health_summary, stress, heart_rate, spo2_respiration, hydration |
| Create | `src/tools/training.py` | 6 training tools: activities, activity, training_status, vo2max, training_load, race_predictions |
| Create | `src/tools/profile.py` | 4 profile tools: user_profile, personal_records, fitness_age, weight_history |
| Modify | `main.py` | Bootstrap only: import tools, register list_tools/call_tool handlers |
| Modify | `src/garmin_client.py` | Update model imports; add 10 new API methods |
| Modify | `src/cache.py` | Add new data types to DATA_TYPES dict |
| Modify | `src/alerts.py` | Update import path |
| Modify | `tests/test_models.py` | Update imports; add new model tests |
| Modify | `tests/test_garmin_client.py` | Update imports; add new client method tests |
| Create | `tests/test_tools_health.py` | Tests for new health tools |
| Create | `tests/test_tools_training.py` | Tests for new training tools |
| Create | `tests/test_tools_profile.py` | Tests for new profile tools |
| Modify | `README.md` | Update MCP Tools table with all 18 tools |

---

## Task 1: Split src/models.py into src/models/ package

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/health.py`
- Create: `src/models/training.py`
- Create: `src/models/alerts.py`
- Create: `src/models/profile.py` (empty placeholder for Task 5)
- Modify: `src/alerts.py`
- Delete: `src/models.py`

- [ ] **Step 1: Create `src/models/health.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, List


class SleepData(BaseModel):
    date: str
    sleep_score: Optional[int] = None
    total_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None
    hrv_weekly_average: Optional[float] = None
    hrv_last_night: Optional[float] = None
    avg_overnight_hrv: Optional[float] = None
    resting_heart_rate: Optional[int] = None
    stale: bool = False


class BodyBatteryEntry(BaseModel):
    timestamp: str
    level: int


class BodyBatteryData(BaseModel):
    current_level: Optional[int] = None
    charged: Optional[int] = None
    drained: Optional[int] = None
    trend: Optional[List[BodyBatteryEntry]] = None
    stale: bool = False


class DailyStats(BaseModel):
    date: str
    total_steps: Optional[int] = None
    step_goal: Optional[int] = None
    total_kilocalories: Optional[float] = None
    active_kilocalories: Optional[float] = None
    floors_ascended: Optional[int] = None
    minutes_sedentary: Optional[int] = None
    minutes_lightly_active: Optional[int] = None
    minutes_fairly_active: Optional[int] = None
    minutes_highly_active: Optional[int] = None
    avg_stress_level: Optional[int] = None
    max_stress_level: Optional[int] = None
    rest_stress_duration: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    stale: bool = False


class HealthSummary(BaseModel):
    days: int
    avg_sleep_score: Optional[float] = None
    avg_hrv: Optional[float] = None
    avg_steps: Optional[float] = None
    avg_stress: Optional[float] = None
    avg_resting_hr: Optional[float] = None
    total_activities: Optional[int] = None
    avg_body_battery_start: Optional[float] = None
    trends: dict = Field(default_factory=dict)
    stale: bool = False


class StressData(BaseModel):
    date: str
    avg_stress: Optional[int] = None
    max_stress: Optional[int] = None
    rest_stress: Optional[int] = None
    activity_stress: Optional[int] = None
    hourly_values: Optional[List[dict]] = None
    stale: bool = False


class HeartRateData(BaseModel):
    date: str
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    min_hr: Optional[int] = None
    hourly_values: Optional[List[dict]] = None
    stale: bool = False


class SpO2RespirationData(BaseModel):
    date: str
    avg_spo2: Optional[float] = None
    min_spo2: Optional[float] = None
    avg_respiration: Optional[float] = None
    max_respiration: Optional[float] = None
    stale: bool = False


class HydrationData(BaseModel):
    date: str
    goal_ml: Optional[int] = None
    intake_ml: Optional[int] = None
    percent_complete: Optional[float] = None
    stale: bool = False
```

- [ ] **Step 2: Create `src/models/training.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, List


class HRZone(BaseModel):
    zone_number: int
    time_in_zone_seconds: Optional[int] = None


class LapData(BaseModel):
    lap_index: int
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    avg_pace_per_km_seconds: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    avg_cadence: Optional[int] = None


class ActivitySummary(BaseModel):
    activity_id: Optional[int] = None
    activity_name: Optional[str] = None
    activity_type: Optional[str] = None
    start_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    distance_meters: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[float] = None
    avg_speed: Optional[float] = None
    elevation_gain: Optional[float] = None
    stale: bool = False


class ActivityList(BaseModel):
    activities: List[ActivitySummary] = Field(default_factory=list)
    count: int = 0
    stale: bool = False


class ActivityData(BaseModel):
    activity_id: Optional[int] = None
    activity_name: Optional[str] = None
    activity_type: Optional[str] = None
    start_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    distance_meters: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[float] = None
    avg_speed: Optional[float] = None
    elevation_gain: Optional[float] = None
    avg_cadence: Optional[float] = None
    max_cadence: Optional[float] = None
    avg_power: Optional[int] = None
    normalized_power: Optional[int] = None
    training_effect: Optional[float] = None
    anaerobic_training_effect: Optional[float] = None
    stride_length_cm: Optional[float] = None
    vertical_oscillation_cm: Optional[float] = None
    ground_contact_time_ms: Optional[float] = None
    steps: Optional[int] = None
    hr_zones: Optional[List[HRZone]] = None
    laps: Optional[List[LapData]] = None
    stale: bool = False


class TrainingStatus(BaseModel):
    date: str
    training_status: Optional[str] = None
    training_readiness_score: Optional[int] = None
    acute_load: Optional[float] = None
    chronic_load: Optional[float] = None
    load_ratio: Optional[float] = None
    stale: bool = False


class VO2MaxHistory(BaseModel):
    date: str
    value: Optional[float] = None


class VO2MaxData(BaseModel):
    sport: str
    value: Optional[float] = None
    fitness_age_equivalent: Optional[int] = None
    history: Optional[List[VO2MaxHistory]] = None
    stale: bool = False


class TrainingLoad(BaseModel):
    week_start: str
    total_load: Optional[float] = None
    aerobic_low: Optional[float] = None
    aerobic_high: Optional[float] = None
    anaerobic: Optional[float] = None
    stale: bool = False


class RacePredictions(BaseModel):
    race_5k_seconds: Optional[int] = None
    race_10k_seconds: Optional[int] = None
    half_marathon_seconds: Optional[int] = None
    marathon_seconds: Optional[int] = None
    stale: bool = False
```

- [ ] **Step 3: Create `src/models/alerts.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WebhookPayload(BaseModel):
    event: str = "health_synced"
    body_battery: Optional[int] = None
    sleep_score: Optional[int] = None
    hrv: Optional[float] = None
    steps: Optional[int] = None
    avg_stress: Optional[int] = None
    alert_triggers: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
```

- [ ] **Step 4: Create `src/models/profile.py`** (placeholder, populated in Task 5)

```python
# Populated in Task 5
```

- [ ] **Step 5: Create `src/models/__init__.py`** (re-export everything for backward compat)

```python
from src.models.health import (
    SleepData,
    BodyBatteryEntry,
    BodyBatteryData,
    DailyStats,
    HealthSummary,
    StressData,
    HeartRateData,
    SpO2RespirationData,
    HydrationData,
)
from src.models.training import (
    HRZone,
    LapData,
    ActivitySummary,
    ActivityList,
    ActivityData,
    TrainingStatus,
    VO2MaxData,
    VO2MaxHistory,
    TrainingLoad,
    RacePredictions,
)
from src.models.alerts import WebhookPayload

__all__ = [
    "SleepData", "BodyBatteryEntry", "BodyBatteryData", "DailyStats", "HealthSummary",
    "StressData", "HeartRateData", "SpO2RespirationData", "HydrationData",
    "HRZone", "LapData", "ActivitySummary", "ActivityList", "ActivityData",
    "TrainingStatus", "VO2MaxData", "VO2MaxHistory", "TrainingLoad", "RacePredictions",
    "WebhookPayload",
]
```

- [ ] **Step 6: Update `src/alerts.py` import**

Change line 5 from:
```python
from src.models import WebhookPayload, SleepData, DailyStats, BodyBatteryData
```
to:
```python
from src.models.alerts import WebhookPayload
from src.models.health import SleepData, DailyStats, BodyBatteryData
```

- [ ] **Step 7: Run existing tests to verify no regressions**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 8: Delete `src/models.py`**

```bash
rm src/models.py
```

- [ ] **Step 9: Run tests again to confirm clean import path**

```bash
pytest tests/ -v
```
Expected: All tests still pass.

- [ ] **Step 10: Commit**

```bash
git add src/models/ src/alerts.py
git rm src/models.py
git commit -m "refactor: split src/models.py into src/models/ package"
```

---

## Task 2: Create src/services.py + src/tools/ package, migrate 6 existing tools, slim main.py

**Files:**
- Create: `src/services.py`
- Create: `src/tools/__init__.py`
- Create: `src/tools/health.py`
- Create: `src/tools/training.py`
- Modify: `main.py`
- Modify: `src/garmin_client.py` (update model imports)

- [ ] **Step 1: Create `src/services.py`**

```python
from src.garmin_client import GarminClient
from src.cache import CacheService

garmin = GarminClient()
cache = CacheService()
```

- [ ] **Step 2: Update `src/garmin_client.py` model import line**

Change line 12 from:
```python
from src.models import SleepData, BodyBatteryData, DailyStats, ActivityData, BodyBatteryEntry, HRZone, LapData, ActivitySummary, ActivityList
```
to:
```python
from src.models.health import SleepData, BodyBatteryData, BodyBatteryEntry, DailyStats
from src.models.training import ActivityData, HRZone, LapData, ActivitySummary, ActivityList
```

- [ ] **Step 3: Run existing tests to confirm garmin_client still works**

```bash
pytest tests/test_garmin_client.py -v
```
Expected: All tests pass.

- [ ] **Step 4: Create `src/tools/health.py`** (migrate 4 existing health tools from main.py)

```python
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
        avg_resting_hr=avg([r.get("resting_heart_rate") for r in sleep_records]),
        total_activities=total_activities,
    )
    return summary.model_dump()
```

- [ ] **Step 5: Create `src/tools/training.py`** (migrate 2 existing training tools from main.py)

```python
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
```

- [ ] **Step 6: Create `src/tools/__init__.py`**

```python
from src.tools import health, training

ALL_TOOLS = health.TOOL_DEFINITIONS + training.TOOL_DEFINITIONS


async def dispatch(name: str, arguments: dict):
    for module in [health, training]:
        result = await module.handle(name, arguments)
        if result is not None:
            return result
    return None
```

- [ ] **Step 7: Rewrite `main.py`** to use the tools package

```python
import asyncio
import logging

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from src.config import settings
from src.scheduler import start_scheduler, sync_health_data
from src.tools import ALL_TOOLS, dispatch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = Server("garmin-mcp")


@mcp.list_tools()
async def list_tools():
    return ALL_TOOLS


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"Tool called: {name} | args: {arguments}")
    try:
        result = await dispatch(name, arguments)
        if result is None:
            result = {"error": f"Unknown tool: {name}"}
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"Tool error ({name}): {e}")
        return [TextContent(type="text", text=f"Error fetching data: {str(e)}")]


async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "garmin-mcp"})


async def manual_sync(request: Request):
    asyncio.create_task(sync_health_data())
    return JSONResponse({"status": "sync_started"})


sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())


@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health_check),
        Route("/sync", manual_sync, methods=["POST"]),
        Route("/sse", handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.mcp_port, log_level="info")
```

- [ ] **Step 8: Run all tests to confirm migration is clean**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/services.py src/tools/ main.py src/garmin_client.py
git commit -m "refactor: migrate tools to src/tools/ package, slim main.py"
```

---

## Task 3: Add new health tools (stress, heart_rate, spo2_respiration, hydration)

**Files:**
- Modify: `src/garmin_client.py`
- Modify: `src/tools/health.py`
- Modify: `src/cache.py`
- Create: `tests/test_tools_health.py`

- [ ] **Step 1: Write failing tests for new garmin client methods**

Create `tests/test_tools_health.py`:

```python
import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.health import StressData, HeartRateData, SpO2RespirationData, HydrationData


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_STRESS = {
    "overallStressLevel": 32,
    "maxStressLevel": 65,
    "restStressDuration": 7200,
    "activityStressDuration": 3600,
    "stressValuesArray": [[1743667200000, 28], [1743670800000, 35]],
}

MOCK_HEART_RATE = {
    "restingHeartRate": 52,
    "maxHeartRate": 178,
    "minHeartRate": 48,
    "heartRateValues": [[1743667200000, 55], [1743670800000, 58]],
}

MOCK_SPO2 = {
    "averageSpO2": 97.2,
    "lowestSpO2": 94.0,
}

MOCK_RESPIRATION = {
    "avgWakingRespirationValue": 14.5,
    "highestRespirationValue": 18.0,
}

MOCK_HYDRATION = {
    "valueInML": 1800,
    "goalInML": 2500,
}


@pytest.mark.asyncio
async def test_get_stress_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_STRESS):
            result = await client.get_stress_data("2026-04-03")

    assert isinstance(result, StressData)
    assert result.date == "2026-04-03"
    assert result.avg_stress == 32
    assert result.max_stress == 65
    assert result.rest_stress == 7200
    assert result.activity_stress == 3600
    assert len(result.hourly_values) == 2


@pytest.mark.asyncio
async def test_get_heart_rate_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_HEART_RATE):
            result = await client.get_heart_rate_data("2026-04-03")

    assert isinstance(result, HeartRateData)
    assert result.resting_hr == 52
    assert result.max_hr == 178
    assert result.min_hr == 48
    assert len(result.hourly_values) == 2


@pytest.mark.asyncio
async def test_get_spo2_respiration_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    def side_effect(endpoint, **kwargs):
        if "spo2" in endpoint:
            return MOCK_SPO2
        return MOCK_RESPIRATION

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_spo2_respiration("2026-04-03")

    assert isinstance(result, SpO2RespirationData)
    assert result.avg_spo2 == 97.2
    assert result.min_spo2 == 94.0
    assert result.avg_respiration == 14.5
    assert result.max_respiration == 18.0


@pytest.mark.asyncio
async def test_get_hydration_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_HYDRATION):
            result = await client.get_hydration_data("2026-04-03")

    assert isinstance(result, HydrationData)
    assert result.intake_ml == 1800
    assert result.goal_ml == 2500
    assert result.percent_complete == pytest.approx(72.0, rel=0.01)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_tools_health.py -v
```
Expected: FAIL — `GarminClient` has no `get_stress_data`, `get_heart_rate_data`, `get_spo2_respiration`, `get_hydration_data` methods.

- [ ] **Step 3: Add 4 new methods to `src/garmin_client.py`**

Replace the health models import line (set in Task 2) with:
```python
from src.models.health import (
    SleepData, BodyBatteryData, BodyBatteryEntry, DailyStats,
    StressData, HeartRateData, SpO2RespirationData, HydrationData,
)
```

Then add these methods to the `GarminClient` class (after `get_daily_stats`):

```python
    @with_retry
    async def get_stress_data(self, target_date: Optional[str] = None) -> StressData:
        """Fetch hourly stress data for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/wellness-service/wellness/dailyStress/{target_date}",
        )

        hourly = [
            {"time": entry[0], "stress_level": entry[1]}
            for entry in (data.get("stressValuesArray") or [])
            if entry[1] is not None and entry[1] >= 0
        ]

        return StressData(
            date=target_date,
            avg_stress=data.get("overallStressLevel"),
            max_stress=data.get("maxStressLevel"),
            rest_stress=data.get("restStressDuration"),
            activity_stress=data.get("activityStressDuration"),
            hourly_values=hourly or None,
        )

    @with_retry
    async def get_heart_rate_data(self, target_date: Optional[str] = None) -> HeartRateData:
        """Fetch detailed heart rate data for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/wellness-service/wellness/dailyHeartRate/{self._display_name}",
            params={"date": target_date},
        )

        hourly = [
            {"time": entry[0], "hr": entry[1]}
            for entry in (data.get("heartRateValues") or [])
            if entry[1] is not None
        ]

        return HeartRateData(
            date=target_date,
            resting_hr=data.get("restingHeartRate"),
            max_hr=data.get("maxHeartRate"),
            min_hr=data.get("minHeartRate"),
            hourly_values=hourly or None,
        )

    @with_retry
    async def get_spo2_respiration(self, target_date: Optional[str] = None) -> SpO2RespirationData:
        """Fetch SpO2 and respiration data for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = (date.today() - timedelta(days=1)).isoformat()

        spo2_data, resp_data = await asyncio.gather(
            asyncio.to_thread(
                garth.connectapi,
                f"/wellness-service/wellness/daily/spo2/{target_date}",
            ),
            asyncio.to_thread(
                garth.connectapi,
                f"/wellness-service/wellness/daily/respiration/{target_date}",
            ),
        )

        return SpO2RespirationData(
            date=target_date,
            avg_spo2=spo2_data.get("averageSpO2") if spo2_data else None,
            min_spo2=spo2_data.get("lowestSpO2") if spo2_data else None,
            avg_respiration=resp_data.get("avgWakingRespirationValue") if resp_data else None,
            max_respiration=resp_data.get("highestRespirationValue") if resp_data else None,
        )

    @with_retry
    async def get_hydration_data(self, target_date: Optional[str] = None) -> HydrationData:
        """Fetch hydration goal and intake for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/usersummary-service/usersummary/hydration/allData/{target_date}",
        )

        intake = data.get("valueInML")
        goal = data.get("goalInML")
        pct = round(intake / goal * 100, 1) if intake and goal and goal > 0 else None

        return HydrationData(
            date=target_date,
            goal_ml=goal,
            intake_ml=intake,
            percent_complete=pct,
        )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_tools_health.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 5: Add 4 new tool definitions + handlers to `src/tools/health.py`**

Append to `TOOL_DEFINITIONS` list in `src/tools/health.py`:

```python
    Tool(
        name="get_stress_data",
        description=(
            "Returns hourly stress levels throughout the day: average, max, rest vs activity stress. "
            "Use when the user asks about stress, anxiety level, or relaxation."
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
        name="get_heart_rate",
        description=(
            "Returns detailed heart rate data for a day: resting HR, max HR, min HR, and hourly breakdown. "
            "Use when the user asks about heart rate trends, resting HR, or cardiovascular data."
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
        name="get_spo2_respiration",
        description=(
            "Returns blood oxygen saturation (SpO2) and respiration rate. "
            "Use when the user asks about oxygen levels, breathing, or sleep quality vitals."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Defaults to last night.",
                }
            },
        },
    ),
    Tool(
        name="get_hydration",
        description=(
            "Returns daily hydration goal, intake in ml, and completion percentage. "
            "Use when the user asks about water intake or hydration."
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
```

Add to `handle()` function in `src/tools/health.py`:

```python
    if name == "get_stress_data":
        return await _get_stress_data(arguments.get("date"))
    if name == "get_heart_rate":
        return await _get_heart_rate(arguments.get("date"))
    if name == "get_spo2_respiration":
        return await _get_spo2_respiration(arguments.get("date"))
    if name == "get_hydration":
        return await _get_hydration(arguments.get("date"))
```

Add these implementation functions to `src/tools/health.py`:

```python
async def _get_stress_data(target_date: Optional[str] = None):
    if not target_date:
        target_date = date.today().isoformat()
    cached = cache.get("stress", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_stress_data(target_date)
        cache.set("stress", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for stress data, trying stale cache: {e}")
        stale = cache.get_stale("stress", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_heart_rate(target_date: Optional[str] = None):
    if not target_date:
        target_date = date.today().isoformat()
    cached = cache.get("heart_rate", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_heart_rate_data(target_date)
        cache.set("heart_rate", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for heart rate data, trying stale cache: {e}")
        stale = cache.get_stale("heart_rate", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_spo2_respiration(target_date: Optional[str] = None):
    if not target_date:
        target_date = (date.today() - timedelta(days=1)).isoformat()
    cached = cache.get("spo2_respiration", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_spo2_respiration(target_date)
        cache.set("spo2_respiration", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for SpO2/respiration, trying stale cache: {e}")
        stale = cache.get_stale("spo2_respiration", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise


async def _get_hydration(target_date: Optional[str] = None):
    if not target_date:
        target_date = date.today().isoformat()
    cached = cache.get("hydration", target_date)
    if cached:
        return cached
    try:
        data = await garmin.get_hydration_data(target_date)
        cache.set("hydration", target_date, data.model_dump())
        return data.model_dump()
    except Exception as e:
        logger.warning(f"Garmin API failed for hydration, trying stale cache: {e}")
        stale = cache.get_stale("hydration", target_date)
        if stale:
            stale["stale"] = True
            return stale
        raise
```

- [ ] **Step 6: Update `src/cache.py` DATA_TYPES**

Add new health types to the `DATA_TYPES` dict:

```python
DATA_TYPES = {
    "sleep": settings.cache_ttl_historical,
    "daily_stats": settings.cache_ttl_daily,
    "body_battery": settings.cache_ttl_daily,
    "activity": settings.cache_ttl_daily,
    "stress": settings.cache_ttl_daily,
    "heart_rate": settings.cache_ttl_daily,
    "spo2_respiration": settings.cache_ttl_historical,
    "hydration": settings.cache_ttl_daily,
}
```

- [ ] **Step 7: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/garmin_client.py src/tools/health.py src/cache.py tests/test_tools_health.py
git commit -m "feat: add health tools (stress, heart_rate, spo2_respiration, hydration)"
```

---

## Task 4: Add new training tools (training_status, vo2max, training_load, race_predictions)

**Files:**
- Modify: `src/garmin_client.py`
- Modify: `src/tools/training.py`
- Modify: `src/tools/__init__.py`
- Modify: `src/cache.py`
- Create: `tests/test_tools_training.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tools_training.py`:

```python
import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.training import TrainingStatus, VO2MaxData, TrainingLoad, RacePredictions


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_TRAINING_STATUS = {
    "trainingStatusDTO": {
        "latestTrainingStatusPhrase": "Productive",
        "trainingReadinessDTO": {"score": 72},
        "acuteLoad": 420.0,
        "chronicLoad": 385.0,
    }
}

MOCK_VO2MAX = {
    "generic": {
        "vo2MaxValue": 52.0,
        "fitnessAge": 34,
    },
    "running": {
        "vo2MaxValue": 52.0,
    }
}

MOCK_TRAINING_LOAD = {
    "metricsMap": {
        "TRAINING_LOAD_7_DAYS": [
            {"value": 520.0, "startDate": "2026-03-27"}
        ]
    },
    "aerobicLowLoad": 180.0,
    "aerobicHighLoad": 250.0,
    "anaerobicLoad": 90.0,
}

MOCK_RACE_PREDICTIONS = {
    "racePredictions": [
        {"distance": 5000, "time": 1380},
        {"distance": 10000, "time": 2880},
        {"distance": 21097, "time": 6300},
        {"distance": 42195, "time": 13200},
    ]
}


@pytest.mark.asyncio
async def test_get_training_status_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_TRAINING_STATUS):
            result = await client.get_training_status("2026-04-03")

    assert isinstance(result, TrainingStatus)
    assert result.date == "2026-04-03"
    assert result.training_status == "Productive"
    assert result.training_readiness_score == 72
    assert result.acute_load == 420.0
    assert result.chronic_load == 385.0


@pytest.mark.asyncio
async def test_get_vo2max_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_VO2MAX):
            result = await client.get_vo2max("running")

    assert isinstance(result, VO2MaxData)
    assert result.sport == "running"
    assert result.value == 52.0
    assert result.fitness_age_equivalent == 34


@pytest.mark.asyncio
async def test_get_training_load_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_TRAINING_LOAD):
            result = await client.get_training_load("2026-03-27")

    assert isinstance(result, TrainingLoad)
    assert result.week_start == "2026-03-27"
    assert result.total_load == 520.0
    assert result.aerobic_low == 180.0
    assert result.aerobic_high == 250.0
    assert result.anaerobic == 90.0


@pytest.mark.asyncio
async def test_get_race_predictions_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_RACE_PREDICTIONS):
            result = await client.get_race_predictions()

    assert isinstance(result, RacePredictions)
    assert result.race_5k_seconds == 1380
    assert result.race_10k_seconds == 2880
    assert result.half_marathon_seconds == 6300
    assert result.marathon_seconds == 13200
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_tools_training.py -v
```
Expected: FAIL — methods not yet on `GarminClient`.

- [ ] **Step 3: Add training imports to `src/garmin_client.py`**

Replace the training models import line (set in Task 2) with:
```python
from src.models.training import (
    ActivityData, HRZone, LapData, ActivitySummary, ActivityList,
    TrainingStatus, VO2MaxData, VO2MaxHistory, TrainingLoad, RacePredictions,
)
```

- [ ] **Step 4: Add 4 new methods to `GarminClient` in `src/garmin_client.py`**

```python
    @with_retry
    async def get_training_status(self, target_date: Optional[str] = None) -> TrainingStatus:
        """Fetch training status and readiness for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/metrics-service/metrics/trainingStatus/daily/{target_date}",
            params={"displayName": self._display_name},
        )

        dto = data.get("trainingStatusDTO", {}) if data else {}
        readiness = dto.get("trainingReadinessDTO", {}) or {}
        acute = dto.get("acuteLoad")
        chronic = dto.get("chronicLoad")
        ratio = round(acute / chronic, 2) if acute and chronic and chronic > 0 else None

        return TrainingStatus(
            date=target_date,
            training_status=dto.get("latestTrainingStatusPhrase"),
            training_readiness_score=readiness.get("score"),
            acute_load=acute,
            chronic_load=chronic,
            load_ratio=ratio,
        )

    @with_retry
    async def get_vo2max(self, sport: str = "running") -> VO2MaxData:
        """Fetch VO2 max value for a given sport."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/metrics-service/metrics/maxMet/latest/{self._display_name}",
        )

        generic = data.get("generic", {}) if data else {}
        sport_data = data.get(sport, {}) if data else {}
        value = sport_data.get("vo2MaxValue") or generic.get("vo2MaxValue")

        return VO2MaxData(
            sport=sport,
            value=value,
            fitness_age_equivalent=generic.get("fitnessAge"),
        )

    @with_retry
    async def get_training_load(self, week_start: Optional[str] = None) -> TrainingLoad:
        """Fetch weekly training load breakdown."""
        self._ensure_auth()
        if not week_start:
            today = date.today()
            week_start = (today - timedelta(days=today.weekday())).isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/metrics-service/metrics/trainingLoad/daily/{week_start}",
            params={"displayName": self._display_name},
        )

        metrics = data.get("metricsMap", {}) if data else {}
        load_entries = metrics.get("TRAINING_LOAD_7_DAYS", [{}])
        total = load_entries[0].get("value") if load_entries else None

        return TrainingLoad(
            week_start=week_start,
            total_load=total,
            aerobic_low=data.get("aerobicLowLoad") if data else None,
            aerobic_high=data.get("aerobicHighLoad") if data else None,
            anaerobic=data.get("anaerobicLoad") if data else None,
        )

    @with_retry
    async def get_race_predictions(self) -> RacePredictions:
        """Fetch race time predictions from Garmin."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/metrics-service/metrics/racePredictions/{self._display_name}",
        )

        predictions = {p["distance"]: p["time"] for p in (data.get("racePredictions") or [])}

        return RacePredictions(
            race_5k_seconds=predictions.get(5000),
            race_10k_seconds=predictions.get(10000),
            half_marathon_seconds=predictions.get(21097),
            marathon_seconds=predictions.get(42195),
        )
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_tools_training.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 6: Add tool definitions + handlers to `src/tools/training.py`**

Append to `TOOL_DEFINITIONS` in `src/tools/training.py`:

```python
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
```

Add to `handle()` in `src/tools/training.py`:

```python
    if name == "get_training_status":
        return await _get_training_status(arguments.get("date"))
    if name == "get_vo2max":
        return await _get_vo2max(arguments.get("sport", "running"))
    if name == "get_training_load":
        return await _get_training_load(arguments.get("week_start"))
    if name == "get_race_predictions":
        return await _get_race_predictions()
```

Add implementation functions to `src/tools/training.py`:

```python
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
```

- [ ] **Step 7: Update `src/cache.py` DATA_TYPES**

```python
DATA_TYPES = {
    "sleep": settings.cache_ttl_historical,
    "daily_stats": settings.cache_ttl_daily,
    "body_battery": settings.cache_ttl_daily,
    "activity": settings.cache_ttl_daily,
    "stress": settings.cache_ttl_daily,
    "heart_rate": settings.cache_ttl_daily,
    "spo2_respiration": settings.cache_ttl_historical,
    "hydration": settings.cache_ttl_daily,
    "training_status": settings.cache_ttl_daily,
    "vo2max_running": settings.cache_ttl_daily,
    "vo2max_cycling": settings.cache_ttl_daily,
    "training_load": settings.cache_ttl_daily,
    "race_predictions": settings.cache_ttl_daily,
}
```

- [ ] **Step 8: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/garmin_client.py src/tools/training.py src/cache.py tests/test_tools_training.py
git commit -m "feat: add training tools (training_status, vo2max, training_load, race_predictions)"
```

---

## Task 5: Add new profile tools (user_profile, personal_records, fitness_age, weight_history)

**Files:**
- Modify: `src/models/profile.py`
- Modify: `src/models/__init__.py`
- Modify: `src/garmin_client.py`
- Create: `src/tools/profile.py`
- Modify: `src/tools/__init__.py`
- Modify: `src/cache.py`
- Create: `tests/test_tools_profile.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tools_profile.py`:

```python
import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.profile import UserProfile, PersonalRecords, WeightHistory, FitnessAge


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_PROFILE = {
    "displayName": "runner42",
    "fullName": "Jan Kowalski",
    "userEmail": "jan@example.com",
    "birthDate": "1990-05-15",
    "genderType": "MALE",
    "weight": 75000.0,  # grams
    "height": 180.0,    # cm
}

MOCK_PERSONAL_RECORDS = [
    {"activityType": "running", "typeKey": "fastest5K", "value": 1320.0, "activityStartDateTimeLocal": "2025-10-12"},
    {"activityType": "running", "typeKey": "longestRun", "value": 42195.0, "activityStartDateTimeLocal": "2025-04-06"},
]

MOCK_FITNESS_AGE = {
    "chronologicalAge": 35,
    "fitnessAge": 28,
    "potentialFitnessAge": 25,
}

MOCK_WEIGHT_ENTRIES = [
    {"samplePk": 1, "date": "2026-04-01 08:00:00", "weight": 75200.0, "bmi": 23.2, "bodyFat": 18.5},
    {"samplePk": 2, "date": "2026-03-25 08:00:00", "weight": 75500.0, "bmi": 23.3, "bodyFat": 18.8},
]


@pytest.mark.asyncio
async def test_get_user_profile_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_PROFILE):
            result = await client.get_user_profile()

    assert isinstance(result, UserProfile)
    assert result.display_name == "runner42"
    assert result.full_name == "Jan Kowalski"
    assert result.birth_date == "1990-05-15"
    assert result.gender == "MALE"
    assert result.weight_kg == pytest.approx(75.0, rel=0.01)
    assert result.height_cm == 180.0


@pytest.mark.asyncio
async def test_get_personal_records_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_PERSONAL_RECORDS):
            result = await client.get_personal_records()

    assert isinstance(result, PersonalRecords)
    assert len(result.records) == 2
    assert result.records[0].type_key == "fastest5K"
    assert result.records[0].value == 1320.0
    assert result.records[0].pr_date == "2025-10-12"


@pytest.mark.asyncio
async def test_get_fitness_age_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_FITNESS_AGE):
            result = await client.get_fitness_age()

    assert isinstance(result, FitnessAge)
    assert result.current_age == 35
    assert result.fitness_age == 28
    assert result.potential_fitness_age == 25


@pytest.mark.asyncio
async def test_get_weight_history_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value={"dailyWeightSummaries": MOCK_WEIGHT_ENTRIES}):
            result = await client.get_weight_history(30)

    assert isinstance(result, WeightHistory)
    assert len(result.entries) == 2
    assert result.entries[0].weight_kg == pytest.approx(75.2, rel=0.01)
    assert result.entries[0].body_fat_percent == 18.5
    assert result.avg_weight_kg is not None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_tools_profile.py -v
```
Expected: FAIL — `src.models.profile` has no content, `GarminClient` has no profile methods.

- [ ] **Step 3: Populate `src/models/profile.py`**

```python
from pydantic import BaseModel
from typing import Optional, List


class UserProfile(BaseModel):
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    stale: bool = False


class PersonalRecord(BaseModel):
    activity_type: Optional[str] = None
    type_key: Optional[str] = None
    value: Optional[float] = None
    pr_date: Optional[str] = None


class PersonalRecords(BaseModel):
    records: List[PersonalRecord] = []
    stale: bool = False


class WeightEntry(BaseModel):
    date: str
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_percent: Optional[float] = None


class WeightHistory(BaseModel):
    entries: List[WeightEntry] = []
    avg_weight_kg: Optional[float] = None
    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    stale: bool = False


class FitnessAge(BaseModel):
    current_age: Optional[int] = None
    fitness_age: Optional[int] = None
    potential_fitness_age: Optional[int] = None
    stale: bool = False
```

- [ ] **Step 4: Update `src/models/__init__.py`** to include profile models

Add to the imports and `__all__`:
```python
from src.models.profile import (
    UserProfile,
    PersonalRecord,
    PersonalRecords,
    WeightEntry,
    WeightHistory,
    FitnessAge,
)
```

And add to `__all__`:
```python
"UserProfile", "PersonalRecord", "PersonalRecords", "WeightEntry", "WeightHistory", "FitnessAge",
```

- [ ] **Step 5: Add profile client imports to `src/garmin_client.py`**

Add after existing health/training imports:
```python
from src.models.profile import UserProfile, PersonalRecord, PersonalRecords, WeightEntry, WeightHistory, FitnessAge
```

- [ ] **Step 6: Add 4 profile methods to `GarminClient` in `src/garmin_client.py`**

```python
    @with_retry
    async def get_user_profile(self) -> UserProfile:
        """Fetch user profile information."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            "/userprofile-service/userprofile/personal-information",
        )

        weight_g = data.get("weight")
        return UserProfile(
            display_name=data.get("displayName"),
            full_name=data.get("fullName"),
            birth_date=data.get("birthDate"),
            gender=data.get("genderType"),
            weight_kg=round(weight_g / 1000, 1) if weight_g else None,
            height_cm=data.get("height"),
        )

    @with_retry
    async def get_personal_records(self) -> PersonalRecords:
        """Fetch personal records across all sports."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/activitylist-service/records/list/{self._display_name}",
        )

        records = [
            PersonalRecord(
                activity_type=r.get("activityType"),
                type_key=r.get("typeKey"),
                value=r.get("value"),
                pr_date=(r.get("activityStartDateTimeLocal") or "")[:10] or None,
            )
            for r in (data or [])
        ]
        return PersonalRecords(records=records)

    @with_retry
    async def get_fitness_age(self) -> FitnessAge:
        """Fetch Garmin fitness age."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/metrics-service/metrics/fitnessAge/{self._display_name}",
        )

        return FitnessAge(
            current_age=data.get("chronologicalAge") if data else None,
            fitness_age=data.get("fitnessAge") if data else None,
            potential_fitness_age=data.get("potentialFitnessAge") if data else None,
        )

    @with_retry
    async def get_weight_history(self, days: int = 30) -> WeightHistory:
        """Fetch weight history for the past N days."""
        self._ensure_auth()
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days)).isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            "/weight-service/weight/dateRange",
            params={"startDate": start_date, "endDate": end_date},
        )

        summaries = data.get("dailyWeightSummaries", []) if data else []
        entries = []
        for s in summaries:
            weight_g = s.get("weight")
            entries.append(WeightEntry(
                date=(s.get("date") or "")[:10],
                weight_kg=round(weight_g / 1000, 1) if weight_g else None,
                bmi=s.get("bmi"),
                body_fat_percent=s.get("bodyFat"),
            ))

        weights = [e.weight_kg for e in entries if e.weight_kg is not None]
        return WeightHistory(
            entries=entries,
            avg_weight_kg=round(sum(weights) / len(weights), 1) if weights else None,
            min_weight_kg=min(weights) if weights else None,
            max_weight_kg=max(weights) if weights else None,
        )
```

- [ ] **Step 7: Run tests to confirm they pass**

```bash
pytest tests/test_tools_profile.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 8: Create `src/tools/profile.py`**

```python
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
```

- [ ] **Step 9: Update `src/tools/__init__.py`** to include profile tools

```python
from src.tools import health, training, profile

ALL_TOOLS = health.TOOL_DEFINITIONS + training.TOOL_DEFINITIONS + profile.TOOL_DEFINITIONS


async def dispatch(name: str, arguments: dict):
    for module in [health, training, profile]:
        result = await module.handle(name, arguments)
        if result is not None:
            return result
    return None
```

- [ ] **Step 10: Update `src/cache.py` DATA_TYPES**

```python
DATA_TYPES = {
    "sleep": settings.cache_ttl_historical,
    "daily_stats": settings.cache_ttl_daily,
    "body_battery": settings.cache_ttl_daily,
    "activity": settings.cache_ttl_daily,
    "stress": settings.cache_ttl_daily,
    "heart_rate": settings.cache_ttl_daily,
    "spo2_respiration": settings.cache_ttl_historical,
    "hydration": settings.cache_ttl_daily,
    "training_status": settings.cache_ttl_daily,
    "vo2max_running": settings.cache_ttl_daily,
    "vo2max_cycling": settings.cache_ttl_daily,
    "training_load": settings.cache_ttl_daily,
    "race_predictions": settings.cache_ttl_daily,
    "user_profile": settings.cache_ttl_historical,
    "personal_records": settings.cache_ttl_historical,
    "fitness_age": settings.cache_ttl_daily,
    "weight_history_30d": settings.cache_ttl_historical,
}
```

- [ ] **Step 11: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 12: Commit**

```bash
git add src/models/profile.py src/models/__init__.py src/garmin_client.py src/tools/profile.py src/tools/__init__.py src/cache.py tests/test_tools_profile.py
git commit -m "feat: add profile tools (user_profile, personal_records, fitness_age, weight_history)"
```

---

## Task 6: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the MCP Tools table in `README.md`**

Replace the existing tools table (lines 15–23) with:

```markdown
## MCP Tools

### Health & Wellness

| Tool | Description |
|------|-------------|
| `get_sleep_data` | Sleep quality, duration, phases (deep/light/REM), HRV, resting HR for a given date |
| `get_body_battery` | Current Body Battery level (0–100) and today's charge/drain trend |
| `get_daily_stats` | Steps, calories, active minutes, stress level for a given date |
| `get_stress_data` | Hourly stress levels throughout the day: average, max, rest vs activity stress |
| `get_heart_rate` | Detailed HR data: resting, max, min, hourly breakdown for a given date |
| `get_spo2_respiration` | Blood oxygen saturation (SpO2) and respiration rate |
| `get_hydration` | Daily hydration goal, intake in ml, and completion percentage |
| `get_health_summary` | Multi-day overview: avg sleep score, HRV, steps, stress, activity count |

### Training & Performance

| Tool | Description |
|------|-------------|
| `get_activities` | List of activities filtered by sport type and/or time period |
| `get_activity` | Full activity details: splits, cadence, power, HR zones, stride metrics, training effect |
| `get_training_status` | Training status (Productive/Maintaining/Detraining), readiness score, load ratio |
| `get_vo2max` | VO2 max value and fitness age equivalent for running or cycling |
| `get_training_load` | Weekly training load by intensity: aerobic low/high, anaerobic |
| `get_race_predictions` | Predicted finish times for 5K, 10K, half marathon, and marathon |

### Profile & Body

| Tool | Description |
|------|-------------|
| `get_user_profile` | Account details: name, birth date, gender, weight, height |
| `get_personal_records` | Personal bests across all sports (fastest 5K, longest run, etc.) |
| `get_fitness_age` | Garmin fitness age, chronological age, and potential fitness age |
| `get_weight_history` | Weight history with average, min, max over a configurable date range |
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with all 18 MCP tools"
```

---

## Verification

After all tasks complete:

```bash
# 1. Server starts without import errors
python main.py &
sleep 2

# 2. Health endpoint
curl http://localhost:8080/health
# Expected: {"status": "ok", "service": "garmin-mcp"}

# 3. Full test suite
pytest tests/ -v
# Expected: All tests pass

# 4. Manual MCP tool calls (via Claude Desktop or mcp-inspector)
# Test each of the 18 tools — smoke test that they return data or a graceful error

# 5. Cache test: call the same tool twice, second call should be faster
```
