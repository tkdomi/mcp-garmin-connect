# Activity Details — Design Spec

**Date:** 2026-04-02  
**Status:** Approved

## Goal

Extend the existing `get_last_activity` MCP tool to return rich training data: per-km splits, cadence, HR zones, and VO2 Max — without adding a new tool or changing the tool's interface.

## Approach

`get_last_activity` remains a zero-parameter tool. Internally, `GarminClient.get_last_activity()` makes three sequential Garmin API calls and aggregates the results into one enriched response.

## API Calls

1. `/activitylist-service/activities/search/activities?limit=1` — existing call, returns `activity_id` + summary fields
2. `/activity-service/activity/{activity_id}` — returns avg/max cadence, VO2 Max estimate
3. `/activity-service/activity/{activity_id}/laps` — returns per-lap (per-km) splits

## Data Model Changes (`src/models.py`)

### New models

```python
class HRZone(BaseModel):
    zone_number: int
    time_in_zone_seconds: Optional[int] = None

class LapData(BaseModel):
    lap_index: int
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    avg_pace_per_km_seconds: Optional[int] = None  # derived: duration/distance*1000
    avg_heart_rate: Optional[int] = None
    avg_cadence: Optional[int] = None
```

### Extended `ActivityData`

Add to existing fields:
```python
avg_cadence: Optional[int] = None
max_cadence: Optional[int] = None
vo2_max: Optional[float] = None
hr_zones: Optional[List[HRZone]] = None
laps: Optional[List[LapData]] = None
```

## Implementation Changes

### `src/garmin_client.py`

`get_last_activity()` extended to:
1. Fetch activity list (existing)
2. Fetch `/activity-service/activity/{activity_id}` for cadence and VO2 Max
3. Fetch `/activity-service/activity/{activity_id}/laps` for splits
4. Map all fields into the enriched `ActivityData` model

### `main.py`

No changes required — the tool registration and dispatch logic already handles `get_last_activity`.

## Cache Behavior

No change to cache key (`"activity"`, `start_date`). Since activity data is immutable after completion, the enriched data is cached on first fetch and served from cache on subsequent calls within the TTL window (`CACHE_TTL_DAILY`, default 1h).

## Error Handling

If calls 2 or 3 fail (e.g., 403 for older activities), the tool degrades gracefully: returns data from call 1 with the new fields as `None`. This matches the existing pattern of all `ActivityData` fields being `Optional`.

## Out of Scope

- GPS trace / map data
- Per-second HR/pace streams
- Activities other than the most recent one
