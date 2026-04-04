from pydantic import BaseModel, Field
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
    records: List[PersonalRecord] = Field(default_factory=list)
    stale: bool = False


class WeightEntry(BaseModel):
    date: str
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_percent: Optional[float] = None


class WeightHistory(BaseModel):
    entries: List[WeightEntry] = Field(default_factory=list)
    avg_weight_kg: Optional[float] = None
    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    stale: bool = False


class FitnessAge(BaseModel):
    current_age: Optional[int] = None
    fitness_age: Optional[int] = None
    potential_fitness_age: Optional[int] = None
    stale: bool = False
