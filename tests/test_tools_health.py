import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.health import StressData, HeartRateData, SpO2RespirationData, HydrationData


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_STRESS = {
    "overallStressLevel": 32,
    "maxStressLevel": 65,
    "restStressDuration": 7200,
    "activityStressDuration": 3600,
    "stressValuesArray": [[1743667200000, 28], [1743670800000, 35]],
}

MOCK_HEART_RATE = {
    "restingHeartRate": 52,
    "maxHeartRate": 178,
    "minHeartRate": 48,
    "heartRateValues": [[1743667200000, 55], [1743670800000, 58]],
}

MOCK_SPO2 = {
    "averageSpO2": 97.2,
    "lowestSpO2": 94.0,
}

MOCK_RESPIRATION = {
    "avgWakingRespirationValue": 14.5,
    "highestRespirationValue": 18.0,
}

MOCK_HYDRATION = {
    "valueInML": 1800,
    "goalInML": 2500,
}


@pytest.mark.asyncio
async def test_get_stress_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_STRESS):
            result = await client.get_stress_data("2026-04-03")

    assert isinstance(result, StressData)
    assert result.date == "2026-04-03"
    assert result.avg_stress == 32
    assert result.max_stress == 65
    assert result.rest_stress == 7200
    assert result.activity_stress == 3600
    assert len(result.hourly_values) == 2


@pytest.mark.asyncio
async def test_get_heart_rate_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_HEART_RATE):
            result = await client.get_heart_rate_data("2026-04-03")

    assert isinstance(result, HeartRateData)
    assert result.resting_hr == 52
    assert result.max_hr == 178
    assert result.min_hr == 48
    assert len(result.hourly_values) == 2


@pytest.mark.asyncio
async def test_get_spo2_respiration_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    def side_effect(endpoint, **kwargs):
        if "spo2" in endpoint:
            return MOCK_SPO2
        elif "respiration" in endpoint:
            return MOCK_RESPIRATION
        return {}

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_spo2_respiration("2026-04-03")

    assert isinstance(result, SpO2RespirationData)
    assert result.avg_spo2 == 97.2
    assert result.min_spo2 == 94.0
    assert result.avg_respiration == 14.5
    assert result.max_respiration == 18.0


@pytest.mark.asyncio
async def test_get_hydration_data_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_HYDRATION):
            result = await client.get_hydration_data("2026-04-03")

    assert isinstance(result, HydrationData)
    assert result.intake_ml == 1800
    assert result.goal_ml == 2500
    assert result.percent_complete == pytest.approx(72.0, rel=0.01)
