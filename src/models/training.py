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
