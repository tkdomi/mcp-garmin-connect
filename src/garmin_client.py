import logging
import asyncio
from datetime import date, timedelta
from typing import Optional
from functools import wraps

import garth
from garth.exc import GarthHTTPError

from src.config import settings
from src.models import SleepData, BodyBatteryData, DailyStats, ActivityData, BodyBatteryEntry

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


def with_retry(func):
    """Decorator: retry with exponential backoff on GarthHTTPError."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except GarthHTTPError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = RETRY_BACKOFF ** attempt
                logger.warning(f"Garmin API error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
    return wrapper


class GarminClient:
    def __init__(self):
        self._authenticated = False

    def authenticate(self):
        """Login to Garmin Connect and persist session via garth."""
        try:
            garth.login(settings.garmin_email, settings.garmin_password)
            garth.save("~/.garth")
            self._authenticated = True
            logger.info("Garmin authentication successful.")
        except Exception as e:
            logger.error(f"Garmin authentication failed: {e}")
            raise

    def _ensure_auth(self):
        if not self._authenticated:
            try:
                garth.resume("~/.garth")
                self._authenticated = True
                logger.info("Garmin session resumed from cache.")
            except Exception:
                logger.info("No cached session found, authenticating...")
                self.authenticate()

    @with_retry
    async def get_sleep_data(self, target_date: Optional[str] = None) -> SleepData:
        """Fetch sleep data for a given date (YYYY-MM-DD). Defaults to last night."""
        self._ensure_auth()
        if not target_date:
            target_date = (date.today() - timedelta(days=1)).isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/wellness-service/wellness/dailySleepData/{settings.garmin_email}",
            params={"date": target_date, "nonSleepBufferMinutes": 60}
        )

        daily = data.get("dailySleepDTO", {})
        return SleepData(
            date=target_date,
            sleep_score=daily.get("sleepScores", {}).get("overall", {}).get("value"),
            total_sleep_seconds=daily.get("sleepTimeSeconds"),
            deep_sleep_seconds=daily.get("deepSleepSeconds"),
            light_sleep_seconds=daily.get("lightSleepSeconds"),
            rem_sleep_seconds=daily.get("remSleepSeconds"),
            awake_seconds=daily.get("awakeSleepSeconds"),
            hrv_weekly_average=data.get("hrvSummary", {}).get("weeklyAvg"),
            hrv_last_night=data.get("hrvSummary", {}).get("lastNight"),
            avg_overnight_hrv=data.get("hrvSummary", {}).get("lastNight5MinHigh"),
            resting_heart_rate=daily.get("restingHeartRate"),
        )

    @with_retry
    async def get_body_battery(self) -> BodyBatteryData:
        """Fetch current Body Battery level and today's trend."""
        self._ensure_auth()
        today = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            "/wellness-service/wellness/bodyBattery/reports/daily",
            params={"startDate": today, "endDate": today}
        )

        if not data:
            return BodyBatteryData()

        report = data[0] if isinstance(data, list) else data
        readings = report.get("bodyBatteryReadingDTO", [])

        current = readings[-1]["bodyBatteryLevel"] if readings else None
        trend = [
            BodyBatteryEntry(timestamp=r["timestampGMT"], level=r["bodyBatteryLevel"])
            for r in readings
        ]

        return BodyBatteryData(
            current_level=current,
            charged=report.get("charged"),
            drained=report.get("drained"),
            trend=trend,
        )

    @with_retry
    async def get_daily_stats(self, target_date: Optional[str] = None) -> DailyStats:
        """Fetch daily stats (steps, calories, stress, HR) for a given date."""
        self._ensure_auth()
        if not target_date:
            target_date = date.today().isoformat()

        data = await asyncio.to_thread(
            garth.connectapi,
            f"/usersummary-service/usersummary/daily/{settings.garmin_email}",
            params={"calendarDate": target_date}
        )

        return DailyStats(
            date=target_date,
            total_steps=data.get("totalSteps"),
            step_goal=data.get("dailyStepGoal"),
            total_kilocalories=data.get("totalKilocalories"),
            active_kilocalories=data.get("activeKilocalories"),
            floors_ascended=data.get("floorsAscended"),
            minutes_sedentary=data.get("sedentaryMinutes"),
            minutes_lightly_active=data.get("lightlyActiveMinutes"),
            minutes_fairly_active=data.get("fairlyActiveMinutes"),
            minutes_highly_active=data.get("highlyActiveMinutes"),
            avg_stress_level=data.get("averageStressLevel"),
            max_stress_level=data.get("maxStressLevel"),
            rest_stress_duration=data.get("restStressDuration"),
            resting_heart_rate=data.get("restingHeartRate"),
            max_heart_rate=data.get("maxHeartRate"),
        )

    @with_retry
    async def get_last_activity(self) -> ActivityData:
        """Fetch the most recent physical activity."""
        self._ensure_auth()

        data = await asyncio.to_thread(
            garth.connectapi,
            "/activitylist-service/activities/search/activities",
            params={"limit": 1, "start": 0}
        )

        if not data:
            return ActivityData()

        a = data[0]
        return ActivityData(
            activity_id=a.get("activityId"),
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
