import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.training import TrainingStatus, VO2MaxData, TrainingLoad, RacePredictions


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_TRAINING_STATUS = {
    "trainingStatusDTO": {
        "latestTrainingStatusPhrase": "Productive",
        "trainingReadinessDTO": {"score": 72},
        "acuteLoad": 420.0,
        "chronicLoad": 385.0,
    }
}

MOCK_VO2MAX = {
    "generic": {
        "vo2MaxValue": 52.0,
        "fitnessAge": 34,
    },
    "running": {
        "vo2MaxValue": 52.0,
    }
}

MOCK_TRAINING_LOAD = {
    "metricsMap": {
        "TRAINING_LOAD_7_DAYS": [
            {"value": 520.0, "startDate": "2026-03-27"}
        ]
    },
    "aerobicLowLoad": 180.0,
    "aerobicHighLoad": 250.0,
    "anaerobicLoad": 90.0,
}

MOCK_RACE_PREDICTIONS = {
    "racePredictions": [
        {"distance": 5000, "time": 1380},
        {"distance": 10000, "time": 2880},
        {"distance": 21097, "time": 6300},
        {"distance": 42195, "time": 13200},
    ]
}


@pytest.mark.asyncio
async def test_get_training_status_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_TRAINING_STATUS):
            result = await client.get_training_status("2026-04-03")

    assert isinstance(result, TrainingStatus)
    assert result.date == "2026-04-03"
    assert result.training_status == "Productive"
    assert result.training_readiness_score == 72
    assert result.acute_load == 420.0
    assert result.chronic_load == 385.0
    assert result.load_ratio == pytest.approx(1.09, rel=0.01)


@pytest.mark.asyncio
async def test_get_vo2max_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_VO2MAX):
            result = await client.get_vo2max("running")

    assert isinstance(result, VO2MaxData)
    assert result.sport == "running"
    assert result.value == 52.0
    assert result.fitness_age_equivalent == 34


@pytest.mark.asyncio
async def test_get_training_load_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_TRAINING_LOAD):
            result = await client.get_training_load("2026-03-27")

    assert isinstance(result, TrainingLoad)
    assert result.week_start == "2026-03-27"
    assert result.total_load == 520.0
    assert result.aerobic_low == 180.0
    assert result.aerobic_high == 250.0
    assert result.anaerobic == 90.0


@pytest.mark.asyncio
async def test_get_race_predictions_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "testuser"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_RACE_PREDICTIONS):
            result = await client.get_race_predictions()

    assert isinstance(result, RacePredictions)
    assert result.race_5k_seconds == 1380
    assert result.race_10k_seconds == 2880
    assert result.half_marathon_seconds == 6300
    assert result.marathon_seconds == 13200
