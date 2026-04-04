# Garmin MCP Tools Expansion — Design Spec

**Date:** 2026-04-03
**Status:** Approved

---

## Context

The current implementation has 6 MCP tools. Competitor implementations have 22–96+ tools. The primary use case is a Mia AI health assistant (read queries: "how did I sleep", "should I train today", "analyze my run"). We are expanding to 18 tools by adding 12 new read-only tools across training metrics, detailed health, weight/body composition, and user profile. Write operations are deferred to a future iteration.

---

## Architecture

### Module restructure

`main.py` becomes a thin bootstrap — MCP setup + REST endpoints only. Tools move to `src/tools/`, models split by domain into `src/models/`.

```
main.py                          — MCP server init, REST endpoints (/health, /sync, /sse)
                                   imports: from src.tools import register_all_tools

src/
  tools/
    __init__.py                  — register_all_tools(mcp) helper
    health.py                    — sleep, body_battery, daily_stats, health_summary, stress,
                                   heart_rate, spo2_respiration, hydration  (8 tools)
    training.py                  — activities, activity, training_status, vo2max,
                                   training_load, race_predictions  (6 tools)
    profile.py                   — user_profile, personal_records, fitness_age,
                                   weight_history  (4 tools)

  models/
    __init__.py                  — re-exports all models
    health.py                    — SleepData, BodyBatteryData, BodyBatteryEntry, DailyStats,
                                   StressData, HeartRateData, SpO2RespirationData, HydrationData
    training.py                  — HRZone, LapData, ActivitySummary, ActivityData, ActivityList,
                                   TrainingStatus, VO2MaxData, TrainingLoad, RacePredictions
    profile.py                   — UserProfile, PersonalRecord, PersonalRecords,
                                   WeightEntry, WeightHistory, FitnessAge
    alerts.py                    — WebhookPayload

  garmin_client.py               — existing auth/retry logic + ~10 new API methods
  cache.py                       — no changes
  scheduler.py                   — no changes
  alerts.py                      — no changes
  config.py                      — no changes
```

### Migration of existing code

- 6 existing tools in `main.py` → split into `src/tools/health.py` (sleep, body_battery, daily_stats, health_summary) and `src/tools/training.py` (activities, activity)
- All models in `src/models.py` → split into domain files under `src/models/`
- `src/models.py` deleted after migration
- `main.py` reduced to ~30 lines

---

## New Tools (12)

### Training metrics

| Tool | Parameters | Returns | Cache TTL |
|------|-----------|---------|-----------|
| `get_training_status` | `date` (optional, default today) | training_status string, readiness_score 0–100, acute_load, chronic_load, load_ratio | CACHE_TTL_DAILY (1h) |
| `get_vo2max` | `sport` (optional: running/cycling, default running) | current value, fitness_age_equivalent, 30-day history | CACHE_TTL_DAILY (1h) |
| `get_training_load` | `date` (optional, default current week) | total_load, aerobic_low, aerobic_high, anaerobic breakdown | CACHE_TTL_DAILY (1h) |
| `get_race_predictions` | none | predicted finish times: 5k, 10k, half marathon, marathon in seconds | CACHE_TTL_DAILY (1h) |

### Detailed health

| Tool | Parameters | Returns | Cache TTL |
|------|-----------|---------|-----------|
| `get_stress_data` | `date` (optional, default today) | avg_stress, max_stress, rest_stress, activity_stress, hourly values | CACHE_TTL_DAILY (1h) |
| `get_heart_rate` | `date` (optional, default today) | resting_hr, max_hr, min_hr, hourly breakdown | CACHE_TTL_DAILY (1h) |
| `get_spo2_respiration` | `date` (optional, default last night) | avg_spo2, min_spo2, avg_respiration, max_respiration | CACHE_TTL_DAILY (1h) |
| `get_hydration` | `date` (optional, default today) | goal_ml, intake_ml, percent_complete | CACHE_TTL_DAILY (1h) |

### Weight & body composition

| Tool | Parameters | Returns | Cache TTL |
|------|-----------|---------|-----------|
| `get_weight_history` | `days` (optional, default 30) | list of WeightEntry (date, weight_kg, bmi, body_fat_percent?), avg/min/max | CACHE_TTL_HISTORICAL (24h) |

### User profile

| Tool | Parameters | Returns | Cache TTL |
|------|-----------|---------|-----------|
| `get_user_profile` | none | display_name, full_name, birth_date, gender, weight_kg, height_cm | CACHE_TTL_HISTORICAL (24h) |
| `get_personal_records` | `activity_type` (optional) | list of PRs per sport with value + date | CACHE_TTL_HISTORICAL (24h) |
| `get_fitness_age` | none | current_age, fitness_age, potential_fitness_age | CACHE_TTL_DAILY (1h) |

---

## Data Models

### `src/models/health.py` (new models)

```python
class StressData(BaseModel):
    date: str
    avg_stress: Optional[int]
    max_stress: Optional[int]
    rest_stress: Optional[int]
    activity_stress: Optional[int]
    hourly_values: Optional[list[dict]]  # [{time, stress_level}]
    stale: bool = False

class HeartRateData(BaseModel):
    date: str
    resting_hr: Optional[int]
    max_hr: Optional[int]
    min_hr: Optional[int]
    hourly_values: Optional[list[dict]]  # [{time, hr}]
    stale: bool = False

class SpO2RespirationData(BaseModel):
    date: str
    avg_spo2: Optional[float]
    min_spo2: Optional[float]
    avg_respiration: Optional[float]
    max_respiration: Optional[float]
    stale: bool = False

class HydrationData(BaseModel):
    date: str
    goal_ml: Optional[int]
    intake_ml: Optional[int]
    percent_complete: Optional[float]
    stale: bool = False
```

### `src/models/training.py` (new models)

```python
class TrainingStatus(BaseModel):
    date: str
    training_status: Optional[str]
    training_readiness_score: Optional[int]
    acute_load: Optional[float]
    chronic_load: Optional[float]
    load_ratio: Optional[float]
    stale: bool = False

class VO2MaxHistory(BaseModel):
    date: str
    value: Optional[float]

class VO2MaxData(BaseModel):
    sport: str
    value: Optional[float]
    fitness_age_equivalent: Optional[int]
    history: Optional[list[VO2MaxHistory]]
    stale: bool = False

class TrainingLoad(BaseModel):
    week_start: str
    total_load: Optional[float]
    aerobic_low: Optional[float]
    aerobic_high: Optional[float]
    anaerobic: Optional[float]
    stale: bool = False

class RacePredictions(BaseModel):
    race_5k_seconds: Optional[int]
    race_10k_seconds: Optional[int]
    half_marathon_seconds: Optional[int]
    marathon_seconds: Optional[int]
    stale: bool = False
```

### `src/models/profile.py` (new models)

```python
class UserProfile(BaseModel):
    display_name: Optional[str]
    full_name: Optional[str]
    birth_date: Optional[str]
    gender: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    stale: bool = False

class PersonalRecord(BaseModel):
    activity_type: Optional[str]
    type_key: Optional[str]
    value: Optional[float]
    pr_date: Optional[str]

class PersonalRecords(BaseModel):
    records: list[PersonalRecord] = []
    stale: bool = False

class WeightEntry(BaseModel):
    date: str
    weight_kg: Optional[float]
    bmi: Optional[float]
    body_fat_percent: Optional[float]

class WeightHistory(BaseModel):
    entries: list[WeightEntry] = []
    avg_weight_kg: Optional[float]
    min_weight_kg: Optional[float]
    max_weight_kg: Optional[float]
    stale: bool = False

class FitnessAge(BaseModel):
    current_age: Optional[int]
    fitness_age: Optional[int]
    potential_fitness_age: Optional[int]
    stale: bool = False
```

---

## Garmin API endpoints (new in `garmin_client.py`)

All new methods follow existing pattern: `asyncio.to_thread` + `@with_retry`.

| Method | Garmin endpoint |
|--------|----------------|
| `get_training_status(date)` | `/metrics-service/metrics/trainingStatus/daily/{date}` |
| `get_training_readiness(date)` | `/metrics-service/metrics/trainingReadiness/{date}` |
| `get_vo2max(sport)` | `/metrics-service/metrics/maxMet/latest/{displayName}` |
| `get_training_load(week_start)` | `/metrics-service/metrics/trainingLoad/daily/{date}` |
| `get_race_predictions()` | `/metrics-service/metrics/racePredictions/{displayName}` |
| `get_stress_data(date)` | `/wellness-service/wellness/dailyStress/{date}` |
| `get_heart_rates(date)` | `/wellness-service/wellness/dailyHeartRate/{displayName}` |
| `get_spo2_data(date)` | `/wellness-service/wellness/daily/spo2/{date}` |
| `get_respiration_data(date)` | `/wellness-service/wellness/daily/respiration/{date}` |
| `get_hydration_data(date)` | `/usersummary-service/usersummary/hydration/allData/{date}` |
| `get_weight_entries(start, end)` | `/weight-service/weight/dateRange` |
| `get_user_profile()` | `/userprofile-service/userprofile/personal-information` (already exists, extend) |
| `get_personal_records()` | `/activitylist-service/records/list` |
| `get_fitness_age()` | `/metrics-service/metrics/fitnessAge/{displayName}` |

---

## Verification

```bash
# 1. Server starts cleanly
python main.py

# 2. Health endpoint
curl http://localhost:8080/health

# 3. All 12 new tools via MCP (Claude Desktop or test client)
get_training_status()
get_vo2max()
get_training_load()
get_race_predictions()
get_stress_data()
get_heart_rate()
get_spo2_respiration()
get_hydration()
get_weight_history()
get_user_profile()
get_personal_records()
get_fitness_age()

# 4. Smoke test existing tools (regression)
get_sleep_data()
get_daily_stats()
get_body_battery()
get_activities()
get_activity()
get_health_summary()

# 5. Cache works (second call faster, stale=false)
# 6. No import errors in any src/ module
```
