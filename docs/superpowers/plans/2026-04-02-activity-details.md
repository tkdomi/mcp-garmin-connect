# Activity Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `get_last_activity` to return per-km splits, cadence, HR zones, and VO2 Max by making additional Garmin API calls internally.

**Architecture:** `GarminClient.get_last_activity()` makes 3 sequential API calls (activity list → activity detail → laps), aggregates results into an enriched `ActivityData` model. `main.py` requires no changes. New fields degrade gracefully to `None` if secondary API calls fail.

**Tech Stack:** Python, garth, Pydantic v2, pytest, unittest.mock

---

### Task 1: Add `HRZone` and `LapData` models and extend `ActivityData`

**Files:**
- Modify: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Install pytest (if not present)**

```bash
pip install pytest pytest-asyncio
echo "pytest>=8.0.0\npytest-asyncio>=0.23.0" >> requirements.txt
```

- [ ] **Step 2: Write failing tests for new models**

Create `tests/__init__.py` (empty), then create `tests/test_models.py`:

```python
from src.models import HRZone, LapData, ActivityData


def test_hr_zone_defaults():
    z = HRZone(zone_number=1)
    assert z.zone_number == 1
    assert z.time_in_zone_seconds is None


def test_lap_data_defaults():
    lap = LapData(lap_index=0)
    assert lap.lap_index == 0
    assert lap.distance_meters is None
    assert lap.duration_seconds is None
    assert lap.avg_pace_per_km_seconds is None
    assert lap.avg_heart_rate is None
    assert lap.avg_cadence is None


def test_activity_data_has_new_fields():
    a = ActivityData()
    assert a.avg_cadence is None
    assert a.max_cadence is None
    assert a.vo2_max is None
    assert a.hr_zones is None
    assert a.laps is None


def test_activity_data_with_laps_and_zones():
    a = ActivityData(
        activity_id=123,
        laps=[LapData(lap_index=0, distance_meters=1000.0, duration_seconds=300.0, avg_pace_per_km_seconds=300, avg_heart_rate=150, avg_cadence=170)],
        hr_zones=[HRZone(zone_number=2, time_in_zone_seconds=600)],
        avg_cadence=168,
        max_cadence=185,
        vo2_max=52.3,
    )
    assert len(a.laps) == 1
    assert a.laps[0].avg_pace_per_km_seconds == 300
    assert len(a.hr_zones) == 1
    assert a.hr_zones[0].zone_number == 2
    assert a.vo2_max == 52.3
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/domi/IdeaProjects/mcp-garmin-connect && python -m pytest tests/test_models.py -v
```

Expected: `ImportError` or `AttributeError` — `HRZone`, `LapData` not defined yet.

- [ ] **Step 4: Add new models and extend `ActivityData` in `src/models.py`**

Add after the `BodyBatteryEntry` class (line 21) and update `ActivityData`:

```python
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
```

Replace the `ActivityData` class with:

```python
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
    avg_cadence: Optional[int] = None
    max_cadence: Optional[int] = None
    vo2_max: Optional[float] = None
    hr_zones: Optional[List[HRZone]] = None
    laps: Optional[List[LapData]] = None
    stale: bool = False
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/models.py tests/test_models.py tests/__init__.py requirements.txt
git commit -m "feat: add HRZone, LapData models and extend ActivityData with cadence/VO2/laps/hr_zones"
```

---

### Task 2: Extend `GarminClient.get_last_activity()` with additional API calls

**Files:**
- Modify: `src/garmin_client.py`
- Create: `tests/test_garmin_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_garmin_client.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.garmin_client import GarminClient
from src.models import ActivityData, LapData, HRZone


MOCK_ACTIVITY_LIST = [{
    "activityId": 99001,
    "activityName": "Morning Run",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2026-04-02 08:00:00",
    "duration": 1800.0,
    "distance": 5000.0,
    "averageHR": 155,
    "maxHR": 175,
    "calories": 400.0,
    "averageSpeed": 2.78,
    "elevationGain": 30.0,
}]

MOCK_ACTIVITY_DETAIL = {
    "summaryDTO": {
        "averageRunningCadenceInStepsPerMinute": 168,
        "maxRunningCadenceInStepsPerMinute": 182,
        "vO2MaxValue": 51.0,
    },
    "heartRateZones": [
        {"zoneNumber": 1, "secsInZone": 120},
        {"zoneNumber": 2, "secsInZone": 300},
        {"zoneNumber": 3, "secsInZone": 600},
        {"zoneNumber": 4, "secsInZone": 720},
        {"zoneNumber": 5, "secsInZone": 60},
    ],
}

MOCK_LAPS = [
    {
        "lapIndex": 0,
        "distance": 1000.0,
        "duration": 295.0,
        "averageHR": 152,
        "averageRunCadence": 166,
    },
    {
        "lapIndex": 1,
        "distance": 1000.0,
        "duration": 305.0,
        "averageHR": 158,
        "averageRunCadence": 170,
    },
]


def make_connectapi_side_effect(activity_id):
    """Returns different mock data depending on the endpoint called."""
    def side_effect(endpoint, **kwargs):
        if "search/activities" in endpoint:
            return MOCK_ACTIVITY_LIST
        elif f"/activity/{activity_id}/laps" in endpoint:
            return {"lapDTOs": MOCK_LAPS}
        elif f"/activity/{activity_id}" in endpoint:
            return MOCK_ACTIVITY_DETAIL
        return {}
    return side_effect


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


@pytest.mark.asyncio
async def test_get_last_activity_returns_enriched_data():
    client = GarminClient()
    client._authenticated = True

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi",
                   side_effect=make_connectapi_side_effect(99001)):
            result = await client.get_last_activity()

    assert isinstance(result, ActivityData)
    assert result.activity_id == 99001
    assert result.avg_cadence == 168
    assert result.max_cadence == 182
    assert result.vo2_max == 51.0
    assert len(result.hr_zones) == 5
    assert result.hr_zones[0].zone_number == 1
    assert result.hr_zones[0].time_in_zone_seconds == 120
    assert len(result.laps) == 2
    assert result.laps[0].lap_index == 0
    assert result.laps[0].distance_meters == 1000.0
    assert result.laps[0].avg_pace_per_km_seconds == 295  # 295s / 1000m * 1000
    assert result.laps[0].avg_heart_rate == 152
    assert result.laps[0].avg_cadence == 166


@pytest.mark.asyncio
async def test_get_last_activity_degrades_gracefully_on_detail_failure():
    """If the detail/laps API calls fail, return base data with new fields as None."""
    client = GarminClient()
    client._authenticated = True

    call_count = 0

    def side_effect(endpoint, **kwargs):
        nonlocal call_count
        call_count += 1
        if "search/activities" in endpoint:
            return MOCK_ACTIVITY_LIST
        raise Exception("403 Forbidden")

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_last_activity()

    assert result.activity_id == 99001
    assert result.avg_cadence is None
    assert result.laps is None
    assert result.hr_zones is None


@pytest.mark.asyncio
async def test_get_last_activity_empty_list():
    client = GarminClient()
    client._authenticated = True

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=[]):
            result = await client.get_last_activity()

    assert result == ActivityData()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_garmin_client.py -v
```

Expected: tests fail because `get_last_activity` doesn't fetch detail/laps yet.

- [ ] **Step 3: Extend `get_last_activity` in `src/garmin_client.py`**

Replace the `get_last_activity` method (lines 150-177) with:

```python
@with_retry
async def get_last_activity(self) -> ActivityData:
    """Fetch the most recent activity with splits, cadence, HR zones, and VO2 Max."""
    self._ensure_auth()

    data = await asyncio.to_thread(
        garth.connectapi,
        "/activitylist-service/activities/search/activities",
        params={"limit": 1, "start": 0}
    )

    if not data:
        return ActivityData()

    a = data[0]
    activity_id = a.get("activityId")

    base = ActivityData(
        activity_id=activity_id,
        activity_name=a.get("activityName"),
        activity_type=a.get("activityType", {}).get("typeKey"),
        start_time=a.get("startTimeLocal"),
        duration_seconds=a.get("duration"),
        distance_meters=a.get("distance"),
        avg_heart_rate=a.get("averageHR"),
        max_heart_rate=a.get("maxHR"),
        calories=a.get("calories"),
        avg_speed=a.get("averageSpeed"),
        elevation_gain=a.get("elevationGain"),
    )

    if not activity_id:
        return base

    try:
        detail = await asyncio.to_thread(
            garth.connectapi,
            f"/activity-service/activity/{activity_id}",
        )
        summary = detail.get("summaryDTO", {})
        base.avg_cadence = summary.get("averageRunningCadenceInStepsPerMinute")
        base.max_cadence = summary.get("maxRunningCadenceInStepsPerMinute")
        base.vo2_max = summary.get("vO2MaxValue")
        base.hr_zones = [
            HRZone(
                zone_number=z["zoneNumber"],
                time_in_zone_seconds=z.get("secsInZone"),
            )
            for z in detail.get("heartRateZones", [])
        ]
    except Exception as e:
        logger.warning(f"Could not fetch activity detail for {activity_id}: {e}")

    try:
        laps_data = await asyncio.to_thread(
            garth.connectapi,
            f"/activity-service/activity/{activity_id}/laps",
        )
        lap_dtos = laps_data.get("lapDTOs", []) if isinstance(laps_data, dict) else []
        base.laps = []
        for lap in lap_dtos:
            dist = lap.get("distance")
            dur = lap.get("duration")
            pace = round(dur / dist * 1000) if dist and dur and dist > 0 else None
            base.laps.append(LapData(
                lap_index=lap.get("lapIndex", 0),
                distance_meters=dist,
                duration_seconds=dur,
                avg_pace_per_km_seconds=pace,
                avg_heart_rate=lap.get("averageHR"),
                avg_cadence=lap.get("averageRunCadence"),
            ))
    except Exception as e:
        logger.warning(f"Could not fetch laps for {activity_id}: {e}")

    return base
```

- [ ] **Step 4: Update import in `src/garmin_client.py`**

The import line at the top already imports `ActivityData`. Add `HRZone` and `LapData` to the same import:

```python
from src.models import SleepData, BodyBatteryData, DailyStats, ActivityData, BodyBatteryEntry, HRZone, LapData
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/ -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/garmin_client.py tests/test_garmin_client.py
git commit -m "feat: extend get_last_activity with splits, cadence, HR zones, and VO2 Max"
```

---

### Task 3: Manual smoke test

- [ ] **Step 1: Start the server**

```bash
python main.py
```

Expected: server starts on port 8080, no errors.

- [ ] **Step 2: Trigger a sync and check the tool response**

In a second terminal:

```bash
curl -s http://localhost:8080/health
```

Expected: `{"status": "ok", "service": "garmin-mcp"}`

- [ ] **Step 3: Verify via MCP client or logs**

Call `get_last_activity` from your MCP client (e.g. Claude Desktop or the running garmin-mcp MCP server). Check that the response now includes `laps`, `hr_zones`, `avg_cadence`, `max_cadence`, `vo2_max` fields. New fields may be `None` if the Garmin API returns 403 for those endpoints — that is expected graceful degradation.
