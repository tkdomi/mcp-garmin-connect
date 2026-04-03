from src.models import HRZone, LapData, ActivityData


def test_hr_zone_defaults():
    z = HRZone(zone_number=1)
    assert z.zone_number == 1
    assert z.time_in_zone_seconds is None


def test_lap_data_defaults():
    lap = LapData(lap_index=0)
    assert lap.lap_index == 0
    assert lap.distance_meters is None
    assert lap.duration_seconds is None
    assert lap.avg_pace_per_km_seconds is None
    assert lap.avg_heart_rate is None
    assert lap.avg_cadence is None


def test_activity_data_has_new_fields():
    a = ActivityData()
    assert a.avg_cadence is None
    assert a.max_cadence is None
    assert a.avg_power is None
    assert a.training_effect is None
    assert a.hr_zones is None
    assert a.laps is None


def test_activity_data_with_laps_and_zones():
    a = ActivityData(
        activity_id=123,
        laps=[LapData(lap_index=0, distance_meters=1000.0, duration_seconds=300.0, avg_pace_per_km_seconds=300, avg_heart_rate=150, avg_cadence=170)],
        hr_zones=[HRZone(zone_number=2, time_in_zone_seconds=600)],
        avg_cadence=168.0,
        max_cadence=185.0,
        avg_power=300,
        training_effect=4.2,
    )
    assert len(a.laps) == 1
    assert a.laps[0].avg_pace_per_km_seconds == 300
    assert len(a.hr_zones) == 1
    assert a.hr_zones[0].zone_number == 2
    assert a.training_effect == 4.2
