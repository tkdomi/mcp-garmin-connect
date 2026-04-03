import pytest
from unittest.mock import patch
from src.garmin_client import GarminClient
from src.models import ActivityData, ActivityList, LapData, HRZone


MOCK_ACTIVITY_LIST = [{
    "activityId": 99001,
    "activityName": "Morning Run",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2026-04-02 08:00:00",
    "duration": 1800.0,
    "distance": 5000.0,
    "averageHR": 155,
    "maxHR": 175,
    "calories": 400.0,
    "averageSpeed": 2.78,
    "elevationGain": 30.0,
}]

MOCK_ACTIVITY_DETAIL = {
    "summaryDTO": {
        "averageRunCadence": 168.0,
        "maxRunCadence": 182.0,
        "averagePower": 310,
        "normalizedPower": 320,
        "trainingEffect": 4.3,
        "anaerobicTrainingEffect": 2.1,
        "strideLength": 121.0,
        "verticalOscillation": 8.8,
        "groundContactTime": 267.0,
        "steps": 4200,
    },
    "heartRateZones": [
        {"zoneNumber": 1, "secsInZone": 120},
        {"zoneNumber": 2, "secsInZone": 300},
        {"zoneNumber": 3, "secsInZone": 600},
        {"zoneNumber": 4, "secsInZone": 720},
        {"zoneNumber": 5, "secsInZone": 60},
    ],
}

MOCK_LAPS = [
    {"lapIndex": 0, "distance": 1000.0, "duration": 295.0, "averageHR": 152, "averageRunCadence": 166},
    {"lapIndex": 1, "distance": 1000.0, "duration": 305.0, "averageHR": 158, "averageRunCadence": 170},
]


def make_activity_side_effect(activity_id):
    def side_effect(endpoint, **kwargs):
        if "search/activities" in endpoint:
            return MOCK_ACTIVITY_LIST
        elif f"/activity/{activity_id}/laps" in endpoint:
            return {"lapDTOs": MOCK_LAPS}
        elif f"/activity/{activity_id}" in endpoint:
            return MOCK_ACTIVITY_DETAIL
        return {}
    return side_effect


async def mock_to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


# ─── get_activity tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_activity_no_id_returns_enriched_data():
    client = GarminClient()
    client._authenticated = True

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi",
                   side_effect=make_activity_side_effect(99001)):
            result = await client.get_activity()

    assert isinstance(result, ActivityData)
    assert result.activity_id == 99001
    assert result.avg_cadence == 168.0
    assert result.max_cadence == 182.0
    assert result.avg_power == 310
    assert result.training_effect == 4.3
    assert result.steps == 4200
    assert len(result.hr_zones) == 5
    assert result.hr_zones[0].zone_number == 1
    assert result.hr_zones[0].time_in_zone_seconds == 120
    assert len(result.laps) == 2
    assert result.laps[0].avg_pace_per_km_seconds == 295
    assert result.laps[0].avg_heart_rate == 152
    assert result.laps[0].avg_cadence == 166


@pytest.mark.asyncio
async def test_get_activity_by_id_fetches_correct_activity():
    client = GarminClient()
    client._authenticated = True
    called_endpoints = []

    def side_effect(endpoint, **kwargs):
        called_endpoints.append(endpoint)
        if "search/activities" in endpoint:
            return MOCK_ACTIVITY_LIST
        elif "/laps" in endpoint:
            return {"lapDTOs": MOCK_LAPS}
        else:
            return MOCK_ACTIVITY_DETAIL

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_activity(activity_id=99001)

    assert result.activity_id == 99001
    assert any("search/activities" in ep for ep in called_endpoints)
    assert any("/activity/99001" in ep for ep in called_endpoints)


@pytest.mark.asyncio
async def test_get_activity_degrades_gracefully_on_detail_failure():
    client = GarminClient()
    client._authenticated = True

    def side_effect(endpoint, **kwargs):
        if "search/activities" in endpoint:
            return MOCK_ACTIVITY_LIST
        raise Exception("403 Forbidden")

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_activity()

    assert result.activity_id == 99001
    assert result.avg_cadence is None
    assert result.laps is None
    assert result.hr_zones is None


@pytest.mark.asyncio
async def test_get_activity_empty_list_returns_empty():
    client = GarminClient()
    client._authenticated = True

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", return_value=[]):
            result = await client.get_activity()

    assert result == ActivityData()


# ─── get_activities_list tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_activities_list_no_filter():
    client = GarminClient()
    client._authenticated = True
    captured_params = {}

    def side_effect(endpoint, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return MOCK_ACTIVITY_LIST

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            result = await client.get_activities_list()

    assert isinstance(result, ActivityList)
    assert result.count == 1
    assert result.activities[0].activity_id == 99001
    assert captured_params["limit"] == 10
    assert "activityType" not in captured_params
    assert "startDate" not in captured_params


@pytest.mark.asyncio
async def test_get_activities_list_with_type():
    client = GarminClient()
    client._authenticated = True
    captured_params = {}

    def side_effect(endpoint, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return MOCK_ACTIVITY_LIST

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            await client.get_activities_list(activity_type="running")

    assert captured_params["activityType"] == "running"


@pytest.mark.asyncio
async def test_get_activities_list_swimming_maps_to_lap_swimming():
    client = GarminClient()
    client._authenticated = True
    captured_params = {}

    def side_effect(endpoint, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return []

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            await client.get_activities_list(activity_type="swimming")

    assert captured_params["activityType"] == "lap_swimming"


@pytest.mark.asyncio
async def test_get_activities_list_with_date_range():
    client = GarminClient()
    client._authenticated = True
    captured_params = {}

    def side_effect(endpoint, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return []

    with patch("src.garmin_client.asyncio.to_thread", side_effect=mock_to_thread):
        with patch("src.garmin_client.garth.connectapi", side_effect=side_effect):
            await client.get_activities_list(start_date="2026-03-31", end_date="2026-04-03")

    assert captured_params["startDate"] == "2026-03-31"
    assert captured_params["endDate"] == "2026-04-03"
