import logging
import asyncio
from datetime import date, timedelta
from typing import Optional
from functools import wraps

import garth
from garth.exc import GarthHTTPError

from src.config import settings
from src.models.health import (
    SleepData, BodyBatteryData, BodyBatteryEntry, DailyStats,
    StressData, HeartRateData, SpO2RespirationData, HydrationData,
)
from src.models.training import (
    ActivityData, HRZone, LapData, ActivitySummary, ActivityList,
    TrainingStatus, VO2MaxData, VO2MaxHistory, TrainingLoad, RacePredictions,
)

logger = logging.getLogger(__name__)

ACTIVITY_TYPE_MAP: dict[str, str] = {
    "swimming": "lap_swimming",
}

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
        self._display_name: Optional[str] = None

    def _fetch_display_name(self):
        try:
            profile = garth.connectapi("/userprofile-service/userprofile/personal-information")
            self._display_name = profile.get("displayName") or profile.get("userName")
            if not self._display_name:
                logger.warning("Display name not found in profile, falling back to email.")
                self._display_name = settings.garmin_email
            logger.info(f"Garmin display name: {self._display_name}")
        except Exception as e:
            logger.warning(f"Could not fetch display name, falling back to email: {e}")
            self._display_name = settings.garmin_email

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
        if self._display_name is None:
            self._fetch_display_name()

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
            f"/usersummary-service/usersummary/daily/{self._display_name}",
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
        pct = round(intake / goal * 100, 1) if intake is not None and goal and goal > 0 else None

        return HydrationData(
            date=target_date,
            goal_ml=goal,
            intake_ml=intake,
            percent_complete=pct,
        )

    @with_retry
    async def get_activities_list(
        self,
        activity_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> ActivityList:
        """Fetch a list of activities with optional type and date filters."""
        self._ensure_auth()
        params: dict = {"limit": limit, "start": 0}
        if activity_type:
            params["activityType"] = ACTIVITY_TYPE_MAP.get(activity_type, activity_type)
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        data = await asyncio.to_thread(
            garth.connectapi,
            "/activitylist-service/activities/search/activities",
            params=params,
        )
        activities = [
            ActivitySummary(
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
            for a in (data or [])
        ]
        return ActivityList(activities=activities, count=len(activities))

    @with_retry
    async def get_activity(self, activity_id: Optional[int] = None) -> ActivityData:
        """Fetch full details of a single activity. Defaults to most recent if no ID given."""
        self._ensure_auth()

        if activity_id is None:
            data = await asyncio.to_thread(
                garth.connectapi,
                "/activitylist-service/activities/search/activities",
                params={"limit": 1, "start": 0},
            )
            if not data:
                return ActivityData()
            a = data[0]
            activity_id = a.get("activityId")
        else:
            data = await asyncio.to_thread(
                garth.connectapi,
                "/activitylist-service/activities/search/activities",
                params={"activityId": activity_id, "limit": 1, "start": 0},
            )
            a = data[0] if data else {}

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
            base.avg_cadence = summary.get("averageRunCadence")
            base.max_cadence = summary.get("maxRunCadence")
            base.avg_power = summary.get("averagePower")
            base.normalized_power = summary.get("normalizedPower")
            base.training_effect = summary.get("trainingEffect")
            base.anaerobic_training_effect = summary.get("anaerobicTrainingEffect")
            base.stride_length_cm = summary.get("strideLength")
            base.vertical_oscillation_cm = summary.get("verticalOscillation")
            base.ground_contact_time_ms = summary.get("groundContactTime")
            base.steps = summary.get("steps")
            base.hr_zones = [
                HRZone(zone_number=z["zoneNumber"], time_in_zone_seconds=z.get("secsInZone"))
                for z in (detail.get("heartRateZones") or [])
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
                dist, dur = lap.get("distance"), lap.get("duration")
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
        value = (sport_data or {}).get("vo2MaxValue") or generic.get("vo2MaxValue")

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
