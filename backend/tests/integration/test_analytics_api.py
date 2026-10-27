"""GET /v1/analytics/summary through the real API, DynamoDB (moto) and engine."""

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.api.dependencies import get_analytics_service
from app.core.config import get_settings
from app.domain.analytics import DISCLAIMER, compute_summary
from app.domain.models import Goal
from app.main import app
from app.repositories.checkins import CheckInRepository
from app.repositories.dynamodb import get_table
from app.repositories.profiles import ProfileRepository
from app.repositories.workouts import WorkoutRepository
from app.services.analytics import AnalyticsService, round_floats
from tests.integration.conftest import ALICE, BOB, as_user
from tests.unit.test_analytics import (
    AS_OF,
    worked_example_checkins,
    worked_example_workouts,
)

NOON_UTC_ON_AS_OF = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def freeze_clock(now: datetime) -> None:
    """Make the analytics service see a fixed 'now' (UTC)."""

    def service() -> AnalyticsService:
        table = get_table(get_settings())
        return AnalyticsService(
            WorkoutRepository(table),
            CheckInRepository(table),
            ProfileRepository(table),
            clock=lambda: now,
        )

    app.dependency_overrides[get_analytics_service] = service


def post_record(client, headers, record) -> None:
    body = {
        "type": record.workout_type.value,
        "date": record.workout_date.isoformat(),
        "duration_min": record.duration_min,
        "rpe": record.rpe,
    }
    if record.distance_km is not None:
        body["distance_km"] = record.distance_km
    assert client.post("/v1/workouts", json=body, headers=headers).status_code == 201


def put_checkin(client, headers, checkin) -> None:
    body = {
        k: v
        for k, v in {
            "sleep_hours": checkin.sleep_hours,
            "fatigue": checkin.fatigue,
            "soreness": checkin.soreness,
        }.items()
        if v is not None
    }
    url = f"/v1/checkins/{checkin.checkin_date.isoformat()}"
    assert client.put(url, json=body, headers=headers).status_code == 200


def summary(client, headers) -> dict:
    response = client.get("/v1/analytics/summary", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def worked_example(client):
    """The hand-verified worked example, written through the real endpoints."""
    client.put("/v1/me/profile", json={"goal": "endurance", "timezone": "UTC"}, headers=ALICE)
    for record in worked_example_workouts():
        post_record(client, ALICE, record)
    for checkin in worked_example_checkins():
        put_checkin(client, ALICE, checkin)
    freeze_clock(NOON_UTC_ON_AS_OF)
    return client


# ---------------------------------------------------------------------------
# Worked example end to end
# ---------------------------------------------------------------------------
def test_worked_example_matches_hand_calculation(worked_example) -> None:
    s = summary(worked_example, ALICE)

    assert s["as_of"] == "2026-10-27"
    assert s["goal"] == "endurance"
    assert s["current_week"]["sessions"] == 5
    assert s["current_week"]["training_days"] == 4
    assert s["current_week"]["rest_days"] == 3
    assert s["current_week"]["duration_min"] == 275
    assert s["current_week"]["run_distance_km"] == 23.0
    assert s["current_week"]["ride_distance_km"] == 40.0
    assert s["load"] == {
        "load_7d": 1750,
        "load_previous_7d": 800,
        "load_28d": 4150,
        "chronic_weekly_load": 800.0,
        "weekly_change_pct": 118.75,
        "acwr": 2.19,  # 2.1875 rounded half-up to 2 decimals
        "history_days": 28,
    }
    assert s["consistency"]["consistency_pct"] == 25.0
    assert s["consistency"]["avg_sessions_per_week"] == 3.5
    assert s["wellness"]["avg_fatigue"] == 4.33
    assert s["wellness"]["avg_sleep_hours"] == 5.25
    statuses = {f["code"]: f["status"] for f in s["flags"]}
    assert statuses == {
        "weekly_load_jump": "triggered",
        "acwr_spike": "triggered",
        "sustained_fatigue": "triggered",
        "short_sleep": "insufficient_data",
    }
    assert s["overall_status"] == "elevated"
    assert s["goal_summary"]["metrics"]["endurance_distance_km"] == 63.0
    assert s["disclaimer"] == DISCLAIMER
    assert "not medical" in s["disclaimer"]


def test_api_output_equals_engine_output(worked_example) -> None:
    expected = round_floats(
        asdict(
            compute_summary(
                worked_example_workouts(), worked_example_checkins(), Goal.ENDURANCE, AS_OF
            )
        )
    )
    actual = summary(worked_example, ALICE)

    for key, value in expected.items():
        assert actual[key] == (value.isoformat() if isinstance(value, date) else value), key


# ---------------------------------------------------------------------------
# History beyond the 28-day window
# ---------------------------------------------------------------------------
def test_old_history_is_reflected_without_reading_it_all(client) -> None:
    """A workout 60 days ago must make history_days = 61 and enable ACWR, exactly as
    if the engine had received the full history."""
    workouts = worked_example_workouts()
    old = workouts[0].__class__(AS_OF - timedelta(days=60), workouts[0].workout_type, 30, 4, 5.0)
    middle = workouts[0].__class__(AS_OF - timedelta(days=45), workouts[0].workout_type, 30, 4)
    client.put("/v1/me/profile", json={"goal": "endurance", "timezone": "UTC"}, headers=ALICE)
    for record in [old, middle, *workouts]:
        post_record(client, ALICE, record)
    freeze_clock(NOON_UTC_ON_AS_OF)

    s = summary(client, ALICE)
    full_history = round_floats(
        asdict(compute_summary([old, middle, *workouts], [], Goal.ENDURANCE, AS_OF))
    )

    assert s["load"]["history_days"] == 61
    assert s["load"] == full_history["load"]
    assert s["consistency"] == full_history["consistency"]
    # Out-of-window records add no load and no sessions to any window.
    assert s["load"]["load_28d"] == 4150


# ---------------------------------------------------------------------------
# Timezones
# ---------------------------------------------------------------------------
def test_timezone_decides_which_day_is_today(client) -> None:
    """At 03:00 UTC on Oct 28 it is still Oct 27 in Los Angeles."""
    alice, tokyo = ALICE, as_user("tokyo-user")
    client.put(
        "/v1/me/profile",
        json={"goal": "general_fitness", "timezone": "America/Los_Angeles"},
        headers=alice,
    )
    client.put(
        "/v1/me/profile",
        json={"goal": "general_fitness", "timezone": "Asia/Tokyo"},
        headers=tokyo,
    )
    for headers in (alice, tokyo):
        body = {"type": "run", "date": "2026-10-21", "duration_min": 30, "rpe": 5}
        client.post("/v1/workouts", json=body, headers=headers)
    freeze_clock(datetime(2026, 10, 28, 3, 0, tzinfo=UTC))

    la = summary(client, alice)
    jp = summary(client, tokyo)

    assert (la["as_of"], la["timezone"]) == ("2026-10-27", "America/Los_Angeles")
    assert jp["as_of"] == "2026-10-28"
    # Oct 21 is in LA's current window (Oct 21-27) but Tokyo's previous one (Oct 15-21).
    assert la["current_week"]["sessions"] == 1
    assert jp["current_week"]["sessions"] == 0
    assert jp["previous_week"]["sessions"] == 1


def test_missing_profile_uses_utc_and_general_fitness(client) -> None:
    client.post(
        "/v1/workouts",
        json={"type": "ride", "date": "2026-10-27", "duration_min": 60, "rpe": 5},
        headers=ALICE,
    )
    freeze_clock(datetime(2026, 10, 27, 23, 30, tzinfo=UTC))

    s = summary(client, ALICE)

    assert s["profile_configured"] is False
    assert (s["timezone"], s["goal"], s["as_of"]) == ("UTC", "general_fitness", "2026-10-27")
    assert s["consistency"]["target_sessions_per_week"] == 3
    assert s["current_week"]["load"] == 300


# ---------------------------------------------------------------------------
# Empty and partial data
# ---------------------------------------------------------------------------
def test_empty_history_returns_valid_summary(client) -> None:
    freeze_clock(NOON_UTC_ON_AS_OF)
    s = summary(client, as_user("brand-new"))

    assert s["current_week"]["sessions"] == 0
    assert s["current_week"]["rest_days"] == 7
    assert s["load"]["weekly_change_pct"] is None
    assert s["load"]["acwr"] is None
    assert s["consistency"]["consistency_pct"] is None
    assert s["overall_status"] == "insufficient_data"
    assert all(f["status"] == "insufficient_data" for f in s["flags"])
    assert s["disclaimer"] == DISCLAIMER


def test_workouts_without_checkins_leave_wellness_null(worked_example, table) -> None:
    # Remove Alice's check-ins; workouts remain.
    for checkin in worked_example_checkins():
        table.delete_item(
            Key={"PK": "USER#alice", "SK": f"CHECKIN#{checkin.checkin_date.isoformat()}"}
        )

    s = summary(worked_example, ALICE)

    assert s["current_week"]["load"] == 1750
    assert s["wellness"]["avg_fatigue"] is None
    assert s["wellness"]["avg_sleep_hours"] is None
    statuses = {f["code"]: f["status"] for f in s["flags"]}
    assert statuses["sustained_fatigue"] == "insufficient_data"
    assert statuses["short_sleep"] == "insufficient_data"
    assert s["overall_status"] == "elevated"  # both load flags still trigger


# ---------------------------------------------------------------------------
# Isolation, auth, efficiency
# ---------------------------------------------------------------------------
def test_other_users_data_never_appears(worked_example) -> None:
    s = summary(worked_example, BOB)
    assert s["current_week"]["sessions"] == 0
    assert s["load"]["load_28d"] == 0
    assert s["wellness"]["fatigue_days_reported"] == 0
    assert s["profile_configured"] is False


def test_summary_requires_authentication(client) -> None:
    response = client.get("/v1/analytics/summary")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_summary_uses_queries_not_scans(worked_example, table) -> None:
    table.scan = MagicMock(side_effect=AssertionError("Scan is not allowed"))
    service = AnalyticsService(
        WorkoutRepository(table),
        CheckInRepository(table),
        ProfileRepository(table),
        clock=lambda: NOON_UTC_ON_AS_OF,
    )

    result = service.summary("alice")

    assert result.load.load_7d == 1750
    table.scan.assert_not_called()


def test_earliest_ignores_profile_and_checkin_items(client, table) -> None:
    # PROFILE and CHECKIN# share the partition; earliest() must only see workouts.
    client.put("/v1/me/profile", json={"goal": "strength", "timezone": "UTC"}, headers=ALICE)
    client.put("/v1/checkins/2026-01-01", json={"fatigue": 2}, headers=ALICE)
    assert WorkoutRepository(table).earliest("alice") is None

    client.post(
        "/v1/workouts",
        json={"type": "run", "date": "2026-03-05", "duration_min": 20, "rpe": 3},
        headers=ALICE,
    )
    assert WorkoutRepository(table).earliest("alice").record.workout_date == date(2026, 3, 5)
