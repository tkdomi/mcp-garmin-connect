import logging
from typing import List

from src.config import settings
from src.models.alerts import WebhookPayload
from src.models.health import SleepData, DailyStats, BodyBatteryData

logger = logging.getLogger(__name__)


def evaluate_alerts(
    sleep: SleepData | None,
    stats: DailyStats | None,
    battery: BodyBatteryData | None,
) -> List[str]:
    """Evaluate health data against thresholds and return list of alert trigger names."""
    triggers = []

    if battery and battery.current_level is not None:
        if battery.current_level <= settings.alert_body_battery_critical:
            triggers.append("body_battery_critical")
        elif battery.current_level <= settings.alert_body_battery_warning:
            triggers.append("low_body_battery")

    if sleep and sleep.sleep_score is not None:
        if sleep.sleep_score <= settings.alert_sleep_score_critical:
            triggers.append("sleep_critical")
        elif sleep.sleep_score <= settings.alert_sleep_score_warning:
            triggers.append("poor_sleep")

    if stats:
        if stats.avg_stress_level is not None:
            if stats.avg_stress_level >= settings.alert_stress_critical:
                triggers.append("stress_critical")
            elif stats.avg_stress_level >= settings.alert_stress_warning:
                triggers.append("high_stress")

        if stats.total_steps is not None:
            if stats.total_steps <= settings.alert_steps_critical:
                triggers.append("steps_critical")
            elif stats.total_steps <= settings.alert_steps_warning:
                triggers.append("low_steps")

    if triggers:
        logger.info(f"Alert triggers: {triggers}")

    return triggers


def build_webhook_payload(
    sleep: SleepData | None,
    stats: DailyStats | None,
    battery: BodyBatteryData | None,
) -> WebhookPayload:
    """Build webhook payload from synced health data."""
    triggers = evaluate_alerts(sleep, stats, battery)

    return WebhookPayload(
        body_battery=battery.current_level if battery else None,
        sleep_score=sleep.sleep_score if sleep else None,
        hrv=sleep.hrv_last_night if sleep else None,
        steps=stats.total_steps if stats else None,
        avg_stress=stats.avg_stress_level if stats else None,
        alert_triggers=triggers,
    )
