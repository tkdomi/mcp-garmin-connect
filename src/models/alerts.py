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
