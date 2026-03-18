from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Garmin
    garmin_email: str
    garmin_password: str

    # Supabase
    supabase_url: str
    supabase_key: str

    # n8n
    n8n_webhook_url: str
    n8n_bearer_token: str

    # MCP Server
    mcp_port: int = 8080
    mcp_transport: str = "sse"  # "stdio" or "sse"

    # Scheduler
    sync_hour: int = 7
    sync_minute: int = 0

    # Cache TTL (hours)
    cache_ttl_daily: int = 1
    cache_ttl_historical: int = 24

    # Alert thresholds
    alert_body_battery_warning: int = 40
    alert_body_battery_critical: int = 20
    alert_sleep_score_warning: int = 65
    alert_sleep_score_critical: int = 50
    alert_stress_warning: int = 60
    alert_stress_critical: int = 75
    alert_steps_warning: int = 5000
    alert_steps_critical: int = 2000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
