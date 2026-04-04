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
    stale: bool = False  # True if returned from cache due to API failure


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
