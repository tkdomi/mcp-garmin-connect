import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models.profile import UserProfile, PersonalRecords, WeightHistory, FitnessAge


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


MOCK_PROFILE = {
    "displayName": "runner42",
    "fullName": "Jan Kowalski",
    "userEmail": "jan@example.com",
    "birthDate": "1990-05-15",
    "genderType": "MALE",
    "weight": 75000.0,
    "height": 180.0,
}

MOCK_PERSONAL_RECORDS = [
    {"activityType": "running", "typeKey": "fastest5K", "value": 1320.0, "activityStartDateTimeLocal": "2025-10-12 08:00:00"},
    {"activityType": "running", "typeKey": "longestRun", "value": 42195.0, "activityStartDateTimeLocal": "2025-04-06 09:00:00"},
]

MOCK_FITNESS_AGE = {
    "chronologicalAge": 35,
    "fitnessAge": 28,
    "potentialFitnessAge": 25,
}

MOCK_WEIGHT = {
    "dailyWeightSummaries": [
        {"date": "2026-04-01 08:00:00", "weight": 75200.0, "bmi": 23.2, "bodyFat": 18.5},
        {"date": "2026-03-25 08:00:00", "weight": 75500.0, "bmi": 23.3, "bodyFat": 18.8},
    ]
}


@pytest.mark.asyncio
async def test_get_user_profile_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_PROFILE):
            result = await client.get_user_profile()

    assert isinstance(result, UserProfile)
    assert result.display_name == "runner42"
    assert result.full_name == "Jan Kowalski"
    assert result.birth_date == "1990-05-15"
    assert result.gender == "MALE"
    assert result.weight_kg == pytest.approx(75.0, rel=0.01)
    assert result.height_cm == 180.0


@pytest.mark.asyncio
async def test_get_personal_records_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_PERSONAL_RECORDS):
            result = await client.get_personal_records()

    assert isinstance(result, PersonalRecords)
    assert len(result.records) == 2
    assert result.records[0].type_key == "fastest5K"
    assert result.records[0].value == 1320.0
    assert result.records[0].pr_date == "2025-10-12"


@pytest.mark.asyncio
async def test_get_fitness_age_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_FITNESS_AGE):
            result = await client.get_fitness_age()

    assert isinstance(result, FitnessAge)
    assert result.current_age == 35
    assert result.fitness_age == 28
    assert result.potential_fitness_age == 25


@pytest.mark.asyncio
async def test_get_weight_history_parses_correctly():
    client = GarminClient()
    client._authenticated = True
    client._display_name = "runner42"

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=MOCK_WEIGHT):
            result = await client.get_weight_history(30)

    assert isinstance(result, WeightHistory)
    assert len(result.entries) == 2
    assert result.entries[0].weight_kg == pytest.approx(75.2, rel=0.01)
    assert result.entries[0].body_fat_percent == 18.5
    assert result.avg_weight_kg is not None
